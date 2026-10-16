"""
End-to-End Unit Tests for Evaluation Orchestrator
Verifies the core platform differentiator: distinguishing functionally matching solutions
based on conceptual compliance (e.g. loop requirement vs repeated print statements).
"""

import sys
from pathlib import Path
import pytest

from evaluation_specifications.models import (
    ConceptType,
    RequiredConcept,
    ProhibitedConstruct,
    RubricSchema,
)
from app.evaluation.orchestrator import EvaluationOrchestrator


class TestEvaluationOrchestratorDualTrack:
    """Validates full dual-track assessment (functional correctness + AST concept check)."""

    @pytest.fixture
    def hello_world_problem_setup(self):
        """Standard setup for 'Print Hello World 4 times using a loop'."""
        rubric = RubricSchema(
            schema_version="1.0.0",
            max_score=100.0,
            functional_weight=40.0,
            concept_weight=35.0,
            algorithmic_weight=15.0,
            constraint_weight=10.0,
            required_concepts=[
                RequiredConcept(
                    concept=ConceptType.LOOP,
                    rule_id="rule_loop_hello_world",
                    accepted_constructs=["for", "while"],
                    min_occurrences=1,
                    description="Must use a loop (for or while) to repeat the print statement.",
                )
            ],
            prohibited_constructs=[],
        )

        test_cases = [
            {
                "id": "tc_1",
                "visibility": "sample",
                "input_data": "",
                "expected_output": "Hello World\nHello World\nHello World\nHello World",
                "timeout_ms": 2000,
            }
        ]

        return rubric, test_cases

    def test_compliant_loop_solution_scores_full_points(self, hello_world_problem_setup):
        """Compliant code with loop receives 100/100."""
        rubric, test_cases = hello_world_problem_setup

        compliant_source = """
for i in range(4):
    print("Hello World")
"""

        result = EvaluationOrchestrator.evaluate_submission(
            submission_id="sub_compliant_1",
            source_code=compliant_source,
            rubric=rubric,
            test_cases=test_cases,
        )

        assert result.status == "completed"
        assert result.syntax_valid is True
        assert result.total_score == 100.0

        scores_by_criterion = {c.criterion: c.awarded_points for c in result.criteria_scores}
        assert scores_by_criterion["functional_correctness"] == 40.0
        assert scores_by_criterion["concept_compliance"] == 35.0
        assert scores_by_criterion["algorithmic_logic"] == 15.0
        assert scores_by_criterion["constraints"] == 10.0

        # Check concept evidence
        assert len(result.concept_evidence) == 1
        assert result.concept_evidence[0].passed is True
        assert result.concept_evidence[0].occurrences_found == 1
        assert "Accepted: Full score awarded" in result.summary_feedback

    def test_repeated_print_solution_withholds_concept_points(self, hello_world_problem_setup):
        """Code matching output without loop gets functional points, but 0 concept points."""
        rubric, test_cases = hello_world_problem_setup

        non_compliant_source = """
print("Hello World")
print("Hello World")
print("Hello World")
print("Hello World")
"""

        result = EvaluationOrchestrator.evaluate_submission(
            submission_id="sub_repeated_prints",
            source_code=non_compliant_source,
            rubric=rubric,
            test_cases=test_cases,
        )

        assert result.status == "completed"
        assert result.syntax_valid is True
        # Awarded functional (40) + constraints (10) = 50. Concept (35) and Algorithmic (15) withheld
        assert result.total_score == 50.0

        scores_by_criterion = {c.criterion: c.awarded_points for c in result.criteria_scores}
        assert scores_by_criterion["functional_correctness"] == 40.0
        assert scores_by_criterion["concept_compliance"] == 0.0
        assert scores_by_criterion["algorithmic_logic"] == 0.0
        assert scores_by_criterion["constraints"] == 10.0

        # Check concept evidence explicitly flags failure
        assert len(result.concept_evidence) == 1
        assert result.concept_evidence[0].passed is False
        assert "Requirement violated" in result.concept_evidence[0].message
        assert any("Requirement violated" in s for s in result.actionable_suggestions)

    def test_syntax_error_submission_gets_zero_score(self, hello_world_problem_setup):
        """Syntax error results in 0 score and clear actionable explanation."""
        rubric, test_cases = hello_world_problem_setup

        broken_source = """
for i in range(4)
    print "Missing colon and parentheses"
"""

        result = EvaluationOrchestrator.evaluate_submission(
            submission_id="sub_syntax_err",
            source_code=broken_source,
            rubric=rubric,
            test_cases=test_cases,
        )

        assert result.status == "failed"
        assert result.syntax_valid is False
        assert result.total_score == 0.0
        assert "Syntax Error" in result.summary_feedback
        assert any("Fix the reported SyntaxError" in s for s in result.actionable_suggestions)
