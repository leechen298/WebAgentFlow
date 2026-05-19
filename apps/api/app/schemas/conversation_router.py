"""M11.3.5 customer-facing Agent Router schemas."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RouteDecisionKind(StrEnum):
    ASK_USER = "ask_user"
    INSPECT_PAGE = "inspect_page"
    UNDERSTAND_PAGE = "understand_page"
    DELEGATE_TO_LEARNING_AGENT = "delegate_to_learning_agent"
    DELEGATE_TO_WEB_OPERATION_AGENT = "delegate_to_web_operation_agent"
    REPORT_UNKNOWN = "report_unknown"
    DECLINE_UNSUPPORTED = "decline_unsupported"


class RouterAgentRole(StrEnum):
    CONVERSATION_ORCHESTRATOR = "conversation_orchestrator"
    PAGE_UNDERSTANDING_AGENT = "page_understanding_agent"
    LEARNING_AGENT = "learning_agent"
    WEB_OPERATION_AGENT = "web_operation_agent"
    TASK_RESULT_REPORTER = "task_result_reporter"


class ApplicationSkillName(StrEnum):
    COLLECT_CONVERSATION_CONTEXT = "collect_conversation_context"
    INSPECT_TARGET_PAGE = "inspect_target_page"
    UNDERSTAND_PAGE = "understand_page"
    LOOKUP_LEARNED_ACTIONS = "lookup_learned_actions"
    ASK_USER_FOR_MISSING_INFO = "ask_user_for_missing_info"
    START_LEARNING = "start_learning"
    START_REPLAY = "start_replay"
    LEARN_THEN_EXECUTE = "learn_then_execute"
    RECORD_PROGRESS_EVENT = "record_progress_event"
    RECORD_AGENT_TRACE = "record_agent_trace"


class RouteTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str | None = None
    site_origin: str | None = None
    source: str | None = None


class RouteKnownContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    has_learned_action: bool = False
    has_required_user_inputs: bool = False
    page_context_available: bool = False


class RouteMissingField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    semantic_type: str
    display_name: str


class RouteDecision(BaseModel):
    """Schema-constrained Router recommendation.

    This schema is intentionally narrow. The Router may recommend a next
    component and skill, but it must not smuggle browser execution details or a
    LearnedPath authorization into the orchestration path.
    """

    model_config = ConfigDict(extra="forbid")

    route_decision: RouteDecisionKind
    next_agent: RouterAgentRole
    recommended_skill: ApplicationSkillName
    target: RouteTarget = Field(default_factory=RouteTarget)
    user_goal: str | None = None
    known_context: RouteKnownContext = Field(default_factory=RouteKnownContext)
    missing_fields: list[RouteMissingField] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason_summary: str = ""
    source: str = "deterministic"

    @model_validator(mode="after")
    def _reject_execution_authorization(self) -> RouteDecision:
        payload_text = self.model_dump_json(exclude_none=True)
        forbidden = (
            "selector",
            "target_selector",
            "playwright",
            "browser_action",
            "learned_path_id",
        )
        lowered = payload_text.lower()
        for token in forbidden:
            if token in lowered:
                raise ValueError(f"router output must not contain {token}")
        return self
