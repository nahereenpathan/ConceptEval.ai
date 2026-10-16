"""
AST Analyzer Module
Coordinates structural parsing and concept extraction against evaluation rubrics.
"""

import ast
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

# Fallback imports or import from evaluation_specifications
try:
    from evaluation_specifications.models import (
        ConceptType,
        RequiredConcept,
        ProhibitedConstruct,
        ConceptEvidence,
        ASTNodeLocation,
    )
except ImportError:
    # If not installed as package, import from relative or local package path
    import sys
    from pathlib import Path
    pkg_path = str(Path(__file__).resolve().parents[5] / "packages" / "evaluation-specifications")
    if pkg_path not in sys.path:
        sys.path.insert(0, pkg_path)
    from evaluation_specifications.models import (
        ConceptType,
        RequiredConcept,
        ProhibitedConstruct,
        ConceptEvidence,
        ASTNodeLocation,
    )

from .visitors import (
    LoopVisitor,
    RecursionVisitor,
    ConditionalVisitor,
    ComprehensionVisitor,
    FunctionDefVisitor,
    ExceptionHandlingVisitor,
    ClassDefVisitor,
    ProhibitedConstructVisitor,
    SliceVisitor,
    DictionaryVisitor,
    SetVisitor,
    StackVisitor,
)


@dataclass
class ParseResult:
    """Represents the outcome of parsing Python code into an AST."""
    is_valid: bool
    tree: Optional[ast.AST] = None
    syntax_error_line: Optional[int] = None
    syntax_error_col: Optional[int] = None
    syntax_error_message: Optional[str] = None


