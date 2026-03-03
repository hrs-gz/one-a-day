"""Card Writer agent — scores a VerifiedLeadBundle and emits a ScoringCard."""

from __future__ import annotations

import json

import structlog

from app.llm.openrouter_client import OpenRouterClient
from app.models.interest_config import InterestConfig
from app.schemas.agent_contracts import ScoringCard, VerifiedLeadBundle

logger = structlog.get_logger(__name__)

MODEL = "meta-llama/llama-3.3-70b-instruct:free"

_SYSTEM = """\
You are the Card Writer for a lead-discovery pipeline.

Given a VerifiedLeadBundle and active user interests, produce a ScoringCard.

Rules:
- Use ONLY facts from the VerifiedLeadBundle — no external knowledge.
- No outreach copy. No email drafts. No contact suggestions beyond what the
  bundle explicitly contains.
- Score each of the six dimensions 0–100, then set total = round(mean of
  all six dimensions). total must be in 0–100.
- why_relevant: 2–4 concise bullet strings explaining match to interests.
- evidence: Pick the 2–3 most compelling excerpts from the bundle's facts.
- questions: 1–3 open questions to investigate further.
- research_tasks: 1–2 specific follow-up tasks with an expected finding.

Scoring dimensions:
- relevance: How closely does their work match the stated interests?
- novelty: How unusual or niche is their angle / approach?
- authority: Seniority, publications, recognition in their domain.
- reachability: Likelihood they respond to a thoughtful cold message.
- timeliness: Is their work recent and actively ongoing?
- diversity: Does this person add a unique perspective vs. a typical lead?

Return ONLY valid JSON — no prose, no markdown fences:
{
  "lead": {
    "name": "Dr. Jane Smith",
    "role": "Associate Professor",
    "org": "MIT",
    "primary_url": "https://example.edu/faculty/jsmith",
    "tags": ["urban planning", "climate"]
  },
  "score": {
    "total": 72,
    "breakdown": {
      "relevance": 90, "novelty": 70, "authority": 75,
      "reachability": 60, "timeliness": 65, "diversity": 70
    }
  },
  "why_relevant": ["Matches 'urban planning' interest at high weight"],
  "evidence": [{"excerpt": "...", "url": "https://..."}],
  "questions": [{"q": "...", "why": "...", "linked_fact_urls": []}],
  "research_tasks": [{"task": "...", "expected_find": "..."}]
}
"""


def run(
    bundle: VerifiedLeadBundle,
    interests: list[InterestConfig],
    client: OpenRouterClient | None = None,
) -> ScoringCard | None:
    """Run the Card Writer agent on a verified lead bundle.

    Args:
        bundle: The ``VerifiedLeadBundle`` from the Verifier/Extractor.
        interests: Active interest configs (for scoring context).
        client: LLM client; constructed from env vars if omitted.

    Returns:
        ``ScoringCard``, or ``None`` if the response cannot be parsed.
    """
    if client is None:
        client = OpenRouterClient()

    active = [i for i in interests if i.active]
    interests_text = "\n".join(f"- {i.keyword} (weight={i.weight:.2f})" for i in active)
    facts_text = "\n".join(
        f'- {f.fact} [source: {f.url}] excerpt: "{f.excerpt}"' for f in bundle.facts
    )
    contacts_text = (
        "\n".join(f"- {c.type}: {c.url}" for c in bundle.contact_paths) or "None"
    )

    user_prompt = (
        f"Person: {bundle.identity.name}, "
        f"{bundle.identity.role} at {bundle.identity.org}\n"
        f"URLs: {', '.join(bundle.urls)}\n\n"
        f"Verified facts:\n{facts_text}\n\n"
        f"Contact paths:\n{contacts_text}\n\n"
        f"User interests:\n{interests_text}\n\n"
        "Produce a ScoringCard."
    )

    logger.info("card_writer_start", name=bundle.identity.name)
    raw = client.complete(MODEL, _SYSTEM, user_prompt)

    try:
        data = json.loads(raw)
        # Recompute total as mean of dimensions to enforce 0-100 invariant
        if "score" in data and "breakdown" in data["score"]:
            bd = data["score"]["breakdown"]
            dims = [
                "relevance",
                "novelty",
                "authority",
                "reachability",
                "timeliness",
                "diversity",
            ]
            vals = [int(bd.get(d, 0)) for d in dims]
            data["score"]["total"] = round(sum(vals) / len(vals))
        card = ScoringCard.model_validate(data)
        logger.info(
            "card_writer_complete",
            name=bundle.identity.name,
            total=card.score.total,
        )
        return card
    except Exception as exc:
        logger.warning(
            "card_writer_parse_failed",
            name=bundle.identity.name,
            error=str(exc),
            raw=raw[:300],
        )
        return None
