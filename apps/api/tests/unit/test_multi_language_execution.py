"""
Tests for multi-language execution and AST analysis support in ConceptEval.ai:
- Real compilation & execution of Python, Java (JDK), and C++ (g++)
- Successful execution against test cases with stdin/stdout
- Compilation errors with diagnostic compiler messages
- Runtime errors (exceptions / crashes)
- Timeouts (infinite loops)
- Language-specific AST analysis (loop detection, recursion, prohibited constructs)
"""

import pytest
from runner.languages import LanguageDetector
from runner.protocol import ExecutionJob
from runner.subprocess_runner import SubprocessRunner
from app.evaluation.ast_analysis.analyzer import ASTAnalyzer
from evaluation_specifications.models import (
    ConceptType,
    RequiredConcept,
    RubricSchema,
    ProhibitedConstruct,
)
from app.evaluation.orchestrator import EvaluationOrchestrator


class TestLanguageDetector:
    """Verifies that installed compilers (Python, Java, C++) are detected accurately."""

    def test_detector_finds_supported_languages(self):
        detector = LanguageDetector()
        specs = detector.get_all_languages()

        ids = [s["id"] for s in specs]
        assert "python" in ids
        assert "java" in ids
        assert "cpp" in ids

        py_spec = next(s for s in specs if s["id"] == "python")
        java_spec = next(s for s in specs if s["id"] == "java")
        cpp_spec = next(s for s in specs if s["id"] == "cpp")

        assert py_spec["is_available"] is True
        # Java JDK and MinGW g++ installed on host
        assert java_spec["is_available"] is True
        assert cpp_spec["is_available"] is True

        assert "25" in str(java_spec["version"])
        assert "6.3.0" in str(cpp_spec["version"])
        assert java_spec["requires_compilation"] is True
        assert cpp_spec["requires_compilation"] is True
        assert py_spec["requires_compilation"] is False


class TestSubprocessRunnerMultiLanguage:
    """Tests real execution, compilation, errors, and timeouts using SubprocessRunner."""

    def test_python_real_execution(self):
        runner = SubprocessRunner()
        job = ExecutionJob(
            job_id="test_py_1",
            source_code="import sys\nfor line in sys.stdin:\n    print(int(line.strip()) * 2)\n",
            language="python",
            stdin_input="7\n",
            timeout_seconds=5.0,
        )
        res = runner.run(job)
        assert res.exit_code == 0
        assert res.stdout.strip() == "14"
        assert res.compilation_error is False

    def test_java_real_execution_success(self):
        runner = SubprocessRunner()
        java_code = """
import java.util.Scanner;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        while (sc.hasNextInt()) {
            int val = sc.nextInt();
            System.out.println(val * 3);
        }
    }
}
"""
        job = ExecutionJob(
            job_id="test_java_success",
            source_code=java_code,
            language="java",
            stdin_input="9\n",
            timeout_seconds=10.0,
        )
        res = runner.run(job)
        assert res.exit_code == 0
        assert res.stdout.strip() == "27"
        assert res.compilation_error is False

    def test_java_compilation_error(self):
        runner = SubprocessRunner()
        bad_java = """
public class Solution {
    public static void main(String[] args) {
        System.out.println("Missing semicolon")
    }
}
"""
        job = ExecutionJob(
            job_id="test_java_compile_err",
            source_code=bad_java,
            language="java",
            stdin_input="",
            timeout_seconds=10.0,
        )
        res = runner.run(job)
        assert res.compilation_error is True
        assert res.error_type == "COMPILATION_ERROR"
        assert "error: ';' expected" in (res.compile_output or res.stderr)

    def test_java_runtime_error(self):
        runner = SubprocessRunner()
        runtime_err_java = """
public class Solution {
    public static void main(String[] args) {
        int a = 10;
        int b = 0;
        System.out.println(a / b);
    }
}
"""
        job = ExecutionJob(
            job_id="test_java_runtime_err",
            source_code=runtime_err_java,
            language="java",
            stdin_input="",
            timeout_seconds=10.0,
        )
        res = runner.run(job)
        assert res.compilation_error is False
        assert res.exit_code != 0
        assert "ArithmeticException" in res.stderr

    def test_java_timeout(self):
        runner = SubprocessRunner()
        inf_java = """
public class Solution {
    public static void main(String[] args) {
        while (true) {
        }
    }
}
"""
        job = ExecutionJob(
            job_id="test_java_timeout",
            source_code=inf_java,
            language="java",
            stdin_input="",
            timeout_seconds=2.0,
        )
        res = runner.run(job)
        assert res.timed_out is True
        assert res.error_type == "TIMEOUT"

    def test_cpp_real_execution_success(self):
        runner = SubprocessRunner()
        cpp_code = """
#include <iostream>

using namespace std;

int main() {
    int x;
    while (cin >> x) {
        cout << (x + 10) << endl;
    }
    return 0;
}
"""
        job = ExecutionJob(
            job_id="test_cpp_success",
            source_code=cpp_code,
            language="cpp",
            stdin_input="42\n",
            timeout_seconds=10.0,
        )
        res = runner.run(job)
        assert res.exit_code == 0
        assert res.stdout.strip() == "52"
        assert res.compilation_error is False

    def test_cpp_compilation_error(self):
        runner = SubprocessRunner()
        bad_cpp = """
#include <iostream>

int main() {
    this_is_an_undeclared_identifier_error
    return 0;
}
"""
        job = ExecutionJob(
            job_id="test_cpp_compile_err",
            source_code=bad_cpp,
            language="cpp",
            stdin_input="",
            timeout_seconds=10.0,
        )
        res = runner.run(job)
        assert res.compilation_error is True
        assert res.error_type == "COMPILATION_ERROR"
        assert "undeclared" in (res.compile_output or res.stderr).lower()

    def test_cpp_runtime_error(self):
        runner = SubprocessRunner()
        crash_cpp = """
#include <cstdlib>

int main() {
    abort();
}
"""
        job = ExecutionJob(
            job_id="test_cpp_runtime_err",
            source_code=crash_cpp,
            language="cpp",
            stdin_input="",
            timeout_seconds=10.0,
        )
        res = runner.run(job)
        assert res.compilation_error is False
        assert res.exit_code != 0

    def test_cpp_timeout(self):
        runner = SubprocessRunner()
        inf_cpp = """
int main() {
    while (1) {}
    return 0;
}
"""
        job = ExecutionJob(
            job_id="test_cpp_timeout",
            source_code=inf_cpp,
            language="cpp",
            stdin_input="",
            timeout_seconds=2.0,
        )
        res = runner.run(job)
        assert res.timed_out is True
        assert res.error_type == "TIMEOUT"


