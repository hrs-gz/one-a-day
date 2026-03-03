"""Verifier/Extractor agent — fetches pages and emits evidence-gated fact bundles."""

from __future__ import annotations

import json

import httpx
import structlog
from bs4 import BeautifulSoup

from app.config import settings
from app.llm.gemini_client import GeminiClient
from app.schemas.agent_contracts import VerifiedLeadBundle

logger = structlog.get_logger(__name__)

MODEL = "gemini-2.5-flash-lite"

# Trim page text to keep prompts within token budgets
_MAX_CONTENT_CHARS = 8_000

_SYSTEM = """\
You are the Verifier/Extractor for a lead-discovery pipeline.

Given the text content of a webpage, extract structured facts about a specific
person found on that page.

Rules:
- Every fact MUST include the source URL and a verbatim excerpt copied
  directly from the page text. Never paraphrase an excerpt.
- If a fact cannot be grounded in a direct quote from the page, omit it.
  Never fabricate.
- Extract facts about one specific person only (the most prominent person
  on the page).
- Prefer concrete, specific facts over vague claims.

Return ONLY valid JSON — no prose, no markdown fences:
{
  "identity": {"name": "Dr. Jane Smith", "role": "Associate Professor", "org": "MIT"},
  "urls": ["https://example.edu/faculty/jsmith"],
  "facts": [
    {
      "fact": "Researches urban resilience",
      "url": "https://example.edu/faculty/jsmith",
      "excerpt": "Jane Smith's research focuses on urban resilience"
    }
  ],
  "contact_paths": [
    {
      "type": "email",
      "url": "mailto:jsmith@mit.edu",
      "excerpt": "Contact: jsmith@mit.edu"
    }
  ]
}

If no clear individual person is found, return:
{"identity": {"name": null, "role": null, "org": null},
 "urls": [], "facts": [], "contact_paths": []}
"""


def _fetch_page_text(url: str) -> str | None:
    """Fetch a URL and return trimmed plain text (strips scripts/nav/footer)."""
    try:
        response = httpx.get(
            url,
            headers={"User-Agent": settings.scraper_user_agent},
            follow_redirects=True,
            timeout=15.0,
        )
        if response.status_code != 200:
            logger.debug("verifier_fetch_non200", url=url, status=response.status_code)
            return None
        soup = BeautifulSoup(response.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text[:_MAX_CONTENT_CHARS]
    except Exception as exc:
        logger.warning("verifier_fetch_failed", url=url, error=str(exc))
        return None


def run(
    urls: list[str],
    client: GeminiClient | None = None,
) -> list[VerifiedLeadBundle]:
    """Run the Verifier/Extractor agent on a list of candidate URLs.

    Fetches each URL, sends the page text to the LLM, and parses the
    structured response. Bundles whose identity has no ``name`` are
    discarded. Facts that fail evidence gating (missing url or excerpt)
    cause the entire bundle to be skipped.

    Args:
        urls: Candidate URLs to fetch and verify.
        client: LLM client; constructed from env vars if omitted.

    Returns:
        List of valid ``VerifiedLeadBundle`` objects (one per URL that
        yielded a named individual).
    """
    if client is None:
        client = GeminiClient()

    bundles: list[VerifiedLeadBundle] = []

    for url in urls:
        logger.info("verifier_processing", url=url)
        page_text = _fetch_page_text(url)
        if not page_text:
            continue

        user_prompt = f"URL: {url}\n\nPage content:\n{page_text}"
        try:
            raw = client.complete(MODEL, _SYSTEM, user_prompt)
            data = json.loads(raw)
            bundle = VerifiedLeadBundle.model_validate(data)
            if bundle.identity.name:
                bundles.append(bundle)
                logger.info(
                    "verifier_extracted",
                    name=bundle.identity.name,
                    fact_count=len(bundle.facts),
                    url=url,
                )
            else:
                logger.debug("verifier_no_person", url=url)
        except Exception as exc:
            logger.warning("verifier_bundle_failed", url=url, error=str(exc))

    logger.info("verifier_complete", bundle_count=len(bundles))
    return bundles
