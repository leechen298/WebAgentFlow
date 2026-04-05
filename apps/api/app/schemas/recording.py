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
# Initial state schemas (Task Pack 6.5)
# ---------------------------------------------------------------------------

class InitialFieldSnapshot(BaseModel):
    """Snapshot of one form field's state at recording start."""
    field_label: str | None = None
    field_path: str | None = None
    section_label: str | None = None
    field_prop: str | None = None
    field_type: str | None = None
    required: bool | None = None
    item_count: int | None = None
    default_value_text: str | None = None
    placeholder: str | None = None
    default_value_html: str | None = None


class PageInitialState(BaseModel):
    """Page initial state snapshot captured at recording start."""
    captured_at: int | None = None
    page_url: str | None = None
    page_title: str | None = None
    fields: list[InitialFieldSnapshot] = Field(default_factory=list)


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
    initial_state: dict[str, Any] | None = None
