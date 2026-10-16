"""
Evaluation Specifications & Contracts
Defines strictly-typed schemas for concepts, rubrics, evidence, and scores.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ConceptType(str, Enum):
    LOOP = "loop"
    RECURSION = "recursion"
    CONDITIONAL = "conditional"
    COMPREHENSION = "comprehension"
    FUNCTION_DEFINITION = "function_definition"
    EXCEPTION_HANDLING = "exception_handling"
    OOP_CLASS = "oop_class"
    PROHIBITED_CONSTRUCT = "prohibited_construct"
    SPECIFIC_BUILTIN = "specific_builtin"
    NESTED_LOOP = "nested_loop"
    WHILE_LOOP = "while_loop"
    SLICING = "slicing"
    SLICE = "slice"
    DICTIONARY = "dictionary"
    SET = "set"
    STACK = "stack"


class RequiredConcept(BaseModel):
    """Specification of a required programming concept for a problem version."""
    concept: ConceptType
    rule_id: str = Field(description="Unique identifier for this rubric rule")
    accepted_constructs: List[str] = Field(
        default_factory=list,
        description="List of AST constructs accepted (e.g. ['for', 'while'])"
    )
    required: bool = True
    min_occurrences: int = 1
    max_occurrences: Optional[int] = None
    target_identifier: Optional[str] = Field(
        default=None,
        description="Optional function/variable identifier being inspected"
    )
    description: str = Field(
        default="",
        description="Human-readable requirement explanation"
    )

    @field_validator("concept", mode="before")
    @classmethod
    def normalize_concept_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip().lower()
            alias_map = {
                "dict": ConceptType.DICTIONARY,
                "hash_map": ConceptType.DICTIONARY,
                "hashmap": ConceptType.DICTIONARY,
                "hash_set": ConceptType.SET,
                "hashset": ConceptType.SET,
                "slice": ConceptType.SLICING,
                "slicing": ConceptType.SLICING,
                "while": ConceptType.WHILE_LOOP,
            }
            if v_clean in alias_map:
                return alias_map[v_clean]
        return v


class ProhibitedConstruct(BaseModel):
    """Specification of a construct strictly forbidden by the problem statement."""
    rule_id: str
    construct_type: str = Field(
        description="Construct category (e.g. 'builtin_call', 'import', 'loop', 'comprehension')"
    )
    forbidden_targets: List[str] = Field(
        default_factory=list,
        description="Specific functions/modules forbidden (e.g. ['eval', 'exec', 'math.factorial'])"
    )
    description: str = Field(
        default="",
        description="Reason why this construct is prohibited"
    )


class RubricSchema(BaseModel):
    """Versioned grading rubric schema."""
    schema_version: str = "1.0.0"
    max_score: float = Field(default=100.0, ge=1.0)
    functional_weight: float = Field(default=40.0, ge=0.0, le=100.0)
    concept_weight: float = Field(default=35.0, ge=0.0, le=100.0)
    algorithmic_weight: float = Field(default=15.0, ge=0.0, le=100.0)
    constraint_weight: float = Field(default=10.0, ge=0.0, le=100.0)
    
    required_concepts: List[RequiredConcept] = Field(default_factory=list)
    prohibited_constructs: List[ProhibitedConstruct] = Field(default_factory=list)
    allow_partial_concept_credit: bool = True

    @field_validator("constraint_weight")
    @classmethod
    def validate_total_weights(cls, v: float, info) -> float:
        values = info.data
        f = values.get("functional_weight", 0.0)
        c = values.get("concept_weight", 0.0)
        a = values.get("algorithmic_weight", 0.0)
        total = f + c + a + v
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Rubric criteria weights must sum to 100.0 (got {total:.2f})")
        return v


class ASTNodeLocation(BaseModel):
    """Source code location for detected AST constructs."""
    line: int
    col: int
    end_line: Optional[int] = None
    end_col: Optional[int] = None
    node_type: str
    code_snippet: Optional[str] = None


class ConceptEvidence(BaseModel):
    """Machine-readable evidence captured during static AST analysis."""
    concept: ConceptType
    rule_id: str
    passed: bool
    occurrences_found: int = 0
    locations: List[ASTNodeLocation] = Field(default_factory=list)
    message: str
    confidence: float = 1.0


class TestCaseResultPayload(BaseModel):
    """Execution outcome for a single test case."""
    test_case_id: str
    visibility: str  # "sample", "public", "hidden"
    status: str      # "passed", "failed", "timeout", "runtime_error", "memory_limit"
    execution_time_ms: float = 0.0
    memory_used_bytes: int = 0
    actual_output_summary: Optional[str] = None
    expected_output_summary: Optional[str] = None
    error_message: Optional[str] = None


class ScoreCriterionResult(BaseModel):
    """Detailed score for one rubric criterion."""
    criterion: str
    max_points: float
    awarded_points: float
    passed: bool
    reason_code: str
    explanation: str


class EvaluationResultPayload(BaseModel):
    """Consolidated evaluation payload produced by the evaluation orchestrator."""
    submission_id: str
    evaluator_version: str = "1.0.0"
    status: str  # "completed", "failed", "infrastructure_error"
    syntax_valid: bool
    syntax_error_details: Optional[str] = None
    
    total_score: float = Field(ge=0.0, le=100.0)
    criteria_scores: List[ScoreCriterionResult] = Field(default_factory=list)
    concept_evidence: List[ConceptEvidence] = Field(default_factory=list)
    test_case_results: List[TestCaseResultPayload] = Field(default_factory=list)
    
    summary_feedback: str
    actionable_suggestions: List[str] = Field(default_factory=list)
