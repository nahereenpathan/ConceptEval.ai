"""
NLP Intent Extraction Engine
Analyzes natural-language problem statements to extract required concepts,
forbidden patterns, and draft grading rubrics under human review workflows.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from evaluation_specifications.models import (
    ConceptType,
    RequiredConcept,
    ProhibitedConstruct,
    RubricSchema,
)


class IntentExtractionResult:
    """Outcome of parsing a problem description for conceptual requirements."""
    def __init__(
        self,
        rubric_draft: RubricSchema,
        extracted_concepts: List[Dict[str, Any]],
        extracted_prohibitions: List[Dict[str, Any]],
        confidence: float,
        requires_human_review: bool,
        review_notes: List[str],
    ):
        self.rubric_draft = rubric_draft
        self.extracted_concepts = extracted_concepts
        self.extracted_prohibitions = extracted_prohibitions
        self.confidence = confidence
        self.requires_human_review = requires_human_review
        self.review_notes = review_notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rubric_draft": self.rubric_draft.model_dump(),
            "extracted_concepts": self.extracted_concepts,
            "extracted_prohibitions": self.extracted_prohibitions,
            "confidence": self.confidence,
            "requires_human_review": self.requires_human_review,
            "review_notes": self.review_notes,
        }


class NLPIntentExtractor:
    """Extracts pedagogical constraints from problem statements using controlled NLP rules."""

    # Controlled phrase patterns for required concepts
    CONCEPT_PATTERNS = [
        (
            ConceptType.LOOP,
            r"\b(using (a |the )?(loop|for loop|while loop)|iterate|iteration|looping|through each)\b",
            ["for", "while"],
            "Requires iterative execution using a loop (for or while).",
        ),
        (
            ConceptType.RECURSION,
            r"\b(recursive(ly)?|recursion|call(s)? itself|without (using )?loops?)\b",
            ["recursion"],
            "Requires recursive algorithmic implementation.",
        ),
        (
            ConceptType.COMPREHENSION,
            r"\b(list comprehension|dict(ionary)? comprehension|set comprehension)\b",
            ["list_comprehension", "dict_comprehension", "set_comprehension"],
            "Requires Python comprehension syntax.",
        ),
        (
            ConceptType.CONDITIONAL,
            r"\b(using (if|conditional)|branching|case|condition)\b",
            ["if", "ternary", "match"],
            "Requires conditional branching logic.",
        ),
        (
            ConceptType.EXCEPTION_HANDLING,
            r"\b(try[- ]except|exception handling|raise error|catch)\b",
            ["try_except"],
            "Requires exception handling with try/except.",
        ),
        (
            ConceptType.OOP_CLASS,
            r"\b(class|object[- ]oriented|oop|encapsulat(e|ion)|method)\b",
            ["class_def"],
            "Requires object-oriented class definition.",
        ),
    ]

    # Prohibited constructs patterns
    PROHIBITED_PATTERNS = [
        (
            "loop",
            r"\b(without (using )?loops?|do not use (a )?loop|no loops? allowed)\b",
            ["for", "while"],
            "Loops are prohibited for this problem.",
        ),
        (
            "builtin_call",
            r"\b(do not use|without (using )?built-?in|avoid|prohibit(ed)?) (eval|exec|compile|help)\b",
            ["eval", "exec", "compile", "help"],
            "Dynamic execution built-ins are strictly prohibited.",
        ),
        (
            "import",
            r"\b(without (any )?imports?|do not import|standard library only|no external libraries)\b",
            ["os", "sys", "subprocess"],
            "Low-level system and process imports are prohibited.",
        ),
    ]

    @classmethod
    def extract_intent(cls, problem_text: str) -> IntentExtractionResult:
        """
        Parses problem markdown or statement and constructs a draft RubricSchema.
        """
        cleaned_text = problem_text.lower()
        extracted_concepts: List[Dict[str, Any]] = []
        required_concepts: List[RequiredConcept] = []
        extracted_prohibitions: List[Dict[str, Any]] = []
        prohibited_constructs: List[ProhibitedConstruct] = []
        review_notes: List[str] = []

        confidence = 0.95

        # 1. Check for required concepts
        for concept_type, pattern, constructs, desc in cls.CONCEPT_PATTERNS:
            match = re.search(pattern, cleaned_text, re.IGNORECASE)
            if match:
                rule_id = f"rule_{concept_type.value}"
                req = RequiredConcept(
                    concept=concept_type,
                    rule_id=rule_id,
                    accepted_constructs=constructs,
                    required=True,
                    min_occurrences=1,
                    description=desc,
                )
                required_concepts.append(req)
                extracted_concepts.append({
                    "concept": concept_type.value,
                    "matched_phrase": match.group(0),
                    "accepted_constructs": constructs,
                    "rule_id": rule_id,
                })

        # 2. Check for prohibited constructs
        for construct_type, pattern, targets, desc in cls.PROHIBITED_PATTERNS:
            match = re.search(pattern, cleaned_text, re.IGNORECASE)
            if match:
                rule_id = f"proh_{construct_type}"
                proh = ProhibitedConstruct(
                    rule_id=rule_id,
                    construct_type=construct_type,
                    forbidden_targets=targets,
                    description=desc,
                )
                prohibited_constructs.append(proh)
                extracted_prohibitions.append({
                    "construct_type": construct_type,
                    "matched_phrase": match.group(0),
                    "forbidden_targets": targets,
                    "rule_id": rule_id,
                })

        # Check for ambiguity
        if not required_concepts and not prohibited_constructs:
            confidence = 0.50
            review_notes.append("No explicit programming concept patterns detected. Problem may be purely functional.")
        elif any(c["concept"] == "loop" for c in extracted_concepts) and any(p["construct_type"] == "loop" for p in extracted_prohibitions):
            confidence = 0.30
            review_notes.append("Conflict detected: Statement mentions both loop requirement and loop prohibition.")

        requires_human_review = confidence < 0.80 or len(review_notes) > 0

        # Construct balanced draft rubric (always sums to 100.0)
        if required_concepts:
            f_w, c_w, a_w, k_w = 40.0, 35.0, 15.0, 10.0
        else:
            f_w, c_w, a_w, k_w = 50.0, 0.0, 30.0, 20.0

        rubric_draft = RubricSchema(
            schema_version="1.0.0",
            max_score=100.0,
            functional_weight=f_w,
            concept_weight=c_w,
            algorithmic_weight=a_w,
            constraint_weight=k_w,
            required_concepts=required_concepts,
            prohibited_constructs=prohibited_constructs,
            allow_partial_concept_credit=True,
        )

        return IntentExtractionResult(
            rubric_draft=rubric_draft,
            extracted_concepts=extracted_concepts,
            extracted_prohibitions=extracted_prohibitions,
            confidence=confidence,
            requires_human_review=requires_human_review,
            review_notes=review_notes,
        )
