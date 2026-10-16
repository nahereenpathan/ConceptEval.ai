"""
Database Seed Script
Populates the database with initial topics, sample published problems,
grading rubrics, and test cases for immediate local development and demonstration.
"""

import asyncio
import json
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import engine, AsyncSessionLocal
from app.models import (
    User,
    Organization,
    OrganizationMembership,
    Problem,
    ProblemVersion,
    ProblemTopic,
    ProblemTopicAssignment,
    GradingRubric,
    TestCase,
)


async def seed():
    print("🌱 Connecting to database and creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        existing_user = (await session.execute(select(User).where(User.email == "teacher@codeedu.org"))).scalar_one_or_none()
        if existing_user:
            print("Database already seeded with demo data. Skipping.")
            return

        print("👤 Creating demo users...")
        teacher = User(
            email="teacher@codeedu.org",
            password_hash=get_password_hash("TeacherPassword123!"),
            display_name="Prof. Alan Turing",
            status="active",
            email_verified_at=datetime.now(timezone.utc),
        )
        student = User(
            email="student@codeedu.org",
            password_hash=get_password_hash("StudentPassword123!"),
            display_name="Ada Lovelace",
            status="active",
            email_verified_at=datetime.now(timezone.utc),
        )
        session.add_all([teacher, student])
        await session.flush()

        print("🏛️ Creating organization...")
        org = Organization(
            name="Institute of Computer Science",
            slug="institute-cs",
            status="active",
            created_by_user_id=teacher.id,
        )
        session.add(org)
        await session.flush()

        mem_teacher = OrganizationMembership(
            organization_id=org.id,
            user_id=teacher.id,
            role="teacher",
        )
        mem_student = OrganizationMembership(
            organization_id=org.id,
            user_id=student.id,
            role="student",
        )
        session.add_all([mem_teacher, mem_student])

        print("🏷️ Creating problem topics...")
        topic_loops = ProblemTopic(name="Loops & Iteration", slug="loops")
        topic_recursion = ProblemTopic(name="Recursion", slug="recursion")
        topic_comp = ProblemTopic(name="Comprehensions", slug="comprehensions")
        session.add_all([topic_loops, topic_recursion, topic_comp])
        await session.flush()

        # Problem 1: Print Hello World Exactly 4 Times with a Loop
        print("📘 Creating Problem 1: Loop Print Hello World...")
        p1 = Problem(
            slug="print-hello-world-4-times",
            owner_type="platform",
            status="published",
            created_by_user_id=teacher.id,
        )
        session.add(p1)
        await session.flush()

        pv1 = ProblemVersion(
            problem_id=p1.id,
            version_number=1,
            title="Print Hello World 4 Times (Using a Loop)",
            statement_markdown="""### Problem Description

Write a Python program that prints the phrase `Hello World` exactly four times, with each repetition printed on a new line.

### Required Concept & Constraints
- **Loop Required:** You **MUST** use a loop (`for` or `while`).
- Simply writing multiple `print()` statements consecutively or printing repeated strings without iteration violates the concept requirement.

### Expected Output
```text
Hello World
Hello World
Hello World
Hello World
```
""",
            difficulty="easy",
            language="python",
            published_at=datetime.now(timezone.utc),
        )
        session.add(pv1)
        await session.flush()

        r1_schema = {
            "schema_version": "1.0.0",
            "max_score": 100.0,
            "functional_weight": 40.0,
            "concept_weight": 35.0,
            "algorithmic_weight": 15.0,
            "constraint_weight": 10.0,
            "required_concepts": [
                {
                    "concept": "loop",
                    "rule_id": "rule_require_loop",
                    "accepted_constructs": ["for", "while"],
                    "required": True,
                    "min_occurrences": 1,
                    "description": "Must use a loop (for or while) to repeat the print statement.",
                }
            ],
            "prohibited_constructs": [],
            "allow_partial_concept_credit": True,
        }

        rubric1 = GradingRubric(
            problem_version_id=pv1.id,
            version_number=1,
            schema_version="1.0.0",
            rubric_json=json.dumps(r1_schema),
            status="published",
            created_by_user_id=teacher.id,
            reviewed_by_user_id=teacher.id,
            reviewed_at=datetime.now(timezone.utc),
            published_at=datetime.now(timezone.utc),
        )
        session.add(rubric1)

        tc1_sample = TestCase(
            problem_version_id=pv1.id,
            visibility="sample",
            input_data="",
            expected_output="Hello World\nHello World\nHello World\nHello World",
            weight=1.0,
            timeout_ms=3000,
            is_active=True,
        )
        tc1_hidden = TestCase(
            problem_version_id=pv1.id,
            visibility="hidden",
            input_data="",
            expected_output="Hello World\nHello World\nHello World\nHello World",
            weight=1.0,
            timeout_ms=3000,
            is_active=True,
        )
        session.add_all([tc1_sample, tc1_hidden])

        # Problem 2: Recursive Factorial
        print("📘 Creating Problem 2: Recursive Factorial...")
        p2 = Problem(
            slug="recursive-factorial",
            owner_type="platform",
            status="published",
            created_by_user_id=teacher.id,
        )
        session.add(p2)
        await session.flush()

        pv2 = ProblemVersion(
            problem_id=p2.id,
            version_number=1,
            title="Factorial of N (Recursive Implementation)",
            statement_markdown="""### Problem Description

Given an integer `n` via standard input, print its factorial ($n!$).

### Required Concept & Constraints
- **Recursion Required:** You **MUST** implement the solution using a recursive function that calls itself with a valid base case.
- **No Iteration:** Do **NOT** use `for` or `while` loops.
- **No Built-in Factorial:** Do not import `math.factorial`.

### Example
**Input:**
```text
5
```
**Output:**
```text
120
```
""",
            difficulty="medium",
            language="python",
            published_at=datetime.now(timezone.utc),
        )
        session.add(pv2)
        await session.flush()

        r2_schema = {
            "schema_version": "1.0.0",
            "max_score": 100.0,
            "functional_weight": 40.0,
            "concept_weight": 35.0,
            "algorithmic_weight": 15.0,
            "constraint_weight": 10.0,
            "required_concepts": [
                {
                    "concept": "recursion",
                    "rule_id": "rule_require_recursion",
                    "accepted_constructs": ["recursion"],
                    "required": True,
                    "min_occurrences": 1,
                    "description": "Solution must contain a recursive function call.",
                }
            ],
            "prohibited_constructs": [
                {
                    "rule_id": "proh_no_loops",
                    "construct_type": "loop",
                    "forbidden_targets": ["for", "while"],
                    "description": "Iterative loops (for/while) are strictly prohibited.",
                }
            ],
            "allow_partial_concept_credit": True,
        }

        rubric2 = GradingRubric(
            problem_version_id=pv2.id,
            version_number=1,
            schema_version="1.0.0",
            rubric_json=json.dumps(r2_schema),
            status="published",
            created_by_user_id=teacher.id,
            reviewed_by_user_id=teacher.id,
            reviewed_at=datetime.now(timezone.utc),
            published_at=datetime.now(timezone.utc),
        )
        session.add(rubric2)

        tc2_1 = TestCase(
            problem_version_id=pv2.id,
            visibility="sample",
            input_data="5\n",
            expected_output="120",
            weight=1.0,
            timeout_ms=3000,
            is_active=True,
        )
        tc2_2 = TestCase(
            problem_version_id=pv2.id,
            visibility="hidden",
            input_data="1\n",
            expected_output="1",
            weight=1.0,
            timeout_ms=3000,
            is_active=True,
        )
        tc2_3 = TestCase(
            problem_version_id=pv2.id,
            visibility="hidden",
            input_data="6\n",
            expected_output="720",
            weight=1.0,
            timeout_ms=3000,
            is_active=True,
        )
        session.add_all([tc2_1, tc2_2, tc2_3])

        await session.commit()
        print("✅ Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
