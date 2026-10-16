"""
Unit Tests for Required Concepts Enforcement
Validates that required concepts are strictly and accurately verified across Python, Java, and C++,
ensuring:
1. Solutions producing correct functional output without mandatory concepts do NOT receive concept marks.
2. Comments, strings, and variable names containing keywords do NOT award concept marks.
3. Dead branches (e.g. `if False:`) do NOT award concept marks.
4. Equivalent valid implementations are accepted.
5. All newly supported concepts (while_loop, slicing, dictionary, set, stack) are genuinely enforced.
"""

import pytest
from evaluation_specifications.models import (
    ConceptType,
    RequiredConcept,
    RubricSchema,
    ScoreCriterionResult,
)
from app.evaluation.ast_analysis.analyzer import ASTAnalyzer
from app.evaluation.ast_analysis.multi_language import JavaASTAnalyzer, CppASTAnalyzer
from app.evaluation.scoring.engine import ScoringEngine
from app.evaluation.orchestrator import EvaluationOrchestrator


class TestRequiredConceptsDistinction:
    """Demonstrates that correct output with a missing required concept is strictly distinguished."""

    def test_python_correct_output_missing_required_loop(self):
        """
        Problem: Sum of first N numbers.
        Rubric requires a loop.
        Student uses closed-form math formula n * (n + 1) // 2.
        Functional test passes, but concept marks MUST be 0.
        """
        formula_solution = "n = int(input())\nprint(n * (n + 1) // 2)\n"
        loop_solution = "n = int(input())\ntotal = 0\nfor i in range(1, n + 1):\n    total += i\nprint(total)\n"

        rubric = RubricSchema(
            functional_weight=60.0,
            concept_weight=40.0,
            algorithmic_weight=0.0,
            constraint_weight=0.0,
            required_concepts=[
                RequiredConcept(
                    concept=ConceptType.LOOP,
                    rule_id="rule_loop",
                    accepted_constructs=["for", "while"],
                    min_occurrences=1,
                    description="Requires loop iteration",
                )
            ],
        )

        test_cases = [
            {"id": "tc1", "input_data": "5\n", "expected_output": "15", "visibility": "public"},
            {"id": "tc2", "input_data": "10\n", "expected_output": "55", "visibility": "hidden"},
        ]

        # 1. Evaluate formula solution (omits mandatory concept)
        res_formula = EvaluationOrchestrator.evaluate_submission(
            submission_id="sub_formula",
            source_code=formula_solution,
            rubric=rubric,
            test_cases=test_cases,
            language="python",
        )

        # Both test cases passed output correctness
        assert res_formula.syntax_valid is True
        assert all(tc.status == "passed" for tc in res_formula.test_case_results)
        
        # Concept was violated
        assert any(not ev.passed and ev.concept == ConceptType.LOOP for ev in res_formula.concept_evidence)
        
        # Scoring: Full functional marks (60.0), 0 concept marks (0.0) -> total 60.0
        func_score = next(c for c in res_formula.criteria_scores if c.criterion == "functional_correctness")
        concept_score = next(c for c in res_formula.criteria_scores if c.criterion == "concept_compliance")
        assert func_score.awarded_points == 60.0
        assert func_score.passed is True
        assert concept_score.awarded_points == 0.0
        assert concept_score.passed is False
        assert res_formula.total_score == 60.0
        assert "Requirement violated" in res_formula.actionable_suggestions[0]

        # 2. Evaluate loop solution (satisfies mandatory concept)
        res_loop = EvaluationOrchestrator.evaluate_submission(
            submission_id="sub_loop",
            source_code=loop_solution,
            rubric=rubric,
            test_cases=test_cases,
            language="python",
        )

        assert res_loop.syntax_valid is True
        assert all(tc.status == "passed" for tc in res_loop.test_case_results)
        assert all(ev.passed for ev in res_loop.concept_evidence)
        assert res_loop.total_score == 100.0


    def test_keywords_in_comments_and_strings_never_award_marks(self):
        """Superficial syntax tricks (comments, strings, variable names) must not satisfy concepts."""
        code_with_tricks = (
            "# for i in range(10): while True: recursion()\n"
            "for_loop_var = 'for x in y:'\n"
            "comment_fake = 'while True: pass'\n"
            "n = int(input())\n"
            "print(n * (n + 1) // 2)\n"
        )

        valid, evidences, _ = ASTAnalyzer.evaluate_concepts(
            source_code=code_with_tricks,
            required_concepts=[
                RequiredConcept(concept=ConceptType.LOOP, rule_id="req_loop", min_occurrences=1)
            ],
            language="python",
        )

        assert valid is True
        assert len(evidences) == 1
        assert evidences[0].passed is False
        assert evidences[0].occurrences_found == 0


    def test_dead_branch_loops_do_not_award_marks(self):
        """Loops placed inside unreachable dead branches (e.g. if False:) must be ignored."""
        code_dead_branch = (
            "if False:\n"
            "    for i in range(10):\n"
            "        pass\n"
            "n = int(input())\n"
            "print(n * 2)\n"
        )

        valid, evidences, _ = ASTAnalyzer.evaluate_concepts(
            source_code=code_dead_branch,
            required_concepts=[
                RequiredConcept(concept=ConceptType.LOOP, rule_id="req_loop", min_occurrences=1)
            ],
            language="python",
        )

        assert valid is True
        assert evidences[0].passed is False
        assert evidences[0].occurrences_found == 0


    def test_while_loop_distinction(self):
        """A problem specifying WHILE_LOOP rejects a solution that only uses a FOR loop."""
        for_code = "total = 0\nfor x in range(5):\n    total += x\nprint(total)\n"
        while_code = "total = 0\ni = 0\nwhile i < 5:\n    total += i\n    i += 1\nprint(total)\n"

        req = RequiredConcept(concept=ConceptType.WHILE_LOOP, rule_id="req_while", min_occurrences=1)

        # For loop fails while_loop requirement
        valid_for, ev_for, _ = ASTAnalyzer.evaluate_concepts(for_code, [req], language="python")
        assert valid_for is True
        assert ev_for[0].passed is False
        assert ev_for[0].occurrences_found == 0

        # While loop satisfies while_loop requirement
        valid_while, ev_while, _ = ASTAnalyzer.evaluate_concepts(while_code, [req], language="python")
        assert valid_while is True
        assert ev_while[0].passed is True
        assert ev_while[0].occurrences_found >= 1


    def test_slicing_concept_enforcement(self):
        """Validates SLICING requirement on Python string reversal."""
        slicing_code = "s = input()\nprint(s[::-1])\n"
        loop_code = "s = input()\nrev = ''\nfor ch in s:\n    rev = ch + rev\nprint(rev)\n"

        req = RequiredConcept(concept=ConceptType.SLICING, rule_id="req_slice", min_occurrences=1)

        valid_slice, ev_slice, _ = ASTAnalyzer.evaluate_concepts(slicing_code, [req], language="python")
        assert valid_slice is True
        assert ev_slice[0].passed is True
        assert ev_slice[0].occurrences_found >= 1

        valid_loop, ev_loop, _ = ASTAnalyzer.evaluate_concepts(loop_code, [req], language="python")
        assert valid_loop is True
        assert ev_loop[0].passed is False
        assert ev_loop[0].occurrences_found == 0


    def test_dictionary_concept_enforcement(self):
        """Validates DICTIONARY requirement (two-sum, word frequency)."""
        dict_code = "seen = {}\nfor i, x in enumerate([1, 2, 3]):\n    seen[x] = i\n"
        list_code = "pairs = []\nfor i, x in enumerate([1, 2, 3]):\n    pairs.append((x, i))\n"

        req = RequiredConcept(concept=ConceptType.DICTIONARY, rule_id="req_dict", min_occurrences=1)

        valid_dict, ev_dict, _ = ASTAnalyzer.evaluate_concepts(dict_code, [req], language="python")
        assert valid_dict is True
        assert ev_dict[0].passed is True

        valid_list, ev_list, _ = ASTAnalyzer.evaluate_concepts(list_code, [req], language="python")
        assert valid_list is True
        assert ev_list[0].passed is False


    def test_set_concept_enforcement(self):
        """Validates SET requirement."""
        set_code = "seen = set()\nseen.add(42)\n"
        list_code = "seen = []\nseen.append(42)\n"

        req = RequiredConcept(concept=ConceptType.SET, rule_id="req_set", min_occurrences=1)

        valid_set, ev_set, _ = ASTAnalyzer.evaluate_concepts(set_code, [req], language="python")
        assert valid_set is True
        assert ev_set[0].passed is True

        valid_list, ev_list, _ = ASTAnalyzer.evaluate_concepts(list_code, [req], language="python")
        assert valid_list is True
        assert ev_list[0].passed is False


    def test_stack_concept_enforcement(self):
        """Validates STACK requirement (append and pop)."""
        stack_code = "stack = []\nstack.append('(')\nstack.pop()\n"
        counter_code = "count = 0\ncount += 1\ncount -= 1\n"

        req = RequiredConcept(concept=ConceptType.STACK, rule_id="req_stack", min_occurrences=1)

        valid_stack, ev_stack, _ = ASTAnalyzer.evaluate_concepts(stack_code, [req], language="python")
        assert valid_stack is True
        assert ev_stack[0].passed is True

        valid_counter, ev_counter, _ = ASTAnalyzer.evaluate_concepts(counter_code, [req], language="python")
        assert valid_counter is True
        assert ev_counter[0].passed is False


