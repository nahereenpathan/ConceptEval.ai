"""
Problem Library API Endpoints
Browsing published problems, search, filtering, pagination, bookmarks,
student submission history, and authorized dataset imports.
Strictly preserves tenant boundaries and hides private test cases from students.
"""

import json
import math
import sys
import uuid
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, Union
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_current_user_optional
from app.content_import.pipeline import import_problem_dataset, parse_csv_dataset
from app.core.authz import (
    authorize_problem_access,
    get_user_organization_ids,
    verify_organization_access,
)
from app.db.session import get_db
from app.evaluation.ast_analysis.analyzer import ASTAnalyzer
from app.models.problem import (
    GradingRubric,
    Problem,
    ProblemBookmark,
    ProblemTopic,
    ProblemTopicAssignment,
    ProblemVersion,
    TestCase,
)
from app.models.submission import (
    ConceptEvidenceRecord,
    EvaluationRun,
    ScoreBreakdown,
    Submission,
)
from app.models.user import User
from app.schemas.problem import (
    BookmarkToggleResponse,
    CodeWalkthroughStep,
    ConceptCheckItem,
    ContentImportReportResponse,
    ContentImportRequest,
    CsvContentImportRequest,
    LanguageOption,
    LanguagesResponse,
    PaginatedProblemResponse,
    ProblemDetailResponse,
    ProblemSubmissionHistoryItem,
    ProblemSummaryResponse,
    ProgressiveHintItem,
    ProgressiveHintsResponse,
    RunCodeRequest,
    RunCodeResponse,
    SampleCaseRunResult,
    TestCaseSampleResponse,
    TopicResponse,
    VerifiedSolutionResponse,
)

from app.evaluation.feedback.explainer import IntelligentExplainer
from app.evaluation.solutions.service import VerifiedSolutionService

_cur = Path(__file__).resolve().parent
while _cur.parent != _cur:
    candidate = _cur / "apps" / "execution-runner"
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))
        break
    if (_cur / "execution-runner").exists() and str(_cur / "execution-runner") not in sys.path:
        sys.path.insert(0, str(_cur / "execution-runner"))
        break
    _cur = _cur.parent
from runner.executor import CodeExecutor
from runner.protocol import ExecutionJob

router = APIRouter(prefix="/problems", tags=["Problem Library"])


def _extract_concepts_from_rubric(rubric_json_str: Optional[str]) -> List[str]:
    """Parse rubric json and extract required concept identifiers."""
    if not rubric_json_str:
        return []
    try:
        data = json.loads(rubric_json_str)
        required = data.get("required_concepts", [])
        return [c.get("concept") for c in required if c.get("concept")]
    except Exception:
        return []


