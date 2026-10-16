"""
Submissions API Endpoints
Accepting student code submissions, orchestrating dual-track evaluation, and returning evidence-backed scores.
"""

from datetime import datetime, timezone, timedelta
import hashlib
import json
import logging
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from evaluation_specifications.models import RubricSchema
from app.api.deps import get_current_user
from app.core.authz import (
    FACULTY_ROLES,
    authorize_submission_access,
    verify_organization_access,
)
from app.db.session import get_db
from app.evaluation.feedback.explainer import IntelligentExplainer
from app.models.problem import GradingRubric, Problem, ProblemVersion, TestCase
from app.models.submission import (
    ConceptEvidenceRecord,
    EvaluationRun,
    ScoreBreakdown,
    Submission,
    SubmissionFeedback,
    TestCaseResult,
)
from app.models.user import User
from app.schemas.submission import (
    ConceptEvidenceResponse,
    CriterionScoreResponse,
    SubmissionCreateRequest,
    SubmissionResponse,
    TestCaseSummaryResponse,
)
from app.tasks.evaluation import evaluate_submission_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/submissions", tags=["Submissions"])


@router.post("", response_model=SubmissionResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_submission(
    req: SubmissionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Submit Python source code for dual-track evaluation.
    Verifies problem accessibility and organization membership on server.
    Persists a durable queued submission and dispatches evaluation to background Celery worker.
    Returns HTTP 202 Accepted.
    """
    # 1. Fetch published problem version
    stmt = (
        select(ProblemVersion)
        .join(Problem, Problem.id == ProblemVersion.problem_id)
        .where(
            Problem.id == req.problem_id,
            ProblemVersion.version_number == req.problem_version_number,
            Problem.status == "published",
        )
        .options(selectinload(ProblemVersion.problem))
    )
    pv = (await db.execute(stmt)).scalars().first()

    if not pv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROBLEM_VERSION_NOT_FOUND", "message": "Published problem version not found."},
        )

    # 2. Multi-tenant organization scoping
    target_org_id: Optional[str] = None
    if pv.problem.owner_type == "organization":
        if not pv.problem.owner_organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PROBLEM_NOT_FOUND", "message": "Problem is missing owning organization."},
            )
        # Caller MUST be a verified member of the problem's owning organization
        await verify_organization_access(db, current_user.id, pv.problem.owner_organization_id)
        target_org_id = pv.problem.owner_organization_id
        if req.organization_id and req.organization_id != target_org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "ORGANIZATION_MISMATCH",
                    "message": "Supplied organization_id does not match the problem's owning organization.",
                },
            )
    else:
        # Platform problem: client may optionally associate with their verified organization
        if req.organization_id:
            await verify_organization_access(db, current_user.id, req.organization_id)
            target_org_id = req.organization_id

    # 3. Compute source code SHA256 hash
    source_hash = hashlib.sha256(req.source_code.encode("utf-8")).hexdigest()

    # Deduplicate rapid repeated clicks within 5 seconds for the same user, problem, and code
    last_dup = (
        await db.execute(
            select(Submission)
            .where(
                Submission.user_id == current_user.id,
                Submission.problem_version_id == pv.id,
                Submission.source_hash == source_hash,
            )
            .order_by(Submission.created_at.desc())
        )
    ).scalars().first()

    if last_dup and last_dup.created_at:
        last_dt = last_dup.created_at
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        now_dt = datetime.now(timezone.utc)
        diff_sec = abs((now_dt - last_dt).total_seconds())
        if diff_sec <= 5.0:
            return SubmissionResponse(
                id=last_dup.id,
                user_id=last_dup.user_id,
                organization_id=last_dup.organization_id,
                problem_id=req.problem_id,
                status=last_dup.status,
                verdict="accepted" if last_dup.status == "completed" else last_dup.status,
                language=last_dup.language,
                created_at=last_dup.created_at,
                completed_at=last_dup.completed_at,
                total_score=None,
                syntax_valid=None,
                summary_feedback="Submission queued for evaluation (deduplicated).",
                criteria_scores=[],
                concept_evidence=[],
                test_case_results=[],
                actionable_suggestions=[],
            )

    # 4. Create durable Submission record in queued state
    submission = Submission(
        user_id=current_user.id,
        organization_id=target_org_id,
        problem_version_id=pv.id,
        language=req.language,
        source_code=req.source_code,
        source_hash=source_hash,
        status="queued",
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # 5. Dispatch asynchronous evaluation task to Celery message broker
    try:
        evaluate_submission_task.delay(submission.id)
    except Exception as broker_err:
        logger.error(f"Failed to dispatch evaluation task for submission {submission.id} to Celery: {broker_err}")
        submission.status = "infrastructure_error"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "BROKER_UNAVAILABLE",
                "message": "Evaluation message broker is currently unavailable. Submission could not be queued.",
                "submission_id": submission.id,
            },
        )

    return SubmissionResponse(
        id=submission.id,
        user_id=submission.user_id,
        organization_id=submission.organization_id,
        problem_id=req.problem_id,
        status=submission.status,
        language=submission.language,
        created_at=submission.created_at,
        completed_at=None,
        total_score=None,
        syntax_valid=None,
        summary_feedback="Submission queued for evaluation.",
        criteria_scores=[],
        concept_evidence=[],
        test_case_results=[],
        actionable_suggestions=[],
    )


@router.get("/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve an authorized submission with complete score breakdown and concept evidence."""
    stmt = (
        select(Submission)
        .where(Submission.id == submission_id)
        .options(
            selectinload(Submission.evaluation_runs).selectinload(EvaluationRun.score_breakdowns),
            selectinload(Submission.evaluation_runs).selectinload(EvaluationRun.concept_evidence),
            selectinload(Submission.evaluation_runs).selectinload(EvaluationRun.test_results),
            selectinload(Submission.evaluation_runs).selectinload(EvaluationRun.feedback),
        )
    )
    sub = (await db.execute(stmt)).scalars().first()

    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SUBMISSION_NOT_FOUND", "message": "Submission record not found."},
        )

    # Verify authorization: student owner or verified faculty of the submission's organization
    await authorize_submission_access(db, current_user, sub)


    latest_eval = sub.evaluation_runs[-1] if sub.evaluation_runs else None
    criteria_scores = []
    concept_evidences = []
    test_results = []
    summary_feedback = None
    suggestions = []
    total_score = None
    syntax_valid = None

    if sub.status == "queued":
        summary_feedback = "Submission queued for background evaluation."
    elif sub.status == "running":
        summary_feedback = "Submission evaluation in progress."
    elif sub.status == "infrastructure_error":
        err_detail = latest_eval.failure_category if latest_eval else "Worker or database failure"
        summary_feedback = f"Infrastructure error during evaluation: {err_detail}"

    if latest_eval and latest_eval.status in ("completed", "failed"):
        syntax_valid = (latest_eval.failure_category is None)
        criteria_scores = [
            CriterionScoreResponse(
                criterion=s.criterion,
                max_points=s.max_points,
                awarded_points=s.awarded_points,
                passed=(s.awarded_points == s.max_points),
                reason_code=s.reason_code,
                explanation="",
            )
            for s in latest_eval.score_breakdowns
        ]
        total_score = sum(s.awarded_points for s in latest_eval.score_breakdowns)

        concept_evidences = [
            ConceptEvidenceResponse(
                concept=ce.concept_name,
                rule_id=ce.rule_id,
                passed=(ce.status == "passed"),
                occurrences_found=1 if ce.status == "passed" else 0,
                message=ce.explanation_code or "",
            )
            for ce in latest_eval.concept_evidence
        ]

        test_results = [
            TestCaseSummaryResponse(
                test_case_id=tr.test_case_id,
                visibility="public",
                status=tr.status,
                execution_time_ms=tr.execution_time_ms,
                actual_output_summary=tr.actual_output_summary,
                error_message=tr.failure_category,
            )
            for tr in latest_eval.test_results
        ]

        if latest_eval.feedback:
            try:
                fb_data = json.loads(latest_eval.feedback.feedback_json)
                summary_feedback = fb_data.get("summary")
                suggestions = fb_data.get("suggestions", [])
            except Exception:
                pass

        # Calculate granular evaluation verdict adhering to Requirement 2
        has_compile_err = any(tr.status == "compilation_error" for tr in latest_eval.test_results) or (latest_eval.failure_category and "syntax" in latest_eval.failure_category.lower())
        has_timeout = any(tr.status == "timeout" for tr in latest_eval.test_results)
        has_runtime_err = any(tr.status == "runtime_error" for tr in latest_eval.test_results)
        has_failed_tests = any(tr.status in ("failed", "wrong_answer") for tr in latest_eval.test_results)
        violated_concepts = [ce for ce in latest_eval.concept_evidence if ce.status == "failed"]

        if has_compile_err:
            eval_verdict = "compilation_error"
        elif has_timeout:
            eval_verdict = "time_limit_exceeded"
        elif has_runtime_err:
            eval_verdict = "runtime_error"
        elif has_failed_tests:
            eval_verdict = "wrong_answer"
        elif violated_concepts:
            eval_verdict = "concept_not_satisfied"
        elif total_score == 100.0:
            eval_verdict = "accepted"
        else:
            eval_verdict = "completed"

        # Load problem statement for pedagogical feedback
        pv_stmt = select(ProblemVersion).where(ProblemVersion.id == sub.problem_version_id)
        pv_obj = (await db.execute(pv_stmt)).scalars().first()
        prob_title = pv_obj.title if pv_obj else ""
        prob_stmt = pv_obj.statement_markdown if pv_obj else ""

        test_case_dicts = [
            {
                "status": tr.status,
                "stderr": tr.failure_category,
                "actual_output": tr.actual_output_summary if tr.actual_output_summary else "",
                "expected_output": "",
                "passed": (tr.status == "passed"),
            }
            for tr in latest_eval.test_results
        ]

        concept_check_dicts = [
            {"concept": ce.concept_name, "passed": (ce.status == "passed"), "message": ce.explanation_code or ""}
            for ce in latest_eval.concept_evidence
        ]

        intelligent_fb = IntelligentExplainer.explain_run_failure(
            language=sub.language or "python",
            source_code=sub.source_code,
            status=eval_verdict,
            compile_output=latest_eval.failure_category if has_compile_err else None,
            case_results=test_case_dicts,
            concept_checks=concept_check_dicts,
            problem_title=prob_title,
            problem_statement=prob_stmt,
        )

        learning_hints = None
        if eval_verdict != "accepted":
            learning_hints = IntelligentExplainer.generate_progressive_hints(
                problem_title=prob_title,
                problem_statement=prob_stmt,
                expected_concepts=[ce.concept_name for ce in latest_eval.concept_evidence],
                status=eval_verdict,
                failure_category=intelligent_fb.get("category"),
            )

        return SubmissionResponse(
            id=sub.id,
            user_id=sub.user_id,
            problem_id=sub.problem_version_id,
            status=sub.status,
            verdict=eval_verdict,
            language=sub.language,
            created_at=sub.created_at,
            completed_at=sub.completed_at,
            total_score=total_score,
            syntax_valid=syntax_valid,
            summary_feedback=summary_feedback,
            criteria_scores=criteria_scores,
            concept_evidence=concept_evidences,
            test_case_results=test_results,
            actionable_suggestions=suggestions,
            intelligent_feedback=intelligent_fb,
            learning_hints=learning_hints,
        )

    return SubmissionResponse(
        id=sub.id,
        user_id=sub.user_id,
        problem_id=sub.problem_version_id,
        status=sub.status,
        verdict=sub.status,
        language=sub.language,
        created_at=sub.created_at,
        completed_at=sub.completed_at,
        total_score=total_score,
        syntax_valid=syntax_valid,
        summary_feedback=summary_feedback,
        criteria_scores=criteria_scores,
        concept_evidence=concept_evidences,
        test_case_results=test_results,
        actionable_suggestions=suggestions,
    )



@router.get("", response_model=List[SubmissionResponse])
async def list_user_submissions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    organization_id: Optional[str] = Query(None, description="Filter submissions within an organization (teachers/admins only)"),
    student_id: Optional[str] = Query(None, description="Filter by student ID within organization (teachers/admins only)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
):
    """
    Retrieve submission history.
    - Students retrieve their own submissions.
    - Teachers and Organization Admins can query submissions across their verified organization.
    """
    stmt = (
        select(Submission)
        .options(
            selectinload(Submission.evaluation_runs).selectinload(EvaluationRun.score_breakdowns),
        )
        .order_by(Submission.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    if organization_id:
        # Caller MUST be verified faculty in this organization
        await verify_organization_access(db, current_user.id, organization_id, allowed_roles=FACULTY_ROLES)
        stmt = stmt.where(Submission.organization_id == organization_id)
        if student_id:
            stmt = stmt.where(Submission.user_id == student_id)
    else:
        # Default: caller only views their own private submissions
        stmt = stmt.where(Submission.user_id == current_user.id)

    submissions = (await db.execute(stmt)).scalars().all()

    results = []
    for sub in submissions:
        latest_eval = sub.evaluation_runs[-1] if sub.evaluation_runs else None
        total_score = sum(s.awarded_points for s in latest_eval.score_breakdowns) if latest_eval else None
        results.append(
            SubmissionResponse(
                id=sub.id,
                user_id=sub.user_id,
                organization_id=sub.organization_id,
                problem_id=sub.problem_version_id,
                status=sub.status,
                language=sub.language,
                created_at=sub.created_at,
                completed_at=sub.completed_at,
                total_score=total_score,
                criteria_scores=[],
                concept_evidence=[],
                test_case_results=[],
                actionable_suggestions=[],
            )
        )
    return results

