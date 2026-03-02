from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScraperSourceBase(BaseModel):
    """Shared scraper source fields."""

    name: str
    scraper_class: str
    config: str = "{}"
    enabled: bool = True


class ScraperSourceCreate(ScraperSourceBase):
    """Schema for creating a scraper source."""


class ScraperSourceUpdate(BaseModel):
    """Schema for partially updating a scraper source."""

    name: str | None = None
    scraper_class: str | None = None
    config: str | None = None
    enabled: bool | None = None


class ScraperSourceSchema(ScraperSourceBase):
    """Full scraper source schema returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    last_run_at: datetime | None = None
    last_run_status: str | None = None


class ScraperSourceListSchema(BaseModel):
    """Paginated list of scraper sources."""

    items: list[ScraperSourceSchema]
    total: int
