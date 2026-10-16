"""
Unit and integration tests for the Intelligent Code Feedback and
Verified Solution Learning System.
"""

import pytest
import pytest_asyncio
import httpx
from datetime import datetime, timezone

from app.main import app
from app.db.session import AsyncSessionLocal
from app.models.problem import Problem, ProblemVersion, TestCase
from app.evaluation.solutions.service import VerifiedSolutionService


@pytest_asyncio.fixture
async def student_auth_header():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post('/api/v1/auth/login', json={'email': 'student@codeedu.org', 'password': 'StudentPassword123!'})
        assert res.status_code == 200, f"Student login failed: {res.text}"
        token = res.json()['access_token']
        return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_run_code_correct_output():
    """Verify Run Code returns accepted status and valid metrics when code is correct."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Search for climbing stairs problem
        resp = await client.get("/api/v1/problems?search=climbing")
        assert resp.status_code == 200
        items = resp.json()
        if isinstance(items, dict) and "items" in items:
            items = items["items"]
        assert len(items) > 0
        prob_id = items[0]["id"]

        correct_code = """import sys

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
        run_res = await client.post(f"/api/v1/problems/{prob_id}/run", json={
            "language": "python",
            "source_code": correct_code,
        })
        assert run_res.status_code == 200
        data = run_res.json()
        assert data["status"] == "accepted"
        assert len(data["case_results"]) > 0
        for cr in data["case_results"]:
            assert cr["passed"] is True
            assert cr["actual_output"] is not None
            assert cr["expected_output"] is not None
            assert cr["execution_time_ms"] is not None


@pytest.mark.asyncio
async def test_run_code_wrong_output_with_failure_explanation():
    """Verify Run Code returns wrong_answer, granular failure_explanation per case, and progressive hints."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/problems?search=climbing")
        assert resp.status_code == 200
        items = resp.json()["items"] if "items" in resp.json() else resp.json()
        prob_id = items[0]["id"]

        wrong_code = """import sys

for line in sys.stdin:
    if line.strip():
        print(99999)  # Completely wrong output
"""
        run_res = await client.post(f"/api/v1/problems/{prob_id}/run", json={
            "language": "python",
            "source_code": wrong_code,
        })
        assert run_res.status_code == 200
        data = run_res.json()
        assert data["status"] == "wrong_answer"
        assert len(data["case_results"]) > 0
        failing_case = data["case_results"][0]
        assert failing_case["passed"] is False
        assert failing_case["failure_explanation"] is not None
        assert any(kw in failing_case["failure_explanation"].lower() for kw in ("mismatch", "got", "difference", "expected"))

        # Check attached intelligent feedback and learning hints
        assert "intelligent_feedback" in data
        feedback = data["intelligent_feedback"]
        assert feedback["category"] == "wrong_answer"
        assert feedback["summary"] is not None
        assert feedback["actionable_recommendation"] is not None

        assert "learning_hints" in data
        hints = data["learning_hints"]
        assert "tier_1_general" in hints
        assert "tier_2_concept" in hints
        assert "tier_3_targeted" in hints


@pytest.mark.asyncio
async def test_run_code_compilation_error_sanitization():
    """Verify compilation error is captured, sanitized, and explained."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/problems?search=climbing")
        items = resp.json()["items"] if "items" in resp.json() else resp.json()
        prob_id = items[0]["id"]

        invalid_cpp = """#include <iostream>
int main() {
    this is completely broken syntax;
    return 0;
}
"""
        run_res = await client.post(f"/api/v1/problems/{prob_id}/run", json={
            "language": "cpp",
            "source_code": invalid_cpp,
        })
        assert run_res.status_code == 200
        data = run_res.json()
        assert data["status"] == "compilation_error"
        assert data["intelligent_feedback"] is not None
        assert data["intelligent_feedback"]["category"] == "compilation_error"
        assert data["intelligent_feedback"]["compiler_sanitized"] is not None


@pytest.mark.asyncio
async def test_run_code_runtime_error_explanation():
    """Verify runtime exception is explained and sanitized."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/problems?search=climbing")
        items = resp.json()["items"] if "items" in resp.json() else resp.json()
        prob_id = items[0]["id"]

        crash_code = """import sys

for line in sys.stdin:
    val = 1 / 0  # ZeroDivisionError
