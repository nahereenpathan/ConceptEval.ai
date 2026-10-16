"""
Evaluation Orchestrator
Coordinates static AST analysis, sandboxed execution across test cases,
and scoring calculations to produce reproducible, evidence-based results.
"""

from typing import Any, Dict, List, Optional
from evaluation_specifications.models import (
    RubricSchema,
    EvaluationResultPayload,
    TestCaseResultPayload,
)

from app.evaluation.ast_analysis.analyzer import ASTAnalyzer
from app.evaluation.scoring.engine import ScoringEngine

# Execution runner integration
import sys
from pathlib import Path
runner_path = str(Path(__file__).resolve().parents[4] / "apps" / "execution-runner")
if runner_path not in sys.path:
    sys.path.insert(0, runner_path)
from runner.protocol import ExecutionJob
from runner.executor import CodeExecutor


class EvaluationOrchestrator:
    """Orchestrates submission evaluation according to versioned rubrics and test suites."""

    @classmethod
    def evaluate_submission(
        cls,
        submission_id: str,
        source_code: str,
        rubric: RubricSchema,
        test_cases: List[Dict[str, Any]],
        evaluator_version: str = "1.0.0",
    ) -> EvaluationResultPayload:
        """
        Full evaluation cycle:
        1. Static AST concept check
        2. Test cases execution in sandbox
        3. Weighted rubric scoring
        4. Structured feedback generation
        """
        # Step 1: Static AST Analysis
        syntax_valid, concept_evidences, syntax_err = ASTAnalyzer.evaluate_concepts(
            source_code=source_code,
            required_concepts=rubric.required_concepts,
            prohibited_constructs=rubric.prohibited_constructs,
        )

        test_results: List[TestCaseResultPayload] = []

        # Step 2: Sandbox Execution (only if syntax is valid)
        if syntax_valid:
            for tc in test_cases:
                tc_id = str(tc.get("id", "tc_unknown"))
                visibility = tc.get("visibility", "public")
                expected_output = str(tc.get("expected_output", "")).strip()
                stdin_input = str(tc.get("input_data", ""))
                timeout_s = float(tc.get("timeout_ms", 3000)) / 1000.0

                exec_job = ExecutionJob(
                    job_id=f"{submission_id}_{tc_id}",
                    source_code=source_code,
                    stdin_input=stdin_input,
                    timeout_seconds=timeout_s,
                )

                res = CodeExecutor.run_code(exec_job)

                actual_output = res.stdout.strip()
                status = "passed"
                err_msg = None

                if res.timed_out:
                    status = "timeout"
                    err_msg = f"Time Limit Exceeded ({timeout_s}s)"
                elif res.exit_code != 0:
                    status = "runtime_error"
                    err_msg = res.stderr.strip()[:500] if res.stderr else "Non-zero exit code"
                elif actual_output != expected_output:
                    status = "failed"
                    err_msg = "Output mismatch"

                # Truncate summary for student safety/hidden tests
                summary_actual = actual_output[:200] if visibility != "hidden" else None
                summary_expected = expected_output[:200] if visibility != "hidden" else None

                test_results.append(
                    TestCaseResultPayload(
                        test_case_id=tc_id,
                        visibility=visibility,
                        status=status,
                        execution_time_ms=res.duration_ms,
                        memory_used_bytes=0,
                        actual_output_summary=summary_actual,
                        expected_output_summary=summary_expected,
                        error_message=err_msg,
                    )
                )

        # Step 3: Compute Score Breakdowns
        total_score, criteria_scores, suggestions = ScoringEngine.calculate_score(
            rubric=rubric,
            syntax_valid=syntax_valid,
            concept_evidence=concept_evidences,
            test_case_results=test_results,
        )

        # Formulate summary feedback
        if not syntax_valid:
            summary = f"Syntax Error: {syntax_err}"
            eval_status = "failed"
        elif total_score == rubric.max_score:
            summary = "Accepted: Full score awarded with correct functionality and concept compliance."
            eval_status = "completed"
        elif total_score > 0:
            summary = f"Partially Accepted: Achieved {total_score}/{rubric.max_score} points. Review feedback to improve."
            eval_status = "completed"
        else:
            summary = "Rejected: 0 points awarded. Solution failed functional or conceptual requirements."
            eval_status = "completed"

        return EvaluationResultPayload(
            submission_id=submission_id,
            evaluator_version=evaluator_version,
            status=eval_status,
            syntax_valid=syntax_valid,
            syntax_error_details=syntax_err,
            total_score=total_score,
            criteria_scores=criteria_scores,
            concept_evidence=concept_evidences,
            test_case_results=test_results,
            summary_feedback=summary,
            actionable_suggestions=suggestions,
        )
