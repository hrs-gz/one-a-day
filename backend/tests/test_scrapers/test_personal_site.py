from __future__ import annotations

from unittest.mock import patch

from bs4 import BeautifulSoup

from app.exceptions import ScraperError
from app.scrapers.personal_site import PersonalSiteScraper

PERSONAL_HTML = """
<html>
<head>
  <title>Jane Smith — Independent Researcher</title>
  <meta property="og:title" content="Jane Smith">
  <meta property="og:site_name" content="janesmith.com">
  <meta name="description" content="Independent researcher in urban planning.">
</head>
<body>
  <h1>Jane Smith</h1>
  <p>I am an independent researcher specializing in urban planning.</p>
  <a href="https://linkedin.com/in/janesmith">LinkedIn</a>
</body>
</html>
"""

BASE_CONFIG = {
    "seed_urls": ["https://janesmith.com/about"],
    "selectors": {},
}


class TestPersonalSiteScraper:
    def setup_method(self):
        self.scraper = PersonalSiteScraper()

    def _make_soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    def test_fetch_candidates_success(self):
        soup = self._make_soup(PERSONAL_HTML)
        with patch.object(self.scraper, "_get", return_value=soup):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)

        assert len(candidates) == 1
        assert candidates[0].source_type == "personal"

    def test_infers_name_from_og_title(self):
        soup = self._make_soup(PERSONAL_HTML)
        with patch.object(self.scraper, "_get", return_value=soup):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)
        assert candidates[0].name == "Jane Smith"

    def test_infers_name_from_h1(self):
        html = (
            "<html><head><title>x</title></head><body><h1>Alice Wang</h1></body></html>"
        )
        soup = self._make_soup(html)
        with patch.object(self.scraper, "_get", return_value=soup):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)
        assert len(candidates) == 1
        assert candidates[0].name == "Alice Wang"

    def test_uses_selector_for_name(self):
        config = {
            "seed_urls": ["https://example.com"],
            "selectors": {"name": "h2.person-name"},
        }
        html = "<html><body><h2 class='person-name'>Bob Jones</h2></body></html>"
        soup = self._make_soup(html)
        with patch.object(self.scraper, "_get", return_value=soup):
            candidates = self.scraper.fetch_candidates(config)
        assert candidates[0].name == "Bob Jones"

    def test_affiliation_from_og_site_name(self):
        soup = self._make_soup(PERSONAL_HTML)
        with patch.object(self.scraper, "_get", return_value=soup):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)
        assert candidates[0].affiliation == "janesmith.com"

    def test_affiliation_override(self):
        config = {**BASE_CONFIG, "affiliation_override": "MIT Press"}
        soup = self._make_soup(PERSONAL_HTML)
        with patch.object(self.scraper, "_get", return_value=soup):
            candidates = self.scraper.fetch_candidates(config)
        assert candidates[0].affiliation == "MIT Press"

    def test_contact_hint_linkedin(self):
        soup = self._make_soup(PERSONAL_HTML)
        with patch.object(self.scraper, "_get", return_value=soup):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)
        assert candidates[0].contact_hint == "https://linkedin.com/in/janesmith"

    def test_skips_if_no_name_inferrable(self):
        html = (
            "<html><head><title>Welcome</title></head>"
            "<body><p>Some page</p></body></html>"
        )
        soup = self._make_soup(html)
        with patch.object(self.scraper, "_get", return_value=soup):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)
        assert candidates == []

    def test_http_error_skips_url(self):
        with patch.object(self.scraper, "_get", side_effect=ScraperError("timeout")):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)
        assert candidates == []

    def test_empty_seed_urls(self):
        candidates = self.scraper.fetch_candidates({"seed_urls": []})
        assert candidates == []

    def test_looks_like_name_true(self):
        assert PersonalSiteScraper._looks_like_name("Jane Smith") is True
        assert PersonalSiteScraper._looks_like_name("Alice Marie Wang") is True

    def test_looks_like_name_false(self):
        assert PersonalSiteScraper._looks_like_name("Welcome to my site") is False
        assert PersonalSiteScraper._looks_like_name("Jane") is False
        assert PersonalSiteScraper._looks_like_name("") is False
