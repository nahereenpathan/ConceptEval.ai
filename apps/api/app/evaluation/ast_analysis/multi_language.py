"""
Multi-Language AST & Structural Concept Analyzers
Provides specialized, language-specific AST and syntactic concept analysis for:
- Java (JDK structural analysis + javac syntax validation)
- C++ (g++ structural analysis + syntax validation)

Does NOT apply Python AST rules to Java or C++.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from evaluation_specifications.models import (
        ConceptType,
        RequiredConcept,
        ProhibitedConstruct,
        ConceptEvidence,
        ASTNodeLocation,
    )
except ImportError:
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


def remove_comments_and_strings(code: str) -> Tuple[str, List[str]]:
    """
    Strip single-line and multi-line comments and string literals to prevent false positives.
    Returns cleaned code and original source lines.
    """
    lines = code.splitlines()

    def replacer(match):
        s = match.group(0)
        if s.startswith("/"):
            return " " * len(s)  # replace comments with spaces to preserve line offsets
        else:
            return '"' + (" " * (len(s) - 2)) + '"'  # preserve string boundaries

    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE,
    )
    cleaned = re.sub(pattern, replacer, code)
    return cleaned, lines


def find_loops_with_depth(
    cleaned_code: str,
    source_lines: List[str],
    accepted: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Finds loops (for, while, do-while) in C-like syntax (Java, C++) and accurately
    computes loop nesting depth by tracking brace blocks and statement ranges.
    """
    loop_pattern = re.compile(r"\b(for|while|do)\b")
    loop_matches: List[Dict[str, Any]] = []

    for m in loop_pattern.finditer(cleaned_code):
        start_pos = m.start()
        construct = m.group(1)

        # In do ... while, ignore trailing while (...);
        if construct == "while":
            prefix = cleaned_code[:start_pos].rstrip()
            if prefix.endswith("}"):
                last_brace = prefix.rfind("{")
                if last_brace != -1:
                    pre_do = cleaned_code[:last_brace].rstrip()
                    if pre_do.endswith("do") or re.search(r"\bdo\s*$", pre_do):
                        continue

        # Look past header '(' and ')' if present
        body_start = m.end()
        if construct in ("for", "while"):
            open_p = cleaned_code.find("(", start_pos)
            if open_p != -1 and open_p < start_pos + 15:
                p_count = 1
                curr = open_p + 1
                while curr < len(cleaned_code) and p_count > 0:
                    if cleaned_code[curr] == "(":
                        p_count += 1
                    elif cleaned_code[curr] == ")":
                        p_count -= 1
                    curr += 1
                body_start = curr

        after_header = cleaned_code[body_start:].lstrip()
        offset = len(cleaned_code[body_start:]) - len(after_header)
        body_actual_start = body_start + offset

        if after_header.startswith("{"):
            b_count = 1
            curr = body_actual_start + 1
            while curr < len(cleaned_code) and b_count > 0:
                if cleaned_code[curr] == "{":
                    b_count += 1
                elif cleaned_code[curr] == "}":
                    b_count -= 1
                curr += 1
            body_end = curr
        else:
            semi = cleaned_code.find(";", body_actual_start)
            body_end = semi + 1 if semi != -1 else body_actual_start + 80

        line_no = cleaned_code[:start_pos].count("\n") + 1
        snippet = source_lines[line_no - 1].strip() if line_no <= len(source_lines) else ""
        loop_matches.append({
            "construct": construct,
            "start_pos": start_pos,
            "body_start": body_actual_start,
            "body_end": body_end,
            "line": line_no,
            "col": start_pos - (cleaned_code.rfind("\n", 0, start_pos) + 1),
            "snippet": snippet,
        })

    for lm in loop_matches:
        depth = 1
        for other in loop_matches:
            if other is not lm and other["body_start"] <= lm["start_pos"] < other["body_end"]:
                depth += 1
        lm["nesting_depth"] = depth

    if accepted:
        norm_accepted = [a.lower() for a in accepted]
        loop_matches = [m for m in loop_matches if m["construct"] in norm_accepted]

    return loop_matches


