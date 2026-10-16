"""
Educational Domain Request and Response Schemas
Classrooms, courses, assignments, enrollments, and concept analytics.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ClassroomCreateRequest(BaseModel):
    organization_id: str
    name: str = Field(min_length=2, max_length=128)
    course_name: Optional[str] = "Default Course"


class ClassroomResponse(BaseModel):
    id: str
    organization_id: str
    course_id: str
    name: str
    created_by_user_id: str
    created_at: datetime
    student_count: int = 0


class ClassroomEnrollRequest(BaseModel):
    student_user_id: str


class EnrollmentResponse(BaseModel):
    id: str
    classroom_id: str
    student_user_id: str
    status: str
    enrolled_at: datetime


class AssignmentCreateRequest(BaseModel):
    problem_version_id: str
    title: str = Field(min_length=2, max_length=255)
    due_at: Optional[datetime] = None
    max_attempts: Optional[int] = None


class AssignmentResponse(BaseModel):
    id: str
    classroom_id: str
    problem_version_id: str
    title: str
    available_from: datetime
    due_at: Optional[datetime] = None
    max_attempts: Optional[int] = None
    created_by_user_id: str


class StudentConceptProgressResponse(BaseModel):
    concept_name: str
    attempt_count: int
    successful_attempt_count: int
    mastery_percentage: float
    last_attempt_at: datetime


class ClassroomAnalyticsResponse(BaseModel):
    classroom_id: str
    classroom_name: str
    total_students: int
    concept_mastery_summary: List[StudentConceptProgressResponse]
