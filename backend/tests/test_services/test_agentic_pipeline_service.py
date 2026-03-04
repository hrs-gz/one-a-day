"""Tests for the agentic pipeline service."""

from __future__ import annotations

from unittest.mock import patch

from app.schemas.agent_contracts import (
    CandidateQueryPack,
    ContactPath,
    DailyRunPlan,
    DailyRunPlanConstraints,
    LeadIdentity,
    LeadScore,
    LeadSummary,
    ScoreBreakdown,
    ScoringCard,
    SearchQuery,
    VerifiedFact,
    VerifiedLeadBundle,
)
from app.services import agentic_pipeline_service

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_plan(leads_per_day=3, max_per_org=1) -> DailyRunPlan:
    return DailyRunPlan(
        leads_per_day=leads_per_day,
        source_packs=["academic"],
        constraints=DailyRunPlanConstraints(max_per_org=max_per_org),
    )


def _make_bundle(name: str, org: str = "MIT") -> VerifiedLeadBundle:
    return VerifiedLeadBundle(
        identity=LeadIdentity(name=name, role="Professor", org=org),
        urls=[f"https://example.edu/{name.lower().replace(' ', '')}"],
        facts=[
            VerifiedFact(
                fact=f"{name} researches urban planning",
                url=f"https://example.edu/{name.lower().replace(' ', '')}",
                excerpt=f"{name} is known for urban planning research",
            )
        ],
    )


def _make_card(name: str, org: str = "MIT", total: int = 70) -> ScoringCard:
    breakdown = ScoreBreakdown(
        relevance=total,
        novelty=total,
        authority=total,
        reachability=total,
        timeliness=total,
        diversity=total,
    )
    return ScoringCard(
        lead=LeadSummary(
            name=name,
            role="Professor",
            org=org,
            primary_url=f"https://example.edu/{name.lower().replace(' ', '')}",
        ),
        score=LeadScore(total=total, breakdown=breakdown),
    )


# ---------------------------------------------------------------------------
# _select_top
# ---------------------------------------------------------------------------


class TestSelectTop:
    def test_returns_top_n_by_score(self):
        cards = [
            (_make_card("Alice", total=90), _make_bundle("Alice")),
            (_make_card("Bob", total=50), _make_bundle("Bob")),
            (_make_card("Carol", total=75), _make_bundle("Carol")),
        ]
        result = agentic_pipeline_service._select_top(cards, n=2, max_per_org=3)
        assert len(result) == 2
        assert result[0][0].lead.name == "Alice"
        assert result[1][0].lead.name == "Carol"

    def test_org_cap_applied(self):
        cards = [
            (
                _make_card("Alice", org="MIT", total=90),
                _make_bundle("Alice", org="MIT"),
            ),
            (_make_card("Bob", org="MIT", total=80), _make_bundle("Bob", org="MIT")),
            (
                _make_card("Carol", org="Stanford", total=70),
                _make_bundle("Carol", org="Stanford"),
            ),
        ]
        result = agentic_pipeline_service._select_top(cards, n=3, max_per_org=1)
        assert len(result) == 2
        orgs = [r[0].lead.org for r in result]
        assert orgs.count("MIT") == 1
        assert "Stanford" in orgs

    def test_empty_input(self):
        result = agentic_pipeline_service._select_top([], n=3, max_per_org=1)
        assert result == []

    def test_fewer_than_n_available(self):
        cards = [(_make_card("Alice", total=80), _make_bundle("Alice"))]
        result = agentic_pipeline_service._select_top(cards, n=3, max_per_org=1)
        assert len(result) == 1

    def test_org_cap_two(self):
        cards = [
            (_make_card("A", org="MIT", total=90), _make_bundle("A", org="MIT")),
            (_make_card("B", org="MIT", total=85), _make_bundle("B", org="MIT")),
            (_make_card("C", org="MIT", total=80), _make_bundle("C", org="MIT")),
            (_make_card("D", org="Other", total=70), _make_bundle("D", org="Other")),
        ]
        result = agentic_pipeline_service._select_top(cards, n=4, max_per_org=2)
        assert len(result) == 3
        mit_count = sum(1 for r in result if r[0].lead.org == "MIT")
        assert mit_count == 2


# ---------------------------------------------------------------------------
# _to_candidate
# ---------------------------------------------------------------------------


