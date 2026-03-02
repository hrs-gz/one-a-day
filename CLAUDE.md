# CLAUDE.md — One-A-Day (oad)

## Project Purpose

One-A-Day uses an agent-driven pipeline to surface up to 3 ranked contact leads per day. The target is people worth knowing — academics doing unusual research, professionals working on something niche, local operators, independent thinkers.

The user configures interests (keywords + weights) through a web dashboard. Each day a scheduler runs the agentic pipeline: a Planner agent chooses sources and constraints, a Query Builder generates structured search queries, a Candidate Gatherer fetches and deduplicates URLs, a Verifier/Extractor agent emits only evidence-backed facts (every fact carries a source URL and verbatim excerpt), a Card Writer scores each candidate across multiple dimensions, and a Deterministic Selector picks the top 1–3 leads. The dashboard shows today's ranked leads and a browsable history. Voting on a lead feeds back into interest weights.

## Requirements

- Python 3.11+
- Node 20+
- SQLite 3.35+ (for JSON functions)

## Architecture Overview
```
[scheduler/daily_job.py]              runs on cron or manually with --force
        |
        v
[app/services/agentic_pipeline_service.py]   orchestrates agent chain (Phase 1+)
        |
        +---> [Planner Agent]            → DailyRunPlan (source packs, constraints)
        +---> [Query Builder Agent]      → CandidateQueryPack (structured search queries)
        +---> [Candidate Gatherer]       → deduplicated URLs
        +---> [Verifier/Extractor Agent] → VerifiedLeadBundle (facts w/ url+excerpt)
        +---> [Card Writer Agent]        → ScoringCard (relevance, novelty, authority…)
        +---> [Deterministic Selector]   → top 1–3 ranked leads
        |
        v
[SQLite DB via SQLAlchemy]            persists up to 3 Leads per day (rank 1–3)
        |
        v
[FastAPI backend — /api/v1/]          REST API
        |
        v
[React + TypeScript frontend]         SPA at localhost:5173
        ├── Dashboard (today's ranked leads)
        ├── History (past leads)
        ├── Settings (interests, scraper sources)
        └── Algorithm (interest tag cloud + NL bulk input)
```

Classic scraper pipeline (`PIPELINE_MODE=classic`): `scrape_service.py` → `app/scrapers/*.py` → `lead_service.py`. Used for local development without LLM keys.

### Backend (`backend/`)

- Entry: `app/main.py` — FastAPI app factory, router registration, CORS
- Config: `app/config.py` — `pydantic-settings`, reads from `.env`
- DB: SQLite via SQLAlchemy ORM, Alembic for migrations
- Routers: thin — validate input, call service, return schema. No ORM queries in routers.
- Services: all business logic lives here

### Frontend (`frontend/`)

- Vite + React 18 + TypeScript (strict mode)
- Four pages: Dashboard, History, Settings, Algorithm
- All API calls go through typed functions in `src/api/`
- Server state via TanStack Query v5 — no Redux/Zustand in v1

### Scheduler

- `scheduler/daily_job.py` — runnable directly (`python -m scheduler.daily_job`)
- Default: 06:00 daily via cron or APScheduler
- Idempotent: skips if a lead already exists for today

## Key Commands

### Backend (run from `backend/`)
```bash
# Install
pip install -e ".[dev]"

# Run dev server
uvicorn app.main:app --reload --port 8000

# Migrations
alembic upgrade head
alembic revision --autogenerate -m "describe change"

# Run pipeline manually (ignores existing lead for today)
# NOTE: run from repo root, not backend/
cd .. && python -m scheduler.daily_job --force

# Test
pytest
pytest --cov=app/services --cov=app/scrapers --cov-fail-under=80

# Lint + format
ruff check .
ruff format .

# Pre-commit (run after cloning)
pre-commit install
pre-commit run --all-files
```

### Frontend (run from `frontend/`)
```bash
npm install
npm run dev        # Vite dev server, proxies /api to localhost:8000
npm run build      # Production build
npm run test       # vitest
npm run lint       # ESLint + Prettier check
```

