from __future__ import annotations

import re
from urllib.parse import urljoin

import structlog

from app.exceptions import ScraperError
from app.scrapers.base import BaseScraper, CandidateLead

logger = structlog.get_logger(__name__)

# Simple heuristic: titles that likely refer to a person rather than a topic
_PERSON_INDICATORS = re.compile(
    r"\b(dr\.?|professor|prof\.?|ceo|founder|director|researcher|scientist|"
    r"engineer|author|journalist|attorney|lawyer|chef|artist|musician|"
    r"inventor|entrepreneur|activist|physician|surgeon)\b",
    re.IGNORECASE,
)


class NewsScraper(BaseScraper):
    """Scraper for news headline pages — extracts person mentions from articles.

    Config keys:
        seed_urls (list[str]): News index or section pages.
        selectors (dict): CSS selectors for article_link, headline, byline, body.
        max_articles (int): Max articles to follow per seed URL (default 10).
    """

    source_name = "news"

    def fetch_candidates(self, config: dict) -> list[CandidateLead]:
        """Fetch candidates from news article pages.

        Args:
            config: Source configuration with seed_urls and selectors.

        Returns:
            List of CandidateLead dataclasses.
        """
        seed_urls: list[str] = config.get("seed_urls", [])
        selectors: dict = config.get("selectors", {})
        max_articles: int = config.get("max_articles", 10)

        if not seed_urls:
            logger.warning("no_seed_urls", source=self.source_name)
            return []

        logger.info("scraper_start", source=self.source_name, seed_count=len(seed_urls))
        candidates: list[CandidateLead] = []

        for seed_url in seed_urls:
            try:
                index_soup = self._get(seed_url)
            except ScraperError as exc:
                logger.warning(
                    "seed_url_failed",
                    source=self.source_name,
                    url=seed_url,
                    error=str(exc),
                )
                continue

            article_sel = selectors.get("article_link", "a")
            links = index_soup.select(article_sel)
            article_urls: list[str] = []
            seen: set[str] = set()

            for link in links:
                href = link.get("href", "")
                if not href:
                    continue
                if not href.startswith("http"):
                    href = urljoin(seed_url, href)
                if href not in seen:
                    seen.add(href)
                    article_urls.append(href)
                if len(article_urls) >= max_articles:
                    break

            for article_url in article_urls:
                candidate = self._scrape_article(article_url, selectors)
                if candidate:
                    candidates.append(candidate)

        logger.info(
            "scraper_complete",
            source=self.source_name,
            candidates=len(candidates),
        )
        return candidates

    def _scrape_article(self, url: str, selectors: dict) -> CandidateLead | None:
        """Scrape a news article to extract a person mention.

        Args:
            url: Article URL.
            selectors: CSS selector map.

        Returns:
            CandidateLead or None if no person mention found.
        """
        try:
            soup = self._get(url)
        except ScraperError as exc:
            logger.warning(
                "article_failed",
                source=self.source_name,
                url=url,
                error=str(exc),
            )
            return None

        headline_sel = selectors.get("headline", "h1")
        byline_sel = selectors.get("byline", "")
        body_sel = selectors.get("body", "article,main")

        headline_el = soup.select_one(headline_sel)
        headline = headline_el.get_text(strip=True) if headline_el else ""

        byline_el = soup.select_one(byline_sel) if byline_sel else None
        byline = byline_el.get_text(strip=True) if byline_el else ""

        body_el = soup.select_one(body_sel)
        body_text = body_el.get_text(separator=" ", strip=True) if body_el else ""

        # Heuristic: only yield if headline hints at a person
        if not _PERSON_INDICATORS.search(headline) and not byline:
            logger.debug(
                "no_person_indicator",
                source=self.source_name,
                url=url,
                headline=headline[:80],
            )
            return None

        # Try to extract name from byline or headline
        name = self._extract_name(byline, headline)
        if not name:
            return None

        affiliation = self._extract_affiliation(soup)
        contact_hint = self._extract_contact_hint(soup, url)

        return CandidateLead(
            name=name,
            title=self._extract_title_from_text(headline + " " + body_text[:500]),
            affiliation=affiliation,
            url=url,
            raw_text=(headline + " " + body_text)[:5000],
            source_type="news",
            contact_hint=contact_hint,
        )

    def _extract_name(self, byline: str, headline: str) -> str:
        """Extract a person name from byline or headline text.

        Args:
            byline: Byline text (may contain 'By Name').
            headline: Article headline.

        Returns:
            Best guess at a person name, or empty string.
        """
        # Try byline first: "By Firstname Lastname" or "Firstname Lastname"
        byline_clean = re.sub(r"^[Bb]y\s+", "", byline.strip())
        # Take the first 2–4 capitalized words as a name
        name_match = re.match(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})", byline_clean)
        if name_match:
            return name_match.group(1)

        # Fallback: try headline
        name_match = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})", headline)
        if name_match:
            return name_match.group(1)

        return ""

    def _extract_title_from_text(self, text: str) -> str:
        """Extract a likely job title from article text using indicator words."""
        match = _PERSON_INDICATORS.search(text)
        if match:
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 40)
            return text[start:end].strip()
        return ""

    def _extract_affiliation(self, soup) -> str:  # type: ignore[no-untyped-def]
        """Extract publication name from og:site_name or title."""
        og = soup.find("meta", property="og:site_name")
        if og and og.get("content"):
            return og["content"]
        title = soup.find("title")
        if title:
            parts = re.split(r"[|\-–—]", title.get_text())
            if len(parts) > 1:
                return parts[-1].strip()
        return ""