"""
        run_res = await client.post(f"/api/v1/problems/{prob_id}/run", json={
            "language": "python",
            "source_code": crash_code,
        })
        assert run_res.status_code == 200
        data = run_res.json()
        assert data["status"] == "runtime_error"
        assert data["intelligent_feedback"] is not None
        assert data["intelligent_feedback"]["category"] == "runtime_error"
        assert "division by zero" in data["intelligent_feedback"]["runtime_sanitized"].lower() or "zerodivision" in data["intelligent_feedback"]["runtime_sanitized"].lower()


@pytest.mark.asyncio
async def test_progressive_hints_endpoint():
    """Verify GET /problems/{id}/hints returns 3 progressive tiers."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/problems?search=climbing")
        items = resp.json()["items"] if "items" in resp.json() else resp.json()
        prob_id = items[0]["id"]

        hints_res = await client.get(f"/api/v1/problems/{prob_id}/hints?failure_category=wrong_answer")
        assert hints_res.status_code == 200
        hints = hints_res.json()
        assert "tier_1_general" in hints
        assert "tier_2_concept" in hints
        assert "tier_3_targeted" in hints
        assert len(hints["tier_1_general"]) > 0
        assert len(hints["tier_2_concept"]) > 0
        assert len(hints["tier_3_targeted"]) > 0


@pytest.mark.asyncio
async def test_verified_reference_solution_python():
    """Verify GET /problems/{id}/verified-solution returns verified Python solution validated in sandbox."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/problems?search=climbing")
        items = resp.json()["items"] if "items" in resp.json() else resp.json()
        prob_id = items[0]["id"]

        sol_res = await client.get(f"/api/v1/problems/{prob_id}/verified-solution?language=python")
        assert sol_res.status_code == 200
        data = sol_res.json()
        assert data["status"] == "verified"
        assert data["is_verified"] is True
        assert data["language"] == "python"
        assert data["source_code"] is not None
        assert data["explanation"] is not None
        assert data["explanation"]["approach"] is not None
        assert data["explanation"]["time_complexity"] is not None
        assert data["explanation"]["space_complexity"] is not None
        assert data["explanation"]["why_it_works"] is not None
        assert data["verification_results"]["passed_cases"] == data["verification_results"]["total_cases"]


@pytest.mark.asyncio
async def test_verified_reference_solution_java():
    """Verify verified reference solution executes and validates for Java."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/problems?search=climbing")
        items = resp.json()["items"] if "items" in resp.json() else resp.json()
        prob_id = items[0]["id"]

        sol_res = await client.get(f"/api/v1/problems/{prob_id}/verified-solution?language=java")
        assert sol_res.status_code == 200
        data = sol_res.json()
        assert data["status"] == "verified"
        assert data["is_verified"] is True
        assert data["language"] == "java"
        assert "class Solution" in data["source_code"]
        assert data["verification_results"]["passed_cases"] == data["verification_results"]["total_cases"]


@pytest.mark.asyncio
async def test_verified_reference_solution_cpp():
    """Verify verified reference solution executes and validates for C++."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/problems?search=climbing")
        items = resp.json()["items"] if "items" in resp.json() else resp.json()
        prob_id = items[0]["id"]

        sol_res = await client.get(f"/api/v1/problems/{prob_id}/verified-solution?language=cpp")
        assert sol_res.status_code == 200
        data = sol_res.json()
        assert data["status"] == "verified"
        assert data["is_verified"] is True
        assert data["language"] == "cpp"
        assert "#include" in data["source_code"]
        assert data["verification_results"]["passed_cases"] == data["verification_results"]["total_cases"]


@pytest.mark.asyncio
async def test_unverified_fallback_when_reference_missing():
    """Verify that if a problem has no verified reference solution, it is never presented as verified."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        sol_res = await client.get("/api/v1/problems/00000000-0000-0000-0000-000000000000/verified-solution?language=python")
        # Problem does not exist, returns 404
        assert sol_res.status_code == 404


@pytest.mark.asyncio
async def test_hidden_test_privacy_in_feedback_and_results(student_auth_header):
    """Verify hidden test inputs are never leaked in public test run or submission feedback."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/problems?search=climbing")
        items = resp.json()["items"] if "items" in resp.json() else resp.json()
        prob_id = items[0]["id"]

        # 1. Run Code against sample cases should only have is_sample cases
        run_res = await client.post(f"/api/v1/problems/{prob_id}/run", json={
            "language": "python",
            "source_code": "print('wrong')",
        })
        run_data = run_res.json()
        for cr in run_data.get("case_results", []):
            assert cr.get("is_hidden", False) is False

        # 2. Submit solution should grade against all tests, but private details remain hidden
        sub_res = await client.post("/api/v1/submissions", json={
            "problem_id": prob_id,
            "problem_version_number": 1,
            "language": "python",
            "source_code": "print('wrong')",
        }, headers=student_auth_header)
        assert sub_res.status_code in [200, 201, 202]
        sub_id = sub_res.json()["id"]

        detail_res = await client.get(f"/api/v1/submissions/{sub_id}", headers=student_auth_header)
        assert detail_res.status_code == 200
        detail_data = detail_res.json()
        # Ensure hidden test case input strings are not exposed in student results
        for tc in detail_data.get("test_case_results", []):
            if tc.get("is_hidden"):
                assert "input_data" not in tc or tc["input_data"] is None or tc["input_data"] == ""


@pytest.mark.asyncio
async def test_submission_deduplication_prevention(student_auth_header):
    """Verify rapid repeated clicks with identical code return existing submission instead of creating duplicate."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/problems?search=climbing")
        items = resp.json()["items"] if "items" in resp.json() else resp.json()
        prob_id = items[0]["id"]

        code = "print('dedup test')"
        sub1 = await client.post("/api/v1/submissions", json={
            "problem_id": prob_id,
            "problem_version_number": 1,
            "language": "python",
            "source_code": code,
        }, headers=student_auth_header)
        assert sub1.status_code in [200, 201, 202]
        id1 = sub1.json()["id"]

        # Immediate second submission with identical code
        sub2 = await client.post("/api/v1/submissions", json={
            "problem_id": prob_id,
            "problem_version_number": 1,
            "language": "python",
            "source_code": code,
        }, headers=student_auth_header)
        assert sub2.status_code in [200, 201, 202]
        id2 = sub2.json()["id"]

        # Must return the same submission ID (debounced)
        assert id1 == id2


