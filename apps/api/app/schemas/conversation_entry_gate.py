"""M11.3.5.1 conversation entry gate schemas."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConversationEntryGateCategory(StrEnum):
    WEB_TASK_CANDIDATE = "web_task_candidate"
    NON_WEB_CHAT = "non_web_chat"
    CAPABILITY_QUESTION = "capability_question"
    NEEDS_CLARIFICATION = "needs_clarification"
    UNSUPPORTED = "unsupported"


class ConversationEntryGateResult(BaseModel):
    """Low-latency relevance decision before Intake / Router.

    The gate only decides whether a message should enter the web-task runtime.
    It must not carry browser actions, selector-level details, or LearnedPath
    authorization material.
    """

    model_config = ConfigDict(extra="forbid")

    category: ConversationEntryGateCategory
    requires_agent_runtime: bool
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reply_hint: str | None = None
    reason_summary: str = ""
    latency_ms: int | None = Field(default=None, ge=0)
    provider: str | None = None
    model: str | None = None
    fallback: bool = False
    error_kind: str | None = None
    timeout_ms: int | None = Field(default=None, ge=1, le=2000)
    source: str = "deterministic"

    @model_validator(mode="after")
    def _reject_execution_authorization(self) -> ConversationEntryGateResult:
        payload_text = self.model_dump_json(exclude_none=True).lower()
        forbidden = (
            "selector",
            "target_selector",
            "dom path",
            "dom_path",
            "playwright",
            "browser_action",
            "browser steps",
            "learned_path_id",
        )
        for token in forbidden:
            if token in payload_text:
                raise ValueError(f"entry gate output must not contain {token}")
        return self

    @model_validator(mode="after")
    def _enforce_runtime_category_alignment(self) -> ConversationEntryGateResult:
        should_enter_runtime = (
            self.category == ConversationEntryGateCategory.WEB_TASK_CANDIDATE
        )
        if self.requires_agent_runtime != should_enter_runtime:
            raise ValueError(
                "requires_agent_runtime must be true only for web_task_candidate"
            )
        return self


class ConversationEntryGateTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_event_id: str
    category: ConversationEntryGateCategory
    requires_agent_runtime: bool
    skipped_intake_router: bool
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    latency_ms: int | None = None
    timeout_ms: int | None = None
    provider: str | None = None
    model: str | None = None
    fallback: bool = False
    error_kind: str | None = None
    prompt_template_id: str | None = None
    prompt_hash: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
