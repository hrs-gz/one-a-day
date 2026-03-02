from __future__ import annotations

import json
from datetime import date

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import LeadExistsError, SourceNotFoundError
from app.models.interest_config import InterestConfig
from app.schemas.lead import LeadListSchema, LeadSchema
from app.services import lead_service, scrape_service
from app.services.lead_service import get_active_interests

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/leads", tags=["leads"])


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class VoteBody(BaseModel):
    vote: int  # -1, 0, or 1


class FavoriteBody(BaseModel):
    favorited: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/today", response_model=LeadSchema)
def get_today_lead(db: Session = Depends(get_db)) -> LeadSchema:
    """Return today's lead (rank=1), or 404 if none exists."""
    lead = lead_service.get_today_lead(db)
    if not lead:
        raise HTTPException(status_code=404, detail="No lead found for today")
    return lead  # type: ignore[return-value]


@router.get("/by-date/{target_date}", response_model=list[LeadSchema])
def get_leads_by_date(
    target_date: date,
    db: Session = Depends(get_db),
) -> list[LeadSchema]:
    """Return all leads for a given date (YYYY-MM-DD), ordered by rank.

    Returns an empty list if no leads exist for that date.
    """
    leads = lead_service.get_leads_by_date(db, target_date)
    return leads  # type: ignore[return-value]


@router.get("", response_model=LeadListSchema)
def list_leads(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    source_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> LeadListSchema:
    """Return a paginated list of leads, newest first."""
    leads, total = lead_service.list_leads(
        db, skip=skip, limit=limit, source_type=source_type
    )
    return LeadListSchema(items=leads, total=total)  # type: ignore[arg-type]


@router.get("/{lead_id}", response_model=LeadSchema)
def get_lead(lead_id: int, db: Session = Depends(get_db)) -> LeadSchema:
    """Return a single lead by ID."""
    try:
        return lead_service.get_lead_by_id(db, lead_id)  # type: ignore[return-value]
    except SourceNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"Lead {lead_id} not found"
        ) from exc


@router.post("/generate", response_model=list[LeadSchema], status_code=201)
def generate_lead(db: Session = Depends(get_db)) -> list[LeadSchema]:
    """Manually trigger the scrape-and-select pipeline for today.

    Returns up to 3 leads. Returns 409 if leads already exist for today.
    """
    try:
        candidates = scrape_service.run_all_scrapers(db)
        interests = get_active_interests(db)
        top = lead_service.select_top_candidates(candidates, interests, n=3)
        if not top:
            raise HTTPException(
                status_code=422,
                detail="No candidates found — check scraper sources and configs",
            )
        leads = lead_service.create_leads_from_candidates(db, top, interests)
        return leads  # type: ignore[return-value]
    except LeadExistsError as exc:
        raise HTTPException(
            status_code=409, detail="Lead already exists for today"
        ) from exc


@router.patch("/{lead_id}/vote", response_model=LeadSchema)
def vote_on_lead(
    lead_id: int,
    body: VoteBody,
    db: Session = Depends(get_db),
) -> LeadSchema:
    """Update vote on a lead (-1, 0, or +1) and adjust matched interest weights.

    Upvote adds +0.1 to each matched interest weight (clamped to 1.0).
    Downvote subtracts -0.1 (clamped to 0.0). Neutral resets without adjustment.
    """
    if body.vote not in (-1, 0, 1):
        raise HTTPException(status_code=422, detail="vote must be -1, 0, or 1")

    try:
        lead = lead_service.get_lead_by_id(db, lead_id)
    except SourceNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"Lead {lead_id} not found"
        ) from exc

    old_vote = lead.vote
    lead.vote = body.vote

    # Adjust interest weights only when vote changes to non-neutral
    if body.vote != 0:
        delta = 0.1 if body.vote == 1 else -0.1
        try:
            matched_ids: list[int] = json.loads(lead.matched_interests or "[]")
        except (json.JSONDecodeError, TypeError):
            matched_ids = []

        for interest_id in matched_ids:
            interest = (
                db.query(InterestConfig)
                .filter(InterestConfig.id == interest_id)
                .first()
            )
            if interest:
                interest.weight = max(0.0, min(1.0, interest.weight + delta))

    db.commit()
    db.refresh(lead)
    logger.info("lead_voted", lead_id=lead_id, old_vote=old_vote, new_vote=body.vote)
    return lead  # type: ignore[return-value]


@router.patch("/{lead_id}/favorite", response_model=LeadSchema)
def favorite_lead(
    lead_id: int,
    body: FavoriteBody,
    db: Session = Depends(get_db),
) -> LeadSchema:
    """Toggle the favorited state of a lead."""
    try:
        lead = lead_service.get_lead_by_id(db, lead_id)
    except SourceNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"Lead {lead_id} not found"
        ) from exc

    lead.favorited = body.favorited
    db.commit()
    db.refresh(lead)
    logger.info("lead_favorited", lead_id=lead_id, favorited=body.favorited)
    return lead  # type: ignore[return-value]
