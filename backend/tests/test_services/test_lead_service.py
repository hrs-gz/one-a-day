from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.exceptions import LeadExistsError, SourceNotFoundError
from app.models.interest_config import InterestConfig
from app.models.lead import Lead
from app.scrapers.base import CandidateLead
from app.services.lead_service import (
    create_lead_from_candidate,
    generate_summary,
    get_active_interests,
    get_lead_by_id,
    get_today_lead,
    list_leads,
    score_candidate,
    select_winner,
)

# ---------------------------------------------------------------------------
# score_candidate
# ---------------------------------------------------------------------------


def make_interest(
    keyword: str, weight: float = 1.0, active: bool = True
) -> InterestConfig:
    i = InterestConfig()
    i.id = 1
    i.keyword = keyword
    i.weight = weight
    i.active = active
    i.created_at = datetime.utcnow()
    return i


def make_candidate(raw_text: str) -> CandidateLead:
    return CandidateLead(
        name="Test Person",
        title="Researcher",
        affiliation="Test Uni",
        url="https://example.com",
        raw_text=raw_text,
        source_type="university",
    )


class TestScoreCandidate:
    def test_exact_keyword_match_returns_100(self):
        candidate = make_candidate("urban planning research at city hall")
        interests = [make_interest("urban planning", weight=1.0)]
        score = score_candidate(candidate, interests)
        assert score == 100.0

    def test_partial_match_returns_between_0_and_100(self):
        candidate = make_candidate("city planning department")
        interests = [make_interest("urban planning", weight=1.0)]
        score = score_candidate(candidate, interests)
        assert 0 < score < 100

    def test_no_match_returns_0(self):
        candidate = make_candidate("marine biology lab deep ocean")
        interests = [make_interest("urban planning", weight=1.0)]
        score = score_candidate(candidate, interests)
        assert score == 0.0

    def test_weighted_score(self):
        candidate = make_candidate("urban planning")
        interests = [make_interest("urban planning", weight=0.5)]
        score = score_candidate(candidate, interests)
        assert score == 50.0

    def test_inactive_interest_ignored(self):
        candidate = make_candidate("urban planning research")
        interests = [make_interest("urban planning", weight=1.0, active=False)]
        score = score_candidate(candidate, interests)
        assert score == 0.0

    def test_multiple_interests_weighted_average(self):
        candidate = make_candidate("urban planning and machine learning")
        interests = [
            make_interest("urban planning", weight=1.0),
            make_interest("machine learning", weight=1.0),
        ]
        score = score_candidate(candidate, interests)
        assert score == 100.0

    def test_empty_interests_returns_0(self):
        candidate = make_candidate("urban planning")
        score = score_candidate(candidate, [])
        assert score == 0.0

    def test_case_insensitive_match(self):
        candidate = make_candidate("Urban Planning Department")
        interests = [make_interest("urban planning", weight=1.0)]
        score = score_candidate(candidate, interests)
        assert score == 100.0

    def test_score_capped_at_100(self):
        candidate = make_candidate("urban planning urban planning urban planning")
        interests = [
            make_interest("urban planning", weight=1.0),
            make_interest("urban planning", weight=1.0),
        ]
        score = score_candidate(candidate, interests)
        assert score <= 100.0


# ---------------------------------------------------------------------------
# generate_summary
# ---------------------------------------------------------------------------


class TestGenerateSummary:
    def test_extracts_sentences_with_name(self):
        candidate = CandidateLead(
            name="Jane Smith",
            title="Professor",
            affiliation="MIT",
            url="https://example.com",
            raw_text="MIT has many researchers. Jane Smith leads the urban planning lab. She has published 40 papers.",  # noqa: E501
            source_type="university",
        )
        summary = generate_summary(candidate)
        assert "Jane Smith" in summary

    def test_fallback_to_first_sentences(self):
        candidate = CandidateLead(
            name="John Doe",
            title="Professor",
            affiliation="MIT",
            url="https://example.com",
            raw_text="The lab is very productive. It has many members. They work hard.",
            source_type="university",
        )
        summary = generate_summary(candidate)
        assert len(summary) > 0

    def test_empty_raw_text(self):
        candidate = CandidateLead(
            name="Jane",
            title="T",
            affiliation="A",
            url="https://x.com",
            raw_text="",
            source_type="university",
        )
        summary = generate_summary(candidate)
        assert isinstance(summary, str)


# ---------------------------------------------------------------------------
# select_winner
# ---------------------------------------------------------------------------


