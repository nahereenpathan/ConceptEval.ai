"""
Multi-Tenant Isolation, Organization Boundaries, and Authorization Tests
Validates:
1. Cross-tenant isolation (Org A vs Org B resources).
2. Student submission privacy (students cannot view other students' submissions).
3. Faculty permissions (teachers/admins can view student work within their organization).
4. Platform problem visibility (globally available according to publishing rules).
5. Anti-spoofing (rejecting client-supplied organization_id without verified membership).
6. Refresh-token rotation, revocation, and logout lifecycle.
"""

from datetime import datetime, timezone
import hashlib
from unittest.mock import patch
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token, create_refresh_token, get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.education import Classroom, Course, Enrollment, StudentConceptProgress
from app.models.organization import Organization, OrganizationMembership
from app.models.problem import Problem, ProblemVersion, TestCase
from app.models.submission import Submission
from app.models.user import RefreshSession, User


@pytest_asyncio.fixture
async def db_session():
    """In-memory isolated SQLite database for tenant isolation testing."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    await test_engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """FastAPI async test client with session dependency override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def tenant_fixture(db_session):
    """
    Seeds a two-organization topology with users, roles, problems, and submissions:
    - Organization A (MIT):
      - User: admin_a (org_admin)
      - User: teacher_a (teacher)
      - User: student_a1 (student)
      - User: student_a2 (student)
      - Problem: prob_org_a (organization problem)
    - Organization B (Stanford):
      - User: admin_b (org_admin)
      - User: teacher_b (teacher)
      - User: student_b1 (student)
      - Problem: prob_org_b (organization problem)
    - Platform:
      - Problem: prob_platform (platform problem)
    """
    pw_hash = get_password_hash("SecretPassword123!")

    # Users
    admin_a = User(email="admin_a@mit.edu", display_name="Admin MIT", password_hash=pw_hash, status="active")
    teacher_a = User(email="teacher_a@mit.edu", display_name="Prof A", password_hash=pw_hash, status="active")
    student_a1 = User(email="student_a1@mit.edu", display_name="Student A1", password_hash=pw_hash, status="active")
    student_a2 = User(email="student_a2@mit.edu", display_name="Student A2", password_hash=pw_hash, status="active")

    admin_b = User(email="admin_b@stanford.edu", display_name="Admin Stanford", password_hash=pw_hash, status="active")
    teacher_b = User(email="teacher_b@stanford.edu", display_name="Prof B", password_hash=pw_hash, status="active")
    student_b1 = User(email="student_b1@stanford.edu", display_name="Student B1", password_hash=pw_hash, status="active")

    db_session.add_all([admin_a, teacher_a, student_a1, student_a2, admin_b, teacher_b, student_b1])
    await db_session.flush()

    # Organizations
    org_a = Organization(name="MIT", slug="mit", status="active", created_by_user_id=admin_a.id)
    org_b = Organization(name="Stanford", slug="stanford", status="active", created_by_user_id=admin_b.id)
    db_session.add_all([org_a, org_b])
    await db_session.flush()

    # Memberships
    m_admin_a = OrganizationMembership(organization_id=org_a.id, user_id=admin_a.id, role="org_admin", status="active")
    m_teacher_a = OrganizationMembership(organization_id=org_a.id, user_id=teacher_a.id, role="teacher", status="active")
    m_student_a1 = OrganizationMembership(organization_id=org_a.id, user_id=student_a1.id, role="student", status="active")
    m_student_a2 = OrganizationMembership(organization_id=org_a.id, user_id=student_a2.id, role="student", status="active")

    m_admin_b = OrganizationMembership(organization_id=org_b.id, user_id=admin_b.id, role="org_admin", status="active")
    m_teacher_b = OrganizationMembership(organization_id=org_b.id, user_id=teacher_b.id, role="teacher", status="active")
    m_student_b1 = OrganizationMembership(organization_id=org_b.id, user_id=student_b1.id, role="student", status="active")

    db_session.add_all([m_admin_a, m_teacher_a, m_student_a1, m_student_a2, m_admin_b, m_teacher_b, m_student_b1])
    await db_session.flush()

    # Platform Problem
    p_plat = Problem(owner_type="platform", slug="platform-hello", status="published", created_by_user_id=admin_a.id)
    db_session.add(p_plat)
    await db_session.flush()
    pv_plat = ProblemVersion(problem_id=p_plat.id, version_number=1, title="Platform Hello", statement_markdown="print hello")
    db_session.add(pv_plat)

    # Org A Problem
    p_org_a = Problem(owner_type="organization", owner_organization_id=org_a.id, slug="mit-quiz-1", status="published", created_by_user_id=teacher_a.id)
    db_session.add(p_org_a)
    await db_session.flush()
    pv_org_a = ProblemVersion(problem_id=p_org_a.id, version_number=1, title="MIT Quiz 1", statement_markdown="solve MIT quiz")
    db_session.add(pv_org_a)

    # Org B Problem
    p_org_b = Problem(owner_type="organization", owner_organization_id=org_b.id, slug="stanford-lab-1", status="published", created_by_user_id=teacher_b.id)
    db_session.add(p_org_b)
    await db_session.flush()
    pv_org_b = ProblemVersion(problem_id=p_org_b.id, version_number=1, title="Stanford Lab 1", statement_markdown="solve Stanford lab")
    db_session.add(pv_org_b)

    # Submissions
    sub_a1 = Submission(
        user_id=student_a1.id,
        organization_id=org_a.id,
        problem_version_id=pv_org_a.id,
        source_code="print('mit a1')",
        source_hash=hashlib.sha256(b"mit a1").hexdigest(),
        status="completed",
    )
    db_session.add(sub_a1)
    await db_session.commit()

    return {
        "org_a": org_a,
        "org_b": org_b,
        "admin_a": admin_a,
        "teacher_a": teacher_a,
        "student_a1": student_a1,
        "student_a2": student_a2,
        "admin_b": admin_b,
        "teacher_b": teacher_b,
        "student_b1": student_b1,
        "p_plat": p_plat,
        "pv_plat": pv_plat,
        "p_org_a": p_org_a,
        "pv_org_a": pv_org_a,
        "p_org_b": p_org_b,
        "pv_org_b": pv_org_b,
        "sub_a1": sub_a1,
    }


