"""Unit tests for the Card Writer agent."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from app.agents import card_writer
from app.models.interest_config import InterestConfig
from app.schemas.agent_contracts import (
    LeadIdentity,
    ScoringCard,
    VerifiedFact,
    VerifiedLeadBundle,
)


def _make_interest(
    keyword: str, weight: float = 1.0, active: bool = True
) -> InterestConfig:
    i = InterestConfig(keyword=keyword, weight=weight, active=active)
    i.id = 1
    return i


def _make_bundle(name="Dr. Jane Smith") -> VerifiedLeadBundle:
    return VerifiedLeadBundle(
        identity=LeadIdentity(name=name, role="Professor", org="MIT"),
        urls=["https://example.edu/jsmith"],
        facts=[
            VerifiedFact(
                fact="Researches urban resilience",
                url="https://example.edu/jsmith",
                excerpt="Jane Smith's research focuses on urban resilience",
            )
        ],
    )


def _mock_client(response: str) -> MagicMock:
    client = MagicMock()
    client.complete.return_value = response
    return client


def _valid_card_json(
    relevance=80, novelty=70, authority=75, reachability=60, timeliness=65, diversity=70
) -> str:
    total = round(
        (relevance + novelty + authority + reachability + timeliness + diversity) / 6
    )
    return json.dumps(
        {
            "lead": {
                "name": "Dr. Jane Smith",
                "role": "Professor",
                "org": "MIT",
                "primary_url": "https://example.edu/jsmith",
                "tags": ["urban planning"],
            },
            "score": {
                "total": total,
                "breakdown": {
                    "relevance": relevance,
                    "novelty": novelty,
                    "authority": authority,
                    "reachability": reachability,
                    "timeliness": timeliness,
                    "diversity": diversity,
                },
            },
            "why_relevant": ["Matches urban planning interest"],
            "evidence": [
                {
                    "excerpt": "Jane Smith's research focuses on urban resilience",
                    "url": "https://example.edu/jsmith",
                }
            ],
            "questions": [],
            "research_tasks": [],
        }
    )


class TestCardWriterRun:
    def test_valid_llm_response(self):
        client = _mock_client(_valid_card_json())
        bundle = _make_bundle()
        interests = [_make_interest("urban planning")]

        result = card_writer.run(bundle, interests, client=client)

        assert isinstance(result, ScoringCard)
        assert result.lead.name == "Dr. Jane Smith"
        assert 0 <= result.score.total <= 100

    def test_score_total_computed_as_mean(self):
        # Provide a raw total that differs from the mean — card_writer should recompute
        bad_total_json = json.dumps(
            {
                "lead": {
                    "name": "Bob",
                    "role": "Engineer",
                    "org": "Corp",
                    "primary_url": "https://corp.example.com",
                },
                "score": {
                    "total": 999,  # Wrong — should be recomputed
                    "breakdown": {
                        "relevance": 60,
                        "novelty": 40,
                        "authority": 50,
                        "reachability": 70,
                        "timeliness": 55,
                        "diversity": 45,
                    },
                },
            }
        )
        client = _mock_client(bad_total_json)
        bundle = _make_bundle("Bob")
        interests = [_make_interest("engineering")]

        result = card_writer.run(bundle, interests, client=client)

        assert result is not None
        expected_total = round((60 + 40 + 50 + 70 + 55 + 45) / 6)
        assert result.score.total == expected_total

    def test_invalid_json_returns_none(self):
        client = _mock_client("not valid json")
        bundle = _make_bundle()
        interests = [_make_interest("x")]

        result = card_writer.run(bundle, interests, client=client)

        assert result is None

    def test_passes_bundle_context_in_prompt(self):
        client = _mock_client(_valid_card_json())
        bundle = _make_bundle("Dr. Alice Wong")
        interests = [_make_interest("urban planning")]

        card_writer.run(bundle, interests, client=client)

        _, _, user_prompt = client.complete.call_args[0]
        assert "Dr. Alice Wong" in user_prompt
        assert "urban planning" in user_prompt
        assert "urban resilience" in user_prompt

    def test_contact_paths_included_in_prompt(self):
        from app.schemas.agent_contracts import ContactPath

        client = _mock_client(_valid_card_json())
        bundle = _make_bundle()
        bundle = VerifiedLeadBundle(
            identity=bundle.identity,
            urls=bundle.urls,
            facts=bundle.facts,
            contact_paths=[
                ContactPath(
                    type="linkedin",
                    url="https://linkedin.com/in/jsmith",
                    excerpt="Connect via LinkedIn",
                )
            ],
        )
        interests = [_make_interest("x")]

        card_writer.run(bundle, interests, client=client)

        _, _, user_prompt = client.complete.call_args[0]
        assert "linkedin" in user_prompt

    def test_correct_model_used(self):
        client = _mock_client(_valid_card_json())
        bundle = _make_bundle()
        interests = [_make_interest("x")]

        card_writer.run(bundle, interests, client=client)

        model_arg = client.complete.call_args[0][0]
        assert model_arg == card_writer.MODEL

    def test_schema_violation_returns_none(self):
        # total=200 violates le=100
        bad_json = json.dumps(
            {
                "lead": {
                    "name": "X",
                    "role": "Y",
                    "org": "Z",
                    "primary_url": "https://example.com",
                },
                "score": {
                    "total": 200,
                    "breakdown": {
                        "relevance": 200,
                        "novelty": 200,
                        "authority": 200,
                        "reachability": 200,
                        "timeliness": 200,
                        "diversity": 200,
                    },
                },
            }
        )
        client = _mock_client(bad_json)
        bundle = _make_bundle()
        interests = [_make_interest("x")]

        # card_writer recomputes total as mean; each dim=200 violates le=100
        # so validation should fail and return None
        result = card_writer.run(bundle, interests, client=client)

        assert result is None
