"""Agentic pipeline orchestrator (Phase 2).

Replaces the classic scrape → score → select path with:
    plan → query → gather → verify → write → select → persist

Gated behind PIPELINE_MODE=agentic in app.config.
"""

from __future__ import annotations

import time
from collections import defaultdict

import httpx
import structlog
from sqlalchemy.orm import Session

from app.agents.card_writer import CardWriterAgent
from app.agents.planner import PlannerAgent
from app.agents.query_builder import QueryBuilderAgent
from app.agents.verifier_extractor import VerifierExtractorAgent
from app.config import settings
from app.exceptions import AgentError
from app.models.interest_config import InterestConfig
from app.models.lead import Lead
from app.models.scraper_source import ScraperSource
from app.schemas.agent_contracts import ScoringCard, VerifiedLeadBundle
from app.scrapers.base import CandidateLead
from app.services import lead_service, scrape_service

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Simple in-memory page cache with TTL
# ---------------------------------------------------------------------------

_page_cache: dict[str, tuple[str, float]] = {}

# TTL in seconds (from config/models.yaml runtime.caching.page_ttl_days)
_TTL_NEWS = 10 * 86400
_TTL_FACULTY = 45 * 86400


def _get_page_text(url: str, source_type: str = "news") -> str | None:
    """Fetch page text with caching.  Returns None on failure."""
    now = time.time()
    ttl = _TTL_NEWS if source_type == "news" else _TTL_FACULTY

    if url in _page_cache:
        text, cached_at = _page_cache[url]
        if now - cached_at < ttl:
            return text

    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": settings.scraper_user_agent},
            follow_redirects=True,
            timeout=15.0,
        )
        if resp.status_code != 200:
            return None
        text = resp.text
        _page_cache[url] = (text, now)
        return text
    except Exception:
        logger.warning("page_fetch_failed", url=url)
        return None


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------


def _step_plan(
    interests: list[InterestConfig],
    source_names: list[str],
):
    """Step 1: Plan the daily run."""
    logger.info("agentic_step", step="plan")
    planner = PlannerAgent()
    return planner.run(interests, source_names)


def _step_query(plan, interests: list[InterestConfig]):
    """Step 2: Build search queries."""
    logger.info("agentic_step", step="query")
    qb = QueryBuilderAgent()
    return qb.run(plan, interests)


def _step_gather(db: Session) -> list[CandidateLead]:
    """Step 3: Run classic scrapers to get raw candidates.

    Reuses the existing scrape_service to fetch candidates.
    """
    logger.info("agentic_step", step="gather")
    return scrape_service.run_all_scrapers(db)


def _step_verify(
    candidates: list[CandidateLead],
    max_candidates: int = 20,
) -> list[VerifiedLeadBundle]:
    """Step 4: Verify top candidates by fetching their pages and extracting facts."""
    logger.info("agentic_step", step="verify", candidate_count=len(candidates))
    verifier = VerifierExtractorAgent()
    bundles: list[VerifiedLeadBundle] = []

    for candidate in candidates[:max_candidates]:
        page_text = _get_page_text(candidate.url, candidate.source_type)
        if not page_text:
            logger.warning(
                "verify_skip_no_page",
                url=candidate.url,
                name=candidate.name,
            )
            continue

        try:
            bundle = verifier.run(candidate.url, page_text)
            if bundle.facts:
                bundles.append(bundle)
                logger.info(
                    "verify_success",
                    name=bundle.identity.name,
                    facts=len(bundle.facts),
                )
            else:
                logger.info("verify_no_facts", url=candidate.url)
        except AgentError:
            logger.warning(
                "verify_agent_error",
                url=candidate.url,
                exc_info=True,
            )

    return bundles


def _step_write(
    bundles: list[VerifiedLeadBundle],
    interests: list[InterestConfig],
) -> list[ScoringCard]:
    """Step 5: Write scoring cards from verified bundles."""
    logger.info("agentic_step", step="write", bundle_count=len(bundles))
    writer = CardWriterAgent()
    cards: list[ScoringCard] = []

    for bundle in bundles:
        try:
            card = writer.run(bundle, interests)
            cards.append(card)
            logger.info(
                "card_written",
                name=card.name,
                total_score=card.total_score,
            )
        except AgentError:
            logger.warning(
                "card_write_error",
                name=bundle.identity.name,
                exc_info=True,
            )

    return cards


