"""Agentic pipeline service — orchestrates the full agent chain.

Pipeline stages:
1. Planner        → DailyRunPlan   (source packs + constraints)
2. Query Builder  → CandidateQueryPack  (structured search queries)
3. Candidate Gatherer → deduplicated URLs  (DuckDuckGo HTML search)
4. Verifier/Extractor → list[VerifiedLeadBundle]  (evidence-gated facts)
5. Card Writer    → list[ScoringCard]  (six-dimension scores)
6. Deterministic Selector → top 1–3  (score sort + diversity constraints)
7. Persist        → list[Lead]
"""

from __future__ import annotations

from datetime import date

import httpx
import structlog
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.agents import card_writer, planner, query_builder, verifier_extractor
from app.config import settings
from app.models.lead import Lead
from app.schemas.agent_contracts import (
    CandidateQueryPack,
    ScoringCard,
    VerifiedLeadBundle,
)
from app.scrapers.base import CandidateLead
from app.services import lead_service

logger = structlog.get_logger(__name__)

_MAX_URLS_PER_QUERY = 3
_MAX_TOTAL_URLS = 15


# ---------------------------------------------------------------------------
# Stage 3: Candidate Gatherer
# ---------------------------------------------------------------------------


def _gather_urls(query_pack: CandidateQueryPack) -> list[str]:
    """Execute search queries via DuckDuckGo HTML and return deduplicated URLs.

    Uses DuckDuckGo's no-JS HTML endpoint — no API key required.
    Domain allow/deny filters from each query are applied before collecting.

    Args:
        query_pack: Structured queries from the Query Builder.

    Returns:
        Deduplicated list of candidate URLs (up to ``_MAX_TOTAL_URLS``).
    """
    seen: set[str] = set()
    urls: list[str] = []
    headers = {
        "User-Agent": settings.scraper_user_agent,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for q in query_pack.queries:
        try:
            response = httpx.post(
                "https://html.duckduckgo.com/html/",
                data={"q": q.q, "b": "", "kl": "us-en"},
                headers=headers,
                timeout=15.0,
                follow_redirects=True,
            )
            if response.status_code != 200:
                logger.warning(
                    "gatherer_search_failed", status=response.status_code, query=q.q
                )
                continue

            soup = BeautifulSoup(response.text, "lxml")
            count = 0
            for a in soup.select("a.result__a"):
                href: str = a.get("href", "")
                if not href.startswith("http"):
                    continue
                if "duckduckgo.com" in href:
                    continue
                if q.deny_domains and any(d in href for d in q.deny_domains):
                    continue
                if q.allow_domains and not any(d in href for d in q.allow_domains):
                    continue
                if href not in seen:
                    seen.add(href)
                    urls.append(href)
                    count += 1
                    if count >= _MAX_URLS_PER_QUERY:
                        break

            logger.debug("gatherer_query_done", query=q.q, found=count)

        except Exception as exc:
            logger.warning("gatherer_query_error", query=q.q, error=str(exc))

    result = urls[:_MAX_TOTAL_URLS]
    logger.info("gatherer_complete", url_count=len(result))
    return result


# ---------------------------------------------------------------------------
# Stage 6: Deterministic Selector
# ---------------------------------------------------------------------------


def _select_top(
    cards: list[tuple[ScoringCard, VerifiedLeadBundle]],
    n: int,
    max_per_org: int,
) -> list[tuple[ScoringCard, VerifiedLeadBundle]]:
    """Sort by score, apply diversity constraints, return top-n.

    Args:
        cards: Pairs of (ScoringCard, VerifiedLeadBundle) to rank.
        n: Maximum number of leads to return.
        max_per_org: Maximum leads allowed from the same organisation.

    Returns:
        Up to ``n`` pairs, sorted by ``score.total`` descending.
    """
    # Stable sort: highest total first
    cards = sorted(cards, key=lambda x: x[0].score.total, reverse=True)

    selected: list[tuple[ScoringCard, VerifiedLeadBundle]] = []
    org_counts: dict[str, int] = {}

    for card, bundle in cards:
        org = (bundle.identity.org or card.lead.org or "").lower().strip()
        if org and org_counts.get(org, 0) >= max_per_org:
            logger.debug("selector_skip_org_cap", org=org, cap=max_per_org)
            continue
        if org:
            org_counts[org] = org_counts.get(org, 0) + 1
        selected.append((card, bundle))
        if len(selected) >= n:
            break

    logger.info(
        "selector_complete",
        selected=len(selected),
        evaluated=len(cards),
    )
    return selected


# ---------------------------------------------------------------------------
# Stage 7: Convert to CandidateLead for persistence
# ---------------------------------------------------------------------------


def _to_candidate(card: ScoringCard, bundle: VerifiedLeadBundle) -> CandidateLead:
    """Convert a ScoringCard + VerifiedLeadBundle into a CandidateLead for DB storage.

    ``raw_text`` is built from fact text + excerpts so that interest-matching
    (``get_matched_interest_ids``) still works correctly.
    """
    raw_text = " ".join(f"{f.fact} {f.excerpt}" for f in bundle.facts)

    # Prefer LinkedIn contact, then first available
    contact_hint: str | None = None
    for cp in bundle.contact_paths:
        if "linkedin" in cp.type.lower() or "linkedin" in cp.url.lower():
            contact_hint = cp.url
            break
    if contact_hint is None and bundle.contact_paths:
        contact_hint = bundle.contact_paths[0].url

    primary_url = card.lead.primary_url or (bundle.urls[0] if bundle.urls else "")

    return CandidateLead(
        name=card.lead.name,
        title=card.lead.role,
        affiliation=card.lead.org,
        url=primary_url,
        raw_text=raw_text,
        source_type="personal",
        contact_hint=contact_hint,
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_agentic_pipeline(db: Session) -> list[Lead]:
    """Run the full agentic pipeline and persist today's leads.

    Args:
        db: Active database session.

    Returns:
        List of newly created ``Lead`` objects (up to 3).
    """
    today = date.today()
    logger.info("agentic_pipeline_start", date=str(today))

    # Load active interests — abort if none configured
    interests = lead_service.get_active_interests(db)
    if not interests:
        logger.warning("agentic_pipeline_no_interests")
        return []

    # Stage 1: Plan
    plan = planner.run(interests)

    # Stage 2: Query Builder
    query_pack = query_builder.run(plan, interests)
    if not query_pack.queries:
        logger.warning("agentic_pipeline_no_queries")
        return []

    # Stage 3: Gather candidate URLs
    urls = _gather_urls(query_pack)
    if not urls:
        logger.warning("agentic_pipeline_no_urls")
        return []

    # Stage 4: Verify + Extract
    bundles = verifier_extractor.run(urls)
    if not bundles:
        logger.warning("agentic_pipeline_no_bundles")
        return []

    # Stage 5: Score each bundle
    cards: list[tuple[ScoringCard, VerifiedLeadBundle]] = []
    for bundle in bundles:
        scoring_card = card_writer.run(bundle, interests)
        if scoring_card is not None:
            cards.append((scoring_card, bundle))

    if not cards:
        logger.warning("agentic_pipeline_no_cards")
        return []

    # Stage 6: Deterministic selection
    top = _select_top(
        cards,
        n=plan.leads_per_day,
        max_per_org=plan.constraints.max_per_org,
    )

    # Stage 7: Persist
    candidates = [_to_candidate(card, bundle) for card, bundle in top]
    leads = lead_service.create_leads_from_candidates(db, candidates, interests)

    logger.info(
        "agentic_pipeline_complete",
        lead_count=len(leads),
        date=str(today),
    )
    return leads
