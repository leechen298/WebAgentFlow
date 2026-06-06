"""Pydantic schemas for LearnedCapability projections."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

SENSITIVE_DETAIL_TOKENS = frozenset(
    {
        "debug",
        "raw",
        "selector",
        "dom",
        "html",
        "testid",
        "data-testid",
        "private",
        "payload",
        "playwright",
        "replay",
        "execution",
        "evidence_target",
        "evidence_targets",
        "terminal_detail",
        "learned_path_id",
        "path_id",
    }
)


def _is_sensitive_key(key: object) -> bool:
    normalized = str(key).replace("_", "-").lower()
    compact = normalized.replace("-", "")
    return any(
        token.replace("_", "-") in normalized
        or token.replace("_", "-").replace("-", "") in compact
        for token in SENSITIVE_DETAIL_TOKENS
    )


def _redact_sensitive_detail(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _redact_sensitive_detail(item)
            for key, item in value.items()
            if not _is_sensitive_key(key)
        }
    if isinstance(value, list):
        return [_redact_sensitive_detail(item) for item in value]
    return value


class CapabilityEvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: str
    source: str
    terminal_outcome: str
    business_match_observed: bool | None = None
    evidence_strength: str
    warnings: list[str] = Field(default_factory=list)
    redaction: dict[str, Any] = Field(default_factory=dict)


class LearnedCapabilitySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    page_template: str
    query_signature: dict[str, Any]
    dom_fingerprint: str
    capability_key: str
    capability_kind: str
    human_label: str | None = None
    region_ref: str
    control_ref: str
    adapter_type: str
    provenance: str
    trust: str
    trust_reason: str | None = None
    trust_updated_at: datetime | None = None
    source_run_id: str | None = None
    evidence: CapabilityEvidenceSummary = Field(alias="evidence_json")
    created_at: datetime
    updated_at: datetime

    @field_validator("evidence", mode="before")
    @classmethod
    def _redact_normal_evidence(cls, value: Any) -> Any:
        return _redact_sensitive_detail(value)


class LearnedCapabilityDetail(LearnedCapabilitySummary):
    action_schema: dict[str, Any] = Field(alias="action_schema_json")
    sample_value_policy: dict[str, Any] = Field(alias="sample_value_policy_json")
    terminal_target: dict[str, Any] = Field(alias="terminal_target_json")

    @field_validator("action_schema", "sample_value_policy", "terminal_target", mode="before")
    @classmethod
    def _redact_detail_payload(cls, value: Any) -> Any:
        return _redact_sensitive_detail(value)
