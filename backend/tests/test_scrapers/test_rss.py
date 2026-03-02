"""Tests for RssScraper."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.exceptions import ScraperError
from app.scrapers.rss import RssScraper

# ---------------------------------------------------------------------------
# Minimal RSS 2.0 feed fixture (bytes)
# ---------------------------------------------------------------------------

RSS_WITH_PERSON = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Tech Research Weekly</title>
    <link>https://example.com/feed</link>
    <item>
      <title>Dr. Jane Smith on Urban Planning Research</title>
      <link>https://example.com/articles/jane-smith</link>
      <author>Jane Smith</author>
      <description>Professor Jane Smith discusses her work on urban planning at MIT.</description>
    </item>
    <item>
      <title>New Park Opens Downtown</title>
      <link>https://example.com/articles/park</link>
      <description>A new park opened in the city center.</description>
    </item>
  </channel>
</rss>
"""

RSS_NO_PEOPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>General News</title>
    <item>
      <title>Stock Markets Rise Today</title>
      <link>https://example.com/stocks</link>
      <description>Markets closed higher on Wednesday.</description>
    </item>
  </channel>
</rss>
"""

ATOM_WITH_PERSON = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Science Digest</title>
  <entry>
    <title>Researcher Alice Chen Wins Grant for Climate Study</title>
    <link href="https://sciencedigest.org/alice-chen"/>
    <author><name>Alice Chen</name></author>
    <summary>Scientist Alice Chen, a researcher at Stanford, received funding
    for her climate research work. Contact via LinkedIn: https://linkedin.com/in/alicechen</summary>
  </entry>
</feed>
"""

RSS_AUTHOR_ONLY = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Founders Weekly</title>
    <item>
      <title>Founder launches new startup</title>
      <link>https://example.com/founder-story</link>
      <author>Bob Martinez</author>
      <description>Entrepreneur Bob Martinez launched his new venture this week.</description>
    </item>
  </channel>
</rss>
"""


@pytest.fixture
def scraper() -> RssScraper:
    """Return an RssScraper with rate limiting disabled."""
    s = RssScraper()
    s._last_request_time = {}
    return s


# ---------------------------------------------------------------------------
# fetch_candidates — top-level
# ---------------------------------------------------------------------------


def test_empty_seed_urls(scraper: RssScraper) -> None:
    candidates = scraper.fetch_candidates({"seed_urls": []})
    assert candidates == []


def test_missing_seed_urls_key(scraper: RssScraper) -> None:
    candidates = scraper.fetch_candidates({})
    assert candidates == []


def test_fetch_candidates_success(scraper: RssScraper) -> None:
    """RSS feed with a person-indicator entry produces a CandidateLead."""
    with patch.object(scraper, "_get_raw", return_value=RSS_WITH_PERSON):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://example.com/feed.rss"]}
        )

    assert len(candidates) >= 1
    names = [c.name for c in candidates]
    # The person entry should produce at least one candidate
    assert any("Jane Smith" in n or "Smith" in n for n in names)


def test_fetch_candidates_atom_feed(scraper: RssScraper) -> None:
    """Atom feed is parsed correctly."""
    with patch.object(scraper, "_get_raw", return_value=ATOM_WITH_PERSON):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://sciencedigest.org/feed.atom"]}
        )

    assert len(candidates) >= 1
    assert candidates[0].source_type == "rss"


def test_skips_entry_without_person_indicator(scraper: RssScraper) -> None:
    """Feed with no person-indicator entries returns empty list."""
    with patch.object(scraper, "_get_raw", return_value=RSS_NO_PEOPLE):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://example.com/general.rss"]}
        )

    assert candidates == []


def test_http_error_skips_feed(scraper: RssScraper) -> None:
    """ScraperError from _get_raw is caught; other feeds still processed."""
    good_call_count = 0

    def side_effect(url: str) -> bytes:
        nonlocal good_call_count
        if "bad" in url:
            raise ScraperError("HTTP 500")
        good_call_count += 1
        return RSS_WITH_PERSON

    with patch.object(scraper, "_get_raw", side_effect=side_effect):
        candidates = scraper.fetch_candidates(
            {
                "seed_urls": [
                    "https://bad.example.com/feed.rss",
                    "https://good.example.com/feed.rss",
                ]
            }
        )

    assert good_call_count == 1
    assert len(candidates) >= 1


# ---------------------------------------------------------------------------
# Name extraction
# ---------------------------------------------------------------------------


def test_extracts_name_from_author_field(scraper: RssScraper) -> None:
    """Author field takes priority over title for name extraction."""
    with patch.object(scraper, "_get_raw", return_value=RSS_AUTHOR_ONLY):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://example.com/founders.rss"]}
        )

    assert len(candidates) >= 1
    assert "Bob Martinez" in candidates[0].name or "Martinez" in candidates[0].name


def test_extracts_name_from_atom_author(scraper: RssScraper) -> None:
    """Atom <author><name> is parsed as the author field."""
    with patch.object(scraper, "_get_raw", return_value=ATOM_WITH_PERSON):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://sciencedigest.org/feed.atom"]}
        )

    assert len(candidates) == 1
    assert "Alice" in candidates[0].name or "Chen" in candidates[0].name


# ---------------------------------------------------------------------------
# Affiliation from feed title
# ---------------------------------------------------------------------------


def test_affiliation_from_feed_title(scraper: RssScraper) -> None:
    """Feed-level title is used as affiliation."""
    with patch.object(scraper, "_get_raw", return_value=RSS_WITH_PERSON):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://example.com/feed.rss"]}
        )

    assert len(candidates) >= 1
    assert candidates[0].affiliation == "Tech Research Weekly"


def test_affiliation_fallback_to_domain(scraper: RssScraper) -> None:
    """When feed has no title, domain is used as affiliation."""
    rss_no_title = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Dr. Tom Baker on Machine Learning</title>
      <link>https://notitle.example.com/articles/baker</link>
      <author>Tom Baker</author>
      <description>Researcher Tom Baker presented his findings at the conference.</description>
    </item>
  </channel>
</rss>
"""
    with patch.object(scraper, "_get_raw", return_value=rss_no_title):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://notitle.example.com/feed.rss"]}
        )

    assert len(candidates) >= 1
    assert candidates[0].affiliation == "notitle.example.com"


