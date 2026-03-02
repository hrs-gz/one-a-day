from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.interest_config import InterestConfig
from app.models.lead import Lead
from app.models.scraper_source import ScraperSource
from app.scrapers.base import CandidateLead

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# In-memory database
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def db_session():
    """In-memory SQLite session using a shared cache URI so all connections see the same DB."""  # noqa: E501
    # Use a named in-memory DB with shared cache so TestClient threads and the
    # fixture share the same database instance.
    engine = create_engine(
        "sqlite:///file:testdb?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False, "uri": True},
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI test client with DB session override.

    Overrides get_db to yield the same session used by the test,
    so all router calls share the fixture's in-memory database.
    """

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_lead(db_session) -> Lead:
    """Persisted Lead for today."""
    lead = Lead(
        date=date.today(),
        name="Dr. Jane Smith",
        title="Associate Professor",
        affiliation="MIT",
        url="https://mit.edu/faculty/jsmith",
        summary="Researches urban planning. Jane Smith leads the Urban Futures Lab.",
        source_type="university",
        contact_hint="https://linkedin.com/in/jsmith",
        created_at=datetime.utcnow(),
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)
    return lead


@pytest.fixture
def sample_interests(db_session) -> list[InterestConfig]:
    """Three active InterestConfig objects."""
    interests = [
        InterestConfig(keyword="urban planning", weight=1.0, active=True),
        InterestConfig(keyword="computational biology", weight=0.8, active=True),
        InterestConfig(keyword="machine learning", weight=0.5, active=True),
    ]
    for i in interests:
        db_session.add(i)
    db_session.commit()
    return interests


@pytest.fixture
def inactive_interest(db_session) -> InterestConfig:
    """An inactive interest config."""
    interest = InterestConfig(keyword="inactive topic", weight=1.0, active=False)
    db_session.add(interest)
    db_session.commit()
    return interest


@pytest.fixture
def sample_candidate() -> CandidateLead:
    """CandidateLead dataclass with all fields populated."""
    return CandidateLead(
        name="Dr. Jane Smith",
        title="Associate Professor",
        affiliation="MIT",
        url="https://mit.edu/faculty/jsmith",
        raw_text="Dr. Jane Smith is an Associate Professor specializing in urban planning research at MIT.",  # noqa: E501
        source_type="university",
        contact_hint="https://linkedin.com/in/jsmith",
    )


@pytest.fixture
def sample_scraper_source(db_session) -> ScraperSource:
    """A persisted ScraperSource."""
    source = ScraperSource(
        name="Test University",
        scraper_class="app.scrapers.university.UniversityScraper",
        config=json.dumps(
            {
                "seed_urls": ["https://example.edu/faculty"],
                "selectors": {
                    "profile_link": "a.faculty-link",
                    "name": "h1.name",
                    "title": "span.title",
                    "affiliation": "span.dept",
                },
            }
        ),
        enabled=True,
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)
    return source


@pytest.fixture
def mock_html():
    """Returns a function to load HTML from tests/fixtures/sample_html/."""

    def _load(filename: str) -> str:
        path = FIXTURES_DIR / "sample_html" / filename
        if not path.exists():
            raise FileNotFoundError(f"Fixture not found: {path}")
        return path.read_text(encoding="utf-8")

    return _load
