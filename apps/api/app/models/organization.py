"""
Organization and Multi-Tenant Workspaces
"""

from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Organization(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Educational organization (college, school, coding institute)."""
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    memberships = relationship("OrganizationMembership", back_populates="organization", cascade="all, delete-orphan")
    workspaces = relationship("Workspace", back_populates="organization", cascade="all, delete-orphan")


class OrganizationMembership(Base, UUIDPrimaryKeyMixin):
    """Associates a user with an organization and grants specific organizational roles."""
    __tablename__ = "organization_memberships"

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # student, teacher, org_admin, billing_manager
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    organization = relationship("Organization", back_populates="memberships")
    user = relationship("User", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_membership_user"),
    )


class Workspace(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Departmental or course sub-workspace within an organization."""
    __tablename__ = "workspaces"

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    organization = relationship("Organization", back_populates="workspaces")
    memberships = relationship("WorkspaceMembership", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceMembership(Base, UUIDPrimaryKeyMixin):
    """Workspace-level user role assignments."""
    __tablename__ = "workspace_memberships"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="member", nullable=False)

    workspace = relationship("Workspace", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_membership_user"),
    )