## Directory Structure
```
oad/
├── CLAUDE.md
├── .cursor/rules
├── .env                          # Local only — never commit
├── .env.example                  # Committed template
├── .pre-commit-config.yaml
├── .gitignore
├── README.md
│
├── config/
│   ├── models.yaml               # LLM provider + model assignments per agent role
│   └── agents.yaml               # Agent rules + IO schema contracts
│
├── docs/
│   └── agentic-architecture-plan.md
│
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── exceptions.py         # Domain exceptions
│   │   ├── agents/               # [Phase 1 — in progress]
│   │   │   ├── planner.py
│   │   │   ├── query_builder.py
│   │   │   ├── verifier_extractor.py
│   │   │   └── card_writer.py
│   │   ├── llm/                  # [Phase 1 — in progress]
│   │   │   ├── openrouter_client.py
│   │   │   └── gemini_client.py
│   │   ├── models/
│   │   │   ├── lead.py
│   │   │   ├── interest_config.py
│   │   │   └── scraper_source.py
│   │   ├── schemas/
│   │   │   ├── lead.py
│   │   │   ├── interest_config.py
│   │   │   ├── scraper_source.py
│   │   │   └── agent_contracts.py  # [Phase 1 — in progress]
│   │   ├── routers/
│   │   │   ├── leads.py
│   │   │   ├── interests.py
│   │   │   └── sources.py
│   │   ├── services/
│   │   │   ├── lead_service.py
│   │   │   ├── scrape_service.py
│   │   │   └── agentic_pipeline_service.py  # [Phase 1 — in progress]
│   │   └── scrapers/             # Classic pipeline (PIPELINE_MODE=classic)
│   │       ├── base.py
│   │       ├── university.py
│   │       ├── company.py
│   │       ├── news.py
│   │       ├── personal_site.py
│   │       ├── local_news.py
│   │       ├── rss.py
│   │       └── substack.py
│   └── tests/
│       ├── conftest.py
│       ├── fixtures/
│       │   ├── sample_leads.json
│       │   ├── sample_interests.json
│       │   └── sample_html/
│       │       └── university_page.html
│       ├── test_routers/
│       │   ├── test_leads.py
│       │   ├── test_interests.py
│       │   └── test_sources.py
│       ├── test_services/
│       │   ├── test_lead_service.py
│       │   └── test_scrape_service.py
│       └── test_scrapers/
│           ├── test_university.py
│           ├── test_base.py
│           └── ...               # One file per scraper
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── eslint.config.js
│   ├── .prettierrc
│   ├── index.html
│   ├── DESIGN.md
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   ├── client.ts
│       │   ├── leads.ts
│       │   ├── interests.ts
│       │   └── sources.ts
│       ├── components/
│       │   ├── LeadCard.tsx
│       │   ├── LeadCard.test.tsx
│       │   ├── LeadHistory.tsx
│       │   ├── InterestEditor.tsx
│       │   ├── InterestEditor.test.tsx
│       │   ├── SourceToggle.tsx
│       │   └── Layout.tsx
│       ├── pages/
│       │   ├── Dashboard.tsx     # 3-card layout for ranked leads
│       │   ├── History.tsx
│       │   ├── Settings.tsx
│       │   └── Algorithm.tsx     # Interest tag cloud + NL bulk input
│       ├── hooks/
│       │   ├── useLeads.ts
│       │   └── useInterests.ts
│       ├── types/
│       │   └── index.ts
│       └── utils/
│           └── date.ts
│
└── scheduler/
    └── daily_job.py
```

## Testing

### Structure

| Layer | Location | Runner | Coverage Target |
|-------|----------|--------|-----------------|
| Scrapers | `tests/test_scrapers/` | pytest | 80% |
| Services | `tests/test_services/` | pytest | 80% |
| Routers | `tests/test_routers/` | pytest | 70% |
| Components | colocated (`*.test.tsx`) | vitest | — |
| API modules | `src/api/*.test.ts` | vitest | — |

### Backend Testing

#### Test Categories

| Category | Purpose | Mocking | Example |
|----------|---------|---------|---------|
| Unit | Single function/method | All external deps | `test_score_candidate()` |
| Integration | Service + DB | HTTP only | `test_get_today_lead()` |
| Router | Full request/response | HTTP + external services | `test_get_leads_endpoint()` |

