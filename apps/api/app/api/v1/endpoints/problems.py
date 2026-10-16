"""
Problem Library API Endpoints
Browsing published problems, viewing problem constraints, and retrieving public sample test cases.
"""

from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.problem import Problem, ProblemTopic, ProblemVersion, TestCase
from app.schemas.problem import (
    ProblemDetailResponse,
    ProblemSummaryResponse,
    TestCaseSampleResponse,
    TopicResponse,
)

router = APIRouter(prefix="/problems", tags=["Problem Library"])


@router.get("", response_model=List[ProblemSummaryResponse])
async def list_published_problems(
    db: Annotated[AsyncSession, Depends(get_db)],
    difficulty: Optional[str] = Query(None, description="Filter by difficulty (easy, medium, hard)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """List all published coding problems available for practice."""
    query = (
        select(ProblemVersion)
        .join(Problem, Problem.id == ProblemVersion.problem_id)
        .where(Problem.status == "published")
        .options(selectinload(ProblemVersion.problem))
        .offset(skip)
        .limit(limit)
    )

    if difficulty:
        query = query.where(ProblemVersion.difficulty == difficulty.lower())

    versions = (await db.execute(query)).scalars().all()

    results = []
    for pv in versions:
        results.append(
            ProblemSummaryResponse(
                id=pv.problem.id,
                slug=pv.problem.slug,
                title=pv.title,
                difficulty=pv.difficulty,
                language=pv.language,
                version_number=pv.version_number,
                topics=[],
            )
        )
    return results


@router.get("/topics", response_model=List[TopicResponse])
async def list_topics(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve available topic taxonomies (e.g. Loops, Recursion, OOP)."""
    stmt = select(ProblemTopic).order_by(ProblemTopic.name)
    topics = (await db.execute(stmt)).scalars().all()
    return [
        TopicResponse(id=t.id, name=t.name, slug=t.slug)
        for t in topics
    ]


@router.get("/{problem_id}", response_model=ProblemDetailResponse)
async def get_problem_details(
    problem_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve problem statement, constraints, and public sample test cases."""
    stmt = (
        select(ProblemVersion)
        .join(Problem, Problem.id == ProblemVersion.problem_id)
        .where(Problem.id == problem_id, Problem.status == "published")
        .options(
            selectinload(ProblemVersion.problem),
            selectinload(ProblemVersion.test_cases),
        )
        .order_by(ProblemVersion.version_number.desc())
    )
    pv = (await db.execute(stmt)).scalars().first()

    if not pv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROBLEM_NOT_FOUND", "message": "Published problem not found."},
        )

    # Strictly expose ONLY sample test cases to student callers
    sample_cases = [
        TestCaseSampleResponse(
            id=tc.id,
            input_data=tc.input_data,
            expected_output=tc.expected_output,
        )
        for tc in pv.test_cases
        if tc.visibility in ("sample", "public") and tc.is_active
    ]

    return ProblemDetailResponse(
        id=pv.problem.id,
        slug=pv.problem.slug,
        title=pv.title,
        statement_markdown=pv.statement_markdown,
        difficulty=pv.difficulty,
        language=pv.language,
        version_number=pv.version_number,
        constraints_json=pv.constraints_json,
        input_format=pv.input_format,
        output_format=pv.output_format,
        topics=[],
        sample_test_cases=sample_cases,
    )


@router.get("/{problem_id}/samples", response_model=List[TestCaseSampleResponse])
async def get_sample_test_cases(
    problem_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve public sample cases for running editor tests."""
    stmt = (
        select(TestCase)
        .join(ProblemVersion, ProblemVersion.id == TestCase.problem_version_id)
        .join(Problem, Problem.id == ProblemVersion.problem_id)
        .where(
            Problem.id == problem_id,
            Problem.status == "published",
            TestCase.visibility.in_(["sample", "public"]),
            TestCase.is_active == True,
        )
    )
    test_cases = (await db.execute(stmt)).scalars().all()

    return [
        TestCaseSampleResponse(
            id=tc.id,
            input_data=tc.input_data,
            expected_output=tc.expected_output,
        )
        for tc in test_cases
    ]
