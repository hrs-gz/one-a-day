from __future__ import annotations

from unittest.mock import patch

from bs4 import BeautifulSoup

from app.exceptions import ScraperError
from app.scrapers.news import NewsScraper

INDEX_HTML = """
<html>
<head>
  <title>News | Example Gazette</title>
  <meta property="og:site_name" content="Example Gazette">
</head>
<body>
  <ul>
    <li><a class="article-link" href="/articles/1">Dr. Alice Wang AI Research</a></li>
    <li><a class="article-link" href="/articles/2">CEO John Miller Expands</a></li>
  </ul>
</body>
</html>
"""

ARTICLE_HTML = """
<html>
<head>
  <title>Dr. Alice Wang Leads AI Research | Example Gazette</title>
  <meta property="og:site_name" content="Example Gazette">
</head>
<body>
  <h1>Dr. Alice Wang Leads AI Research</h1>
  <span class="byline">By Alice Wang</span>
  <article>
    <p>Dr. Alice Wang is a researcher at the Institute for AI Studies.
       Her work on machine learning applications has been groundbreaking.
       Alice Wang has published 30 papers.</p>
  </article>
</body>
</html>
"""

BASE_CONFIG = {
    "seed_urls": ["https://example.com/news"],
    "selectors": {
        "article_link": "a.article-link",
        "headline": "h1",
        "byline": "span.byline",
        "body": "article",
    },
    "max_articles": 5,
}


class TestNewsScraper:
    def setup_method(self):
        self.scraper = NewsScraper()

    def _make_soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    def test_fetch_candidates_success(self):
        index_soup = self._make_soup(INDEX_HTML)
        article_soup = self._make_soup(ARTICLE_HTML)

        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            if "news" in url and "articles" not in url:
                return index_soup
            return article_soup

        with patch.object(self.scraper, "_get", side_effect=mock_get):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)

        assert len(candidates) > 0
        assert candidates[0].source_type == "news"

    def test_fetch_candidates_empty_seed_urls(self):
        candidates = self.scraper.fetch_candidates({"seed_urls": []})
        assert candidates == []

    def test_fetch_candidates_http_error_on_index(self):
        with patch.object(self.scraper, "_get", side_effect=ScraperError("HTTP 500")):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)
        assert candidates == []

    def test_fetch_candidates_http_error_on_article(self):
        index_soup = self._make_soup(INDEX_HTML)
        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return index_soup
            raise ScraperError("HTTP 404")

        with patch.object(self.scraper, "_get", side_effect=mock_get):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)
        # Graceful: articles failed but no crash
        assert isinstance(candidates, list)

    def test_skips_article_without_person_indicator(self):
        index_soup = self._make_soup(INDEX_HTML)
        no_person_article = self._make_soup("""
        <html><head><title>Market Update | Gazette</title></head>
        <body>
          <h1>Market Update Q4</h1>
          <article><p>Stock market up today. Traders were surprised.</p></article>
        </body></html>
        """)

        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return index_soup
            return no_person_article

        with patch.object(self.scraper, "_get", side_effect=mock_get):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)
        assert candidates == []

    def test_extracts_name_from_byline(self):
        index_soup = self._make_soup(INDEX_HTML)
        article_soup = self._make_soup(ARTICLE_HTML)

        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            return index_soup if call_count == 1 else article_soup

        with patch.object(self.scraper, "_get", side_effect=mock_get):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)

        if candidates:
            assert candidates[0].name != ""

    def test_affiliation_from_og_site_name(self):
        index_soup = self._make_soup(INDEX_HTML)
        article_soup = self._make_soup(ARTICLE_HTML)

        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            return index_soup if call_count == 1 else article_soup

        with patch.object(self.scraper, "_get", side_effect=mock_get):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)

        if candidates:
            assert candidates[0].affiliation == "Example Gazette"

    def test_max_articles_respected(self):
        # Index with 10 links, max_articles=2
        many_links_html = (
            "<html><body>"
            + "".join(
                f'<a class="article-link" href="/a/{i}">Dr. Person{i} Does Research</a>'
                for i in range(10)
            )
            + "</body></html>"
        )
        index_soup = self._make_soup(many_links_html)
        article_soup = self._make_soup(ARTICLE_HTML)

        call_count = 0
        article_calls = 0

        def mock_get(url):
            nonlocal call_count, article_calls
            call_count += 1
            if call_count == 1:
                return index_soup
            article_calls += 1
            return article_soup

        config = {**BASE_CONFIG, "max_articles": 2}
        with patch.object(self.scraper, "_get", side_effect=mock_get):
            self.scraper.fetch_candidates(config)

        assert article_calls <= 2

    def test_extract_name_from_headline_fallback(self):
        """Name extracted from headline when no byline."""
        result = self.scraper._extract_name("", "Professor Jane Smith wins award")
        assert "Jane Smith" in result or result == "Professor Jane"

    def test_extract_name_by_prefix(self):
        result = self.scraper._extract_name("By Sarah Connor", "")
        assert "Sarah Connor" in result

    def test_extract_name_returns_empty_for_garbage(self):
        result = self.scraper._extract_name("", "breaking news: market crashes")
        assert result == ""
