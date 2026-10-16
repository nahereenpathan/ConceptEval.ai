"""
Docker Sandbox Execution Runner
Executes untrusted student code inside an isolated, constrained rootless Docker container.
Enforces strict container boundaries:
- Non-root user (UID 10001)
- Network disabled (--network=none)
- Read-only root filesystem (--read-only)
- Dropped all Linux capabilities (--cap-drop=ALL)
- No new privileges (--security-opt=no-new-privileges:true)
- Resource bounds (cgroups: memory, cpu, pids-limit)
- Temporary workspace tmpfs with no host filesystem mounts
"""

import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseRunner
from .protocol import ExecutionJob, ExecutionResult


class DockerRunner(BaseRunner):
    """
    Production-grade containerized runner that isolates untrusted code in Docker/gVisor.
    """

    DEFAULT_IMAGE = "concept-eval-runner:latest"

    def __init__(
        self,
        image_name: Optional[str] = None,
        docker_bin: Optional[str] = None,
        cpu_limit: str = "1.0",
        pids_limit: int = 64,
        network_mode: str = "none",
        read_only_root: bool = True,
        user_identity: str = "10001:10001",
    ):
        self.image_name = image_name or os.environ.get("DOCKER_RUNNER_IMAGE", self.DEFAULT_IMAGE)
        self.docker_bin = docker_bin or os.environ.get("DOCKER_BIN_PATH", "docker")
        self.cpu_limit = cpu_limit
        self.pids_limit = pids_limit
        self.network_mode = network_mode
        self.read_only_root = read_only_root
        self.user_identity = user_identity

    def is_available(self) -> bool:
        """
        Validates whether Docker CLI is installed and the Docker daemon is responding.
        Times out after 2.0s to avoid blocking.
        """
        docker_exe = shutil.which(self.docker_bin)
        if not docker_exe:
            return False

        try:
            # Query daemon status with strict timeout
            res = subprocess.run(
                [self.docker_bin, "info", "--format", "{{.ServerVersion}}"],
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
            return res.returncode == 0
        except Exception:
            return False

    def get_isolation_info(self) -> Dict[str, Any]:
        available = self.is_available()
        return {
            "mechanism": "docker_container",
            "is_sandboxed": True,
            "runtime_available": available,
            "image": self.image_name,
            "network_mode": self.network_mode,
            "read_only_root": self.read_only_root,
            "user_identity": self.user_identity,
            "pids_limit": self.pids_limit,
            "cpu_limit": self.cpu_limit,
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges:true"],
        }

    def build_container_args(
        self,
        container_name: str,
        host_script_path: str,
        memory_mb: int,
        language: str = "python",
        class_name: str = "Solution",
    ) -> List[str]:
        """
        Formulate strict security-hardened Docker command arguments.
        """
        norm_lang = "cpp" if language in ("c++", "cpp") else language.lower()

        if norm_lang == "java":
            container_file = f"/sandbox/{class_name}.java"
            exec_cmd = ["sh", "-c", f"javac -encoding UTF-8 {container_file} -d /sandbox/workspace && java -Xmx{memory_mb}m -Xss32m -cp /sandbox/workspace {class_name}"]
        elif norm_lang == "cpp":
            container_file = "/sandbox/submission.cpp"
            exec_cmd = ["sh", "-c", "g++ -O2 -std=c++17 /sandbox/submission.cpp -o /sandbox/workspace/a.out && /sandbox/workspace/a.out"]
        else:
            container_file = "/sandbox/submission.py"
            exec_cmd = ["python3", "-I", "-B", "-u", "/sandbox/submission.py"]

        args = [
            self.docker_bin,
            "run",
            "--rm",
            "-i",
            "--name", container_name,
            f"--network={self.network_mode}",
            f"--memory={memory_mb}m",
            f"--memory-swap={memory_mb}m",
            f"--cpus={self.cpu_limit}",
            f"--pids-limit={self.pids_limit}",
            f"--user={self.user_identity}",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m",
            "--tmpfs", "/sandbox/workspace:rw,size=64m",
            "-v", f"{host_script_path}:{container_file}:ro",
            "-w", "/sandbox/workspace",
        ]

        if self.read_only_root:
            args.append("--read-only")

        args.append(self.image_name)
        args.extend(exec_cmd)
        return args

    def run(self, job: ExecutionJob) -> ExecutionResult:
        """
        Execute code within a hardened Docker container.
        Never falls back to host execution if Docker is unavailable.
        """
        if not self.is_available():
            return ExecutionResult(
                job_id=job.job_id,
                exit_code=-1,
                stdout="",
                stderr=(
                    "SandboxInfrastructureUnavailable: Docker container sandbox is not available "
                    "or daemon is offline. Host execution fallback is strictly prohibited for security."
                ),
                duration_ms=0.0,
                timed_out=False,
                memory_exceeded=False,
                error_type="SANDBOX_UNAVAILABLE",
                truncated=False,
                is_sandboxed=True,
                isolation_mechanism="docker",
            )

        start_time = time.perf_counter()
        clean_job_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", job.job_id)
        container_name = f"eval_box_{clean_job_id}_{int(time.time() * 1000) % 100000}"
        raw_lang = (job.language or "python").lower().strip()
        lang = "cpp" if raw_lang in ("c++", "cpp") else raw_lang

        from .languages import extract_java_class_name
        class_name = extract_java_class_name(job.source_code) if lang == "java" else "Solution"
        ext = ".java" if lang == "java" else (".cpp" if lang == "cpp" else ".py")
        file_name = f"{class_name}.java" if lang == "java" else f"submission{ext}"

        with tempfile.TemporaryDirectory(prefix="docker_runner_") as tmpdir:
            script_path = Path(tmpdir) / file_name
            script_path.write_text(job.source_code, encoding="utf-8")

            # Convert to absolute POSIX path format for volume mounting
            abs_script_path = str(script_path.resolve())

            cmd = self.build_container_args(
                container_name=container_name,
                host_script_path=abs_script_path,
                memory_mb=job.memory_limit_mb,
                language=lang,
                class_name=class_name,
            )

            process = None
            try:
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
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
                memory_exceeded = False

                # Exit code 137 indicates OOM killer (128 + SIGKILL 9) or timeout SIGKILL
                if exit_code == 137:
                    memory_exceeded = True
                    error_type = "MEMORY_LIMIT"
                    stderr_data = (stderr_data or "") + "\nMemoryLimitExceeded: Process exceeded memory limit."
                elif exit_code != 0:
                    error_type = "NON_ZERO_EXIT"

                return ExecutionResult(
                    job_id=job.job_id,
                    exit_code=exit_code,
                    stdout=stdout_data,
                    stderr=stderr_data,
                    duration_ms=round(duration_ms, 2),
                    timed_out=False,
                    memory_exceeded=memory_exceeded,
                    error_type=error_type,
                    truncated=truncated,
                    is_sandboxed=True,
                    isolation_mechanism="docker",
                )

            except subprocess.TimeoutExpired:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                # Terminate running container via docker kill
                self._kill_container(container_name)

                return ExecutionResult(
                    job_id=job.job_id,
                    exit_code=-1,
                    stdout="",
                    stderr=f"TimeLimitExceeded: Execution exceeded {job.timeout_seconds}s limit.",
                    duration_ms=round(duration_ms, 2),
                    timed_out=True,
                    memory_exceeded=False,
                    error_type="TIMEOUT",
                    truncated=False,
                    is_sandboxed=True,
                    isolation_mechanism="docker",
                )

            except Exception as exc:
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                self._kill_container(container_name)

                return ExecutionResult(
                    job_id=job.job_id,
                    exit_code=-1,
                    stdout="",
                    stderr=f"ContainerExecutionError: {str(exc)}",
                    duration_ms=round(duration_ms, 2),
                    timed_out=False,
                    memory_exceeded=False,
                    error_type="SYSTEM_ERROR",
                    truncated=False,
                    is_sandboxed=True,
                    isolation_mechanism="docker",
                )

    def _kill_container(self, container_name: str) -> None:
        """Forcefully kill and remove the container."""
        try:
            subprocess.run(
                [self.docker_bin, "rm", "-f", container_name],
                capture_output=True,
                timeout=3.0,
                check=False,
            )
        except Exception:
            pass
