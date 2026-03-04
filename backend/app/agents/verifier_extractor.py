"""Verifier/extractor agent — extracts verifiable facts from page text."""

from __future__ import annotations

from app.agents.base import BaseAgent
from app.schemas.agent_contracts import VerifiedLeadBundle


class VerifierExtractorAgent(BaseAgent[VerifiedLeadBundle]):
    """Extracts verified facts about a person from fetched page text."""

    agent_name = "verifier_extractor"
    output_type = VerifiedLeadBundle

    def run(self, url: str, page_text: str) -> VerifiedLeadBundle:
        prompt = (
            f"Source URL: {url}\n\n"
            "Page text (truncated to first 4000 chars):\n"
            f"{page_text[:4000]}\n\n"
            "Extract all verifiable facts about the most prominent person "
            "mentioned on this page. For each fact, include the source URL "
            "and a verbatim excerpt. Also extract contact paths (LinkedIn, "
            "email, etc.) and the person's identity (name, title, affiliation).\n\n"
            "Output a VerifiedLeadBundle JSON."
        )
        return self._run(prompt)
