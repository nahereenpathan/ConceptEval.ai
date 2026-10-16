"""
Subprocess Execution Runner (Local Development & Testing Only)
Executes Python scripts using monitored host subprocesses with environment sanitization
and process tree timeout controls.
NOTE: This runner DOES NOT provide containerization or OS-level security boundaries.
It must never be used in a public multi-tenant production environment.
"""

import os
import sys
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Any, Dict

from .base import BaseRunner
from .protocol import ExecutionJob, ExecutionResult


class SubprocessRunner(BaseRunner):
    """
    Subprocess runner for local offline testing and unit tests.
    Applies environment variable sanitization, isolated flags, and timeout process killing.
    """

    SAFE_ENV_KEYS = {
        "PATH",
        "SYSTEMROOT",
        "COMSPEC",
        "PATHEXT",
        "TEMP",
        "TMP",
        "WINDIR",
        "USERPROFILE",
        "JAVA_HOME",
        "JDK_HOME",
        "PYTHONIOENCODING",
        "PYTHONHASHSEED",
    }

    def __init__(self, allow_host_execution: bool = True):
        self.allow_host_execution = allow_host_execution

    def is_available(self) -> bool:
        """Python executable is always available in the local runtime."""
        return bool(sys.executable)

    def is_language_available(self, language: str) -> bool:
        """Check whether compiler/runtime for the given language is available."""
        from .languages import LanguageDetector
        spec = LanguageDetector.get_language_spec(language)
        return bool(spec and spec.get("is_available"))

    def get_isolation_info(self) -> Dict[str, Any]:
        from .languages import LanguageDetector
        return {
            "mechanism": "host_subprocess_uncontained",
            "is_sandboxed": False,
            "environment_sanitized": True,
            "container_enforced": False,
            "network_isolated": False,
            "memory_cgroup_enforced": False,
            "read_only_root": False,
            "warning": "Runs directly on host OS. Unsafe for untrusted multi-tenant workloads.",
            "languages": LanguageDetector.get_all_languages(),
        }

    def _sanitize_env(self) -> Dict[str, str]:
        """Strip all sensitive variables (API keys, database URLs, auth secrets)."""
        clean_env = {
            k: v for k, v in os.environ.items()
            if k.upper() in self.SAFE_ENV_KEYS
        }
        clean_env["PYTHONIOENCODING"] = "utf-8"
        clean_env["PYTHONHASHSEED"] = "random"
        clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
        return clean_env

    def run(self, job: ExecutionJob) -> ExecutionResult:
        """
        Execute code in a monitored, resource-bounded host subprocess.
        Supports Python 3.12, Java (JDK), and C++ (g++ compiler).
        """
        if not self.allow_host_execution:
            return ExecutionResult(
                job_id=job.job_id,
                exit_code=-1,
                stdout="",
                stderr="SandboxPolicyViolation: Host subprocess execution is disabled by policy. A secure container sandbox is required.",
                duration_ms=0.0,
                timed_out=False,
                memory_exceeded=False,
                error_type="SANDBOX_UNAVAILABLE",
                is_sandboxed=False,
                isolation_mechanism="host_subprocess_uncontained",
            )

        start_time = time.perf_counter()
        clean_env = self._sanitize_env()
        raw_lang = (job.language or "python").lower().strip()
        lang = "cpp" if raw_lang in ("c++", "cpp") else raw_lang

        from .languages import extract_java_class_name, LanguageDetector

        # Verify compiler/runtime availability
        lang_spec = LanguageDetector.get_language_spec(lang)
        if not lang_spec or not lang_spec.get("is_available"):
            return ExecutionResult(
                job_id=job.job_id,
                exit_code=-1,
                stdout="",
                stderr=f"CompilerUnavailable: {lang.capitalize()} compiler or runtime is not installed or configured on the system PATH.",
                duration_ms=0.0,
                timed_out=False,
                memory_exceeded=False,
                compilation_error=True,
                error_type="COMPILATION_ERROR",
                is_sandboxed=False,
                isolation_mechanism="host_subprocess_uncontained",
            )

        with tempfile.TemporaryDirectory(prefix=f"runner_{lang}_") as tmpdir:
            tmp_path = Path(tmpdir)
            run_cmd = []

            # -----------------------------------------------------------------
            # 1. Compilation & Preparation Phase
            # -----------------------------------------------------------------
            if lang == "java":
                class_name = extract_java_class_name(job.source_code)
                source_file = tmp_path / f"{class_name}.java"
                source_file.write_text(job.source_code, encoding="utf-8")

                javac_bin = lang_spec.get("compiler") or "javac"
                compile_cmd = [
                    javac_bin,
                    "-encoding", "UTF-8",
                    "-J-Xmx256m",
                    f"{class_name}.java",
                ]

                try:
                    compile_proc = subprocess.run(
                        compile_cmd,
                        cwd=tmpdir,
                        env=clean_env,
                        capture_output=True,
                        text=True,
                        timeout=12.0,
                    )
                except subprocess.TimeoutExpired:
                    return ExecutionResult(
                        job_id=job.job_id,
                        exit_code=-1,
                        stdout="",
                        stderr="CompilationTimeout: Java compilation exceeded timeout limit (12s).",
                        duration_ms=round((time.perf_counter() - start_time) * 1000.0, 2),
                        timed_out=True,
                        compilation_error=True,
                        error_type="COMPILATION_ERROR",
                        is_sandboxed=False,
                        isolation_mechanism="host_subprocess_uncontained",
                    )

                if compile_proc.returncode != 0:
                    compile_err = (compile_proc.stderr or compile_proc.stdout or "").strip()
                    return ExecutionResult(
                        job_id=job.job_id,
                        exit_code=compile_proc.returncode,
                        stdout="",
                        stderr=compile_err,
                        duration_ms=round((time.perf_counter() - start_time) * 1000.0, 2),
                        compilation_error=True,
                        compile_output=compile_err,
                        error_type="COMPILATION_ERROR",
                        is_sandboxed=False,
                        isolation_mechanism="host_subprocess_uncontained",
                    )

                java_bin = lang_spec.get("executable") or "java"
                run_cmd = [
                    java_bin,
                    f"-Xmx{job.memory_limit_mb}m",
                    "-Xss32m",
                    "-Dfile.encoding=UTF-8",
                    "-cp", ".",
                    class_name,
                ]

            elif lang == "cpp":
                source_file = tmp_path / "submission.cpp"
                source_file.write_text(job.source_code, encoding="utf-8")
                binary_name = "submission.exe" if sys.platform == "win32" else "submission"
                binary_path = tmp_path / binary_name

                gpp_bin = lang_spec.get("compiler") or "g++"
                compile_cmd = [
                    gpp_bin,
                    "-O2",
                    "-std=c++17",
                    "-Wall",
                    "submission.cpp",
                    "-o", binary_name,
                ]

                try:
                    compile_proc = subprocess.run(
                        compile_cmd,
                        cwd=tmpdir,
                        env=clean_env,
                        capture_output=True,
                        text=True,
                        timeout=12.0,
                    )
                except subprocess.TimeoutExpired:
                    return ExecutionResult(
                        job_id=job.job_id,
                        exit_code=-1,
                        stdout="",
                        stderr="CompilationTimeout: C++ compilation exceeded timeout limit (12s).",
                        duration_ms=round((time.perf_counter() - start_time) * 1000.0, 2),
                        timed_out=True,
                        compilation_error=True,
                        error_type="COMPILATION_ERROR",
                        is_sandboxed=False,
                        isolation_mechanism="host_subprocess_uncontained",
                    )

                if compile_proc.returncode != 0:
                    compile_err = (compile_proc.stderr or compile_proc.stdout or "").strip()
                    return ExecutionResult(
                        job_id=job.job_id,
                        exit_code=compile_proc.returncode,
                        stdout="",
                        stderr=compile_err,
                        duration_ms=round((time.perf_counter() - start_time) * 1000.0, 2),
                        compilation_error=True,
                        compile_output=compile_err,
                        error_type="COMPILATION_ERROR",
                        is_sandboxed=False,
                        isolation_mechanism="host_subprocess_uncontained",
                    )

                run_cmd = [str(binary_path)]

            else:  # Python
                script_path = tmp_path / "submission.py"
                script_path.write_text(job.source_code, encoding="utf-8")
                run_cmd = [
                    sys.executable,
                    "-I",  # Isolated mode (ignores PYTHONPATH and user site-packages)
                    "-B",  # Don't write bytecode
                    "-u",  # Unbuffered binary stdout and stderr
                    str(script_path),
                ]

            # -----------------------------------------------------------------
            # 2. Execution Phase
            # -----------------------------------------------------------------
            creationflags = 0
            start_new_session = False
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                start_new_session = True

            process = None
            try:
                process = subprocess.Popen(
                    run_cmd,
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
                    is_sandboxed=False,
                    isolation_mechanism="host_subprocess_uncontained",
                )

            except subprocess.TimeoutExpired:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                if process:
                    self._terminate_process(process)
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
                    is_sandboxed=False,
                    isolation_mechanism="host_subprocess_uncontained",
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
                    is_sandboxed=False,
                    isolation_mechanism="host_subprocess_uncontained",
                )

    def _terminate_process(self, process: subprocess.Popen):
        """Forcefully kill the process tree."""
        try:
            if sys.platform == "win32":
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
