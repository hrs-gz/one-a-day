from __future__ import annotations

import time
import urllib.robotparser
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

import httpx
import structlog
from bs4 import BeautifulSoup

from app.config import settings
from app.exceptions import ScraperError

logger = structlog.get_logger(__name__)

SourceType = Literal["university", "company", "news", "personal", "local_news", "rss"]


@dataclass
class CandidateLead:
    """A raw candidate lead returned by a scraper before scoring and selection."""

    name: str
    title: str
    affiliation: str
    url: str
    raw_text: str
    source_type: SourceType
    contact_hint: str | None = None


class BaseScraper(ABC):
    """Abstract base class for all scrapers.

    Subclasses must implement fetch_candidates(). All HTTP calls must go through
    self._get() to ensure rate limiting and robots.txt compliance.
    """

    source_name: str = "base"

    def __init__(self) -> None:
        self._last_request_time: dict[str, float] = {}
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
        self._client = httpx.Client(
            headers={"User-Agent": settings.scraper_user_agent},
            follow_redirects=True,
            timeout=15.0,
        )

    def __del__(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass

    @abstractmethod
    def fetch_candidates(self, config: dict) -> list[CandidateLead]:
        """Fetch and return raw candidates from this source.

        Args:
            config: Source-specific config dict from ScraperSource.config (parsed JSON).

        Returns:
            List of CandidateLead dataclasses. Return [] on total failure.
        """
        ...

    def _get(self, url: str) -> BeautifulSoup:
        """Rate-limited, robots.txt-respecting HTTP GET.

        Args:
            url: The URL to fetch.

        Returns:
            Parsed BeautifulSoup object.

        Raises:
            ScraperError: On non-200 response, timeout, or connection error.
        """
        domain = self._domain(url)

        if not self._is_allowed(url, domain):
            logger.debug("robots_disallowed", url=url, source=self.source_name)
            raise ScraperError(f"robots.txt disallows {url}")

        self._rate_limit(domain)

        logger.debug("fetching", url=url, source=self.source_name)
        try:
            response = self._client.get(url)
        except httpx.TimeoutException as exc:
            raise ScraperError(f"Timeout fetching {url}") from exc
        except httpx.RequestError as exc:
            raise ScraperError(f"Request error fetching {url}: {exc}") from exc

        if response.status_code != 200:
            raise ScraperError(f"HTTP {response.status_code} fetching {url}")

        self._last_request_time[domain] = time.monotonic()
        return BeautifulSoup(response.text, "lxml")

    def _get_raw(self, url: str) -> bytes:
        """Rate-limited, robots.txt-respecting HTTP GET returning raw bytes.

        Identical to _get() but returns response.content instead of BeautifulSoup.
        Useful for binary content (e.g., RSS/Atom XML passed to feedparser).

        Args:
            url: The URL to fetch.

        Returns:
            Raw response bytes.

        Raises:
            ScraperError: On non-200 response, timeout, or connection error.
        """
        domain = self._domain(url)

        if not self._is_allowed(url, domain):
            logger.debug("robots_disallowed", url=url, source=self.source_name)
            raise ScraperError(f"robots.txt disallows {url}")

        self._rate_limit(domain)

        logger.debug("fetching_raw", url=url, source=self.source_name)
        try:
            response = self._client.get(url)
        except httpx.TimeoutException as exc:
            raise ScraperError(f"Timeout fetching {url}") from exc
        except httpx.RequestError as exc:
            raise ScraperError(f"Request error fetching {url}: {exc}") from exc

        if response.status_code != 200:
            raise ScraperError(f"HTTP {response.status_code} fetching {url}")

        self._last_request_time[domain] = time.monotonic()
        return response.content

    def _get_json(self, url: str) -> dict:
        """Rate-limited, robots.txt-respecting HTTP GET returning parsed JSON.

        Args:
            url: The URL to fetch.

        Returns:
            Parsed JSON as a dict.

        Raises:
            ScraperError: On non-200 response, timeout, connection error,
                or invalid JSON.
        """
        domain = self._domain(url)

        if not self._is_allowed(url, domain):
            logger.debug("robots_disallowed", url=url, source=self.source_name)
            raise ScraperError(f"robots.txt disallows {url}")

        self._rate_limit(domain)

        logger.debug("fetching_json", url=url, source=self.source_name)
        try:
            response = self._client.get(url)
        except httpx.TimeoutException as exc:
            raise ScraperError(f"Timeout fetching {url}") from exc
        except httpx.RequestError as exc:
            raise ScraperError(f"Request error fetching {url}: {exc}") from exc

        if response.status_code != 200:
            raise ScraperError(f"HTTP {response.status_code} fetching {url}")

        self._last_request_time[domain] = time.monotonic()
        try:
            return response.json()
        except Exception as exc:
            raise ScraperError(f"Invalid JSON from {url}: {exc}") from exc

    def _domain(self, url: str) -> str:
        """Extract the netloc (domain) from a URL."""
        return urlparse(url).netloc

    def _rate_limit(self, domain: str) -> None:
        """Sleep if needed to respect the configured rate limit per domain."""
        last = self._last_request_time.get(domain)
        if last is not None:
            elapsed = time.monotonic() - last
            wait = settings.scrape_rate_limit_seconds - elapsed
            if wait > 0:
                time.sleep(wait)

    def _is_allowed(self, url: str, domain: str) -> bool:
        """Check robots.txt for the given URL.

        Returns True if allowed or if robots.txt cannot be fetched.
        """
        if domain not in self._robots_cache:
            robots_url = f"{urlparse(url).scheme}://{domain}/robots.txt"
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(robots_url)
            try:
                rp.read()
            except Exception:
                # If we can't fetch robots.txt, allow by default
                logger.debug(
                    "robots_fetch_failed",
                    robots_url=robots_url,
                    source=self.source_name,
                )
                self._robots_cache[domain] = None  # type: ignore[assignment]
                return True
            self._robots_cache[domain] = rp

        rp = self._robots_cache[domain]
        if rp is None:
            return True
        return rp.can_fetch(settings.scraper_user_agent, url)

    @staticmethod
    def _extract_contact_hint(soup: BeautifulSoup, base_url: str) -> str | None:
        """Extract a contact hint (LinkedIn URL or mailto) from a BeautifulSoup object.

        Args:
            soup: Parsed page HTML.
            base_url: Source URL for context.

        Returns:
            A LinkedIn URL, email address, or None.
        """
        for a in soup.find_all("a", href=True):
            href: str = a["href"]
            if "linkedin.com/in/" in href:
                return href
            if href.startswith("mailto:"):
                return href[len("mailto:") :]
        return None
