"""
API v1 Master Router
Aggregates authentication, problem library, and submission endpoints.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    analytics,
    auth,
    authoring,
    classrooms,
    problems,
    submissions,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(problems.router)
api_router.include_router(submissions.router)
api_router.include_router(authoring.router)
api_router.include_router(classrooms.router)
api_router.include_router(analytics.router)

