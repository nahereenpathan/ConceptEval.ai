"""
Classrooms and Assignments API Endpoints
Enforces strict organization-level multi-tenant boundaries and role authorization.
"""

from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.authz import (
    FACULTY_ROLES,
    ROLE_STUDENT,
    get_user_organization_ids,
    verify_organization_access,
)
from app.db.session import get_db
from app.models.education import (
    Assignment,
    Classroom,
    Course,
    Enrollment,
    StudentConceptProgress,
)
from app.models.problem import Problem, ProblemVersion
from app.models.user import User
from app.schemas.education import (
    AssignmentCreateRequest,
    AssignmentResponse,
    ClassroomAnalyticsResponse,
    ClassroomCreateRequest,
    ClassroomEnrollRequest,
    ClassroomResponse,
    EnrollmentResponse,
    StudentConceptProgressResponse,
)

router = APIRouter(prefix="/classrooms", tags=["Classrooms & Assignments"])


@router.get("", response_model=List[ClassroomResponse])
async def list_classrooms(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    organization_id: Optional[str] = Query(None, description="Filter by verified organization"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """
    List classrooms within the caller's verified organizations.
    Cross-organization access is strictly prohibited.
    """
    stmt = (
        select(Classroom)
        .options(selectinload(Classroom.enrollments))
        .offset(skip)
        .limit(limit)
    )

    if organization_id:
        # Verify caller has active membership in this organization (never trust client param)
        await verify_organization_access(db, current_user.id, organization_id)
        stmt = stmt.where(Classroom.organization_id == organization_id)
    else:
        user_org_ids = await get_user_organization_ids(db, current_user.id)
        if not user_org_ids:
            return []
        stmt = stmt.where(Classroom.organization_id.in_(user_org_ids))

    classrooms = (await db.execute(stmt)).scalars().all()

    return [
        ClassroomResponse(
            id=c.id,
            organization_id=c.organization_id,
            course_id=c.course_id,
            name=c.name,
            created_by_user_id=c.created_by_user_id,
            created_at=c.created_at,
            student_count=len(c.enrollments),
        )
        for c in classrooms
    ]


@router.post("", response_model=ClassroomResponse, status_code=status.HTTP_201_CREATED)
async def create_classroom(
    req: ClassroomCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new classroom within an organization.
    Requires verified teacher or org_admin role within that organization.
    """
    # Verify faculty permissions in the target organization
    await verify_organization_access(
        db=db,
        user_id=current_user.id,
        organization_id=req.organization_id,
        allowed_roles=FACULTY_ROLES,
    )

    # Ensure course exists in this organization
    stmt_course = select(Course).where(
        Course.organization_id == req.organization_id,
        Course.name == req.course_name,
    )
    course = (await db.execute(stmt_course)).scalar_one_or_none()
    if not course:
        course = Course(
            organization_id=req.organization_id,
            name=req.course_name or "Default Course",
            created_by_user_id=current_user.id,
        )
        db.add(course)
        await db.flush()

    classroom = Classroom(
        organization_id=req.organization_id,
        course_id=course.id,
        name=req.name.strip(),
        created_by_user_id=current_user.id,
    )
    db.add(classroom)
    await db.commit()
    await db.refresh(classroom)

    return ClassroomResponse(
        id=classroom.id,
        organization_id=classroom.organization_id,
        course_id=classroom.course_id,
        name=classroom.name,
        created_by_user_id=classroom.created_by_user_id,
        created_at=classroom.created_at,
        student_count=0,
    )


@router.get("/{classroom_id}", response_model=ClassroomResponse)
async def get_classroom(
    classroom_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve classroom details with tenant boundary enforcement."""
    stmt = (
        select(Classroom)
        .where(Classroom.id == classroom_id)
        .options(selectinload(Classroom.enrollments))
    )
    classroom = (await db.execute(stmt)).scalars().first()

    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CLASSROOM_NOT_FOUND", "message": "Classroom record not found."},
        )

    # Caller must be a member of the classroom's organization
    await verify_organization_access(db, current_user.id, classroom.organization_id)

    return ClassroomResponse(
        id=classroom.id,
        organization_id=classroom.organization_id,
        course_id=classroom.course_id,
        name=classroom.name,
        created_by_user_id=classroom.created_by_user_id,
        created_at=classroom.created_at,
        student_count=len(classroom.enrollments),
    )


@router.post("/{classroom_id}/enroll", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_student(
    classroom_id: str,
    req: ClassroomEnrollRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Enroll a student into a classroom.
    Requires teacher or org_admin role in the classroom's organization.
    """
    stmt = select(Classroom).where(Classroom.id == classroom_id)
    classroom = (await db.execute(stmt)).scalar_one_or_none()
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CLASSROOM_NOT_FOUND", "message": "Classroom not found."},
        )

    # Faculty check on the classroom's organization
    await verify_organization_access(
        db=db,
        user_id=current_user.id,
        organization_id=classroom.organization_id,
        allowed_roles=FACULTY_ROLES,
    )

    # Verify student is a member of this organization
    await verify_organization_access(
        db=db,
        user_id=req.student_user_id,
        organization_id=classroom.organization_id,
    )

    # Check for existing enrollment
    stmt_existing = select(Enrollment).where(
        Enrollment.classroom_id == classroom_id,
        Enrollment.student_user_id == req.student_user_id,
    )
    existing = (await db.execute(stmt_existing)).scalar_one_or_none()
    if existing:
        return EnrollmentResponse(
            id=existing.id,
            classroom_id=existing.classroom_id,
            student_user_id=existing.student_user_id,
            status=existing.status,
            enrolled_at=existing.enrolled_at,
        )

    enrollment = Enrollment(
        classroom_id=classroom_id,
        student_user_id=req.student_user_id,
        status="active",
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)

    return EnrollmentResponse(
        id=enrollment.id,
        classroom_id=enrollment.classroom_id,
        student_user_id=enrollment.student_user_id,
        status=enrollment.status,
        enrolled_at=enrollment.enrolled_at,
    )


@router.get("/{classroom_id}/assignments", response_model=List[AssignmentResponse])
async def list_assignments(
    classroom_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List assignments for a classroom within caller's organization."""
    stmt_cls = select(Classroom).where(Classroom.id == classroom_id)
    classroom = (await db.execute(stmt_cls)).scalar_one_or_none()
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CLASSROOM_NOT_FOUND", "message": "Classroom not found."},
        )

    await verify_organization_access(db, current_user.id, classroom.organization_id)

    stmt = select(Assignment).where(Assignment.classroom_id == classroom_id)
    assignments = (await db.execute(stmt)).scalars().all()

    return [
        AssignmentResponse(
            id=a.id,
            classroom_id=a.classroom_id,
            problem_version_id=a.problem_version_id,
            title=a.title,
            available_from=a.available_from,
            due_at=a.due_at,
            max_attempts=a.max_attempts,
            created_by_user_id=a.created_by_user_id,
        )
        for a in assignments
    ]


@router.post("/{classroom_id}/assignments", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    classroom_id: str,
    req: AssignmentCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new assignment in a classroom.
    Requires teacher or org_admin role in the classroom's organization.
    Prevents assigning problems owned by other organizations.
    """
    stmt_cls = select(Classroom).where(Classroom.id == classroom_id)
    classroom = (await db.execute(stmt_cls)).scalar_one_or_none()
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CLASSROOM_NOT_FOUND", "message": "Classroom not found."},
        )

    # Faculty check
    await verify_organization_access(
        db=db,
        user_id=current_user.id,
        organization_id=classroom.organization_id,
        allowed_roles=FACULTY_ROLES,
    )

    # Verify problem version exists and check ownership
    stmt_pv = (
        select(ProblemVersion)
        .join(Problem, Problem.id == ProblemVersion.problem_id)
        .where(ProblemVersion.id == req.problem_version_id)
        .options(selectinload(ProblemVersion.problem))
    )
    pv = (await db.execute(stmt_pv)).scalars().first()
    if not pv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROBLEM_VERSION_NOT_FOUND", "message": "Problem version not found."},
        )

    # Cross-tenant problem leakage check:
    # If problem is organization-owned, it must belong to the same organization as the classroom
    if pv.problem.owner_type == "organization":
        if pv.problem.owner_organization_id != classroom.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "CROSS_TENANT_RESOURCE_DENIED",
                    "message": "Cannot assign a problem owned by a different organization.",
                },
            )

    assignment = Assignment(
        classroom_id=classroom_id,
        problem_version_id=req.problem_version_id,
        title=req.title.strip(),
        due_at=req.due_at,
        max_attempts=req.max_attempts,
        created_by_user_id=current_user.id,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    return AssignmentResponse(
        id=assignment.id,
        classroom_id=assignment.classroom_id,
        problem_version_id=assignment.problem_version_id,
        title=assignment.title,
        available_from=assignment.available_from,
        due_at=assignment.due_at,
        max_attempts=assignment.max_attempts,
        created_by_user_id=assignment.created_by_user_id,
    )


@router.get("/{classroom_id}/analytics", response_model=ClassroomAnalyticsResponse)
async def get_classroom_analytics(
    classroom_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Classroom concept mastery analytics.
    Strictly isolated to teachers or org admins of this classroom's organization.
    """
    stmt_cls = (
        select(Classroom)
        .where(Classroom.id == classroom_id)
        .options(selectinload(Classroom.enrollments))
    )
    classroom = (await db.execute(stmt_cls)).scalars().first()
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CLASSROOM_NOT_FOUND", "message": "Classroom not found."},
        )

    # Faculty check
    await verify_organization_access(
        db=db,
        user_id=current_user.id,
        organization_id=classroom.organization_id,
        allowed_roles=FACULTY_ROLES,
    )

    student_ids = [e.student_user_id for e in classroom.enrollments]
    concept_summaries = []

    if student_ids:
        stmt_progress = (
            select(
                StudentConceptProgress.concept_name,
                func.sum(StudentConceptProgress.attempt_count).label("attempts"),
                func.sum(StudentConceptProgress.successful_attempt_count).label("successes"),
                func.max(StudentConceptProgress.last_attempt_at).label("last_attempt"),
            )
            .where(StudentConceptProgress.user_id.in_(student_ids))
            .group_by(StudentConceptProgress.concept_name)
        )
        progress_rows = (await db.execute(stmt_progress)).all()

        for row in progress_rows:
            attempts = row.attempts or 0
            successes = row.successes or 0
            mastery = round((successes / attempts) * 100.0, 1) if attempts > 0 else 0.0
            concept_summaries.append(
                StudentConceptProgressResponse(
                    concept_name=row.concept_name,
                    attempt_count=attempts,
                    successful_attempt_count=successes,
                    mastery_percentage=mastery,
                    last_attempt_at=row.last_attempt,
                )
            )

    return ClassroomAnalyticsResponse(
        classroom_id=classroom.id,
        classroom_name=classroom.name,
        total_students=len(student_ids),
        concept_mastery_summary=concept_summaries,
    )
