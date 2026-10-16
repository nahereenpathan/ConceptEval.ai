"""
Authorized Dataset Content Import Pipeline
Validates original, institution-owned, or open-licensed problem catalogs,
enforcing license declarations, duplicate detection, AST rubric creation,
and comprehensive audit logging.
"""

import csv
import io
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.problem import (
    ContentImportAudit,
    GradingRubric,
    Problem,
    ProblemTopic,
    ProblemTopicAssignment,
    ProblemVersion,
    TestCase,
)
from app.schemas.problem import (
    ContentImportConceptRule,
    ContentImportItem,
    ContentImportReportResponse,
    ContentImportRequest,
    ContentImportTestCase,
)


AUTHORIZED_LICENSES = {
    "cc-by-4.0",
    "cc-by-sa-4.0",
    "cc0-1.0",
    "mit",
    "apache-2.0",
    "bsd-2-clause",
    "bsd-3-clause",
    "institution-owned",
    "educational-use-only",
    "original-pedagogical",
}


def normalize_text(text: str) -> str:
    """Normalize text by lowercasing, removing punctuation and condensing whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compute_content_fingerprint(title: str, statement: str) -> str:
    """Compute deterministic SHA-256 hash of normalized title and core statement."""
    import hashlib
    norm_title = normalize_text(title)
    norm_statement = normalize_text(statement[:300] if statement else "")
    payload = f"{norm_title}::{norm_statement}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def generate_slug(title: str) -> str:
    """Generate a clean URL-friendly slug from problem title."""
    slug = re.sub(r"[^\w\s-]", "", title.lower().strip())
    slug = re.sub(r"[\s_-]+", "-", slug)
    return slug.strip("-")


def parse_csv_dataset(csv_content: str, source_name: str, license_type: str, provenance_url: Optional[str] = None) -> ContentImportRequest:
    """
    Parse a CSV export of coding problems into a validated ContentImportRequest.
    Expected CSV columns:
    title, statement_markdown, difficulty, language, topics, expected_concepts, test_cases_json, rubric_rules_json
    """
    cleaned_csv = csv_content.strip().lstrip("\ufeff")
    if not cleaned_csv:
        raise ValueError("CSV dataset is empty.")

    reader = csv.DictReader(io.StringIO(cleaned_csv))
    if not reader.fieldnames:
        raise ValueError("CSV dataset must contain a header row.")

    problems: List[ContentImportItem] = []

    for row in reader:
        title = row.get("title", "").strip()
        if not title:
            continue
        statement = row.get("statement_markdown", "").strip()
        difficulty = row.get("difficulty", "medium").lower().strip()
        language = row.get("language", "python").lower().strip()

        # Parse topics list (comma-separated)
        raw_topics = row.get("topics", "")
        topics = [t.strip().lower() for t in raw_topics.split(",") if t.strip()]

        # Parse expected concepts (comma-separated)
        raw_concepts = row.get("expected_concepts", "")
        expected_concepts = [c.strip().lower() for c in raw_concepts.split(",") if c.strip()]

        # Parse test cases JSON
        test_cases: List[ContentImportTestCase] = []
        raw_tests = row.get("test_cases_json", "")
        if raw_tests:
            try:
                tc_data = json.loads(raw_tests)
                for tc in tc_data:
                    test_cases.append(ContentImportTestCase(**tc))
            except Exception:
                pass

        # Parse concept rules JSON
        concept_rules: List[ContentImportConceptRule] = []
        raw_rules = row.get("rubric_rules_json", "")
        if raw_rules:
            try:
                rules_data = json.loads(raw_rules)
                for r in rules_data:
                    concept_rules.append(ContentImportConceptRule(**r))
            except Exception:
                pass

        # Fallback if no concept rules specified: construct from expected_concepts
        if not concept_rules and expected_concepts:
            for c in expected_concepts:
                concept_rules.append(
                    ContentImportConceptRule(
                        concept=c,
                        rule_id=f"rule_require_{c}",
                        accepted_constructs=[c],
                        required=True,
                        min_occurrences=1,
                        description=f"Must use {c} construct in code implementation.",
                    )
                )

        problems.append(
            ContentImportItem(
                title=title,
                slug=row.get("slug") or generate_slug(title),
                statement_markdown=statement,
                difficulty=difficulty if difficulty in ("easy", "medium", "hard") else "medium",
                language=language,
                topics=topics,
                expected_concepts=expected_concepts,
                constraints=[c.strip() for c in row.get("constraints", "").split(";") if c.strip()],
                input_format=row.get("input_format"),
                output_format=row.get("output_format"),
                starter_code=row.get("starter_code"),
                reference_solution=row.get("reference_solution"),
                test_cases=test_cases,
                concept_rules=concept_rules,
            )
        )

    return ContentImportRequest(
        source_name=source_name,
        license_type=license_type,
        provenance_url=provenance_url,
        problems=problems,
    )


async def import_problem_dataset(
    db: AsyncSession,
    import_request: ContentImportRequest,
    user_id: str,
    import_format: str = "json",
) -> ContentImportReportResponse:
    """
    Execute validated content import with strict duplicate detection,
    AST rubric creation, test cases, and audit logging.
    """
    # 1. License compliance check
    if not import_request.license_type or not import_request.license_type.strip():
        raise ValueError("Content import rejected: explicit license_type must be declared.")

    norm_license = import_request.license_type.strip().lower()
    if norm_license not in AUTHORIZED_LICENSES:
        raise ValueError(
            f"Content import rejected: License '{import_request.license_type}' is not authorized. "
            f"Permitted license types include: {', '.join(sorted(AUTHORIZED_LICENSES))}"
        )

    # 2. Pre-fetch existing problem slugs, fingerprints, and titles to detect duplicates
    existing_problems_res = await db.execute(
        select(Problem.slug, Problem.content_fingerprint, ProblemVersion.title)
        .join(ProblemVersion, ProblemVersion.problem_id == Problem.id)
    )
    existing_slugs = set()
    existing_fingerprints = set()
    existing_norm_titles = set()
    for s, fp, t in existing_problems_res.all():
        if s:
            existing_slugs.add(s)
        if fp:
            existing_fingerprints.add(fp)
        if t:
            existing_norm_titles.add(normalize_text(t))

    # Pre-fetch existing topics for assignment mapping
    topics_res = await db.execute(select(ProblemTopic))
    topics_by_slug = {t.slug: t.id for t in topics_res.scalars().all()}

    imported_slugs: List[str] = []
    skipped_slugs: List[str] = []
    errors: List[str] = []

    now = datetime.now(timezone.utc)

    for item in import_request.problems:
        slug = item.slug or generate_slug(item.title)
        norm_title = normalize_text(item.title)
        fingerprint = compute_content_fingerprint(item.title, item.statement_markdown)

        # Multi-factor duplicate check: exact slug, normalized title, or content fingerprint
        if (
            slug in existing_slugs
            or slug in imported_slugs
            or norm_title in existing_norm_titles
            or fingerprint in existing_fingerprints
        ):
            skipped_slugs.append(slug)
            continue

        try:
            # Create root Problem entity with content fingerprint
            problem = Problem(
                owner_type="platform",
                slug=slug,
                content_fingerprint=fingerprint,
                status="published",
                created_by_user_id=user_id,
            )
            db.add(problem)
            await db.flush()

            # Create immutable ProblemVersion entity with starter_code and content_fingerprint
            constraints_json = json.dumps(item.constraints) if item.constraints else None
            pv = ProblemVersion(
                problem_id=problem.id,
                version_number=1,
                title=item.title,
                statement_markdown=item.statement_markdown,
                difficulty=item.difficulty.lower(),
                language=item.language.lower(),
                constraints_json=constraints_json,
                input_format=item.input_format,
                output_format=item.output_format,
                starter_code=item.starter_code,
                reference_solution=item.reference_solution,
                content_fingerprint=fingerprint,
                published_at=now,
            )
            db.add(pv)
            await db.flush()

            # Assign topic tags
            for topic_name in item.topics:
                raw_name = topic_name.strip()
                if not raw_name:
                    continue
                norm_slug = generate_slug(raw_name)
                topic_id = topics_by_slug.get(norm_slug) or topics_by_slug.get(raw_name.lower())
                if not topic_id:
                    # Dynamically register new topic in taxonomy
                    new_topic = ProblemTopic(
                        name=raw_name.replace("-", " ").replace("_", " ").title(),
                        slug=norm_slug,
                    )
                    db.add(new_topic)
                    await db.flush()
                    topic_id = new_topic.id
                    topics_by_slug[norm_slug] = topic_id
                    topics_by_slug[raw_name.lower()] = topic_id

                assignment = ProblemTopicAssignment(
                    problem_version_id=pv.id,
                    topic_id=topic_id,
                )
                db.add(assignment)


            # Build rubric schema
            concept_rules_payload = [
                {
                    "concept": r.concept,
                    "rule_id": r.rule_id,
                    "accepted_constructs": r.accepted_constructs or [r.concept],
                    "required": r.required,
                    "min_occurrences": r.min_occurrences,
                    "description": r.description or f"Requires {r.concept}",
                }
                for r in item.concept_rules
            ]

            rubric_schema = {
                "schema_version": "1.0.0",
                "max_score": 100.0,
                "functional_weight": item.functional_weight,
                "concept_weight": item.concept_weight,
                "algorithmic_weight": 0.0,
                "constraint_weight": 0.0,
                "required_concepts": concept_rules_payload,
                "prohibited_constructs": [],
                "allow_partial_concept_credit": True,
            }

            rubric = GradingRubric(
                problem_version_id=pv.id,
                version_number=1,
                schema_version="1.0.0",
                rubric_json=json.dumps(rubric_schema),
                status="published",
                created_by_user_id=user_id,
                reviewed_by_user_id=user_id,
                reviewed_at=now,
                published_at=now,
            )
            db.add(rubric)

            # Add test cases
            for tc in item.test_cases:
                test_case = TestCase(
                    problem_version_id=pv.id,
                    visibility=tc.visibility if tc.visibility in ("sample", "public", "hidden") else "sample",
                    input_data=tc.input_data,
                    expected_output=tc.expected_output,
                    weight=tc.weight,
                    timeout_ms=tc.timeout_ms,
                    memory_limit_mb=tc.memory_limit_mb,
                    is_active=True,
                )
                db.add(test_case)

            imported_slugs.append(slug)
            existing_slugs.add(slug)
            existing_norm_titles.add(norm_title)
            existing_fingerprints.add(fingerprint)

        except Exception as e:
            errors.append(f"Failed to import '{slug}': {str(e)}")

    # Create provenance and audit log
    audit = ContentImportAudit(
        imported_by_user_id=user_id,
        source_name=import_request.source_name,
        license_type=import_request.license_type,
        provenance_url=import_request.provenance_url,
        format=import_format,
        total_processed=len(import_request.problems),
        imported_count=len(imported_slugs),
        skipped_duplicates=len(skipped_slugs),
        errors_json=json.dumps(errors) if errors else None,
        import_metadata_json=json.dumps({
            "imported_slugs": imported_slugs,
            "skipped_slugs": skipped_slugs,
        }),
    )
    db.add(audit)
    await db.commit()

    return ContentImportReportResponse(
        audit_id=audit.id,
        source_name=import_request.source_name,
        license_type=import_request.license_type,
        total_processed=len(import_request.problems),
        imported_count=len(imported_slugs),
        skipped_duplicates=len(skipped_slugs),
        imported_slugs=imported_slugs,
        skipped_slugs=skipped_slugs,
        errors=errors,
    )
