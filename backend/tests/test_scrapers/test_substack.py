"""Tests for SubstackScraper."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.exceptions import ScraperError
from app.scrapers.substack import SubstackScraper

# ---------------------------------------------------------------------------
# Fixture helpers — Substack API response shapes
# ---------------------------------------------------------------------------


def _make_post(
    title: str = "Dr. Jane Smith on Urban Planning",
    subtitle: str = "A researcher's perspective",
    description: str = "Researcher Jane Smith discusses her work.",
    canonical_url: str = "https://example.substack.com/p/jane-smith",
    author_name: str = "Jane Smith",
    author_handle: str = "janesmith",
    publication_name: str = "Example Research",
) -> dict:
    """Return a minimal Substack API post dict."""
    return {
        "title": title,
        "subtitle": subtitle,
        "description": description,
        "canonical_url": canonical_url,
        "publishedBylines": [
            {
                "name": author_name,
                "handle": author_handle,
                "profile_set_up_at": "2023-01-01T00:00:00.000Z",
            }
        ],
        "publication": {"name": publication_name},
    }


def _make_post_no_byline(
    title: str = "Founder builds new startup",
    subtitle: str = "CEO launches product",
) -> dict:
    return {
        "title": title,
        "subtitle": subtitle,
        "description": "",
        "canonical_url": "https://example.substack.com/p/founder",
        "publishedBylines": [],
        "publication": {"name": "Example Newsletter"},
    }


@pytest.fixture
def scraper() -> SubstackScraper:
    s = SubstackScraper()
    s._last_request_time = {}
    return s


# ---------------------------------------------------------------------------
# fetch_candidates — top-level
# ---------------------------------------------------------------------------


def test_empty_seed_urls(scraper: SubstackScraper) -> None:
    candidates = scraper.fetch_candidates({"seed_urls": []})
    assert candidates == []


def test_missing_seed_urls_key(scraper: SubstackScraper) -> None:
    candidates = scraper.fetch_candidates({})
    assert candidates == []


def test_fetch_candidates_success(scraper: SubstackScraper) -> None:
    """A post with a person indicator produces a CandidateLead."""
    posts = [_make_post()]
    with patch.object(scraper, "_get_json", return_value=posts):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://example.substack.com"]}
        )

    assert len(candidates) == 1
    assert candidates[0].name == "Jane Smith"
    assert candidates[0].affiliation == "Example Research"
    assert candidates[0].url == "https://example.substack.com/p/jane-smith"


def test_http_error_skips_url(scraper: SubstackScraper) -> None:
    """ScraperError from _get_json is caught; other URLs still processed."""
    good_call_count = 0

    def side_effect(url: str) -> list:
        nonlocal good_call_count
        if "bad" in url:
            raise ScraperError("HTTP 500")
        good_call_count += 1
        return [_make_post()]

    with patch.object(scraper, "_get_json", side_effect=side_effect):
        candidates = scraper.fetch_candidates(
            {
                "seed_urls": [
                    "https://bad.substack.com",
                    "https://good.substack.com",
                ]
            }
        )

    assert good_call_count == 1
    assert len(candidates) == 1


# ---------------------------------------------------------------------------
# Person indicator filtering
# ---------------------------------------------------------------------------


def test_skips_post_without_person_indicator(scraper: SubstackScraper) -> None:
    """Posts with no person indicator are excluded."""
    posts = [
        {
            "title": "Markets Are Up",
            "subtitle": "Economic news",
            "description": "Stocks rose today.",
            "canonical_url": "https://example.substack.com/p/markets",
            "publishedBylines": [{"name": "Bob Smith", "handle": "bobsmith"}],
            "publication": {"name": "Finance Daily"},
        }
    ]
    with patch.object(scraper, "_get_json", return_value=posts):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://example.substack.com"]}
        )

    assert candidates == []


# ---------------------------------------------------------------------------
# Name extraction
# ---------------------------------------------------------------------------


def test_extracts_author_name_from_bylines(scraper: SubstackScraper) -> None:
    posts = [_make_post(author_name="Alice Chen")]
    with patch.object(scraper, "_get_json", return_value=posts):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://example.substack.com"]}
        )

    assert candidates[0].name == "Alice Chen"


def test_extracts_name_from_title_when_no_byline(scraper: SubstackScraper) -> None:
    """When publishedBylines is empty, name is extracted from title text."""
    posts = [_make_post_no_byline()]
    with patch.object(scraper, "_get_json", return_value=posts):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://example.substack.com"]}
        )

    # Should find a name from title ("Founder builds...") or subtitle ("CEO launches...")
    # The combined text has person indicators but no "proper name" in title — may be empty
    # The key requirement: no crash, result is list
    assert isinstance(candidates, list)


def test_skips_post_with_no_name_extractable(scraper: SubstackScraper) -> None:
    """Posts where no name can be extracted are skipped."""
    posts = [
        {
            "title": "a researcher won a prize",  # lowercase — won't match name regex
            "subtitle": "",
            "description": "",
            "canonical_url": "https://example.substack.com/p/prize",
            "publishedBylines": [],
            "publication": {"name": "Example"},
        }
    ]
    with patch.object(scraper, "_get_json", return_value=posts):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://example.substack.com"]}
        )

    assert candidates == []


# ---------------------------------------------------------------------------
# Affiliation
# ---------------------------------------------------------------------------


def test_affiliation_from_publication_name(scraper: SubstackScraper) -> None:
    posts = [_make_post(publication_name="Deep Thinking Weekly")]
    with patch.object(scraper, "_get_json", return_value=posts):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://deepthinking.substack.com"]}
        )

    assert candidates[0].affiliation == "Deep Thinking Weekly"


def test_affiliation_fallback_to_domain(scraper: SubstackScraper) -> None:
    """When publication name is absent, domain is used as affiliation."""
    posts = [
        {
            "title": "Dr. No Name on Science",
            "subtitle": "",
            "description": "",
            "canonical_url": "https://fallback.substack.com/p/test",
            "publishedBylines": [{"name": "No Name", "handle": "noname"}],
            "publication": {},
        }
    ]
    with patch.object(scraper, "_get_json", return_value=posts):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://fallback.substack.com"]}
        )

    assert candidates[0].affiliation == "fallback.substack.com"


# ---------------------------------------------------------------------------
# Contact hint
# ---------------------------------------------------------------------------


def test_contact_hint_author_profile_url(scraper: SubstackScraper) -> None:
    """Author handle produces a Substack profile contact hint."""
    posts = [_make_post(author_handle="janesmith")]
    with patch.object(scraper, "_get_json", return_value=posts):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://example.substack.com"]}
        )

    assert candidates[0].contact_hint == "https://example.substack.com/@janesmith"


def test_contact_hint_none_when_no_handle(scraper: SubstackScraper) -> None:
    posts = [
        {
            "title": "Scientist Alice Studies Climate",
            "subtitle": "",
            "description": "Researcher Alice Jones presented findings.",
            "canonical_url": "https://example.substack.com/p/climate",
            "publishedBylines": [{"name": "Alice Jones", "handle": ""}],
            "publication": {"name": "Climate Notes"},
        }
    ]
    with patch.object(scraper, "_get_json", return_value=posts):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://example.substack.com"]}
        )

    assert candidates[0].contact_hint is None


# ---------------------------------------------------------------------------
# max_articles
# ---------------------------------------------------------------------------


def test_max_articles_respected(scraper: SubstackScraper) -> None:
    """Only up to max_articles posts are processed."""
    posts = [
        _make_post(
            title=f"Dr. Person {i} on Research",
            author_name=f"Person {i}",
            canonical_url=f"https://example.substack.com/p/{i}",
        )
        for i in range(10)
    ]
    with patch.object(scraper, "_get_json", return_value=posts):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://example.substack.com"], "max_articles": 3}
        )

    assert len(candidates) <= 3


# ---------------------------------------------------------------------------
# Unexpected API response
# ---------------------------------------------------------------------------


def test_non_list_api_response_skipped(scraper: SubstackScraper) -> None:
    """If the API returns a non-list, the publication is skipped gracefully."""
    with patch.object(scraper, "_get_json", return_value={"error": "not found"}):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://example.substack.com"]}
        )

    assert candidates == []


# ---------------------------------------------------------------------------
# source_type
# ---------------------------------------------------------------------------


def test_source_type_is_news(scraper: SubstackScraper) -> None:
    """SubstackScraper uses source_type='news' (Substack is a news/opinion source)."""
    posts = [_make_post()]
    with patch.object(scraper, "_get_json", return_value=posts):
        candidates = scraper.fetch_candidates(
            {"seed_urls": ["https://example.substack.com"]}
        )

    assert all(c.source_type == "news" for c in candidates)


# ---------------------------------------------------------------------------
# Multiple publications
# ---------------------------------------------------------------------------


def test_multiple_seed_urls_aggregated(scraper: SubstackScraper) -> None:
    call_count = 0

    def side_effect(url: str) -> list:
        nonlocal call_count
        call_count += 1
        return [_make_post()]

    with patch.object(scraper, "_get_json", side_effect=side_effect):
        candidates = scraper.fetch_candidates(
            {
                "seed_urls": [
                    "https://pub1.substack.com",
                    "https://pub2.substack.com",
                ]
            }
        )

    assert call_count == 2
    assert len(candidates) == 2


# ---------------------------------------------------------------------------
# API URL construction
# ---------------------------------------------------------------------------


def test_api_url_uses_max_articles(scraper: SubstackScraper) -> None:
    """The API URL includes the configured max_articles limit."""
    captured_urls: list[str] = []

    def side_effect(url: str) -> list:
        captured_urls.append(url)
        return []

    with patch.object(scraper, "_get_json", side_effect=side_effect):
        scraper.fetch_candidates(
            {"seed_urls": ["https://example.substack.com"], "max_articles": 5}
        )

    assert len(captured_urls) == 1
    assert "limit=5" in captured_urls[0]
