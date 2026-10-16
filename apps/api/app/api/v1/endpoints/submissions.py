"""
Submissions API Endpoints
Accepting student code submissions, orchestrating dual-track evaluation, and returning evidence-backed scores.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from evaluation_specifications.models import RubricSchema
from app.api.deps import get_current_user
from app.db.session import get_db
from app.evaluation.orchestrator import EvaluationOrchestrator
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

router = APIRouter(prefix="/submissions", tags=["Submissions"])


@router.post("", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
async def create_submission(
    req: SubmissionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Submit Python source code for dual-track evaluation (sandbox execution + AST concept compliance).
    """
    # 1. Fetch published problem version and associated rubric & test cases
    stmt = (
        select(ProblemVersion)
        .join(Problem, Problem.id == ProblemVersion.problem_id)
        .where(
            Problem.id == req.problem_id,
            ProblemVersion.version_number == req.problem_version_number,
            Problem.status == "published",
        )
        .options(
            selectinload(ProblemVersion.rubrics),
            selectinload(ProblemVersion.test_cases),
        )
    )
    pv = (await db.execute(stmt)).scalars().first()

    if not pv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROBLEM_VERSION_NOT_FOUND", "message": "Published problem version not found."},
        )

    # 2. Get active rubric
    active_rubric = next((r for r in pv.rubrics if r.status in ("published", "approved")), None)
    if not active_rubric:
        # Fallback to default rubric if none published
        rubric_schema = RubricSchema(
            schema_version="1.0.0",
            max_score=100.0,
            functional_weight=50.0,
            concept_weight=30.0,
            algorithmic_weight=10.0,
            constraint_weight=10.0,
            required_concepts=[],
            prohibited_constructs=[],
        )
    else:
        try:
            rubric_dict = json.loads(active_rubric.rubric_json)
            rubric_schema = RubricSchema.model_validate(rubric_dict)
        except Exception:
            rubric_schema = RubricSchema(
                schema_version="1.0.0",
                max_score=100.0,
                functional_weight=50.0,
                concept_weight=30.0,
                algorithmic_weight=10.0,
                constraint_weight=10.0,
                required_concepts=[],
                prohibited_constructs=[],
            )

    # 3. Collect active test cases
    test_cases_dicts = [
        {
            "id": tc.id,
            "visibility": tc.visibility,
            "input_data": tc.input_data,
            "expected_output": tc.expected_output,
            "timeout_ms": tc.timeout_ms,
        }
        for tc in pv.test_cases
        if tc.is_active
    ]

    # 4. Compute source code SHA256 hash
    source_hash = hashlib.sha256(req.source_code.encode("utf-8")).hexdigest()

    # 5. Create durable Submission record
    submission = Submission(
        user_id=current_user.id,
        problem_version_id=pv.id,
        language="python",
        source_code=req.source_code,
        source_hash=source_hash,
        status="running",
    )
    db.add(submission)
    await db.flush()

    # 6. Execute Evaluation Orchestration
    eval_result = EvaluationOrchestrator.evaluate_submission(
        submission_id=submission.id,
        source_code=req.source_code,
        rubric=rubric_schema,
        test_cases=test_cases_dicts,
    )

    # 7. Persist EvaluationRun and results
    eval_run = EvaluationRun(
        submission_id=submission.id,
        rubric_id=active_rubric.id if active_rubric else "default_rubric",
        evaluator_version=eval_result.evaluator_version,
        status=eval_result.status,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(eval_run)
    await db.flush()

    # Save test case outcomes
    for tc_res in eval_result.test_case_results:
        db_tc_res = TestCaseResult(
            evaluation_run_id=eval_run.id,
            test_case_id=tc_res.test_case_id,
            status=tc_res.status,
            execution_time_ms=tc_res.execution_time_ms,
            memory_used_bytes=tc_res.memory_used_bytes,
            actual_output_summary=tc_res.actual_output_summary,
            failure_category=tc_res.error_message,
        )
        db.add(db_tc_res)

    # Save concept evidences
    for ce in eval_result.concept_evidence:
        ce_rec = ConceptEvidenceRecord(
            evaluation_run_id=eval_run.id,
            concept_name=ce.concept.value,
            rule_id=ce.rule_id,
            status="passed" if ce.passed else "failed",
            evidence_json=json.dumps([loc.model_dump() for loc in ce.locations]),
            confidence=ce.confidence,
            explanation_code=ce.message,
        )
        db.add(ce_rec)

    # Save criteria score breakdowns
    for sc in eval_result.criteria_scores:
        sb = ScoreBreakdown(
            evaluation_run_id=eval_run.id,
            criterion=sc.criterion,
            max_points=sc.max_points,
            awarded_points=sc.awarded_points,
            reason_code=sc.reason_code,
        )
        db.add(sb)

    # Save feedback
    feedback = SubmissionFeedback(
        evaluation_run_id=eval_run.id,
        feedback_json=json.dumps({
            "summary": eval_result.summary_feedback,
            "suggestions": eval_result.actionable_suggestions,
        }),
    )
    db.add(feedback)

    # Update submission completion status
    submission.status = "completed"
    submission.completed_at = datetime.now(timezone.utc)
    await db.commit()

    return SubmissionResponse(
        id=submission.id,
        user_id=submission.user_id,
        problem_id=req.problem_id,
        status=submission.status,
        language=submission.language,
        created_at=submission.created_at,
        completed_at=submission.completed_at,
        total_score=eval_result.total_score,
        syntax_valid=eval_result.syntax_valid,
        summary_feedback=eval_result.summary_feedback,
        criteria_scores=[
            CriterionScoreResponse(
                criterion=c.criterion,
                max_points=c.max_points,
                awarded_points=c.awarded_points,
                passed=c.passed,
                reason_code=c.reason_code,
                explanation=c.explanation,
            )
            for c in eval_result.criteria_scores
        ],
        concept_evidence=[
            ConceptEvidenceResponse(
                concept=e.concept.value,
                rule_id=e.rule_id,
                passed=e.passed,
                occurrences_found=e.occurrences_found,
                message=e.message,
            )
            for e in eval_result.concept_evidence
        ],
        test_case_results=[
            TestCaseSummaryResponse(
                test_case_id=t.test_case_id,
                visibility=t.visibility,
                status=t.status,
                execution_time_ms=t.execution_time_ms,
                actual_output_summary=t.actual_output_summary,
                expected_output_summary=t.expected_output_summary,
                error_message=t.error_message,
            )
            for t in eval_result.test_case_results
        ],
        actionable_suggestions=eval_result.actionable_suggestions,
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

    # Verify authorization
    if sub.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCESS_DENIED", "message": "You are not authorized to view this submission."},
        )

    latest_eval = sub.evaluation_runs[-1] if sub.evaluation_runs else None
    criteria_scores = []
    concept_evidences = []
    test_results = []
    summary_feedback = None
    suggestions = []
    total_score = None

    if latest_eval:
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

    return SubmissionResponse(
        id=sub.id,
        user_id=sub.user_id,
        problem_id=sub.problem_version_id,
        status=sub.status,
        language=sub.language,
        created_at=sub.created_at,
        completed_at=sub.completed_at,
        total_score=total_score,
        syntax_valid=True,
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
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
):
    """Retrieve submission history for the authenticated user."""
    stmt = (
        select(Submission)
        .where(Submission.user_id == current_user.id)
        .options(
            selectinload(Submission.evaluation_runs).selectinload(EvaluationRun.score_breakdowns),
        )
        .order_by(Submission.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    submissions = (await db.execute(stmt)).scalars().all()

    results = []
    for sub in submissions:
        latest_eval = sub.evaluation_runs[-1] if sub.evaluation_runs else None
        total_score = sum(s.awarded_points for s in latest_eval.score_breakdowns) if latest_eval else None
        results.append(
            SubmissionResponse(
                id=sub.id,
                user_id=sub.user_id,
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
