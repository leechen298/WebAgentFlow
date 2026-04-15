from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.candidate_feedback import FeedbackJudgment


class CandidateFeedbackBase(BaseModel):
    recording_id: str = Field(max_length=36)
    run_id: str | None = Field(default=None, max_length=36)
    element_key: str = Field(max_length=512)
    judgment: FeedbackJudgment
    comment: str | None = None
    candidate_score: float | None = None
    inferred_actions_json: list[str] | None = None
    evidence_json: dict[str, Any] | None = None


class CandidateFeedbackCreate(CandidateFeedbackBase):
    pass


class CandidateFeedbackUpdate(BaseModel):
    judgment: FeedbackJudgment | None = None
    comment: str | None = None
    candidate_score: float | None = None
    inferred_actions_json: list[str] | None = None
    evidence_json: dict[str, Any] | None = None


class CandidateFeedbackRead(CandidateFeedbackBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