class TestToCandidate:
    def test_basic_conversion(self):
        card = _make_card("Dr. Jane Smith")
        bundle = _make_bundle("Dr. Jane Smith")

        candidate = agentic_pipeline_service._to_candidate(card, bundle)

        assert candidate.name == "Dr. Jane Smith"
        assert candidate.title == "Professor"
        assert candidate.source_type == "personal"

    def test_linkedin_contact_hint_preferred(self):
        card = _make_card("Alice")
        bundle = VerifiedLeadBundle(
            identity=LeadIdentity(name="Alice", role="Prof", org="MIT"),
            urls=["https://example.edu/alice"],
            facts=[
                VerifiedFact(
                    fact="Researches ML",
                    url="https://example.edu/alice",
                    excerpt="Alice researches machine learning",
                )
            ],
            contact_paths=[
                ContactPath(
                    type="email",
                    url="mailto:alice@mit.edu",
                    excerpt="Email: alice@mit.edu",
                ),
                ContactPath(
                    type="linkedin",
                    url="https://linkedin.com/in/alice",
                    excerpt="LinkedIn: alice",
                ),
            ],
        )

        candidate = agentic_pipeline_service._to_candidate(card, bundle)

        assert candidate.contact_hint == "https://linkedin.com/in/alice"

    def test_fallback_to_first_contact_if_no_linkedin(self):
        card = _make_card("Bob")
        bundle = VerifiedLeadBundle(
            identity=LeadIdentity(name="Bob", role="Dev", org="Corp"),
            urls=["https://corp.example.com/bob"],
            facts=[
                VerifiedFact(
                    fact="Builds things",
                    url="https://corp.example.com/bob",
                    excerpt="Bob builds things at Corp",
                )
            ],
            contact_paths=[
                ContactPath(
                    type="website",
                    url="https://bob.example.com",
                    excerpt="Personal site: bob.example.com",
                )
            ],
        )

        candidate = agentic_pipeline_service._to_candidate(card, bundle)

        assert candidate.contact_hint == "https://bob.example.com"

    def test_no_contact_paths_returns_none(self):
        card = _make_card("Carol")
        bundle = _make_bundle("Carol")

        candidate = agentic_pipeline_service._to_candidate(card, bundle)

        assert candidate.contact_hint is None

    def test_raw_text_contains_fact_content(self):
        card = _make_card("Dave")
        bundle = VerifiedLeadBundle(
            identity=LeadIdentity(name="Dave", role="Researcher", org="Lab"),
            urls=["https://lab.example.com/dave"],
            facts=[
                VerifiedFact(
                    fact="Expert in robotics",
                    url="https://lab.example.com/dave",
                    excerpt="Dave is a leading expert in robotics",
                )
            ],
        )

        candidate = agentic_pipeline_service._to_candidate(card, bundle)

        assert "Expert in robotics" in candidate.raw_text
        assert "Dave is a leading expert in robotics" in candidate.raw_text


# ---------------------------------------------------------------------------
# run_agentic_pipeline — integration tests with fully mocked agents
# ---------------------------------------------------------------------------


