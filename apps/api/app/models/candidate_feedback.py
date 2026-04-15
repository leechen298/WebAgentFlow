from __future__ import annotations

from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FeedbackJudgment(StrEnum):
    REASONABLE = "reasonable"
    UNREASONABLE = "unreasonable"


class CandidateFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "candidate_feedbacks"

    recording_id: Mapped[str] = mapped_column(String(36), nullable=False)
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    element_key: Mapped[str] = mapped_column(String(512), nullable=False)
    judgment: Mapped[FeedbackJudgment] = mapped_column(String(16), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidate_score: Mapped[float | None] = mapped_column(nullable=True)
    inferred_actions_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    evidence_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
