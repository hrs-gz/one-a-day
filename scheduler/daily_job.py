from __future__ import annotations

"""Daily job: scrape all enabled sources, score candidates, and persist today's lead.

Usage:
    python -m scheduler.daily_job              # Normal run — skips if lead exists
    python -m scheduler.daily_job --force      # Force run even if lead exists
"""

import argparse
import sys
from datetime import date

import structlog

# Ensure backend app is importable when run from project root
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.config import settings
from app.database import SessionLocal
from app.exceptions import LeadExistsError
from app.services import lead_service, scrape_service

logger = structlog.get_logger(__name__)


def run(force: bool = False) -> None:
    """Run the daily scrape-and-select pipeline.

    Args:
        force: If True, ignore an existing lead for today and re-run.
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
            db.delete(existing)
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
    parser = argparse.ArgumentParser(description="One-A-Day daily scrape job")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run even if a lead already exists for today",
    )
    args = parser.parse_args()
    run(force=args.force)


if __name__ == "__main__":
    main()