class TestLanguageSpecificASTAnalyzers:
    """Verifies that Python, Java, and C++ AST rules operate independently and accurately."""

    def test_python_ast_loop_and_recursion(self):
        analyzer = ASTAnalyzer()

        # Python loop
        py_loop = "for i in range(10):\n    print(i)\n"
        valid, evidences, err = analyzer.evaluate_concepts(
            source_code=py_loop,
            language="python",
            required_concepts=[
                RequiredConcept(
                    rule_id="r_loop",
                    concept=ConceptType.LOOP,
                    accepted_constructs=["for", "while"],
                    description="Use loop",
                )
            ],
        )
        assert valid is True
        assert evidences[0].passed is True

        # Python recursion
        py_rec = "def fact(n):\n    if n <= 1: return 1\n    return n * fact(n - 1)\n"
        valid, evidences, err = analyzer.evaluate_concepts(
            source_code=py_rec,
            language="python",
            required_concepts=[
                RequiredConcept(
                    rule_id="r_rec",
                    concept=ConceptType.RECURSION,
                    description="Use recursion",
                )
            ],
        )
        assert valid is True
        assert evidences[0].passed is True

    def test_java_ast_loop_and_recursion(self):
        analyzer = ASTAnalyzer()

        # Java code with loop
        java_loop = """
public class Solution {
    public static void main(String[] args) {
        for (int i = 0; i < 10; i++) {
            System.out.println(i);
        }
    }
}
"""
        valid, evidences, err = analyzer.evaluate_concepts(
            source_code=java_loop,
            language="java",
            required_concepts=[
                RequiredConcept(
                    rule_id="r_java_loop",
                    concept=ConceptType.LOOP,
                    accepted_constructs=["for", "while"],
                    description="Use loop",
                )
            ],
        )
        assert valid is True
        assert evidences[0].passed is True
        assert "loop" in evidences[0].message.lower()
        assert evidences[0].locations[0].node_type == "ForStatement"

        # Java code without loop (concept violation)
        java_no_loop = """
public class Solution {
    public static void main(String[] args) {
        System.out.println("Hello");
    }
}
"""
        valid, evidences, err = analyzer.evaluate_concepts(
            source_code=java_no_loop,
            language="java",
            required_concepts=[
                RequiredConcept(
                    rule_id="r_java_loop",
                    concept=ConceptType.LOOP,
                    accepted_constructs=["for", "while"],
                    description="Use loop",
                )
            ],
        )
        assert valid is True
        assert evidences[0].passed is False

        # Java recursion
        java_rec = """
public class Solution {
    public static long factorial(int n) {
        if (n <= 1) return 1;
        return n * factorial(n - 1);
    }
}
"""
        valid, evidences, err = analyzer.evaluate_concepts(
            source_code=java_rec,
            language="java",
            required_concepts=[
                RequiredConcept(
                    rule_id="r_java_rec",
                    concept=ConceptType.RECURSION,
                    description="Use recursion",
                )
            ],
        )
        assert valid is True
        assert evidences[0].passed is True
        assert "recursion" in evidences[0].message.lower()
        assert "factorial" in evidences[0].locations[0].code_snippet

    def test_cpp_ast_loop_and_recursion(self):
        analyzer = ASTAnalyzer()

        # C++ loop
        cpp_loop = """
#include <iostream>
int main() {
    for (int i = 0; i < 5; ++i) {
        std::cout << i << std::endl;
    }
    return 0;
}
"""
        valid, evidences, err = analyzer.evaluate_concepts(
            source_code=cpp_loop,
            language="cpp",
            required_concepts=[
                RequiredConcept(
                    rule_id="r_cpp_loop",
                    concept=ConceptType.LOOP,
                    accepted_constructs=["for", "while"],
                    description="Use loop",
                )
            ],
        )
        assert valid is True
        assert evidences[0].passed is True
        assert "loop" in evidences[0].message.lower()
        assert evidences[0].locations[0].node_type == "ForStatement"

        # C++ recursion
        cpp_rec = """
long long solve(int n) {
    if (n <= 1) return 1;
    return n * solve(n - 1);
}
"""
        valid, evidences, err = analyzer.evaluate_concepts(
            source_code=cpp_rec,
            language="cpp",
            required_concepts=[
                RequiredConcept(
                    rule_id="r_cpp_rec",
                    concept=ConceptType.RECURSION,
                    description="Use recursion",
                )
            ],
        )
        assert valid is True
        assert evidences[0].passed is True
        assert "recursion" in evidences[0].message.lower()
        assert "solve" in evidences[0].locations[0].code_snippet


