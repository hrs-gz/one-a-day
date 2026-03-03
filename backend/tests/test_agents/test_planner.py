"""Unit tests for the Planner agent."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from app.agents import planner
from app.models.interest_config import InterestConfig
from app.schemas.agent_contracts import DailyRunPlan


def _make_interest(
    keyword: str, weight: float = 1.0, active: bool = True
) -> InterestConfig:
    i = InterestConfig(keyword=keyword, weight=weight, active=active)
    i.id = 1
    return i


def _mock_client(response: str) -> MagicMock:
    client = MagicMock()
    client.complete.return_value = response
    return client


class TestPlannerRun:
    def test_valid_llm_response(self):
        payload = {
            "leads_per_day": 3,
            "source_packs": ["academic", "professional"],
            "constraints": {"max_per_org": 1, "min_topic_clusters": 2},
        }
        client = _mock_client(json.dumps(payload))
        interests = [_make_interest("urban planning")]

        result = planner.run(interests, client=client)

        assert isinstance(result, DailyRunPlan)
        assert result.leads_per_day == 3
        assert "academic" in result.source_packs
        client.complete.assert_called_once()

    def test_passes_interests_in_prompt(self):
        payload = {
            "leads_per_day": 2,
            "source_packs": ["startup"],
            "constraints": {"max_per_org": 1, "min_topic_clusters": 2},
        }
        client = _mock_client(json.dumps(payload))
        interests = [
            _make_interest("urban planning", weight=1.0),
            _make_interest("machine learning", weight=0.5),
        ]

        planner.run(interests, client=client)

        _, _, user_prompt = client.complete.call_args[0]
        assert "urban planning" in user_prompt
        assert "machine learning" in user_prompt

    def test_fallback_on_invalid_json(self):
        client = _mock_client("not valid json at all")
        interests = [_make_interest("urban planning")]

        result = planner.run(interests, client=client)

        assert isinstance(result, DailyRunPlan)
        assert result.leads_per_day == 3
        assert len(result.source_packs) > 0

    def test_fallback_on_schema_violation(self):
        # leads_per_day=10 violates ge=1,le=3
        payload = {"leads_per_day": 10, "source_packs": ["x"]}
        client = _mock_client(json.dumps(payload))
        interests = [_make_interest("topic")]

        result = planner.run(interests, client=client)

        assert isinstance(result, DailyRunPlan)
        assert 1 <= result.leads_per_day <= 3

    def test_inactive_interests_excluded_from_prompt(self):
        payload = {
            "leads_per_day": 1,
            "source_packs": ["local"],
            "constraints": {"max_per_org": 1, "min_topic_clusters": 1},
        }
        client = _mock_client(json.dumps(payload))
        interests = [
            _make_interest("active topic", active=True),
            _make_interest("inactive topic", active=False),
        ]

        planner.run(interests, client=client)

        _, _, user_prompt = client.complete.call_args[0]
        assert "active topic" in user_prompt
        assert "inactive topic" not in user_prompt

    def test_correct_model_used(self):
        client = _mock_client(
            json.dumps({"leads_per_day": 2, "source_packs": ["academic"]})
        )
        interests = [_make_interest("x")]

        planner.run(interests, client=client)

        model_arg = client.complete.call_args[0][0]
        assert model_arg == planner.MODEL
