"""
Problem Library Schemas
Validation and serialization models for problem browsing, detail view,
bookmarks, student submission history, and authorized dataset imports.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class TopicResponse(BaseModel):
    id: str
    name: str
    slug: str


class TestCaseSampleResponse(BaseModel):
    id: str
    input_data: str
    expected_output: str


class ProblemSummaryResponse(BaseModel):
    id: str
    slug: str
    title: str
    difficulty: str
    language: str
    version_number: int
    statement_preview: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    expected_concepts: List[str] = Field(default_factory=list)
    student_status: str = "not_started"  # not_started, attempted, solved
    is_saved: bool = False
    acceptance_rate: Optional[float] = None
    total_submissions: Optional[int] = 0


class PaginatedProblemResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: List[ProblemSummaryResponse]
    difficulty_counts: Dict[str, int] = Field(default_factory=dict)
    status_counts: Dict[str, int] = Field(default_factory=dict)
    available_topics: List[str] = Field(default_factory=list)


class ProblemDetailResponse(BaseModel):
    id: str
    slug: str
    title: str
    statement_markdown: str
    difficulty: str
    language: str
    version_number: int
    constraints_json: Optional[str] = None
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    expected_concepts: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    sample_test_cases: List[TestCaseSampleResponse] = Field(default_factory=list)
    student_status: str = "not_started"
    is_saved: bool = False
    starter_code: Optional[str] = None
    supported_languages: List[str] = Field(default_factory=lambda: ["python", "java", "cpp"])


class BookmarkToggleResponse(BaseModel):
    problem_id: str
    is_saved: bool
    message: str


class ProblemSubmissionHistoryItem(BaseModel):
    id: str
    submission_id: str
    created_at: str
    status: str
    score: float
    passed: bool
    functional_score: Optional[float] = None
    concept_score: Optional[float] = None
    concept_violations: List[str] = Field(default_factory=list)
    code_snippet: Optional[str] = None


class ContentImportTestCase(BaseModel):
    input_data: str
    expected_output: str
    visibility: str = "sample"  # sample, public, hidden
    weight: float = 1.0
    timeout_ms: int = 3000
    memory_limit_mb: int = 128


class ContentImportConceptRule(BaseModel):
    concept: str
    rule_id: str
    accepted_constructs: List[str] = Field(default_factory=list)
    required: bool = True
    min_occurrences: int = 1
    description: str = ""


class ContentImportItem(BaseModel):
    title: str
    slug: Optional[str] = None
    statement_markdown: str
    difficulty: str = "medium"  # easy, medium, hard
    language: str = "python"
    topics: List[str] = Field(default_factory=list)
    expected_concepts: List[str] = Field(default_factory=list)
    constraints: Optional[List[str]] = Field(default_factory=list)
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    starter_code: Optional[str] = None
    reference_solution: Optional[str] = None
    test_cases: List[ContentImportTestCase] = Field(default_factory=list)
    concept_rules: List[ContentImportConceptRule] = Field(default_factory=list)
    functional_weight: float = 60.0
    concept_weight: float = 40.0


class ContentImportRequest(BaseModel):
    source_name: str
    license_type: str  # e.g., "Educational / CC-BY-4.0", "MIT", "Institution Internal"
    provenance_url: Optional[str] = None
    problems: List[ContentImportItem]


class ContentImportReportResponse(BaseModel):
    audit_id: str
    source_name: str
    license_type: str
    total_processed: int
    imported_count: int
    skipped_duplicates: int
    imported_slugs: List[str] = Field(default_factory=list)
    skipped_slugs: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class CsvContentImportRequest(BaseModel):
    source_name: str
    license_type: str
    provenance_url: Optional[str] = None
    csv_content: str


class RunCodeRequest(BaseModel):
    language: str = "python"
    source_code: str
    custom_input: Optional[str] = None

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        norm = (v or "").lower().strip()
        if norm in ("c++", "cpp"):
            return "cpp"
        if norm in ("python", "java"):
            return norm
        raise ValueError(f"Unsupported language '{v}'. Supported languages: python, java, cpp")


class SampleCaseRunResult(BaseModel):
    case_number: int
    case_id: Optional[str] = None
    input_data: str
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None
    passed: bool
    execution_time_ms: float = 0.0
    memory_used_bytes: Optional[int] = None
    stderr: Optional[str] = None
    status: str = "passed"  # passed, wrong_answer, runtime_error, timeout, compilation_error
    failure_explanation: Optional[str] = None


class ConceptCheckItem(BaseModel):
    concept: str
    passed: bool
    message: str


class RunCodeResponse(BaseModel):
    status: str = "accepted"  # accepted, wrong_answer, runtime_error, timeout, syntax_error, compilation_error, concept_not_satisfied
    syntax_valid: bool = True
    syntax_error_message: Optional[str] = None
    compilation_error: bool = False
    compile_output: Optional[str] = None
    all_passed: bool = False
    total_cases: int = 0
    passed_cases: int = 0
    case_results: List[SampleCaseRunResult] = Field(default_factory=list)
    concept_checks: List[ConceptCheckItem] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    intelligent_feedback: Optional[Dict[str, Any]] = None
    learning_hints: Optional[Any] = None


class LanguageOption(BaseModel):
    id: str
    name: str
    monaco_lang: str
    file_extension: str
    version: str
    is_available: bool
    starter_template: str


class LanguagesResponse(BaseModel):
    languages: List[LanguageOption]


class ProgressiveHintItem(BaseModel):
    tier: int
    title: str
    content: str


class ProgressiveHintsResponse(BaseModel):
    problem_id: str
    problem_title: str
    hints: List[ProgressiveHintItem] = Field(default_factory=list)
    tier_1_general: Optional[str] = None
    tier_2_concept: Optional[str] = None
    tier_3_targeted: Optional[str] = None


class CodeWalkthroughStep(BaseModel):
    section: str
    code_snippet: str
    explanation: str


class VerifiedSolutionResponse(BaseModel):
    problem_id: str
    problem_title: str
    language: str
    is_verified: bool
    status: Optional[str] = None  # alias matching verification_status
    verification_status: str  # "verified", "failed_verification", "concept_not_satisfied", "unverified_candidate", "not_available"
    verification_details: Optional[Dict[str, Any]] = None
    verification_results: Optional[Dict[str, Any]] = None
    source_code: Optional[str] = None
    approach_name: Optional[str] = None
    approach_description: Optional[str] = None
    why_it_works: Optional[str] = None
    code_walkthrough: List[CodeWalkthroughStep] = Field(default_factory=list)
    example_trace: Optional[Dict[str, Any]] = None
    time_complexity: Optional[str] = None
    space_complexity: Optional[str] = None
    required_concepts: List[str] = Field(default_factory=list)
    concept_compliance_verified: bool = False
    alternative_approaches: List[str] = Field(default_factory=list)
    explanation: Optional[Dict[str, Any]] = None

