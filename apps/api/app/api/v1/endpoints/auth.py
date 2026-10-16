"""
Authentication API Endpoints
Registration, Login, Refresh, and User Profile.
"""

from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.models.user import User, RefreshSession
from app.schemas.auth import (
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

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Retrieve authenticated user profile."""
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        status=current_user.status,
    )
