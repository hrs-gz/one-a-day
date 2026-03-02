from __future__ import annotations

import json
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator


class LeadBase(BaseModel):
    """Shared lead fields."""

    name: str
    title: str
    affiliation: str
    url: str
    summary: str
    source_type: str
    contact_hint: str | None = None


class LeadCreate(LeadBase):
    """Schema for creating a lead (internal use)."""

    date: date


class LeadSchema(LeadBase):
    """Full lead schema returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    rank: int = 1
    favorited: bool = False
    vote: int = 0
    matched_interests: list[int] = []
    created_at: datetime

    @field_validator("matched_interests", mode="before")
    @classmethod
    def parse_matched_interests(cls, v: object) -> list[int]:
        """Deserialize JSON string from DB column to list[int]."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [int(x) for x in parsed]
            except (json.JSONDecodeError, ValueError):
                pass
            return []
        if isinstance(v, list):
            return [int(x) for x in v]
        return []


class LeadListSchema(BaseModel):
    """Paginated list of leads."""

    items: list[LeadSchema]
    total: int
