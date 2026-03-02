from __future__ import annotations

from unittest.mock import patch

from bs4 import BeautifulSoup

from app.exceptions import ScraperError
from app.scrapers.university import UniversityScraper

LISTING_HTML = """
<html><body>
  <a class="faculty-link" href="/faculty/jsmith">Dr. Jane Smith</a>
  <a class="faculty-link" href="/faculty/bjones">Prof. Bob Jones</a>
</body></html>
"""

PROFILE_HTML = """
<html><body>
  <h1 class="name">Dr. Jane Smith</h1>
  <span class="title">Associate Professor of Urban Planning</span>
  <span class="dept">Department of Urban Studies</span>
  <p>Dr. Jane Smith researches urban planning and city design.</p>
  <a href="https://linkedin.com/in/jsmith">LinkedIn</a>
</body></html>
"""

BASE_CONFIG = {
    "seed_urls": ["https://example.edu/faculty"],
    "selectors": {
        "profile_link": "a.faculty-link",
        "name": "h1.name",
        "title": "span.title",
        "affiliation": "span.dept",
    },
}


class TestUniversityScraper:
    def setup_method(self):
        self.scraper = UniversityScraper()

    def _make_soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    def test_fetch_candidates_success(self):
        listing_soup = self._make_soup(LISTING_HTML)
        profile_soup = self._make_soup(PROFILE_HTML)

        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            if "faculty" in url and "jsmith" not in url and "bjones" not in url:
                return listing_soup
            return profile_soup

        with patch.object(self.scraper, "_get", side_effect=mock_get):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)

        assert len(candidates) == 2
        assert candidates[0].source_type == "university"
        assert candidates[0].name == "Dr. Jane Smith"

    def test_fetch_candidates_empty_seed_urls(self):
        candidates = self.scraper.fetch_candidates({"seed_urls": [], "selectors": {}})
        assert candidates == []

    def test_fetch_candidates_no_seed_urls_key(self):
        candidates = self.scraper.fetch_candidates({})
        assert candidates == []

    def test_fetch_candidates_http_error_on_seed(self):
        with patch.object(self.scraper, "_get", side_effect=ScraperError("HTTP 500")):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)
        assert candidates == []

    def test_fetch_candidates_http_error_on_profile(self):
        listing_soup = self._make_soup(LISTING_HTML)
        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return listing_soup
            raise ScraperError("HTTP 404")

        with patch.object(self.scraper, "_get", side_effect=mock_get):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)

        # Both profiles failed, so no candidates
        assert candidates == []

    def test_fetch_candidates_missing_name_skipped(self):
        listing_soup = self._make_soup(LISTING_HTML)
        # Profile with no h1.name
        profile_no_name = self._make_soup(
            "<html><body><p>No name here</p></body></html>"
        )

        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return listing_soup
            return profile_no_name

        with patch.object(self.scraper, "_get", side_effect=mock_get):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)

        assert candidates == []

    def test_candidate_has_contact_hint(self):
        listing_soup = self._make_soup(LISTING_HTML)
        profile_soup = self._make_soup(PROFILE_HTML)

        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return listing_soup
            return profile_soup

        with patch.object(self.scraper, "_get", side_effect=mock_get):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)

        assert any(c.contact_hint for c in candidates)

    def test_raw_text_capped(self):
        long_text = "word " * 5000
        listing_soup = self._make_soup(LISTING_HTML)
        profile_soup = self._make_soup(
            f"<html><body><h1 class='name'>Dr. Long</h1><p>{long_text}</p></body></html>"  # noqa: E501
        )

        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return listing_soup
            return profile_soup

        with patch.object(self.scraper, "_get", side_effect=mock_get):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)

        for c in candidates:
            assert len(c.raw_text) <= 5001  # Allow slight overage from get_text
