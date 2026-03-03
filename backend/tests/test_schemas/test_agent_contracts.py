"""Tests for agent_contracts.py — Pydantic schema validation and evidence gating."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.agent_contracts import (
    CandidateQueryPack,
    ContactPath,
    DailyRunPlan,
    EvidenceItem,
    LeadIdentity,
    LeadScore,
    LeadSummary,
    ResearchTask,
    ScoreBreakdown,
    ScoredQuestion,
    ScoringCard,
    SearchQuery,
    VerifiedFact,
    VerifiedLeadBundle,
)

# ---------------------------------------------------------------------------
# DailyRunPlan
# ---------------------------------------------------------------------------


class TestDailyRunPlan:
    def test_valid_plan(self):
        plan = DailyRunPlan(leads_per_day=3, source_packs=["academic", "professional"])
        assert plan.leads_per_day == 3
        assert plan.source_packs == ["academic", "professional"]
        assert plan.constraints.max_per_org == 1

    def test_default_constraints(self):
        plan = DailyRunPlan(leads_per_day=2, source_packs=["startup"])
        assert plan.constraints.max_per_org == 1
        assert plan.constraints.min_topic_clusters == 2

    def test_leads_per_day_bounds(self):
        with pytest.raises(ValidationError):
            DailyRunPlan(leads_per_day=0, source_packs=["x"])
        with pytest.raises(ValidationError):
            DailyRunPlan(leads_per_day=4, source_packs=["x"])

    def test_model_validate_from_dict(self):
        data = {
            "leads_per_day": 2,
            "source_packs": ["local"],
            "constraints": {"max_per_org": 2, "min_topic_clusters": 1},
        }
        plan = DailyRunPlan.model_validate(data)
        assert plan.constraints.max_per_org == 2


# ---------------------------------------------------------------------------
# CandidateQueryPack
# ---------------------------------------------------------------------------


class TestCandidateQueryPack:
    def test_basic_query_pack(self):
        pack = CandidateQueryPack(
            queries=[
                SearchQuery(q="urban planning researcher 2024"),
                SearchQuery(q="computational biology startup", recency_days=90),
            ]
        )
        assert len(pack.queries) == 2
        assert pack.queries[0].q == "urban planning researcher 2024"
        assert pack.queries[0].recency_days is None

    def test_query_with_domain_filters(self):
        q = SearchQuery(
            q="faculty profile",
            allow_domains=["edu", "ac.uk"],
            deny_domains=["twitter.com"],
        )
        assert q.allow_domains == ["edu", "ac.uk"]
        assert q.deny_domains == ["twitter.com"]

    def test_empty_queries_allowed(self):
        pack = CandidateQueryPack(queries=[])
        assert pack.queries == []


# ---------------------------------------------------------------------------
# VerifiedLeadBundle — evidence gating
# ---------------------------------------------------------------------------


def _make_bundle(**kwargs):
    defaults = {
        "identity": LeadIdentity(name="Dr. Jane Smith", role="Professor", org="MIT"),
        "urls": ["https://example.edu/jsmith"],
        "facts": [
            VerifiedFact(
                fact="Researches urban resilience",
                url="https://example.edu/jsmith",
                excerpt="Jane Smith's research focuses on urban resilience",
            )
        ],
        "contact_paths": [],
    }
    defaults.update(kwargs)
    return VerifiedLeadBundle.model_validate(defaults)


class TestVerifiedLeadBundle:
    def test_valid_bundle(self):
        bundle = _make_bundle()
        assert bundle.identity.name == "Dr. Jane Smith"
        assert len(bundle.facts) == 1

    def test_evidence_gating_missing_url(self):
        with pytest.raises(ValidationError, match="Evidence gating"):
            VerifiedLeadBundle(
                identity=LeadIdentity(name="Bob"),
                urls=["https://example.com"],
                facts=[VerifiedFact(fact="Some fact", url="", excerpt="Some quote")],
            )

    def test_evidence_gating_missing_excerpt(self):
        with pytest.raises(ValidationError, match="Evidence gating"):
            VerifiedLeadBundle(
                identity=LeadIdentity(name="Bob"),
                urls=["https://example.com"],
                facts=[
                    VerifiedFact(
                        fact="Some fact",
                        url="https://example.com",
                        excerpt="",
                    )
                ],
            )

    def test_evidence_gating_whitespace_url(self):
        with pytest.raises(ValidationError, match="Evidence gating"):
            VerifiedLeadBundle(
                identity=LeadIdentity(name="Bob"),
                urls=["https://example.com"],
                facts=[
                    VerifiedFact(
                        fact="Some fact",
                        url="   ",
                        excerpt="A real quote",
                    )
                ],
            )

    def test_empty_facts_allowed(self):
        bundle = _make_bundle(facts=[])
        assert bundle.facts == []

    def test_multiple_facts_all_valid(self):
        bundle = _make_bundle(
            facts=[
                VerifiedFact(
                    fact=f"Fact {i}",
                    url="https://example.edu/page",
                    excerpt=f"Excerpt {i} from page",
                )
                for i in range(5)
            ]
        )
        assert len(bundle.facts) == 5

    def test_null_identity_fields_allowed(self):
        bundle = VerifiedLeadBundle(
            identity=LeadIdentity(),
            urls=[],
            facts=[],
        )
        assert bundle.identity.name is None

    def test_contact_paths_default_empty(self):
        bundle = _make_bundle()
        assert bundle.contact_paths == []

    def test_contact_paths_populated(self):
        bundle = _make_bundle(
            contact_paths=[
                ContactPath(
                    type="linkedin",
                    url="https://linkedin.com/in/jsmith",
                    excerpt="Connect on LinkedIn",
                )
            ]
        )
        assert bundle.contact_paths[0].type == "linkedin"


# ---------------------------------------------------------------------------
# ScoringCard
# ---------------------------------------------------------------------------


def _make_score_breakdown(**kwargs):
    defaults = dict(
        relevance=80,
        novelty=70,
        authority=75,
        reachability=60,
        timeliness=65,
        diversity=70,
    )
    defaults.update(kwargs)
    return ScoreBreakdown(**defaults)


def _make_scoring_card(**kwargs):
    defaults = {
        "lead": LeadSummary(
            name="Dr. Jane Smith",
            role="Professor",
            org="MIT",
            primary_url="https://example.edu/jsmith",
        ),
        "score": LeadScore(
            total=70,
            breakdown=_make_score_breakdown(),
        ),
    }
    defaults.update(kwargs)
    return ScoringCard.model_validate(defaults)


class TestScoringCard:
    def test_valid_card(self):
        card = _make_scoring_card()
        assert card.lead.name == "Dr. Jane Smith"
        assert card.score.total == 70

    def test_score_bounds(self):
        with pytest.raises(ValidationError):
            LeadScore(
                total=101,
                breakdown=_make_score_breakdown(),
            )
        with pytest.raises(ValidationError):
            LeadScore(
                total=-1,
                breakdown=_make_score_breakdown(),
            )

    def test_breakdown_bounds(self):
        with pytest.raises(ValidationError):
            _make_score_breakdown(relevance=101)
        with pytest.raises(ValidationError):
            _make_score_breakdown(novelty=-1)

    def test_optional_fields_default_empty(self):
        card = _make_scoring_card()
        assert card.why_relevant == []
        assert card.evidence == []
        assert card.questions == []
        assert card.research_tasks == []

    def test_full_card(self):
        card = ScoringCard(
            lead=LeadSummary(
                name="Bob",
                role="Researcher",
                org="Stanford",
                primary_url="https://stanford.edu/bob",
                tags=["ML", "robotics"],
            ),
            score=LeadScore(
                total=75,
                breakdown=_make_score_breakdown(),
            ),
            why_relevant=["Matches ML interest"],
            evidence=[
                EvidenceItem(
                    excerpt="Bob leads robotics research",
                    url="https://stanford.edu/bob",
                )
            ],
            questions=[
                ScoredQuestion(
                    q="What is his latest project?", why="To understand scope"
                )
            ],
            research_tasks=[
                ResearchTask(
                    task="Check Google Scholar", expected_find="Recent publications"
                )
            ],
        )
        assert card.lead.tags == ["ML", "robotics"]
        assert len(card.evidence) == 1
        assert len(card.questions) == 1
        assert len(card.research_tasks) == 1
