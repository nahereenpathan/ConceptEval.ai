"""
Security and Cryptography Utilities
Argon2id password hashing and JWT authentication tokens.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import uuid
import jwt
from pwdlib import PasswordHash

from app.core.config import settings

# Initialize modern password hashing scheme
password_hasher = PasswordHash.recommended()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the stored Argon2 hash."""
    return password_hasher.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate a secure Argon2 hash from a plain password."""
    return password_hasher.hash(password)


def create_access_token(subject: str, extra_claims: Optional[Dict[str, Any]] = None) -> str:
    """Generate a signed JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": uuid.uuid4().hex,
        "type": "access",
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.APP_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Generate a signed JWT refresh token with unique jti claim."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": uuid.uuid4().hex,
        "type": "refresh",
    }
    return jwt.encode(to_encode, settings.APP_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)



def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a signed JWT token."""
    return jwt.decode(
        token,
        settings.APP_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
