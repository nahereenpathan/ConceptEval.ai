"""
Isolated Execution Engine
Executes untrusted Python submissions under bounded limits and sanitized environments.
"""

import os
import sys
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Dict

from .protocol import ExecutionJob, ExecutionResult


class CodeExecutor:
    """Executes untrusted code within an isolated, monitored subprocess."""

    # Explicit whitelist of environment keys allowed into the untrusted runner
    SAFE_ENV_KEYS = {
        "PATH",
        "SYSTEMROOT",
        "COMSPEC",
        "PATHEXT",
        "TEMP",
        "TMP",
        "PYTHONIOENCODING",
        "PYTHONHASHSEED",
    }

    @classmethod
    def _sanitize_env(cls) -> Dict[str, str]:
        """Strip all sensitive variables (API keys, database URLs, auth secrets)."""
        clean_env = {
            k: v for k, v in os.environ.items()
            if k.upper() in cls.SAFE_ENV_KEYS
        }
        clean_env["PYTHONIOENCODING"] = "utf-8"
        clean_env["PYTHONHASHSEED"] = "random"
        clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
        return clean_env

    @classmethod
    def run_code(cls, job: ExecutionJob) -> ExecutionResult:
        """
        Execute code in a monitored, resource-bounded subprocess.
        """
        start_time = time.perf_counter()
        clean_env = cls._sanitize_env()

        # Create isolated temporary directory
        with tempfile.TemporaryDirectory(prefix="runner_box_") as tmpdir:
            script_path = Path(tmpdir) / "submission.py"
            script_path.write_text(job.source_code, encoding="utf-8")

            # Determine appropriate process group flag
            creationflags = 0
            start_new_session = False
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                start_new_session = True

            cmd = [
                sys.executable,
                "-I",  # Isolated mode (ignores PYTHONPATH and user site-packages)
                "-B",  # Don't write bytecode
                "-u",  # Unbuffered binary stdout and stderr
                str(script_path),
            ]

            process = None
            try:
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=tmpdir,
                    env=clean_env,
                    creationflags=creationflags,
                    start_new_session=start_new_session,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

                stdout_data, stderr_data = process.communicate(
                    input=job.stdin_input or "",
                    timeout=job.timeout_seconds,
                )
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                exit_code = process.returncode

                # Enforce output length bounds
                truncated = False
                if len(stdout_data) > job.max_output_bytes:
                    stdout_data = stdout_data[:job.max_output_bytes] + "\n[Output Truncated: Exceeded Maximum Output Size]"
                    truncated = True

                if len(stderr_data) > job.max_output_bytes:
                    stderr_data = stderr_data[:job.max_output_bytes] + "\n[Error Output Truncated]"
                    truncated = True

                error_type = None
                if exit_code != 0:
                    error_type = "NON_ZERO_EXIT"

                return ExecutionResult(
                    job_id=job.job_id,
                    exit_code=exit_code,
                    stdout=stdout_data,
                    stderr=stderr_data,
                    duration_ms=round(duration_ms, 2),
                    timed_out=False,
                    memory_exceeded=False,
                    error_type=error_type,
                    truncated=truncated,
                )

            except subprocess.TimeoutExpired:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                if process:
                    cls._terminate_process(process)
                    try:
                        stdout_data, stderr_data = process.communicate(timeout=0.5)
                    except Exception:
                        stdout_data, stderr_data = "", ""

                return ExecutionResult(
                    job_id=job.job_id,
                    exit_code=-1,
                    stdout=stdout_data or "",
                    stderr=(stderr_data or "") + f"\nTimeLimitExceeded: Execution exceeded {job.timeout_seconds}s limit.",
                    duration_ms=round(duration_ms, 2),
                    timed_out=True,
                    memory_exceeded=False,
                    error_type="TIMEOUT",
                    truncated=False,
                )

            except Exception as exc:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return ExecutionResult(
                    job_id=job.job_id,
                    exit_code=-1,
                    stdout="",
                    stderr=f"SystemExecutionError: {str(exc)}",
                    duration_ms=round(duration_ms, 2),
                    timed_out=False,
                    memory_exceeded=False,
                    error_type="SYSTEM_ERROR",
                    truncated=False,
                )

    @classmethod
    def _terminate_process(cls, process: subprocess.Popen):
        """Forcefully kill the process tree."""
        try:
            if sys.platform == "win32":
                # Use taskkill /F /T /PID on Windows to terminate child processes
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                    capture_output=True,
                    check=False,
                )
            else:
                import signal
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
