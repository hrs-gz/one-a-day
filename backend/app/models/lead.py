from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Lead(Base):
    """A single curated contact lead selected for a given calendar day."""

    __tablename__ = "leads"
    __table_args__ = (UniqueConstraint("date", "rank", name="uq_lead_date_rank"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    affiliation: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    contact_hint: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    favorited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    vote: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    matched_interests: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )  # JSON string: "[1, 3, 7]"
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
