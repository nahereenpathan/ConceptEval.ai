"""
Scoring Engine
Computes evidence-based, rubric-weighted scores combining AST concept analysis and dynamic test results.
"""

from typing import List, Tuple
from evaluation_specifications.models import (
    RubricSchema,
    ConceptEvidence,
    TestCaseResultPayload,
    ScoreCriterionResult,
)


class ScoringEngine:
    """Calculates deterministic points according to the published versioned rubric."""

    @classmethod
    def calculate_score(
        cls,
        rubric: RubricSchema,
        syntax_valid: bool,
        concept_evidence: List[ConceptEvidence],
        test_case_results: List[TestCaseResultPayload],
    ) -> Tuple[float, List[ScoreCriterionResult], List[str]]:
        """
        Calculates criteria breakdowns and overall score.
        Returns:
            Tuple: (total_score, list of ScoreCriterionResult, actionable_suggestions)
        """
        suggestions: List[str] = []
        criteria_scores: List[ScoreCriterionResult] = []

        # If syntax is completely invalid, functional and concept execution cannot be awarded
        if not syntax_valid:
            criteria_scores.extend([
                ScoreCriterionResult(
                    criterion="functional_correctness",
                    max_points=rubric.functional_weight,
                    awarded_points=0.0,
                    passed=False,
                    reason_code="SYNTAX_ERROR",
                    explanation="Code could not be executed due to a Python SyntaxError.",
                ),
                ScoreCriterionResult(
                    criterion="concept_compliance",
                    max_points=rubric.concept_weight,
                    awarded_points=0.0,
                    passed=False,
                    reason_code="SYNTAX_ERROR",
                    explanation="Concept analysis could not be completed on invalid syntax.",
                ),
                ScoreCriterionResult(
                    criterion="algorithmic_logic",
                    max_points=rubric.algorithmic_weight,
                    awarded_points=0.0,
                    passed=False,
                    reason_code="SYNTAX_ERROR",
                    explanation="Algorithmic logic cannot be evaluated on unparseable code.",
                ),
                ScoreCriterionResult(
                    criterion="constraints",
                    max_points=rubric.constraint_weight,
                    awarded_points=0.0,
                    passed=False,
                    reason_code="SYNTAX_ERROR",
                    explanation="Code must be valid Python syntax to satisfy basic constraints.",
                ),
            ])
            suggestions.append("Fix the reported SyntaxError before testing functionality or concepts.")
            return (0.0, criteria_scores, suggestions)

        # 1. Functional Correctness (Dynamic test cases)
        total_tests = len(test_case_results)
        passed_tests = sum(1 for t in test_case_results if t.status == "passed")
        failed_tests = total_tests - passed_tests

        if total_tests > 0:
            func_fraction = passed_tests / total_tests
            func_points = round(func_fraction * rubric.functional_weight, 2)
            func_passed = (passed_tests == total_tests)
        else:
            func_points = rubric.functional_weight
            func_passed = True

        if not func_passed:
            suggestions.append(f"Your code passed {passed_tests} of {total_tests} test cases. Review test feedback for mismatches.")

        criteria_scores.append(
            ScoreCriterionResult(
                criterion="functional_correctness",
                max_points=rubric.functional_weight,
                awarded_points=func_points,
                passed=func_passed,
                reason_code="ALL_TESTS_PASSED" if func_passed else "SOME_TESTS_FAILED",
                explanation=f"Passed {passed_tests}/{total_tests} test cases.",
            )
        )

        # 2. Concept Compliance (AST evidence for required concepts)
        required_evidences = [
            e for e in concept_evidence
            if e.concept.value != "prohibited_construct"
        ]

        if required_evidences:
            req_passed_count = sum(1 for e in required_evidences if e.passed)
            req_total = len(required_evidences)

            if rubric.allow_partial_concept_credit:
                concept_points = round((req_passed_count / req_total) * rubric.concept_weight, 2)
            else:
                concept_points = rubric.concept_weight if req_passed_count == req_total else 0.0

            concept_passed = (req_passed_count == req_total)

            for e in required_evidences:
                if not e.passed:
                    suggestions.append(e.message)
        else:
            concept_points = rubric.concept_weight
            concept_passed = True

        criteria_scores.append(
            ScoreCriterionResult(
                criterion="concept_compliance",
                max_points=rubric.concept_weight,
                awarded_points=concept_points,
                passed=concept_passed,
                reason_code="CONCEPTS_SATISFIED" if concept_passed else "CONCEPTS_VIOLATED",
                explanation=(
                    "All required programming concepts were identified."
                    if concept_passed
                    else "One or more required programming concepts were missing or insufficient."
                ),
            )
        )

        # 3. Constraints & Prohibited Constructs
        prohibited_evidences = [
            e for e in concept_evidence
            if e.concept.value == "prohibited_construct"
        ]
        proh_violation_count = sum(1 for e in prohibited_evidences if not e.passed)
        has_timeout = any(t.status == "timeout" for t in test_case_results)

        constraints_passed = (proh_violation_count == 0) and not has_timeout
        if constraints_passed:
            constraint_points = rubric.constraint_weight
            constraint_explanation = "No forbidden constructs detected; execution within constraints."
        else:
            constraint_points = 0.0
            reasons = []
            if proh_violation_count > 0:
                reasons.append("Prohibited constructs were detected")
                for e in prohibited_evidences:
                    if not e.passed:
                        suggestions.append(e.message)
            if has_timeout:
                reasons.append("Execution exceeded the allocated time limit")
                suggestions.append("Optimize time complexity to prevent execution timeout.")
            constraint_explanation = "; ".join(reasons)

        criteria_scores.append(
            ScoreCriterionResult(
                criterion="constraints",
                max_points=rubric.constraint_weight,
                awarded_points=constraint_points,
                passed=constraints_passed,
                reason_code="CONSTRAINTS_MET" if constraints_passed else "CONSTRAINTS_VIOLATED",
                explanation=constraint_explanation,
            )
        )

        # 4. Algorithmic Logic
        # Algorithmic points awarded if both functional correctness is substantial (>= 75%) and required concepts met
        if func_passed and concept_passed and constraints_passed:
            algo_points = rubric.algorithmic_weight
            algo_passed = True
            algo_explanation = "Sound algorithmic implementation adhering to all requirements."
        elif (func_points / rubric.functional_weight if rubric.functional_weight else 1.0) >= 0.5 and concept_passed:
            algo_points = round(0.5 * rubric.algorithmic_weight, 2)
            algo_passed = False
            algo_explanation = "Concept used, but logic or edge cases need refinement."
        else:
            algo_points = 0.0
            algo_passed = False
            algo_explanation = "Algorithmic logic requirements not satisfied."

        criteria_scores.append(
            ScoreCriterionResult(
                criterion="algorithmic_logic",
                max_points=rubric.algorithmic_weight,
                awarded_points=algo_points,
                passed=algo_passed,
                reason_code="LOGIC_VERIFIED" if algo_passed else "LOGIC_IMPERFECT",
                explanation=algo_explanation,
            )
        )

        # Sum total score
        total_score = round(sum(c.awarded_points for c in criteria_scores), 2)
        total_score = max(0.0, min(total_score, rubric.max_score))

        if total_score == rubric.max_score:
            suggestions.append("Excellent solution! Correct output and full conceptual compliance achieved.")

        return (total_score, criteria_scores, suggestions)