class JavaASTAnalyzer:
    """Specialized structural and concept analyzer for Java source code."""

    @classmethod
    def check_syntax(cls, source_code: str) -> Tuple[bool, Optional[str]]:
        """Validate Java syntax using javac if installed."""
        javac_bin = shutil.which("javac")
        if not javac_bin:
            # Fallback basic balance check if javac is unavailable
            return cls._heuristic_syntax_check(source_code)

        # Extract class name
        from runner.languages import extract_java_class_name
        class_name = extract_java_class_name(source_code)

        with tempfile.TemporaryDirectory(prefix="java_syntax_") as tmpdir:
            file_path = Path(tmpdir) / f"{class_name}.java"
            file_path.write_text(source_code, encoding="utf-8")

            try:
                proc = subprocess.run(
                    [javac_bin, "-Xlint:none", "-encoding", "UTF-8", f"{class_name}.java"],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=6.0,
                )
                if proc.returncode != 0:
                    err = proc.stderr or proc.stdout
                    first_err = err.strip().splitlines()[0] if err else "Syntax error in Java code."
                    return False, first_err
                return True, None
            except Exception:
                return cls._heuristic_syntax_check(source_code)

    @classmethod
    def _heuristic_syntax_check(cls, source_code: str) -> Tuple[bool, Optional[str]]:
        """Fallback brace balancing check."""
        open_curlies = source_code.count("{")
        close_curlies = source_code.count("}")
        if open_curlies != close_curlies:
            return False, f"Unbalanced curly braces in Java source: {open_curlies} '{{' vs {close_curlies} '}}'"
        return True, None

    @classmethod
    def evaluate(
        cls,
        source_code: str,
        required_concepts: List[Union[RequiredConcept, str]],
        prohibited_constructs: Optional[List[ProhibitedConstruct]] = None,
    ) -> Tuple[bool, List[ConceptEvidence], Optional[str]]:
        """Evaluate Java source code against concept rules."""
        syntax_valid, syntax_err = cls.check_syntax(source_code)
        if not syntax_valid:
            return False, [], syntax_err

        cleaned_code, source_lines = remove_comments_and_strings(source_code)
        evidences: List[ConceptEvidence] = []

        for req in required_concepts:
            evidences.append(cls._check_required_concept(cleaned_code, source_lines, req))

        if prohibited_constructs:
            for proh in prohibited_constructs:
                evidences.append(cls._check_prohibited_construct(cleaned_code, source_lines, proh))

        return True, evidences, None

    @classmethod
    def _check_required_concept(
        cls,
        cleaned_code: str,
        source_lines: List[str],
        req: Union[RequiredConcept, str],
    ) -> ConceptEvidence:
        if isinstance(req, str):
            concept_val = req
            accepted = []
            min_occ = 1
            rule_id = f"java_req_{concept_val}"
            desc = f"Required concept: {concept_val}"
        else:
            concept_val = req.concept.value if hasattr(req.concept, "value") else str(req.concept)
            accepted = [c.lower() for c in req.accepted_constructs] if req.accepted_constructs else []
            min_occ = req.min_occurrences if hasattr(req, "min_occurrences") else 1
            rule_id = req.rule_id if hasattr(req, "rule_id") else f"java_req_{concept_val}"
            desc = req.description if hasattr(req, "description") else f"Required concept: {concept_val}"

        concept = ConceptType(concept_val) if concept_val in ConceptType._value2member_map_ else concept_val
        locations: List[ASTNodeLocation] = []

        if concept == ConceptType.LOOP:
            loop_matches = find_loops_with_depth(cleaned_code, source_lines, accepted)
            for lm in loop_matches:
                node_name = "ForStatement" if lm["construct"] == "for" else ("WhileStatement" if lm["construct"] == "while" else "DoWhileStatement")
                locations.append(ASTNodeLocation(
                    node_type=node_name,
                    line=lm["line"],
                    col=lm["col"],
                    code_snippet=lm["snippet"],
                ))

        elif concept in (ConceptType.WHILE_LOOP, "while_loop"):
            loop_matches = find_loops_with_depth(cleaned_code, source_lines, ["while", "do"])
            for lm in loop_matches:
                node_name = "WhileStatement" if lm["construct"] == "while" else "DoWhileStatement"
                locations.append(ASTNodeLocation(
                    node_type=node_name,
                    line=lm["line"],
                    col=lm["col"],
                    code_snippet=lm["snippet"],
                ))

        elif concept == ConceptType.NESTED_LOOP:
            loop_matches = find_loops_with_depth(cleaned_code, source_lines, accepted)
            nested = [lm for lm in loop_matches if lm["nesting_depth"] >= 2]
            for lm in nested:
                locations.append(ASTNodeLocation(
                    node_type="NestedLoopStatement",
                    line=lm["line"],
                    col=lm["col"],
                    code_snippet=lm["snippet"],
                ))

        elif concept in (ConceptType.SLICING, ConceptType.SLICE, "slicing", "slice"):
            slice_pattern = re.compile(r"\b(substring|subList|copyOfRange|reverse)\s*\(")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in slice_pattern.finditer(line):
                    snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="StringOrCollectionSlice",
                        line=line_idx,
                        col=m.start(),
                        code_snippet=snippet,
                    ))

        elif concept in (ConceptType.DICTIONARY, "dictionary", "dict", "hash_map"):
            dict_pattern = re.compile(r"\b(Map|HashMap|TreeMap|LinkedHashMap|ConcurrentHashMap)\b|\b\.(put|get|containsKey|putIfAbsent)\s*\(")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in dict_pattern.finditer(line):
                    snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="MapOrDictionary",
                        line=line_idx,
                        col=m.start(),
                        code_snippet=snippet,
                    ))

        elif concept in (ConceptType.SET, "set", "hash_set"):
            set_pattern = re.compile(r"\b(Set|HashSet|TreeSet|LinkedHashSet)\b|\b\.(add|contains|remove)\s*\(")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in set_pattern.finditer(line):
                    snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="SetCollection",
                        line=line_idx,
                        col=m.start(),
                        code_snippet=snippet,
                    ))

        elif concept in (ConceptType.STACK, "stack"):
            stack_pattern = re.compile(r"\b(Stack|Deque|ArrayDeque)\b|\b\.(push|pop|peek)\s*\(")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in stack_pattern.finditer(line):
                    snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="StackOperation",
                        line=line_idx,
                        col=m.start(),
                        code_snippet=snippet,
                    ))

        elif concept == ConceptType.RECURSION:
            # Java method recursion: find methods and check self-invocation
            method_pattern = re.compile(
                r"(?:public|private|protected|static|final|\s)*\s*[\w<>\[\],]+\s+([A-Za-z0-9_]+)\s*\([^)]*\)\s*\{",
                re.MULTILINE,
            )
            for m in method_pattern.finditer(cleaned_code):
                method_name = m.group(1)
                if method_name in ("main", "equals", "hashCode", "toString"):
                    continue

                start_idx = m.end()
                # Find matching closing brace
                brace_count = 1
                curr = start_idx
                while curr < len(cleaned_code) and brace_count > 0:
                    if cleaned_code[curr] == "{":
                        brace_count += 1
                    elif cleaned_code[curr] == "}":
                        brace_count -= 1
                    curr += 1

                method_body = cleaned_code[start_idx:curr]
                # Check for recursive call: method_name(...)
                call_pattern = re.compile(rf"\b{method_name}\s*\(")
                for call_match in call_pattern.finditer(method_body):
                    call_pos = start_idx + call_match.start()
                    line_no = cleaned_code[:call_pos].count("\n") + 1
                    snippet = source_lines[line_no - 1].strip() if line_no <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="MethodInvocation",
                        line=line_no,
                        col=0,
                        code_snippet=snippet,
                    ))

        elif concept == ConceptType.CONDITIONAL:
            cond_pattern = re.compile(r"\b(if|switch)\b\s*\(")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in cond_pattern.finditer(line):
                    snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="IfStatement" if m.group(1) == "if" else "SwitchStatement",
                        line=line_idx,
                        col=m.start(),
                        code_snippet=snippet,
                    ))

        elif concept == ConceptType.OOP_CLASS:
            class_pattern = re.compile(r"\b(class|interface)\s+([A-Za-z0-9_]+)\b")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in class_pattern.finditer(line):
                    snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="ClassDeclaration",
                        line=line_idx,
                        col=m.start(),
                        code_snippet=snippet,
                    ))

        elif concept == ConceptType.EXCEPTION_HANDLING:
            try_pattern = re.compile(r"\b(try|catch)\b\s*(\(|\{)")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in try_pattern.finditer(line):
                    snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="TryCatchBlock",
                        line=line_idx,
                        col=m.start(),
                        code_snippet=snippet,
                    ))

        elif concept == ConceptType.FUNCTION_DEFINITION:
            method_pattern = re.compile(r"(?:public|private|protected|static|\s)*\s*[\w<>\[\]]+\s+([A-Za-z0-9_]+)\s*\([^)]*\)\s*\{")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in method_pattern.finditer(line):
                    if m.group(1) != "main":
                        snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                        locations.append(ASTNodeLocation(
                            node_type="MethodDeclaration",
                            line=line_idx,
                            col=m.start(),
                            code_snippet=snippet,
                        ))

        passed = len(locations) >= min_occ
        msg = f"Java concept '{concept_val}' satisfied ({len(locations)} found)" if passed else f"Missing required Java concept '{concept_val}' (found {len(locations)}, requires {min_occ})"

        return ConceptEvidence(
            concept=concept if isinstance(concept, ConceptType) else ConceptType.LOOP,
            rule_id=rule_id,
            passed=passed,
            occurrences_found=len(locations),
            locations=locations,
            confidence=1.0,
            message=msg,
        )

    @classmethod
    def _check_prohibited_construct(
        cls,
        cleaned_code: str,
        source_lines: List[str],
        proh: Union[ProhibitedConstruct, Dict[str, Any], str],
    ) -> ConceptEvidence:
        if isinstance(proh, dict):
            construct_type = str(proh.get("construct_type", ""))
            targets = proh.get("forbidden_targets") or ([construct_type] if construct_type else [])
            rule_id = str(proh.get("rule_id", "prohibited_construct"))
        elif isinstance(proh, str):
            construct_type = proh
            targets = [proh]
            rule_id = f"no_{proh}"
        else:
            construct_type = str(getattr(proh, "construct_type", ""))
            targets = getattr(proh, "forbidden_targets", None) or ([construct_type] if construct_type else [])
            rule_id = str(getattr(proh, "rule_id", "prohibited_construct"))

        locations: List[ASTNodeLocation] = []

        for target in targets:
            clean_target = re.escape(target)
            pattern = re.compile(rf"\b{clean_target}\b")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in pattern.finditer(line):
                    snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="ProhibitedConstruct",
                        line=line_idx,
                        col=m.start(),
                        code_snippet=snippet,
                    ))

        passed = (len(locations) == 0)
        first_target = targets[0] if targets else construct_type
        msg = f"No prohibited Java constructs detected ({construct_type})" if passed else f"Prohibited Java construct detected: '{first_target}' ({len(locations)} violations)"

        return ConceptEvidence(
            concept=ConceptType.PROHIBITED_CONSTRUCT,
            rule_id=rule_id,
            passed=passed,
            occurrences_found=len(locations),
            locations=locations,
            confidence=1.0,
            message=msg,
        )


