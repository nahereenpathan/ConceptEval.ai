"""
Unit Tests for Database Models and Schema Integrity
Verifies that all domain models, relationships, and constraints create cleanly.
"""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from app.models import (
    Base,
    User,
    Organization,
    OrganizationMembership,
    Problem,
    ProblemVersion,
    GradingRubric,
    TestCase,
    Submission,
    EvaluationRun,
)


@pytest.mark.asyncio
async def test_database_schema_initialization():
    """Verify that all models can be mapped and tables created without constraint errors."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Create a test user
        user = User(
            email="teacher@codeedu.org",
            display_name="Professor Ada",
            status="active",
        )
        session.add(user)
        await session.flush()

        # Create an organization
        org = Organization(
            name="Computer Science Dept",
            slug="cs-dept",
            created_by_user_id=user.id,
        )
        session.add(org)
        await session.flush()

        # Create organization membership
        membership = OrganizationMembership(
            organization_id=org.id,
            user_id=user.id,
            role="teacher",
        )
        session.add(membership)

        # Create a problem and problem version
        problem = Problem(
            slug="loop-print-hello-world",
            owner_type="organization",
            owner_organization_id=org.id,
            created_by_user_id=user.id,
            status="published",
        )
        session.add(problem)
        await session.flush()

        pv = ProblemVersion(
            problem_id=problem.id,
            version_number=1,
            title="Loop Print Hello World",
            statement_markdown="Print Hello World exactly 4 times using a loop.",
            difficulty="easy",
            language="python",
        )
        session.add(pv)
        await session.flush()

        # Add rubric
        rubric = GradingRubric(
            problem_version_id=pv.id,
            version_number=1,
            rubric_json="{}",
            created_by_user_id=user.id,
            status="published",
        )
        session.add(rubric)

        # Add sample test case
        tc = TestCase(
            problem_version_id=pv.id,
            visibility="sample",
            input_data="",
            expected_output="Hello World\nHello World\nHello World\nHello World",
        )
        session.add(tc)
        await session.flush()

        # Add a student submission
        sub = Submission(
            user_id=user.id,
            organization_id=org.id,
            problem_version_id=pv.id,
            language="python",
            source_code='for i in range(4): print("Hello World")',
            source_hash="dummyhash123",
            status="completed",
        )
        session.add(sub)
        await session.flush()

        eval_run = EvaluationRun(
            submission_id=sub.id,
            rubric_id=rubric.id,
            status="completed",
        )
        session.add(eval_run)
        await session.commit()

        # Query back and verify relationships
        stmt = select(User).where(User.email == "teacher@codeedu.org")
        queried_user = (await session.execute(stmt)).scalar_one()
        assert queried_user.display_name == "Professor Ada"

        sub_stmt = select(Submission).where(Submission.user_id == user.id)
        queried_sub = (await session.execute(sub_stmt)).scalar_one()
        assert "for i in range(4)" in queried_sub.source_code

    await test_engine.dispose()
