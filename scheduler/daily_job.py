from __future__ import annotations

"""Daily job: run the lead pipeline and persist today's leads.

Supports two pipeline modes controlled by the ``PIPELINE_MODE`` env var:

- ``agentic`` (default): Planner → Query Builder → Candidate Gatherer →
  Verifier/Extractor → Card Writer → Deterministic Selector. Requires
  ``OPENROUTER_API_KEY`` and ``GEMINI_API_KEY``.
- ``classic``: Classic BeautifulSoup scraper pipeline
  (``scrape_service`` → ``lead_service``). Works without LLM keys.

Usage:
    python -m scheduler.daily_job              # Normal — skips if lead exists
    python -m scheduler.daily_job --force      # Force re-run
"""

import argparse
import os
import sys
from datetime import date

import structlog

# Ensure backend app is importable when run from project root
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.config import settings
from app.database import SessionLocal
from app.exceptions import LeadExistsError
from app.models.lead import Lead
from app.services import lead_service, scrape_service

logger = structlog.get_logger(__name__)


def _run_classic(db, today: date) -> None:
    """Run the classic BeautifulSoup scraper pipeline."""
    candidates = scrape_service.run_all_scrapers(db)
    if not candidates:
        logger.warning("no_candidates_found", date=str(today), mode="classic")
        return

    interests = lead_service.get_active_interests(db)
    winner = lead_service.select_winner(candidates, interests)
    if not winner:
        logger.warning("no_winner_selected", date=str(today), mode="classic")
        return

    lead = lead_service.create_lead_from_candidate(db, winner, interests)
    logger.info(
        "daily_job_complete",
        date=str(today),
        lead_id=lead.id,
        name=lead.name,
        source=lead.source_type,
        mode="classic",
    )


def _run_agentic(db, today: date) -> None:
    """Run the LLM-backed agentic pipeline."""
    if not settings.openrouter_api_key:
        logger.error(
            "agentic_pipeline_missing_key",
            missing="OPENROUTER_API_KEY",
            hint="Set OPENROUTER_API_KEY in .env or switch to PIPELINE_MODE=classic",
        )
        sys.exit(1)
    if not settings.gemini_api_key:
        logger.error(
            "agentic_pipeline_missing_key",
            missing="GEMINI_API_KEY",
            hint="Set GEMINI_API_KEY in .env or switch to PIPELINE_MODE=classic",
        )
        sys.exit(1)

    from app.services import agentic_pipeline_service

    leads = agentic_pipeline_service.run_agentic_pipeline(db)
    if not leads:
        logger.warning("agentic_pipeline_no_leads", date=str(today))
        return

    logger.info(
        "daily_job_complete",
        date=str(today),
        lead_count=len(leads),
        names=[lead.name for lead in leads],
        mode="agentic",
    )


def run(force: bool = False) -> None:
    """Run the daily pipeline.

    Args:
        force: If True, delete all existing leads for today and re-run.
    """
    db = SessionLocal()
    try:
        today = date.today()
        existing = lead_service.get_today_lead(db)

        if existing and not force:
            logger.info(
                "lead_already_exists",
                date=str(today),
                name=existing.name,
            )
            return

        if existing and force:
            logger.info("force_run_deleting_existing", date=str(today))
            # Delete all leads for today (up to 3 ranks)
            db.query(Lead).filter(Lead.date == today).delete()
            db.commit()

        logger.info(
            "daily_job_start",
            date=str(today),
            force=force,
            pipeline_mode=settings.pipeline_mode,
        )

        if settings.pipeline_mode == "agentic":
            from app.services.agentic_pipeline_service import (
                run_agentic_pipeline,
            )

            leads = run_agentic_pipeline(db)
            logger.info(
                "daily_job_complete",
                date=str(today),
                pipeline="agentic",
                leads_created=len(leads),
            )
            return

        # Classic pipeline (default)
        candidates = scrape_service.run_all_scrapers(db)
        if not candidates:
            logger.warning("no_candidates_found", date=str(today))
            return

        interests = lead_service.get_active_interests(db)
        winner = lead_service.select_winner(candidates, interests)

        if not winner:
            logger.warning("no_winner_selected", date=str(today))
            return

        lead = lead_service.create_lead_from_candidate(db, winner, interests)
        logger.info(
            "daily_job_complete",
            date=str(today),
            pipeline="classic",
            lead_id=lead.id,
            name=lead.name,
            source=lead.source_type,
        )

    except LeadExistsError:
        logger.warning("lead_exists_race_condition", date=str(date.today()))
    except Exception:
        logger.error("daily_job_failed", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


def main() -> None:
    """Entry point for the daily job."""
    parser = argparse.ArgumentParser(description="One-A-Day daily pipeline job")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run even if leads already exist for today",
    )
    args = parser.parse_args()
    run(force=args.force)


if __name__ == "__main__":
    main()
