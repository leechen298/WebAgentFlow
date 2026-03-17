from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.recording import RecordingStatus


class RecordingBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    status: RecordingStatus = RecordingStatus.DRAFT
    source: str = Field(min_length=1, max_length=64)
    events: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] | None = None


class RecordingCreate(RecordingBase):
    pass


class RecordingUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: RecordingStatus | None = None
    source: str | None = Field(default=None, min_length=1, max_length=64)
    events: list[dict[str, Any]] | None = None
    meta: dict[str, Any] | None = None


class RecordingRead(RecordingBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
