from __future__ import annotations

import re
from urllib.parse import urlparse

import structlog

from app.exceptions import ScraperError
from app.scrapers.base import BaseScraper, CandidateLead

logger = structlog.get_logger(__name__)

# Reuse the same person-indicator heuristic as NewsScraper / RssScraper
_PERSON_INDICATORS = re.compile(
    r"\b(dr\.?|professor|prof\.?|ceo|founder|director|researcher|scientist|"
    r"engineer|author|journalist|attorney|lawyer|chef|artist|musician|"
    r"inventor|entrepreneur|activist|physician|surgeon)\b",
    re.IGNORECASE,
)

_DEFAULT_MAX_ARTICLES = 12


class SubstackScraper(BaseScraper):
    """Scraper for Substack publications via the public Substack JSON API.

    Uses ``/api/v1/posts`` — no JS rendering or browser automation needed.

    Config keys:
        seed_urls (list[str]): Substack publication base URLs
            (e.g. ``https://example.substack.com``).
        max_articles (int): Max posts to fetch per publication (default 12).
    """

    source_name = "substack"

    def fetch_candidates(self, config: dict) -> list[CandidateLead]:
        """Fetch candidates from Substack publication feeds.

        Args:
            config: Source configuration with seed_urls and optional max_articles.

        Returns:
            List of CandidateLead dataclasses.
        """
        seed_urls: list[str] = config.get("seed_urls", [])
        max_articles: int = config.get("max_articles", _DEFAULT_MAX_ARTICLES)

        if not seed_urls:
            logger.warning("no_seed_urls", source=self.source_name)
            return []

        logger.info("scraper_start", source=self.source_name, seed_count=len(seed_urls))
        candidates: list[CandidateLead] = []

        for base_url in seed_urls:
            base_url = base_url.rstrip("/")
            try:
                pub_candidates = self._process_publication(base_url, max_articles)
                candidates.extend(pub_candidates)
            except ScraperError as exc:
                logger.warning(
                    "publication_failed",
                    source=self.source_name,
                    url=base_url,
                    error=str(exc),
                )

        logger.info(
            "scraper_complete",
            source=self.source_name,
            candidates=len(candidates),
        )
        return candidates

    def _process_publication(  # noqa: E501
        self, base_url: str, max_articles: int
    ) -> list[CandidateLead]:
        """Fetch and process posts from a single Substack publication.

        Args:
            base_url: Base URL of the Substack publication (no trailing slash).
            max_articles: Maximum number of posts to fetch.

        Returns:
            List of CandidateLead dataclasses.
        """
        api_url = f"{base_url}/api/v1/posts?limit={max_articles}"
        posts = self._get_json(api_url)

        if not isinstance(posts, list):
            logger.warning(
                "unexpected_api_response",
                source=self.source_name,
                url=api_url,
            )
            return []

        domain = urlparse(base_url).netloc
        candidates: list[CandidateLead] = []

        for post in posts[:max_articles]:
            candidate = self._process_post(post, base_url, domain)
            if candidate:
                candidates.append(candidate)

        return candidates

    def _process_post(
        self, post: dict, base_url: str, domain: str
    ) -> CandidateLead | None:
        """Convert a single Substack post dict to a CandidateLead, or None.

        Args:
            post: Post dict from the Substack API.
            base_url: Base URL of the publication (used for contact hint fallback).
            domain: Netloc of the publication (fallback affiliation).

        Returns:
            CandidateLead or None if not person-relevant.
        """
        title: str = post.get("title", "")
        subtitle: str = post.get("subtitle", "") or ""
        description: str = post.get("description", "") or ""

        combined_text = " ".join(filter(None, [title, subtitle, description]))

        # Heuristic: only yield if text hints at a person
        if not _PERSON_INDICATORS.search(combined_text):
            logger.debug(
                "no_person_indicator",
                source=self.source_name,
                title=title[:80],
            )
            return None

        # Author name from publishedBylines
        bylines: list[dict] = post.get("publishedBylines", [])
        name = bylines[0].get("name", "") if bylines else ""
        if not name:
            # Fallback: scan title for capitalized name pattern
            name = self._extract_name_from_text(title) or self._extract_name_from_text(
                combined_text
            )
        if not name:
            return None

        # Affiliation: publication name → domain
        pub: dict = post.get("publication", {}) or {}
        affiliation: str = pub.get("name", "") or domain

        # Canonical URL
        url: str = post.get("canonical_url", "") or base_url

        # Contact hint: author's Substack profile if handle available
        contact_hint: str | None = None
        if bylines:
            handle: str = bylines[0].get("handle", "") or ""
            if handle:
                contact_hint = f"{base_url}/@{handle}"

        return CandidateLead(
            name=name,
            title=self._extract_title_from_text(combined_text),
            affiliation=affiliation,
            url=url,
            raw_text=combined_text[:5000],
            source_type="news",
            contact_hint=contact_hint,
        )

    def _extract_name_from_text(self, text: str) -> str:
        """Extract a capitalized person name pattern from free text.

        Args:
            text: Any text string.

        Returns:
            Matched name or empty string.
        """
        m = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})", text)
        return m.group(1) if m else ""

    def _extract_title_from_text(self, text: str) -> str:
        """Extract a likely job title excerpt from text using indicator words.

        Args:
            text: Combined post text.

        Returns:
            Short excerpt around the matched indicator, or empty string.
        """
        match = _PERSON_INDICATORS.search(text)
        if match:
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 40)
            return text[start:end].strip()
        return ""