def auth_header(user: User) -> dict:
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def error_code(res) -> str:
    """Helper to extract standardized error code from JSON response."""
    data = res.json()
    if isinstance(data, dict):
        if "error" in data and isinstance(data["error"], dict):
            return data["error"].get("code", "")
        if "detail" in data and isinstance(data["detail"], dict):
            return data["detail"].get("code", "")
    return ""



# ==============================================================================
# 1. Cross-Tenant Problem Scoping Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_platform_problems_are_accessible_globally(client, tenant_fixture):
    """Platform problems are visible to unauthenticated and authenticated users."""
    # Unauthenticated
    res = await client.get("/api/v1/problems")
    assert res.status_code == 200
    slugs = [p["slug"] for p in res.json()]
    assert "platform-hello" in slugs
    assert "mit-quiz-1" not in slugs
    assert "stanford-lab-1" not in slugs

    # Authenticated Student A1 sees Platform + Org A problems
    res_a = await client.get("/api/v1/problems", headers=auth_header(tenant_fixture["student_a1"]))
    assert res_a.status_code == 200
    slugs_a = [p["slug"] for p in res_a.json()]
    assert "platform-hello" in slugs_a
    assert "mit-quiz-1" in slugs_a
    assert "stanford-lab-1" not in slugs_a  # Cannot see Org B problems


