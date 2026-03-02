from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scraper_source import ScraperSource
from app.schemas.scraper_source import (
    ScraperSourceCreate,
    ScraperSourceListSchema,
    ScraperSourceSchema,
    ScraperSourceUpdate,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=ScraperSourceListSchema)
def list_sources(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ScraperSourceListSchema:
    """Return all scraper sources."""
    query = db.query(ScraperSource).order_by(ScraperSource.name)
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return ScraperSourceListSchema(items=items, total=total)  # type: ignore[arg-type]


@router.post("", response_model=ScraperSourceSchema, status_code=201)
def create_source(
    body: ScraperSourceCreate,
    db: Session = Depends(get_db),
) -> ScraperSourceSchema:
    """Create a new scraper source."""
    source = ScraperSource(**body.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    logger.info("source_created", name=source.name)
    return source  # type: ignore[return-value]


@router.get("/{source_id}", response_model=ScraperSourceSchema)
def get_source(source_id: int, db: Session = Depends(get_db)) -> ScraperSourceSchema:
    """Return a single scraper source by ID."""
    source = db.query(ScraperSource).filter(ScraperSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    return source  # type: ignore[return-value]


@router.patch("/{source_id}", response_model=ScraperSourceSchema)
def update_source(
    source_id: int,
    body: ScraperSourceUpdate,
    db: Session = Depends(get_db),
) -> ScraperSourceSchema:
    """Partially update a scraper source (e.g., toggle enabled)."""
    source = db.query(ScraperSource).filter(ScraperSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    db.commit()
    db.refresh(source)
    return source  # type: ignore[return-value]


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a scraper source."""
    source = db.query(ScraperSource).filter(ScraperSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found")
    db.delete(source)
    db.commit()
    logger.info("source_deleted", source_id=source_id)
