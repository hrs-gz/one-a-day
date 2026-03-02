from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from unittest.mock import patch

from app.models.lead import Lead
from app.scrapers.base import CandidateLead


def make_lead(db_session, days_ago: int = 0, rank: int = 1, **kwargs) -> Lead:
    """Helper to create a Lead in the test DB."""
    d = date.today() - timedelta(days=days_ago)
    lead = Lead(
        date=d,
        rank=rank,
        name=kwargs.get("name", f"Person {days_ago}-{rank}"),
        title="T",
        affiliation="A",
        url=kwargs.get("url", f"https://example.com/{days_ago}/{rank}"),
        summary="S",
        source_type=kwargs.get("source_type", "university"),
        favorited=kwargs.get("favorited", False),
        vote=kwargs.get("vote", 0),
        matched_interests=kwargs.get("matched_interests", "[]"),
        created_at=datetime.utcnow(),
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)
    return lead


class TestGetTodayLead:
    def test_returns_today_lead(self, client, sample_lead):
        response = client.get("/api/v1/leads/today")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_lead.name
        assert data["affiliation"] == sample_lead.affiliation

    def test_returns_404_when_no_lead(self, client, db_session):
        response = client.get("/api/v1/leads/today")
        assert response.status_code == 404
        assert response.json()["detail"] == "No lead found for today"


