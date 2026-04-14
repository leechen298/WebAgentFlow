from __future__ import annotations

from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ExplorationMode(StrEnum):
    FORM = "form"
    SEARCH = "search"
    FILTER = "filter"
    MODAL = "modal"


class ExplorationRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class ExplorationRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "exploration_runs"

    page_signature: Mapped[str | None] = mapped_column(String(512), nullable=True)
    mode: Mapped[ExplorationMode] = mapped_column(
        String(32),
        default=ExplorationMode.FORM,
        nullable=False,
    )
    status: Mapped[ExplorationRunStatus] = mapped_column(
        String(32),
        default=ExplorationRunStatus.PENDING,
        nullable=False,
    )
    success_criteria_ids_json: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    strategy_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    # Reserved for interactive candidate element inference (Phase 2).
    # Stores elements identified from AST + mutation history as likely
    # interactive (clickable, inputtable, hoverable) with scores and evidence.
    candidate_elements_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True
    )
    # Reserved for interaction hints derived from candidate inference.
    # Stores prioritized exploration suggestions and inferred action types.
    interaction_hints_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True
    )
