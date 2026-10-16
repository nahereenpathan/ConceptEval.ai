"""
Unit Tests for Isolated Code Execution Runner
Validates resource bounds, timeout termination, I/O handling, and env isolation.
"""

import sys
import os
from pathlib import Path
import pytest

# Ensure execution-runner is accessible on sys.path
runner_path = str(Path(__file__).resolve().parents[3] / "apps" / "execution-runner")
if runner_path not in sys.path:
    sys.path.insert(0, runner_path)

from runner.protocol import ExecutionJob
from runner.executor import CodeExecutor


class TestCodeExecutionRunner:
    """Test suite for sandbox execution constraints and isolation."""

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

        res = CodeExecutor.run_code(job)
        assert res.exit_code == 0
        assert res.timed_out is False
        assert res.error_type is None
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

        res = CodeExecutor.run_code(job)
        assert res.exit_code == 0
        assert "Welcome, Student Alice!" in res.stdout

    def test_infinite_loop_timeout_enforcement(self):
        """Infinite loop triggers timeout and process termination within limit."""
        job = ExecutionJob(
            job_id="job_timeout",
            source_code="""
import time
while True:
    time.sleep(0.1)
""",
            timeout_seconds=1.0,
        )

        res = CodeExecutor.run_code(job)
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

        res = CodeExecutor.run_code(job)
        assert res.exit_code != 0
        assert res.error_type == "NON_ZERO_EXIT"
        assert "ZeroDivisionError: division by zero" in res.stderr

    def test_environment_sanitization(self):
        """Sensitive environment secrets are blocked from student scripts."""
        # Inject dummy secret into test runner environment
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

        res = CodeExecutor.run_code(job)
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

        res = CodeExecutor.run_code(job)
        assert res.exit_code == 0
        assert res.truncated is True
        assert len(res.stdout) <= 5000
        assert "Output Truncated" in res.stdout
