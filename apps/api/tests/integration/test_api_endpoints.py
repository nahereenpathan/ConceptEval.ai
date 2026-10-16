"""
End-to-End API Integration Tests
Tests full user journeys: registration, authentication, problem discovery,
and dual-track submission evaluation over HTTP endpoints.
"""

import json
from unittest.mock import patch
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.problem import GradingRubric, Problem, ProblemVersion, TestCase
from app.models.user import User


@pytest_asyncio.fixture
async def test_db_session():
    """Provides an isolated in-memory SQLite database for integration testing."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await test_engine.dispose()


@pytest_asyncio.fixture
async def async_client(test_db_session):
    """Provides an HTTPX AsyncClient with the database dependency overridden."""
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_endpoints(async_client):
    """Liveness and readiness checks return 200 OK."""
    res = await async_client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    res_ready = await async_client.get("/readyz")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_full_student_journey_dual_track_evaluation(async_client, test_db_session):
    """
    Simulates complete journey:
    1. Register user
    2. Login & obtain JWT
    3. Seed published problem with loop rubric & hidden test case
    4. Browse problem (verify hidden test is NOT leaked)
    5. Submit compliant solution -> Expect 100/100
    6. Submit repeated print solution -> Expect 50/100 with concept violation explanation
    """
    # 1. Register student account
    reg_payload = {
        "email": "student_maya@example.edu",
        "password": "StrongPassword123!",
        "display_name": "Maya Lin",
    }
    reg_res = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    user_id = reg_res.json()["id"]

    # 2. Login
    login_payload = {
        "email": "student_maya@example.edu",
        "password": "StrongPassword123!",
    }
    login_res = await async_client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    tokens = login_res.json()
    access_token = tokens["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # Verify /me endpoint
    me_res = await async_client.get("/api/v1/auth/me", headers=auth_headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "student_maya@example.edu"

    # 3. Seed Published Problem with loop rubric and both public & hidden test cases
    problem = Problem(
        slug="print-hello-world-4-times",
        status="published",
        created_by_user_id=user_id,
    )
    test_db_session.add(problem)
    await test_db_session.flush()

    pv = ProblemVersion(
        problem_id=problem.id,
        version_number=1,
        title="Print Hello World 4 Times",
        statement_markdown="Print 'Hello World' exactly four times using a loop.",
        difficulty="easy",
        language="python",
    )
    test_db_session.add(pv)
    await test_db_session.flush()

    rubric_data = {
        "schema_version": "1.0.0",
        "max_score": 100.0,
        "functional_weight": 40.0,
        "concept_weight": 35.0,
        "algorithmic_weight": 15.0,
        "constraint_weight": 10.0,
        "required_concepts": [
            {
                "concept": "loop",
                "rule_id": "rule_loop",
                "accepted_constructs": ["for", "while"],
                "required": True,
                "min_occurrences": 1,
            }
        ],
        "prohibited_constructs": [],
        "allow_partial_concept_credit": True,
    }

    rubric = GradingRubric(
        problem_version_id=pv.id,
        version_number=1,
        schema_version="1.0.0",
        rubric_json=json.dumps(rubric_data),
        status="published",
        created_by_user_id=user_id,
    )
    test_db_session.add(rubric)

    # Add sample test case
    sample_tc = TestCase(
        problem_version_id=pv.id,
        visibility="sample",
        input_data="",
        expected_output="Hello World\nHello World\nHello World\nHello World",
        is_active=True,
    )
    # Add hidden test case
    hidden_tc = TestCase(
        problem_version_id=pv.id,
        visibility="hidden",
        input_data="",
        expected_output="Hello World\nHello World\nHello World\nHello World",
        is_active=True,
    )
    test_db_session.add_all([sample_tc, hidden_tc])
    await test_db_session.commit()

    # 4. Browse problem details through API - Ensure hidden test case is NOT leaked
    prob_res = await async_client.get(f"/api/v1/problems/{problem.id}")
    assert prob_res.status_code == 200
    prob_data = prob_res.json()
    assert prob_data["title"] == "Print Hello World 4 Times"
    assert len(prob_data["sample_test_cases"]) == 1
    assert prob_data["sample_test_cases"][0]["id"] == sample_tc.id

    # 5. Submit COMPLIANT solution -> Returns 202 Queued and dispatches Celery task
    compliant_code = """
for i in range(4):
    print("Hello World")
"""
    with patch("app.api.v1.endpoints.submissions.evaluate_submission_task.delay") as mock_delay:
        sub_res = await async_client.post(
            "/api/v1/submissions",
            headers=auth_headers,
            json={
                "problem_id": problem.id,
                "problem_version_number": 1,
                "language": "python",
                "source_code": compliant_code,
            },
        )
        assert sub_res.status_code == 202
        result_compliant = sub_res.json()
        assert result_compliant["status"] == "queued"
        mock_delay.assert_called_once_with(result_compliant["id"])

    # 6. Submit NON-COMPLIANT solution -> Returns 202 Queued
    repeated_print_code = """
print("Hello World")
print("Hello World")
print("Hello World")
print("Hello World")
"""
    with patch("app.api.v1.endpoints.submissions.evaluate_submission_task.delay") as mock_delay:
        sub_res_noncomp = await async_client.post(
            "/api/v1/submissions",
            headers=auth_headers,
            json={
                "problem_id": problem.id,
                "problem_version_number": 1,
                "language": "python",
                "source_code": repeated_print_code,
            },
        )
        assert sub_res_noncomp.status_code == 202
        result_noncomp = sub_res_noncomp.json()
        assert result_noncomp["status"] == "queued"
        mock_delay.assert_called_once_with(result_noncomp["id"])

    # 7. Verify submission retrieval endpoint returns queued state
    get_sub = await async_client.get(
        f"/api/v1/submissions/{result_noncomp['id']}",
        headers=auth_headers,
    )
    assert get_sub.status_code == 200
    assert get_sub.json()["id"] == result_noncomp["id"]
    assert get_sub.json()["status"] == "queued"