# ---------------------------------------------------------------------------
# Contact hint
# ---------------------------------------------------------------------------


def test_contact_hint_extracted_from_summary(scraper: RssScraper) -> None:
    """LinkedIn URL in summary is extracted as contact hint."""
    with patch.object(scraper, "_get_raw", return_value=ATOM_WITH_PERSON):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://sciencedigest.org/feed.atom"]}
        )

    assert len(candidates) == 1
    assert candidates[0].contact_hint == "https://linkedin.com/in/alicechen"


# ---------------------------------------------------------------------------
# max_entries
# ---------------------------------------------------------------------------


def test_max_entries_respected(scraper: RssScraper) -> None:
    """Only up to max_entries entries are processed per feed."""
    rss_many = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Busy Feed</title>
    <item>
      <title>Dr. Alpha on Research</title>
      <link>https://busy.example.com/1</link>
      <author>Alpha One</author>
      <description>Researcher Alpha One works on deep learning.</description>
    </item>
    <item>
      <title>Prof. Beta Wins Award</title>
      <link>https://busy.example.com/2</link>
      <author>Beta Two</author>
      <description>Professor Beta Two received an award this year.</description>
    </item>
    <item>
      <title>Scientist Gamma Publishes Study</title>
      <link>https://busy.example.com/3</link>
      <author>Gamma Three</author>
      <description>Scientist Gamma Three published a major study on climate.</description>
    </item>
  </channel>
</rss>
"""
    with patch.object(scraper, "_get_raw", return_value=rss_many):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://busy.example.com/feed.rss"], "max_entries": 2}
        )

    # Should only process the first 2 entries even though 3 match
    assert len(candidates) <= 2


# ---------------------------------------------------------------------------
# source_type
# ---------------------------------------------------------------------------


def test_source_type_is_rss(scraper: RssScraper) -> None:
    with patch.object(scraper, "_get_raw", return_value=RSS_WITH_PERSON):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://example.com/feed.rss"]}
        )

    assert all(c.source_type == "rss" for c in candidates)


# ---------------------------------------------------------------------------
# _strip_html helper
# ---------------------------------------------------------------------------


def test_strip_html_removes_tags() -> None:
    result = RssScraper._strip_html("<p>Hello <b>world</b></p>")
    assert "<" not in result
    assert "Hello" in result
    assert "world" in result


def test_strip_html_empty_string() -> None:
    assert RssScraper._strip_html("") == ""


# ---------------------------------------------------------------------------
# _extract_name
# ---------------------------------------------------------------------------


def test_extract_name_prefers_author_field(scraper: RssScraper) -> None:
    name = scraper._extract_name("Jane Doe", "Some Title", "body text here")
    assert name == "Jane Doe"


def test_extract_name_falls_back_to_title(scraper: RssScraper) -> None:
    name = scraper._extract_name("", "Meet John Smith the Researcher", "")
    assert "John Smith" in name


def test_extract_name_falls_back_to_body(scraper: RssScraper) -> None:
    name = scraper._extract_name("", "Latest research", "Mary Johnson is a scientist.")
    assert "Mary Johnson" in name or "Johnson" in name


def test_extract_name_returns_empty_when_no_match(scraper: RssScraper) -> None:
    name = scraper._extract_name("", "stock prices rise", "markets up 2%")
    assert name == ""


# ---------------------------------------------------------------------------
# Multiple feeds
# ---------------------------------------------------------------------------


def test_multiple_feed_urls_aggregated(scraper: RssScraper) -> None:
    """Results from multiple feed URLs are combined."""
    call_count = 0

    def side_effect(url: str) -> bytes:
        nonlocal call_count
        call_count += 1
        return RSS_WITH_PERSON

    with patch.object(scraper, "_get_raw", side_effect=side_effect):
        candidates = scraper.fetch_candidates(
            {
                "seed_urls": [
                    "https://feed1.example.com/feed.rss",
                    "https://feed2.example.com/feed.rss",
                ]
            }
        )

    assert call_count == 2
    # Each feed has 1 person entry, so total should be 2
    assert len(candidates) == 2
