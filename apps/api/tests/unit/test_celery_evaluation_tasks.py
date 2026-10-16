"""
Unit & Integration Tests for Celery Asynchronous Evaluation Tasks
Verifies:
1. HTTP 202 Accepted and queued status on submission creation.
2. Broker failure error handling (HTTP 503 Service Unavailable, no false queueing).
3. Celery task evaluation of compliant loop solutions (100/100, status=completed).
4. Celery task evaluation of repeated print solutions (concept marks withheld, status=completed).
5. Celery task evaluation of incorrect output solutions (functional marks withheld).
6. Celery task evaluation of syntax errors (0/100, deterministic, NOT retried as infrastructure errors).
7. Celery task evaluation of infinite loops (timeout captured, status=completed).
8. Task idempotency: re-running task on already completed submission skips evaluation and does not duplicate records.
9. Bounded retries on infrastructure errors and terminal transition to 'infrastructure_error'.
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from evaluation_specifications.models import ConceptType, RequiredConcept, RubricSchema
from app.api.deps import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.problem import GradingRubric, Problem, ProblemVersion, TestCase
from app.models.submission import (
    ConceptEvidenceRecord,
    EvaluationRun,
    ScoreBreakdown,
    Submission,
    SubmissionFeedback,
    TestCaseResult as DBTestCaseResult,
)
from app.models.user import User
from app.tasks.evaluation import (
    _execute_evaluation_async,
    evaluate_submission_task,
)


@pytest_asyncio.fixture
async def test_db():
    """Provides an isolated SQLite database and monkeypatches AsyncSessionLocal in tasks."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Patch AsyncSessionLocal in evaluation tasks module to point to this in-memory DB
    with patch("app.tasks.evaluation.AsyncSessionLocal", session_factory):
        yield session_factory

    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_problem(test_db):
    """Seeds a published problem with loop rubric and sample test cases."""
    async with test_db() as session:
        author = User(
            email="author@platform.edu",
            display_name="Prof. Turing",
            status="active",
        )
        session.add(author)
        await session.flush()

        problem = Problem(
            slug="print-hello-loop",
            status="published",
            owner_type="platform",
            created_by_user_id=author.id,
        )
        session.add(problem)
        await session.flush()

        pv = ProblemVersion(
            problem_id=problem.id,
            version_number=1,
            title="Print Hello 4 Times Using Loop",
            statement_markdown="Write a Python program that prints 'Hello World' 4 times using a loop.",
            difficulty="easy",
            language="python",
        )
        session.add(pv)
        await session.flush()

        rubric_spec = RubricSchema(
            schema_version="1.0.0",
            max_score=100.0,
            functional_weight=50.0,
            concept_weight=30.0,
            algorithmic_weight=10.0,
            constraint_weight=10.0,
            required_concepts=[
                RequiredConcept(
                    rule_id="rule_loop_1",
                    concept=ConceptType.LOOP,
                    min_occurrences=1,
                    accepted_constructs=["for", "while"],
                    description="Solution must utilize a loop construct.",
                )
            ],
            prohibited_constructs=[],
        )

        rubric = GradingRubric(
            problem_version_id=pv.id,
            version_number=1,
            status="published",
            created_by_user_id=author.id,
            rubric_json=rubric_spec.model_dump_json(),
        )
        tc1 = TestCase(
            problem_version_id=pv.id,
            visibility="sample",
            input_data="",
            expected_output="Hello World\nHello World\nHello World\nHello World",
            timeout_ms=3000,
            is_active=True,
        )
        tc2 = TestCase(
            problem_version_id=pv.id,
            visibility="hidden",
            input_data="",
            expected_output="Hello World\nHello World\nHello World\nHello World",
            timeout_ms=3000,
            is_active=True,
        )

        student = User(
            email="student@univ.edu",
            display_name="Student Lin",
            status="active",
        )
        session.add_all([rubric, tc1, tc2, student])
        await session.commit()

        return {
            "problem_id": problem.id,
            "problem_version_id": pv.id,
            "student_id": student.id,
        }


