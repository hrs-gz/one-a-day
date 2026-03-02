# One-A-Day

A web scraping tool that surfaces one curated contact lead per day — interesting people (academics, professionals, researchers, local operators) discovered across university pages, company sites, news headlines, personal websites, and local newspapers.

You configure your interests through a web dashboard. A daily scheduled job scrapes configured sources, scores candidates against your interests, picks the single best lead, and stores it. The dashboard shows today's lead and a browsable history of past leads.

See [CLAUDE.md](./CLAUDE.md) for full architecture, data models, conventions, and development workflow.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+

### Backend

```bash
cd backend
pip install -e ".[dev]"
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

### Run the scraper manually

```bash
# From backend/
python -m scheduler.daily_job --force
```


## Agentic roadmap

A proposed agentic architecture plan and starter configuration files are included:

- `docs/agentic-architecture-plan.md`
- `config/models.yaml`
- `config/agents.yaml`

These provide a phased migration path from the current deterministic pipeline to an evidence-gated agentic pipeline.

## GitHub Codespaces

This repo now includes `.devcontainer/devcontainer.json` for quick startup in Codespaces with Python 3.11 + Node 20 and preconfigured forwarded ports (`8000`, `5173`).

## Architecture

```
[Scheduler / daily_job.py]
        |
        v
[Scrape Service]  -->  [Scraper Modules (pluggable)]
        |
        v
[Lead Service]  -->  score + select best lead against your interests
        |
        v
[SQLite DB]  -->  [FastAPI Backend]  -->  [React Dashboard]
```

## Features

- **Interest-Based Scraping**: Configure topics and keywords through the dashboard — scrapers use them to find relevant people
- **Daily Lead**: One curated contact per day, selected by scoring candidates against your interests
- **Multi-Source**: Pluggable scrapers for university faculty pages, company about pages, news headlines, personal sites, local newspapers
- **Browsable History**: Dashboard shows today's lead and all past leads
- **Scraper Management**: Enable/disable sources and configure them through the Settings page