class CppASTAnalyzer:
    """Specialized structural and concept analyzer for C++ source code."""

    @classmethod
    def check_syntax(cls, source_code: str) -> Tuple[bool, Optional[str]]:
        """Validate C++ syntax using g++ -fsyntax-only if installed."""
        gpp_bin = shutil.which("g++") or shutil.which("clang++")
        if not gpp_bin:
            return cls._heuristic_syntax_check(source_code)

        with tempfile.TemporaryDirectory(prefix="cpp_syntax_") as tmpdir:
            file_path = Path(tmpdir) / "submission.cpp"
            file_path.write_text(source_code, encoding="utf-8")

            try:
                proc = subprocess.run(
                    [gpp_bin, "-fsyntax-only", "-std=c++17", "submission.cpp"],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=6.0,
                )
                if proc.returncode != 0:
                    err = proc.stderr or proc.stdout
                    first_err = err.strip().splitlines()[0] if err else "Syntax error in C++ code."
                    return False, first_err
                return True, None
            except Exception:
                return cls._heuristic_syntax_check(source_code)

    @classmethod
    def _heuristic_syntax_check(cls, source_code: str) -> Tuple[bool, Optional[str]]:
        """Fallback check for unbalanced braces."""
        open_curlies = source_code.count("{")
        close_curlies = source_code.count("}")
        if open_curlies != close_curlies:
            return False, f"Unbalanced curly braces in C++ source: {open_curlies} '{{' vs {close_curlies} '}}'"
        return True, None

    @classmethod
    def evaluate(
        cls,
        source_code: str,
        required_concepts: List[Union[RequiredConcept, str]],
        prohibited_constructs: Optional[List[ProhibitedConstruct]] = None,
    ) -> Tuple[bool, List[ConceptEvidence], Optional[str]]:
        """Evaluate C++ source code against concept rules."""
        syntax_valid, syntax_err = cls.check_syntax(source_code)
        if not syntax_valid:
            return False, [], syntax_err

        cleaned_code, source_lines = remove_comments_and_strings(source_code)
        evidences: List[ConceptEvidence] = []

        for req in required_concepts:
            evidences.append(cls._check_required_concept(cleaned_code, source_lines, req))

        if prohibited_constructs:
            for proh in prohibited_constructs:
                evidences.append(cls._check_prohibited_construct(cleaned_code, source_lines, proh))

        return True, evidences, None

    @classmethod
    def _check_required_concept(
        cls,
        cleaned_code: str,
        source_lines: List[str],
        req: Union[RequiredConcept, str],
    ) -> ConceptEvidence:
        if isinstance(req, str):
            concept_val = req
            accepted = []
            min_occ = 1
            rule_id = f"cpp_req_{concept_val}"
            desc = f"Required concept: {concept_val}"
        else:
            concept_val = req.concept.value if hasattr(req.concept, "value") else str(req.concept)
            accepted = [c.lower() for c in req.accepted_constructs] if req.accepted_constructs else []
            min_occ = req.min_occurrences if hasattr(req, "min_occurrences") else 1
            rule_id = req.rule_id if hasattr(req, "rule_id") else f"cpp_req_{concept_val}"
            desc = req.description if hasattr(req, "description") else f"Required concept: {concept_val}"

        concept = ConceptType(concept_val) if concept_val in ConceptType._value2member_map_ else concept_val
        locations: List[ASTNodeLocation] = []

        if concept == ConceptType.LOOP:
            loop_matches = find_loops_with_depth(cleaned_code, source_lines, accepted)
            for lm in loop_matches:
                node_name = "ForStatement" if lm["construct"] == "for" else ("WhileStatement" if lm["construct"] == "while" else "DoWhileStatement")
                locations.append(ASTNodeLocation(
                    node_type=node_name,
                    line=lm["line"],
                    col=lm["col"],
                    code_snippet=lm["snippet"],
                ))

        elif concept in (ConceptType.WHILE_LOOP, "while_loop"):
            loop_matches = find_loops_with_depth(cleaned_code, source_lines, ["while", "do"])
            for lm in loop_matches:
                node_name = "WhileStatement" if lm["construct"] == "while" else "DoWhileStatement"
                locations.append(ASTNodeLocation(
                    node_type=node_name,
                    line=lm["line"],
                    col=lm["col"],
                    code_snippet=lm["snippet"],
                ))

        elif concept == ConceptType.NESTED_LOOP:
            loop_matches = find_loops_with_depth(cleaned_code, source_lines, accepted)
            nested = [lm for lm in loop_matches if lm["nesting_depth"] >= 2]
            for lm in nested:
                locations.append(ASTNodeLocation(
                    node_type="NestedLoopStatement",
                    line=lm["line"],
                    col=lm["col"],
                    code_snippet=lm["snippet"],
                ))

        elif concept in (ConceptType.SLICING, ConceptType.SLICE, "slicing", "slice"):
            slice_pattern = re.compile(r"\b(substr|string_view|reverse)\s*\(")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in slice_pattern.finditer(line):
                    snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="SubstringOrSlice",
                        line=line_idx,
                        col=m.start(),
                        code_snippet=snippet,
                    ))

        elif concept in (ConceptType.DICTIONARY, "dictionary", "dict", "hash_map"):
            dict_pattern = re.compile(r"\b(unordered_map|map|unordered_multimap|multimap)\b")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in dict_pattern.finditer(line):
                    snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="MapOrDictionary",
                        line=line_idx,
                        col=m.start(),
                        code_snippet=snippet,
                    ))

        elif concept in (ConceptType.SET, "set", "hash_set"):
            set_pattern = re.compile(r"\b(unordered_set|set|unordered_multiset|multiset)\b")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in set_pattern.finditer(line):
                    snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="SetCollection",
                        line=line_idx,
                        col=m.start(),
                        code_snippet=snippet,
                    ))

        elif concept in (ConceptType.STACK, "stack"):
            stack_pattern = re.compile(r"\b(std::stack|stack<)\b|\b\.(push|pop|push_back|pop_back)\s*\(")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in stack_pattern.finditer(line):
                    snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="StackOperation",
                        line=line_idx,
                        col=m.start(),
                        code_snippet=snippet,
                    ))

        elif concept == ConceptType.RECURSION:
            # C++ function recursion
            func_pattern = re.compile(
                r"(?:inline|static|virtual|\s)*\s*[\w:*&<>]+\s+([A-Za-z0-9_]+)\s*\([^)]*\)\s*\{",
                re.MULTILINE,
            )
            for m in func_pattern.finditer(cleaned_code):
                func_name = m.group(1)
                if func_name in ("main", "operator"):
                    continue

                start_idx = m.end()
                brace_count = 1
                curr = start_idx
                while curr < len(cleaned_code) and brace_count > 0:
                    if cleaned_code[curr] == "{":
                        brace_count += 1
                    elif cleaned_code[curr] == "}":
                        brace_count -= 1
                    curr += 1

                body = cleaned_code[start_idx:curr]
                call_pattern = re.compile(rf"\b{func_name}\s*\(")
                for call_match in call_pattern.finditer(body):
                    call_pos = start_idx + call_match.start()
                    line_no = cleaned_code[:call_pos].count("\n") + 1
                    snippet = source_lines[line_no - 1].strip() if line_no <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="FunctionCall",
                        line=line_no,
                        col=0,
                        code_snippet=snippet,
                    ))

        elif concept == ConceptType.CONDITIONAL:
            cond_pattern = re.compile(r"\b(if|switch)\b\s*\(")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in cond_pattern.finditer(line):
                    snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="IfStatement" if m.group(1) == "if" else "SwitchStatement",
                        line=line_idx,
                        col=m.start(),
                        code_snippet=snippet,
                    ))

        elif concept == ConceptType.OOP_CLASS:
            class_pattern = re.compile(r"\b(class|struct)\s+([A-Za-z0-9_]+)\b")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in class_pattern.finditer(line):
                    snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="ClassOrStructDeclaration",
                        line=line_idx,
                        col=m.start(),
                        code_snippet=snippet,
                    ))

        elif concept == ConceptType.EXCEPTION_HANDLING:
            try_pattern = re.compile(r"\b(try|catch)\b\s*(\(|\{)")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in try_pattern.finditer(line):
                    snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="TryCatchBlock",
                        line=line_idx,
                        col=m.start(),
                        code_snippet=snippet,
                    ))

        elif concept == ConceptType.FUNCTION_DEFINITION:
            func_pattern = re.compile(r"(?:inline|static|\s)*\s*[\w:*&<>]+\s+([A-Za-z0-9_]+)\s*\([^)]*\)\s*\{")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in func_pattern.finditer(line):
                    if m.group(1) != "main":
                        snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                        locations.append(ASTNodeLocation(
                            node_type="FunctionDefinition",
                            line=line_idx,
                            col=m.start(),
                            code_snippet=snippet,
                        ))

        passed = len(locations) >= min_occ
        msg = f"C++ concept '{concept_val}' satisfied ({len(locations)} found)" if passed else f"Missing required C++ concept '{concept_val}' (found {len(locations)}, requires {min_occ})"

        return ConceptEvidence(
            concept=concept if isinstance(concept, ConceptType) else ConceptType.LOOP,
            rule_id=rule_id,
            passed=passed,
            occurrences_found=len(locations),
            locations=locations,
            confidence=1.0,
            message=msg,
        )

    @classmethod
    def _check_prohibited_construct(
        cls,
        cleaned_code: str,
        source_lines: List[str],
        proh: Union[ProhibitedConstruct, Dict[str, Any], str],
    ) -> ConceptEvidence:
        if isinstance(proh, dict):
            construct_type = str(proh.get("construct_type", ""))
            targets = proh.get("forbidden_targets") or ([construct_type] if construct_type else [])
            rule_id = str(proh.get("rule_id", "prohibited_construct"))
        elif isinstance(proh, str):
            construct_type = proh
            targets = [proh]
            rule_id = f"no_{proh}"
        else:
            construct_type = str(getattr(proh, "construct_type", ""))
            targets = getattr(proh, "forbidden_targets", None) or ([construct_type] if construct_type else [])
            rule_id = str(getattr(proh, "rule_id", "prohibited_construct"))

        locations: List[ASTNodeLocation] = []

        for target in targets:
            clean_target = re.escape(target)
            pattern = re.compile(rf"\b{clean_target}\b")
            for line_idx, line in enumerate(cleaned_code.splitlines(), start=1):
                for m in pattern.finditer(line):
                    snippet = source_lines[line_idx - 1].strip() if line_idx <= len(source_lines) else ""
                    locations.append(ASTNodeLocation(
                        node_type="ProhibitedConstruct",
                        line=line_idx,
                        col=m.start(),
                        code_snippet=snippet,
                    ))

        passed = (len(locations) == 0)
        first_target = targets[0] if targets else construct_type
        msg = f"No prohibited C++ constructs detected ({construct_type})" if passed else f"Prohibited C++ construct detected: '{first_target}' ({len(locations)} violations)"

        return ConceptEvidence(
            concept=ConceptType.PROHIBITED_CONSTRUCT,
            rule_id=rule_id,
            passed=passed,
            occurrences_found=len(locations),
            locations=locations,
            confidence=1.0,
            message=msg,
        )

