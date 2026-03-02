from __future__ import annotations

from urllib.parse import urljoin

import structlog

from app.exceptions import ScraperError
from app.scrapers.base import BaseScraper, CandidateLead

logger = structlog.get_logger(__name__)


class CompanyScraper(BaseScraper):
    """Scraper for company team/about pages.

    Config keys:
        seed_urls (list[str]): Team or about page URLs.
        selectors (dict): CSS selectors for person_card, name, title, affiliation.
        requires_js (bool): Always False for this scraper.
    """

    source_name = "company"

    def fetch_candidates(self, config: dict) -> list[CandidateLead]:
        """Fetch candidates from company team pages.

        Args:
            config: Source configuration with seed_urls and selectors.

        Returns:
            List of CandidateLead dataclasses.
        """
        seed_urls: list[str] = config.get("seed_urls", [])
        selectors: dict = config.get("selectors", {})

        if not seed_urls:
            logger.warning("no_seed_urls", source=self.source_name)
            return []

        logger.info("scraper_start", source=self.source_name, seed_count=len(seed_urls))
        candidates: list[CandidateLead] = []

        for url in seed_urls:
            try:
                soup = self._get(url)
            except ScraperError as exc:
                logger.warning(
                    "seed_url_failed",
                    source=self.source_name,
                    url=url,
                    error=str(exc),
                )
                continue

            card_sel = selectors.get("person_card", "")
            name_sel = selectors.get("name", "h2,h3")
            title_sel = selectors.get("title", "")
            affiliation = selectors.get("affiliation", "")

            if card_sel:
                cards = soup.select(card_sel)
            else:
                cards = [soup]

            for card in cards:
                name_el = card.select_one(name_sel) if name_sel else None
                name = name_el.get_text(strip=True) if name_el else ""
                if not name:
                    continue

                title_el = card.select_one(title_sel) if title_sel else None
                title = title_el.get_text(strip=True) if title_el else ""

                # Try to find a profile link for this card
                link = card.find("a", href=True)
                profile_url = url
                if link:
                    href = link["href"]
                    if not href.startswith("http"):
                        href = urljoin(url, href)
                    profile_url = href

                raw_text = card.get_text(separator=" ", strip=True)
                contact_hint = self._extract_contact_hint(card, url)

                candidates.append(
                    CandidateLead(
                        name=name,
                        title=title,
                        affiliation=affiliation or self._extract_company_name(soup),
                        url=profile_url,
                        raw_text=raw_text[:5000],
                        source_type="company",
                        contact_hint=contact_hint,
                    )
                )

        logger.info(
            "scraper_complete",
            source=self.source_name,
            candidates=len(candidates),
        )
        return candidates

    def _extract_company_name(self, soup) -> str:  # type: ignore[no-untyped-def]
        """Best-effort extraction of company name from page title or og:site_name."""
        og = soup.find("meta", property="og:site_name")
        if og and og.get("content"):
            return og["content"]
        title = soup.find("title")
        if title:
            parts = title.get_text(strip=True).split("|")
            return parts[-1].strip() if len(parts) > 1 else parts[0].strip()
        return ""
