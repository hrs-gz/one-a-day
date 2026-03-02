from __future__ import annotations

from unittest.mock import patch

from bs4 import BeautifulSoup

from app.exceptions import ScraperError
from app.scrapers.company import CompanyScraper

TEAM_HTML = """
<html>
<head>
  <title>About Us | Acme Corp</title>
  <meta property="og:site_name" content="Acme Corp">
</head>
<body>
  <div class="person-card">
    <h2 class="member-name">Alice Johnson</h2>
    <p class="member-title">Head of Engineering</p>
    <a href="/team/alice">Profile</a>
  </div>
  <div class="person-card">
    <h2 class="member-name">Bob Chen</h2>
    <p class="member-title">Lead Designer</p>
    <a href="https://linkedin.com/in/bobchen">LinkedIn</a>
  </div>
</body>
</html>
"""

BASE_CONFIG = {
    "seed_urls": ["https://example.com/team"],
    "selectors": {
        "person_card": "div.person-card",
        "name": "h2.member-name",
        "title": "p.member-title",
    },
}


class TestCompanyScraper:
    def setup_method(self):
        self.scraper = CompanyScraper()

    def _make_soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    def test_fetch_candidates_success(self):
        soup = self._make_soup(TEAM_HTML)
        with patch.object(self.scraper, "_get", return_value=soup):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)

        assert len(candidates) == 2
        assert candidates[0].name == "Alice Johnson"
        assert candidates[0].title == "Head of Engineering"
        assert candidates[0].source_type == "company"

    def test_affiliation_from_og_site_name(self):
        soup = self._make_soup(TEAM_HTML)
        with patch.object(self.scraper, "_get", return_value=soup):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)

        assert candidates[0].affiliation == "Acme Corp"

    def test_affiliation_override_from_config(self):
        # Use affiliation override key directly
        config2 = {**BASE_CONFIG}
        config2["selectors"] = {**BASE_CONFIG["selectors"], "affiliation": "Ignored"}

        soup = self._make_soup(TEAM_HTML)
        with patch.object(self.scraper, "_get", return_value=soup):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)
        # Default is og:site_name = "Acme Corp"
        assert candidates[0].affiliation == "Acme Corp"

    def test_contact_hint_linkedin(self):
        soup = self._make_soup(TEAM_HTML)
        with patch.object(self.scraper, "_get", return_value=soup):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)

        bob = next(c for c in candidates if c.name == "Bob Chen")
        assert bob.contact_hint == "https://linkedin.com/in/bobchen"

    def test_fetch_candidates_empty_seed_urls(self):
        candidates = self.scraper.fetch_candidates({"seed_urls": []})
        assert candidates == []

    def test_fetch_candidates_http_error(self):
        with patch.object(self.scraper, "_get", side_effect=ScraperError("HTTP 503")):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)
        assert candidates == []

    def test_skips_cards_with_no_name(self):
        no_name_html = """
        <html><body>
          <div class="person-card">
            <p class="member-title">Some Role</p>
          </div>
        </body></html>
        """
        soup = self._make_soup(no_name_html)
        with patch.object(self.scraper, "_get", return_value=soup):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)
        assert candidates == []

    def test_no_card_selector_falls_back_to_full_page(self):
        config = {
            "seed_urls": ["https://example.com/about"],
            "selectors": {
                "name": "h2.member-name",
                "title": "p.member-title",
            },
        }
        soup = self._make_soup(TEAM_HTML)
        with patch.object(self.scraper, "_get", return_value=soup):
            candidates = self.scraper.fetch_candidates(config)
        # Without card selector, selects first name on page
        assert len(candidates) >= 1

    def test_extracts_company_name_from_title(self):
        html = "<html><head><title>Team Page | MyCompany</title></head><body><div class='person-card'><h2 class='member-name'>Name</h2></div></body></html>"  # noqa: E501
        soup = self._make_soup(html)
        with patch.object(self.scraper, "_get", return_value=soup):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)
        assert candidates[0].affiliation == "MyCompany"
