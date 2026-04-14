from __future__ import annotations

from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LearnedPathStatus(StrEnum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    REJECTED = "rejected"


class LearnedPath(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learned_paths"

    page_signature: Mapped[str | None] = mapped_column(String(512), nullable=True)
    goal_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    success_criteria_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("success_criteria.id", ondelete="SET NULL"),
        nullable=True,
    )
    steps_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    variable_slots_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    observed_effects_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    constraints_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    user_labels_json: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    recommended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[LearnedPathStatus] = mapped_column(
        String(32),
        default=LearnedPathStatus.CANDIDATE,
        nullable=False,
    )