class TestMultiLanguageConceptEnforcement:
    """Tests that Java and C++ consistently enforce concepts without being fooled by comments."""

    def test_java_loop_and_comment_safety(self):
        valid_java = (
            "public class Solution {\n"
            "    public static void main(String[] args) {\n"
            "        int sum = 0;\n"
            "        for (int i = 0; i < 10; i++) { sum += i; }\n"
            "        System.out.println(sum);\n"
            "    }\n"
            "}\n"
        )
        fake_java = (
            "public class Solution {\n"
            "    public static void main(String[] args) {\n"
            "        // for (int i = 0; i < 10; i++) while (true)\n"
            "        String fake = \"for (int i=0; i<5; i++)\";\n"
            "        System.out.println(45);\n"
            "    }\n"
            "}\n"
        )

        req = RequiredConcept(concept=ConceptType.LOOP, rule_id="req_loop", min_occurrences=1)

        # Real loop satisfies requirement
        _, ev_valid, _ = JavaASTAnalyzer.evaluate(valid_java, [req])
        assert ev_valid[0].passed is True
        assert ev_valid[0].occurrences_found >= 1

        # Comment / string fake fails requirement
        _, ev_fake, _ = JavaASTAnalyzer.evaluate(fake_java, [req])
        assert ev_fake[0].passed is False
        assert ev_fake[0].occurrences_found == 0


    def test_java_nested_loop_distinction(self):
        """Java nested loop requirement rejects a single loop and accepts a nested loop."""
        single_loop = (
            "public class Solution {\n"
            "    public static void main(String[] args) {\n"
            "        for (int i = 0; i < 10; i++) { System.out.println(i); }\n"
            "    }\n"
            "}\n"
        )
        nested_loop = (
            "public class Solution {\n"
            "    public static void main(String[] args) {\n"
            "        for (int i = 0; i < 5; i++) {\n"
            "            for (int j = 0; j < 5; j++) {\n"
            "                System.out.println(i * j);\n"
            "            }\n"
            "        }\n"
            "    }\n"
            "}\n"
        )

        req = RequiredConcept(concept=ConceptType.NESTED_LOOP, rule_id="req_nested", min_occurrences=1)

        _, ev_single, _ = JavaASTAnalyzer.evaluate(single_loop, [req])
        assert ev_single[0].passed is False

        _, ev_nested, _ = JavaASTAnalyzer.evaluate(nested_loop, [req])
        assert ev_nested[0].passed is True


    def test_cpp_loop_and_comment_safety(self):
        valid_cpp = (
            "#include <iostream>\n"
            "int main() {\n"
            "    int sum = 0;\n"
            "    for (int i = 0; i < 10; ++i) { sum += i; }\n"
            "    std::cout << sum << std::endl;\n"
            "    return 0;\n"
            "}\n"
        )
        fake_cpp = (
            "#include <iostream>\n"
            "int main() {\n"
            "    // for (int i = 0; i < 10; i++) while (true)\n"
            "    const char* fake = \"for (int i=0; i<5; i++)\";\n"
            "    std::cout << 45 << std::endl;\n"
            "    return 0;\n"
            "}\n"
        )

        req = RequiredConcept(concept=ConceptType.LOOP, rule_id="req_loop", min_occurrences=1)

        _, ev_valid, _ = CppASTAnalyzer.evaluate(valid_cpp, [req])
        assert ev_valid[0].passed is True

        _, ev_fake, _ = CppASTAnalyzer.evaluate(fake_cpp, [req])
        assert ev_fake[0].passed is False
        assert ev_fake[0].occurrences_found == 0


    def test_cpp_nested_loop_distinction(self):
        """C++ nested loop requirement rejects a single loop and accepts a nested loop."""
        single_loop = (
            "#include <iostream>\n"
            "int main() {\n"
            "    for (int i = 0; i < 10; ++i) { std::cout << i; }\n"
            "    return 0;\n"
            "}\n"
        )
        nested_loop = (
            "#include <iostream>\n"
            "int main() {\n"
            "    for (int i = 0; i < 5; ++i) {\n"
            "        for (int j = 0; j < 5; ++j) {\n"
            "            std::cout << i * j;\n"
            "        }\n"
            "    }\n"
            "    return 0;\n"
            "}\n"
        )

        req = RequiredConcept(concept=ConceptType.NESTED_LOOP, rule_id="req_nested", min_occurrences=1)

        _, ev_single, _ = CppASTAnalyzer.evaluate(single_loop, [req])
        assert ev_single[0].passed is False

        _, ev_nested, _ = CppASTAnalyzer.evaluate(nested_loop, [req])
        assert ev_nested[0].passed is True
