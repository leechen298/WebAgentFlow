from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.exploration_run import ExplorationMode, ExplorationRunStatus


class ExplorationRunBase(BaseModel):
    page_signature: str | None = Field(default=None, max_length=512)
    mode: ExplorationMode = ExplorationMode.FORM
    status: ExplorationRunStatus = ExplorationRunStatus.PENDING
    success_criteria_ids_json: list[str] = Field(default_factory=list)
    strategy_json: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None
    result_snapshot_json: dict[str, Any] | None = None
    candidate_elements_json: list[dict[str, Any]] | None = None
    interaction_hints_json: list[dict[str, Any]] | None = None


class ExplorationRunCreate(ExplorationRunBase):
    pass


class ExplorationRunUpdate(BaseModel):
    page_signature: str | None = Field(default=None, max_length=512)
    mode: ExplorationMode | None = None
    status: ExplorationRunStatus | None = None
    success_criteria_ids_json: list[str] | None = None
    strategy_json: dict[str, Any] | None = None
    summary: str | None = None
    result_snapshot_json: dict[str, Any] | None = None
    candidate_elements_json: list[dict[str, Any]] | None = None
    interaction_hints_json: list[dict[str, Any]] | None = None


class ExplorationRunRead(ExplorationRunBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
