"""
Standard Error Response Schema
Complies with Section 7.7 of the Architecture Blueprint.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(description="Machine-readable uppercase error code")
    message: str = Field(description="Human-readable explanation of the error")
    request_id: Optional[str] = Field(default=None, description="Unique trace request ID")


class ErrorResponse(BaseModel):
    error: ErrorDetail