#### Required Test Files
```
tests/
├── conftest.py                    # Shared fixtures
├── fixtures/
│   ├── sample_leads.json          # Lead test data
│   ├── sample_interests.json      # InterestConfig test data
│   └── sample_html/               # Scraped page snapshots
│       ├── university_page.html
│       └── news_page.html
├── test_scrapers/
│   ├── test_base.py               # BaseScraper._get(), rate limiting
│   ├── test_university.py         # UniversityScraper.fetch_candidates()
│   └── ...                        # One file per scraper
├── test_services/
│   ├── test_lead_service.py       # Scoring, selection, dedup
│   └── test_scrape_service.py     # Orchestration, error handling
└── test_routers/
    ├── test_leads.py              # /api/v1/leads endpoints
    ├── test_interests.py          # /api/v1/interests endpoints
    └── test_sources.py            # /api/v1/sources endpoints
```

#### Key Fixtures (`conftest.py`)
```python
@pytest.fixture
def db_session():
    """In-memory SQLite session, rolled back after each test."""

@pytest.fixture
def sample_lead(db_session):
    """Persisted Lead for today."""

@pytest.fixture
def sample_interests(db_session):
    """List of 3 active InterestConfig objects."""

@pytest.fixture
def sample_candidate():
    """CandidateLead dataclass with all fields populated."""

@pytest.fixture
def mock_html():
    """Returns function to load HTML from tests/fixtures/sample_html/."""
```

#### Scoring Function Tests

The scoring function is core business logic. Test with explicit numeric assertions:
```python
def test_score_candidate_exact_keyword_match():
    candidate = CandidateLead(raw_text="urban planning research")
    interests = [InterestConfig(keyword="urban planning", weight=1.0, active=True)]
    score = score_candidate(candidate, interests)
    assert score == 100.0

def test_score_candidate_partial_match():
    candidate = CandidateLead(raw_text="city planning department")
    interests = [InterestConfig(keyword="urban planning", weight=1.0, active=True)]
    score = score_candidate(candidate, interests)
    assert 0 < score < 100

def test_score_candidate_no_match():
    candidate = CandidateLead(raw_text="marine biology lab")
    interests = [InterestConfig(keyword="urban planning", weight=1.0, active=True)]
    score = score_candidate(candidate, interests)
    assert score == 0.0

def test_score_candidate_weighted():
    candidate = CandidateLead(raw_text="urban planning")
    interests = [InterestConfig(keyword="urban planning", weight=0.5, active=True)]
    score = score_candidate(candidate, interests)
    assert score == 50.0
```

#### Scraper Tests

All scraper tests must mock HTTP. Never hit real URLs.
```python
# tests/test_scrapers/test_university.py
import responses

@responses.activate
def test_fetch_candidates_success(mock_html):
    responses.add(
        responses.GET,
        "https://example.edu/faculty",
        body=mock_html("university_page.html"),
        status=200,
    )
    scraper = UniversityScraper()
    config = {"seed_urls": ["https://example.edu/faculty"], ...}
    candidates = scraper.fetch_candidates(config)
    
    assert len(candidates) == 3
    assert candidates[0].name == "Dr. Jane Smith"
    assert candidates[0].source_type == "university"

@responses.activate
def test_fetch_candidates_http_error():
    responses.add(responses.GET, "https://example.edu/faculty", status=500)
    scraper = UniversityScraper()
    candidates = scraper.fetch_candidates(config)
    
    assert candidates == []  # Graceful degradation
```

#### Router Tests

Use `httpx.AsyncClient` with the FastAPI app:
```python
# tests/test_routers/test_leads.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_get_today_lead(db_session, sample_lead):
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/leads/today")
    
    assert response.status_code == 200
    assert response.json()["name"] == sample_lead.name

@pytest.mark.asyncio
async def test_get_today_lead_not_found(db_session):
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/leads/today")
    
    assert response.status_code == 404
    assert response.json()["detail"] == "No lead found for today"
```

### Frontend Testing

#### Component Tests (colocated)
```
src/components/
├── LeadCard.tsx
├── LeadCard.test.tsx       # Tests LeadCard
├── InterestEditor.tsx
└── InterestEditor.test.tsx # Tests InterestEditor
```

#### Required Component Coverage

| Component | Test Cases |
|-----------|------------|
| `LeadCard` | Renders all fields; handles missing `contact_hint`; displays correct source badge |
| `InterestEditor` | Add new interest; edit existing; delete with confirmation; weight validation |
| `SourceToggle` | Toggle enabled/disabled; shows last run status |
| `LeadHistory` | Renders list; pagination; empty state |

