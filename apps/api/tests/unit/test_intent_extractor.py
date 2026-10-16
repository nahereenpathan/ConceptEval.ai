"""
Unit Tests for NLP Intent Extractor
Verifies extraction of concept requirements, prohibitions, confidence metrics, and rubric drafting.
"""

from app.evaluation.intent.extractor import NLPIntentExtractor
from evaluation_specifications.models import ConceptType


class TestNLPIntentExtractor:
    """Tests NLP rule parsing from problem prompts."""

    def test_extract_loop_requirement(self):
        """Extracts loop requirement from 'Print Hello World 4 times using a loop'."""
        text = "Write a Python script to print Hello World exactly four times using a loop."
        res = NLPIntentExtractor.extract_intent(text)

        assert res.confidence >= 0.80
        assert res.requires_human_review is False
        assert len(res.extracted_concepts) == 1
        assert res.extracted_concepts[0]["concept"] == "loop"

        rubric = res.rubric_draft
        assert len(rubric.required_concepts) == 1
        assert rubric.required_concepts[0].concept == ConceptType.LOOP

    def test_extract_recursion_and_forbidden_loops(self):
        """Extracts recursion requirement and loop prohibition."""
        text = "Compute the factorial of n recursively without using loops."
        res = NLPIntentExtractor.extract_intent(text)

        concepts = [c["concept"] for c in res.extracted_concepts]
        assert "recursion" in concepts

        prohibitions = [p["construct_type"] for p in res.extracted_prohibitions]
        assert "loop" in prohibitions

    def test_ambiguous_text_requires_human_review(self):
        """Purely algorithmic text with no explicit concept flags requires review."""
        text = "Find two numbers in the list that sum to target."
        res = NLPIntentExtractor.extract_intent(text)

        assert res.requires_human_review is True
        assert res.confidence < 0.80
        assert any("No explicit programming concept patterns detected" in note for note in res.review_notes)
