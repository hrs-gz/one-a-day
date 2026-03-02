from __future__ import annotations

import structlog

from app.scrapers.base import CandidateLead
from app.scrapers.news import NewsScraper

logger = structlog.get_logger(__name__)


class LocalNewsScraper(NewsScraper):
    """Scraper for local newspaper and regional publication websites.

    Inherits all logic from NewsScraper — the distinction is in the source_type
    tag applied to candidates, allowing downstream filtering by source.

    Config keys: Same as NewsScraper.
    """

    source_name = "local_news"

    def fetch_candidates(self, config: dict) -> list[CandidateLead]:
        """Fetch candidates from local news pages.

        Args:
            config: Source configuration (same as NewsScraper).

        Returns:
            List of CandidateLead dataclasses with source_type='local_news'.
        """
        candidates = super().fetch_candidates(config)
        # Re-tag source_type for local news distinction
        return [
            CandidateLead(
                name=c.name,
                title=c.title,
                affiliation=c.affiliation,
                url=c.url,
                raw_text=c.raw_text,
                source_type="local_news",
                contact_hint=c.contact_hint,
            )
            for c in candidates
        ]