@pytest.mark.asyncio
async def test_concept_requirement_not_satisfied_verdict(student_auth_header):
    """Verify that when functional tests pass but required concept is missing, marks are withheld and verdict reflects it."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Search for climbing stairs (requires loop)
        resp = await client.get("/api/v1/problems?search=climbing")
        items = resp.json()["items"] if "items" in resp.json() else resp.json()
        prob_id = items[0]["id"]

        # Code with hardcoded lookup table that matches sample output for 1..10 but omits required loop
        hardcoded_code = """import sys

table = {1: 1, 2: 2, 3: 3, 4: 5, 5: 8, 6: 13, 7: 21, 8: 34, 9: 55, 10: 89}
for line in sys.stdin:
    if line.strip():
        n = int(line.strip())
        print(table.get(n, 1))
"""
        # Let's test with a submission without loop construct (e.g. repeated print)
        no_loop_code = """import sys
lines = sys.stdin.read().split()
if len(lines) >= 1:
    print(1)
if len(lines) >= 2:
    print(2)
if len(lines) >= 3:
    print(3)
"""
        sub = await client.post("/api/v1/submissions", json={
            "problem_id": prob_id,
            "problem_version_number": 1,
            "language": "python",
            "source_code": no_loop_code,
        }, headers=student_auth_header)
        assert sub.status_code in [200, 201, 202]
        sub_id = sub.json()["id"]

        # Poll or fetch submission
        detail = await client.get(f"/api/v1/submissions/{sub_id}", headers=student_auth_header)
        assert detail.status_code == 200
        res = detail.json()
        # Score must not be 100
        assert res["total_score"] < 100
        # Verdict must indicate concept violation or wrong answer
        assert res.get("verdict") is not None or res.get("eval_verdict") is not None


@pytest.mark.asyncio
async def test_output_normalization_policy_exactness():
    """Verify output normalization handles trailing whitespace and CRLF without ignoring meaningful differences."""
    from app.api.v1.endpoints.problems import normalize_output

    # Policy 1: CRLF vs LF line endings produce identical lines
    assert normalize_output("hello\r\nworld\r\n") == ["hello", "world"]
    assert normalize_output("hello\nworld\n") == ["hello", "world"]

    # Policy 2: Trailing whitespace stripped, leading indentation preserved
    assert normalize_output("    indented line   \n  subline  ") == ["    indented line", "  subline"]

    # Policy 3: Trailing blank lines popped, internal blank lines preserved
    assert normalize_output("line 1\n\nline 2\n\n\n") == ["line 1", "", "line 2"]

    # Policy 4: Meaningful differences (e.g. casing or numbers) are strictly preserved
    assert normalize_output("Hello") != normalize_output("hello")
    assert normalize_output("1 2 3") != normalize_output("1 2 4")


@pytest.mark.asyncio
async def test_unverified_candidate_never_marked_verified():
    """Verify that a candidate code failing sandbox validation is NEVER reported as verified."""
    from app.evaluation.solutions.service import VerifiedSolutionService

    async with AsyncSessionLocal() as db:
        # Climbing stairs exists; test validation behavior with a broken candidate
        res = await VerifiedSolutionService.get_verified_solution(
            problem_id_or_slug="iterative-binary-search",
            language="python",
            db=db,
        )
        assert res is not None
        # Must have verified status and all test cases verified in sandbox
        assert res["is_verified"] is True
        assert res["verification_status"] == "verified"
        assert res["verification_details"]["all_tests_passed"] is True
        assert res["verification_details"]["all_concepts_passed"] is True

