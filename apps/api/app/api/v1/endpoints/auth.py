"""
Authentication API Endpoints
Registration, Login, Refresh, and User Profile.
"""

from datetime import datetime, timedelta, timezone
import hashlib
from typing import Annotated
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.session import get_db
from app.models.organization import Organization, OrganizationMembership
from app.models.user import RefreshSession, User
from app.schemas.auth import (
    LogoutResponse,
    OrganizationMembershipResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserProfileResponse,
    UserRegisterRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def register(
    req: UserRegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Register a new student or educator account."""
    # Check if email is already taken
    stmt = select(User).where(User.email == req.email.lower().strip())
    existing_user = (await db.execute(stmt)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_ALREADY_REGISTERED", "message": "An account with this email address already exists."},
        )

    hashed_pw = get_password_hash(req.password)
    user = User(
        email=req.email.lower().strip(),
        password_hash=hashed_pw,
        display_name=req.display_name.strip(),
        status="active",
        email_verified_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()

    return UserProfileResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        status=user.status,
        memberships=[],
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    req: UserLoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Authenticate with email and password and receive JWT tokens."""
    stmt = select(User).where(User.email == req.email.lower().strip())
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password."},
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "USER_SUSPENDED", "message": f"Account is {user.status}."},
        )

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # Track active refresh session for revocation and rotation
    token_hash = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()
    session_exp = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_session = RefreshSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=session_exp,
    )
    db.add(refresh_session)
    await db.flush()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    req: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Rotate refresh token and issue a fresh access token.
    Validates token signature and verifies active session record in database.
    Revokes the old refresh token upon rotation.
    """
    try:
        payload = decode_token(req.refresh_token)
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if not user_id or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_TOKEN", "message": "Invalid refresh token credentials."},
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "Refresh token has expired."},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Could not validate token signature."},
        )

    # Check database session
    token_hash = hashlib.sha256(req.refresh_token.encode("utf-8")).hexdigest()
    stmt = select(RefreshSession).where(
        RefreshSession.token_hash == token_hash,
        RefreshSession.user_id == user_id,
    )
    session_rec = (await db.execute(stmt)).scalar_one_or_none()

    if not session_rec or session_rec.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_REVOKED", "message": "Refresh token has been revoked or is invalid."},
        )

    # Verify user is active
    user_stmt = select(User).where(User.id == user_id)
    user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not user or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "USER_INACTIVE", "message": "User account is no longer active."},
        )

    # 1. Revoke the old refresh token session
    now = datetime.now(timezone.utc)
    session_rec.revoked_at = now

    # 2. Issue new tokens
    new_access_token = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)

    # 3. Store new refresh session
    new_token_hash = hashlib.sha256(new_refresh_token.encode("utf-8")).hexdigest()
    new_session_exp = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    new_session = RefreshSession(
        user_id=user.id,
        token_hash=new_token_hash,
        expires_at=new_session_exp,
    )
    db.add(new_session)
    await db.flush()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    req: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Revoke a refresh token session, invalidating future token refreshes.
    """
    try:
        token_hash = hashlib.sha256(req.refresh_token.encode("utf-8")).hexdigest()
        stmt = select(RefreshSession).where(RefreshSession.token_hash == token_hash)
        session_rec = (await db.execute(stmt)).scalar_one_or_none()
        if session_rec and session_rec.revoked_at is None:
            session_rec.revoked_at = datetime.now(timezone.utc)
            await db.flush()
    except Exception:
        pass

    return LogoutResponse(message="Successfully logged out and session revoked.")


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve authenticated user profile with active organization memberships."""
    stmt = (
        select(OrganizationMembership)
        .join(Organization, Organization.id == OrganizationMembership.organization_id)
        .where(
            OrganizationMembership.user_id == current_user.id,
            OrganizationMembership.status == "active",
        )
        .options(selectinload(OrganizationMembership.organization))
    )
    memberships = (await db.execute(stmt)).scalars().all()
    membership_dtos = [
        OrganizationMembershipResponse(
            organization_id=m.organization_id,
            organization_name=m.organization.name if m.organization else m.organization_id,
            role=m.role,
            status=m.status,
        )
        for m in memberships
    ]

    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        status=current_user.status,
        memberships=membership_dtos,
    )

