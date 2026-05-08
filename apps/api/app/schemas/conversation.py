"""M11.0 runtime conversation domain schemas.

These contracts are pure API/domain shapes for session state, messages,
events, slash commands, and state transition decisions. They intentionally do
not define persistence, API routes, replay execution, or LLM behavior.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ConversationStatus(StrEnum):
    IDLE = "idle"
    TASK_INTAKE = "task_intake"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
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