class TestOrchestratorMultiLanguageEvaluation:
    """Verifies end-to-end evaluation with test cases, AST grading, and compilation failure handling."""

    def test_java_full_evaluation_accepted(self):
        rubric = RubricSchema(
            schema_version="1.0.0",
            max_score=100.0,
            functional_weight=60.0,
            concept_weight=40.0,
            algorithmic_weight=0.0,
            constraint_weight=0.0,
            required_concepts=[
                RequiredConcept(
                    rule_id="r_loop",
                    concept=ConceptType.LOOP,
                    accepted_constructs=["for", "while"],
                    description="Must use loop",
                )
            ],
        )

        test_cases = [
            {"id": "tc_1", "visibility": "sample", "input_data": "2\n", "expected_output": "4", "timeout_ms": 3000},
            {"id": "tc_2", "visibility": "hidden", "input_data": "5\n", "expected_output": "10", "timeout_ms": 3000},
        ]

        java_solution = """
import java.util.Scanner;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        while (sc.hasNextInt()) {
            int n = sc.nextInt();
            int ans = 0;
            for (int i = 0; i < n; i++) {
                ans += 2;
            }
            System.out.println(ans);
        }
    }
}
"""
        res = EvaluationOrchestrator.evaluate_submission(
            submission_id="sub_java_full_1",
            source_code=java_solution,
            rubric=rubric,
            test_cases=test_cases,
            evaluator_version="1.0",
            language="java",
        )

        assert res.status == "completed"
        assert res.total_score == 100.0
        assert res.syntax_valid is True
        assert all(tc.status == "passed" for tc in res.test_case_results)
        assert any(ce.passed and ce.concept == ConceptType.LOOP for ce in res.concept_evidence)

    def test_cpp_full_evaluation_compilation_error_zero_score(self):
        rubric = RubricSchema(
            schema_version="1.0.0",
            max_score=100.0,
            functional_weight=60.0,
            concept_weight=40.0,
            algorithmic_weight=0.0,
            constraint_weight=0.0,
            required_concepts=[],
        )

        test_cases = [
            {"id": "tc_1", "visibility": "sample", "input_data": "1\n", "expected_output": "1", "timeout_ms": 3000},
            {"id": "tc_2", "visibility": "hidden", "input_data": "2\n", "expected_output": "2", "timeout_ms": 3000},
        ]

        bad_cpp = """
#include <iostream>
int main() {
    std::cout << UndefinedVar << std::endl
    return 0;
}
"""
        res = EvaluationOrchestrator.evaluate_submission(
            submission_id="sub_cpp_compile_fail",
            source_code=bad_cpp,
            rubric=rubric,
            test_cases=test_cases,
            evaluator_version="1.0",
            language="cpp",
        )

        assert res.status == "failed"
        assert res.total_score == 0.0
        assert "Syntax Error" in res.summary_feedback or "Compilation Error" in res.summary_feedback
