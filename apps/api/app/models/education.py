"""
Educational Domain Models
Courses, Classrooms, Assignments, Enrollments, and Student Concept Mastery Analytics.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Course(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Course curriculum established within an organization."""
    __tablename__ = "courses"

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    classrooms = relationship("Classroom", back_populates="course", cascade="all, delete-orphan")


class Classroom(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Teacher-managed student cohort or section."""
    __tablename__ = "classrooms"

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    course = relationship("Course", back_populates="classrooms")
    enrollments = relationship("Enrollment", back_populates="classroom", cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="classroom", cascade="all, delete-orphan")


class Enrollment(Base, UUIDPrimaryKeyMixin):
    """Student enrollment record within a classroom."""
    __tablename__ = "enrollments"

    classroom_id: Mapped[str] = mapped_column(String(36), ForeignKey("classrooms.id", ondelete="CASCADE"), index=True, nullable=False)
    student_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)  # active, dropped, completed
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    classroom = relationship("Classroom", back_populates="enrollments")

    __table_args__ = (
        UniqueConstraint("classroom_id", "student_user_id", name="uq_classroom_student_enrollment"),
    )


class Assignment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Classroom coding assignment linking to a published problem version."""
    __tablename__ = "assignments"

    classroom_id: Mapped[str] = mapped_column(String(36), ForeignKey("classrooms.id", ondelete="CASCADE"), index=True, nullable=False)
    problem_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("problem_versions.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    available_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    max_attempts: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    classroom = relationship("Classroom", back_populates="assignments")


class AssignmentSubmission(Base, UUIDPrimaryKeyMixin):
    """Associates an official student submission with an assigned classroom assignment."""
    __tablename__ = "assignment_submissions"

    assignment_id: Mapped[str] = mapped_column(String(36), ForeignKey("assignments.id", ondelete="CASCADE"), index=True, nullable=False)
    submission_id: Mapped[str] = mapped_column(String(36), ForeignKey("submissions.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    student_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class StudentConceptProgress(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Derived analytics tracking concept mastery counts for individual students."""
    __tablename__ = "student_concept_progress"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    concept_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "concept_name", name="uq_user_concept_progress"),
    )
