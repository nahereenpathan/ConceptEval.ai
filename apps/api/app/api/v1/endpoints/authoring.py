"""
Problem Authoring, NLP Intent Extraction, and Validation Endpoints
Provides educators with full creation, drafting, preview validation,
and publishing workflows for concept-aware coding problems.
"""

import json
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.content_import.pipeline import (
    compute_content_fingerprint,
    generate_slug,
    normalize_text,
)
from app.evaluation.ast_analysis.analyzer import ASTAnalyzer
from app.evaluation.intent.extractor import NLPIntentExtractor
from app.models.organization import OrganizationMembership
from app.models.problem import (
    GradingRubric,
    Problem,
    ProblemTopic,
    ProblemTopicAssignment,
    ProblemVersion,
    TestCase,
)
from app.models.user import User

from runner.executor import CodeExecutor
from runner.protocol import ExecutionJob

router = APIRouter(prefix="/authoring", tags=["Authoring"])


# ---------------------------------------------------------------------------
# Authorization Helper
# ---------------------------------------------------------------------------
async def require_authoring_access(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Verify that current user is an educator or administrator authorized to author problems."""
    stmt = select(OrganizationMembership).where(
        OrganizationMembership.user_id == current_user.id,
        OrganizationMembership.role.in_(["teacher", "org_admin", "admin"]),
        OrganizationMembership.status == "active",
    )
    res = await db.execute(stmt)
    membership = res.scalar_one_or_none()
    if not membership:
        email = current_user.email.lower()
        if "teacher" not in email and "admin" not in email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "Only educators or administrators are authorized to author or publish problems."},
            )
    return current_user


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class IntentExtractionRequest(BaseModel):
    problem_text: str = Field(min_length=5, max_length=10000)


class IntentExtractionResponse(BaseModel):
    rubric_draft: Dict[str, Any]
    extracted_concepts: List[Dict[str, Any]]
    extracted_prohibitions: List[Dict[str, Any]]
    confidence: float
    requires_human_review: bool
    review_notes: List[str]


class AuthoringTestCase(BaseModel):
    id: Optional[str] = None
    input_data: str
    expected_output: str
    visibility: str = "sample"  # sample, public, hidden
    weight: float = 1.0
    timeout_ms: int = 3000
    memory_limit_mb: int = 128


class AuthoringConceptRule(BaseModel):
    concept: str
    rule_id: Optional[str] = None
    accepted_constructs: List[str] = Field(default_factory=list)
    required: bool = True
    min_occurrences: int = 1
    description: str = ""


class AuthoringProblemRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    slug: Optional[str] = None
    statement_markdown: str = Field(..., min_length=10)
    difficulty: str = Field(default="medium")  # easy, medium, hard
    language: str = "python"
    topics: List[str] = Field(default_factory=list)
    constraints: Optional[List[str]] = Field(default_factory=list)
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    starter_code: Optional[str] = None
    reference_solution: Optional[str] = None
    test_cases: List[AuthoringTestCase] = Field(default_factory=list)
    concept_rules: List[AuthoringConceptRule] = Field(default_factory=list)
    prohibited_constructs: List[str] = Field(default_factory=list)
    functional_weight: float = 60.0
    concept_weight: float = 40.0
    status: str = Field(default="draft")  # draft, published


class AuthoringProblemItemResponse(BaseModel):
    id: str
    slug: str
    title: str
    statement_markdown: str
    difficulty: str
    language: str
    status: str
    version_number: int
    topics: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    starter_code: Optional[str] = None
    reference_solution: Optional[str] = None
    test_cases: List[AuthoringTestCase] = Field(default_factory=list)
    concept_rules: List[AuthoringConceptRule] = Field(default_factory=list)
    prohibited_constructs: List[str] = Field(default_factory=list)
    functional_weight: float = 60.0
    concept_weight: float = 40.0
    created_at: str


class AuthoringValidationRequest(BaseModel):
    source_code: str
    language: str = "python"
    test_cases: List[AuthoringTestCase] = Field(default_factory=list)
    concept_rules: List[AuthoringConceptRule] = Field(default_factory=list)
    prohibited_constructs: List[str] = Field(default_factory=list)


class AuthoringValidationResponse(BaseModel):
    all_passed: bool
    functional_passed: bool
    concept_passed: bool
    syntax_valid: bool
    syntax_error: Optional[str] = None
    total_tests: int
    passed_tests: int
    case_results: List[Dict[str, Any]]
    concept_results: List[Dict[str, Any]]
    validation_messages: List[str]


# ---------------------------------------------------------------------------
# NLP Intent Extraction
# ---------------------------------------------------------------------------
@router.post("/extract-intent", response_model=IntentExtractionResponse)
async def extract_intent(req: IntentExtractionRequest):
    """
    Extracts programming concepts and prohibitions from natural-language statements
    to construct a draft grading rubric with confidence metrics.
    """
    try:
        result = NLPIntentExtractor.extract_intent(req.problem_text)
        return IntentExtractionResponse(
            rubric_draft=result.rubric_draft.model_dump(),
            extracted_concepts=result.extracted_concepts,
            extracted_prohibitions=result.extracted_prohibitions,
            confidence=result.confidence,
            requires_human_review=result.requires_human_review,
            review_notes=result.review_notes,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INTENT_EXTRACTION_FAILED", "message": str(exc)},
        )


# ---------------------------------------------------------------------------
# Validation / Preview Runner
# ---------------------------------------------------------------------------
@router.post("/validate", response_model=AuthoringValidationResponse)
async def validate_problem_solution(
    req: AuthoringValidationRequest,
    current_user: Annotated[User, Depends(require_authoring_access)],
):
    """
    Validates a solution against authored test cases and AST concept rules
    in the secure sandbox without saving to database.
    """
    # 1. AST Concept Check
    from evaluation_specifications.models import (
        ConceptType,
        ProhibitedConstruct,
        RequiredConcept,
    )

    req_concepts = []
    for r in req.concept_rules:
        c_type = None
        for member in ConceptType:
            if member.value == r.concept.lower():
                c_type = member
                break
        if c_type:
            req_concepts.append(
                RequiredConcept(
                    concept=c_type,
                    rule_id=r.rule_id or f"rule_{r.concept.lower()}",
                    min_occurrences=r.min_occurrences,
                    description=r.description or f"Requires {r.concept}",
                )
            )

    prohibitions = []
    for p in req.prohibited_constructs:
        c_type = None
        for member in ConceptType:
            if member.value == p.lower():
                c_type = member
                break
        if c_type:
            prohibitions.append(
                ProhibitedConstruct(
                    construct=c_type,
                    rule_id=f"prohibit_{p.lower()}",
                    description=f"Forbidden construct: {p}",
                )
            )

    norm_lang = (req.language or "python").lower().strip()
    if norm_lang in ("c++", "cpp"):
        norm_lang = "cpp"

    syntax_valid, evidences, syntax_error = ASTAnalyzer.evaluate_concepts(
        req.source_code, req_concepts, prohibitions, language=norm_lang
    )

    concept_results = [
        {
            "concept": ev.concept.value if hasattr(ev.concept, "value") else str(ev.concept),
            "passed": ev.passed,
            "message": ev.message,
        }
        for ev in evidences
    ]
    concept_passed = all(ev.passed for ev in evidences) if evidences else True

    if not syntax_valid:
        return AuthoringValidationResponse(
            all_passed=False,
            functional_passed=False,
            concept_passed=False,
            syntax_valid=False,
            syntax_error=syntax_error,
            total_tests=len(req.test_cases),
            passed_tests=0,
            case_results=[],
            concept_results=concept_results,
            validation_messages=[f"Syntax Error ({norm_lang.capitalize()}): {syntax_error}"],
        )

    # 2. Functional Sandbox Execution
    case_results = []
    passed_tests = 0
    has_compile_error = False

    for idx, tc in enumerate(req.test_cases):
        job = ExecutionJob(
            job_id=f"preview_tc_{idx}",
            source_code=req.source_code,
            language=norm_lang,
            stdin_input=tc.input_data or "",
            timeout_seconds=min(tc.timeout_ms / 1000.0, 5.0),
            memory_limit_mb=tc.memory_limit_mb or 128,
        )
        res = CodeExecutor.run_code(job)
        if res.compilation_error or res.error_type == "COMPILATION_ERROR":
            has_compile_error = True
            case_results.append({
                "case_number": idx + 1,
                "visibility": tc.visibility,
                "input_data": tc.input_data,
                "expected_output": tc.expected_output,
                "actual_output": "",
                "passed": False,
                "error": res.stderr or "Compilation Error",
                "execution_time_ms": res.duration_ms,
            })
            break
        actual = (res.stdout or "").strip()
        expected = (tc.expected_output or "").strip()
        passed = (actual == expected and res.exit_code == 0)
        if passed:
            passed_tests += 1

        case_results.append({
            "case_number": idx + 1,
            "visibility": tc.visibility,
            "input_data": tc.input_data,
            "expected_output": tc.expected_output,
            "actual_output": actual,
            "passed": passed,
            "execution_time_ms": res.duration_ms,
            "stderr": res.stderr if res.stderr else None,
        })

    functional_passed = (passed_tests == len(req.test_cases)) if req.test_cases else True
    all_passed = functional_passed and concept_passed

    messages = []
    if all_passed:
        messages.append("All test cases passed and all conceptual rules satisfied.")
    else:
        if not functional_passed:
            messages.append(f"Functional failures: {len(req.test_cases) - passed_tests} test case(s) failed.")
        if not concept_passed:
            messages.append("Concept violations: Code does not satisfy required AST rules.")

    return AuthoringValidationResponse(
        all_passed=all_passed,
        functional_passed=functional_passed,
        concept_passed=concept_passed,
        syntax_valid=True,
        syntax_error=None,
        total_tests=len(req.test_cases),
        passed_tests=passed_tests,
        case_results=case_results,
        concept_results=concept_results,
        validation_messages=messages,
    )


# ---------------------------------------------------------------------------
# Authoring CRUD
# ---------------------------------------------------------------------------
@router.get("/problems", response_model=List[AuthoringProblemItemResponse])
async def list_authored_problems(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authoring_access)],
):
    """List problems created by this educator (both draft and published)."""
    stmt = (
        select(ProblemVersion)
        .join(Problem, Problem.id == ProblemVersion.problem_id)
        .where(Problem.created_by_user_id == current_user.id)
        .options(
            selectinload(ProblemVersion.problem),
            selectinload(ProblemVersion.test_cases),
            selectinload(ProblemVersion.rubrics),
            selectinload(ProblemVersion.topic_assignments).selectinload(ProblemTopicAssignment.topic),
        )
        .order_by(ProblemVersion.created_at.desc())
    )
    pvs = (await db.execute(stmt)).scalars().all()

    results = []
    for pv in pvs:
        topics = [a.topic.name for a in pv.topic_assignments if a.topic]
        constraints = []
        if pv.constraints_json:
            try:
                constraints = json.loads(pv.constraints_json)
                if not isinstance(constraints, list):
                    constraints = [str(constraints)]
            except Exception:
                constraints = [pv.constraints_json]

        # Extract rubrics
        concept_rules = []
        prohibited = []
        f_weight = 60.0
        c_weight = 40.0
        if pv.rubrics:
            r = pv.rubrics[0]
            try:
                r_data = json.loads(r.rubric_json)
                f_weight = r_data.get("functional_weight", 60.0)
                c_weight = r_data.get("concept_weight", 40.0)
                for cr in r_data.get("required_concepts", []):
                    concept_rules.append(AuthoringConceptRule(
                        concept=cr.get("concept", ""),
                        rule_id=cr.get("rule_id", ""),
                        accepted_constructs=cr.get("accepted_constructs", []),
                        required=cr.get("required", True),
                        min_occurrences=cr.get("min_occurrences", 1),
                        description=cr.get("description", ""),
                    ))
                prohibited = r_data.get("prohibited_constructs", [])
            except Exception:
                pass

        test_cases = [
            AuthoringTestCase(
                id=tc.id,
                input_data=tc.input_data,
                expected_output=tc.expected_output,
                visibility=tc.visibility,
                weight=tc.weight,
                timeout_ms=tc.timeout_ms,
                memory_limit_mb=tc.memory_limit_mb,
            )
            for tc in pv.test_cases
            if tc.is_active
        ]

        results.append(
            AuthoringProblemItemResponse(
                id=pv.problem.id,
                slug=pv.problem.slug,
                title=pv.title,
                statement_markdown=pv.statement_markdown,
                difficulty=pv.difficulty,
                language=pv.language,
                status=pv.problem.status,
                version_number=pv.version_number,
                topics=topics,
                constraints=constraints,
                input_format=pv.input_format,
                output_format=pv.output_format,
                starter_code=pv.starter_code,
                reference_solution=pv.reference_solution,
                test_cases=test_cases,
                concept_rules=concept_rules,
                prohibited_constructs=prohibited,
                functional_weight=f_weight,
                concept_weight=c_weight,
                created_at=pv.created_at.isoformat() if pv.created_at else "",
            )
        )

    return results


@router.post("/problems", response_model=AuthoringProblemItemResponse, status_code=status.HTTP_201_CREATED)
async def create_authored_problem(
    payload: AuthoringProblemRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authoring_access)],
):
    """
    Create a new problem (Draft or Published) with full AST rubrics and test cases.
    Enforces multi-factor uniqueness checks on slug, title, and content fingerprint.
    Teacher-authored questions require at least 1 public test case before publishing.
    """
    slug = payload.slug or generate_slug(payload.title)
    norm_title = normalize_text(payload.title)
    fingerprint = compute_content_fingerprint(payload.title, payload.statement_markdown)

    # Multi-factor uniqueness validation: slug, content fingerprint, or identical normalized title
    existing_problem = (
        await db.execute(
            select(Problem)
            .join(ProblemVersion, ProblemVersion.problem_id == Problem.id)
            .where(
                or_(
                    Problem.slug == slug,
                    Problem.content_fingerprint == fingerprint,
                    func.lower(ProblemVersion.title) == norm_title,
                )
            )
            .options(selectinload(Problem.versions))
        )
    ).scalars().first()

    if existing_problem:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_PROBLEM",
                "message": f"A problem with this title, slug, or content already exists ('{existing_problem.slug}'). Duplicate problem creation is blocked.",
                "existing_problem_id": existing_problem.id,
                "existing_slug": existing_problem.slug,
            },
        )

    # Validation when publishing directly
    if payload.status == "published":
        if not payload.test_cases:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "VALIDATION_ERROR", "message": "At least one test case is required to publish a problem."},
            )

    now = datetime.now(timezone.utc)

    # 1. Master Problem with content fingerprint
    problem = Problem(
        owner_type="platform",
        slug=slug,
        content_fingerprint=fingerprint,
        status=payload.status,
        created_by_user_id=current_user.id,
    )
    db.add(problem)
    await db.flush()

    # 2. Problem Version with starter_code and content fingerprint
    constraints_json = json.dumps(payload.constraints) if payload.constraints else None
    pv = ProblemVersion(
        problem_id=problem.id,
        version_number=1,
        title=payload.title,
        statement_markdown=payload.statement_markdown,
        difficulty=payload.difficulty.lower(),
        language=payload.language.lower(),
        constraints_json=constraints_json,
        input_format=payload.input_format,
        output_format=payload.output_format,
        starter_code=payload.starter_code,
        reference_solution=payload.reference_solution,
        content_fingerprint=fingerprint,
        published_at=now if payload.status == "published" else None,
    )
    db.add(pv)
    await db.flush()

    # 3. Topic Assignments
    for topic_name in payload.topics:
        raw_name = topic_name.strip()
        if not raw_name:
            continue
        norm_slug = generate_slug(raw_name)
        topic_obj = (await db.execute(select(ProblemTopic).where(or_(ProblemTopic.slug == norm_slug, ProblemTopic.name.ilike(raw_name))))).scalar_one_or_none()
        if not topic_obj:
            topic_obj = ProblemTopic(
                name=raw_name.title(),
                slug=norm_slug,
            )
            db.add(topic_obj)
            await db.flush()

        db.add(ProblemTopicAssignment(
            problem_version_id=pv.id,
            topic_id=topic_obj.id,
        ))

    # 4. Grading Rubric
    concept_rules_payload = [
        {
            "concept": r.concept,
            "rule_id": r.rule_id or f"rule_{generate_slug(r.concept)}",
            "accepted_constructs": r.accepted_constructs or [r.concept],
            "required": r.required,
            "min_occurrences": r.min_occurrences,
            "description": r.description or f"Requires {r.concept}",
        }
        for r in payload.concept_rules
    ]

    rubric_schema = {
        "schema_version": "1.0.0",
        "max_score": 100.0,
        "functional_weight": payload.functional_weight,
        "concept_weight": payload.concept_weight,
        "algorithmic_weight": 0.0,
        "constraint_weight": 0.0,
        "required_concepts": concept_rules_payload,
        "prohibited_constructs": payload.prohibited_constructs,
        "allow_partial_concept_credit": True,
    }

    rubric = GradingRubric(
        problem_version_id=pv.id,
        version_number=1,
        schema_version="1.0.0",
        rubric_json=json.dumps(rubric_schema),
        status=payload.status,
        created_by_user_id=current_user.id,
        reviewed_by_user_id=current_user.id,
        reviewed_at=now,
        published_at=now if payload.status == "published" else None,
    )
    db.add(rubric)

    # 5. Test Cases
    for tc in payload.test_cases:
        db.add(TestCase(
            problem_version_id=pv.id,
            visibility=tc.visibility if tc.visibility in ("sample", "public", "hidden") else "sample",
            input_data=tc.input_data,
            expected_output=tc.expected_output,
            weight=tc.weight,
            timeout_ms=tc.timeout_ms,
            memory_limit_mb=tc.memory_limit_mb,
            is_active=True,
        ))

    await db.commit()

    return AuthoringProblemItemResponse(
        id=problem.id,
        slug=problem.slug,
        title=pv.title,
        statement_markdown=pv.statement_markdown,
        difficulty=pv.difficulty,
        language=pv.language,
        status=problem.status,
        version_number=pv.version_number,
        topics=payload.topics,
        constraints=payload.constraints or [],
        input_format=pv.input_format,
        output_format=pv.output_format,
        starter_code=payload.starter_code,
        reference_solution=pv.reference_solution,
        test_cases=payload.test_cases,
        concept_rules=payload.concept_rules,
        prohibited_constructs=payload.prohibited_constructs,
        functional_weight=payload.functional_weight,
        concept_weight=payload.concept_weight,
        created_at=problem.created_at.isoformat() if problem.created_at else now.isoformat(),
    )


@router.post("/problems/{problem_id}/publish", response_model=Dict[str, Any])
async def publish_authored_problem(
    problem_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_authoring_access)],
):
    """
    Validates that a problem has required sample cases and marks it as Published.
    """
    stmt = (
        select(Problem)
        .where(Problem.id == problem_id)
        .options(
            selectinload(Problem.versions).selectinload(ProblemVersion.test_cases),
            selectinload(Problem.versions).selectinload(ProblemVersion.rubrics),
        )
    )
    problem = (await db.execute(stmt)).scalar_one_or_none()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROBLEM_NOT_FOUND", "message": "Problem not found."},
        )

    if problem.created_by_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "You can only publish problems you created."},
        )

    pv = problem.versions[0] if problem.versions else None
    if not pv:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Problem has no versions.")

    if not pv.test_cases:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "TESTS_REQUIRED", "message": "Cannot publish: at least one test case must be configured."},
        )

    now = datetime.now(timezone.utc)
    problem.status = "published"
    pv.published_at = now
    if pv.rubrics:
        pv.rubrics[0].status = "published"
        pv.rubrics[0].published_at = now

    await db.commit()

    return {
        "status": "published",
        "problem_id": problem.id,
        "slug": problem.slug,
        "message": f"Problem '{pv.title}' published successfully to Problem Library.",
    }
