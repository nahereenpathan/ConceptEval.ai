"""
Base Runner Interface
Abstract base class defining the contract for sandboxed and subprocess code execution runners.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
from .protocol import ExecutionJob, ExecutionResult


class BaseRunner(ABC):
    """Abstract base class for code execution runners."""

    @abstractmethod
    def run(self, job: ExecutionJob) -> ExecutionResult:
        """Execute a code execution job and return a bounded result."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the execution runtime environment is installed and functional."""
        pass

    @abstractmethod
    def get_isolation_info(self) -> Dict[str, Any]:
        """Return diagnostic metadata about the isolation boundaries and mechanisms enforced."""
        pass