class ASTAnalyzer:
    """Analyzes Python source code against versioned conceptual requirements and prohibitions."""

    @staticmethod
    def parse_source(source_code: str) -> ParseResult:
        """Safely parse Python code into an AST without execution."""
        try:
            tree = ast.parse(source_code)
            return ParseResult(is_valid=True, tree=tree)
        except SyntaxError as exc:
            return ParseResult(
                is_valid=False,
                syntax_error_line=exc.lineno,
                syntax_error_col=exc.offset,
                syntax_error_message=str(exc.msg) if hasattr(exc, "msg") else str(exc),
            )

    @classmethod
    def evaluate_concepts(
        cls,
        source_code: str,
        required_concepts: List[Union[RequiredConcept, str]],
        prohibited_constructs: Optional[List[ProhibitedConstruct]] = None,
        language: str = "python",
    ) -> Tuple[bool, List[ConceptEvidence], Optional[str]]:
        """
        Main evaluation entrypoint supporting Python, Java, and C++.
        Applies language-specific AST analysis without applying Python rules to other languages.
        Returns:
            Tuple: (syntax_valid, list of ConceptEvidence, optional syntax error message)
        """
        norm_lang = (language or "python").lower().strip()
        if norm_lang == "java":
            from .multi_language import JavaASTAnalyzer
            return JavaASTAnalyzer.evaluate(source_code, required_concepts, prohibited_constructs)
        elif norm_lang in ("cpp", "c++"):
            from .multi_language import CppASTAnalyzer
            return CppASTAnalyzer.evaluate(source_code, required_concepts, prohibited_constructs)

        # Standard Python AST evaluation
        parse_res = cls.parse_source(source_code)
        if not parse_res.is_valid:
            return (
                False,
                [],
                f"SyntaxError at line {parse_res.syntax_error_line}, col {parse_res.syntax_error_col}: {parse_res.syntax_error_message}"
            )

        source_lines = source_code.splitlines()
        tree = parse_res.tree
        evidences: List[ConceptEvidence] = []

        # 1. Evaluate Required Concepts
        for req in required_concepts:
            evidence = cls._check_required_concept(tree, source_lines, req)
            evidences.append(evidence)

        # 2. Evaluate Prohibited Constructs
        if prohibited_constructs:
            for proh in prohibited_constructs:
                evidence = cls._check_prohibited_construct(tree, source_lines, proh)
                evidences.append(evidence)

        return (True, evidences, None)

    @classmethod
    def _check_required_concept(
        cls,
        tree: ast.AST,
        source_lines: List[str],
        req: Union[RequiredConcept, str]
    ) -> ConceptEvidence:
        """Inspects the tree for a single required concept."""
        if isinstance(req, str):
            concept_val = req
            accepted = []
            min_occ = 1
            rule_id = f"req_{concept_val}"
            desc = f"Required concept: {concept_val}"
        else:
            concept_val = req.concept.value if hasattr(req.concept, "value") else str(req.concept)
            accepted = [c.lower() for c in req.accepted_constructs] if req.accepted_constructs else []
            min_occ = req.min_occurrences if hasattr(req, "min_occurrences") else 1
            rule_id = req.rule_id if hasattr(req, "rule_id") else f"req_{concept_val}"
            desc = req.description if hasattr(req, "description") else f"Required concept: {concept_val}"

        concept = ConceptType(concept_val) if concept_val in ConceptType._value2member_map_ else concept_val

        matches: List[Dict] = []

        if concept == ConceptType.LOOP:
            visitor = LoopVisitor(source_lines)
            visitor.visit(tree)
            # Filter matches by accepted_constructs if specified (e.g. only 'for' or only 'while')
            if accepted and "loop" not in accepted:
                matches = [m for m in visitor.matches if m["construct"] in accepted]
            else:
                matches = visitor.matches

        elif concept == ConceptType.NESTED_LOOP:
            visitor = LoopVisitor(source_lines)
            visitor.visit(tree)
            matches = [m for m in visitor.matches if m.get("nesting_depth", 1) >= 2]

        elif concept == ConceptType.RECURSION:
            visitor = RecursionVisitor(source_lines)
            visitor.visit(tree)
            matches = visitor.matches

        elif concept == ConceptType.CONDITIONAL:
            visitor = ConditionalVisitor(source_lines)
            visitor.visit(tree)
            if accepted:
                matches = [m for m in visitor.matches if m["construct"] in accepted]
            else:
                matches = visitor.matches

        elif concept == ConceptType.COMPREHENSION:
            visitor = ComprehensionVisitor(source_lines)
            visitor.visit(tree)
            if accepted and "comprehension" not in accepted:
                norm_accepted = []
                for a in accepted:
                    if a in ("listcomp", "list_comp", "list_comprehension"):
                        norm_accepted.append("list_comprehension")
                    elif a in ("dictcomp", "dict_comp", "dict_comprehension"):
                        norm_accepted.append("dict_comprehension")
                    elif a in ("setcomp", "set_comp", "set_comprehension"):
                        norm_accepted.append("set_comprehension")
                    else:
                        norm_accepted.append(a)
                matches = [m for m in visitor.matches if m["construct"] in norm_accepted]
            else:
                matches = visitor.matches

        elif concept == ConceptType.FUNCTION_DEFINITION:
            visitor = FunctionDefVisitor(source_lines)
            visitor.visit(tree)
            if req.target_identifier:
                matches = [m for m in visitor.matches if m.get("function_name") == req.target_identifier]
            else:
                matches = visitor.matches

        elif concept == ConceptType.EXCEPTION_HANDLING:
            visitor = ExceptionHandlingVisitor(source_lines)
            visitor.visit(tree)
            matches = visitor.matches

        elif concept in (ConceptType.WHILE_LOOP, "while_loop"):
            visitor = LoopVisitor(source_lines)
            visitor.visit(tree)
            matches = [m for m in visitor.matches if m["construct"] == "while"]

        elif concept == ConceptType.OOP_CLASS:
            visitor = ClassDefVisitor(source_lines)
            visitor.visit(tree)
            matches = visitor.matches

        elif concept in (ConceptType.SLICING, ConceptType.SLICE, "slicing", "slice"):
            visitor = SliceVisitor(source_lines)
            visitor.visit(tree)
            matches = visitor.matches

        elif concept in (ConceptType.DICTIONARY, "dictionary", "dict", "hash_map"):
            visitor = DictionaryVisitor(source_lines)
            visitor.visit(tree)
            if accepted:
                norm_accepted = [a.lower() for a in accepted]
                matches = [m for m in visitor.matches if m["construct"].lower() in norm_accepted]
            else:
                matches = visitor.matches

        elif concept in (ConceptType.SET, "set", "hash_set"):
            visitor = SetVisitor(source_lines)
            visitor.visit(tree)
            if accepted:
                norm_accepted = [a.lower() for a in accepted]
                matches = [m for m in visitor.matches if m["construct"].lower() in norm_accepted]
            else:
                matches = visitor.matches

        elif concept in (ConceptType.STACK, "stack"):
            visitor = StackVisitor(source_lines)
            visitor.visit(tree)
            matches = visitor.matches

        occurrences = len(matches)
        max_occ = getattr(req, "max_occurrences", None)
        passed = occurrences >= min_occ
        if max_occ is not None and occurrences > max_occ:
            passed = False

        locations = [
            ASTNodeLocation(
                line=m["line"],
                col=m["col"],
                end_line=m.get("end_line"),
                end_col=m.get("end_col"),
                node_type=m["node_type"],
                code_snippet=m.get("snippet"),
            )
            for m in matches
        ]

        concept_label = concept.value if hasattr(concept, "value") else str(concept)
        if passed:
            msg = f"Requirement satisfied: detected {occurrences} occurrence(s) of '{concept_label}'."
        else:
            if occurrences == 0:
                msg = f"Requirement violated: expected at least {min_occ} '{concept_label}' construct(s), but found none."
            elif max_occ is not None and occurrences > max_occ:
                msg = f"Requirement violated: expected at most {max_occ} '{concept_label}' construct(s), but found {occurrences}."
            else:
                msg = f"Requirement violated: expected at least {min_occ} '{concept_label}' construct(s), but only found {occurrences}."

        return ConceptEvidence(
            concept=concept,
            rule_id=rule_id,
            passed=passed,
            occurrences_found=occurrences,
            locations=locations,
            message=msg,
            confidence=1.0,
        )

    @classmethod
    def _check_prohibited_construct(
        cls,
        tree: ast.AST,
        source_lines: List[str],
        proh: Union[ProhibitedConstruct, Dict[str, Any], str]
    ) -> ConceptEvidence:
        """Inspects the tree to ensure no prohibited constructs are present."""
        if isinstance(proh, dict):
            construct_type = str(proh.get("construct_type", ""))
            forbidden_targets = proh.get("forbidden_targets", []) or ([construct_type] if construct_type else [])
            rule_id = str(proh.get("rule_id", "prohibited_construct"))
        elif isinstance(proh, str):
            construct_type = proh
            forbidden_targets = [proh]
            rule_id = f"no_{proh}"
        else:
            construct_type = str(getattr(proh, "construct_type", ""))
            forbidden_targets = getattr(proh, "forbidden_targets", []) or ([construct_type] if construct_type else [])
            rule_id = str(getattr(proh, "rule_id", "prohibited_construct"))

        forbidden_set = set(forbidden_targets)
        visitor = ProhibitedConstructVisitor(source_lines, forbidden_set, construct_type)
        visitor.visit(tree)

        # Also check for construct-level prohibitions like prohibiting loops completely
        if construct_type.lower() in ("loop", "loops"):
            loop_vis = LoopVisitor(source_lines)
            loop_vis.visit(tree)
            for m in loop_vis.matches:
                visitor.matches.append({
                    "construct": "prohibited_loop",
                    "target": m["construct"],
                    "line": m["line"],
                    "col": m["col"],
                    "node_type": m["node_type"],
                    "snippet": m.get("snippet"),
                })

        occurrences = len(visitor.matches)
        passed = (occurrences == 0)

        locations = [
            ASTNodeLocation(
                line=m["line"],
                col=m["col"],
                end_line=m.get("end_line"),
                end_col=m.get("end_col"),
                node_type=m["node_type"],
                code_snippet=m.get("snippet"),
            )
            for m in visitor.matches
        ]

        if passed:
            msg = f"Prohibition verified: no prohibited '{construct_type}' constructs found."
        else:
            targets_found = [m.get("target") for m in visitor.matches]
            msg = f"Prohibition violated: found {occurrences} prohibited construct(s): {targets_found}."

        return ConceptEvidence(
            concept=ConceptType.PROHIBITED_CONSTRUCT,
            rule_id=rule_id,
            passed=passed,
            occurrences_found=occurrences,
            locations=locations,
            message=msg,
            confidence=1.0,
        )

