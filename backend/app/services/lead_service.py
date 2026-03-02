from __future__ import annotations

import json
import re
from datetime import date, datetime

import structlog
from sqlalchemy.orm import Session

from app.exceptions import LeadExistsError, SourceNotFoundError
from app.models.interest_config import InterestConfig
from app.models.lead import Lead
from app.scrapers.base import CandidateLead

logger = structlog.get_logger(__name__)


def score_candidate(
    candidate: CandidateLead,
    interests: list[InterestConfig],
) -> float:
    """Score a candidate against active interest configs.

    Scoring: For each active interest, check if the keyword appears in the
    candidate's raw_text (case-insensitive). Partial word matches are also
    rewarded proportionally. Score is normalized to 0–100, weighted by
    interest.weight.

    Args:
        candidate: The candidate lead to score.
        interests: Active interest configs with keywords and weights.

    Returns:
        Score from 0.0 to 100.0.
    """
    active = [i for i in interests if i.active]
    if not active:
        return 0.0

    text = candidate.raw_text.lower()

    weighted_score = 0.0
    for interest in active:
        keyword = interest.keyword.lower()
        if keyword in text:
            # Exact phrase match: full score for this interest
            match_score = 100.0
        else:
            # Partial match: check if all words of keyword appear individually
            words = keyword.split()
            matches = sum(
                1 for w in words if re.search(r"\b" + re.escape(w) + r"\b", text)
            )
            match_score = (matches / len(words)) * 100.0 if words else 0.0

        # Each interest contributes match_score * weight,
        # averaged over all active interests
        weighted_score += match_score * interest.weight

    # Normalize: divide by number of active interests so one fully-weighted
    # exact match = 100, one half-weighted exact match = 50.
    return min(100.0, weighted_score / len(active))


def generate_summary(candidate: CandidateLead) -> str:
    """Generate a 1–3 sentence summary for a candidate lead.

    V1: Extract sentences containing the candidate's name from raw_text.
    Future: Use LLM if OPENAI_API_KEY is set.

    Args:
        candidate: The candidate to summarize.

    Returns:
        Summary string (may be empty if no matching sentences found).
    """
    sentences = re.split(r"(?<=[.!?])\s+", candidate.raw_text)
    name_lower = candidate.name.lower()
    relevant = [s for s in sentences if name_lower in s.lower()]

    if relevant:
        return " ".join(relevant[:2]).strip()

    # Fallback: first 2 sentences of raw_text
    return " ".join(sentences[:2]).strip()


def get_active_interests(db: Session) -> list[InterestConfig]:
    """Return all active interest configs.

    Args:
        db: Database session.

    Returns:
        List of active InterestConfig objects.
    """
    return db.query(InterestConfig).filter(InterestConfig.active.is_(True)).all()


def get_matched_interest_ids(
    candidate: CandidateLead,
    interests: list[InterestConfig],
) -> list[int]:
    """Return IDs of interests that scored > 0 for this candidate.

    Args:
        candidate: The candidate lead to check.
        interests: Interest configs to evaluate against.

    Returns:
        List of InterestConfig IDs that had any match (score > 0).
    """
    matched: list[int] = []
    text = candidate.raw_text.lower()
    for interest in interests:
        if not interest.active:
            continue
        keyword = interest.keyword.lower()
        if keyword in text:
            matched.append(interest.id)
        else:
            words = keyword.split()
            if words and any(
                re.search(r"\b" + re.escape(w) + r"\b", text) for w in words
            ):
                matched.append(interest.id)
    return matched


def get_today_lead(db: Session) -> Lead | None:
    """Return today's first lead if it exists (rank=1).

    Args:
        db: Database session.

    Returns:
        Lead for today with rank=1, or None.
    """
    return db.query(Lead).filter(Lead.date == date.today(), Lead.rank == 1).first()


def get_leads_by_date(db: Session, target_date: date) -> list[Lead]:
    """Return all leads for a given date, ordered by rank.

    Args:
        db: Database session.
        target_date: The calendar date to query.

    Returns:
        List of Lead objects ordered by rank ascending.
    """
    return db.query(Lead).filter(Lead.date == target_date).order_by(Lead.rank).all()


