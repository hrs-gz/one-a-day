"""Unit tests for the Verifier/Extractor agent."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from app.agents import verifier_extractor


def _mock_gemini(response: str) -> MagicMock:
    client = MagicMock()
    client.complete.return_value = response
    return client


def _valid_bundle_json(name="Dr. Jane Smith") -> str:
    return json.dumps(
        {
            "identity": {"name": name, "role": "Professor", "org": "MIT"},
            "urls": ["https://example.edu/jsmith"],
            "facts": [
                {
                    "fact": "Researches urban resilience",
                    "url": "https://example.edu/jsmith",
                    "excerpt": "Jane Smith's research focuses on urban resilience and climate",
                }
            ],
            "contact_paths": [
                {
                    "type": "email",
                    "url": "mailto:jsmith@mit.edu",
                    "excerpt": "Contact: jsmith@mit.edu",
                }
            ],
        }
    )


def _no_person_json() -> str:
    return json.dumps(
        {
            "identity": {"name": None, "role": None, "org": None},
            "urls": [],
            "facts": [],
            "contact_paths": [],
        }
    )


class TestVerifierExtractorRun:
    @patch("app.agents.verifier_extractor._fetch_page_text")
    def test_valid_bundle_returned(self, mock_fetch):
        mock_fetch.return_value = "Some page content about Dr. Jane Smith"
        client = _mock_gemini(_valid_bundle_json())

        results = verifier_extractor.run(["https://example.edu/jsmith"], client=client)

        assert len(results) == 1
        assert results[0].identity.name == "Dr. Jane Smith"
        assert len(results[0].facts) == 1

    @patch("app.agents.verifier_extractor._fetch_page_text")
    def test_no_person_bundle_discarded(self, mock_fetch):
        mock_fetch.return_value = "Generic page content"
        client = _mock_gemini(_no_person_json())

        results = verifier_extractor.run(["https://example.com/page"], client=client)

        assert results == []

    @patch("app.agents.verifier_extractor._fetch_page_text")
    def test_fetch_failure_skips_url(self, mock_fetch):
        mock_fetch.return_value = None
        client = _mock_gemini(_valid_bundle_json())

        results = verifier_extractor.run(
            ["https://unreachable.example.com"], client=client
        )

        assert results == []
        client.complete.assert_not_called()

    @patch("app.agents.verifier_extractor._fetch_page_text")
    def test_invalid_json_from_llm_skipped(self, mock_fetch):
        mock_fetch.return_value = "Some page content"
        client = _mock_gemini("not valid json")

        results = verifier_extractor.run(["https://example.com"], client=client)

        assert results == []

    @patch("app.agents.verifier_extractor._fetch_page_text")
    def test_evidence_gating_violation_skipped(self, mock_fetch):
        mock_fetch.return_value = "Some page content"
        # Bundle with empty url — should fail evidence gating
        bad_bundle = json.dumps(
            {
                "identity": {"name": "Bob", "role": "Engineer", "org": "Acme"},
                "urls": ["https://example.com"],
                "facts": [
                    {
                        "fact": "Built a bridge",
                        "url": "",
                        "excerpt": "Bob built a bridge",
                    }
                ],
                "contact_paths": [],
            }
        )
        client = _mock_gemini(bad_bundle)

        results = verifier_extractor.run(["https://example.com"], client=client)

        assert results == []

    @patch("app.agents.verifier_extractor._fetch_page_text")
    def test_multiple_urls_processed(self, mock_fetch):
        mock_fetch.return_value = "Page content"
        client = _mock_gemini(_valid_bundle_json())

        urls = ["https://a.example.com", "https://b.example.com"]
        results = verifier_extractor.run(urls, client=client)

        assert len(results) == 2
        assert mock_fetch.call_count == 2

    @patch("app.agents.verifier_extractor._fetch_page_text")
    def test_mixed_success_and_failure(self, mock_fetch):
        mock_fetch.side_effect = [
            "Page content",  # First URL — succeeds
            None,  # Second URL — fetch fails
            "Page content",  # Third URL — succeeds
        ]
        client = _mock_gemini(_valid_bundle_json())

        urls = ["https://a.com", "https://bad.com", "https://c.com"]
        results = verifier_extractor.run(urls, client=client)

        assert len(results) == 2

    @patch("app.agents.verifier_extractor._fetch_page_text")
    def test_correct_model_used(self, mock_fetch):
        mock_fetch.return_value = "Content"
        client = _mock_gemini(_valid_bundle_json())

        verifier_extractor.run(["https://example.com"], client=client)

        model_arg = client.complete.call_args[0][0]
        assert model_arg == verifier_extractor.MODEL

    @patch("app.agents.verifier_extractor._fetch_page_text")
    def test_empty_url_list_returns_empty(self, mock_fetch):
        client = _mock_gemini(_valid_bundle_json())

        results = verifier_extractor.run([], client=client)

        assert results == []
        client.complete.assert_not_called()
