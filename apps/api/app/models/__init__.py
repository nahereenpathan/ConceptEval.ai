"""
Export all SQLAlchemy models for metadata registration and Alembic discovery.
"""

from app.db.base import Base
from app.models.user import User, RefreshSession, AuditLog, IdempotencyKey
from app.models.organization import Organization, OrganizationMembership, Workspace, WorkspaceMembership
from app.models.problem import (
    Problem,
    ProblemVersion,
    ProblemTopic,
    ProblemTopicAssignment,
    GradingRubric,
    TestCase,
    RubricExtractionRun,
    ProblemBookmark,
    ContentImportAudit,
)
from app.models.submission import Submission, EvaluationRun, TestCaseResult, ConceptEvidenceRecord, ScoreBreakdown, SubmissionFeedback
from app.models.education import Course, Classroom, Enrollment, Assignment, AssignmentSubmission, StudentConceptProgress
from app.models.billing import Plan, PlanLimit, Subscription, BillingEvent, UsageCounter, Invoice

__all__ = [
    "Base",
    "User",
    "RefreshSession",
    "AuditLog",
    "IdempotencyKey",
    "Organization",
    "OrganizationMembership",
    "Workspace",
    "WorkspaceMembership",
    "Problem",
    "ProblemVersion",
    "ProblemTopic",
    "ProblemTopicAssignment",
    "GradingRubric",
    "TestCase",
    "RubricExtractionRun",
    "ProblemBookmark",
    "ContentImportAudit",
    "Submission",
    "EvaluationRun",
    "TestCaseResult",
    "ConceptEvidenceRecord",
    "ScoreBreakdown",
    "SubmissionFeedback",
    "Course",
    "Classroom",
    "Enrollment",
    "Assignment",
    "AssignmentSubmission",
    "StudentConceptProgress",
    "Plan",
    "PlanLimit",
    "Subscription",
    "BillingEvent",
    "UsageCounter",
    "Invoice",
]
