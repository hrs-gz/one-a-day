from __future__ import annotations

import importlib
import json
from datetime import datetime

import structlog
from sqlalchemy.orm import Session

from app.exceptions import ScraperError
from app.models.scraper_source import ScraperSource
from app.scrapers.base import BaseScraper, CandidateLead

logger = structlog.get_logger(__name__)


def load_scraper(scraper_class: str) -> BaseScraper:
    """Dynamically import and instantiate a scraper class by dotted path.

    Args:
        scraper_class: Dotted module path,
            e.g. 'app.scrapers.university.UniversityScraper'.

    Returns:
        Instantiated BaseScraper subclass.

    Raises:
        ScraperError: If the class cannot be imported or instantiated.
    """
    try:
        module_path, class_name = scraper_class.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        return cls()
    except (ImportError, AttributeError, ValueError) as exc:
        raise ScraperError(
            f"Cannot load scraper class '{scraper_class}': {exc}"
        ) from exc


def run_all_scrapers(db: Session) -> list[CandidateLead]:
    """Run all enabled scrapers and collect candidates.

    Each scraper's errors are caught and logged independently —
    a failing scraper does not abort the pipeline.

    Args:
        db: Database session (used to fetch enabled ScraperSources).

    Returns:
        Aggregated list of CandidateLead from all scrapers.
    """
    sources = db.query(ScraperSource).filter(ScraperSource.enabled.is_(True)).all()

    if not sources:
        logger.warning("no_enabled_sources")
        return []

    logger.info("pipeline_start", source_count=len(sources))
    all_candidates: list[CandidateLead] = []

    for source in sources:
        logger.info("source_start", source_name=source.name)
        try:
            config = json.loads(source.config or "{}")
            scraper = load_scraper(source.scraper_class)
            candidates = scraper.fetch_candidates(config)
        except ScraperError as exc:
            logger.error(
                "source_failed",
                source_name=source.name,
                error=str(exc),
            )
            _update_source_status(db, source, "error")
            continue
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "source_unexpected_error",
                source_name=source.name,
                error=str(exc),
                exc_info=True,
            )
            _update_source_status(db, source, "error")
            continue

        all_candidates.extend(candidates)
        _update_source_status(db, source, "success")
        logger.info(
            "source_complete",
            source_name=source.name,
            candidates=len(candidates),
        )

    logger.info("pipeline_complete", total_candidates=len(all_candidates))
    return all_candidates


def _update_source_status(db: Session, source: ScraperSource, status: str) -> None:
    """Update last_run_at and last_run_status on a scraper source.

    Args:
        db: Database session.
        source: ScraperSource ORM object to update.
        status: 'success', 'error', or 'skipped'.
    """
    source.last_run_at = datetime.utcnow()
    source.last_run_status = status
    db.commit()
