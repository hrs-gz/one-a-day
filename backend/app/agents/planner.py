"""Planner agent — chooses source packs and constraints for the day's run."""

from __future__ import annotations

import json

import structlog

from app.llm.openrouter_client import OpenRouterClient
from app.models.interest_config import InterestConfig
from app.schemas.agent_contracts import DailyRunPlan, DailyRunPlanConstraints

logger = structlog.get_logger(__name__)

MODEL = "arcee-ai/trinity-large-preview:free"

_SYSTEM = """\
You are the Planner for an agentic lead-discovery pipeline.

Given the user's active interests (keywords + weights), decide:
1. How many leads to surface today (1–3, usually 3).
2. Which source packs to search. Valid packs: "academic", "professional",
   "startup", "local", "research", "media", "independent".
3. Constraints: max leads per organization, minimum distinct topic clusters.

Return ONLY valid JSON — no prose, no markdown fences:
{
  "leads_per_day": 3,
  "source_packs": ["academic", "professional"],
  "constraints": {
    "max_per_org": 1,
    "min_topic_clusters": 2
  }
}
"""


def run(
    interests: list[InterestConfig],
    client: OpenRouterClient | None = None,
) -> DailyRunPlan:
    """Run the Planner agent.

    Args:
        interests: Active interest configs from the DB.
        client: LLM client to use; constructed from env vars if omitted.

    Returns:
        ``DailyRunPlan`` with source packs and constraints. Falls back to
        sensible defaults if the LLM response cannot be parsed.
    """
    if client is None:
        client = OpenRouterClient()

    active = [i for i in interests if i.active]
    interests_text = "\n".join(f"- {i.keyword} (weight={i.weight:.2f})" for i in active)
    user_prompt = f"Active interests:\n{interests_text}\n\nProduce a DailyRunPlan."

    logger.info("planner_start", active_interest_count=len(active))
    raw = client.complete(MODEL, _SYSTEM, user_prompt)

    try:
        data = json.loads(raw)
        plan = DailyRunPlan.model_validate(data)
        logger.info(
            "planner_complete",
            source_packs=plan.source_packs,
            leads_per_day=plan.leads_per_day,
        )
        return plan
    except Exception as exc:
        logger.warning("planner_parse_failed", error=str(exc), raw=raw[:300])
        return DailyRunPlan(
            leads_per_day=3,
            source_packs=["academic", "professional", "startup"],
            constraints=DailyRunPlanConstraints(max_per_org=1, min_topic_clusters=2),
        )
