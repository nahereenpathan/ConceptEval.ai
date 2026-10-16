"""
Student Analytics and Concept Mastery API Endpoints
Provides personal and faculty-scoped concept mastery analytics.
"""

from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.authz import (
    FACULTY_ROLES,
    get_user_organization_ids,
)
from app.db.session import get_db
from app.models.education import StudentConceptProgress
from app.models.organization import OrganizationMembership
from app.models.user import User
from app.schemas.education import StudentConceptProgressResponse

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/student/me", response_model=List[StudentConceptProgressResponse])
async def get_my_concept_progress(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve personal concept mastery progression for the authenticated student."""
    stmt = (
        select(StudentConceptProgress)
        .where(StudentConceptProgress.user_id == current_user.id)
        .order_by(StudentConceptProgress.concept_name)
    )
    records = (await db.execute(stmt)).scalars().all()

    results = []
    for r in records:
        attempts = r.attempt_count or 0
        successes = r.successful_attempt_count or 0
        mastery = round((successes / attempts) * 100.0, 1) if attempts > 0 else 0.0
        results.append(
            StudentConceptProgressResponse(
                concept_name=r.concept_name,
                attempt_count=attempts,
                successful_attempt_count=successes,
                mastery_percentage=mastery,
                last_attempt_at=r.last_attempt_at,
            )
        )
    return results


@router.get("/student/{student_user_id}", response_model=List[StudentConceptProgressResponse])
async def get_student_concept_progress(
    student_user_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Retrieve concept progress for a specific student.
    Allowed if caller is the student themselves, or a verified teacher/admin
    sharing an organization with the student.
    Cross-organization student spying is strictly prohibited.
    """
    if student_user_id != current_user.id:
        # Check for shared organization where caller has faculty role
        caller_faculty_orgs_stmt = select(OrganizationMembership.organization_id).where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.status == "active",
            OrganizationMembership.role.in_(FACULTY_ROLES),
        )
        caller_faculty_orgs = set((await db.execute(caller_faculty_orgs_stmt)).scalars().all())

        if not caller_faculty_orgs:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "ACCESS_DENIED", "message": "You do not have faculty permissions to view student analytics."},
            )

        student_orgs_stmt = select(OrganizationMembership.organization_id).where(
            OrganizationMembership.user_id == student_user_id,
            OrganizationMembership.status == "active",
        )
        student_orgs = set((await db.execute(student_orgs_stmt)).scalars().all())

        shared_orgs = caller_faculty_orgs.intersection(student_orgs)
        if not shared_orgs:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "ACCESS_DENIED", "message": "Cannot view analytics for a student outside your organization."},
            )

    stmt = (
        select(StudentConceptProgress)
        .where(StudentConceptProgress.user_id == student_user_id)
        .order_by(StudentConceptProgress.concept_name)
    )
    records = (await db.execute(stmt)).scalars().all()

    results = []
    for r in records:
        attempts = r.attempt_count or 0
        successes = r.successful_attempt_count or 0
        mastery = round((successes / attempts) * 100.0, 1) if attempts > 0 else 0.0
        results.append(
            StudentConceptProgressResponse(
                concept_name=r.concept_name,
                attempt_count=attempts,
                successful_attempt_count=successes,
                mastery_percentage=mastery,
                last_attempt_at=r.last_attempt_at,
            )
        )
    return results