#### Example Component Test
```typescript
// src/components/LeadCard.test.tsx
import { render, screen } from '@testing-library/react';
import { LeadCard } from './LeadCard';

const mockLead = {
  id: 1,
  name: 'Dr. Jane Smith',
  title: 'Associate Professor',
  affiliation: 'MIT',
  url: 'https://mit.edu/faculty/jsmith',
  summary: 'Researches urban planning.',
  source_type: 'university',
  contact_hint: 'https://linkedin.com/in/jsmith',
  date: '2025-03-01',
};

describe('LeadCard', () => {
  it('renders all lead fields', () => {
    render(<LeadCard lead={mockLead} />);
    
    expect(screen.getByText('Dr. Jane Smith')).toBeInTheDocument();
    expect(screen.getByText('Associate Professor')).toBeInTheDocument();
    expect(screen.getByText('MIT')).toBeInTheDocument();
  });

  it('renders without contact_hint', () => {
    const leadNoContact = { ...mockLead, contact_hint: null };
    render(<LeadCard lead={leadNoContact} />);
    
    expect(screen.queryByRole('link', { name: /linkedin/i })).not.toBeInTheDocument();
  });

  it('displays source type badge', () => {
    render(<LeadCard lead={mockLead} />);
    
    expect(screen.getByText('university')).toHaveClass('badge');
  });
});
```

#### API Module Tests
```typescript
// src/api/leads.test.ts
import { describe, it, expect, vi } from 'vitest';
import { getTodayLead, getLeads } from './leads';
import { client } from './client';

vi.mock('./client');

describe('leads API', () => {
  it('getTodayLead calls correct endpoint', async () => {
    vi.mocked(client.get).mockResolvedValue({ data: mockLead });
    
    const result = await getTodayLead();
    
    expect(client.get).toHaveBeenCalledWith('/api/v1/leads/today');
    expect(result).toEqual(mockLead);
  });
});
```

### CI Requirements

All checks must pass before merge:

| Check | Command | Threshold |
|-------|---------|-----------|
| Backend tests | `pytest` | All pass |
| Backend coverage | `pytest --cov --cov-fail-under=80` | 80% on services/scrapers |
| Backend lint | `ruff check .` | No errors |
| Backend format | `ruff format --check .` | No changes |
| Frontend tests | `npm run test` | All pass |
| Frontend lint | `npm run lint` | No errors |
| Secrets scan | `detect-secrets scan` | No secrets |

## Data Models

### Lead (`models/lead.py`)
```python
class Lead(Base):
    id: int                      # PK
    date: date                   # Part of composite unique constraint
    rank: int                    # 1–3; rank 1 = best match; UNIQUE(date, rank)
    name: str
    title: str                   # Role or job title
    affiliation: str             # Employer, university, publication, etc.
    url: str                     # Source URL where they were found
    summary: str                 # 1–3 sentence description
    source_type: str             # "university"|"company"|"news"|"personal"|"local_news"|"rss"|"substack"
    contact_hint: str | None     # LinkedIn URL, email format guess, or None
    favorited: bool              # default False
    vote: int                    # -1 (down), 0 (neutral), 1 (up); default 0
    matched_interests: str       # JSON string of InterestConfig IDs e.g. "[1, 3]"
    created_at: datetime         # UTC
```

Up to 3 leads are stored per day. The uniqueness constraint is `UNIQUE(date, rank)`, not `UNIQUE(date)`.

### InterestConfig (`models/interest_config.py`)
```python
class InterestConfig(Base):
    id: int
    keyword: str                 # e.g. "urban planning", "computational biology"
    weight: float                # 0.0–1.0, used in scoring
    active: bool
    created_at: datetime         # UTC
```

### ScraperSource (`models/scraper_source.py`)
```python
class ScraperSource(Base):
    id: int
    name: str                    # Human-readable, e.g. "MIT Faculty Directory"
    scraper_class: str           # Dotted import path
    config: str                  # JSON (see example below)
    enabled: bool
    last_run_at: datetime | None # UTC
    last_run_status: str | None  # "success" | "error" | "skipped"
```

#### Example `ScraperSource.config`
```json
{
  "seed_urls": [
    "https://example.edu/faculty",
    "https://example.edu/faculty?page=2"
  ],
  "selectors": {
    "profile_link": "a.faculty-card",
    "name": "h2.name",
    "title": "span.title",
    "affiliation": "span.department"
  },
  "pagination": {
    "type": "next_link",
    "selector": "a.next-page",
    "max_pages": 5
  },
  "requires_js": false
}
```

