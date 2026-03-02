from __future__ import annotations

import structlog
from bs4 import BeautifulSoup

from app.exceptions import ScraperError
from app.scrapers.base import BaseScraper, CandidateLead

logger = structlog.get_logger(__name__)


class UniversityScraper(BaseScraper):
    """Scraper for university faculty/researcher pages.

    Config keys:
        seed_urls (list[str]): Faculty directory or listing pages.
        selectors (dict): CSS selectors for profile_link, name, title, affiliation.
        pagination (dict, optional): {type: "next_link", selector: str, max_pages: int}
        requires_js (bool): Always False for this scraper.
    """

    source_name = "university"

    def fetch_candidates(self, config: dict) -> list[CandidateLead]:
        """Fetch candidates from university faculty pages.

        Args:
            config: Source configuration with seed_urls and selectors.

        Returns:
            List of CandidateLead dataclasses.
        """
        seed_urls: list[str] = config.get("seed_urls", [])
        selectors: dict = config.get("selectors", {})
        pagination: dict = config.get("pagination", {})

        if not seed_urls:
            logger.warning("no_seed_urls", source=self.source_name)
            return []

        logger.info("scraper_start", source=self.source_name, seed_count=len(seed_urls))
        candidates: list[CandidateLead] = []

        for seed_url in seed_urls:
            try:
                page_candidates = self._scrape_listing(seed_url, selectors, pagination)
                candidates.extend(page_candidates)
            except ScraperError as exc:
                logger.warning(
                    "seed_url_failed",
                    source=self.source_name,
                    url=seed_url,
                    error=str(exc),
                )

        logger.info(
            "scraper_complete",
            source=self.source_name,
            candidates=len(candidates),
        )
        return candidates

    def _scrape_listing(
        self, url: str, selectors: dict, pagination: dict
    ) -> list[CandidateLead]:
        """Scrape a faculty listing page and follow profile links.

        Args:
            url: The listing page URL.
            selectors: CSS selector map.
            pagination: Pagination config.

        Returns:
            Candidates found on this page and its profiles.
        """
        candidates: list[CandidateLead] = []
        max_pages = pagination.get("max_pages", 1) if pagination else 1
        current_url: str | None = url
        pages_scraped = 0

        while current_url and pages_scraped < max_pages:
            try:
                soup = self._get(current_url)
            except ScraperError as exc:
                logger.warning(
                    "listing_page_failed",
                    source=self.source_name,
                    url=current_url,
                    error=str(exc),
                )
                break

            profile_link_sel = selectors.get("profile_link", "a")
            profile_links = soup.select(profile_link_sel)

            for link in profile_links:
                href = link.get("href", "")
                if not href:
                    continue
                if not href.startswith("http"):
                    from urllib.parse import urljoin

                    href = urljoin(current_url, href)
                candidate = self._scrape_profile(href, selectors)
                if candidate:
                    candidates.append(candidate)

            # Pagination
            current_url = None
            if pagination.get("type") == "next_link":
                next_sel = pagination.get("selector", "")
                if next_sel:
                    next_link = soup.select_one(next_sel)
                    if next_link and next_link.get("href"):
                        from urllib.parse import urljoin

                        current_url = urljoin(url, next_link["href"])
            pages_scraped += 1

        return candidates

    def _scrape_profile(self, url: str, selectors: dict) -> CandidateLead | None:
        """Scrape an individual faculty profile page.

        Args:
            url: Profile page URL.
            selectors: CSS selector map.

        Returns:
            CandidateLead or None if extraction fails.
        """
        try:
            soup = self._get(url)
        except ScraperError as exc:
            logger.warning(
                "profile_page_failed",
                source=self.source_name,
                url=url,
                error=str(exc),
            )
            return None

        name = self._extract_text(soup, selectors.get("name", "h1"))
        title = self._extract_text(soup, selectors.get("title", ""))
        affiliation = self._extract_text(soup, selectors.get("affiliation", ""))

        if not name:
            logger.warning("missing_name", source=self.source_name, url=url)
            return None

        raw_text = soup.get_text(separator=" ", strip=True)
        contact_hint = self._extract_contact_hint(soup, url)

        return CandidateLead(
            name=name,
            title=title or "",
            affiliation=affiliation or "",
            url=url,
            raw_text=raw_text[:5000],  # Cap to avoid memory bloat
            source_type="university",
            contact_hint=contact_hint,
        )

    def _extract_text(self, soup: BeautifulSoup, selector: str) -> str:
        """Extract and clean text from a CSS selector.

        Args:
            soup: Parsed page.
            selector: CSS selector string.

        Returns:
            Stripped text or empty string.
        """
        if not selector:
            return ""
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else ""
