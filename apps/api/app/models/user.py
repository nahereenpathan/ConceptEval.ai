"""
Identity, Session, Audit, and Idempotency Models
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Platform user account for learners, educators, and administrators."""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)  # active, suspended, pending

    # Relationships
    memberships = relationship("OrganizationMembership", back_populates="user", cascade="all, delete-orphan")
    refresh_sessions = relationship("RefreshSession", back_populates="user", cascade="all, delete-orphan")


class RefreshSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User refresh token tracking for secure session revocation."""
    __tablename__ = "refresh_sessions"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="refresh_sessions")


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Auditable log of administrative, authoring, and security actions."""
    __tablename__ = "audit_logs"

    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    organization_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class IdempotencyKey(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Idempotency enforcement record for financial and submission workflows."""
    __tablename__ = "idempotency_keys"

    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    response_reference: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("scope", "key_hash", name="uq_idempotency_scope_key"),
    )