class TestRunAgenticPipeline:
    def _setup_mocks(
        self, mock_planner, mock_qb, mock_gatherer, mock_verifier, mock_cw
    ):
        mock_planner.return_value = _make_plan()
        mock_qb.return_value = CandidateQueryPack(
            queries=[SearchQuery(q="urban planning researcher")]
        )
        mock_gatherer.return_value = ["https://example.edu/jsmith"]
        mock_verifier.return_value = [_make_bundle("Dr. Jane Smith")]
        mock_cw.return_value = _make_card("Dr. Jane Smith", total=80)

    @patch("app.services.agentic_pipeline_service.card_writer.run")
    @patch("app.services.agentic_pipeline_service.verifier_extractor.run")
    @patch("app.services.agentic_pipeline_service._gather_urls")
    @patch("app.services.agentic_pipeline_service.query_builder.run")
    @patch("app.services.agentic_pipeline_service.planner.run")
    def test_full_pipeline_creates_leads(
        self,
        mock_planner,
        mock_qb,
        mock_gatherer,
        mock_verifier,
        mock_cw,
        db_session,
        sample_interests,
    ):
        self._setup_mocks(mock_planner, mock_qb, mock_gatherer, mock_verifier, mock_cw)

        leads = agentic_pipeline_service.run_agentic_pipeline(db_session)

        assert len(leads) == 1
        assert leads[0].name == "Dr. Jane Smith"
        assert leads[0].source_type == "personal"

    @patch("app.services.agentic_pipeline_service.card_writer.run")
    @patch("app.services.agentic_pipeline_service.verifier_extractor.run")
    @patch("app.services.agentic_pipeline_service._gather_urls")
    @patch("app.services.agentic_pipeline_service.query_builder.run")
    @patch("app.services.agentic_pipeline_service.planner.run")
    def test_no_interests_returns_empty(
        self, mock_planner, mock_qb, mock_gatherer, mock_verifier, mock_cw, db_session
    ):
        # No interests configured
        leads = agentic_pipeline_service.run_agentic_pipeline(db_session)

        assert leads == []
        mock_planner.assert_not_called()

    @patch("app.services.agentic_pipeline_service.card_writer.run")
    @patch("app.services.agentic_pipeline_service.verifier_extractor.run")
    @patch("app.services.agentic_pipeline_service._gather_urls")
    @patch("app.services.agentic_pipeline_service.query_builder.run")
    @patch("app.services.agentic_pipeline_service.planner.run")
    def test_no_urls_gathered_returns_empty(
        self,
        mock_planner,
        mock_qb,
        mock_gatherer,
        mock_verifier,
        mock_cw,
        db_session,
        sample_interests,
    ):
        mock_planner.return_value = _make_plan()
        mock_qb.return_value = CandidateQueryPack(queries=[SearchQuery(q="test")])
        mock_gatherer.return_value = []  # No URLs found

        leads = agentic_pipeline_service.run_agentic_pipeline(db_session)

        assert leads == []
        mock_verifier.assert_not_called()

    @patch("app.services.agentic_pipeline_service.card_writer.run")
    @patch("app.services.agentic_pipeline_service.verifier_extractor.run")
    @patch("app.services.agentic_pipeline_service._gather_urls")
    @patch("app.services.agentic_pipeline_service.query_builder.run")
    @patch("app.services.agentic_pipeline_service.planner.run")
    def test_no_bundles_returns_empty(
        self,
        mock_planner,
        mock_qb,
        mock_gatherer,
        mock_verifier,
        mock_cw,
        db_session,
        sample_interests,
    ):
        mock_planner.return_value = _make_plan()
        mock_qb.return_value = CandidateQueryPack(queries=[SearchQuery(q="test")])
        mock_gatherer.return_value = ["https://example.com"]
        mock_verifier.return_value = []  # Verifier found nobody

        leads = agentic_pipeline_service.run_agentic_pipeline(db_session)

        assert leads == []
        mock_cw.assert_not_called()

    @patch("app.services.agentic_pipeline_service.card_writer.run")
    @patch("app.services.agentic_pipeline_service.verifier_extractor.run")
    @patch("app.services.agentic_pipeline_service._gather_urls")
    @patch("app.services.agentic_pipeline_service.query_builder.run")
    @patch("app.services.agentic_pipeline_service.planner.run")
    def test_card_writer_failure_returns_empty(
        self,
        mock_planner,
        mock_qb,
        mock_gatherer,
        mock_verifier,
        mock_cw,
        db_session,
        sample_interests,
    ):
        mock_planner.return_value = _make_plan()
        mock_qb.return_value = CandidateQueryPack(queries=[SearchQuery(q="test")])
        mock_gatherer.return_value = ["https://example.com"]
        mock_verifier.return_value = [_make_bundle("Alice")]
        mock_cw.return_value = None  # Card writer failed

        leads = agentic_pipeline_service.run_agentic_pipeline(db_session)

        assert leads == []

    @patch("app.services.agentic_pipeline_service.card_writer.run")
    @patch("app.services.agentic_pipeline_service.verifier_extractor.run")
    @patch("app.services.agentic_pipeline_service._gather_urls")
    @patch("app.services.agentic_pipeline_service.query_builder.run")
    @patch("app.services.agentic_pipeline_service.planner.run")
    def test_diversity_constraint_applied(
        self,
        mock_planner,
        mock_qb,
        mock_gatherer,
        mock_verifier,
        mock_cw,
        db_session,
        sample_interests,
    ):
        # Two candidates from the same org — max_per_org=1 should select only one
        mock_planner.return_value = _make_plan(leads_per_day=3, max_per_org=1)
        mock_qb.return_value = CandidateQueryPack(queries=[SearchQuery(q="test")])
        mock_gatherer.return_value = [
            "https://mit.edu/alice",
            "https://mit.edu/bob",
            "https://stanford.edu/carol",
        ]
        mock_verifier.return_value = [
            _make_bundle("Alice", org="MIT"),
            _make_bundle("Bob", org="MIT"),
            _make_bundle("Carol", org="Stanford"),
        ]
        mock_cw.side_effect = [
            _make_card("Alice", org="MIT", total=90),
            _make_card("Bob", org="MIT", total=85),
            _make_card("Carol", org="Stanford", total=80),
        ]

        leads = agentic_pipeline_service.run_agentic_pipeline(db_session)

        # Alice (90) and Carol (80) should be selected — Bob skipped due to MIT cap
        assert len(leads) == 2
        names = {lead.name for lead in leads}
        assert "Alice" in names
        assert "Carol" in names
        assert "Bob" not in names