@pytest.mark.asyncio
async def test_cross_tenant_problem_detail_access_denied(client, tenant_fixture):
    """User in Org B cannot retrieve problem details for Org A's private problem."""
    prob_a_id = tenant_fixture["p_org_a"].id

    # Student A1 (Org A) can view Org A problem
    res_ok = await client.get(f"/api/v1/problems/{prob_a_id}", headers=auth_header(tenant_fixture["student_a1"]))
    assert res_ok.status_code == 200
    assert res_ok.json()["title"] == "MIT Quiz 1"

    # Student B1 (Org B) is denied access to Org A problem
    res_denied = await client.get(f"/api/v1/problems/{prob_a_id}", headers=auth_header(tenant_fixture["student_b1"]))
    assert res_denied.status_code in (403, 404)

    # Unauthenticated visitor cannot view Org A problem
    res_unauth = await client.get(f"/api/v1/problems/{prob_a_id}")
    assert res_unauth.status_code == 401


@pytest.mark.asyncio
async def test_tenant_spoofing_in_query_rejected(client, tenant_fixture):
    """User passing an organization_id they do not belong to is rejected with 403."""
    org_a_id = tenant_fixture["org_a"].id

    # Student B1 attempts to spoof ?organization_id=org_a
    res = await client.get(
        f"/api/v1/problems?organization_id={org_a_id}",
        headers=auth_header(tenant_fixture["student_b1"]),
    )
    assert res.status_code == 403
    assert error_code(res) == "TENANT_ACCESS_DENIED"


# ==============================================================================
# 2. Student Submission Privacy & Faculty Review Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_student_can_only_view_own_submission(client, tenant_fixture):
    """Student cannot view another student's submission even within the same organization."""
    sub_id = tenant_fixture["sub_a1"].id

    # Student A1 views their own submission -> 200 OK
    res_self = await client.get(f"/api/v1/submissions/{sub_id}", headers=auth_header(tenant_fixture["student_a1"]))
    assert res_self.status_code == 200
    assert res_self.json()["id"] == sub_id

    # Student A2 (same organization) attempts to view Student A1's submission -> 403 Forbidden
    res_peer = await client.get(f"/api/v1/submissions/{sub_id}", headers=auth_header(tenant_fixture["student_a2"]))
    assert res_peer.status_code == 403
    assert error_code(res_peer) == "ACCESS_DENIED"

    # Student B1 (different organization) attempts to view -> 403 Forbidden
    res_outside = await client.get(f"/api/v1/submissions/{sub_id}", headers=auth_header(tenant_fixture["student_b1"]))
    assert res_outside.status_code == 403


@pytest.mark.asyncio
async def test_faculty_permissions_within_organization(client, tenant_fixture):
    """Teachers and Org Admins in Org A can view Student A1's submission, but Org B faculty cannot."""
    sub_id = tenant_fixture["sub_a1"].id

    # Teacher A (MIT faculty) views Student A1 submission -> 200 OK
    res_teacher_a = await client.get(f"/api/v1/submissions/{sub_id}", headers=auth_header(tenant_fixture["teacher_a"]))
    assert res_teacher_a.status_code == 200

    # Admin A (MIT admin) views Student A1 submission -> 200 OK
    res_admin_a = await client.get(f"/api/v1/submissions/{sub_id}", headers=auth_header(tenant_fixture["admin_a"]))
    assert res_admin_a.status_code == 200

    # Teacher B (Stanford faculty) attempts to view MIT student submission -> 403 Forbidden
    res_teacher_b = await client.get(f"/api/v1/submissions/{sub_id}", headers=auth_header(tenant_fixture["teacher_b"]))
    assert res_teacher_b.status_code == 403

    # Admin B (Stanford admin) attempts to view MIT student submission -> 403 Forbidden
    res_admin_b = await client.get(f"/api/v1/submissions/{sub_id}", headers=auth_header(tenant_fixture["admin_b"]))
    assert res_admin_b.status_code == 403


