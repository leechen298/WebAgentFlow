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


# ---------------------------------------------------------------------------
# Normalized recording schemas (Task Pack 6)
# ---------------------------------------------------------------------------

class NormalizedStep(BaseModel):
    action_type: str
    timestamp: int
    url: str
    page_title: str | None = None
    field_label: str | None = None
    field_prop: str | None = None
    field_required: bool | None = None
    value: str | None = None
    button_text: str | None = None
    in_iframe: bool = False
    frame_url: str | None = None
    is_richtext: bool = False
    html_content: str | None = None
    raw_event_indices: list[int] = Field(default_factory=list)


class NormalizedSegment(BaseModel):
    index: int
    type: str
    title: str
    steps: list[NormalizedStep] = Field(default_factory=list)


class NormalizationSummary(BaseModel):
    event_count_raw: int
    event_count_normalized: int
    page_count: int
    segment_count: int
    contains_iframe: bool
    contains_richtext: bool


class NormalizedRecordingRead(BaseModel):
    recording_id: str
    summary: NormalizationSummary
    segments: list[NormalizedSegment]
    key_actions: list[NormalizedStep]
