from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from app.exceptions import ScraperError
from app.scrapers.base import BaseScraper, CandidateLead


class ConcreteTestScraper(BaseScraper):
    """Minimal concrete implementation for testing BaseScraper."""

    source_name = "test"

    def fetch_candidates(self, config: dict) -> list[CandidateLead]:
        return []


class TestBaseScraper:
    def setup_method(self):
        self.scraper = ConcreteTestScraper()

    def test_domain_extraction(self):
        assert self.scraper._domain("https://example.com/path") == "example.com"
        assert self.scraper._domain("http://sub.example.org/a/b") == "sub.example.org"

    def test_rate_limit_sleeps_when_too_fast(self):
        domain = "example.com"
        self.scraper._last_request_time[domain] = time.monotonic()  # Just now

        with patch("app.scrapers.base.time.sleep") as mock_sleep:
            self.scraper._rate_limit(domain)
            mock_sleep.assert_called_once()
            sleep_time = mock_sleep.call_args[0][0]
            assert sleep_time > 0

    def test_rate_limit_no_sleep_after_enough_time(self):
        domain = "example.com"
        # Set last request time far in the past
        self.scraper._last_request_time[domain] = time.monotonic() - 100.0

        with patch("app.scrapers.base.time.sleep") as mock_sleep:
            self.scraper._rate_limit(domain)
            mock_sleep.assert_not_called()

    def test_rate_limit_no_sleep_on_first_request(self):
        with patch("app.scrapers.base.time.sleep") as mock_sleep:
            self.scraper._rate_limit("new-domain.com")
            mock_sleep.assert_not_called()

    def test_get_raises_scraper_error_on_non_200(self):
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch.object(self.scraper._client, "get", return_value=mock_response):
            with patch.object(self.scraper, "_is_allowed", return_value=True):
                with pytest.raises(ScraperError, match="HTTP 500"):
                    self.scraper._get("https://example.com/page")

    def test_get_raises_on_timeout(self):
        import httpx

        with patch.object(
            self.scraper._client, "get", side_effect=httpx.TimeoutException("timeout")
        ):
            with patch.object(self.scraper, "_is_allowed", return_value=True):
                with pytest.raises(ScraperError, match="Timeout"):
                    self.scraper._get("https://example.com/page")

    def test_get_raises_on_request_error(self):
        import httpx

        with patch.object(
            self.scraper._client, "get", side_effect=httpx.RequestError("connect fail")
        ):
            with patch.object(self.scraper, "_is_allowed", return_value=True):
                with pytest.raises(ScraperError, match="Request error"):
                    self.scraper._get("https://example.com/page")

    def test_get_skips_disallowed_url(self):
        with patch.object(self.scraper, "_is_allowed", return_value=False):
            with pytest.raises(ScraperError, match="robots.txt disallows"):
                self.scraper._get("https://example.com/private")

    def test_get_returns_beautifulsoup_on_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><h1>Hello</h1></body></html>"

        with patch.object(self.scraper._client, "get", return_value=mock_response):
            with patch.object(self.scraper, "_is_allowed", return_value=True):
                with patch.object(self.scraper, "_rate_limit"):
                    soup = self.scraper._get("https://example.com")
                    assert soup.find("h1").get_text() == "Hello"

    def test_is_allowed_returns_true_when_robots_fails(self):
        with patch(
            "urllib.robotparser.RobotFileParser.read", side_effect=Exception("fail")
        ):
            result = self.scraper._is_allowed("https://example.com/page", "example.com")
        assert result is True

    def test_extract_contact_hint_linkedin(self):
        from bs4 import BeautifulSoup

        html = '<html><body><a href="https://linkedin.com/in/jsmith">LinkedIn</a></body></html>'
        soup = BeautifulSoup(html, "lxml")
        hint = self.scraper._extract_contact_hint(soup, "https://example.com")
        assert hint == "https://linkedin.com/in/jsmith"

    def test_extract_contact_hint_mailto(self):
        from bs4 import BeautifulSoup

        html = '<html><body><a href="mailto:jane@example.com">Email</a></body></html>'
        soup = BeautifulSoup(html, "lxml")
        hint = self.scraper._extract_contact_hint(soup, "https://example.com")
        assert hint == "jane@example.com"

    def test_extract_contact_hint_none(self):
        from bs4 import BeautifulSoup

        html = "<html><body><p>No contact info</p></body></html>"
        soup = BeautifulSoup(html, "lxml")
        hint = self.scraper._extract_contact_hint(soup, "https://example.com")
        assert hint is None