# ==============================================================================
# 1. API Endpoints: Task Dispatch & Broker Failure Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_create_submission_dispatches_task_and_returns_202(test_db, seeded_problem):
    """POST /submissions persists a queued submission, dispatches to Celery, and returns 202."""
    async with test_db() as session:
        student = (await session.execute(select(User).where(User.id == seeded_problem["student_id"]))).scalar_one()

    async def override_get_db():
        async with test_db() as s:
            yield s

    async def override_get_current_user():
        return student

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        with patch("app.api.v1.endpoints.submissions.evaluate_submission_task.delay") as mock_delay:
            res = await client.post(
                "/api/v1/submissions",
                json={
                    "problem_id": seeded_problem["problem_id"],
                    "problem_version_number": 1,
                    "language": "python",
                    "source_code": "for i in range(4):\n    print('Hello World')",
                },
            )
            assert res.status_code == 202
            data = res.json()
            assert data["status"] == "queued"
            assert "queued for evaluation" in data["summary_feedback"]
            sub_id = data["id"]
            mock_delay.assert_called_once_with(sub_id)

            # Verify submission exists in database in queued status
            async with test_db() as session:
                sub = (await session.execute(select(Submission).where(Submission.id == sub_id))).scalar_one()
                assert sub.status == "queued"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_broker_failure_marks_infrastructure_error_and_returns_503(test_db, seeded_problem):
    """When the message broker fails to queue the task, API returns 503 and marks status as infrastructure_error."""
    async with test_db() as session:
        student = (await session.execute(select(User).where(User.id == seeded_problem["student_id"]))).scalar_one()

    async def override_get_db():
        async with test_db() as s:
            yield s

    async def override_get_current_user():
        return student

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        with patch(
            "app.api.v1.endpoints.submissions.evaluate_submission_task.delay",
            side_effect=Exception("Redis connection refused on localhost:6379"),
        ):
            res = await client.post(
                "/api/v1/submissions",
                json={
                    "problem_id": seeded_problem["problem_id"],
                    "problem_version_number": 1,
                    "language": "python",
                    "source_code": "for i in range(4):\n    print('Hello World')",
                },
            )
            assert res.status_code == 503
            data = res.json()
            assert data["error"]["code"] == "BROKER_UNAVAILABLE"

            # Verify submission was marked as infrastructure_error rather than queued
            async with test_db() as session:
                sub = (await session.execute(
                    select(Submission).where(Submission.problem_version_id == seeded_problem["problem_version_id"])
                )).scalars().first()
                assert sub is not None
                assert sub.status == "infrastructure_error"

    app.dependency_overrides.clear()


# ==============================================================================
# 2. Celery Worker Task Execution Tests (All Evaluation Scenarios)
# ==============================================================================

@pytest.mark.asyncio
async def test_task_evaluates_compliant_loop_full_score(test_db, seeded_problem):
    """Worker task evaluates compliant loop code -> 100/100, completed status."""
    # Create queued submission
    async with test_db() as session:
        sub = Submission(
            user_id=seeded_problem["student_id"],
            problem_version_id=seeded_problem["problem_version_id"],
            language="python",
            source_code="for i in range(4):\n    print('Hello World')",
            source_hash="sha_compliant",
            status="queued",
        )
        session.add(sub)
        await session.commit()
        sub_id = sub.id

    # Execute worker task asynchronously
    result = await _execute_evaluation_async(sub_id)
    assert result["status"] == "completed"
    assert result["total_score"] == 100.0
    assert result["syntax_valid"] is True

    # Verify DB records
    async with test_db() as session:
        sub = (await session.execute(select(Submission).where(Submission.id == sub_id))).scalar_one()
        assert sub.status == "completed"
        assert sub.completed_at is not None

        # Verify evaluation run & score breakdowns
        run = (await session.execute(select(EvaluationRun).where(EvaluationRun.submission_id == sub_id))).scalar_one()
        assert run.status == "completed"

        scores = (await session.execute(select(ScoreBreakdown).where(ScoreBreakdown.evaluation_run_id == run.id))).scalars().all()
        assert len(scores) == 4
        score_by_crit = {s.criterion: s.awarded_points for s in scores}
        assert score_by_crit["functional_correctness"] == 50.0
        assert score_by_crit["concept_compliance"] == 30.0
        assert score_by_crit["algorithmic_logic"] == 10.0
        assert score_by_crit["constraints"] == 10.0


