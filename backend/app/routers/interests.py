from __future__ import annotations

import json
import re

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.interest_config import InterestConfig
from app.schemas.interest_config import (
    InterestConfigCreate,
    InterestConfigListSchema,
    InterestConfigSchema,
    InterestConfigUpdate,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/interests", tags=["interests"])


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class ParseInterestsBody(BaseModel):
    text: str


class ParseInterestsResponse(BaseModel):
    created: list[InterestConfigSchema]
    skipped: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SPLIT_RE = re.compile(r"[,\n]|\band\b", re.IGNORECASE)


def _extract_keywords_fallback(text: str) -> list[str]:
    """Split text on commas, newlines, and 'and' to extract keywords."""
    parts = _SPLIT_RE.split(text)
    return [p.strip().lower() for p in parts if p.strip()]


def _extract_keywords_openrouter(text: str, api_key: str) -> list[str]:
    """Call OpenRouter to extract keyword list from natural language text."""
    system_prompt = (
        "Extract interest keywords from the user text. "
        "Return ONLY a JSON array of lowercase keyword strings. "
        'Example: ["urban planning", "marine biology"]. No explanations.'
    )
    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openrouter_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
            },
            timeout=15.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        # Extract JSON array from response (may have surrounding text)
        match = re.search(r"\[.*?\]", content, re.DOTALL)
        if match:
            keywords = json.loads(match.group())
            if isinstance(keywords, list):
                return [str(k).strip().lower() for k in keywords if str(k).strip()]
    except Exception as exc:
        logger.warning("openrouter_parse_failed", error=str(exc))
    # Fall back to heuristic on any failure
    return _extract_keywords_fallback(text)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=InterestConfigListSchema)
def list_interests(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> InterestConfigListSchema:
    """Return all interest configs."""
    query = db.query(InterestConfig).order_by(InterestConfig.created_at.desc())
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return InterestConfigListSchema(items=items, total=total)  # type: ignore[arg-type]


@router.post("", response_model=InterestConfigSchema, status_code=201)
def create_interest(
    body: InterestConfigCreate,
    db: Session = Depends(get_db),
) -> InterestConfigSchema:
    """Create a new interest config."""
    interest = InterestConfig(**body.model_dump())
    db.add(interest)
    db.commit()
    db.refresh(interest)
    logger.info("interest_created", keyword=interest.keyword)
    return interest  # type: ignore[return-value]


@router.get("/{interest_id}", response_model=InterestConfigSchema)
def get_interest(
    interest_id: int, db: Session = Depends(get_db)
) -> InterestConfigSchema:
    """Return a single interest config by ID."""
    interest = db.query(InterestConfig).filter(InterestConfig.id == interest_id).first()
    if not interest:
        raise HTTPException(status_code=404, detail=f"Interest {interest_id} not found")
    return interest  # type: ignore[return-value]


@router.patch("/{interest_id}", response_model=InterestConfigSchema)
def update_interest(
    interest_id: int,
    body: InterestConfigUpdate,
    db: Session = Depends(get_db),
) -> InterestConfigSchema:
    """Partially update an interest config."""
    interest = db.query(InterestConfig).filter(InterestConfig.id == interest_id).first()
    if not interest:
        raise HTTPException(status_code=404, detail=f"Interest {interest_id} not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(interest, field, value)
    db.commit()
    db.refresh(interest)
    return interest  # type: ignore[return-value]


@router.delete("/{interest_id}", status_code=204)
def delete_interest(interest_id: int, db: Session = Depends(get_db)) -> None:
    """Delete an interest config."""
    interest = db.query(InterestConfig).filter(InterestConfig.id == interest_id).first()
    if not interest:
        raise HTTPException(status_code=404, detail=f"Interest {interest_id} not found")
    db.delete(interest)
    db.commit()
    logger.info("interest_deleted", interest_id=interest_id)


@router.post("/parse", response_model=ParseInterestsResponse, status_code=201)
def parse_interests(
    body: ParseInterestsBody,
    db: Session = Depends(get_db),
) -> ParseInterestsResponse:
    """Parse natural language text into interest keywords and create new ones.

    Uses OpenRouter (mistral-7b-instruct:free) if OPENROUTER_API_KEY is set,
    otherwise falls back to comma/newline/and splitting heuristic.

    Returns created InterestConfig objects and a list of skipped (duplicate) keywords.
    """
    if not body.text.strip():
        raise HTTPException(status_code=422, detail="text cannot be empty")

    # Extract keywords
    if settings.openrouter_api_key:
        keywords = _extract_keywords_openrouter(body.text, settings.openrouter_api_key)
    else:
        keywords = _extract_keywords_fallback(body.text)

    if not keywords:
        raise HTTPException(
            status_code=422, detail="Could not extract any keywords from text"
        )

    # Fetch existing keywords (case-insensitive dedup)
    existing = db.query(InterestConfig).all()
    existing_keywords = {i.keyword.lower() for i in existing}

    created: list[InterestConfig] = []
    skipped: list[str] = []

    for keyword in keywords:
        if not keyword:
            continue
        if keyword in existing_keywords:
            skipped.append(keyword)
        else:
            interest = InterestConfig(keyword=keyword, weight=1.0, active=True)
            db.add(interest)
            db.flush()
            existing_keywords.add(keyword)
            created.append(interest)
            logger.info("interest_parsed_created", keyword=keyword)

    if created:
        db.commit()
        for interest in created:
            db.refresh(interest)

    return ParseInterestsResponse(created=created, skipped=skipped)  # type: ignore[arg-type]