@pytest.mark.asyncio
async def test_submission_creation_tenant_enforcement(client, tenant_fixture):
    """Submissions to organization problems require verified membership and cannot spoof org_id."""
    prob_a_id = tenant_fixture["p_org_a"].id
    org_a_id = tenant_fixture["org_a"].id
    org_b_id = tenant_fixture["org_b"].id

    # Student B attempts to submit to MIT problem -> 403 Forbidden
    with patch("app.tasks.evaluation.evaluate_submission_task.delay"):
        res_cross = await client.post(
            "/api/v1/submissions",
            json={
                "problem_id": prob_a_id,
                "problem_version_number": 1,
                "source_code": "print('exploit')",
            },
            headers=auth_header(tenant_fixture["student_b1"]),
        )
        assert res_cross.status_code == 403
        assert error_code(res_cross) == "TENANT_ACCESS_DENIED"

        # Student A attempts to spoof organization_id as Org B -> 400 Mismatch
        res_mismatch = await client.post(
            "/api/v1/submissions",
            json={
                "problem_id": prob_a_id,
                "problem_version_number": 1,
                "organization_id": org_b_id,
                "source_code": "print('mit')",
            },
            headers=auth_header(tenant_fixture["student_a1"]),
        )
        assert res_mismatch.status_code == 400
        assert error_code(res_mismatch) == "ORGANIZATION_MISMATCH"

        # Student A legitimately submits to MIT problem -> 202 Accepted
        res_ok = await client.post(
            "/api/v1/submissions",
            json={
                "problem_id": prob_a_id,
                "problem_version_number": 1,
                "source_code": "print('valid mit')",
            },
            headers=auth_header(tenant_fixture["student_a1"]),
        )
        assert res_ok.status_code == 202
        assert res_ok.json()["organization_id"] == org_a_id


# ==============================================================================
# 3. Classroom & Assignment Boundary Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_classroom_creation_and_cross_tenant_isolation(client, tenant_fixture):
    """Only faculty can create classrooms and cannot create classrooms in other organizations."""
    org_a_id = tenant_fixture["org_a"].id

    # Student A attempts to create classroom -> 403 INSUFFICIENT_PERMISSIONS
    res_student = await client.post(
        "/api/v1/classrooms",
        json={"organization_id": org_a_id, "name": "Hacked Class"},
        headers=auth_header(tenant_fixture["student_a1"]),
    )
    assert res_student.status_code == 403
    assert error_code(res_student) == "INSUFFICIENT_PERMISSIONS"

    # Teacher B (from Org B) attempts to create classroom in Org A -> 403 TENANT_ACCESS_DENIED
    res_cross = await client.post(
        "/api/v1/classrooms",
        json={"organization_id": org_a_id, "name": "Infiltrator Class"},
        headers=auth_header(tenant_fixture["teacher_b"]),
    )
    assert res_cross.status_code == 403
    assert error_code(res_cross) == "TENANT_ACCESS_DENIED"

    # Teacher A (from Org A) creates classroom in Org A -> 201 Created
    res_ok = await client.post(
        "/api/v1/classrooms",
        json={"organization_id": org_a_id, "name": "MIT CS101"},
        headers=auth_header(tenant_fixture["teacher_a"]),
    )
    assert res_ok.status_code == 201
    classroom_id = res_ok.json()["id"]

    # Teacher B attempts to view MIT classroom -> 403 Forbidden
    res_view_denied = await client.get(
        f"/api/v1/classrooms/{classroom_id}",
        headers=auth_header(tenant_fixture["teacher_b"]),
    )
    assert res_view_denied.status_code == 403


@pytest.mark.asyncio
async def test_cross_tenant_problem_assignment_prevented(client, tenant_fixture):
    """Teacher cannot attach an Org B problem to an Org A classroom assignment."""
    org_a_id = tenant_fixture["org_a"].id

    # Create classroom in Org A
    cls_res = await client.post(
        "/api/v1/classrooms",
        json={"organization_id": org_a_id, "name": "MIT Algorithms"},
        headers=auth_header(tenant_fixture["teacher_a"]),
    )
    assert cls_res.status_code == 201
    classroom_id = cls_res.json()["id"]

    # Attempt to assign Stanford problem (Org B) to MIT classroom (Org A)
    res_assign_cross = await client.post(
        f"/api/v1/classrooms/{classroom_id}/assignments",
        json={
            "problem_version_id": tenant_fixture["pv_org_b"].id,
            "title": "Stolen Lab Assignment",
        },
        headers=auth_header(tenant_fixture["teacher_a"]),
    )
    assert res_assign_cross.status_code == 403
    assert error_code(res_assign_cross) == "CROSS_TENANT_RESOURCE_DENIED"

    # Legitimate assignment of MIT problem to MIT classroom -> 201 Created
    res_assign_ok = await client.post(
        f"/api/v1/classrooms/{classroom_id}/assignments",
        json={
            "problem_version_id": tenant_fixture["pv_org_a"].id,
            "title": "MIT Quiz 1 Assignment",
        },
        headers=auth_header(tenant_fixture["teacher_a"]),
    )
    assert res_assign_ok.status_code == 201
    assert res_assign_ok.json()["title"] == "MIT Quiz 1 Assignment"


