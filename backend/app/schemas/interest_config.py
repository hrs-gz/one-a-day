from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InterestConfigBase(BaseModel):
    """Shared interest config fields."""

    keyword: str
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    active: bool = True


class InterestConfigCreate(InterestConfigBase):
    """Schema for creating an interest config."""


class InterestConfigUpdate(BaseModel):
    """Schema for partially updating an interest config."""

    keyword: str | None = None
    weight: float | None = Field(default=None, ge=0.0, le=1.0)
    active: bool | None = None


class InterestConfigSchema(InterestConfigBase):
    """Full interest config schema returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class InterestConfigListSchema(BaseModel):
    """Paginated list of interest configs."""

    items: list[InterestConfigSchema]
    total: int