@router.get("", response_model=Union[PaginatedProblemResponse, List[ProblemSummaryResponse]])
async def list_published_problems(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(get_current_user_optional)] = None,
    difficulty: Optional[str] = Query(None, description="Filter by difficulty (easy, medium, hard)"),
    topic: Optional[str] = Query(None, description="Filter by topic slug or comma-separated slugs"),
    search: Optional[str] = Query(None, description="Search term for title, description, slug, or ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by student status (not_started, attempted, solved)"),
    saved_only: bool = Query(False, description="Filter to bookmarked problems only"),
    sort_by: str = Query("created_at", description="Field to sort by (created_at, title, difficulty)"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    skip: Optional[int] = Query(None, ge=0),
    limit: Optional[int] = Query(None, ge=1, le=100),
    paginate: bool = Query(False, description="Return rich paginated response model with metadata"),
    organization_id: Optional[str] = Query(None, description="Filter by verified organization"),
):
    """
    List published coding problems with rich multi-facet search, difficulty & topic filtering,
    student progress tracking, bookmark indicators, and pagination.
    Backward-compatible: returns List[ProblemSummaryResponse] by default unless paginate=true.
    """
    # 1. Base tenant query for visible problems
    base_query = (
        select(ProblemVersion)
        .join(Problem, Problem.id == ProblemVersion.problem_id)
        .where(Problem.status == "published")
        .options(
            selectinload(ProblemVersion.problem),
            selectinload(ProblemVersion.topic_assignments).selectinload(ProblemTopicAssignment.topic),
            selectinload(ProblemVersion.rubrics),
        )
    )

    # Multi-tenant scoping logic
    if organization_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "UNAUTHENTICATED", "message": "Authentication required to filter by organization."},
            )
        await verify_organization_access(db, current_user.id, organization_id)
        base_query = base_query.where(
            Problem.owner_type == "organization",
            Problem.owner_organization_id == organization_id,
        )
    else:
        if current_user:
            user_org_ids = await get_user_organization_ids(db, current_user.id)
            if user_org_ids:
                base_query = base_query.where(
                    or_(
                        Problem.owner_type == "platform",
                        and_(
                            Problem.owner_type == "organization",
                            Problem.owner_organization_id.in_(user_org_ids),
                        ),
                    )
                )
            else:
                base_query = base_query.where(Problem.owner_type == "platform")
        else:
            base_query = base_query.where(Problem.owner_type == "platform")

    # 2. Difficulty filter
    if difficulty:
        base_query = base_query.where(ProblemVersion.difficulty == difficulty.lower())

    # 3. Topic filter (supports comma-separated slugs or names, e.g. "linked-lists" or "linked_lists")
    if topic:
        raw_slugs = [t.strip().lower() for t in topic.split(",") if t.strip()]
        topic_slugs = []
        for s in raw_slugs:
            topic_slugs.append(s)
            topic_slugs.append(s.replace("_", "-"))
            topic_slugs.append(s.replace("-", "_"))
        if topic_slugs:
            topic_subq = (
                select(ProblemTopicAssignment.problem_version_id)
                .join(ProblemTopic, ProblemTopic.id == ProblemTopicAssignment.topic_id)
                .where(
                    or_(
                        ProblemTopic.slug.in_(topic_slugs),
                        func.lower(ProblemTopic.name).in_(raw_slugs),
                    )
                )
            )
            base_query = base_query.where(ProblemVersion.id.in_(topic_subq))

    # 4. Search filter across title, slug, statement_markdown, problem ID, topic, and required concepts in rubrics
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        topic_search_subq = (
            select(ProblemTopicAssignment.problem_version_id)
            .join(ProblemTopic, ProblemTopic.id == ProblemTopicAssignment.topic_id)
            .where(
                or_(
                    func.lower(ProblemTopic.name).like(term),
                    func.lower(ProblemTopic.slug).like(term),
                )
            )
        )
        rubric_search_subq = (
            select(GradingRubric.problem_version_id)
            .where(func.lower(GradingRubric.rubric_json).like(term))
        )
        base_query = base_query.where(
            or_(
                func.lower(ProblemVersion.title).like(term),
                func.lower(Problem.slug).like(term),
                func.lower(ProblemVersion.statement_markdown).like(term),
                Problem.id == search.strip(),
                ProblemVersion.id.in_(topic_search_subq),
                ProblemVersion.id.in_(rubric_search_subq),
            )
        )

    # 5. Saved-only bookmark filter
    if saved_only:
        if not current_user:
            return PaginatedProblemResponse(total=0, page=1, page_size=page_size, total_pages=0, items=[]) if paginate else []
        bm_subq = select(ProblemBookmark.problem_id).where(ProblemBookmark.user_id == current_user.id)
        base_query = base_query.where(Problem.id.in_(bm_subq))

    # 6. Fetch user context (bookmarks & submission statuses) for personalization
    bookmarked_ids = set()
    user_status_by_problem: Dict[str, str] = {}  # problem_id -> "not_started" | "attempted" | "solved"

    if current_user:
        # Load user bookmarks
        bm_stmt = select(ProblemBookmark.problem_id).where(ProblemBookmark.user_id == current_user.id)
        bookmarked_ids = set((await db.execute(bm_stmt)).scalars().all())

        # Load user submissions to calculate progress per problem
        user_sub_stmt = (
            select(
                ProblemVersion.problem_id,
                Submission.id,
                Submission.status,
                func.coalesce(func.sum(ScoreBreakdown.awarded_points), 0.0).label("total_score"),
            )
            .join(ProblemVersion, ProblemVersion.id == Submission.problem_version_id)
            .outerjoin(EvaluationRun, EvaluationRun.submission_id == Submission.id)
            .outerjoin(ScoreBreakdown, ScoreBreakdown.evaluation_run_id == EvaluationRun.id)
            .where(Submission.user_id == current_user.id)
            .group_by(ProblemVersion.problem_id, Submission.id, Submission.status)
        )
        user_subs = (await db.execute(user_sub_stmt)).all()

        for prob_id, sub_id, sub_status, total_score in user_subs:
            current_st = user_status_by_problem.get(prob_id, "not_started")
            if total_score >= 100.0:
                user_status_by_problem[prob_id] = "solved"
            elif current_st != "solved":
                user_status_by_problem[prob_id] = "attempted"


    # 7. Sorting
    if sort_by == "title":
        order_col = ProblemVersion.title.asc() if sort_order == "asc" else ProblemVersion.title.desc()
    elif sort_by == "difficulty":
        order_col = ProblemVersion.difficulty.asc() if sort_order == "asc" else ProblemVersion.difficulty.desc()
    else:
        order_col = ProblemVersion.created_at.asc() if sort_order == "asc" else ProblemVersion.created_at.desc()
    base_query = base_query.order_by(order_col)

    # Execute and fetch all candidate matching versions to compute aggregates & filters
    all_matched_versions = (await db.execute(base_query)).scalars().all()

    # Deduplicate versions by problem_id (picking latest version)
    seen_problems = set()
    unique_versions: List[ProblemVersion] = []
    for pv in all_matched_versions:
        if pv.problem.id not in seen_problems:
            seen_problems.add(pv.problem.id)
            unique_versions.append(pv)

    # 8. Post-filter by student progress status if requested
    if status_filter and status_filter.lower() in ("not_started", "attempted", "solved"):
        target_status = status_filter.lower()
        unique_versions = [
            pv for pv in unique_versions
            if user_status_by_problem.get(pv.problem.id, "not_started") == target_status
        ]

    # Calculate difficulty and status counts for facet pills
    difficulty_counts = {"easy": 0, "medium": 0, "hard": 0, "total": len(unique_versions)}
    status_counts = {"not_started": 0, "attempted": 0, "solved": 0}

    for pv in unique_versions:
        diff_key = pv.difficulty.lower()
        if diff_key in difficulty_counts:
            difficulty_counts[diff_key] += 1
        st_key = user_status_by_problem.get(pv.problem.id, "not_started")
        if st_key in status_counts:
            status_counts[st_key] += 1

    total_records = len(unique_versions)

    # 9. Handle pagination offsets
    if skip is not None and limit is not None:
        effective_offset = skip
        effective_limit = limit
        current_page = (skip // limit) + 1
        current_page_size = limit
    else:
        current_page = page
        current_page_size = page_size
        effective_offset = (page - 1) * page_size
        effective_limit = page_size

    total_pages = math.ceil(total_records / current_page_size) if total_records > 0 else 1
    paginated_versions = unique_versions[effective_offset : effective_offset + effective_limit]

    # Build response items with real database submission metrics
    prob_version_ids = [pv.id for pv in paginated_versions]
    stats_by_vid = {}
    if prob_version_ids:
        stats_stmt = (
            select(
                Submission.problem_version_id,
                func.count(Submission.id).label("total"),
                func.sum(
                    case(
                        (Submission.status == "completed", 1),
                        else_=0
                    )
                ).label("accepted")
            )
            .where(Submission.problem_version_id.in_(prob_version_ids))
            .group_by(Submission.problem_version_id)
        )
        sub_stats = (await db.execute(stats_stmt)).all()
        for vid, total, accepted in sub_stats:
            acc_rate = round((accepted / total) * 100.0, 1) if total > 0 else None
            stats_by_vid[vid] = (total, acc_rate)

    items: List[ProblemSummaryResponse] = []
    for pv in paginated_versions:
        topic_names = [
            assignment.topic.name
            for assignment in pv.topic_assignments
            if assignment.topic
        ]
        # Extract concepts from active rubric
        active_rubric = pv.rubrics[0] if pv.rubrics else None
        expected_concepts = _extract_concepts_from_rubric(active_rubric.rubric_json if active_rubric else None)
        if not expected_concepts and topic_names:
            expected_concepts = [t.lower() for t in topic_names[:2]]

        preview = pv.statement_markdown.split("\n\n")[0] if pv.statement_markdown else ""
        if len(preview) > 160:
            preview = preview[:157] + "..."

        is_saved = pv.problem.id in bookmarked_ids
        student_st = user_status_by_problem.get(pv.problem.id, "not_started")
        total_subs, acc_rate = stats_by_vid.get(pv.id, (0, None))

        items.append(
            ProblemSummaryResponse(
                id=pv.problem.id,
                slug=pv.problem.slug,
                title=pv.title,
                difficulty=pv.difficulty,
                language=pv.language,
                version_number=pv.version_number,
                statement_preview=preview,
                topics=topic_names,
                expected_concepts=expected_concepts,
                student_status=student_st,
                is_saved=is_saved,
                acceptance_rate=acc_rate,
                total_submissions=total_subs,
            )
        )

    # Set standard pagination response headers
    response.headers["X-Total-Count"] = str(total_records)
    response.headers["X-Page"] = str(current_page)
    response.headers["X-Page-Size"] = str(current_page_size)
    response.headers["X-Total-Pages"] = str(total_pages)

    if paginate:
        # Fetch available topics for filter bar
        topics_stmt = select(ProblemTopic.name).order_by(ProblemTopic.name)
        topic_names = (await db.execute(topics_stmt)).scalars().all()

        return PaginatedProblemResponse(
            total=total_records,
            page=current_page,
            page_size=current_page_size,
            total_pages=total_pages,
            items=items,
            difficulty_counts=difficulty_counts,
            status_counts=status_counts,
            available_topics=list(topic_names),
        )

    return items


@router.get("/topics", response_model=List[TopicResponse])
async def list_topics(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve available topic taxonomies (e.g. Loops, Recursion, Comprehensions)."""
    stmt = select(ProblemTopic).order_by(ProblemTopic.name)
    topics = (await db.execute(stmt)).scalars().all()
    return [
        TopicResponse(id=t.id, name=t.name, slug=t.slug)
        for t in topics
    ]


@router.get("/languages", response_model=LanguagesResponse)
async def get_supported_languages():
    """Retrieve live compiler availability, runtime versions, and starter templates for supported languages."""
    from runner.languages import LanguageDetector, get_default_starter_template
    all_info = LanguageDetector.get_all_languages()
    return LanguagesResponse(
        languages=[
            LanguageOption(
                id=l["id"],
                name=l["name"],
                monaco_lang=l["monaco_lang"],
                file_extension=l["file_extension"],
                version=l["version"],
                is_available=l["is_available"],
                starter_template=get_default_starter_template(l["id"]),
            )
            for l in all_info
        ]
    )


@router.post("/{problem_id}/bookmark", response_model=BookmarkToggleResponse)
async def toggle_problem_bookmark(
    problem_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Save or remove a problem bookmark for the authenticated user."""
    # Verify problem existence
    stmt_p = select(Problem).where(Problem.id == problem_id, Problem.status == "published")
    problem = (await db.execute(stmt_p)).scalar_one_or_none()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROBLEM_NOT_FOUND", "message": "Problem not found."},
        )

    # Check existing bookmark
    stmt_bm = select(ProblemBookmark).where(
        ProblemBookmark.user_id == current_user.id,
        ProblemBookmark.problem_id == problem_id,
    )
    bookmark = (await db.execute(stmt_bm)).scalar_one_or_none()

    if bookmark:
        await db.delete(bookmark)
        await db.commit()
        return BookmarkToggleResponse(
            problem_id=problem_id,
            is_saved=False,
            message="Problem removed from your saved bookmarks.",
        )
    else:
        new_bm = ProblemBookmark(
            user_id=current_user.id,
            problem_id=problem_id,
        )
        db.add(new_bm)
        await db.commit()
        return BookmarkToggleResponse(
            problem_id=problem_id,
            is_saved=True,
            message="Problem saved to your bookmarks.",
        )


@router.get("/bookmarks/me", response_model=List[ProblemSummaryResponse])
async def get_my_bookmarks(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Retrieve all problems bookmarked by the currently authenticated user."""
    stmt = (
        select(ProblemVersion)
        .join(Problem, Problem.id == ProblemVersion.problem_id)
        .join(ProblemBookmark, ProblemBookmark.problem_id == Problem.id)
        .where(ProblemBookmark.user_id == current_user.id, Problem.status == "published")
        .options(
            selectinload(ProblemVersion.problem),
            selectinload(ProblemVersion.topic_assignments).selectinload(ProblemTopicAssignment.topic),
            selectinload(ProblemVersion.rubrics),
        )
        .order_by(ProblemBookmark.created_at.desc())
    )
    versions = (await db.execute(stmt)).scalars().all()

    results = []
    seen = set()
    for pv in versions:
        if pv.problem.id in seen:
            continue
        seen.add(pv.problem.id)
        topic_names = [a.topic.name for a in pv.topic_assignments if a.topic]
        active_rubric = pv.rubrics[0] if pv.rubrics else None
        expected_concepts = _extract_concepts_from_rubric(active_rubric.rubric_json if active_rubric else None)

        results.append(
            ProblemSummaryResponse(
                id=pv.problem.id,
                slug=pv.problem.slug,
                title=pv.title,
                difficulty=pv.difficulty,
                language=pv.language,
                version_number=pv.version_number,
                topics=topic_names,
                expected_concepts=expected_concepts,
                student_status="attempted",
                is_saved=True,
            )
        )
    return results


@router.get("/recent/me", response_model=List[ProblemSummaryResponse])
async def get_my_recent_problems(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Retrieve recently attempted problems by the authenticated user."""
    stmt = (
        select(ProblemVersion)
        .join(Submission, Submission.problem_version_id == ProblemVersion.id)
        .join(Problem, Problem.id == ProblemVersion.problem_id)
        .where(Submission.user_id == current_user.id, Problem.status == "published")
        .options(
            selectinload(ProblemVersion.problem),
            selectinload(ProblemVersion.topic_assignments).selectinload(ProblemTopicAssignment.topic),
            selectinload(ProblemVersion.rubrics),
        )
        .order_by(Submission.created_at.desc())
        .limit(20)
    )
    versions = (await db.execute(stmt)).scalars().all()

    # Deduplicate in order of appearance
    seen = set()
    unique = []
    for pv in versions:
        if pv.problem.id not in seen:
            seen.add(pv.problem.id)
            topic_names = [a.topic.name for a in pv.topic_assignments if a.topic]
            active_rubric = pv.rubrics[0] if pv.rubrics else None
            expected_concepts = _extract_concepts_from_rubric(active_rubric.rubric_json if active_rubric else None)
            unique.append(
                ProblemSummaryResponse(
                    id=pv.problem.id,
                    slug=pv.problem.slug,
                    title=pv.title,
                    difficulty=pv.difficulty,
                    language=pv.language,
                    version_number=pv.version_number,
                    topics=topic_names,
                    expected_concepts=expected_concepts,
                    student_status="attempted",
                    is_saved=False,
                )
            )
    return unique[:10]


@router.get("/{problem_id}/submissions", response_model=List[ProblemSubmissionHistoryItem])
async def get_problem_submissions(
    problem_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Retrieve user's submission history and concept-aware score breakdowns for this problem."""
    stmt = (
        select(Submission)
        .join(ProblemVersion, ProblemVersion.id == Submission.problem_version_id)
        .where(
            ProblemVersion.problem_id == problem_id,
            Submission.user_id == current_user.id,
        )
        .options(
            selectinload(Submission.evaluation_runs).selectinload(EvaluationRun.score_breakdowns),
            selectinload(Submission.evaluation_runs).selectinload(EvaluationRun.concept_evidence),
        )
        .order_by(Submission.created_at.desc())
        .limit(50)
    )
    submissions = (await db.execute(stmt)).scalars().all()

    history: List[ProblemSubmissionHistoryItem] = []
    for sub in submissions:
        eval_run = sub.evaluation_runs[0] if sub.evaluation_runs else None
        total_score = 0.0
        passed = False
        func_score = None
        concept_score = None
        violations = []

        if eval_run:
            total_score = sum(sb.awarded_points for sb in eval_run.score_breakdowns)
            passed = total_score >= 100.0 or eval_run.status == "completed"
            for sb in eval_run.score_breakdowns:
                if sb.criterion in ("functional_correctness", "functional"):
                    func_score = sb.awarded_points
                elif sb.criterion in ("concept_compliance", "concept"):
                    concept_score = sb.awarded_points
            for ev in eval_run.concept_evidence:
                if ev.status == "failed":
                    violations.append(f"Missing required concept: {ev.concept_name}")

        history.append(
            ProblemSubmissionHistoryItem(
                id=sub.id,
                submission_id=sub.id,
                created_at=sub.created_at.isoformat() if sub.created_at else "",
                status=sub.status,
                score=total_score,
                passed=passed,
                functional_score=func_score,
                concept_score=concept_score,
                concept_violations=violations,
                code_snippet=sub.source_code[:120] + "..." if len(sub.source_code) > 120 else sub.source_code,
            )
        )
    return history


@router.post("/import", response_model=ContentImportReportResponse)
async def import_problem_dataset_endpoint(
    payload: ContentImportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Import an authorized, original, or licensed problem dataset (JSON schema).
    Enforces provenance tracking, duplicate detection, and AST rubric generation.
    """
    try:
        report = await import_problem_dataset(db, payload, current_user.id, import_format="json")
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "IMPORT_VALIDATION_ERROR", "message": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "IMPORT_ERROR", "message": f"Failed to import dataset: {str(e)}"},
        )


@router.post("/import-csv", response_model=ContentImportReportResponse)
async def import_csv_dataset_endpoint(
    payload: CsvContentImportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Import an authorized problem dataset from CSV text.
    Validates CSV schema, provenance, license declaration, duplicate detection, and AST rubrics.
    """
    try:
        import_request = parse_csv_dataset(
            csv_content=payload.csv_content,
            source_name=payload.source_name,
            license_type=payload.license_type,
            provenance_url=payload.provenance_url,
        )
        report = await import_problem_dataset(db, import_request, current_user.id, import_format="csv")
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "IMPORT_VALIDATION_ERROR", "message": str(e)},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "IMPORT_ERROR", "message": f"Failed to import CSV dataset: {str(e)}"},
        )


@router.get("/{problem_id}", response_model=ProblemDetailResponse)
async def get_problem_details(
    problem_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(get_current_user_optional)] = None,
):
    """
    Retrieve problem statement, constraints, expected concepts, and public sample test cases.
    Verifies caller authorization and strictly prevents student leakage of hidden test cases.
    """
    stmt = (
        select(ProblemVersion)
        .join(Problem, Problem.id == ProblemVersion.problem_id)
        .where(
            or_(Problem.id == problem_id, Problem.slug == problem_id),
            Problem.status == "published",
        )
        .options(
            selectinload(ProblemVersion.problem),
            selectinload(ProblemVersion.test_cases),
            selectinload(ProblemVersion.topic_assignments).selectinload(ProblemTopicAssignment.topic),
            selectinload(ProblemVersion.rubrics),
        )
        .order_by(ProblemVersion.version_number.desc())
    )
    pv = (await db.execute(stmt)).scalars().first()

    if not pv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROBLEM_NOT_FOUND", "message": "Published problem not found."},
        )

    # Server-side tenant authorization check
    await authorize_problem_access(db, current_user, pv.problem)

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

    # Topics and expected concepts
    topic_names = [a.topic.name for a in pv.topic_assignments if a.topic]
    active_rubric = pv.rubrics[0] if pv.rubrics else None
    expected_concepts = _extract_concepts_from_rubric(active_rubric.rubric_json if active_rubric else None)
    if not expected_concepts and topic_names:
        expected_concepts = [t.lower() for t in topic_names[:2]]

    # User personalization
    is_saved = False
    student_status = "not_started"
    if current_user:
        bm_stmt = select(ProblemBookmark).where(
            ProblemBookmark.user_id == current_user.id,
            ProblemBookmark.problem_id == pv.problem.id,
        )
        if (await db.execute(bm_stmt)).scalar_one_or_none():
            is_saved = True

        sub_stmt = (
            select(
                Submission.id,
                Submission.status,
                func.coalesce(func.sum(ScoreBreakdown.awarded_points), 0.0).label("total_score"),
            )
            .outerjoin(EvaluationRun, EvaluationRun.submission_id == Submission.id)
            .outerjoin(ScoreBreakdown, ScoreBreakdown.evaluation_run_id == EvaluationRun.id)
            .where(
                Submission.user_id == current_user.id,
                Submission.problem_version_id == pv.id,
            )
            .group_by(Submission.id, Submission.status)
        )
        subs = (await db.execute(sub_stmt)).all()
        if any(total_score >= 100.0 for sub_id, sub_status, total_score in subs):
            student_status = "solved"
        elif len(subs) > 0:
            student_status = "attempted"


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
        expected_concepts=expected_concepts,
        topics=topic_names,
        sample_test_cases=sample_cases,
        student_status=student_status,
        is_saved=is_saved,
        starter_code=pv.starter_code,
    )