def _step_select(
    cards: list[ScoringCard],
    max_per_org: int = 1,
    leads_per_day: int = 3,
) -> list[ScoringCard]:
    """Step 6: Deterministic selection — sort by score, enforce constraints."""
    logger.info("agentic_step", step="select", card_count=len(cards))

    # Sort by total score descending
    ranked = sorted(cards, key=lambda c: c.total_score, reverse=True)

    # Enforce max_per_org
    org_counts: dict[str, int] = defaultdict(int)
    selected: list[ScoringCard] = []

    for card in ranked:
        org = card.affiliation.strip().lower() if card.affiliation else ""
        if org and org_counts[org] >= max_per_org:
            continue
        selected.append(card)
        if org:
            org_counts[org] += 1
        if len(selected) >= leads_per_day:
            break

    logger.info(
        "selection_complete",
        selected=len(selected),
        top_score=selected[0].total_score if selected else 0,
    )
    return selected


def _cards_to_candidates(cards: list[ScoringCard]) -> list[CandidateLead]:
    """Convert ScoringCards back to CandidateLeads for persistence."""
    return [
        CandidateLead(
            name=card.name,
            title=card.title,
            affiliation=card.affiliation,
            url=card.source_url,
            raw_text=card.summary,
            source_type=card.source_type,  # type: ignore[arg-type]
            contact_hint=card.contact_hint,
        )
        for card in cards
    ]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_agentic_pipeline(db: Session) -> list[Lead]:
    """Run the full agentic pipeline and persist leads.

    Steps: plan → query → gather → verify → write → select → persist.

    Args:
        db: Database session.

    Returns:
        List of newly created Lead objects.
    """
    logger.info("agentic_pipeline_start")

    # Gather inputs
    interests = lead_service.get_active_interests(db)
    sources = db.query(ScraperSource).filter(ScraperSource.enabled.is_(True)).all()
    source_names = [s.name for s in sources]

    if not interests:
        logger.warning("agentic_no_interests")
        return []

    if not source_names:
        logger.warning("agentic_no_sources")
        return []

    # Step 1: Plan
    try:
        plan = _step_plan(interests, source_names)
    except (AgentError, Exception):
        logger.error("agentic_plan_failed", exc_info=True)
        logger.info("agentic_fallback_to_classic")
        return _fallback_classic(db, interests)

    # Step 2: Query (informational — logged but queries not directly used yet)
    try:
        query_pack = _step_query(plan, interests)
        logger.info(
            "queries_generated",
            count=len(query_pack.queries),
        )
    except (AgentError, Exception):
        logger.warning("agentic_query_failed", exc_info=True)
        # Non-fatal — continue with classic gather

    # Step 3: Gather (reuse classic scrapers)
    candidates = _step_gather(db)
    if not candidates:
        logger.warning("agentic_no_candidates")
        return []

    # Pre-score to prioritise which candidates to verify
    scored = [(c, lead_service.score_candidate(c, interests)) for c in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    top_candidates = [c for c, _ in scored[:20]]

    # Step 4: Verify
    bundles = _step_verify(top_candidates)
    if not bundles:
        logger.warning("agentic_no_verified_bundles")
        logger.info("agentic_fallback_to_classic")
        return _fallback_classic(db, interests)

    # Step 5: Write scoring cards
    cards = _step_write(bundles, interests)
    if not cards:
        logger.warning("agentic_no_cards")
        return _fallback_classic(db, interests)

    # Step 6: Select
    selected = _step_select(
        cards,
        max_per_org=plan.constraints.max_per_org,
        leads_per_day=plan.constraints.leads_per_day,
    )
    if not selected:
        return _fallback_classic(db, interests)

    # Step 7: Persist
    logger.info("agentic_step", step="persist", count=len(selected))
    final_candidates = _cards_to_candidates(selected)
    leads = lead_service.create_leads_from_candidates(db, final_candidates, interests)

    logger.info(
        "agentic_pipeline_complete",
        leads_created=len(leads),
    )
    return leads


def _fallback_classic(
    db: Session,
    interests: list[InterestConfig],
) -> list[Lead]:
    """Fall back to the classic pipeline when agentic steps fail."""
    logger.info("fallback_classic_start")
    candidates = scrape_service.run_all_scrapers(db)
    if not candidates:
        return []
    top = lead_service.select_top_candidates(candidates, interests, n=3)
    if not top:
        return []
    return lead_service.create_leads_from_candidates(db, top, interests)