class TestGetLeadsByDate:
    def test_returns_leads_for_date(self, client, db_session):
        yesterday = date.today() - timedelta(days=1)
        for rank in (1, 2, 3):
            db_session.add(
                Lead(
                    date=yesterday,
                    rank=rank,
                    name=f"Person {rank}",
                    title="T",
                    affiliation="A",
                    url=f"https://example.com/{rank}",
                    summary="S",
                    source_type="university",
                    created_at=datetime.utcnow(),
                )
            )
        db_session.commit()

        response = client.get(f"/api/v1/leads/by-date/{yesterday.isoformat()}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["rank"] == 1
        assert data[1]["rank"] == 2
        assert data[2]["rank"] == 3

    def test_returns_empty_list_when_no_leads(self, client, db_session):
        response = client.get("/api/v1/leads/by-date/2000-01-01")
        assert response.status_code == 200
        assert response.json() == []


class TestListLeads:
    def test_returns_empty_list(self, client, db_session):
        response = client.get("/api/v1/leads")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_returns_leads(self, client, sample_lead):
        response = client.get("/api/v1/leads")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    def test_pagination(self, client, db_session):
        for i in range(5):
            lead = Lead(
                date=date.today() - timedelta(days=i + 1),
                rank=1,
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

        response = client.get("/api/v1/leads?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    def test_filter_by_source_type(self, client, db_session):
        news_lead = Lead(
            date=date.today() - timedelta(days=1),
            rank=1,
            name="News Person",
            title="T",
            affiliation="A",
            url="https://news.com",
            summary="S",
            source_type="news",
            created_at=datetime.utcnow(),
        )
        db_session.add(news_lead)
        db_session.commit()

        response = client.get("/api/v1/leads?source_type=news")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["source_type"] == "news"


class TestGetLeadById:
    def test_returns_lead(self, client, sample_lead):
        response = client.get(f"/api/v1/leads/{sample_lead.id}")
        assert response.status_code == 200
        assert response.json()["id"] == sample_lead.id

    def test_returns_404(self, client, db_session):
        response = client.get("/api/v1/leads/9999")
        assert response.status_code == 404


class TestGenerateLead:
    def test_generates_leads_successfully(self, client, db_session, sample_interests):
        fake_candidate = CandidateLead(
            name="New Person",
            title="Researcher",
            affiliation="Institute",
            url="https://example.com/new",
            raw_text="urban planning researcher at institute",
            source_type="university",
        )
        with patch("app.routers.leads.scrape_service.run_all_scrapers") as mock_scrape:
            mock_scrape.return_value = [fake_candidate]
            response = client.post("/api/v1/leads/generate")

        assert response.status_code == 201
        data = response.json()
        # Returns a list now
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == "New Person"

    def test_returns_409_if_lead_exists(self, client, sample_lead, sample_interests):
        with patch("app.routers.leads.scrape_service.run_all_scrapers") as mock_scrape:
            fake = CandidateLead(
                name="Another",
                title="T",
                affiliation="A",
                url="https://example.com/another",
                raw_text="urban planning",
                source_type="university",
            )
            mock_scrape.return_value = [fake]
            # sample_lead already exists at rank=1 for today
            with patch(
                "app.routers.leads.lead_service.create_leads_from_candidates"
            ) as mock_create:
                from app.exceptions import LeadExistsError

                mock_create.side_effect = LeadExistsError("exists")
                response = client.post("/api/v1/leads/generate")

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_returns_422_when_no_candidates(self, client, db_session):
        with patch("app.routers.leads.scrape_service.run_all_scrapers") as mock_scrape:
            mock_scrape.return_value = []
            response = client.post("/api/v1/leads/generate")

        assert response.status_code == 422


class TestVoteOnLead:
    def test_upvote_lead(self, client, db_session, sample_interests):
        # Lead matched to interest[0] (urban planning, weight=1.0)
        # Set weight to 0.7 so +0.1 is not clamped
        interest = sample_interests[0]
        interest.weight = 0.7
        db_session.commit()
        interest_id = interest.id
        lead = make_lead(
            db_session,
            days_ago=0,
            rank=1,
            matched_interests=json.dumps([interest_id]),
        )

        response = client.patch(f"/api/v1/leads/{lead.id}/vote", json={"vote": 1})
        assert response.status_code == 200
        data = response.json()
        assert data["vote"] == 1

        # Check weight was adjusted +0.1 (0.7 → 0.8)
        db_session.refresh(interest)
        assert abs(interest.weight - 0.8) < 1e-9

    def test_downvote_lead(self, client, db_session, sample_interests):
        interest_id = sample_interests[1].id
        lead = make_lead(
            db_session,
            days_ago=0,
            rank=1,
            matched_interests=json.dumps([interest_id]),
        )
        old_weight = sample_interests[1].weight

        response = client.patch(f"/api/v1/leads/{lead.id}/vote", json={"vote": -1})
        assert response.status_code == 200
        assert response.json()["vote"] == -1

        db_session.refresh(sample_interests[1])
        assert abs(sample_interests[1].weight - max(0.0, old_weight - 0.1)) < 1e-9

    def test_neutral_vote_no_weight_change(self, client, db_session, sample_interests):
        interest_id = sample_interests[0].id
        lead = make_lead(
            db_session,
            days_ago=0,
            rank=1,
            matched_interests=json.dumps([interest_id]),
        )
        old_weight = sample_interests[0].weight

        response = client.patch(f"/api/v1/leads/{lead.id}/vote", json={"vote": 0})
        assert response.status_code == 200

        db_session.refresh(sample_interests[0])
        assert sample_interests[0].weight == old_weight

    def test_invalid_vote_value(self, client, db_session):
        lead = make_lead(db_session, days_ago=0, rank=1)
        response = client.patch(f"/api/v1/leads/{lead.id}/vote", json={"vote": 5})
        assert response.status_code == 422

    def test_vote_clamps_weight_to_1(self, client, db_session, sample_interests):
        interest = sample_interests[0]
        interest.weight = 1.0
        db_session.commit()
        lead = make_lead(
            db_session,
            days_ago=0,
            rank=1,
            matched_interests=json.dumps([interest.id]),
        )

        response = client.patch(f"/api/v1/leads/{lead.id}/vote", json={"vote": 1})
        assert response.status_code == 200
        db_session.refresh(interest)
        assert interest.weight <= 1.0

    def test_vote_clamps_weight_to_0(self, client, db_session, sample_interests):
        interest = sample_interests[0]
        interest.weight = 0.0
        db_session.commit()
        lead = make_lead(
            db_session,
            days_ago=0,
            rank=1,
            matched_interests=json.dumps([interest.id]),
        )

        response = client.patch(f"/api/v1/leads/{lead.id}/vote", json={"vote": -1})
        assert response.status_code == 200
        db_session.refresh(interest)
        assert interest.weight >= 0.0

    def test_vote_returns_404_for_missing_lead(self, client, db_session):
        response = client.patch("/api/v1/leads/9999/vote", json={"vote": 1})
        assert response.status_code == 404


class TestFavoriteLead:
    def test_favorite_lead(self, client, db_session):
        lead = make_lead(db_session, days_ago=0, rank=1)
        assert not lead.favorited

        response = client.patch(
            f"/api/v1/leads/{lead.id}/favorite", json={"favorited": True}
        )
        assert response.status_code == 200
        assert response.json()["favorited"] is True

    def test_unfavorite_lead(self, client, db_session):
        lead = make_lead(db_session, days_ago=0, rank=1, favorited=True)

        response = client.patch(
            f"/api/v1/leads/{lead.id}/favorite", json={"favorited": False}
        )
        assert response.status_code == 200
        assert response.json()["favorited"] is False

    def test_favorite_returns_404_for_missing_lead(self, client, db_session):
        response = client.patch("/api/v1/leads/9999/favorite", json={"favorited": True})
        assert response.status_code == 404
