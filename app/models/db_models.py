"""
ORM Models — Validation History
=================================
Defines the database schema for persisting every validation result.
SQLAlchemy 2.0 mapped-column style with full type annotations.

Tables:
  validation_history — one row per /validate-chart call
"""

import json
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    """Registered users of the API."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ValidationHistory(Base):
    """Persisted record of a single chart validation call."""

    __tablename__ = "validation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Chart metadata ────────────────────────────────────────────────────
    chart_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    dataset_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    label_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_point_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Result ────────────────────────────────────────────────────────────
    score: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Dimension scores
    structure_score: Mapped[int] = mapped_column(Integer, nullable=False)
    objective_match_score: Mapped[int] = mapped_column(Integer, nullable=False)
    data_quality_score: Mapped[int] = mapped_column(Integer, nullable=False)
    viz_score: Mapped[int] = mapped_column(Integer, nullable=False)

    # Serialised lists (stored as JSON strings)
    issues_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    warnings_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    recommendations_json: Mapped[str] = mapped_column(
        Text, default="[]", nullable=False
    )

    # ── Audit ─────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Composite index for time-range queries on status
    __table_args__ = (
        Index("ix_validation_history_status_created", "status", "created_at"),
    )

    # ── Helpers ───────────────────────────────────────────────────────────
    @property
    def issues(self) -> list:
        return json.loads(self.issues_json)

    @property
    def warnings(self) -> list:
        return json.loads(self.warnings_json)

    @property
    def recommendations(self) -> list:
        return json.loads(self.recommendations_json)

    def __repr__(self) -> str:
        return (
            f"<ValidationHistory id={self.id} chart_type={self.chart_type!r} "
            f"score={self.score} status={self.status!r}>"
        )
