"""Unit tests for the Query Builder agent."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from app.agents import query_builder
from app.models.interest_config import InterestConfig
from app.schemas.agent_contracts import (
    CandidateQueryPack,
    DailyRunPlan,
    DailyRunPlanConstraints,
)


def _make_plan(source_packs=None, leads_per_day=3) -> DailyRunPlan:
    return DailyRunPlan(
        leads_per_day=leads_per_day,
        source_packs=source_packs or ["academic", "professional"],
        constraints=DailyRunPlanConstraints(),
    )


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


class TestQueryBuilderRun:
    def test_valid_llm_response(self):
        payload = {
            "queries": [
                {"q": "urban planning researcher site:edu", "recency_days": 90},
                {"q": "computational biology startup founder"},
            ]
        }
        client = _mock_client(json.dumps(payload))
        plan = _make_plan()
        interests = [_make_interest("urban planning")]

        result = query_builder.run(plan, interests, client=client)

        assert isinstance(result, CandidateQueryPack)
        assert len(result.queries) == 2
        assert result.queries[0].q == "urban planning researcher site:edu"

    def test_passes_plan_context_in_prompt(self):
        payload = {"queries": [{"q": "test query"}]}
        client = _mock_client(json.dumps(payload))
        plan = _make_plan(source_packs=["startup", "local"])
        interests = [_make_interest("machine learning")]

        query_builder.run(plan, interests, client=client)

        _, _, user_prompt = client.complete.call_args[0]
        assert "startup" in user_prompt
        assert "local" in user_prompt
        assert "machine learning" in user_prompt

    def test_fallback_on_invalid_json(self):
        client = _mock_client("not json")
        plan = _make_plan()
        interests = [
            _make_interest("urban planning"),
            _make_interest("machine learning"),
        ]

        result = query_builder.run(plan, interests, client=client)

        assert isinstance(result, CandidateQueryPack)
        assert len(result.queries) >= 1
        # Fallback queries should contain interest keywords
        all_query_text = " ".join(q.q for q in result.queries)
        assert (
            "urban planning" in all_query_text or "machine learning" in all_query_text
        )

    def test_fallback_respects_active_interests_only(self):
        client = _mock_client("bad json")
        plan = _make_plan()
        interests = [
            _make_interest("active keyword", active=True),
            _make_interest("inactive keyword", active=False),
        ]

        result = query_builder.run(plan, interests, client=client)

        all_query_text = " ".join(q.q for q in result.queries)
        assert "active keyword" in all_query_text
        assert "inactive keyword" not in all_query_text

    def test_fallback_caps_at_four_queries(self):
        client = _mock_client("bad json")
        plan = _make_plan()
        interests = [_make_interest(f"topic {i}") for i in range(10)]

        result = query_builder.run(plan, interests, client=client)

        assert len(result.queries) <= 4

    def test_correct_model_used(self):
        client = _mock_client(json.dumps({"queries": [{"q": "test"}]}))
        plan = _make_plan()
        interests = [_make_interest("x")]

        query_builder.run(plan, interests, client=client)

        model_arg = client.complete.call_args[0][0]
        assert model_arg == query_builder.MODEL

    def test_query_with_domain_filters(self):
        payload = {
            "queries": [
                {
                    "q": "faculty profile",
                    "allow_domains": ["edu"],
                    "deny_domains": ["twitter.com"],
                }
            ]
        }
        client = _mock_client(json.dumps(payload))
        plan = _make_plan()
        interests = [_make_interest("x")]

        result = query_builder.run(plan, interests, client=client)

        assert result.queries[0].allow_domains == ["edu"]
        assert result.queries[0].deny_domains == ["twitter.com"]
