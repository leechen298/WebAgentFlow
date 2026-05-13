"""M11.0 runtime conversation domain schemas.

These contracts are pure API/domain shapes for session state, messages,
events, slash commands, and state transition decisions. They intentionally do
not define persistence, API routes, replay execution, or LLM behavior.

API request/response schemas added in 11.0.3 are suffix-tagged with
*Request / *Response to distinguish them from the pure domain models.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ConversationStatus(StrEnum):
    IDLE = "idle"
    TASK_INTAKE = "task_intake"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    PLAN_CONFIRMED = "plan_confirmed"
    EXECUTING = "executing"
    EXECUTION_FINISHED = "execution_finished"
    EXECUTION_FAILED = "execution_failed"
    REPLAY_REQUESTED = "replay_requested"
    REPLAY_RUNNING = "replay_running"
    PAUSED = "paused"
    ABORT_REQUESTED = "abort_requested"
    TAKEOVER_REQUESTED = "takeover_requested"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversationRole(StrEnum):
    USER = "user"
    SYSTEM = "system"
    AGENT = "agent"
    ENGINE = "engine"


class ConversationEventType(StrEnum):
    SESSION_CREATED = "session_created"
    MESSAGE_RECEIVED = "message_received"
    COMMAND_PARSED = "command_parsed"
    STATE_CHANGED = "state_changed"
    REPLAY_REQUESTED = "replay_requested"
    REPLAY_COMPLETED = "replay_completed"
    REPLAY_FAILED = "replay_failed"
    PAUSE_REQUESTED = "pause_requested"
    RESUME_REQUESTED = "resume_requested"
    ABORT_REQUESTED = "abort_requested"
    TAKEOVER_REQUESTED = "takeover_requested"
    PLAN_PREVIEW_PROPOSED = "plan_preview_proposed"
    PLAN_PREVIEW_UNABLE = "plan_preview_unable"
    PLAN_CONFIRMED = "plan_confirmed"
    PLAN_CANCELLED = "plan_cancelled"
    PLAN_REJECTED = "plan_rejected"
    CONFIRMATION_CLARIFICATION_REQUESTED = (
        "confirmation_clarification_requested"
    )
    EXPLICIT_REPLAY_BLOCKED_BY_PENDING_CONFIRMATION = (
        "explicit_replay_blocked_by_pending_confirmation"
    )
    PLAN_EXECUTION_STARTED = "plan_execution_started"
    PLAN_EXECUTION_COMPLETED = "plan_execution_completed"
    PLAN_EXECUTION_FAILED = "plan_execution_failed"
    PLAN_EXECUTION_BLOCKED = "plan_execution_blocked"
    SESSION_COMPLETED = "session_completed"
    SESSION_FAILED = "session_failed"


class ConversationCommandKind(StrEnum):
    STATUS = "status"
    CANCEL = "cancel"
    PAUSE = "pause"
    RESUME = "resume"
    ABORT = "abort"
    TAKEOVER = "takeover"
    REPLAY = "replay"
    FREE_TEXT = "free_text"
    ERROR = "error"


class ConversationCommand(BaseModel):
    kind: ConversationCommandKind
    raw: str
    args: list[str] = Field(default_factory=list)
    learned_path_id: str | None = None
    url: str | None = None
    text: str | None = None
    error: str | None = None


class ConversationTransitionResult(BaseModel):
    next_status: ConversationStatus
    response_hint: str
    event_type: ConversationEventType
    allowed: bool
    error: str | None = None


class ConversationSession(BaseModel):
    id: str
    status: ConversationStatus = ConversationStatus.IDLE
    current_mode: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationMessage(BaseModel):
    id: str
    session_id: str
    role: ConversationRole
    content: str
    created_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationEvent(BaseModel):
    id: str
    session_id: str
    type: ConversationEventType
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# 11.0.3 API request / response schemas
# ---------------------------------------------------------------------------

PublicConversationMessageRole = Literal["user", "system", "engine"]


class ConversationSessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_mode: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationSessionResponse(BaseModel):
    id: str
    status: ConversationStatus
    current_mode: str | None = None
    previous_status: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConversationMessageCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: PublicConversationMessageRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationMessageResponse(BaseModel):
    id: str
    session_id: str
    role: ConversationRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class ConversationEventCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ConversationEventType
    payload: dict[str, Any] = Field(default_factory=dict)


class ConversationEventResponse(BaseModel):
    id: str
    session_id: str
    type: ConversationEventType
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# 11.0.6 Dispatch request / response schemas
# ---------------------------------------------------------------------------


class ConversationReplaySummary(BaseModel):
    """Summary of a LearnedPath replay outcome surfaced on the dispatch response."""

    learned_path_id: str
    url: str
    replay_status: str
    drift_status: str
    drift_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    final_url: str | None = None
    final_title: str | None = None
    step_count: int = 0
    error: str | None = None


class ConversationDispatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationDispatchResponse(BaseModel):
    session_id: str
    previous_status: str
    next_status: str
    command_kind: str
    user_response: str
    events_appended: list[str] = Field(default_factory=list)
    message_id: str | None = None
    allowed: bool
    error: str | None = None
    replay_result: ConversationReplaySummary | None = None
