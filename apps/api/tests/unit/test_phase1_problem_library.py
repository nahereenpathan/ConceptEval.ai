"""
Phase 1 Problem Library Automated Tests
Validates:
1. Rich multi-faceted problem listing, search, topic and difficulty filtering, and pagination.
2. Problem detail retrieval with expected concepts and strict privacy of hidden test cases.
3. Interactive student bookmarking toggle and personal bookmark lists.
4. Dynamic student progress calculation (not_started, attempted, solved).
5. Student submission history retrieval with AST concept violation reporting.
6. Extensible authorized content import pipeline with schema validation, provenance tracking,
   and duplicate slug detection.
"""

import json
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.content_import.pipeline import import_problem_dataset
from app.core.security import create_access_token, get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.problem import (
    GradingRubric,
    Problem,
    ProblemBookmark,
    ProblemTopic,
    ProblemTopicAssignment,
    ProblemVersion,
    TestCase,
)
from app.models.submission import (
    ConceptEvidenceRecord,
    EvaluationRun,
    ScoreBreakdown,
    Submission,
)
from app.models.user import User
from app.schemas.problem import ContentImportItem, ContentImportRequest, ContentImportTestCase


@pytest_asyncio.fixture
async def db_session():
    """In-memory isolated SQLite database for Phase 1 tests."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await test_engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """FastAPI async test client with database override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()


def auth_header(user: User) -> dict:
    token = create_access_token(subject=user.id, extra_claims={"type": "access"})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def library_fixture(db_session):
    """Seed users, topics, problems, rubrics, and test cases."""
    now = datetime.now(timezone.utc)

    # 1. Users
    teacher = User(
        email="prof.ada@university.edu",
        password_hash=get_password_hash("Secret123!"),
        display_name="Prof. Ada Lovelace",
        status="active",
    )
    student = User(
        email="student.grace@university.edu",
        password_hash=get_password_hash("Secret123!"),
        display_name="Grace Hopper",
        status="active",
    )
    db_session.add_all([teacher, student])
    await db_session.flush()

    # 2. Topics
    t_loops = ProblemTopic(name="Loops & Iteration", slug="loops")
    t_recursion = ProblemTopic(name="Recursion", slug="recursion")
    t_arrays = ProblemTopic(name="Arrays", slug="arrays")
    db_session.add_all([t_loops, t_recursion, t_arrays])
    await db_session.flush()

    # 3. Problems
    # Problem 1: Loop problem (Easy)
    p1 = Problem(owner_type="platform", slug="print-hello-loop", status="published", created_by_user_id=teacher.id)
    db_session.add(p1)
    await db_session.flush()

    pv1 = ProblemVersion(
        problem_id=p1.id,
        version_number=1,
        title="Print Hello World Using a Loop",
        statement_markdown="Print Hello World exactly four times using a for or while loop.",
        difficulty="easy",
        language="python",
        published_at=now,
    )
    db_session.add(pv1)
    await db_session.flush()

    # Assign topic to p1
    db_session.add(ProblemTopicAssignment(problem_version_id=pv1.id, topic_id=t_loops.id))

    # Add Rubric with expected concepts
    r1_json = {
        "required_concepts": [{"concept": "loop", "required": True}],
        "functional_weight": 60.0,
        "concept_weight": 40.0,
    }
    db_session.add(GradingRubric(
        problem_version_id=pv1.id,
        version_number=1,
        rubric_json=json.dumps(r1_json),
        status="published",
        created_by_user_id=teacher.id,
    ))

    # Test cases: 1 sample, 1 hidden
    tc1_sample = TestCase(
        problem_version_id=pv1.id,
        visibility="sample",
        input_data="",
        expected_output="Hello World\nHello World\nHello World\nHello World\n",
    )
    tc1_hidden = TestCase(
        problem_version_id=pv1.id,
        visibility="hidden",
        input_data="",
        expected_output="Hello World\nHello World\nHello World\nHello World\n",
    )
    db_session.add_all([tc1_sample, tc1_hidden])

    # Problem 2: Recursion problem (Medium)
    p2 = Problem(owner_type="platform", slug="factorial-recursion", status="published", created_by_user_id=teacher.id)
    db_session.add(p2)
    await db_session.flush()

    pv2 = ProblemVersion(
        problem_id=p2.id,
        version_number=1,
        title="Recursive Factorial Calculator",
        statement_markdown="Compute factorial of N using direct recursion.",
        difficulty="medium",
        language="python",
        published_at=now,
    )
    db_session.add(pv2)
    await db_session.flush()

    db_session.add(ProblemTopicAssignment(problem_version_id=pv2.id, topic_id=t_recursion.id))

    r2_json = {
        "required_concepts": [{"concept": "recursion", "required": True}],
        "functional_weight": 50.0,
        "concept_weight": 50.0,
    }
    db_session.add(GradingRubric(
        problem_version_id=pv2.id,
        version_number=1,
        rubric_json=json.dumps(r2_json),
        status="published",
        created_by_user_id=teacher.id,
    ))

    # Problem 3: Arrays problem (Hard)
    p3 = Problem(owner_type="platform", slug="array-max-subarray", status="published", created_by_user_id=teacher.id)
    db_session.add(p3)
    await db_session.flush()

    pv3 = ProblemVersion(
        problem_id=p3.id,
        version_number=1,
        title="Maximum Subarray Sum",
        statement_markdown="Find contiguous subarray with maximum sum.",
        difficulty="hard",
        language="python",
        published_at=now,
    )
    db_session.add(pv3)
    await db_session.flush()

    db_session.add(ProblemTopicAssignment(problem_version_id=pv3.id, topic_id=t_arrays.id))

    await db_session.commit()

    return {
        "teacher": teacher,
        "student": student,
        "p1": p1,
        "pv1": pv1,
        "p2": p2,
        "pv2": pv2,
        "p3": p3,
        "pv3": pv3,
        "tc1_sample": tc1_sample,
        "tc1_hidden": tc1_hidden,
    }


