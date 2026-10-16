"""
Celery Evaluation Tasks
Executes the EvaluationOrchestrator asynchronously in a dedicated worker process.
Guarantees idempotent execution, distinguishes student code outcomes from infrastructure
failures, and maintains reliable submission states.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from evaluation_specifications.models import RubricSchema
from app.db.session import AsyncSessionLocal
from app.evaluation.orchestrator import EvaluationOrchestrator
from app.models.problem import ProblemVersion
from app.models.submission import (
    ConceptEvidenceRecord,
    EvaluationRun,
    ScoreBreakdown,
    Submission,
    SubmissionFeedback,
    TestCaseResult,
)
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _execute_evaluation_async(submission_id: str) -> Dict[str, Any]:
    """
    Asynchronous implementation of submission evaluation.
    Operates on a fresh AsyncSessionLocal per invocation.
    """
    async with AsyncSessionLocal() as db:
        try:
            # 1. Fetch submission with existing evaluation runs to check idempotency
            stmt = (
                select(Submission)
                .where(Submission.id == submission_id)
                .options(
                    selectinload(Submission.evaluation_runs).selectinload(EvaluationRun.score_breakdowns),
                )
            )
            submission = (await db.execute(stmt)).scalars().first()

            if not submission:
                logger.error(f"Submission {submission_id} not found in database.")
                return {"status": "error", "error": "Submission not found", "submission_id": submission_id}

            # Idempotency check: If already completed with score breakdowns, do not duplicate
            if submission.status == "completed" and submission.evaluation_runs:
                completed_run = next((r for r in submission.evaluation_runs if r.status in ("completed", "failed")), None)
                if completed_run and completed_run.score_breakdowns:
                    logger.info(f"Submission {submission_id} already evaluated. Skipping duplicate execution.")
                    return {
                        "status": "already_completed",
                        "submission_id": submission_id,
                        "evaluation_run_id": completed_run.id,
                    }

            # Mark submission as running
            submission.status = "running"
            await db.commit()

            # 2. Fetch published problem version, active rubric, and test cases
            pv_stmt = (
                select(ProblemVersion)
                .where(ProblemVersion.id == submission.problem_version_id)
                .options(
                    selectinload(ProblemVersion.rubrics),
                    selectinload(ProblemVersion.test_cases),
                )
            )
            pv = (await db.execute(pv_stmt)).scalars().first()
            if not pv:
                logger.error(f"ProblemVersion {submission.problem_version_id} not found.")
                submission.status = "infrastructure_error"
                await db.commit()
                return {"status": "infrastructure_error", "error": "Problem version not found", "submission_id": submission_id}

            # Retrieve active rubric
            active_rubric = next((r for r in pv.rubrics if r.status in ("published", "approved")), None)
            if not active_rubric:
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
                except Exception as parse_err:
                    logger.warning(f"Failed to parse rubric JSON: {parse_err}. Using fallback rubric.")
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

            # Collect active test cases
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

            # 3. Execute Evaluation Orchestrator (Sandbox subprocess + Static AST analysis + Scoring)
            # Student syntax errors, timeouts, or wrong answers are handled deterministically inside orchestrator
            eval_result = EvaluationOrchestrator.evaluate_submission(
                submission_id=submission.id,
                source_code=submission.source_code,
                rubric=rubric_schema,
                test_cases=test_cases_dicts,
                language=submission.language or "python",
            )

            # 4. Clean up any prior incomplete evaluation runs on this submission to maintain clean state
            if submission.evaluation_runs:
                for old_run in list(submission.evaluation_runs):
                    if old_run.status == "running":
                        await db.delete(old_run)
                await db.flush()

            # 5. Persist durable EvaluationRun and detailed evidence
            eval_run = EvaluationRun(
                submission_id=submission.id,
                rubric_id=active_rubric.id if active_rubric else "default_rubric",
                evaluator_version=eval_result.evaluator_version,
                status=eval_result.status,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                failure_category=eval_result.syntax_error_details if not eval_result.syntax_valid else None,
            )
            db.add(eval_run)
            await db.flush()

            # Persist test case outcomes
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

            # Persist concept evidence records
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

            # Persist criteria score breakdowns
            for sc in eval_result.criteria_scores:
                sb = ScoreBreakdown(
                    evaluation_run_id=eval_run.id,
                    criterion=sc.criterion,
                    max_points=sc.max_points,
                    awarded_points=sc.awarded_points,
                    reason_code=sc.reason_code,
                )
                db.add(sb)

            # Persist structured feedback
            feedback = SubmissionFeedback(
                evaluation_run_id=eval_run.id,
                feedback_json=json.dumps({
                    "summary": eval_result.summary_feedback,
                    "suggestions": eval_result.actionable_suggestions,
                }),
            )
            db.add(feedback)

            # 6. Update submission to completed status
            submission.status = "completed"
            submission.completed_at = datetime.now(timezone.utc)
            await db.commit()

            return {
                "status": "completed",
                "submission_id": submission.id,
                "evaluation_run_id": eval_run.id,
                "total_score": eval_result.total_score,
                "syntax_valid": eval_result.syntax_valid,
            }

        except Exception as exc:
            await db.rollback()
            logger.error(f"Infrastructure error during evaluation of submission {submission_id}: {exc}", exc_info=True)
            raise exc


def _run_coro_sync(coro):
    """Run an async coroutine safely whether an event loop is already active or not."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


@celery_app.task(
    bind=True,
    name="app.tasks.evaluation.evaluate_submission_task",
    max_retries=3,
    default_retry_delay=5,
)
def evaluate_submission_task(self, submission_id: str) -> Dict[str, Any]:
    """
    Celery task wrapper for evaluating a student code submission.
    Retries only on unexpected infrastructure/database errors.
    Deterministic student syntax errors or test failures are NOT retried.
    """
    try:
        return _run_coro_sync(_execute_evaluation_async(submission_id))
    except Exception as exc:
        retries = getattr(self.request, "retries", 0)
        default_req = getattr(self, "_default_request", None)
        if retries == 0 and default_req and getattr(default_req, "retries", 0) > 0:
            retries = default_req.retries
        max_retries = getattr(self, "max_retries", 3)
        if retries < max_retries:
            countdown = 2 ** retries
            logger.warning(
                f"Infrastructure error evaluating submission {submission_id}. "
                f"Retrying (attempt {retries + 1}/{max_retries}) in {countdown}s..."
            )
            raise self.retry(exc=exc, countdown=countdown)

        # Retries exhausted: mark submission as infrastructure_error
        logger.error(
            f"All {max_retries} retries exhausted for submission {submission_id}. "
            f"Marking as infrastructure_error."
        )

        async def _mark_infrastructure_error():
            async with AsyncSessionLocal() as db:
                stmt = select(Submission).where(Submission.id == submission_id)
                sub = (await db.execute(stmt)).scalars().first()
                if sub:
                    sub.status = "infrastructure_error"
                    eval_run = EvaluationRun(
                        submission_id=sub.id,
                        rubric_id="infrastructure_error",
                        status="infrastructure_error",
                        failure_category=str(exc)[:64],
                        started_at=datetime.now(timezone.utc),
                        completed_at=datetime.now(timezone.utc),
                    )
                    db.add(eval_run)
                    await db.commit()

        try:
            _run_coro_sync(_mark_infrastructure_error())
        except Exception as mark_err:
            logger.critical(f"Failed to persist infrastructure_error status for submission {submission_id}: {mark_err}")

        return {
            "status": "infrastructure_error",
            "submission_id": submission_id,
            "error": str(exc),
        }
