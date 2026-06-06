"""Schemas for deterministic LearnedCapability composition."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CapabilityCompositionStatus = Literal[
    "ready",
    "missing_capability",
    "ambiguous",
    "unsafe",
    "prefer_learned_path",
    "unsupported",
]
CapabilityCompositionRisk = Literal["low", "medium", "high"]
CapabilityCompositionConfidence = Literal["high", "medium", "low"]

_RAW_PUBLIC_MARKER_RE = re.compile(
    r"(#|//|\[|\]|>|<html|playwright|page\.|locator\()",
    re.IGNORECASE,
)


def _reject_raw_public_value(value: object) -> object:
    if isinstance(value, str) and _RAW_PUBLIC_MARKER_RE.search(value):
        raise ValueError("public composition field must not contain raw execution detail")
    return value


def _reject_raw_public_tree(value: object) -> object:
    _reject_raw_public_value(value)
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_raw_public_value(key)
            _reject_raw_public_tree(item)
    if isinstance(value, list):
        for item in value:
            _reject_raw_public_tree(item)
    return value


class CapabilityCompositionPolicy(BaseModel):
    version: str = "capability_composition_policy.v1"
    allow_provisional_trust: bool = False
    require_dom_fingerprint_match: bool = True
    supported_action_versions: list[str] = Field(
        default_factory=lambda: ["capability_action.v1"]
    )
    supported_adapter_types: list[str] = Field(
        default_factory=lambda: [
            "fill",
            "input",
            "text",
            "date",
            "month",
            "set_value",
            "select",
            "toggle",
            "click",
        ]
    )
    supported_operations: list[str] = Field(
        default_factory=lambda: [
            "fill",
            "set_value",
            "select",
            "select_first_option",
            "click",
            "press",
            "observe",
        ]
    )


class CapabilityCompositionRequest(BaseModel):
    target_url: str
    page_template: str
    query_signature: dict[str, Any] = Field(default_factory=dict)
    user_goal: str
    required_capability_kinds: list[str] = Field(default_factory=list)
    slot_bindings: dict[str, str] = Field(default_factory=dict)
    dom_fingerprint: str | None = None


class CapabilityCompositionStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str
    source_capability_id: str
    capability_kind: str
    action_kind: str
    required_slots: list[str] = Field(default_factory=list)
    slot_refs: list[str] = Field(default_factory=list)
    terminal_target_kind: str | None = None

    @field_validator(
        "step_id",
        "source_capability_id",
        "capability_kind",
        "action_kind",
        "terminal_target_kind",
    )
    @classmethod
    def _public_strings_are_safe(cls, value: str | None) -> str | None:
        return _reject_raw_public_value(value)

    @field_validator("required_slots", "slot_refs")
    @classmethod
    def _public_lists_are_safe(cls, values: list[str]) -> list[str]:
        for value in values:
            _reject_raw_public_value(value)
        return values

class CapabilityCompositionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    composition_id: str
    version: str = "capability_composition.v1"
    target_url: str
    page_template: str
    user_goal: str
    status: CapabilityCompositionStatus
    source_capability_ids: list[str] = Field(default_factory=list)
    ordered_steps: list[CapabilityCompositionStep] = Field(default_factory=list)
    expected_terminal_target: dict[str, Any] = Field(default_factory=dict)
    risk_level: CapabilityCompositionRisk = "medium"
    confidence: CapabilityCompositionConfidence = "medium"
    missing_capabilities: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    preferred_learned_path_id: str | None = None

    @field_validator(
        "composition_id",
        "page_template",
        "user_goal",
        "preferred_learned_path_id",
    )
    @classmethod
    def _public_strings_are_safe(cls, value: str | None) -> str | None:
        return _reject_raw_public_value(value)

    @field_validator(
        "source_capability_ids",
        "missing_capabilities",
        "rejection_reasons",
        "warnings",
    )
    @classmethod
    def _public_lists_are_safe(cls, values: list[str]) -> list[str]:
        for value in values:
            _reject_raw_public_value(value)
        return values

    @field_validator("expected_terminal_target")
    @classmethod
    def _terminal_target_is_safe(cls, value: dict[str, Any]) -> dict[str, Any]:
        _reject_raw_public_tree(value)
        return value


class CapabilityExecutionHandoff(BaseModel):
    """Service-internal execution handoff. Do not expose as a public plan."""

    composition_id: str
    source_capability_ids: list[str]
    ordered_action_schemas: list[dict[str, Any]]
    slot_bindings: dict[str, str]
    expected_terminal_target: dict[str, Any] = Field(default_factory=dict)


class CapabilityCompositionResult(BaseModel):
    plan: CapabilityCompositionPlan
    execution_handoff: CapabilityExecutionHandoff | None = Field(default=None, exclude=True)


class CapabilityPromotionDecision(BaseModel):
    promotable: bool
    composition_id: str | None = None
    source_capability_ids: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)
    learned_path_metadata: dict[str, Any] = Field(default_factory=dict)
