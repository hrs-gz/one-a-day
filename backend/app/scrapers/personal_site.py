from __future__ import annotations

import re

import structlog

from app.exceptions import ScraperError
from app.scrapers.base import BaseScraper, CandidateLead

logger = structlog.get_logger(__name__)


class PersonalSiteScraper(BaseScraper):
    """Scraper for personal websites and blogs.

    Config keys:
        seed_urls (list[str]): Personal site or about-page URLs.
        selectors (dict): CSS selectors for name, title, affiliation (all optional).
        affiliation_override (str, optional): Manually set affiliation if not on page.
    """

    source_name = "personal"

    def fetch_candidates(self, config: dict) -> list[CandidateLead]:
        """Fetch candidates from personal websites.

        Args:
            config: Source configuration with seed_urls.

        Returns:
            List of CandidateLead dataclasses.
        """
        seed_urls: list[str] = config.get("seed_urls", [])
        selectors: dict = config.get("selectors", {})
        affiliation_override: str = config.get("affiliation_override", "")

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

            name_sel = selectors.get("name", "")
            title_sel = selectors.get("title", "")
            affil_sel = selectors.get("affiliation", "")

            name = self._extract_text(soup, name_sel) or self._infer_name(soup)
            if not name:
                logger.warning("could_not_infer_name", source=self.source_name, url=url)
                continue

            title = self._extract_text(soup, title_sel) or self._infer_title(soup)
            affiliation = (
                affiliation_override
                or self._extract_text(soup, affil_sel)
                or self._infer_affiliation(soup)
            )
            contact_hint = self._extract_contact_hint(soup, url)
            raw_text = soup.get_text(separator=" ", strip=True)

            candidates.append(
                CandidateLead(
                    name=name,
                    title=title,
                    affiliation=affiliation,
                    url=url,
                    raw_text=raw_text[:5000],
                    source_type="personal",
                    contact_hint=contact_hint,
                )
            )

        logger.info(
            "scraper_complete",
            source=self.source_name,
            candidates=len(candidates),
        )
        return candidates

    def _extract_text(self, soup, selector: str) -> str:
        """Extract text from a CSS selector."""
        if not selector:
            return ""
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else ""

    def _infer_name(self, soup) -> str:  # type: ignore[no-untyped-def]
        """Infer a person name from og:title, twitter:title, or <title>."""
        for meta_name in ["og:title", "twitter:title"]:
            meta = soup.find("meta", property=meta_name) or soup.find(
                "meta", attrs={"name": meta_name}
            )
            if meta and meta.get("content"):
                text = meta["content"].split("|")[0].strip()
                if self._looks_like_name(text):
                    return text

        h1 = soup.find("h1")
        if h1:
            text = h1.get_text(strip=True)
            if self._looks_like_name(text):
                return text

        return ""

    def _infer_title(self, soup) -> str:  # type: ignore[no-untyped-def]
        """Infer a professional title from meta description or first <p>."""
        meta = soup.find("meta", attrs={"name": "description"}) or soup.find(
            "meta", property="og:description"
        )
        if meta and meta.get("content"):
            return meta["content"][:120]
        p = soup.find("p")
        if p:
            return p.get_text(strip=True)[:120]
        return ""

    def _infer_affiliation(self, soup) -> str:  # type: ignore[no-untyped-def]
        """Infer affiliation from og:site_name or page title."""
        og = soup.find("meta", property="og:site_name")
        if og and og.get("content"):
            return og["content"]
        title = soup.find("title")
        if title:
            parts = re.split(r"[|\-–—]", title.get_text())
            if len(parts) > 1:
                return parts[-1].strip()
        return ""

    @staticmethod
    def _looks_like_name(text: str) -> bool:
        """Heuristic: is this text plausibly a person's name?"""
        words = text.split()
        return (
            2 <= len(words) <= 4
            and all(w[0].isupper() for w in words if w)
            and len(text) < 60
        )