def get_lead_by_id(db: Session, lead_id: int) -> Lead:
    """Return a lead by ID.

    Args:
        db: Database session.
        lead_id: Lead primary key.

    Returns:
        Lead ORM object.

    Raises:
        SourceNotFoundError: If lead does not exist.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise SourceNotFoundError(f"Lead {lead_id} not found")
    return lead


def list_leads(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    source_type: str | None = None,
) -> tuple[list[Lead], int]:
    """Return a paginated list of leads.

    Args:
        db: Database session.
        skip: Number of records to skip.
        limit: Maximum records to return.
        source_type: Optional filter by source type.

    Returns:
        Tuple of (leads, total_count).
    """
    query = db.query(Lead).order_by(Lead.date.desc(), Lead.rank)
    if source_type:
        query = query.filter(Lead.source_type == source_type)
    total = query.count()
    return query.offset(skip).limit(limit).all(), total


def select_top_candidates(
    candidates: list[CandidateLead],
    interests: list[InterestConfig],
    n: int = 3,
) -> list[CandidateLead]:
    """Score all candidates and return the top-n unique by URL.

    Args:
        candidates: All raw candidates from all scrapers.
        interests: Active interest configs.
        n: Number of top candidates to return.

    Returns:
        Up to n candidates sorted by score descending.
    """
    if not candidates:
        return []

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique: list[CandidateLead] = []
    for c in candidates:
        if c.url not in seen_urls:
            seen_urls.add(c.url)
            unique.append(c)

    scored = [(c, score_candidate(c, interests)) for c in unique]
    scored.sort(key=lambda x: x[1], reverse=True)

    top = scored[:n]
    logger.info(
        "top_candidates_selected",
        count=len(top),
        top_score=top[0][1] if top else 0,
        candidates_evaluated=len(unique),
    )
    return [c for c, _ in top]


# Keep select_winner as a backward-compatible alias (used by scheduler)
def select_winner(
    candidates: list[CandidateLead],
    interests: list[InterestConfig],
) -> CandidateLead | None:
    """Return the single highest-scoring candidate (backward compat)."""
    top = select_top_candidates(candidates, interests, n=1)
    return top[0] if top else None


def create_leads_from_candidates(
    db: Session,
    candidates: list[CandidateLead],
    interests: list[InterestConfig],
    target_date: date | None = None,
) -> list[Lead]:
    """Persist top candidates as Leads for the given date.

    Skips ranks that already have a lead for that date (idempotent).

    Args:
        db: Database session.
        candidates: Ordered list (rank = index+1).
        interests: Used to compute matched_interests.
        target_date: Date to store leads for; defaults to today.

    Returns:
        List of newly created Lead objects.
    """
    today = target_date or date.today()
    created: list[Lead] = []

    for rank, candidate in enumerate(candidates, start=1):
        existing = db.query(Lead).filter(Lead.date == today, Lead.rank == rank).first()
        if existing:
            logger.info(
                "lead_exists_skipping",
                date=str(today),
                rank=rank,
            )
            continue

        matched_ids = get_matched_interest_ids(candidate, interests)
        summary = generate_summary(candidate)
        lead = Lead(
            date=today,
            rank=rank,
            name=candidate.name,
            title=candidate.title,
            affiliation=candidate.affiliation,
            url=candidate.url,
            summary=summary,
            source_type=candidate.source_type,
            contact_hint=candidate.contact_hint,
            matched_interests=json.dumps(matched_ids),
            created_at=datetime.utcnow(),
        )
        db.add(lead)
        db.flush()  # get ID before commit
        created.append(lead)

    if created:
        db.commit()
        for lead in created:
            db.refresh(lead)
        logger.info("leads_created", count=len(created), date=str(today))

    return created


def create_lead_from_candidate(
    db: Session,
    candidate: CandidateLead,
    interests: list[InterestConfig],
) -> Lead:
    """Persist the winning candidate as a Lead for today (backward compat).

    Args:
        db: Database session.
        candidate: The winning candidate.
        interests: Used to generate matched_interests.

    Returns:
        The newly created Lead.

    Raises:
        LeadExistsError: If a lead already exists for today at rank=1.
    """
    today = date.today()
    existing = db.query(Lead).filter(Lead.date == today, Lead.rank == 1).first()
    if existing:
        raise LeadExistsError(f"Lead already exists for {today}")

    leads = create_leads_from_candidates(db, [candidate], interests, target_date=today)
    return leads[0]
