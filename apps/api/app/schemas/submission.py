"""
Submission and Evaluation Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SubmissionCreateRequest(BaseModel):
    problem_id: str
    problem_version_number: int = 1
    language: str = "python"
    source_code: str = Field(min_length=1, max_length=65536)
    idempotency_key: Optional[str] = None


class CriterionScoreResponse(BaseModel):
    criterion: str
    max_points: float
    awarded_points: float
    passed: bool
    reason_code: str
    explanation: str


class ConceptEvidenceResponse(BaseModel):
    concept: str
    rule_id: str
    passed: bool
    occurrences_found: int
    message: str


class TestCaseSummaryResponse(BaseModel):
    test_case_id: str
    visibility: str
    status: str
    execution_time_ms: float
    actual_output_summary: Optional[str] = None
    expected_output_summary: Optional[str] = None
    error_message: Optional[str] = None


class SubmissionResponse(BaseModel):
    id: str
    user_id: str
    problem_id: str
    status: str
    language: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    total_score: Optional[float] = None
    syntax_valid: Optional[bool] = None
    summary_feedback: Optional[str] = None
    criteria_scores: List[CriterionScoreResponse] = Field(default_factory=list)
    concept_evidence: List[ConceptEvidenceResponse] = Field(default_factory=list)
    test_case_results: List[TestCaseSummaryResponse] = Field(default_factory=list)
    actionable_suggestions: List[str] = Field(default_factory=list)