### CandidateLead (dataclass — `scrapers/base.py`)
```python
@dataclass
class CandidateLead:
    name: str
    title: str
    affiliation: str
    url: str
    raw_text: str                # Used for scoring; discarded after selection
    source_type: SourceType      # Literal type
    contact_hint: str | None = None

SourceType = Literal["university", "company", "news", "personal", "local_news", "rss", "substack"]
```

### Lead Field Generation

| Field | Source |
|-------|--------|
| `summary` | `lead_service.generate_summary()` — first 2 sentences containing person's name. Agentic pipeline: Card Writer agent writes a structured summary from `VerifiedLeadBundle`. |
| `contact_hint` | Extracted by scraper (classic) or from `VerifiedLeadBundle.contact_paths` (agentic). Falls back to `None`. |
| `matched_interests` | JSON array of `InterestConfig` IDs whose keywords matched during scoring. Used by voting to adjust weights. |

## Environment Variables

Required (read via `pydantic-settings`):
```
DATABASE_URL=sqlite:///./oad.db
CORS_ORIGINS=http://localhost:5173
LOG_LEVEL=INFO
SCRAPE_RATE_LIMIT_SECONDS=2
SCRAPER_USER_AGENT=OneADay/1.0 (+https://yoursite.com/bot-info)
PIPELINE_MODE=agentic           # "agentic" (default) | "classic" (legacy scraper pipeline)
```

Required for agentic pipeline:
```
OPENROUTER_API_KEY=             # Used by planner, query_builder, card_writer agents (free tier works)
GEMINI_API_KEY=                 # Used by verifier_extractor agent (free tier works)
```

Optional:
```
SENTRY_DSN=                     # Error tracking (production)
```

## Error Handling

### Exception Hierarchy
```python
# app/exceptions.py
class OADError(Exception):
    """Base exception for all domain errors."""

class LeadExistsError(OADError):
    """Raised when attempting to create a lead for a date that already has one."""

class SourceNotFoundError(OADError):
    """Raised when a ScraperSource ID doesn't exist."""

class ScraperError(OADError):
    """Raised when a scraper fails (HTTP error, parse error, timeout)."""
```

### Layer Responsibilities

| Layer | Raises | Catches |
|-------|--------|---------|
| Scrapers | `ScraperError` | Nothing (let it bubble) |
| `scrape_service` | Nothing | `ScraperError` (log, continue to next source) |
| `lead_service` | `LeadExistsError`, `SourceNotFoundError` | Nothing |
| Routers | `HTTPException` | Domain exceptions → translate to HTTP status |

### Router Error Translation
```python
@router.post("/leads/generate", status_code=201)
def generate_lead(db: Session = Depends(get_db)):
    try:
        candidates = scrape_service.run_all_scrapers(db)
        interests = lead_service.get_active_interests(db)
        top = lead_service.select_top_candidates(candidates, interests, n=3)
        return lead_service.create_leads_from_candidates(db, top, interests)
    except LeadExistsError:
        raise HTTPException(status_code=409, detail="Lead already exists for today")
```

### Frontend Error Handling

- TanStack Query handles errors via `error` property
- No try/catch around API calls in components
- Display error state using query's `isError` and `error`

## Logging

### Configuration

- Library: `structlog`
- Logger per module: `logger = structlog.get_logger(__name__)`
- Format: JSON in production, console in development

### Levels

| Level | Use Case | Example |
|-------|----------|---------|
| DEBUG | Detailed flow, individual fetches | `logger.debug("fetching", url=url)` |
| INFO | Scraper start/end, lead selection, API requests | `logger.info("scraper_complete", source=name, candidates=10)` |
| WARNING | Parse failures, missing elements, retries | `logger.warning("selector_miss", selector=sel)` |
| ERROR | Unrecoverable failures | `logger.error("scraper_failed", exc_info=True)` |

### Rules

- Always bind context: `logger.info("event", key=value)`
- Never log PII (emails, phone numbers, addresses)
- Scraper logs must include `source_name`

## Ethical Scraping

### robots.txt

- `BaseScraper._get()` checks `robotparser` before fetching
- Disallowed URLs are skipped with a DEBUG log
- Cache parsed `robots.txt` per domain for session duration

### User-Agent

