"""
Problem Library Schemas
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class TopicResponse(BaseModel):
    id: str
    name: str
    slug: str


class TestCaseSampleResponse(BaseModel):
    id: str
    input_data: str
    expected_output: str


class ProblemSummaryResponse(BaseModel):
    id: str
    slug: str
    title: str
    difficulty: str
    language: str
    version_number: int
    topics: List[str] = Field(default_factory=list)


class ProblemDetailResponse(BaseModel):
    id: str
    slug: str
    title: str
    statement_markdown: str
    difficulty: str
    language: str
    version_number: int
    constraints_json: Optional[str] = None
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    topics: List[str] = Field(default_factory=list)
    sample_test_cases: List[TestCaseSampleResponse] = Field(default_factory=list)
