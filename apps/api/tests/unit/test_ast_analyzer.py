"""
Unit Tests for AST Analysis & Concept Detection Engine
Validates structural concept extraction, rule enforcement, and prohibition detection.
"""

import pytest
from evaluation_specifications.models import (
    ConceptType,
    RequiredConcept,
    ProhibitedConstruct,
)
from app.evaluation.ast_analysis.analyzer import ASTAnalyzer


class TestASTConceptEvaluation:
    """Tests evaluating Python code solutions for conceptual requirements."""

    def test_loop_requirement_satisfied_with_for_loop(self):
        """Solution with 'for' loop satisfies loop concept."""
        source_code = """
for i in range(4):
    print("Hello World")
"""
        req = RequiredConcept(
            concept=ConceptType.LOOP,
            rule_id="rule_require_loop",
            accepted_constructs=["for", "while"],
            required=True,
            min_occurrences=1,
        )

        valid, evidences, err = ASTAnalyzer.evaluate_concepts(source_code, [req])
        assert valid is True
        assert err is None
        assert len(evidences) == 1
        ev = evidences[0]
        assert ev.passed is True
        assert ev.occurrences_found == 1
        assert ev.locations[0].node_type == "For"
        assert ev.locations[0].line == 2

    def test_loop_requirement_violated_by_repeated_prints(self):
        """Solution matching output without loop fails concept requirement."""
        source_code = """
print("Hello World")
print("Hello World")
print("Hello World")
print("Hello World")
"""
        req = RequiredConcept(
            concept=ConceptType.LOOP,
            rule_id="rule_require_loop",
            accepted_constructs=["for", "while"],
            required=True,
            min_occurrences=1,
        )

        valid, evidences, err = ASTAnalyzer.evaluate_concepts(source_code, [req])
        assert valid is True
        assert err is None
        assert len(evidences) == 1
        ev = evidences[0]
        assert ev.passed is False
        assert ev.occurrences_found == 0
        assert "Requirement violated" in ev.message

    def test_loop_requirement_satisfied_with_while_loop(self):
        """Solution with 'while' loop satisfies loop concept when while is accepted."""
        source_code = """
count = 0
while count < 4:
    print("Hello World")
    count += 1
"""
        req = RequiredConcept(
            concept=ConceptType.LOOP,
            rule_id="rule_require_loop",
            accepted_constructs=["for", "while"],
            min_occurrences=1,
        )

        valid, evidences, _ = ASTAnalyzer.evaluate_concepts(source_code, [req])
        assert valid is True
        assert evidences[0].passed is True
        assert evidences[0].locations[0].node_type == "While"

    def test_strict_for_loop_rejects_while_loop(self):
        """If rubric strictly requires 'for' loop, a 'while' loop must fail."""
        source_code = """
i = 0
while i < 10:
    i += 1
"""
        req = RequiredConcept(
            concept=ConceptType.LOOP,
            rule_id="rule_for_loop_only",
            accepted_constructs=["for"],  # Only 'for' allowed
            min_occurrences=1,
        )

        valid, evidences, _ = ASTAnalyzer.evaluate_concepts(source_code, [req])
        assert valid is True
        assert evidences[0].passed is False
        assert evidences[0].occurrences_found == 0

    def test_recursion_detection(self):
        """Detects direct recursive function calls."""
        source_code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        req = RequiredConcept(
            concept=ConceptType.RECURSION,
            rule_id="rule_require_recursion",
            min_occurrences=1,
        )

        valid, evidences, _ = ASTAnalyzer.evaluate_concepts(source_code, [req])
        assert valid is True
        ev = evidences[0]
        assert ev.passed is True
        assert ev.occurrences_found == 1
        assert ev.locations[0].node_type == "FunctionDef"

    def test_comprehension_detection(self):
        """Detects list comprehensions."""
        source_code = """
squares = [x**2 for x in range(10) if x % 2 == 0]
"""
        req = RequiredConcept(
            concept=ConceptType.COMPREHENSION,
            rule_id="rule_require_listcomp",
            accepted_constructs=["list_comprehension"],
            min_occurrences=1,
        )

        valid, evidences, _ = ASTAnalyzer.evaluate_concepts(source_code, [req])
        assert valid is True
        assert evidences[0].passed is True
        assert evidences[0].locations[0].node_type == "ListComp"

    def test_prohibited_builtins_detection(self):
        """Detects usage of prohibited built-ins like eval or exec."""
        source_code = """
code = "print(42)"
eval(code)
"""
        proh = ProhibitedConstruct(
            rule_id="proh_no_eval",
            construct_type="builtin_call",
            forbidden_targets=["eval", "exec"],
            description="Arbitrary code execution functions are forbidden.",
        )

        valid, evidences, _ = ASTAnalyzer.evaluate_concepts(source_code, [], [proh])
        assert valid is True
        assert len(evidences) == 1
        assert evidences[0].passed is False
        assert "Prohibition violated" in evidences[0].message
        assert evidences[0].locations[0].node_type == "Call"

    def test_prohibited_module_imports(self):
        """Detects prohibited imports such as 'os' or 'sys'."""
        source_code = """
import os
print(os.getcwd())
"""
        proh = ProhibitedConstruct(
            rule_id="proh_no_os",
            construct_type="import",
            forbidden_targets=["os"],
            description="Direct OS access is forbidden.",
        )

        valid, evidences, _ = ASTAnalyzer.evaluate_concepts(source_code, [], [proh])
        assert valid is True
        assert evidences[0].passed is False
        assert evidences[0].locations[0].node_type == "Import"

    def test_syntax_error_handling(self):
        """Invalid Python syntax returns syntax_valid=False with line and error details."""
        source_code = """
for i in range(4)
    print("Missing colon")
"""
        req = RequiredConcept(
            concept=ConceptType.LOOP,
            rule_id="rule_require_loop",
        )

        valid, evidences, err = ASTAnalyzer.evaluate_concepts(source_code, [req])
        assert valid is False
        assert len(evidences) == 0
        assert "SyntaxError at line 2" in err

    def test_dead_code_loop_ignored(self):
        """Loops placed inside obviously dead/unreachable branches (if False:) are not counted."""
        source_code = """
if False:
    for i in range(4):
        pass
print("Hello World")
"""
        req = RequiredConcept(
            concept=ConceptType.LOOP,
            rule_id="rule_require_loop",
            accepted_constructs=["for", "while"],
            min_occurrences=1,
        )

        valid, evidences, err = ASTAnalyzer.evaluate_concepts(source_code, [req])
        assert valid is True
        assert evidences[0].passed is False
        assert evidences[0].occurrences_found == 0