- Set in `BaseScraper._get()`: value from `SCRAPER_USER_AGENT` env var
- Default: `OneADay/1.0 (+https://yoursite.com/bot-info)`

### Rate Limiting

- Minimum delay between requests to same domain: `SCRAPE_RATE_LIMIT_SECONDS` (default 2s)
- Enforced in `BaseScraper._get()` via per-domain timestamp tracking
- Never bypass in development

## Key Design Patterns

### BaseScraper Interface
```python
class BaseScraper(ABC):
    source_name: str

    @abstractmethod
    def fetch_candidates(self, config: dict) -> list[CandidateLead]:
        """Return candidates. Must use self._get() for HTTP."""
        ...

    def _get(self, url: str) -> BeautifulSoup:
        """Rate-limited, robots.txt-respecting HTTP GET. Raises ScraperError on failure."""
        ...
```

### Scoring
```python
def score_candidate(candidate: CandidateLead, interests: list[InterestConfig]) -> float:
    """Returns 0–100. Keyword overlap weighted by interest.weight."""
```

Classic pipeline scoring: keyword overlap against active interests, weighted 0–1.

Agentic pipeline scoring: Card Writer produces a `ScoringCard` with six explicit dimensions — relevance, novelty, authority, reachability, timeliness, diversity — summed to a 0–100 total.

**Voting feedback loop**: Upvoting a lead (`vote=1`) adds `+0.1` to each matched interest's weight (clamped to 1.0). Downvoting (`vote=-1`) subtracts `0.1` (clamped to 0.0). Matched interest IDs are stored in `Lead.matched_interests` as a JSON array and adjusted in `PATCH /api/v1/leads/{id}/vote`.

### Thin Routers

Routers: validate → call service → return schema. No ORM queries. No business logic.

### API Response Shapes

- List: `{ "items": [...], "total": 42 }`
- Single: flat object
- Error: `{ "detail": "message" }`

### API Reference — Leads

| Method | Path | Description | Status codes |
|--------|------|-------------|-------------|
| GET | `/api/v1/leads/today` | Today's rank-1 lead | 200, 404 |
| GET | `/api/v1/leads/by-date/{date}` | All leads for YYYY-MM-DD, ordered by rank; `[]` if none | 200 |
| GET | `/api/v1/leads?skip&limit&source_type` | Paginated list, newest first | 200 |
| GET | `/api/v1/leads/{id}` | Single lead by ID | 200, 404 |
| POST | `/api/v1/leads/generate` | Trigger pipeline for today; returns up to 3 leads | 201, 409, 422 |
| PATCH | `/api/v1/leads/{id}/vote` | `{vote: -1|0|1}`; adjusts matched interest weights ±0.1 | 200, 404, 422 |
| PATCH | `/api/v1/leads/{id}/favorite` | `{favorited: bool}` | 200, 404 |

## Agent Contracts

Agent IO is defined in `config/agents.yaml` and will be validated by `app/schemas/agent_contracts.py` (Phase 1).

| Agent | Output schema | Key rule |
|-------|--------------|----------|
| Planner | `DailyRunPlan` | Choose source packs + constraints for today |
| Query Builder | `CandidateQueryPack` | Structured queries only — no prose |
| Verifier/Extractor | `VerifiedLeadBundle` | Every fact must carry `{url, excerpt}` — omit unverifiable facts |
| Card Writer | `ScoringCard` | Use only `VerifiedLeadBundle.facts` — no outreach copy |
| Selector | deterministic | Apply score breakdown + diversity constraints (`max_per_org`, `min_topic_clusters`) |

**`VerifiedLeadBundle`** fields: `identity {name, role, org}`, `urls[]`, `facts[{fact, url, excerpt}]`, `contact_paths[{type, url, excerpt}]`

**`ScoringCard`** score breakdown: `relevance`, `novelty`, `authority`, `reachability`, `timeliness`, `diversity` (each 0–100, summed to total)

LLM models are assigned per role in `config/models.yaml`:
- `planner`: `arcee-ai/trinity-large-preview:free` via OpenRouter
- `writer`: `meta-llama/llama-3.3-70b-instruct:free` via OpenRouter
- `cheap` (query builder): `liquid/lfm-2.5-1.2b-thinking:free` via OpenRouter
- `verifier`: `gemini-2.5-flash-lite` via Gemini

## Important Constraints

