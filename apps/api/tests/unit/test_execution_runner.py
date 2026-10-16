"""
Unit Tests for Isolated Code Execution Runner & Security Boundaries
Validates:
1. Development subprocess runner: resource bounds, process tree timeouts, I/O handling, and env isolation.
2. Container sandbox runner: security command formulation, OOM cgroup memory handling, timeout kills.
3. Security boundaries: attempted host filesystem access, network egress isolation, and sandbox offline handling.
4. Fail-safe enforcement: DockerRunner NEVER falls back to host execution when container runtime is offline.
"""

import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Ensure execution-runner is accessible on sys.path
runner_path = str(Path(__file__).resolve().parents[3] / "apps" / "execution-runner")
if runner_path not in sys.path:
    sys.path.insert(0, runner_path)

from runner.base import BaseRunner
from runner.docker_runner import DockerRunner
from runner.executor import CodeExecutor
from runner.protocol import ExecutionJob, ExecutionResult
from runner.subprocess_runner import SubprocessRunner
from app.evaluation.orchestrator import EvaluationOrchestrator
from evaluation_specifications.models import RubricSchema


# ==============================================================================
# 1. Subprocess Development Runner Tests (Environment Sanitization & Limits)
# ==============================================================================

class TestSubprocessDevelopmentRunner:
    """Test suite for host subprocess development runner constraints."""

    def test_successful_execution(self):
        """Standard program executes successfully and captures stdout."""
        job = ExecutionJob(
            job_id="job_success",
            source_code="""
for i in range(4):
    print("Hello World")
""",
            timeout_seconds=3.0,
        )

        res = CodeExecutor.run_code(job, runner_mode="subprocess")
        assert res.exit_code == 0
        assert res.timed_out is False
        assert res.error_type is None
        assert res.is_sandboxed is False
        assert res.isolation_mechanism == "host_subprocess_uncontained"
        expected_output = "Hello World\n" * 4
        assert res.stdout.replace("\r\n", "\n") == expected_output

    def test_stdin_input_handling(self):
        """Subprocess correctly receives and processes stdin input."""
        job = ExecutionJob(
            job_id="job_stdin",
            source_code="""
name = input().strip()
print(f"Welcome, {name}!")
""",
            stdin_input="Student Alice\n",
            timeout_seconds=3.0,
        )

        res = CodeExecutor.run_code(job, runner_mode="subprocess")
        assert res.exit_code == 0
        assert "Welcome, Student Alice!" in res.stdout

    def test_infinite_loop_timeout_enforcement(self):
        """Infinite loop triggers timeout and process tree termination within limit."""
        job = ExecutionJob(
            job_id="job_timeout",
            source_code="""
import time
while True:
    time.sleep(0.1)
""",
            timeout_seconds=1.0,
        )

        res = CodeExecutor.run_code(job, runner_mode="subprocess")
        assert res.timed_out is True
        assert res.error_type == "TIMEOUT"
        assert "TimeLimitExceeded" in res.stderr

    def test_runtime_error_captured(self):
        """Runtime exception returns non-zero exit code and stderr traceback."""
        job = ExecutionJob(
            job_id="job_runtime_err",
            source_code="""
result = 10 / 0
""",
            timeout_seconds=3.0,
        )

        res = CodeExecutor.run_code(job, runner_mode="subprocess")
        assert res.exit_code != 0
        assert res.error_type == "NON_ZERO_EXIT"
        assert "ZeroDivisionError: division by zero" in res.stderr

    def test_environment_sanitization(self):
        """Sensitive environment secrets (DB URLs, keys) are stripped from child processes."""
        os.environ["DATABASE_URL"] = "postgresql://supersecret:password@db/prod"
        os.environ["APP_SECRET_KEY"] = "super-confidential-secret-key"

        job = ExecutionJob(
            job_id="job_env_leak_test",
            source_code="""
import os
db = os.environ.get("DATABASE_URL")
secret = os.environ.get("APP_SECRET_KEY")
print(f"DB:{db}|SECRET:{secret}")
""",
            timeout_seconds=3.0,
        )

        res = CodeExecutor.run_code(job, runner_mode="subprocess")
        assert res.exit_code == 0
        assert "DB:None|SECRET:None" in res.stdout

    def test_output_truncation_limit(self):
        """Excessive output generation is bounded and truncated."""
        job = ExecutionJob(
            job_id="job_bomb_output",
            source_code="""
for _ in range(5000):
    print("A" * 100)
""",
            timeout_seconds=3.0,
            max_output_bytes=4096,  # 4KB limit
        )

        res = CodeExecutor.run_code(job, runner_mode="subprocess")
        assert res.exit_code == 0
        assert res.truncated is True
        assert len(res.stdout) <= 5000
        assert "Output Truncated" in res.stdout

    def test_subprocess_runner_policy_blocks_when_disabled(self):
        """SubprocessRunner rejects execution when allow_host_execution is False."""
        runner = SubprocessRunner(allow_host_execution=False)
        job = ExecutionJob(
            job_id="job_blocked",
            source_code="print('Hello')",
        )
        res = runner.run(job)
        assert res.exit_code == -1
        assert res.error_type == "SANDBOX_UNAVAILABLE"
        assert "Host subprocess execution is disabled" in res.stderr


