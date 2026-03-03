"""Query Builder agent — produces structured search queries from a DailyRunPlan."""

from __future__ import annotations

import json

import structlog

from app.llm.openrouter_client import OpenRouterClient
from app.models.interest_config import InterestConfig
from app.schemas.agent_contracts import CandidateQueryPack, DailyRunPlan, SearchQuery

logger = structlog.get_logger(__name__)

MODEL = "liquid/lfm-2.5-1.2b-thinking:free"

_SYSTEM = """\
You are the Query Builder for a lead-discovery pipeline.

Given a run plan and active user interests, generate a CandidateQueryPack:
a list of structured search queries to find specific interesting people
(researchers, professionals, operators, independent thinkers).

Rules:
- Return ONLY valid JSON — no prose, no markdown fences.
- Each query must have a "q" field (string). Other fields are optional.
- Generate 2–4 queries total across all source packs.
- Queries must target specific people, not generic topics.
- Prefer queries that include: name-like terms, role/title terms, location
  or institution hints when relevant.

JSON schema:
{
  "queries": [
    {
      "q": "urban planning researcher independent 2024",
      "recency_days": 90,
      "allow_domains": null,
      "deny_domains": null
    }
  ]
}
"""


def run(
    plan: DailyRunPlan,
    interests: list[InterestConfig],
    client: OpenRouterClient | None = None,
) -> CandidateQueryPack:
    """Run the Query Builder agent.

    Args:
        plan: The ``DailyRunPlan`` from the Planner.
        interests: Active interest configs for context.
        client: LLM client; constructed from env vars if omitted.

    Returns:
        ``CandidateQueryPack`` with structured search queries. Falls back
        to keyword-derived queries if the LLM response cannot be parsed.
    """
    if client is None:
        client = OpenRouterClient()

    active = [i for i in interests if i.active]
    interests_text = "\n".join(f"- {i.keyword} (weight={i.weight:.2f})" for i in active)
    user_prompt = (
        f"Source packs: {', '.join(plan.source_packs)}\n"
        f"Leads per day: {plan.leads_per_day}\n"
        f"Max per org: {plan.constraints.max_per_org}\n\n"
        f"Active interests:\n{interests_text}\n\n"
        "Generate a CandidateQueryPack."
    )

    logger.info("query_builder_start", source_packs=plan.source_packs)
    raw = client.complete(MODEL, _SYSTEM, user_prompt)

    try:
        data = json.loads(raw)
        pack = CandidateQueryPack.model_validate(data)
        logger.info("query_builder_complete", query_count=len(pack.queries))
        return pack
    except Exception as exc:
        logger.warning("query_builder_parse_failed", error=str(exc), raw=raw[:300])
        # Fallback: one query per active interest
        fallback_queries = [
            SearchQuery(
                q=f'"{i.keyword}" researcher OR professional OR operator',
                recency_days=180,
            )
            for i in active[:4]
        ]
        return CandidateQueryPack(queries=fallback_queries)
