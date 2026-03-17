from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.run import RunStatus


class RunBase(BaseModel):
    skill_id: str = Field(min_length=1, max_length=36)
    status: RunStatus = RunStatus.PENDING
    input_payload: dict[str, Any] | list[Any]
    result_payload: dict[str, Any] | list[Any] | None = None
    logs: list[dict[str, Any]] | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class RunCreate(RunBase):
    pass


class RunUpdate(BaseModel):
    skill_id: str | None = Field(default=None, min_length=1, max_length=36)
    status: RunStatus | None = None
    input_payload: dict[str, Any] | list[Any] | None = None
    result_payload: dict[str, Any] | list[Any] | None = None
    logs: list[dict[str, Any]] | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class RunRead(RunBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