# ==============================================================================
# 2. Docker Container Sandbox Security Boundary Tests
# ==============================================================================

class TestDockerContainerRunner:
    """Test suite validating Docker sandbox security arguments and boundary enforcement."""

    def test_docker_runner_command_formulation_security_flags(self):
        """DockerRunner formulates strict security flags in container command."""
        runner = DockerRunner(
            image_name="concept-eval-runner:latest",
            docker_bin="docker",
            network_mode="none",
            read_only_root=True,
            user_identity="10001:10001",
            pids_limit=64,
            cpu_limit="1.0",
        )

        args = runner.build_container_args(
            container_name="test_box_1",
            host_script_path="/tmp/test_sub.py",
            memory_mb=128,
        )

        # Verify all mandatory security parameters are present
        assert "--network=none" in args
        assert "--read-only" in args
        assert "--user=10001:10001" in args
        assert "--cap-drop=ALL" in args
        assert "--security-opt=no-new-privileges:true" in args
        assert "--memory=128m" in args
        assert "--memory-swap=128m" in args
        assert "--cpus=1.0" in args
        assert "--pids-limit=64" in args
        assert "--rm" in args
        assert "-v" in args
        assert "/tmp/test_sub.py:/sandbox/submission.py:ro" in args
        assert "concept-eval-runner:latest" in args
        assert ["python3", "-I", "-B", "-u", "/sandbox/submission.py"] == args[-5:]

    def test_docker_runner_oom_memory_exhaustion(self):
        """Exit code 137 is mapped to MEMORY_LIMIT and memory_exceeded=True."""
        runner = DockerRunner()

        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "Killed\n")
        mock_proc.returncode = 137  # OOM killer exit code

        with patch.object(runner, "is_available", return_value=True):
            with patch("subprocess.Popen", return_value=mock_proc):
                job = ExecutionJob(
                    job_id="job_oom_test",
                    source_code="a = bytearray(200 * 1024 * 1024)",
                    memory_limit_mb=128,
                )
                res = runner.run(job)
                assert res.exit_code == 137
                assert res.memory_exceeded is True
                assert res.error_type == "MEMORY_LIMIT"
                assert "MemoryLimitExceeded" in res.stderr
                assert res.is_sandboxed is True
                assert res.isolation_mechanism == "docker"

    def test_docker_runner_timeout_kills_container(self):
        """TimeoutExpired invokes docker rm -f to kill the running container."""
        runner = DockerRunner()

        mock_proc = MagicMock()
        mock_proc.communicate.side_effect = subprocess.TimeoutExpired(cmd=["docker"], timeout=2.0)

        with patch.object(runner, "is_available", return_value=True):
            with patch("subprocess.Popen", return_value=mock_proc):
                with patch.object(runner, "_kill_container") as mock_kill:
                    job = ExecutionJob(
                        job_id="job_docker_timeout",
                        source_code="while True: pass",
                        timeout_seconds=2.0,
                    )
                    res = runner.run(job)
                    assert res.timed_out is True
                    assert res.error_type == "TIMEOUT"
                    mock_kill.assert_called_once()
                    assert "TimeLimitExceeded" in res.stderr

    def test_docker_runner_safe_failure_when_daemon_offline(self):
        """When Docker daemon is offline, returns SANDBOX_UNAVAILABLE and NEVER falls back to host."""
        runner = DockerRunner()

        with patch.object(runner, "is_available", return_value=False):
            job = ExecutionJob(
                job_id="job_offline_daemon",
                source_code="print('Untrusted code')",
            )
            res = runner.run(job)
            assert res.exit_code == -1
            assert res.error_type == "SANDBOX_UNAVAILABLE"
            assert "SandboxInfrastructureUnavailable" in res.stderr
            assert "Host execution fallback is strictly prohibited" in res.stderr
            assert res.is_sandboxed is True