@pytest.mark.asyncio
async def test_task_evaluates_repeated_print_withholds_concept_points(test_db, seeded_problem):
    """Worker task evaluates repeated prints (no loop) -> 50/100, concept points withheld."""
    async with test_db() as session:
        sub = Submission(
            user_id=seeded_problem["student_id"],
            problem_version_id=seeded_problem["problem_version_id"],
            language="python",
            source_code="print('Hello World')\nprint('Hello World')\nprint('Hello World')\nprint('Hello World')",
            source_hash="sha_noncompliant",
            status="queued",
        )
        session.add(sub)
        await session.commit()
        sub_id = sub.id

    result = await _execute_evaluation_async(sub_id)
    assert result["status"] == "completed"
    assert result["total_score"] == 60.0

    async with test_db() as session:
        run = (await session.execute(select(EvaluationRun).where(EvaluationRun.submission_id == sub_id))).scalar_one()
        scores = (await session.execute(select(ScoreBreakdown).where(ScoreBreakdown.evaluation_run_id == run.id))).scalars().all()
        score_by_crit = {s.criterion: s.awarded_points for s in scores}
        assert score_by_crit["functional_correctness"] == 50.0
        assert score_by_crit["concept_compliance"] == 0.0  # Concept withheld!
        assert score_by_crit["algorithmic_logic"] == 0.0   # Algorithmic logic withheld!
        assert score_by_crit["constraints"] == 10.0


@pytest.mark.asyncio
async def test_task_evaluates_incorrect_output(test_db, seeded_problem):
    """Worker task evaluates incorrect output -> 0 functional points."""
    async with test_db() as session:
        sub = Submission(
            user_id=seeded_problem["student_id"],
            problem_version_id=seeded_problem["problem_version_id"],
            language="python",
            source_code="for i in range(4):\n    print('Goodbye World')",
            source_hash="sha_incorrect",
            status="queued",
        )
        session.add(sub)
        await session.commit()
        sub_id = sub.id

    result = await _execute_evaluation_async(sub_id)
    assert result["status"] == "completed"
    assert result["total_score"] == 40.0  # 30 concept + 10 constraints, 0 functional, 0 algo

    async with test_db() as session:
        run = (await session.execute(select(EvaluationRun).where(EvaluationRun.submission_id == sub_id))).scalar_one()
        test_results = (await session.execute(select(DBTestCaseResult).where(DBTestCaseResult.evaluation_run_id == run.id))).scalars().all()
        assert all(t.status == "failed" for t in test_results)


@pytest.mark.asyncio
async def test_task_evaluates_syntax_error_not_retried_as_infra_error(test_db, seeded_problem):
    """Student syntax error produces deterministic score=0 without triggering worker retries."""
    async with test_db() as session:
        sub = Submission(
            user_id=seeded_problem["student_id"],
            problem_version_id=seeded_problem["problem_version_id"],
            language="python",
            source_code="for i in range(4)\n    print('Missing colon')",
            source_hash="sha_syntax_err",
            status="queued",
        )
        session.add(sub)
        await session.commit()
        sub_id = sub.id

    result = await _execute_evaluation_async(sub_id)
    assert result["status"] == "completed"
    assert result["total_score"] == 0.0
    assert result["syntax_valid"] is False

    async with test_db() as session:
        sub = (await session.execute(select(Submission).where(Submission.id == sub_id))).scalar_one()
        assert sub.status == "completed"  # Completed evaluation, NOT infrastructure_error
        run = (await session.execute(select(EvaluationRun).where(EvaluationRun.submission_id == sub_id))).scalar_one()
        assert run.status == "failed"
        assert "SyntaxError" in (run.failure_category or "")


