# Agentic Architecture Plan (One-a-Day)

## 1) Current-state codebase understanding

Today, One-a-Day already has a deterministic scrape → score → select pipeline:

- `scheduler/daily_job.py` runs daily, calls scrape service, scores candidates, and stores one winner.
- `backend/app/services/scrape_service.py` loads enabled scraper plugins and aggregates candidate leads.
- `backend/app/services/lead_service.py` performs interest-based scoring, deduplication, ranking, and persistence.
- FastAPI routers expose leads/interests/sources for the React dashboard.

This is a strong base for introducing an agentic pipeline without disrupting what currently works.

---

## 2) Review of the proposed “new approach”

Your proposed architecture is a good fit for the product direction because it introduces:

- **Evidence gating** (non-negotiable): every fact must include `source_url + excerpt`.
- **Separation of concerns** across agents (planner, query builder, verifier, card writer).
- **Deterministic selection and availability logic** to keep behavior auditable.
- **Cost-aware free-tier model strategy** with clear fallback behavior.

### Recommended adaptation for this repo

1. Keep existing deterministic scheduler/service skeleton.
2. Replace scraper output contract from “raw candidate text” to “verified evidence bundle”.
3. Introduce a composable agent runtime with strict schema validation.
4. Preserve current DB/API/UI flows, then extend schemas for evidence-first cards.

---

## 3) Target agentic pipeline

1. **Planner agent** chooses source packs and run constraints.
2. **Query builder agent** emits search query packs (structured only).
3. **Candidate gatherer** executes search requests and deduplicates URLs early.
4. **Verifier/extractor agent** fetches top-K pages and emits only verifiable facts.
5. **Card writer agent** renders scoring cards from verified facts only.
6. **Deterministic selector** applies score breakdown + diversity constraints to select top 1–3.
7. **Availability suggester** computes meeting windows from read-only calendar data.
8. **UI** presents Today / Lead Detail / History / Settings and flags hypotheses explicitly.

---

## 4) Delivery plan (phased)

### Phase 0: Foundations (safe scaffolding)

- Add `config/models.yaml` and `config/agents.yaml` as runtime-configurable contracts.
- Add provider abstractions (OpenAI-compatible + Gemini).
- Add schema validation layer (Pydantic) for all agent IO.

### Phase 1: Evidence-first data model

- Add new entities for:
  - `LeadFact(fact, url, excerpt)`
  - `LeadQuestion(q, why, linked_fact_urls)`
  - `LeadResearchTask(task, expected_find)`
  - `LeadAvailabilityWindow(start, end, rationale)`
- Keep existing `Lead` table backward compatible during migration.

### Phase 2: Agent runtime in scheduler

- Replace single `select_winner` path in `scheduler/daily_job.py` with a step-wise orchestrator:
  - plan → query → gather → verify → write → deterministic select → persist.
- Add retries, exponential backoff, and provider fallback for 429/timeouts.
- Cache fetched pages with TTL by source category.

### Phase 3: Deterministic selector + diversity

- Move score calculation into explicit weighted dimensions:
  - relevance, novelty, authority, reachability, timeliness, diversity.
- Add constraints like `max_per_org` and `min_topic_clusters` from plan config.

### Phase 4: Availability suggestions

- Integrate read-only calendar free/busy endpoint.
- Emit suggested windows and rationale; avoid booking side effects.

### Phase 5: UI contract upgrade

- Add card detail components for evidence, questions, and research tasks.
- Add badges:
  - “Verified fact” (has url+excerpt)
  - “Hypothesis / to verify” (explicitly non-factual)

### Phase 6: Hardening

- Contract tests for each agent schema.
- Golden tests for deterministic selector outputs.
- End-to-end daily job replay tests with fixed fixtures.

---

## 5) Codespaces-first development plan

Use GitHub Codespaces as the default environment to speed onboarding and keep backend/frontend aligned.

- Include a `.devcontainer/devcontainer.json` with Python + Node features.
- Auto-install backend/frontend dependencies in `postCreateCommand`.
- Forward ports:
  - `8000` backend API
  - `5173` frontend dev server
- Keep secrets in Codespaces secrets:
  - `OPENROUTER_API_KEY`
  - `GEMINI_API_KEY`
  - optional search/calendar keys

---

## 6) Immediate next implementation tasks (agentic MVP)

1. Add `backend/app/agents/` package with interfaces:
   - `planner.py`, `query_builder.py`, `verifier_extractor.py`, `card_writer.py`.
2. Add `backend/app/llm/` provider clients:
   - `openrouter_client.py`, `gemini_client.py`.
3. Add `backend/app/schemas/agent_contracts.py` for config/output validation.
4. Add `backend/app/services/agentic_pipeline_service.py` orchestrator.
5. Add feature flag:
   - `PIPELINE_MODE=classic|agentic` (default `classic` until parity achieved).
6. Add tests for:
   - evidence gating
   - fallback/retry behavior
   - deterministic selector constraints.

This sequence keeps the current app stable while progressively shipping the new architecture.