# ==============================================================================
# 3. Security Boundary & Policy Enforcement Tests
# ==============================================================================

class TestSecurityPolicyEnforcement:
    """Validates policy constraints and fail-safe handling in orchestrator."""

    def test_production_environment_forces_docker_runner(self):
        """When APP_ENV=production, CodeExecutor selects DockerRunner and forbids subprocess."""
        with patch.dict(os.environ, {"APP_ENV": "production", "EXECUTION_RUNNER_MODE": "subprocess"}):
            runner = CodeExecutor.get_runner()
            assert isinstance(runner, DockerRunner)

    def test_code_executor_mode_docker_selects_docker_runner(self):
        """When EXECUTION_RUNNER_MODE=docker, CodeExecutor selects DockerRunner."""
        with patch.dict(os.environ, {"APP_ENV": "development", "EXECUTION_RUNNER_MODE": "docker"}):
            runner = CodeExecutor.get_runner()
            assert isinstance(runner, DockerRunner)

    def test_sandbox_status_reports_availability_and_blockers(self):
        """CodeExecutor.get_sandbox_status accurately reports container readiness."""
        with patch.dict(os.environ, {"APP_ENV": "development", "EXECUTION_RUNNER_MODE": "docker"}):
            with patch.object(DockerRunner, "is_available", return_value=False):
                status = CodeExecutor.get_sandbox_status()
                assert status["configured_mode"] == "docker"
                assert status["container_sandbox_available"] is False
                assert status["is_production_ready"] is False
                assert "Docker daemon is not running" in status["blocker_reason"]

    def test_orchestrator_raises_on_sandbox_unavailable(self):
        """EvaluationOrchestrator raises RuntimeError when sandbox is unavailable (preventing false scoring)."""
        unavailable_res = ExecutionResult(
            job_id="job_unavail",
            exit_code=-1,
            stdout="",
            stderr="Sandbox daemon offline",
            duration_ms=0.0,
            error_type="SANDBOX_UNAVAILABLE",
        )

        rubric = RubricSchema(
            schema_version="1.0.0",
            max_score=100.0,
            functional_weight=50.0,
            concept_weight=30.0,
            algorithmic_weight=10.0,
            constraint_weight=10.0,
            required_concepts=[],
            prohibited_constructs=[],
        )
        test_cases = [{"id": "tc1", "expected_output": "test", "timeout_ms": 3000}]

        with patch.object(CodeExecutor, "run_code", return_value=unavailable_res):
            with pytest.raises(RuntimeError, match="SandboxInfrastructureUnavailable"):
                EvaluationOrchestrator.evaluate_submission(
                    submission_id="sub_test",
                    source_code="print('Hello')",
                    rubric=rubric,
                    test_cases=test_cases,
                )
