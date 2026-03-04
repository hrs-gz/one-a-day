# One-A-Day

An agent-driven pipeline that surfaces up to 3 curated contact leads per day — interesting people (academics, professionals, researchers, local operators) discovered, verified, and ranked by a chain of LLM agents.

You configure your interests through a web dashboard. Each day, a scheduler runs the agentic pipeline: a Planner agent chooses sources, a Query Builder generates structured search queries, a Candidate Gatherer fetches and deduplicates URLs, a Verifier/Extractor agent extracts only evidence-backed facts (every fact carries a source URL and verbatim excerpt), a Card Writer scores each candidate, and a Deterministic Selector picks the top 1–3 leads. The dashboard shows today's ranked leads and a browsable history. Voting on a lead feeds back into your interest weights.

See [CLAUDE.md](./CLAUDE.md) for full architecture, data models, conventions, and development workflow.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- An [OpenRouter](https://openrouter.ai) API key (free tier works)
- A [Gemini](https://aistudio.google.com) API key (free tier works — used for the verifier agent)

### Backend

```bash
cd backend
pip install -e ".[dev]"
cd ..
cp .env.example .env        # then fill in OPENROUTER_API_KEY and GEMINI_API_KEY
cd backend
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: http://localhost:5173

### Run the pipeline manually

```bash
# From repo root (not backend/)
python -m scheduler.daily_job --force
```

### Pre-commit hooks (after cloning)

```bash
pre-commit install
```

---

## Architecture

```
[Scheduler / daily_job.py]
        |
        v
[Agentic Pipeline Service]
        |
        +---> [Planner Agent]            → DailyRunPlan (source packs, constraints)
        +---> [Query Builder Agent]      → CandidateQueryPack (structured search queries)
        +---> [Candidate Gatherer]       → deduplicated URLs
        +---> [Verifier/Extractor Agent] → VerifiedLeadBundle (facts w/ url+excerpt)
        +---> [Card Writer Agent]        → ScoringCard (relevance, novelty, authority…)
        +---> [Deterministic Selector]   → top 1–3 ranked leads
        |
        v
[SQLite DB]  -->  [FastAPI Backend /api/v1/]  -->  [React Dashboard]
```

Classic scraper pipeline (BeautifulSoup + static selectors) is still available via `PIPELINE_MODE=classic` for local development without LLM keys.

---

## Features

- **Agent-driven discovery**: Planner + Query Builder agents dynamically choose what to search for each day based on your interests
- **Evidence-gated facts**: Verifier agent only emits facts with a source URL and verbatim excerpt — no hallucinations
- **3 ranked leads per day**: Card Writer + Deterministic Selector produce rank-1/2/3 leads with score breakdowns (relevance, novelty, authority, reachability, timeliness, diversity)
- **Voting feedback loop**: Thumbs up/down on a lead adjusts the weights of matched interests (±0.1, clamped 0–1)
- **Favorites**: Pin leads for later reference
- **Algorithm page**: Tag cloud visualization of interests + natural language input to bulk-add interests
- **Classic fallback**: Set `PIPELINE_MODE=classic` to use the original BeautifulSoup scraper pipeline without LLM keys

---

## Agentic Pipeline

The agentic architecture is the primary production path. Configuration lives in:

- `config/models.yaml` — LLM provider definitions (OpenRouter + Gemini) and model assignments per agent role
- `config/agents.yaml` — Agent rules, IO schema contracts, and output validation
- `docs/agentic-architecture-plan.md` — Full phased delivery plan

**Current status:**
- Phase 0 (config scaffolding): done
- Phase 1–2 (agent runtime + scheduler integration): in progress

---

## GitHub Codespaces

This repo includes `.devcontainer/devcontainer.json` for quick startup in Codespaces with Python 3.11 + Node 20 and preconfigured forwarded ports (`8000`, `5173`). Store `OPENROUTER_API_KEY` and `GEMINI_API_KEY` as Codespaces secrets.
