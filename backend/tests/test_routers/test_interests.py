from __future__ import annotations


class TestListInterests:
    def test_returns_empty(self, client, db_session):
        response = client.get("/api/v1/interests")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_returns_interests(self, client, sample_interests):
        response = client.get("/api/v1/interests")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == len(sample_interests)


class TestCreateInterest:
    def test_creates_interest(self, client, db_session):
        response = client.post(
            "/api/v1/interests",
            json={"keyword": "urban planning", "weight": 0.8, "active": True},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["keyword"] == "urban planning"
        assert data["weight"] == 0.8
        assert data["active"] is True
        assert "id" in data

    def test_weight_defaults_to_1(self, client, db_session):
        response = client.post(
            "/api/v1/interests",
            json={"keyword": "new topic"},
        )
        assert response.status_code == 201
        assert response.json()["weight"] == 1.0

    def test_rejects_weight_out_of_range(self, client, db_session):
        response = client.post(
            "/api/v1/interests",
            json={"keyword": "bad", "weight": 1.5},
        )
        assert response.status_code == 422

    def test_rejects_negative_weight(self, client, db_session):
        response = client.post(
            "/api/v1/interests",
            json={"keyword": "bad", "weight": -0.1},
        )
        assert response.status_code == 422


class TestGetInterest:
    def test_returns_interest(self, client, sample_interests):
        interest_id = sample_interests[0].id
        response = client.get(f"/api/v1/interests/{interest_id}")
        assert response.status_code == 200
        assert response.json()["id"] == interest_id

    def test_returns_404(self, client, db_session):
        response = client.get("/api/v1/interests/9999")
        assert response.status_code == 404


class TestUpdateInterest:
    def test_updates_keyword(self, client, sample_interests):
        interest_id = sample_interests[0].id
        response = client.patch(
            f"/api/v1/interests/{interest_id}",
            json={"keyword": "new keyword"},
        )
        assert response.status_code == 200
        assert response.json()["keyword"] == "new keyword"

    def test_deactivates_interest(self, client, sample_interests):
        interest_id = sample_interests[0].id
        response = client.patch(
            f"/api/v1/interests/{interest_id}",
            json={"active": False},
        )
        assert response.status_code == 200
        assert response.json()["active"] is False

    def test_returns_404(self, client, db_session):
        response = client.patch("/api/v1/interests/9999", json={"keyword": "x"})
        assert response.status_code == 404


class TestDeleteInterest:
    def test_deletes_interest(self, client, sample_interests):
        interest_id = sample_interests[0].id
        response = client.delete(f"/api/v1/interests/{interest_id}")
        assert response.status_code == 204

        # Confirm gone
        get_response = client.get(f"/api/v1/interests/{interest_id}")
        assert get_response.status_code == 404

    def test_returns_404(self, client, db_session):
        response = client.delete("/api/v1/interests/9999")
        assert response.status_code == 404


class TestParseInterests:
    def test_parse_creates_interests_fallback(self, client, db_session):
        response = client.post(
            "/api/v1/interests/parse",
            json={"text": "urban planning, marine biology, machine learning"},
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["created"]) == 3
        keywords = {i["keyword"] for i in data["created"]}
        assert "urban planning" in keywords
        assert "marine biology" in keywords
        assert "machine learning" in keywords
        assert data["skipped"] == []

    def test_parse_skips_duplicates(self, client, sample_interests):
        # sample_interests already has "urban planning"
        response = client.post(
            "/api/v1/interests/parse",
            json={"text": "urban planning, new topic"},
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["created"]) == 1
        assert data["created"][0]["keyword"] == "new topic"
        assert "urban planning" in data["skipped"]

    def test_parse_empty_text_returns_422(self, client, db_session):
        response = client.post("/api/v1/interests/parse", json={"text": "   "})
        assert response.status_code == 422

    def test_parse_newline_split(self, client, db_session):
        response = client.post(
            "/api/v1/interests/parse",
            json={"text": "deep learning\nocean science\nclimate change"},
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["created"]) == 3

    def test_parse_and_split(self, client, db_session):
        response = client.post(
            "/api/v1/interests/parse",
            json={"text": "robotics and computer vision"},
        )
        assert response.status_code == 201
        data = response.json()
        # "robotics" and "computer vision" extracted
        assert len(data["created"]) >= 1
