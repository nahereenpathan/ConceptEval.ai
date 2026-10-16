"""
Problem Authoring, Versioning, Test Cases, and Rubrics
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Problem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Coding challenge master container."""
    __tablename__ = "problems"

    owner_type: Mapped[str] = mapped_column(String(32), default="platform", nullable=False)  # platform, organization
    owner_organization_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="SET NULL"), index=True, nullable=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    content_fingerprint: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)  # draft, published, archived
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    versions = relationship("ProblemVersion", back_populates="problem", cascade="all, delete-orphan")
    organization = relationship("Organization")

    __table_args__ = (
        Index("ix_problems_owner_org_status", "owner_organization_id", "status"),
    )



class ProblemVersion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable published or draft version of a problem statement and requirements."""
    __tablename__ = "problem_versions"

    problem_id: Mapped[str] = mapped_column(String(36), ForeignKey("problems.id", ondelete="CASCADE"), index=True, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    statement_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)  # easy, medium, hard
    language: Mapped[str] = mapped_column(String(32), default="python", nullable=False)
    constraints_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_format: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_format: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    starter_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reference_solution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_fingerprint: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    problem = relationship("Problem", back_populates="versions")
    rubrics = relationship("GradingRubric", back_populates="problem_version", cascade="all, delete-orphan")
    test_cases = relationship("TestCase", back_populates="problem_version", cascade="all, delete-orphan")
    topic_assignments = relationship("ProblemTopicAssignment", back_populates="problem_version", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("problem_id", "version_number", name="uq_problem_version_number"),
    )


class ProblemTopic(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tagging taxonomy for programming topics (e.g. loops, recursion, arrays, OOP)."""
    __tablename__ = "problem_topics"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)


class ProblemTopicAssignment(Base, UUIDPrimaryKeyMixin):
    """Join table associating problem versions with topic tags."""
    __tablename__ = "problem_topic_assignments"

    problem_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("problem_versions.id", ondelete="CASCADE"), index=True, nullable=False)
    topic_id: Mapped[str] = mapped_column(String(36), ForeignKey("problem_topics.id", ondelete="CASCADE"), index=True, nullable=False)

    problem_version = relationship("ProblemVersion", back_populates="topic_assignments")
    topic = relationship("ProblemTopic")


class GradingRubric(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Versioned grading rubric containing required concepts, weights, and prohibitions."""
    __tablename__ = "grading_rubrics"

    problem_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("problem_versions.id", ondelete="CASCADE"), index=True, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    rubric_json: Mapped[str] = mapped_column(Text, nullable=False)  # Serialized RubricSchema
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)  # draft, approved, published
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    reviewed_by_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    problem_version = relationship("ProblemVersion", back_populates="rubrics")


class TestCase(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Public, sample, or hidden test inputs and expected outputs."""
    __tablename__ = "test_cases"
    __test__ = False

    problem_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("problem_versions.id", ondelete="CASCADE"), index=True, nullable=False)
    visibility: Mapped[str] = mapped_column(String(32), default="public", nullable=False)  # sample, public, hidden
    input_data: Mapped[str] = mapped_column(Text, default="", nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, default="", nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    timeout_ms: Mapped[int] = mapped_column(Integer, default=3000, nullable=False)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, default=128, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    problem_version = relationship("ProblemVersion", back_populates="test_cases")


class RubricExtractionRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Audit log of NLP intent extraction runs for a problem draft."""
    __tablename__ = "rubric_extraction_runs"

    problem_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("problem_versions.id", ondelete="CASCADE"), index=True, nullable=False)
    model_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    output_json: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    validation_errors_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="completed", nullable=False)


class ProblemBookmark(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Student problem bookmarks and saved practice lists."""
    __tablename__ = "problem_bookmarks"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    problem_id: Mapped[str] = mapped_column(String(36), ForeignKey("problems.id", ondelete="CASCADE"), index=True, nullable=False)

    user = relationship("User")
    problem = relationship("Problem")

    __table_args__ = (
        UniqueConstraint("user_id", "problem_id", name="uq_user_problem_bookmark"),
    )


class ContentImportAudit(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Provenance tracking and audit report for authorized dataset imports."""
    __tablename__ = "content_import_audits"

    imported_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    license_type: Mapped[str] = mapped_column(String(64), nullable=False)
    provenance_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    format: Mapped[str] = mapped_column(String(32), default="json", nullable=False)
    total_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    imported_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_duplicates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    import_metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

