"""
Execution Engine Facade
Dispatches execution requests to the appropriate isolation runner (Docker sandbox or local subprocess).
Enforces security boundaries:
- In production, requires containerized isolation.
- If container runner is unavailable, NEVER falls back to host execution.
- Exposes diagnostic status on sandbox availability.
"""

import os
from typing import Any, Dict, Optional

from .base import BaseRunner
from .docker_runner import DockerRunner
from .protocol import ExecutionJob, ExecutionResult
from .subprocess_runner import SubprocessRunner


class CodeExecutor:
    """Unified execution manager coordinating isolated sandboxes and development runners."""

    @classmethod
    def get_runner(cls, runner_mode: Optional[str] = None) -> BaseRunner:
        """
        Instantiate the appropriate runner backend based on mode and environment.
        """
        mode = runner_mode or os.environ.get("EXECUTION_RUNNER_MODE", "subprocess").lower()
        app_env = os.environ.get("APP_ENV", "development").lower()

        # In production, containerized runner is mandatory
        if app_env == "production" or mode in ("docker", "gvisor"):
            return DockerRunner()

        # In development/test, allow subprocess runner with explicit environment sanitization
        return SubprocessRunner(allow_host_execution=True)

    @classmethod
    def run_code(
        cls,
        job: ExecutionJob,
        runner_mode: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Execute code within the configured runner backend.
        Never falls back to host execution if container runner fails or is offline.
        """
        runner = cls.get_runner(runner_mode=runner_mode)
        return runner.run(job)

    @classmethod
    def get_sandbox_status(cls) -> Dict[str, Any]:
        """
        Diagnostic check reporting whether the secure container sandbox is available.
        """
        mode = os.environ.get("EXECUTION_RUNNER_MODE", "subprocess").lower()
        app_env = os.environ.get("APP_ENV", "development").lower()
        docker_runner = DockerRunner()
        docker_available = docker_runner.is_available()

        is_production_ready = docker_available
        blocker = None if docker_available else "Docker daemon is not running or unavailable on host."

        from .languages import LanguageDetector

        return {
            "configured_mode": mode,
            "environment": app_env,
            "container_sandbox_available": docker_available,
            "is_production_ready": is_production_ready,
            "blocker_reason": blocker,
            "docker_isolation_info": docker_runner.get_isolation_info(),
            "supported_languages": LanguageDetector.get_all_languages(),
        }
