from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.learned_path import LearnedPathStatus


class LearnedPathBase(BaseModel):
    page_signature: str | None = Field(default=None, max_length=512)
    goal_type: str | None = Field(default=None, max_length=64)
    success_criteria_id: str | None = None
    steps_json: list[dict[str, Any]] = Field(default_factory=list)
    variable_slots_json: list[dict[str, Any]] = Field(default_factory=list)
    observed_effects_json: list[dict[str, Any]] = Field(default_factory=list)
    constraints_json: list[dict[str, Any]] = Field(default_factory=list)
    user_labels_json: list[str] = Field(default_factory=list)
    recommended: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    status: LearnedPathStatus = LearnedPathStatus.CANDIDATE


class LearnedPathCreate(LearnedPathBase):
    pass


class LearnedPathUpdate(BaseModel):
    page_signature: str | None = Field(default=None, max_length=512)
    goal_type: str | None = Field(default=None, max_length=64)
    success_criteria_id: str | None = None
    steps_json: list[dict[str, Any]] | None = None
    variable_slots_json: list[dict[str, Any]] | None = None
    observed_effects_json: list[dict[str, Any]] | None = None
    constraints_json: list[dict[str, Any]] | None = None
    user_labels_json: list[str] | None = None
    recommended: bool | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    status: LearnedPathStatus | None = None


class LearnedPathRead(LearnedPathBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
