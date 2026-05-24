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

from app.schemas.conversation_entry_gate import ConversationEntryGateTrace
from app.schemas.learned_path_replay import ExecutionEvidence


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
    TASK_RESULT_REPORTED = "task_result_reported"
    CHAT_LEARNING_STARTED = "chat_learning_started"
    CHAT_LEARNING_COMPLETED = "chat_learning_completed"
    CHAT_LEARNING_FAILED = "chat_learning_failed"
    CHAT_EXECUTION_STARTED = "chat_execution_started"
    CHAT_EXECUTION_COMPLETED = "chat_execution_completed"
    CHAT_EXECUTION_FAILED = "chat_execution_failed"
    CHAT_NO_PATH = "chat_no_path"
    CHAT_PROGRESS_RECORDED = "chat_progress_recorded"
    AGENT_TRACE_RECORDED = "agent_trace_recorded"
    SKILL_CALL_RECORDED = "skill_call_recorded"
    LLM_TRACE_RECORDED = "llm_trace_recorded"
    ENTRY_GATE_RECORDED = "entry_gate_recorded"
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


class ConversationResponseSourceType(StrEnum):
    CODE = "code"
    AGENT = "agent"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class ConversationResponseProducerType(StrEnum):
    CODE = "code"
    AGENT = "agent"
    UNKNOWN = "unknown"


class ConversationResponseProducer(BaseModel):
    type: ConversationResponseProducerType
    id: str
    display_name: str
    internal_agent_role: str | None = None


class ConversationResponseProvenance(BaseModel):
    source_type: ConversationResponseSourceType
    producer: ConversationResponseProducer
    llm_trace_ids: list[str] = Field(default_factory=list)
    generated_from_event_ids: list[str] = Field(default_factory=list)
    fallback: bool = False


class ConversationLlmTraceResponse(BaseModel):
    trace_id: str
    purpose: str | None = None
    agent_role: str | None = None
    provider: str | None = None
    model: str | None = None
    request_id: str | None = None
    prompt_template_id: str | None = None
    prompt_hash: str | None = None
    schema_name: str | None = None
    schema_version: str | None = None
    validation: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    redaction: dict[str, Any] = Field(default_factory=dict)
    source_event_id: str | None = None
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
    response_provenance: ConversationResponseProvenance | None = None
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
    execution_evidence: list[ExecutionEvidence] = Field(default_factory=list)


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


# ---------------------------------------------------------------------------
# 11.3.2 Chat History & Debug Console read-model schemas
# ---------------------------------------------------------------------------


class ConversationSessionSummaryResponse(BaseModel):
    id: str
    status: ConversationStatus
    current_mode: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    message_count: int = 0
    event_count: int = 0
    last_user_message: str | None = None
    last_agent_message: str | None = None
    learned_action_count: int = 0
    learned_actions: list[dict[str, Any]] = Field(default_factory=list)


class ConversationSessionListResponse(BaseModel):
    items: list[ConversationSessionSummaryResponse] = Field(default_factory=list)


class ConversationLearningRunSummary(BaseModel):
    source_event_id: str
    source_event_type: str
    run_id: str | None = None
    learned_path_id: str | None = None
    status: str | None = None
    summary: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class ConversationReplayHistorySummary(BaseModel):
    source_event_id: str
    source_event_type: str
    learned_path_id: str | None = None
    run_id: str | None = None
    status: str | None = None
    summary: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class ConversationHistoryResponse(BaseModel):
    session: ConversationSessionResponse
    messages: list[ConversationMessageResponse] = Field(default_factory=list)
    events: list[ConversationEventResponse] = Field(default_factory=list)
    learned_actions: list[dict[str, Any]] = Field(default_factory=list)
    learning_runs: list[ConversationLearningRunSummary] = Field(default_factory=list)
    replay_summaries: list[ConversationReplayHistorySummary] = Field(default_factory=list)
    llm_traces: list[ConversationLlmTraceResponse] = Field(default_factory=list)
    entry_gate_traces: list[ConversationEntryGateTrace] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