@router.get("/{problem_id}/samples", response_model=List[TestCaseSampleResponse])
async def get_sample_test_cases(
    problem_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(get_current_user_optional)] = None,
):
    """Retrieve public sample cases for running editor tests with tenant scoping."""
    stmt_problem = select(Problem).where(
        or_(Problem.id == problem_id, Problem.slug == problem_id),
        Problem.status == "published",
    )
    problem = (await db.execute(stmt_problem)).scalar_one_or_none()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROBLEM_NOT_FOUND", "message": "Published problem not found."},
        )

    await authorize_problem_access(db, current_user, problem)

    stmt = (
        select(TestCase)
        .join(ProblemVersion, ProblemVersion.id == TestCase.problem_version_id)
        .join(Problem, Problem.id == ProblemVersion.problem_id)
        .where(
            Problem.id == problem.id,
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


def normalize_output(raw: Optional[str]) -> List[str]:
    """
    Standard execution output normalization policy:
    1. Handles Windows (\\r\\n) and Unix (\\n) line endings identically via splitlines().
    2. Strips trailing whitespace from each line while preserving leading indentation.
    3. Strips trailing empty lines at the end of output.
    4. Preserves meaningful internal blank lines and casing.
    """
    if not raw:
        return []
    lines = [line.rstrip() for line in raw.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return lines


@router.post("/{problem_id}/run", response_model=RunCodeResponse)
async def run_code_against_samples(
    problem_id: str,
    payload: RunCodeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(get_current_user_optional)] = None,
):
    """
    Run student code in the sandboxed execution environment against public sample test cases or custom input.
    Provides instant sample test results, execution runtime, stdout/stderr,
    failure diagnostics, progressive hints, and static AST concept compliance checks.
    """
    stmt = (
        select(ProblemVersion)
        .join(Problem, Problem.id == ProblemVersion.problem_id)
        .where(
            or_(Problem.id == problem_id, Problem.slug == problem_id),
            Problem.status == "published",
        )
        .options(
            selectinload(ProblemVersion.problem),
            selectinload(ProblemVersion.test_cases),
            selectinload(ProblemVersion.rubrics),
        )
        .order_by(ProblemVersion.version_number.desc())
    )
    pv = (await db.execute(stmt)).scalars().first()

    if not pv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROBLEM_NOT_FOUND", "message": "Published problem not found."},
        )

    await authorize_problem_access(db, current_user, pv.problem)

    # 1. Static AST concept check
    active_rubric = pv.rubrics[0] if pv.rubrics else None
    required_concepts = []
    prohibited_constructs = []
    if active_rubric and active_rubric.rubric_json:
        try:
            r_data = json.loads(active_rubric.rubric_json)
            required_concepts = [c.get("concept") for c in r_data.get("required_concepts", []) if c.get("concept")]
            prohibited_constructs = r_data.get("prohibited_constructs", [])
        except Exception:
            pass

    norm_lang = (payload.language or "python").lower().strip()
    if norm_lang in ("c++", "cpp"):
        norm_lang = "cpp"

    syntax_valid, concept_evidences, syntax_err = ASTAnalyzer.evaluate_concepts(
        source_code=payload.source_code,
        required_concepts=required_concepts,
        prohibited_constructs=prohibited_constructs,
        language=norm_lang,
    )

    concept_checks = [
        ConceptCheckItem(
            concept=ev.concept.value if hasattr(ev.concept, "value") else str(ev.concept),
            passed=bool(ev.passed),
            message=ev.message or f"Concept '{ev.concept}' {'detected in solution' if ev.passed else 'missing from solution'}",
        )
        for ev in concept_evidences
    ]

    if not syntax_valid:
        intelligent_fb = IntelligentExplainer.explain_run_failure(
            language=norm_lang,
            source_code=payload.source_code,
            status="syntax_error",
            syntax_error=syntax_err,
            case_results=[],
            concept_checks=[c.model_dump() for c in concept_checks],
            problem_title=pv.title,
            problem_statement=pv.statement_markdown or "",
        )
        status_name = "compilation_error" if norm_lang in ("java", "cpp") else "syntax_error"
        learning_hints = IntelligentExplainer.generate_progressive_hints_payload(
            problem_title=pv.title,
            problem_statement=pv.statement_markdown or "",
            expected_concepts=[c.concept for c in concept_checks],
            status=status_name,
            failure_category="compilation_error",
        )
        return RunCodeResponse(
            status=status_name,
            syntax_valid=False,
            compilation_error=(norm_lang in ("java", "cpp")),
            compile_output=syntax_err if norm_lang in ("java", "cpp") else None,
            syntax_error_message=syntax_err or f"Syntax error in {norm_lang.capitalize()} source code.",
            all_passed=False,
            total_cases=0,
            passed_cases=0,
            case_results=[],
            concept_checks=concept_checks,
            execution_time_ms=0.0,
            intelligent_feedback=intelligent_fb,
            learning_hints=learning_hints,
        )


    # 2. Test Execution
    case_results: List[SampleCaseRunResult] = []
    total_exec_time = 0.0

    if payload.custom_input is not None and payload.custom_input.strip() != "":
        # Execute against custom input
        job = ExecutionJob(
            job_id=f"run_custom_{uuid.uuid4().hex[:8]}",
            source_code=payload.source_code,
            language=norm_lang,
            stdin_input=payload.custom_input,
            timeout_seconds=3.0,
        )
        res = CodeExecutor.run_code(job)
        total_exec_time += res.duration_ms

        if res.compilation_error or res.error_type == "COMPILATION_ERROR":
            compile_err = res.stderr or "Compilation Error"
            diag_explanation = IntelligentExplainer._diagnose_compiler_error(norm_lang, compile_err)
            case_res = SampleCaseRunResult(
                case_number=1,
                case_id=None,
                input_data=payload.custom_input,
                expected_output=None,
                actual_output="",
                passed=False,
                execution_time_ms=res.duration_ms,
                stderr=compile_err.strip(),
                status="compilation_error",
                failure_explanation=diag_explanation,
            )
            intelligent_fb = IntelligentExplainer.explain_run_failure(
                language=norm_lang,
                source_code=payload.source_code,
                status="compilation_error",
                compile_output=compile_err,
                case_results=[case_res.model_dump()],
                concept_checks=[c.model_dump() for c in concept_checks],
                problem_title=pv.title,
                problem_statement=pv.statement_markdown or "",
            )
            return RunCodeResponse(
                status="compilation_error",
                syntax_valid=True,
                compilation_error=True,
                compile_output=compile_err,
                all_passed=False,
                total_cases=1,
                passed_cases=0,
                case_results=[case_res],
                concept_checks=concept_checks,
                execution_time_ms=res.duration_ms,
                intelligent_feedback=intelligent_fb,
                learning_hints=IntelligentExplainer.generate_progressive_hints_payload(
                    problem_title=pv.title,
                    problem_statement=pv.statement_markdown or "",
                    expected_concepts=[c.concept for c in concept_checks],
                    status="compilation_error",
                    failure_category="compilation_error",
                ),
            )

        passed = (res.exit_code == 0 and not res.timed_out)
        if res.timed_out:
            status_val = "timeout"
            fail_expl = "Time Limit Exceeded: Execution exceeded 3.0s limit (possible infinite loop or deep recursion)."
        elif res.exit_code != 0:
            status_val = "runtime_error"
            fail_expl = IntelligentExplainer._diagnose_runtime_error(norm_lang, res.stderr or "Process exited with non-zero exit code.")
        else:
            status_val = "passed"
            fail_expl = None

        case_results.append(
            SampleCaseRunResult(
                case_number=1,
                case_id=None,
                input_data=payload.custom_input,
                expected_output=None,
                actual_output=res.stdout.strip(),
                passed=passed,
                execution_time_ms=res.duration_ms,
                stderr=res.stderr.strip() if res.stderr else None,
                status=status_val,
                failure_explanation=fail_expl,
            )
        )
    else:
        # Execute against public sample cases
        sample_cases = [
            tc for tc in pv.test_cases
            if tc.is_active and tc.visibility in ("sample", "public")
        ]

        if not sample_cases:
            # Fallback to first active test case if no explicit sample flag
            sample_cases = [tc for tc in pv.test_cases if tc.is_active][:2]

        for idx, tc in enumerate(sample_cases, start=1):
            job = ExecutionJob(
                job_id=f"run_sample_{uuid.uuid4().hex[:8]}_{idx}",
                source_code=payload.source_code,
                language=norm_lang,
                stdin_input=tc.input_data or "",
                timeout_seconds=float(tc.timeout_ms or 3000) / 1000.0,
            )
            res = CodeExecutor.run_code(job)
            total_exec_time += res.duration_ms

            if res.compilation_error or res.error_type == "COMPILATION_ERROR":
                compile_err = res.stderr or "Compilation Error"
                diag_explanation = IntelligentExplainer._diagnose_compiler_error(norm_lang, compile_err)
                case_results.append(
                    SampleCaseRunResult(
                        case_number=idx,
                        case_id=tc.id,
                        input_data=tc.input_data or "",
                        expected_output=(tc.expected_output or "").strip(),
                        actual_output="",
                        passed=False,
                        execution_time_ms=res.duration_ms,
                        stderr=compile_err.strip(),
                        status="compilation_error",
                        failure_explanation=diag_explanation,
                    )
                )
                intelligent_fb = IntelligentExplainer.explain_run_failure(
                    language=norm_lang,
                    source_code=payload.source_code,
                    status="compilation_error",
                    compile_output=compile_err,
                    case_results=[c.model_dump() for c in case_results],
                    concept_checks=[c.model_dump() for c in concept_checks],
                    problem_title=pv.title,
                    problem_statement=pv.statement_markdown or "",
                )
                return RunCodeResponse(
                    status="compilation_error",
                    syntax_valid=True,
                    compilation_error=True,
                    compile_output=compile_err,
                    all_passed=False,
                    total_cases=len(sample_cases),
                    passed_cases=0,
                    case_results=case_results,
                    concept_checks=concept_checks,
                    execution_time_ms=round(total_exec_time, 2),
                    intelligent_feedback=intelligent_fb,
                    learning_hints=IntelligentExplainer.generate_progressive_hints_payload(
                        problem_title=pv.title,
                        problem_statement=pv.statement_markdown or "",
                        expected_concepts=[c.concept for c in concept_checks],
                        status="compilation_error",
                        failure_category="compilation_error",
                    ),
                )

            actual = res.stdout.strip()
            expected = (tc.expected_output or "").strip()

            if res.timed_out:
                status_val = "timeout"
                passed = False
                fail_expl = "Time Limit Exceeded: Process timed out (exceeded 3.0s limit)."
            elif res.exit_code != 0:
                status_val = "runtime_error"
                passed = False
                fail_expl = IntelligentExplainer._diagnose_runtime_error(norm_lang, res.stderr or "Process exited with non-zero exit code.")
            else:
                passed = (normalize_output(actual) == normalize_output(expected))
                status_val = "passed" if passed else "wrong_answer"
                fail_expl = None if passed else IntelligentExplainer._analyze_output_difference(expected, actual)

            case_results.append(
                SampleCaseRunResult(
                    case_number=idx,
                    case_id=tc.id,
                    input_data=tc.input_data or "",
                    expected_output=expected,
                    actual_output=actual,
                    passed=passed,
                    execution_time_ms=res.duration_ms,
                    stderr=res.stderr.strip() if res.stderr else None,
                    status=status_val,
                    failure_explanation=fail_expl,
                )
            )

    all_passed = len(case_results) > 0 and all(c.passed for c in case_results)
    passed_cases = sum(1 for c in case_results if c.passed)

    if any(c.status == "compilation_error" for c in case_results):
        overall_status = "compilation_error"
    elif any(c.status == "timeout" for c in case_results):
        overall_status = "timeout"
    elif any(c.status == "runtime_error" for c in case_results):
        overall_status = "runtime_error"
    elif all_passed:
        violated_concepts = [c for c in concept_checks if not c.passed]
        if violated_concepts:
            overall_status = "concept_not_satisfied"
        else:
            overall_status = "accepted"
    else:
        overall_status = "wrong_answer"

    intelligent_fb = IntelligentExplainer.explain_run_failure(
        language=norm_lang,
        source_code=payload.source_code,
        status=overall_status,
        compile_output=None,
        case_results=[c.model_dump() for c in case_results],
        concept_checks=[c.model_dump() for c in concept_checks],
        problem_title=pv.title,
        problem_statement=pv.statement_markdown or "",
    )

    learning_hints = None
    if overall_status != "accepted":
        learning_hints = IntelligentExplainer.generate_progressive_hints_payload(
            problem_title=pv.title,
            problem_statement=pv.statement_markdown or "",
            expected_concepts=[c.concept for c in concept_checks],
            status=overall_status,
            failure_category=intelligent_fb.get("category"),
        )

    return RunCodeResponse(
        status=overall_status,
        syntax_valid=True,
        syntax_error_message=None,
        all_passed=all_passed,
        total_cases=len(case_results),
        passed_cases=passed_cases,
        case_results=case_results,
        concept_checks=concept_checks,
        execution_time_ms=round(total_exec_time, 2),
        intelligent_feedback=intelligent_fb,
        learning_hints=learning_hints,
    )


@router.get("/{problem_id}/hints", response_model=ProgressiveHintsResponse)
async def get_problem_hints(
    problem_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(get_current_user_optional)] = None,
    failure_category: Optional[str] = Query(None, description="Active failure category (e.g. concept_violation, wrong_answer, compilation_error, timeout, runtime_error)"),
):
    """
    Retrieve progressive educational hints for solving the problem without revealing the full solution.
    Tier 1: General Direction
    Tier 2: Algorithmic & Concept Guidance
    Tier 3: Specific Edge Cases and Tactical Hints
    """
    stmt = (
        select(ProblemVersion)
        .join(Problem, Problem.id == ProblemVersion.problem_id)
        .where(
            or_(Problem.id == problem_id, Problem.slug == problem_id),
            Problem.status == "published",
        )
        .options(
            selectinload(ProblemVersion.problem),
            selectinload(ProblemVersion.rubrics),
        )
        .order_by(ProblemVersion.version_number.desc())
    )
    pv = (await db.execute(stmt)).scalars().first()
    if not pv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROBLEM_NOT_FOUND", "message": "Published problem not found."},
        )

    await authorize_problem_access(db, current_user, pv.problem)

    active_rubric = pv.rubrics[0] if pv.rubrics else None
    expected_concepts = _extract_concepts_from_rubric(active_rubric.rubric_json if active_rubric else None)

    hint_items = IntelligentExplainer.generate_progressive_hints(
        problem_title=pv.title,
        problem_statement=pv.statement_markdown or "",
        expected_concepts=expected_concepts,
        failure_category=failure_category,
    )

    return ProgressiveHintsResponse(
        problem_id=pv.problem.id,
        problem_title=pv.title,
        hints=[
            ProgressiveHintItem(
                tier=h["tier"],
                title=h["title"],
                content=h["content"],
            )
            for h in hint_items
        ],
        tier_1_general=hint_items[0]["content"],
        tier_2_concept=hint_items[1]["content"],
        tier_3_targeted=hint_items[2]["content"],
    )


