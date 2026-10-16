"""
Unit & Integration Tests for Phase 2 (Run Code Runner) and Phase 5 (Teacher Authoring & RBAC)
"""

import pytest
import pytest_asyncio
import httpx
from datetime import datetime, timezone

from app.main import app
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.models.organization import Organization, OrganizationMembership
from app.models.problem import Problem, ProblemVersion, TestCase, GradingRubric


@pytest_asyncio.fixture
async def teacher_auth_header():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post('/api/v1/auth/login', json={'email': 'teacher@codeedu.org', 'password': 'TeacherPassword123!'})
        assert res.status_code == 200, f"Teacher login failed: {res.text}"
        token = res.json()['access_token']
        return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def student_auth_header():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post('/api/v1/auth/login', json={'email': 'student@codeedu.org', 'password': 'StudentPassword123!'})
        assert res.status_code == 200, f"Student login failed: {res.text}"
        token = res.json()['access_token']
        return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_run_code_against_sample_cases():
    """Verify that POST /problems/{id}/run executes code against sample test cases in sandbox."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Search for climbing stairs problem
        resp = await client.get("/api/v1/problems?search=climbing")
        assert resp.status_code == 200
        items = resp.json()
        if isinstance(items, dict) and "items" in items:
            items = items["items"]
        assert len(items) > 0
        prob = items[0]

        code = """import sys

def climb(n):
    if n <= 2:
        return n
    a, b = 1, 2
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b

for line in sys.stdin:
    line = line.strip()
    if line:
        print(climb(int(line)))
"""
        run_res = await client.post(f"/api/v1/problems/{prob['id']}/run", json={
            "source_code": code,
            "language": "python",
        })
        assert run_res.status_code == 200
        data = run_res.json()
        assert data["status"] == "accepted"
        assert data["all_passed"] is True
        assert len(data["case_results"]) >= 1
        assert data["syntax_valid"] is True
        assert any(c["concept"] == "loop" and c["passed"] for c in data["concept_checks"])


@pytest.mark.asyncio
async def test_run_code_custom_input():
    """Verify that POST /problems/{id}/run handles custom STDIN inputs without error."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/problems?search=climbing")
        prob = resp.json()["items"][0] if isinstance(resp.json(), dict) else resp.json()[0]

        code = """import sys
for line in sys.stdin:
    if line.strip():
        print(int(line.strip()) * 2)
"""
        run_res = await client.post(f"/api/v1/problems/{prob['id']}/run", json={
            "source_code": code,
            "language": "python",
            "custom_input": "21\n",
        })
        assert run_res.status_code == 200
        data = run_res.json()
        assert len(data["case_results"]) == 1
        assert data["case_results"][0]["actual_output"] == "42"


@pytest.mark.asyncio
async def test_student_cannot_author_or_publish_problems(student_auth_header):
    """Verify that RBAC prevents students from authoring or publishing problems (403 Forbidden)."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post("/api/v1/authoring/problems", json={
            "title": "Unauthorized Student Problem",
            "statement_markdown": "This should be strictly rejected",
            "test_cases": [{"input_data": "1", "expected_output": "1"}],
        }, headers=student_auth_header)
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_teacher_authoring_validation_and_publishing_lifecycle(teacher_auth_header):
    """Test full teacher lifecycle: create draft -> sandbox validate -> publish -> discover."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        problem_payload = {
            "title": "Authoring Test: Triple Array Elements",
            "statement_markdown": "Given space-separated integers, multiply each by 3 using a loop.",
            "difficulty": "easy",
            "language": "python",
            "topics": ["Loops & Iteration", "Arrays"],
            "constraints": ["1 <= len(arr) <= 100"],
            "input_format": "Space-separated integers.",
            "output_format": "Space-separated tripled integers.",
            "starter_code": "import sys\npass\n",
            "reference_solution": "import sys\nline = sys.stdin.read().strip()\nif line:\n    res = []\n    for x in line.split():\n        res.append(str(int(x) * 3))\n    print(' '.join(res))\n",
            "test_cases": [
                {
                    "input_data": "1 2 3\n",
                    "expected_output": "3 6 9",
                    "visibility": "sample",
                },
                {
                    "input_data": "10 20\n",
                    "expected_output": "30 60",
                    "visibility": "hidden",
                },
            ],
            "concept_rules": [
                {
                    "concept": "loop",
                    "required": True,
                    "min_occurrences": 1,
                    "description": "Requires a for or while loop",
                }
            ],
            "functional_weight": 60.0,
            "concept_weight": 40.0,
            "status": "draft",
        }

        prob_id = None
        try:
            # 1. Create problem draft
            create_res = await client.post(
                "/api/v1/authoring/problems",
                json=problem_payload,
                headers=teacher_auth_header,
            )
            assert create_res.status_code == 201
            created_prob = create_res.json()
            assert created_prob["status"] == "draft"
            prob_id = created_prob["id"]

            # 2. Validate reference solution in sandbox
            val_res = await client.post("/api/v1/authoring/validate", json={
                "source_code": problem_payload["reference_solution"],
                "language": "python",
                "test_cases": problem_payload["test_cases"],
                "concept_rules": problem_payload["concept_rules"],
            }, headers=teacher_auth_header)
            assert val_res.status_code == 200
            val_data = val_res.json()
            assert val_data["all_passed"] is True
            assert val_data["passed_tests"] == 2

            # 3. Publish problem
            pub_res = await client.post(
                f"/api/v1/authoring/problems/{prob_id}/publish",
                headers=teacher_auth_header,
            )
            assert pub_res.status_code == 200
            assert pub_res.json()["status"] == "published"

            # 4. Confirm student can discover in library
            lib_res = await client.get("/api/v1/problems?search=Triple Array Elements")
            assert lib_res.status_code == 200
            items = lib_res.json()
            if isinstance(items, dict) and "items" in items:
                items = items["items"]
            assert any(p["id"] == prob_id for p in items)
        finally:
            if prob_id:
                async with AsyncSessionLocal() as session:
                    prob = await session.get(Problem, prob_id)
                    if prob:
                        await session.delete(prob)
                        await session.commit()


@pytest.mark.asyncio
async def test_authoring_blocks_duplicate_problem(teacher_auth_header):
    """Verify that attempting to create a problem with duplicate title/fingerprint returns HTTP 409 Conflict."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Multiply Array Elements by Two is already a canonical problem in the library
        duplicate_payload = {
            "title": "Multiply Array Elements by Two",
            "statement_markdown": "Given space-separated integers, multiply each by 2 using a loop.",
            "difficulty": "easy",
            "language": "python",
            "topics": ["Loops & Iteration"],
            "test_cases": [{"input_data": "1 2\n", "expected_output": "2 4", "visibility": "sample"}],
            "concept_rules": [{"concept": "loop", "required": True}],
        }
        res = await client.post(
            "/api/v1/authoring/problems",
            json=duplicate_payload,
            headers=teacher_auth_header,
        )
        assert res.status_code == 409
        body = res.json()
        err = body.get("error") or body.get("detail")
        assert err["code"] == "DUPLICATE_PROBLEM"
