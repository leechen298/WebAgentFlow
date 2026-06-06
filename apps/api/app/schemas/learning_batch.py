"""Pydantic schemas for bounded learning batches."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

LearningBatchStatusValue = Literal[
    "pending",
    "running",
    "completed",
    "partial_success",
    "timed_out",
    "cancel_requested",
    "cancelled",
    "failed",
    "unverified",
]

TERMINAL_LEARNING_BATCH_STATUS_VALUES = frozenset(
    {
        "completed",
        "partial_success",
        "timed_out",
        "cancelled",
        "failed",
        "unverified",
    }
)

SENSITIVE_BATCH_TOKENS = frozenset(
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
        "seed_value",
        "seed_values",
        "target_value",
        "value",
        "values",
        "fill_values",
        "toggle_values",
    }
)


class BoundedLearningPolicy(BaseModel):
    version: str = "bounded_learning_policy.v1"
    max_scenario_count: int = Field(default=6, ge=1, le=50)
    max_wall_clock_seconds: int = Field(default=120, ge=1, le=3600)
    max_failures_per_adapter: int = Field(default=1, ge=0, le=20)
    max_consecutive_no_new_capability: int = Field(default=2, ge=0, le=20)
    allow_dependency_pairs: bool = False
    allow_all_supported_smoke: bool = False
    cancel_check_interval: str = "scenario_boundary"


class LearningBatchScenarioSummary(BaseModel):
    model_config = ConfigDict(extra="allow")

    scenario_id: str
    scenario_kind: str | None = None
    human_label: str | None = None
    status: str | None = None
    run_id: str | None = None
    learned_capability_ids: list[str] = Field(default_factory=list)
    learned_path_id: str | None = None
    warnings: list[str] = Field(default_factory=list)


class LearningBatchSummaryPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    policy_version: str | None = None
    planned_count: int = 0
    attempted_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    unverified_count: int = 0
    unsupported_count: int = 0
    skipped_count: int = 0
    terminal_reason: str | None = None
    timeout_occurred: bool = False
    cancellation_requested: bool = False
    warnings: list[str] = Field(default_factory=list)


class LearningBatchSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    session_id: str | None = None
    target_url: str
    page_template: str | None = None
    query_signature: dict[str, Any]
    dom_fingerprint: str | None = None
    status: LearningBatchStatusValue
    summary: dict[str, Any] = Field(alias="summary_json")
    created_run_ids: list[str] = Field(alias="created_run_ids_json")
    created_capability_ids: list[str] = Field(alias="created_capability_ids_json")
    created_learned_path_ids: list[str] = Field(alias="created_learned_path_ids_json")
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancel_requested_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("summary", mode="before")
    @classmethod
    def _redact_summary(cls, value: Any) -> Any:
        return redact_learning_batch_payload(value)


class LearningBatchDetail(LearningBatchSummary):
    policy: dict[str, Any] = Field(alias="policy_json")
    request: dict[str, Any] = Field(alias="request_json")
    planned_scenarios: list[dict[str, Any]] = Field(alias="planned_scenarios_json")

    @field_validator("policy", "request", "planned_scenarios", mode="before")
    @classmethod
    def _redact_detail(cls, value: Any) -> Any:
        return redact_learning_batch_payload(value)


def redact_learning_batch_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: redact_learning_batch_payload(item)
            for key, item in value.items()
            if not _is_sensitive_key(key)
        }
    if isinstance(value, list):
        return [redact_learning_batch_payload(item) for item in value]
    return value


def _is_sensitive_key(key: object) -> bool:
    normalized = str(key).replace("_", "-").lower()
    compact = normalized.replace("-", "")
    return any(
        token.replace("_", "-") in normalized
        or token.replace("_", "-").replace("-", "") in compact
        for token in SENSITIVE_BATCH_TOKENS
    )