@pytest.mark.asyncio
async def test_problem_listing_and_pagination(client, library_fixture):
    """Test standard list and rich paginated list with facet counts."""
    # 1. Standard list (backward compatible)
    res_raw = await client.get("/api/v1/problems")
    assert res_raw.status_code == 200
    raw_list = res_raw.json()
    assert isinstance(raw_list, list)
    assert len(raw_list) == 3

    # 2. Rich paginated response
    res_p = await client.get("/api/v1/problems?paginate=true&page=1&page_size=2")
    assert res_p.status_code == 200
    data = res_p.json()
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 2
    assert len(data["items"]) == 2
    assert data["difficulty_counts"] == {"easy": 1, "medium": 1, "hard": 1, "total": 3}


@pytest.mark.asyncio
async def test_problem_filtering_and_search(client, library_fixture):
    """Test filtering by difficulty, topic, and keyword search."""
    # Filter by difficulty
    res_easy = await client.get("/api/v1/problems?difficulty=easy")
    assert res_easy.status_code == 200
    easy_items = res_easy.json()
    assert len(easy_items) == 1
    assert easy_items[0]["slug"] == "print-hello-loop"

    # Filter by topic slug
    res_rec = await client.get("/api/v1/problems?topic=recursion")
    assert res_rec.status_code == 200
    rec_items = res_rec.json()
    assert len(rec_items) == 1
    assert rec_items[0]["slug"] == "factorial-recursion"

    # Search keyword
    res_search = await client.get("/api/v1/problems?search=subarray")
    assert res_search.status_code == 200
    search_items = res_search.json()
    assert len(search_items) == 1
    assert search_items[0]["slug"] == "array-max-subarray"


