"""
Execution Runner Protocol & Data Contracts
Defines bounded input and output objects for the isolated execution environment.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ExecutionJob(BaseModel):
    """Execution request submitted to the sandbox worker."""
    job_id: str
    source_code: str
    stdin_input: str = ""
    timeout_seconds: float = Field(default=3.0, ge=0.1, le=15.0)
    memory_limit_mb: int = Field(default=128, ge=16, le=512)
    max_output_bytes: int = Field(default=65536, ge=1024, le=1048576)


class ExecutionResult(BaseModel):
    """Bounded result returned by the sandbox execution runner."""
    job_id: str
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False
    memory_exceeded: bool = False
    error_type: Optional[str] = None  # "TIMEOUT", "MEMORY_LIMIT", "NON_ZERO_EXIT", "SYSTEM_ERROR"
    truncated: bool = False