- **Never commit `.env`** or files containing secrets
- **Never call HTTP directly in scrapers** — use `self._get()`
- **Never bypass rate limiting** or robots.txt
- **Never store >3 leads per day** — unique constraint on `(Lead.date, Lead.rank)`; ranks 1–3 only
- **Evidence gating**: Verifier agent must omit any fact it cannot support with a source URL and verbatim excerpt — never fabricate
- **Never store raw HTML** or full page text in DB
- **Never store excess PII** — name, title, affiliation, URL, contact hint only
- **Never access DB inside scrapers** — stateless, config in, dataclasses out
- **Never put ORM/logic in routers** — routers call services only
- **Never use Playwright/Selenium** unless JS required (document in config)
- **Never log PII** at any level
- **Never add deps** without updating `pyproject.toml` / `package.json`
- **Never push to main** — use branches
- **All datetimes UTC** in database
- **Scheduler must be idempotent** — check for existing lead before running
- **`PIPELINE_MODE`**: set to `classic` only for local testing without LLM keys; `agentic` is the production default

## Production Checklist

Items to complete before the app is production-ready. Check off as you go.

### Database
| Item | Status |
|------|--------|
| Generate initial Alembic migration (`alembic revision --autogenerate -m "initial schema"`) | ✅ |
| Run migration on prod DB (`alembic upgrade head`) | ⬜ |
| Consider Postgres for multi-user / high-volume (SQLite fine for single-user) | ⬜ optional |

### Backend Config
| Item | Status |
|------|--------|
| Create `.env.example` (template of all env vars, no secrets) | ✅ |
| Set `SCRAPER_USER_AGENT` to a real domain with bot info URL | ⬜ |
| Set `CORS_ORIGINS` to your actual frontend origin | ⬜ |
| Set `LOG_LEVEL=INFO` in production | ⬜ |

### Agentic Pipeline
| Item | Status |
|------|--------|
| Add `config/models.yaml` and `config/agents.yaml` | ✅ |
| Implement `backend/app/agents/` (planner, query_builder, verifier_extractor, card_writer) | ⬜ Phase 1 |
| Implement `backend/app/llm/` (openrouter_client, gemini_client) | ⬜ Phase 1 |
| Add `backend/app/schemas/agent_contracts.py` (Pydantic IO validation) | ⬜ Phase 1 |
| Implement `backend/app/services/agentic_pipeline_service.py` orchestrator | ⬜ Phase 2 |
| Wire `PIPELINE_MODE` feature flag into scheduler | ⬜ Phase 2 |
| Add evidence-gating contract tests | ⬜ Phase 6 |

### Pre-commit & CI
| Item | Status |
|------|--------|
| Create `.pre-commit-config.yaml` (ruff + detect-secrets) | ✅ |
| Run `pre-commit install` after cloning | ⬜ |
| Confirm CI passes: `pytest --cov-fail-under=80`, `ruff check`, `npm run test`, `npm run lint` | ⬜ |

### Scheduler
| Item | Status |
|------|--------|
| Set up cron job or systemd timer: `0 6 * * * python -m scheduler.daily_job` | ⬜ |
| Add initial `ScraperSource` rows (seed data script or Alembic data migration) | ⬜ |
| Verify `--force` flag works for manual re-runs | ⬜ |

### Frontend
| Item | Status |
|------|--------|
| Drop design file in `frontend/DESIGN.md` and implement UI | ✅ |
| Add error boundaries around Dashboard, History, Settings, Algorithm | ⬜ |
| Run `npm run build` — confirm clean TypeScript + Vite build | ⬜ |
| Decide on serving: FastAPI `StaticFiles` mount or separate CDN | ⬜ |

### Auth & Security
| Item | Status |
|------|--------|
| Add HTTP Basic Auth or network-level restriction (e.g. Tailscale) before exposing publicly | ⬜ |
| Set `Secure` + `HttpOnly` cookie flags if sessions are added | ⬜ |

### Monitoring (optional)
| Item | Status |
|------|--------|
| Set `SENTRY_DSN` in `.env` — Sentry SDK already in config | ⬜ optional |
| Add structured log aggregation (e.g. Papertrail, Loki) | ⬜ optional |

### Ops (optional)
| Item | Status |
|------|--------|
| Create `docker-compose.yml` for local + prod parity | ⬜ optional |
| Add `robots.txt` for the app itself | ⬜ optional |
| Set up automated daily backup of `oad.db` | ⬜ optional |