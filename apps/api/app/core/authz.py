"""
Server-Side Authorization and Multi-Tenant Isolation Engine
Enforces tenant boundary verification, role-based access control,
and resource-scoping across problems, submissions, classrooms, and analytics.
"""

from typing import List, Optional, Set
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization, OrganizationMembership
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import User

# Standard Role Constants
ROLE_STUDENT = "student"
ROLE_TEACHER = "teacher"
ROLE_ORG_ADMIN = "org_admin"
ROLE_BILLING_MANAGER = "billing_manager"

FACULTY_ROLES = {ROLE_TEACHER, ROLE_ORG_ADMIN}
ALL_ORG_ROLES = {ROLE_STUDENT, ROLE_TEACHER, ROLE_ORG_ADMIN, ROLE_BILLING_MANAGER}


async def get_user_active_memberships(
    db: AsyncSession,
    user_id: str,
) -> List[OrganizationMembership]:
    """Retrieve all active organization memberships for a user."""
    stmt = (
        select(OrganizationMembership)
        .where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.status == "active",
        )
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_user_organization_ids(
    db: AsyncSession,
    user_id: str,
) -> Set[str]:
    """Retrieve set of organization IDs where the user has active membership."""
    memberships = await get_user_active_memberships(db, user_id)
    return {m.organization_id for m in memberships}


async def verify_organization_access(
    db: AsyncSession,
    user_id: str,
    organization_id: str,
    allowed_roles: Optional[Set[str]] = None,
) -> OrganizationMembership:
    """
    Verify that user is an active member of the specified organization
    and possesses at least one of the allowed roles.
    Org admins always satisfy role requirements.
    Raises HTTPException 403 on violation. Never trusts client tenant input.
    """
    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "ORGANIZATION_REQUIRED", "message": "An organization identifier is required."},
        )

    stmt = select(OrganizationMembership).where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.user_id == user_id,
        OrganizationMembership.status == "active",
    )
    membership = (await db.execute(stmt)).scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "TENANT_ACCESS_DENIED",
                "message": "You are not an active member of this organization.",
                "organization_id": organization_id,
            },
        )

    if allowed_roles:
        # Org admin satisfies all organization-level roles
        if membership.role != ROLE_ORG_ADMIN and membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Operation requires one of roles: {sorted(list(allowed_roles))}. Current role: {membership.role}.",
                    "organization_id": organization_id,
                },
            )

    return membership


async def authorize_submission_access(
    db: AsyncSession,
    user: User,
    submission: Submission,
) -> None:
    """
    Verify that the user is authorized to view a submission.
    - Owner can always view their own submission.
    - Teachers and Org Admins in the submission's organization can view student submissions.
    - Other students or outside users receive 403 Forbidden.
    """
    if submission.user_id == user.id:
        return

    if not submission.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCESS_DENIED", "message": "You are not authorized to view this submission."},
        )

    # Check if user has teacher or org_admin role in the submission's organization
    stmt = select(OrganizationMembership).where(
        OrganizationMembership.organization_id == submission.organization_id,
        OrganizationMembership.user_id == user.id,
        OrganizationMembership.status == "active",
        OrganizationMembership.role.in_([ROLE_TEACHER, ROLE_ORG_ADMIN]),
    )
    faculty_membership = (await db.execute(stmt)).scalar_one_or_none()

    if not faculty_membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCESS_DENIED", "message": "You are not authorized to view this submission."},
        )


async def authorize_problem_access(
    db: AsyncSession,
    user: Optional[User],
    problem: Problem,
) -> None:
    """
    Verify that the user is authorized to view or access a problem.
    - Platform published problems: publicly visible.
    - Organization problems: strictly restricted to active members of that organization.
    - Draft problems: strictly restricted to teachers or org admins of that organization.
    """
    if problem.owner_type == "platform" and problem.status == "published":
        return

    if problem.owner_type == "organization":
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHENTICATED", "message": "Authentication required to access organization problems."},
            )

        if not problem.owner_organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "PROBLEM_NOT_FOUND", "message": "Problem not found."},
            )

        # Verify membership
        membership = await verify_organization_access(
            db=db,
            user_id=user.id,
            organization_id=problem.owner_organization_id,
        )

        if problem.status != "published":
            if membership.role not in FACULTY_ROLES:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "PROBLEM_NOT_FOUND", "message": "Problem not found."},
                )
        return

    # Non-published platform problem
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROBLEM_NOT_FOUND", "message": "Problem not found."},
        )
