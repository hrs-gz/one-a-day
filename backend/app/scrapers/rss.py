from __future__ import annotations

import re
from urllib.parse import urlparse

import feedparser
import structlog
from bs4 import BeautifulSoup

from app.exceptions import ScraperError
from app.scrapers.base import BaseScraper, CandidateLead

logger = structlog.get_logger(__name__)

# Reuse the same person-indicator heuristic as NewsScraper
_PERSON_INDICATORS = re.compile(
    r"\b(dr\.?|professor|prof\.?|ceo|founder|director|researcher|scientist|"
    r"engineer|author|journalist|attorney|lawyer|chef|artist|musician|"
    r"inventor|entrepreneur|activist|physician|surgeon)\b",
    re.IGNORECASE,
)


class RssScraper(BaseScraper):
    """Scraper for RSS and Atom feeds — extracts person mentions from entries.

    Config keys:
        seed_urls (list[str]): Feed URLs (RSS 2.0, Atom, or JSON Feed).
        max_entries (int): Max entries to process per feed (default 20).
    """

    source_name = "rss"

    def fetch_candidates(self, config: dict) -> list[CandidateLead]:
        """Fetch candidates from RSS/Atom feed entries.

        Args:
            config: Source configuration with seed_urls and optional max_entries.

        Returns:
            List of CandidateLead dataclasses.
        """
        seed_urls: list[str] = config.get("seed_urls", [])
        max_entries: int = config.get("max_entries", 20)

        if not seed_urls:
            logger.warning("no_seed_urls", source=self.source_name)
            return []

        logger.info("scraper_start", source=self.source_name, seed_count=len(seed_urls))
        candidates: list[CandidateLead] = []

        for feed_url in seed_urls:
            try:
                feed_candidates = self._process_feed(feed_url, max_entries)
                candidates.extend(feed_candidates)
            except ScraperError as exc:
                logger.warning(
                    "feed_failed",
                    source=self.source_name,
                    url=feed_url,
                    error=str(exc),
                )

        logger.info(
            "scraper_complete",
            source=self.source_name,
            candidates=len(candidates),
        )
        return candidates

    def _process_feed(self, feed_url: str, max_entries: int) -> list[CandidateLead]:
        """Fetch and parse a single feed URL.

        Args:
            feed_url: URL of the RSS or Atom feed.
            max_entries: Maximum number of entries to process.

        Returns:
            List of CandidateLead dataclasses found in this feed.
        """
        raw_bytes = self._get_raw(feed_url)
        feed = feedparser.parse(raw_bytes)

        feed_title: str = feed.feed.get("title", "") if hasattr(feed, "feed") else ""
        domain = urlparse(feed_url).netloc

        candidates: list[CandidateLead] = []

        for entry in feed.entries[:max_entries]:
            candidate = self._process_entry(entry, feed_title, domain, feed_url)
            if candidate:
                candidates.append(candidate)

        return candidates

    def _process_entry(
        self,
        entry: feedparser.util.FeedParserDict,
        feed_title: str,
        domain: str,
        feed_url: str,
    ) -> CandidateLead | None:
        """Convert a single feed entry to a CandidateLead, or None if irrelevant.

        Args:
            entry: Parsed feedparser entry dict.
            feed_title: Title of the feed (used as affiliation).
            domain: Domain of the feed (fallback affiliation).
            feed_url: Source feed URL (fallback candidate URL).

        Returns:
            CandidateLead or None.
        """
        title: str = entry.get("title", "")
        summary_html: str = entry.get("summary", "")

        # Also check content if available
        content_html = ""
        if entry.get("content"):
            content_html = entry["content"][0].get("value", "")

        raw_html = summary_html or content_html

        # Heuristic: only yield if title or summary hints at a person
        combined_text = title + " " + raw_html
        if not _PERSON_INDICATORS.search(combined_text):
            logger.debug(
                "no_person_indicator",
                source=self.source_name,
                title=title[:80],
            )
            return None

        # Extract name from author field, then fall back to text patterns
        author_field: str = entry.get("author", "")
        raw_text = self._strip_html(raw_html)
        name = self._extract_name(author_field, title, raw_text)
        if not name:
            return None

        url: str = entry.get("link", feed_url)
        affiliation: str = feed_title or domain

        # Try to extract contact hint from summary HTML (anchor tags first,
        # then bare LinkedIn URLs in plain text)
        contact_hint: str | None = None
        if raw_html:
            soup = BeautifulSoup(raw_html, "lxml")
            contact_hint = self._extract_contact_hint(soup, url)
            if not contact_hint:
                contact_hint = self._extract_contact_hint_from_text(raw_html)

        return CandidateLead(
            name=name,
            title=self._extract_title_from_text(combined_text),
            affiliation=affiliation,
            url=url,
            raw_text=(title + " " + raw_text)[:5000],
            source_type="rss",
            contact_hint=contact_hint,
        )

    def _extract_name(self, author: str, title: str, raw_text: str) -> str:
        """Extract a person name from the author field, title, or body text.

        Args:
            author: Author field from the feed entry.
            title: Entry title.
            raw_text: Plain text body.

        Returns:
            Best guess at a person name, or empty string.
        """
        # Author field: strip "By " prefix, then grab 2–4 capitalized words
        if author:
            author_clean = re.sub(r"^[Bb]y\s+", "", author.strip())
            m = re.match(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})", author_clean)
            if m:
                return m.group(1)

        # Fallback: scan title for a capitalized name pattern
        m = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})", title)
        if m:
            return m.group(1)

        # Last resort: scan raw text
        m = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})", raw_text)
        if m:
            return m.group(1)

        return ""

    def _extract_title_from_text(self, text: str) -> str:
        """Extract a likely job title from text using indicator words.

        Args:
            text: Combined title + body text.

        Returns:
            Short excerpt around the matched indicator, or empty string.
        """
        match = _PERSON_INDICATORS.search(text)
        if match:
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 40)
            return text[start:end].strip()
        return ""

    @staticmethod
    def _extract_contact_hint_from_text(text: str) -> str | None:
        """Scan raw text for a bare LinkedIn URL or mailto address.

        Args:
            text: Raw HTML or plain text string.

        Returns:
            LinkedIn URL, email address, or None.
        """
        linkedin_match = re.search(r"https?://(?:www\.)?linkedin\.com/in/[\w\-]+", text)
        if linkedin_match:
            return linkedin_match.group(0)
        mailto_match = re.search(r"mailto:([\w.+\-]+@[\w.\-]+)", text)
        if mailto_match:
            return mailto_match.group(1)
        return None

    @staticmethod
    def _strip_html(html: str) -> str:
        """Strip HTML tags from a string, returning plain text.

        Args:
            html: Raw HTML string.

        Returns:
            Plain text with tags removed.
        """
        if not html:
            return ""
        return BeautifulSoup(html, "lxml").get_text(separator=" ", strip=True)