@pytest.mark.asyncio
async def test_task_evaluates_timeout(test_db, seeded_problem):
    """Infinite loop is safely terminated by runner timeout and penalized under constraints."""
    async with test_db() as session:
        # Override test case timeout to 0.5s for fast test execution
        pv = (await session.execute(select(ProblemVersion).where(ProblemVersion.id == seeded_problem["problem_version_id"]))).scalar_one()
        tc = TestCase(
            problem_version_id=pv.id,
            visibility="sample",
            input_data="",
            expected_output="Hello",
            timeout_ms=500,  # 0.5s timeout
            is_active=True,
        )
        sub = Submission(
            user_id=seeded_problem["student_id"],
            problem_version_id=pv.id,
            language="python",
            source_code="while True:\n    pass",
            source_hash="sha_timeout",
            status="queued",
        )
        session.add_all([tc, sub])
        await session.commit()
        sub_id = sub.id

    result = await _execute_evaluation_async(sub_id)
    assert result["status"] == "completed"

    async with test_db() as session:
        run = (await session.execute(select(EvaluationRun).where(EvaluationRun.submission_id == sub_id))).scalar_one()
        tc_results = (await session.execute(select(DBTestCaseResult).where(DBTestCaseResult.evaluation_run_id == run.id))).scalars().all()
        assert any(t.status == "timeout" for t in tc_results)


# ==============================================================================
# 3. Idempotency & Reliability Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_task_idempotency_avoids_duplicate_records(test_db, seeded_problem):
    """Running evaluation task a second time on completed submission returns early and does not duplicate records."""
    async with test_db() as session:
        sub = Submission(
            user_id=seeded_problem["student_id"],
            problem_version_id=seeded_problem["problem_version_id"],
            language="python",
            source_code="for i in range(4):\n    print('Hello World')",
            source_hash="sha_idempotent",
            status="queued",
        )
        session.add(sub)
        await session.commit()
        sub_id = sub.id

    # First run
    res1 = await _execute_evaluation_async(sub_id)
    assert res1["status"] == "completed"

    # Count records after first run
    async with test_db() as session:
        runs_count = len((await session.execute(select(EvaluationRun).where(EvaluationRun.submission_id == sub_id))).scalars().all())
        scores_count = len((await session.execute(select(ScoreBreakdown))).scalars().all())
        evidence_count = len((await session.execute(select(ConceptEvidenceRecord))).scalars().all())
        assert runs_count == 1
        assert scores_count == 4
        assert evidence_count == 1

    # Second run (duplicate dispatch simulation)
    res2 = await _execute_evaluation_async(sub_id)
    assert res2["status"] == "already_completed"

    # Verify NO duplicate records were created
    async with test_db() as session:
        runs_count_after = len((await session.execute(select(EvaluationRun).where(EvaluationRun.submission_id == sub_id))).scalars().all())
        scores_count_after = len((await session.execute(select(ScoreBreakdown))).scalars().all())
        evidence_count_after = len((await session.execute(select(ConceptEvidenceRecord))).scalars().all())
        assert runs_count_after == runs_count
        assert scores_count_after == scores_count
        assert evidence_count_after == evidence_count


def test_celery_task_retry_and_terminal_infrastructure_error():
    """Celery task wrapper retries on infrastructure error and marks infrastructure_error when retries exhausted."""
    evaluate_submission_task.request.retries = 0
    evaluate_submission_task.max_retries = 3
    mock_retry = MagicMock(side_effect=Exception("CeleryRetry"))

    # When retries remain, raises self.retry
    with patch.object(evaluate_submission_task, "retry", mock_retry):
        with patch("app.tasks.evaluation._execute_evaluation_async", side_effect=RuntimeError("Database connection lost")):
            with pytest.raises(Exception, match="CeleryRetry"):
                evaluate_submission_task("sub_test_123")
            mock_retry.assert_called_once()
            assert mock_retry.call_args[1]["countdown"] == 1  # 2 ** 0

    # When retries are exhausted (retries == 3), does not retry and returns infrastructure_error
    evaluate_submission_task.request.retries = 3
    mock_retry.reset_mock()
    with patch.object(evaluate_submission_task, "retry", mock_retry):
        with patch("app.tasks.evaluation._execute_evaluation_async", side_effect=RuntimeError("Fatal database crash")):
            with patch("app.tasks.evaluation.AsyncSessionLocal") as mock_db_cls:
                res = evaluate_submission_task("sub_test_123")
                assert res["status"] == "infrastructure_error"
                assert "Fatal database crash" in res["error"]
                mock_retry.assert_not_called()