class TestSelectWinner:
    def test_selects_highest_scoring_candidate(self):
        interests = [make_interest("urban planning", weight=1.0)]

        def cand(text: str, url_suffix: str) -> CandidateLead:
            return CandidateLead(
                name="Person",
                title="T",
                affiliation="A",
                url=f"https://example.com/{url_suffix}",
                raw_text=text,
                source_type="university",
            )

        candidates = [
            cand("marine biology research", "marine"),
            cand("urban planning professor", "urban"),
            cand("computer science department", "cs"),
        ]
        winner = select_winner(candidates, interests)
        assert winner is not None
        assert "urban planning" in winner.raw_text

    def test_returns_none_on_empty_list(self):
        winner = select_winner([], [make_interest("anything")])
        assert winner is None

    def test_deduplicates_by_url(self):
        interests = [make_interest("urban planning", weight=1.0)]
        c = CandidateLead(
            name="Same Person",
            title="T",
            affiliation="A",
            url="https://same.url",
            raw_text="urban planning",
            source_type="university",
        )
        winner = select_winner([c, c, c], interests)
        assert winner is not None
        assert winner.url == "https://same.url"


# ---------------------------------------------------------------------------
# DB-backed tests (require db_session fixture)
# ---------------------------------------------------------------------------


class TestGetTodayLead:
    def test_returns_today_lead(self, db_session, sample_lead):
        result = get_today_lead(db_session)
        assert result is not None
        assert result.name == sample_lead.name

    def test_returns_none_when_no_lead(self, db_session):
        result = get_today_lead(db_session)
        assert result is None


class TestGetLeadById:
    def test_returns_lead(self, db_session, sample_lead):
        result = get_lead_by_id(db_session, sample_lead.id)
        assert result.id == sample_lead.id

    def test_raises_for_missing_id(self, db_session):
        with pytest.raises(SourceNotFoundError):
            get_lead_by_id(db_session, 9999)


class TestListLeads:
    def test_returns_all_leads(self, db_session, sample_lead):
        leads, total = list_leads(db_session)
        assert total == 1
        assert len(leads) == 1

    def test_pagination(self, db_session):
        for i in range(5):
            lead = Lead(
                date=date.today() - timedelta(days=i + 1),
                name=f"Person {i}",
                title="T",
                affiliation="A",
                url=f"https://example.com/{i}",
                summary="S",
                source_type="university",
                created_at=datetime.utcnow(),
            )
            db_session.add(lead)
        db_session.commit()
        leads, total = list_leads(db_session, skip=0, limit=2)
        assert len(leads) == 2
        assert total == 5

    def test_filter_by_source_type(self, db_session):
        news_lead = Lead(
            date=date.today() - timedelta(days=1),
            name="News Person",
            title="T",
            affiliation="A",
            url="https://news.com/1",
            summary="S",
            source_type="news",
            created_at=datetime.utcnow(),
        )
        uni_lead = Lead(
            date=date.today() - timedelta(days=2),
            name="Uni Person",
            title="T",
            affiliation="A",
            url="https://uni.com/1",
            summary="S",
            source_type="university",
            created_at=datetime.utcnow(),
        )
        db_session.add_all([news_lead, uni_lead])
        db_session.commit()
        leads, total = list_leads(db_session, source_type="news")
        assert total == 1
        assert leads[0].source_type == "news"


class TestCreateLeadFromCandidate:
    def test_creates_lead(self, db_session, sample_candidate, sample_interests):
        lead = create_lead_from_candidate(
            db_session, sample_candidate, sample_interests
        )
        assert lead.id is not None
        assert lead.name == sample_candidate.name
        assert lead.date == date.today()

    def test_raises_if_lead_exists_today(
        self, db_session, sample_lead, sample_candidate, sample_interests
    ):
        with pytest.raises(LeadExistsError):
            create_lead_from_candidate(db_session, sample_candidate, sample_interests)


class TestGetActiveInterests:
    def test_returns_only_active(self, db_session, sample_interests, inactive_interest):
        active = get_active_interests(db_session)
        assert all(i.active for i in active)
        assert len(active) == len(sample_interests)


# ---------------------------------------------------------------------------
# get_matched_interest_ids
# ---------------------------------------------------------------------------


class TestGetMatchedInterestIds:
    def test_returns_matching_interest_ids(self):
        interests = [
            make_interest("urban planning", weight=1.0),
            make_interest("marine biology", weight=1.0),
        ]
        interests[0].id = 1
        interests[1].id = 2
        candidate = make_candidate("urban planning research")
        from app.services.lead_service import get_matched_interest_ids

        matched = get_matched_interest_ids(candidate, interests)
        assert 1 in matched
        assert 2 not in matched

    def test_returns_empty_when_no_match(self):
        interests = [make_interest("urban planning", weight=1.0)]
        interests[0].id = 10
        candidate = make_candidate("marine biology deep sea")
        from app.services.lead_service import get_matched_interest_ids

        matched = get_matched_interest_ids(candidate, interests)
        assert matched == []

    def test_skips_inactive_interests(self):
        interests = [make_interest("urban planning", weight=1.0, active=False)]
        interests[0].id = 5
        candidate = make_candidate("urban planning research")
        from app.services.lead_service import get_matched_interest_ids

        matched = get_matched_interest_ids(candidate, interests)
        assert matched == []


