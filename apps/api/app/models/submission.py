"""
Submission and Evaluation Results Domain Models
Durable persistence for code submissions, AST concept evidence, sandbox outputs, and scores.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Submission(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Student or user code submission record."""
    __tablename__ = "submissions"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    organization_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    problem_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("problem_versions.id"), index=True, nullable=False)
    language: Mapped[str] = mapped_column(String(32), default="python", nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True, nullable=False)  # queued, running, completed, failed, cancelled, infrastructure_error
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    evaluation_runs = relationship("EvaluationRun", back_populates="submission", cascade="all, delete-orphan")


class EvaluationRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Specific evaluation run executed for a submission against a versioned rubric."""
    __tablename__ = "evaluation_runs"

    submission_id: Mapped[str] = mapped_column(String(36), ForeignKey("submissions.id", ondelete="CASCADE"), index=True, nullable=False)
    rubric_id: Mapped[str] = mapped_column(String(36), ForeignKey("grading_rubrics.id"), nullable=False)
    evaluator_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    sandbox_image_digest: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running", index=True, nullable=False)  # running, completed, failed, infrastructure_error
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    submission = relationship("Submission", back_populates="evaluation_runs")
    test_results = relationship("TestCaseResult", back_populates="evaluation_run", cascade="all, delete-orphan")
    concept_evidence = relationship("ConceptEvidenceRecord", back_populates="evaluation_run", cascade="all, delete-orphan")
    score_breakdowns = relationship("ScoreBreakdown", back_populates="evaluation_run", cascade="all, delete-orphan")
    feedback = relationship("SubmissionFeedback", back_populates="evaluation_run", uselist=False, cascade="all, delete-orphan")


class TestCaseResult(Base, UUIDPrimaryKeyMixin):
    """Dynamic test execution outcome for a test case."""
    __tablename__ = "test_case_results"

    evaluation_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    test_case_id: Mapped[str] = mapped_column(String(36), ForeignKey("test_cases.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # passed, failed, timeout, runtime_error
    execution_time_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    memory_used_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    actual_output_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    failure_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    evaluation_run = relationship("EvaluationRun", back_populates="test_results")


class ConceptEvidenceRecord(Base, UUIDPrimaryKeyMixin):
    """Machine-readable evidence captured during static AST evaluation."""
    __tablename__ = "concept_evidence_records"

    evaluation_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    concept_name: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # passed, failed
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)  # Locations, AST node types, snippets
    confidence: Mapped[Optional[float]] = mapped_column(Float, default=1.0, nullable=True)
    explanation_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    evaluation_run = relationship("EvaluationRun", back_populates="concept_evidence")


class ScoreBreakdown(Base, UUIDPrimaryKeyMixin):
    """Criteria-level points and reasons awarded under the rubric."""
    __tablename__ = "score_breakdowns"

    evaluation_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    criterion: Mapped[str] = mapped_column(String(64), nullable=False)  # functional_correctness, concept_compliance, etc.
    max_points: Mapped[float] = mapped_column(Float, nullable=False)
    awarded_points: Mapped[float] = mapped_column(Float, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)

    evaluation_run = relationship("EvaluationRun", back_populates="score_breakdowns")


class SubmissionFeedback(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Structured pedagogical feedback presented to the student."""
    __tablename__ = "submission_feedback"

    evaluation_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    feedback_json: Mapped[str] = mapped_column(Text, nullable=False)  # Explanations, suggestions, summary
    reference_solution_version_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    evaluation_run = relationship("EvaluationRun", back_populates="feedback")
