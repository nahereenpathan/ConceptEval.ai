"""
Problem Authoring & NLP Intent API Endpoints
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.evaluation.intent.extractor import NLPIntentExtractor

router = APIRouter(prefix="/authoring", tags=["Authoring"])


class IntentExtractionRequest(BaseModel):
    problem_text: str = Field(min_length=5, max_length=10000)


class IntentExtractionResponse(BaseModel):
    rubric_draft: Dict[str, Any]
    extracted_concepts: List[Dict[str, Any]]
    extracted_prohibitions: List[Dict[str, Any]]
    confidence: float
    requires_human_review: bool
    review_notes: List[str]


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