# ==============================================================================
# 4. Analytics Privacy Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_student_concept_analytics_privacy(client, tenant_fixture, db_session):
    """Students can view their own analytics; faculty can only view students in their organization."""
    student_a_id = tenant_fixture["student_a1"].id

    # Seed analytics progress record for student A1
    progress = StudentConceptProgress(
        user_id=student_a_id,
        concept_name="loops",
        attempt_count=5,
        successful_attempt_count=4,
        last_attempt_at=datetime.now(timezone.utc),
    )
    db_session.add(progress)
    await db_session.commit()

    # Student A1 checks personal analytics -> 200 OK
    res_me = await client.get("/api/v1/analytics/student/me", headers=auth_header(tenant_fixture["student_a1"]))
    assert res_me.status_code == 200
    assert len(res_me.json()) == 1
    assert res_me.json()[0]["concept_name"] == "loops"
    assert res_me.json()[0]["mastery_percentage"] == 80.0

    # Student A2 tries to inspect Student A1 analytics -> 403 Forbidden
    res_peer = await client.get(f"/api/v1/analytics/student/{student_a_id}", headers=auth_header(tenant_fixture["student_a2"]))
    assert res_peer.status_code == 403

    # Teacher A (same org) views Student A1 analytics -> 200 OK
    res_teacher_a = await client.get(f"/api/v1/analytics/student/{student_a_id}", headers=auth_header(tenant_fixture["teacher_a"]))
    assert res_teacher_a.status_code == 200
    assert res_teacher_a.json()[0]["mastery_percentage"] == 80.0

    # Teacher B (outside org) attempts to view Student A1 analytics -> 403 Forbidden
    res_teacher_b = await client.get(f"/api/v1/analytics/student/{student_a_id}", headers=auth_header(tenant_fixture["teacher_b"]))
    assert res_teacher_b.status_code == 403


# ==============================================================================
# 5. Authentication Lifecycle, Token Rotation & Revocation Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_auth_refresh_rotation_and_revocation(client):
    """Verifies refresh token rotation, replay prevention, and logout session revocation."""
    # 1. Register and Login
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "lifecycle_user@example.com", "password": "Password123!", "display_name": "Lifecycle Tester"},
    )
    assert reg_res.status_code == 201

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "lifecycle_user@example.com", "password": "Password123!"},
    )
    assert login_res.status_code == 200
    tokens = login_res.json()
    refresh_token_v1 = tokens["refresh_token"]

    # 2. Rotate refresh token -> Expect new tokens
    refresh_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token_v1},
    )
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    refresh_token_v2 = new_tokens["refresh_token"]
    assert refresh_token_v2 != refresh_token_v1

    # 3. Attempt replay of rotated refresh token v1 -> Expect 401 TOKEN_REVOKED
    replay_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token_v1},
    )
    assert replay_res.status_code == 401
    assert error_code(replay_res) == "TOKEN_REVOKED"

    # 4. Logout using refresh token v2
    logout_res = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token_v2},
    )
    assert logout_res.status_code == 200

    # 5. Attempt refresh with logged-out token v2 -> Expect 401 TOKEN_REVOKED
    after_logout_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token_v2},
    )
    assert after_logout_res.status_code == 401
    assert error_code(after_logout_res) == "TOKEN_REVOKED"
