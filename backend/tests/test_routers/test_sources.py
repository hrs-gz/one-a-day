from __future__ import annotations

import json


class TestListSources:
    def test_returns_empty(self, client, db_session):
        response = client.get("/api/v1/sources")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_returns_sources(self, client, sample_scraper_source):
        response = client.get("/api/v1/sources")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == sample_scraper_source.name


class TestCreateSource:
    def test_creates_source(self, client, db_session):
        payload = {
            "name": "Test Source",
            "scraper_class": "app.scrapers.university.UniversityScraper",
            "config": json.dumps({"seed_urls": ["https://example.edu"]}),
            "enabled": True,
        }
        response = client.post("/api/v1/sources", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Source"
        assert data["enabled"] is True

    def test_defaults_enabled_true(self, client, db_session):
        payload = {
            "name": "Test Source",
            "scraper_class": "app.scrapers.university.UniversityScraper",
        }
        response = client.post("/api/v1/sources", json=payload)
        assert response.status_code == 201
        assert response.json()["enabled"] is True


class TestGetSource:
    def test_returns_source(self, client, sample_scraper_source):
        response = client.get(f"/api/v1/sources/{sample_scraper_source.id}")
        assert response.status_code == 200
        assert response.json()["id"] == sample_scraper_source.id

    def test_returns_404(self, client, db_session):
        response = client.get("/api/v1/sources/9999")
        assert response.status_code == 404


class TestUpdateSource:
    def test_disables_source(self, client, sample_scraper_source):
        response = client.patch(
            f"/api/v1/sources/{sample_scraper_source.id}",
            json={"enabled": False},
        )
        assert response.status_code == 200
        assert response.json()["enabled"] is False

    def test_updates_name(self, client, sample_scraper_source):
        response = client.patch(
            f"/api/v1/sources/{sample_scraper_source.id}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_returns_404(self, client, db_session):
        response = client.patch("/api/v1/sources/9999", json={"enabled": False})
        assert response.status_code == 404


class TestDeleteSource:
    def test_deletes_source(self, client, sample_scraper_source):
        response = client.delete(f"/api/v1/sources/{sample_scraper_source.id}")
        assert response.status_code == 204

        get_response = client.get(f"/api/v1/sources/{sample_scraper_source.id}")
        assert get_response.status_code == 404

    def test_returns_404(self, client, db_session):
        response = client.delete("/api/v1/sources/9999")
        assert response.status_code == 404