@router.get("/{problem_id}/verified-solution", response_model=VerifiedSolutionResponse)
async def get_verified_solution_endpoint(
    problem_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Optional[User], Depends(get_current_user_optional)] = None,
    language: str = Query("python", description="Selected programming language (python, java, cpp)"),
):
    """
    Load and dynamically validate the teacher-authorized reference solution in the sandbox.
    Verifies functional correctness and AST concept compliance.
    Returns step-by-step pedagogical explanation, code walkthrough, complexity analysis, and verified status.
    Never fabricates results or claims unverified code is correct.
    """
    norm_lang = (language or "python").lower().strip()
    if norm_lang in ("c++", "cpp"):
        norm_lang = "cpp"
    elif norm_lang not in ("python", "java"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "UNSUPPORTED_LANGUAGE", "message": f"Unsupported language '{language}'"},
        )

    # Check published problem exists and caller is authorized
    stmt = (
        select(Problem)
        .where(
            or_(Problem.id == problem_id, Problem.slug == problem_id),
            Problem.status == "published",
        )
    )
    problem = (await db.execute(stmt)).scalar_one_or_none()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROBLEM_NOT_FOUND", "message": "Published problem not found."},
        )

    await authorize_problem_access(db, current_user, problem)

    result = await VerifiedSolutionService.get_verified_solution(
        problem_id_or_slug=problem_id,
        language=norm_lang,
        db=db,
    )

    walkthrough_steps = [
        CodeWalkthroughStep(
            section=w.get("section", ""),
            code_snippet=w.get("code_snippet", ""),
            explanation=w.get("explanation", ""),
        )
        for w in result.get("code_walkthrough", [])
    ]

    v_status = result.get("verification_status", "not_available")
    v_details = result.get("verification_details") or {}
    v_results = {
        "total_cases": v_details.get("total_cases", v_details.get("total_cases_tested", 0)),
        "passed_cases": v_details.get("passed_cases", 0),
        "execution_time_ms": v_details.get("execution_time_ms", 0.0),
        "concept_verified": result.get("concept_compliance_verified", False),
    }
    explanation_obj = {
        "approach": result.get("approach_description") or result.get("approach_name") or "Optimal algorithm",
        "why_it_works": result.get("why_it_works", ""),
        "time_complexity": result.get("time_complexity", "O(N)"),
        "space_complexity": result.get("space_complexity", "O(1)"),
        "step_by_step": [w.get("explanation", "") for w in result.get("code_walkthrough", []) if w.get("explanation")],
        "example_walkthrough": result.get("example_trace", {}).get("description", "") if isinstance(result.get("example_trace"), dict) else "",
        "required_concepts_satisfied": result.get("required_concepts", []),
        "alternative_approaches": "; ".join(result.get("alternative_approaches", [])) if isinstance(result.get("alternative_approaches"), list) else str(result.get("alternative_approaches", "")),
    }

    return VerifiedSolutionResponse(
        problem_id=result.get("problem_id", problem.id),
        problem_title=result.get("problem_title", "Problem"),
        language=result.get("language", norm_lang),
        is_verified=result.get("is_verified", False),
        status=v_status,
        verification_status=v_status,
        verification_details=v_details,
        verification_results=v_results,
        source_code=result.get("source_code"),
        approach_name=result.get("approach_name"),
        approach_description=result.get("approach_description"),
        why_it_works=result.get("why_it_works"),
        code_walkthrough=walkthrough_steps,
        example_trace=result.get("example_trace"),
        time_complexity=result.get("time_complexity"),
        space_complexity=result.get("space_complexity"),
        required_concepts=result.get("required_concepts", []),
        concept_compliance_verified=result.get("concept_compliance_verified", False),
        alternative_approaches=result.get("alternative_approaches", []),
        explanation=explanation_obj,
    )


