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


# ---------------------------------------------------------------------------
# Operation Step schemas — event → mutation correlation
#
# Phase 5 boundary: The Step layer is a lightweight event → DOM-change
# organizer. It correlates user events with subsequent mutations using
# simple time-window rules. It is NOT:
#   - A causal inference engine
#   - An execution decision layer
#   - A path template or replay strategy layer
# See step_builder.py module docstring for the full boundary statement.
# ---------------------------------------------------------------------------

class StepMutationSummary(BaseModel):
    """Mutation summary for a single step.

    Agent-core fields: total, by_type
    Debug/context fields: mutation_ids, highlights
    """

    total: int = 0
    by_type: dict[str, int] = Field(default_factory=lambda: {"childList": 0, "attributes": 0, "characterData": 0})
    # --- Debug / context ---
    mutation_ids: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)


class OperationStep(BaseModel):
    """A single operation step: one user event + its correlated DOM mutations.

    Field classification for downstream consumers:

    **Agent-core** — fields an Agent should rely on to understand what
    happened and decide what to do next:
      - event_type, event_target_summary, has_changes,
        mutations.total, mutations.by_type, change_area, summary

    **Debug / context** — useful for visualization, tracing, and debugging
    but not part of the stable Agent input contract:
      - id, timestamp, end_timestamp, url, frame_info,
        event_index, event_ast_match, mutations.mutation_ids,
        mutations.highlights
    """

    # --- Debug / context ---
    id: str
    timestamp: int
    end_timestamp: int
    url: str
    frame_info: dict[str, Any] | None = None

    # --- Agent-core: event ---
    event_index: int  # debug, but needed for cross-referencing raw events
    event_type: str
    event_target_summary: str

    # --- Debug / context ---
    event_ast_match: dict[str, Any] | None = None

    # --- Agent-core: mutations ---
    mutations: StepMutationSummary = Field(default_factory=StepMutationSummary)

    # --- Agent-core: outcome ---
    has_changes: bool = False
    change_area: str | None = None
    summary: str = ""


class OperationStepResult(BaseModel):
    recording_id: str
    steps: list[OperationStep] = Field(default_factory=list)
    event_count: int = 0
    mutation_count: int = 0
    mutations_correlated: int = 0
    mutations_uncorrelated: int = 0


# ---------------------------------------------------------------------------
# Agent-ready Step view — lightweight projection for Agent consumption
#
# Strips debug fields, flattens mutation stats, and provides a stable
# contract that downstream Agent phases (6+) can depend on.
# ---------------------------------------------------------------------------

class AgentStepView(BaseModel):
    """Stable, minimal representation of one step for Agent consumption.

    This is the primary input an Agent should use to understand a recorded
    user operation. All fields are considered part of the stable contract.
    """

    # What the user did
    event_type: str
    target: str  # human-readable target summary
    # What changed
    has_changes: bool
    mutation_total: int = 0
    mutation_types: dict[str, int] = Field(
        default_factory=lambda: {"childList": 0, "attributes": 0, "characterData": 0},
    )
    change_area: str | None = None
    # Human-readable summary (action → result format)
    summary: str = ""
    # No-change semantics: when has_changes is False, this field explains why.
    # Possible values:
    #   "no_mutations_observed" — default, no DOM mutations in the time window
    #   "navigate"             — navigation events are not expected to produce
    #                            mutations in the same document
    #
    # IMPORTANT: no-change does NOT mean failure. It may indicate:
    #   - The change happened outside the observation window
    #   - The change is in a different frame (cross-origin)
    #   - The action requires an async server round-trip
    #   - A precondition was not met (e.g. form validation blocked submit)
    #   - The action is genuinely a no-op (e.g. clicking an already-selected tab)
    # Downstream consumers must NOT treat no-change as an automatic failure.
    no_change_reason: str | None = None


class AgentStepListView(BaseModel):
    """Agent-ready projection of an entire recording's steps."""

    recording_id: str
    steps: list[AgentStepView] = Field(default_factory=list)
    step_count: int = 0
    has_mutations: bool = False


class NormalizedRecordingRead(BaseModel):
    recording_id: str
    summary: NormalizationSummary
    segments: list[NormalizedSegment]
    key_actions: list[NormalizedStep]
    initial_state: dict[str, Any] | None = None