@pytest.mark.asyncio
async def test_student_bookmark_toggle_and_retrieval(client, library_fixture):
    """Test authenticated bookmark save, listing, and removal lifecycle."""
    student = library_fixture["student"]
    p1 = library_fixture["p1"]
    headers = auth_header(student)

    # 1. Unauthenticated toggle rejected
    res_unauth = await client.post(f"/api/v1/problems/{p1.id}/bookmark")
    assert res_unauth.status_code == 401

    # 2. Authenticated student toggles bookmark ON
    res_bm_on = await client.post(f"/api/v1/problems/{p1.id}/bookmark", headers=headers)
    assert res_bm_on.status_code == 200
    assert res_bm_on.json()["is_saved"] is True

    # 3. Retrieve student's bookmarks list
    res_my_bms = await client.get("/api/v1/problems/bookmarks/me", headers=headers)
    assert res_my_bms.status_code == 200
    bms = res_my_bms.json()
    assert len(bms) == 1
    assert bms[0]["id"] == p1.id
    assert bms[0]["is_saved"] is True

    # 4. Toggle bookmark OFF
    res_bm_off = await client.post(f"/api/v1/problems/{p1.id}/bookmark", headers=headers)
    assert res_bm_off.status_code == 200
    assert res_bm_off.json()["is_saved"] is False

    # 5. Retrieve student's bookmarks list again (empty)
    res_my_bms2 = await client.get("/api/v1/problems/bookmarks/me", headers=headers)
    assert res_my_bms2.status_code == 200
    assert len(res_my_bms2.json()) == 0


