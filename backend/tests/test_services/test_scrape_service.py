from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.exceptions import ScraperError
from app.models.scraper_source import ScraperSource
from app.scrapers.base import CandidateLead
from app.services.scrape_service import load_scraper, run_all_scrapers


class TestLoadScraper:
    def test_loads_valid_scraper_class(self):
        scraper = load_scraper("app.scrapers.university.UniversityScraper")
        from app.scrapers.university import UniversityScraper

        assert isinstance(scraper, UniversityScraper)

    def test_raises_for_invalid_module(self):
        with pytest.raises(ScraperError, match="Cannot load scraper"):
            load_scraper("nonexistent.module.SomeClass")

    def test_raises_for_invalid_class(self):
        with pytest.raises(ScraperError, match="Cannot load scraper"):
            load_scraper("app.scrapers.university.NoSuchClass")

    def test_raises_for_malformed_path(self):
        with pytest.raises(ScraperError, match="Cannot load scraper"):
            load_scraper("nodotsatall")


class TestRunAllScrapers:
    def test_returns_empty_when_no_sources(self, db_session):
        results = run_all_scrapers(db_session)
        assert results == []

    def test_runs_enabled_sources(self, db_session, sample_scraper_source):
        fake_candidate = CandidateLead(
            name="Test Person",
            title="Researcher",
            affiliation="Uni",
            url="https://example.com",
            raw_text="test content",
            source_type="university",
        )
        with patch("app.services.scrape_service.load_scraper") as mock_load:
            mock_scraper = MagicMock()
            mock_scraper.fetch_candidates.return_value = [fake_candidate]
            mock_load.return_value = mock_scraper

            results = run_all_scrapers(db_session)

        assert len(results) == 1
        assert results[0].name == "Test Person"

    def test_skips_disabled_sources(self, db_session, sample_scraper_source):
        sample_scraper_source.enabled = False
        db_session.commit()

        results = run_all_scrapers(db_session)
        assert results == []

    def test_continues_on_scraper_error(self, db_session, sample_scraper_source):
        # Add a second source
        second_source = ScraperSource(
            name="Second Source",
            scraper_class="app.scrapers.company.CompanyScraper",
            config=json.dumps({"seed_urls": ["https://example.com/team"]}),
            enabled=True,
        )
        db_session.add(second_source)
        db_session.commit()

        fake_candidate = CandidateLead(
            name="Good Person",
            title="Engineer",
            affiliation="Co",
            url="https://example.com",
            raw_text="content",
            source_type="company",
        )

        call_count = 0

        def side_effect_load(class_path):
            nonlocal call_count
            call_count += 1
            mock = MagicMock()
            if call_count == 1:
                mock.fetch_candidates.side_effect = ScraperError("boom")
            else:
                mock.fetch_candidates.return_value = [fake_candidate]
            return mock

        with patch(
            "app.services.scrape_service.load_scraper", side_effect=side_effect_load
        ):
            results = run_all_scrapers(db_session)

        # Should still get candidates from the second source
        assert len(results) == 1

    def test_updates_source_status_on_success(self, db_session, sample_scraper_source):
        with patch("app.services.scrape_service.load_scraper") as mock_load:
            mock_scraper = MagicMock()
            mock_scraper.fetch_candidates.return_value = []
            mock_load.return_value = mock_scraper

            run_all_scrapers(db_session)

        db_session.refresh(sample_scraper_source)
        assert sample_scraper_source.last_run_status == "success"
        assert sample_scraper_source.last_run_at is not None

    def test_updates_source_status_on_error(self, db_session, sample_scraper_source):
        with patch("app.services.scrape_service.load_scraper") as mock_load:
            mock_scraper = MagicMock()
            mock_scraper.fetch_candidates.side_effect = ScraperError("fail")
            mock_load.return_value = mock_scraper

            run_all_scrapers(db_session)

        db_session.refresh(sample_scraper_source)
        assert sample_scraper_source.last_run_status == "error"