# ---------------------------------------------------------------------------
# select_top_candidates
# ---------------------------------------------------------------------------


class TestSelectTopCandidates:
    def test_returns_top_n(self):
        interests = [make_interest("urban planning", weight=1.0)]

        def cand(text: str, url_suffix: str) -> CandidateLead:
            return CandidateLead(
                name="Person",
                title="T",
                affiliation="A",
                url=f"https://example.com/{url_suffix}",
                raw_text=text,
                source_type="university",
            )

        candidates = [
            cand("marine biology research", "marine"),
            cand("urban planning professor", "urban"),
            cand("computer science department", "cs"),
            cand("urban planning and city design", "urban2"),
        ]
        from app.services.lead_service import select_top_candidates

        top = select_top_candidates(candidates, interests, n=2)
        assert len(top) == 2
        # Top candidates should be urban planning related
        assert all("urban" in c.url for c in top)

    def test_returns_empty_for_empty_input(self):
        from app.services.lead_service import select_top_candidates

        result = select_top_candidates([], [make_interest("x")])
        assert result == []

    def test_deduplicates_by_url(self):
        interests = [make_interest("urban planning", weight=1.0)]
        c = CandidateLead(
            name="Same",
            title="T",
            affiliation="A",
            url="https://same.url",
            raw_text="urban planning",
            source_type="university",
        )
        from app.services.lead_service import select_top_candidates

        top = select_top_candidates([c, c, c], interests, n=3)
        assert len(top) == 1

    def test_returns_fewer_than_n_if_not_enough(self):
        interests = [make_interest("urban planning", weight=1.0)]
        candidates = [
            CandidateLead(
                name="P",
                title="T",
                affiliation="A",
                url="https://example.com/1",
                raw_text="urban planning",
                source_type="university",
            )
        ]
        from app.services.lead_service import select_top_candidates

        top = select_top_candidates(candidates, interests, n=3)
        assert len(top) == 1


# ---------------------------------------------------------------------------
# create_leads_from_candidates
# ---------------------------------------------------------------------------


class TestCreateLeadsFromCandidates:
    def test_creates_multiple_leads(self, db_session, sample_interests):
        from datetime import date

        from app.services.lead_service import create_leads_from_candidates

        candidates = [
            CandidateLead(
                name=f"Person {i}",
                title="T",
                affiliation="A",
                url=f"https://example.com/{i}",
                raw_text="urban planning researcher",
                source_type="university",
            )
            for i in range(3)
        ]
        leads = create_leads_from_candidates(db_session, candidates, sample_interests)
        assert len(leads) == 3
        assert leads[0].rank == 1
        assert leads[1].rank == 2
        assert leads[2].rank == 3
        for lead in leads:
            assert lead.date == date.today()

    def test_idempotent_skips_existing_ranks(self, db_session, sample_interests):
        from app.services.lead_service import create_leads_from_candidates

        candidate = CandidateLead(
            name="Test Person",
            title="T",
            affiliation="A",
            url="https://example.com/test",
            raw_text="urban planning",
            source_type="university",
        )
        leads1 = create_leads_from_candidates(db_session, [candidate], sample_interests)
        leads2 = create_leads_from_candidates(db_session, [candidate], sample_interests)
        assert len(leads1) == 1
        assert len(leads2) == 0  # skipped

    def test_stores_matched_interests(self, db_session, sample_interests):
        import json

        from app.services.lead_service import create_leads_from_candidates

        candidate = CandidateLead(
            name="Planner",
            title="T",
            affiliation="A",
            url="https://example.com/planner",
            raw_text="urban planning researcher",
            source_type="university",
        )
        leads = create_leads_from_candidates(db_session, [candidate], sample_interests)
        assert len(leads) == 1
        matched = json.loads(leads[0].matched_interests)
        # urban planning interest should be in matched
        assert sample_interests[0].id in matched


# ---------------------------------------------------------------------------
# get_leads_by_date
# ---------------------------------------------------------------------------


class TestGetLeadsByDate:
    def test_returns_leads_ordered_by_rank(self, db_session):
        from datetime import date

        from app.services.lead_service import get_leads_by_date

        today = date.today()
        for rank in (3, 1, 2):  # deliberately disordered
            lead = Lead(
                date=today,
                rank=rank,
                name=f"Person {rank}",
                title="T",
                affiliation="A",
                url=f"https://example.com/{rank}",
                summary="S",
                source_type="university",
                created_at=datetime.utcnow(),
            )
            db_session.add(lead)
        db_session.commit()

        leads = get_leads_by_date(db_session, today)
        assert len(leads) == 3
        assert leads[0].rank == 1
        assert leads[1].rank == 2
        assert leads[2].rank == 3

    def test_returns_empty_for_no_leads(self, db_session):
        from datetime import date

        from app.services.lead_service import get_leads_by_date

        leads = get_leads_by_date(db_session, date(2000, 1, 1))
        assert leads == []
