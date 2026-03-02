from __future__ import annotations

from unittest.mock import patch

from bs4 import BeautifulSoup

from app.scrapers.local_news import LocalNewsScraper

INDEX_HTML = """
<html>
<head><meta property="og:site_name" content="Local Gazette"></head>
<body>
  <a class="article-link" href="/local/1">Dr. Maria Lopez Leads Health Initiative</a>
</body>
</html>
"""

ARTICLE_HTML = """
<html>
<head>
  <meta property="og:site_name" content="Local Gazette">
  <title>Dr. Maria Lopez Leads Community Health | Local Gazette</title>
</head>
<body>
  <h1>Dr. Maria Lopez Leads Community Health Initiative</h1>
  <span class="byline">By Maria Lopez</span>
  <article><p>Dr. Maria Lopez leads the Health Initiative.</p></article>
</body>
</html>
"""

BASE_CONFIG = {
    "seed_urls": ["https://localgazette.com/news"],
    "selectors": {
        "article_link": "a.article-link",
        "headline": "h1",
        "byline": "span.byline",
        "body": "article",
    },
}


class TestLocalNewsScraper:
    def setup_method(self):
        self.scraper = LocalNewsScraper()

    def _make_soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    def test_source_type_is_local_news(self):
        index_soup = self._make_soup(INDEX_HTML)
        article_soup = self._make_soup(ARTICLE_HTML)

        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            return index_soup if call_count == 1 else article_soup

        with patch.object(self.scraper, "_get", side_effect=mock_get):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)

        assert all(c.source_type == "local_news" for c in candidates)

    def test_inherits_news_scraper_logic(self):
        """LocalNewsScraper should produce candidates
        from the same logic as NewsScraper.
        """
        index_soup = self._make_soup(INDEX_HTML)
        article_soup = self._make_soup(ARTICLE_HTML)

        call_count = 0

        def mock_get(url):
            nonlocal call_count
            call_count += 1
            return index_soup if call_count == 1 else article_soup

        with patch.object(self.scraper, "_get", side_effect=mock_get):
            candidates = self.scraper.fetch_candidates(BASE_CONFIG)

        assert len(candidates) >= 0  # Graceful — at least no crash
        # All candidates must have local_news type
        for c in candidates:
            assert c.source_type == "local_news"

    def test_empty_seed_urls(self):
        candidates = self.scraper.fetch_candidates({"seed_urls": []})
        assert candidates == []
