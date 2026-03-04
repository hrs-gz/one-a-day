"""Card-writer agent — produces scoring cards from verified facts."""

from __future__ import annotations

from app.agents.base import BaseAgent
from app.models.interest_config import InterestConfig
from app.schemas.agent_contracts import ScoringCard, VerifiedLeadBundle


class CardWriterAgent(BaseAgent[ScoringCard]):
    """Renders a ScoringCard from verified facts and user interests."""

    agent_name = "card_writer"
    output_type = ScoringCard

    def run(
        self,
        bundle: VerifiedLeadBundle,
        interests: list[InterestConfig],
    ) -> ScoringCard:
        keywords = [f"{i.keyword} (weight={i.weight})" for i in interests if i.active]
        facts_text = "\n".join(
            f'- {f.claim} [excerpt: "{f.excerpt}"]' for f in bundle.facts
        )
        contacts_text = (
            "\n".join(f"- {c.type}: {c.value}" for c in bundle.contact_paths)
            or "None found"
        )

        prompt = (
            f"Person: {bundle.identity.name}\n"
            f"Title: {bundle.identity.title}\n"
            f"Affiliation: {bundle.identity.affiliation}\n"
            f"Source URL: {bundle.source_url}\n\n"
            f"Verified facts:\n{facts_text}\n\n"
            f"Contact paths:\n{contacts_text}\n\n"
            "User interests:\n"
            + "\n".join(f"- {k}" for k in keywords)
            + "\n\nProduce a ScoringCard JSON. Score dimensions: "
            "relevance (0-40), novelty (0-20), authority (0-15), "
            "reachability (0-15), timeliness (0-10). "
            "Write a 1-3 sentence summary. Include evidence items "
            "and any follow-up research questions."
        )
        return self._run(prompt)