@pytest.mark.asyncio
async def test_test_case_privacy_enforcement(client, library_fixture):
    """Verify that private and hidden test cases are NEVER leaked to students."""
    p1 = library_fixture["p1"]

    # Problem details endpoint
    res_detail = await client.get(f"/api/v1/problems/{p1.id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    # Should only return sample test cases
    assert len(detail["sample_test_cases"]) == 1
    assert detail["sample_test_cases"][0]["id"] == library_fixture["tc1_sample"].id

    # Samples endpoint
    res_samples = await client.get(f"/api/v1/problems/{p1.id}/samples")
    assert res_samples.status_code == 200
    samples = res_samples.json()
    sample_ids = [s["id"] for s in samples]
    assert library_fixture["tc1_sample"].id in sample_ids
    assert library_fixture["tc1_hidden"].id not in sample_ids


@pytest.mark.asyncio
async def test_submission_history_and_concept_violations(client, library_fixture, db_session):
    """Test student submission history retrieval with criterion scores and violations."""
    student = library_fixture["student"]
    p1 = library_fixture["p1"]
    pv1 = library_fixture["pv1"]
    headers = auth_header(student)

    # Insert a submission with evaluation run, score breakdown, and violation
    sub = Submission(
        user_id=student.id,
        problem_version_id=pv1.id,
        language="python",
        source_code="print('Hello World')\nprint('Hello World')\nprint('Hello World')\nprint('Hello World')",
        source_hash="hash123",
        status="completed",
    )
    db_session.add(sub)
    await db_session.flush()

    eval_run = EvaluationRun(
        submission_id=sub.id,
        rubric_id="rubric1",
        status="completed",
    )
    db_session.add(eval_run)
    await db_session.flush()

    # Functional passed (60), Concept failed (0)
    sb_func = ScoreBreakdown(evaluation_run_id=eval_run.id, criterion="functional_correctness", max_points=60.0, awarded_points=60.0, reason_code="ALL_TESTS_PASSED")
    sb_concept = ScoreBreakdown(evaluation_run_id=eval_run.id, criterion="concept_compliance", max_points=40.0, awarded_points=0.0, reason_code="MISSING_LOOP")
    db_session.add_all([sb_func, sb_concept])

    # Concept evidence record failure
    ev = ConceptEvidenceRecord(
        evaluation_run_id=eval_run.id,
        concept_name="loop",
        rule_id="rule_require_loop",
        status="failed",
        evidence_json="{}",
    )
    db_session.add(ev)
    await db_session.commit()

    # Query history endpoint
    res = await client.get(f"/api/v1/problems/{p1.id}/submissions", headers=headers)
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["score"] == 60.0
    assert items[0]["functional_score"] == 60.0
    assert items[0]["concept_score"] == 0.0
    assert "Missing required concept: loop" in items[0]["concept_violations"]


@pytest.mark.asyncio
async def test_content_import_validation_and_duplicate_detection(client, library_fixture, db_session):
    """Test dataset import pipeline with provenance, license requirement, and duplicate handling."""
    teacher = library_fixture["teacher"]
    headers = auth_header(teacher)

    # 1. Missing license type should be rejected
    bad_req = {
        "source_name": "Test Source",
        "license_type": "",
        "problems": []
    }
    res_bad = await client.post("/api/v1/problems/import", json=bad_req, headers=headers)
    assert res_bad.status_code == 400

    # 2. Valid dataset with one new problem and one duplicate of existing p1
    import_payload = {
        "source_name": "University Algorithms Courseware",
        "license_type": "CC-BY-4.0",
        "provenance_url": "https://cs.university.edu/problems",
        "problems": [
            {
                "title": "Print Hello World Using a Loop",
                "slug": "print-hello-loop", # duplicate of p1
                "statement_markdown": "Duplicate",
                "difficulty": "easy",
                "language": "python",
                "topics": ["loops"],
                "expected_concepts": ["loop"],
                "test_cases": [],
                "concept_rules": []
            },
            {
                "title": "Reverse Array In-Place",
                "slug": "reverse-array-in-place", # brand new
                "statement_markdown": "Reverse array using two pointers.",
                "difficulty": "medium",
                "language": "python",
                "topics": ["arrays", "loops"],
                "expected_concepts": ["while_loop"],
                "test_cases": [
                    {
                        "input_data": "1 2 3 4\n",
                        "expected_output": "4 3 2 1\n",
                        "visibility": "sample",
                        "weight": 1.0
                    }
                ],
                "concept_rules": [
                    {
                        "concept": "while_loop",
                        "rule_id": "rule_require_while",
                        "accepted_constructs": ["While"],
                        "required": True,
                        "min_occurrences": 1,
                        "description": "Must use while loop"
                    }
                ]
            }
        ]
    }

    res_import = await client.post("/api/v1/problems/import", json=import_payload, headers=headers)
    assert res_import.status_code == 200
    report = res_import.json()
    assert report["total_processed"] == 2
    assert report["imported_count"] == 1
    assert report["skipped_duplicates"] == 1
    assert "reverse-array-in-place" in report["imported_slugs"]
    assert "print-hello-loop" in report["skipped_slugs"]

    # Verify the newly imported problem is searchable and browseable in the library
    res_search = await client.get("/api/v1/problems?search=Reverse Array")
    assert res_search.status_code == 200
    found = res_search.json()
    assert len(found) == 1
    assert found[0]["slug"] == "reverse-array-in-place"
    assert "while_loop" in found[0]["expected_concepts"]


@pytest.mark.asyncio
async def test_csv_content_import_validation_and_audit(client, library_fixture, db_session):
    """Test importing datasets from CSV format via POST /problems/import-csv."""
    teacher = library_fixture["teacher"]
    headers = auth_header(teacher)

    csv_data = (
        'title,slug,statement_markdown,difficulty,language,topics,expected_concepts,test_cases_json,rubric_rules_json\n'
        '"Count Vowels in String",count-vowels-in-string,"Count vowels using loop and membership.",easy,python,"strings,loops","loop","[]","[]"\n'
        '"Print Hello World Using a Loop",print-hello-loop,"Duplicate statement",easy,python,"loops","loop","[]","[]"\n'
    )


    req = {
        "source_name": "University CS101 Lab Sheets",
        "license_type": "CC-BY-4.0",
        "provenance_url": "https://cs101.university.edu/labs",
        "csv_content": csv_data,
    }

    res = await client.post("/api/v1/problems/import-csv", json=req, headers=headers)
    assert res.status_code == 200
    report = res.json()
    assert report["total_processed"] == 2
    assert report["imported_count"] == 1
    assert report["skipped_duplicates"] == 1
    assert "count-vowels-in-string" in report["imported_slugs"]
    assert "print-hello-loop" in report["skipped_slugs"]

    # Verify invalid CSV rejection
    res_empty = await client.post("/api/v1/problems/import-csv", json={"source_name": "S", "license_type": "MIT", "csv_content": ""}, headers=headers)
    assert res_empty.status_code == 400


@pytest.mark.asyncio
async def test_keyword_search_across_topic_and_concept(client, library_fixture):
    """Verify search finds problems by title, slug, ID, or topic keyword."""
    p1 = library_fixture["p1"]
    p2 = library_fixture["p2"]

    # Search by topic keyword "recursion"
    res_rec = await client.get("/api/v1/problems?search=recursion")
    assert res_rec.status_code == 200
    found_rec = [p["id"] for p in res_rec.json()]
    assert p2.id in found_rec

    # Search by problem ID
    res_id = await client.get(f"/api/v1/problems?search={p1.id}")
    assert res_id.status_code == 200
    found_id = [p["id"] for p in res_id.json()]
    assert p1.id in found_id


@pytest.mark.asyncio
async def test_student_progress_accurate_scoring_classification(client, library_fixture, db_session):
    """
    Verify that a student submission with 60/100 (concept violation) is classified
    as 'attempted', while a submission with 100/100 is classified as 'solved'.
    """
    student = library_fixture["student"]
    p1 = library_fixture["p1"]
    pv1 = library_fixture["pv1"]
    p2 = library_fixture["p2"]
    pv2 = library_fixture["pv2"]
    headers = auth_header(student)

    # 1. Student submits p1 and gets 60/100 (Attempted)
    sub1 = Submission(
        user_id=student.id,
        problem_version_id=pv1.id,
        language="python",
        source_code="print('Hello World')",
        source_hash="hash1",
        status="completed",
    )
    db_session.add(sub1)
    await db_session.flush()

    eval_run1 = EvaluationRun(submission_id=sub1.id, rubric_id="r1", status="completed")
    db_session.add(eval_run1)
    await db_session.flush()

    sb1 = ScoreBreakdown(evaluation_run_id=eval_run1.id, criterion="functional", max_points=60.0, awarded_points=60.0, reason_code="OUTPUT_MATCH")
    db_session.add(sb1)

    # 2. Student submits p2 and gets 100/100 (Solved)
    sub2 = Submission(
        user_id=student.id,
        problem_version_id=pv2.id,
        language="python",
        source_code="def fact(n): return 1 if n<=1 else n*fact(n-1)",
        source_hash="hash2",
        status="completed",
    )
    db_session.add(sub2)
    await db_session.flush()

    eval_run2 = EvaluationRun(submission_id=sub2.id, rubric_id="r2", status="completed")
    db_session.add(eval_run2)
    await db_session.flush()

    sb2_func = ScoreBreakdown(evaluation_run_id=eval_run2.id, criterion="functional", max_points=60.0, awarded_points=60.0, reason_code="OUTPUT_MATCH")
    sb2_conc = ScoreBreakdown(evaluation_run_id=eval_run2.id, criterion="concept", max_points=40.0, awarded_points=40.0, reason_code="RECURSION_FOUND")
    db_session.add_all([sb2_func, sb2_conc])
    await db_session.commit()

    # Query problem library as student
    res = await client.get("/api/v1/problems?paginate=true", headers=headers)
    assert res.status_code == 200
    data = res.json()
    items_by_id = {item["id"]: item for item in data["items"]}

    assert items_by_id[p1.id]["student_status"] == "attempted"
    assert items_by_id[p2.id]["student_status"] == "solved"

    # Query problem detail for p1
    res_det1 = await client.get(f"/api/v1/problems/{p1.id}", headers=headers)
    assert res_det1.status_code == 200
    assert res_det1.json()["student_status"] == "attempted"

    # Query problem detail for p2
    res_det2 = await client.get(f"/api/v1/problems/{p2.id}", headers=headers)
    assert res_det2.status_code == 200
    assert res_det2.json()["student_status"] == "solved"

    # Filter by status=solved
    res_solved = await client.get("/api/v1/problems?status=solved", headers=headers)
    assert res_solved.status_code == 200
    solved_ids = [p["id"] for p in res_solved.json()]
    assert p2.id in solved_ids
    assert p1.id not in solved_ids

    # Filter by status=attempted
    res_att = await client.get("/api/v1/problems?status=attempted", headers=headers)
    assert res_att.status_code == 200
    att_ids = [p["id"] for p in res_att.json()]
    assert p1.id in att_ids
    assert p2.id not in att_ids

