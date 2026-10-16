"""
Intelligent Code Feedback & Explanation Engine
Produces evidence-based diagnostics, sanitized compiler/runtime explanations,
and progressive learning hints based on real execution outcomes and problem rubrics.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


class IntelligentExplainer:
    """Generates actionable educational explanations for code failures and progressive hints."""

    @classmethod
    def explain_run_failure(
        cls,
        language: str,
        source_code: str,
        status: str,
        compile_output: Optional[str] = None,
        syntax_error: Optional[str] = None,
        case_results: Optional[List[Dict[str, Any]]] = None,
        concept_checks: Optional[List[Dict[str, Any]]] = None,
        problem_title: str = "",
        problem_statement: str = "",
    ) -> Dict[str, Any]:
        """
        Produces detailed diagnostic feedback for Run Code or Submit Solution failures.
        """
        norm_lang = (language or "python").lower().strip()
        if norm_lang in ("c++", "cpp"):
            norm_lang = "cpp"

        # 1. Compilation or Syntax Error
        if status in ("compilation_error", "syntax_error") or compile_output or syntax_error:
            raw_err = compile_output or syntax_error or "Unknown compilation error"
            sanitized = cls._sanitize_compiler_output(raw_err)
            explanation = cls._diagnose_compiler_error(norm_lang, sanitized)
            return {
                "category": "compilation_error",
                "headline": f"Compilation Error in {norm_lang.capitalize()} code",
                "summary": f"Compilation Error in {norm_lang.capitalize()} code",
                "detailed_explanation": explanation,
                "diagnostic_details": explanation,
                "sanitized_diagnostic": sanitized,
                "compiler_sanitized": sanitized,
                "actionable_suggestion": "Review the compiler diagnostic above. Check line numbers, semicolons, brackets, and type declarations.",
                "actionable_recommendation": "Review the compiler diagnostic above. Check line numbers, semicolons, brackets, and type declarations.",
            }

        # 2. Concept Not Satisfied (Functional tests passed, but AST concept missing)
        violated_concepts = []
        if concept_checks:
            for cc in concept_checks:
                passed = cc.get("passed", False) if isinstance(cc, dict) else getattr(cc, "passed", False)
                concept = cc.get("concept", "") if isinstance(cc, dict) else getattr(cc, "concept", "")
                msg = cc.get("message", "") if isinstance(cc, dict) else getattr(cc, "message", "")
                if not passed:
                    violated_concepts.append((concept, msg))

        if status == "concept_not_satisfied" or (violated_concepts and status == "accepted"):
            first_concept, first_msg = violated_concepts[0]
            explanation = cls._diagnose_concept_violation(norm_lang, first_concept)
            return {
                "category": "concept_violation",
                "headline": f"Concept Requirement Not Satisfied: '{first_concept}'",
                "summary": f"Concept Requirement Not Satisfied: '{first_concept}'",
                "detailed_explanation": explanation,
                "diagnostic_details": explanation,
                "sanitized_diagnostic": first_msg,
                "concept_guidance": f"Problem requires {first_concept}: {first_msg}",
                "actionable_suggestion": f"Refactor your solution to use the required '{first_concept}' construct. Output alone is not sufficient.",
                "actionable_recommendation": f"Refactor your solution to use the required '{first_concept}' construct. Output alone is not sufficient.",
            }

        # 3. Timeout / Time Limit Exceeded
        if status in ("timeout", "time_limit_exceeded"):
            return {
                "category": "timeout",
                "headline": "Time Limit Exceeded (Timeout)",
                "summary": "Time Limit Exceeded (Timeout)",
                "detailed_explanation": (
                    "Your program exceeded the allocated execution time limit (3.0 seconds). "
                    "This usually happens when there is an infinite loop (e.g. `while True:` without a break condition, "
                    "or loop counter not incrementing), deep recursion without a proper base case, or an algorithm with too high complexity."
                ),
                "diagnostic_details": "Execution timed out after 3.0s limit.",
                "sanitized_diagnostic": "Execution exceeded maximum allowed time limit (3000 ms).",
                "actionable_suggestion": "Check while loop termination conditions and ensure loop variables are properly updated on every iteration.",
                "actionable_recommendation": "Check while loop termination conditions and ensure loop variables are properly updated on every iteration.",
            }

        # 4. Runtime Error
        failed_cases = [c for c in (case_results or []) if (c.get("status") if isinstance(c, dict) else getattr(c, "status", "")) in ("runtime_error", "failed")]
        runtime_cases = [c for c in (case_results or []) if (c.get("status") if isinstance(c, dict) else getattr(c, "status", "")) == "runtime_error"]
        
        if status == "runtime_error" or runtime_cases:
            target_case = runtime_cases[0] if runtime_cases else failed_cases[0]
            stderr_text = target_case.get("stderr") if isinstance(target_case, dict) else getattr(target_case, "stderr", None)
            sanitized = cls._sanitize_compiler_output(stderr_text or "Process exited with non-zero status.")
            explanation = cls._diagnose_runtime_error(norm_lang, sanitized)
            return {
                "category": "runtime_error",
                "headline": "Runtime Error during execution",
                "summary": "Runtime Error during execution",
                "detailed_explanation": explanation,
                "diagnostic_details": explanation,
                "sanitized_diagnostic": sanitized,
                "runtime_sanitized": sanitized,
                "actionable_suggestion": "Inspect array bounds, division by zero, null pointer access, or invalid input type conversions.",
                "actionable_recommendation": "Inspect array bounds, division by zero, null pointer access, or invalid input type conversions.",
            }

        # 5. Wrong Answer (Output Mismatch)
        wrong_cases = [c for c in (case_results or []) if not (c.get("passed") if isinstance(c, dict) else getattr(c, "passed", True))]
        if wrong_cases:
            first_wrong = wrong_cases[0]
            expected = first_wrong.get("expected_output") if isinstance(first_wrong, dict) else getattr(first_wrong, "expected_output", "")
            actual = first_wrong.get("actual_output") if isinstance(first_wrong, dict) else getattr(first_wrong, "actual_output", "")
            diff_analysis = cls._analyze_output_difference(expected or "", actual or "")
            return {
                "category": "wrong_answer",
                "headline": "Output Mismatch (Wrong Answer)",
                "summary": "Output Mismatch (Wrong Answer)",
                "detailed_explanation": diff_analysis,
                "diagnostic_details": diff_analysis,
                "sanitized_diagnostic": f"Expected: {repr(expected[:100])} vs Actual: {repr(actual[:100])}",
                "actionable_suggestion": "Compare your actual output carefully with the expected sample format and verify edge case values.",
                "actionable_recommendation": "Compare your actual output carefully with the expected sample format and verify edge case values.",
            }

        # Default healthy
        return {
            "category": "accepted",
            "headline": "Accepted: Full Correctness & Concept Compliance",
            "summary": "Accepted: Full Correctness & Concept Compliance",
            "detailed_explanation": "All test cases passed output correctness, and required programming concepts were satisfied.",
            "diagnostic_details": "All test cases passed output correctness, and required programming concepts were satisfied.",
            "sanitized_diagnostic": None,
            "actionable_suggestion": None,
            "actionable_recommendation": None,
        }


    @classmethod
    def _sanitize_compiler_output(cls, raw: str) -> str:
        """Strips local filesystem paths and internal temporary directory noise."""
        if not raw:
            return ""
        # Remove paths like C:\Users\...\tmp\... or /tmp/...
        cleaned = re.sub(r"[A-Za-z]:\\[\w\\\.-]+\\", "", raw)
        cleaned = re.sub(r"/(?:tmp|var|home)/[\w/\.-]+/", "", cleaned)
        return cleaned.strip()

    @classmethod
    def _diagnose_compiler_error(cls, lang: str, err: str) -> str:
        """Explains common compiler diagnostics in educational, student-friendly terms."""
        lower = err.lower()
        if "syntaxerror" in lower or "syntax error" in lower:
            if "expected ':'" in lower:
                return "Python SyntaxError: A colon ':' was expected at the end of a header line (e.g. `def ...:`, `for ...:`, `if ...:`, `while ...:`)."
            if "indentationerror" in lower:
                return "Python IndentationError: Inconsistent indentation detected. Make sure all block bodies are uniformly indented (typically 4 spaces)."
            if "invalid syntax" in lower:
                return "Python SyntaxError: The code has a syntax mistake such as unmatched parentheses, misplaced operators, or invalid variable naming."
            return "Syntax error in code. Check line numbers indicated in the trace."

        if lang == "java":
            if "';' expected" in lower:
                return "Java Compiler Error: Missing semicolon ';' at the end of a statement."
            if "cannot find symbol" in lower:
                return "Java Compiler Error: 'Cannot find symbol' means a variable, method, or class name was referenced without being declared or imported in scope."
            if "incompatible types" in lower:
                return "Java Compiler Error: 'Incompatible types' indicates trying to assign or pass a value of one type to a variable of an incompatible type."
            if "missing return statement" in lower:
                return "Java Compiler Error: A non-void method must return a value along every execution path."
            if "reached end of file while parsing" in lower:
                return "Java Compiler Error: Missing closing curly brace '}' before the end of the file."

        if lang == "cpp":
            if "expected ';'" in lower:
                return "C++ Compiler Error: Missing semicolon ';' before a statement or closing brace."
            if "was not declared in this scope" in lower:
                return "C++ Compiler Error: An identifier was used without being declared. Ensure required headers are included (e.g. `#include <iostream>`, `#include <vector>`) or check namespace scoping."
            if "no matching function for call" in lower:
                return "C++ Compiler Error: Argument types passed to a function do not match any available function overload."
            if "expected '}'" in lower:
                return "C++ Compiler Error: Missing closing brace '}'."

        return f"Compiler error occurred while compiling your {lang.capitalize()} program. Inspect the diagnostic line number for details."

    @classmethod
    def _diagnose_runtime_error(cls, lang: str, err: str) -> str:
        """Explains runtime exceptions and fault signals."""
        lower = err.lower()
        if "indexerror" in lower or "arrayindexoutofboundsexception" in lower or "out_of_range" in lower:
            return (
                "Index Out of Bounds: Your code tried to read or write an index beyond the boundaries of an array/list. "
                "Check loop boundary conditions (e.g. using `< len` rather than `<= len`), or check if list is empty."
            )
        if "zerodivisionerror" in lower or "by zero" in lower or "arithmeticexception" in lower:
            return (
                "Division by Zero: An arithmetic operation attempted to divide or modulo by zero. "
                "Check that the divisor variable is not zero before performing division."
            )
        if "keyerror" in lower or "nosuchelementexception" in lower:
            return (
                "Key / Element Not Found: Attempted to look up a key in a dictionary/map that does not exist. "
                "Check key existence with `if key in dict:` or use default access methods."
            )
        if "nullpointerexception" in lower or "null_pointer" in lower:
            return (
                "Null Pointer Exception: Your code tried to call a method or access an attribute on an object reference that was null. "
                "Ensure variables are properly initialized before accessing their fields."
            )
        if "recursionerror" in lower or "stackoverflowerror" in lower:
            return (
                "Stack Overflow / Maximum Recursion Exceeded: The recursive calls went too deep without stopping. "
                "Check your base case condition to make sure the recursion safely terminates."
            )
        if "segmentation fault" in lower or "sigsegv" in lower:
            return (
                "Segmentation Fault (SIGSEGV): The program attempted to access an invalid memory address. "
                "This typically happens from accessing an out-of-bounds array element or dereferencing an invalid pointer."
            )
        if "valueerror" in lower or "numberformatexception" in lower:
            return (
                "Number Format / Value Error: Could not convert a string input into a number. "
                "Check if the input has extra whitespace or blank lines before parsing."
            )

        return "Runtime exception occurred while running the program. Check input boundary cases and initialization."

    @classmethod
    def _analyze_output_difference(cls, expected: str, actual: str) -> str:
        """Compares expected and actual outputs and identifies the nature of the difference."""
        exp_clean = expected.strip()
        act_clean = actual.strip()

        if not act_clean:
            return "No output was produced by your program. Make sure your solution outputs to stdout (e.g. print/println/cout)."

        if exp_clean.lower() == act_clean.lower() and exp_clean != act_clean:
            return f"Casing mismatch: your output differs only in uppercase/lowercase (Expected '{exp_clean}', got '{act_clean}')."

        # Check numerical difference
        try:
            exp_num = int(exp_clean)
            act_num = int(act_clean)
            diff = act_num - exp_num
            if abs(diff) == 1:
                direction = "higher" if diff > 0 else "lower"
                return f"Off-by-one error: Your output ({act_num}) is 1 {direction} than expected ({exp_num}). Check your loop starting or ending boundary."
            return f"Numerical difference: Expected {exp_num}, but your code returned {act_num}."
        except ValueError:
            pass

        # Check line count difference
        exp_lines = exp_clean.splitlines()
        act_lines = act_clean.splitlines()
        if len(exp_lines) != len(act_lines):
            return f"Line count mismatch: Expected {len(exp_lines)} line(s) of output, but your code produced {len(act_lines)} line(s)."

        # Compare first mismatched line
        for i, (el, al) in enumerate(zip(exp_lines, act_lines), 1):
            if el.strip() != al.strip():
                if el.replace(" ", "") == al.replace(" ", ""):
                    return f"Spacing format mismatch on line {i}: values match, but space separation differs."
                return f"Mismatch on line {i}: Expected '{el.strip()[:60]}', but your code produced '{al.strip()[:60]}'."

        return "Output format or content did not match the expected result for this test case."

    @classmethod
    def _diagnose_concept_violation(cls, lang: str, concept: str) -> str:
        """Explains why a specific concept violation occurred and how to fix it."""
        norm_concept = concept.lower()
        if "loop" in norm_concept or norm_concept == "while_loop":
            if "while" in norm_concept:
                return (
                    "This problem requires an iterative while loop (e.g. `while condition:`). "
                    "A closed-form formula, hardcoded response, or for-loop alone does not satisfy this requirement."
                )
            return (
                "This problem requires an iterative loop construct (`for` or `while`). "
                "Solutions that use closed-form mathematical formulas or hardcoded lookups without iterative loops are withheld concept points."
            )
        if "recursion" in norm_concept:
            return (
                "This problem requires a recursive function implementation (a function that invokes itself). "
                "Iterative loops or external libraries do not satisfy the recursive concept requirement."
            )
        if "nested_loop" in norm_concept:
            return (
                "This problem requires nested loops (a loop inside another loop with nesting depth >= 2). "
                "A single linear loop or 1D scan is insufficient for multi-dimensional operations."
            )
        if "comprehension" in norm_concept:
            return (
                "This problem requires Python comprehension syntax (e.g. `[x for x in ...]`). "
                "Standard for loops or manual list appending do not satisfy the comprehension requirement."
            )
        if "dictionary" in norm_concept or "dict" in norm_concept:
            return (
                "This problem requires a dictionary or hash map data structure (e.g. `{}` in Python, `HashMap` in Java, `unordered_map` in C++) "
                "for O(1) average lookup times."
            )
        if "set" in norm_concept:
            return (
                "This problem requires a set collection data structure (e.g. `set()` in Python, `HashSet` in Java, `unordered_set` in C++) "
                "for constant-time membership tracking."
            )
        if "stack" in norm_concept:
            return (
                "This problem requires a stack data structure with push/pop operations to manage nested or LIFO state."
            )
        if "slicing" in norm_concept or "slice" in norm_concept:
            return (
                "This problem requires string or sequence slicing notation (e.g. `[::-1]` in Python, `substring()` in Java, `substr()` in C++)."
            )
        if "oop_class" in norm_concept:
            return (
                "This problem requires defining an object-oriented class (e.g. `class Node:`)."
            )

        return f"This problem requires using the '{concept}' programming construct as specified in the rubric."

    @classmethod
    def generate_progressive_hints(
        cls,
        problem_title: str,
        problem_statement: str,
        expected_concepts: List[str],
        status: Optional[str] = None,
        failure_category: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Generates 3 progressive learning hints:
        1. General Direction (High-level algorithm/approach)
        2. Concept & Data Structure (Specific construct to use)
        3. Tactical Guidance (Specific edge cases and implementation fix)
        """
        title_lower = problem_title.lower()
        stmt_lower = problem_statement.lower()
        concepts_str = ", ".join(expected_concepts) if expected_concepts else "standard constructs"

        # Tier 1: General Strategy
        if "binary search" in title_lower or "binary search" in stmt_lower:
            tier1 = "Consider dividing the search space in half at each step. Track the lower and upper bounds of your search range."
            tier2 = "Use boundary pointers (`low` and `high`) inside a while loop (`while low <= high:`). Compute the midpoint and adjust pointers based on comparisons."
            tier3 = "Be careful with integer overflow when computing `mid = low + (high - low) // 2`. Ensure you return -1 if the target is not found."
        elif "recursion" in title_lower or "recursive" in stmt_lower or "recursion" in expected_concepts:
            tier1 = "Break the problem down into a smaller subproblem of the exact same structure until you reach a trivial base case."
            tier2 = "Define a recursive function with two parts: (1) Base case returning immediately for small inputs (e.g. N <= 1), and (2) Recursive case calling the function with N - 1."
            tier3 = "Double check your base case condition. Without an explicit base case, the function will call itself indefinitely and cause a RecursionError."
        elif "dynamic programming" in title_lower or "dp" in title_lower or "stairs" in title_lower or "coin" in title_lower:
            tier1 = "Notice that the solution for size N depends on optimal answers to smaller subproblems (optimal substructure)."
            tier2 = "Build a dynamic programming table or use variables to store previous results, accumulating them inside a loop."
            tier3 = "Verify your base cases (e.g. dp[0], dp[1]) before starting the loop from index 2 up to N."
        elif "stack" in title_lower or "parentheses" in title_lower or "stack" in expected_concepts:
            tier1 = "Think about matching pairs in Last-In, First-Out (LIFO) order. When you see an opening symbol, remember it until you find its matching close."
            tier2 = "Push opening brackets onto a stack. When encountering a closing bracket, pop the top element and verify it matches."
            tier3 = "Watch out for edge cases: what if the stack is empty when a closing bracket arrives, or what if opening brackets remain on the stack at the end?"
        elif "hash map" in title_lower or "two sum" in title_lower or "dictionary" in expected_concepts:
            tier1 = "Instead of searching through the entire array with an inner loop (O(N^2)), consider storing past elements for O(1) instant lookup."
            tier2 = "Use a dictionary/hash map mapping each value to its index. On each number X, check if target - X is already in your dictionary."
            tier3 = "Make sure you check for the complement in the dictionary BEFORE or AFTER inserting the current number so you don't use the same element twice."
        elif "slicing" in title_lower or "reverse words" in title_lower or "slicing" in expected_concepts:
            tier1 = "Think about Python sequence step parameters or built-in subrange extraction."
            tier2 = "Use slice step notation `[::-1]` to reverse a sequence in a single concise operation."
            tier3 = "Ensure you don't print extra trailing newlines or spaces when reversing."
        elif "comprehension" in title_lower or "comprehension" in expected_concepts:
            tier1 = "Look for a way to transform and filter elements in a single declarative expression."
            tier2 = "Use list comprehension syntax: `[expression for item in iterable if condition]`."
            tier3 = "Ensure your filtering condition uses modulo `% 2 == 0` for even numbers."
        elif "hash set" in title_lower or "duplicates" in title_lower or "set" in expected_concepts:
            tier1 = "Track items you have already encountered to detect if any item appears more than once."
            tier2 = "Initialize an empty set `seen = set()`. For each element, if it's already in `seen`, you found a duplicate; otherwise add it."
            tier3 = "A set lookup `x in seen` runs in O(1) average time, making your entire duplicate check O(N) linear time."
        else:
            tier1 = f"Read the problem constraints carefully. The expected algorithmic approach involves {concepts_str}."
            tier2 = f"Structure your logic to explicitly utilize the required concept: '{expected_concepts[0] if expected_concepts else 'loop'}'. Avoid shortcuts that omit it."
            tier3 = "Test with boundary cases: empty input, smallest possible N, largest constraint value, and negative inputs if applicable."

        # Adjust Tier 3 if there is an active failure category
        if failure_category == "concept_violation":
            tier3 = f"Your code produces correct outputs on tests, but was withheld marks because it omits '{expected_concepts[0] if expected_concepts else 'the required construct'}'. Refactor to satisfy the concept."
        elif failure_category == "compilation_error":
            tier3 = "Fix the reported syntax or compiler errors first. Look at the line number mentioned in the diagnostic message."
        elif failure_category == "timeout":
            tier3 = "Your loop is not terminating. Check the loop condition variable and ensure it makes progress towards the exit condition on every iteration."

        return [
            {
                "tier": 1,
                "title": "Hint 1: General Direction",
                "content": tier1,
            },
            {
                "tier": 2,
                "title": "Hint 2: Concept & Algorithm",
                "content": tier2,
            },
            {
                "tier": 3,
                "title": "Hint 3: Targeted Guidance",
                "content": tier3,
            },
        ]

    @classmethod
    def generate_progressive_hints_payload(
        cls,
        problem_title: str,
        problem_statement: str,
        expected_concepts: List[str],
        status: Optional[str] = None,
        failure_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Returns hints as a dictionary containing both flat keys and list."""
        hints_list = cls.generate_progressive_hints(
            problem_title=problem_title,
            problem_statement=problem_statement,
            expected_concepts=expected_concepts,
            status=status,
            failure_category=failure_category,
        )
        return {
            "hints": hints_list,
            "tier_1_general": hints_list[0]["content"],
            "tier_2_concept": hints_list[1]["content"],
            "tier_3_targeted": hints_list[2]["content"],
        }

