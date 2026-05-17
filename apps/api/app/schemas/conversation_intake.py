"""M11.3.4 conversation intake schemas."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ConversationIntakeIntent(StrEnum):
    LEARN_OPERATION = "learn_operation"
    EXECUTE_OPERATION = "execute_operation"
    PROVIDE_MISSING_INFO = "provide_missing_info"
    UNKNOWN = "unknown"


class ConversationIntakeTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str | None = None
    site_origin: str | None = None
    page_hint: str | None = None


class ConversationIntakeAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str | None = None
    canonical_goal: str | None = None
    aliases: list[str] = Field(default_factory=list)


class ConversationIntakeSlot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    semantic_type: str
    label_seen: str | None = None
    value: str | None = None
    sensitive: bool = False
    source: str = "user_message"


class ConversationMissingField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    semantic_type: str
    display_name: str


class ConversationIntakeResult(BaseModel):
    """Schema-constrained natural-language intake result.

    Extra fields are forbidden deliberately: intake output must not smuggle
    selectors, browser actions, or learned_path_id authorization into the
    runtime path.
    """

    model_config = ConfigDict(extra="forbid")

    intent: ConversationIntakeIntent
    target: ConversationIntakeTarget = Field(default_factory=ConversationIntakeTarget)
    action: ConversationIntakeAction = Field(default_factory=ConversationIntakeAction)
    slots: list[ConversationIntakeSlot] = Field(default_factory=list)
    missing_fields: list[ConversationMissingField] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    should_ask_user: bool = False
    ask_user_message_hint: str | None = None
    source: str = "deterministic"
