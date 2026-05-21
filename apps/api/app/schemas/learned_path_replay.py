"""Replay execution + drift detection schemas.

Contracts for explicit LearnedPath replay. These statuses are independent of
autonomous-run ``pass_gate`` or Supervisor verdict.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# ──────────────────────────────────────────────────────────────────────────────
# Request
# ──────────────────────────────────────────────────────────────────────────────


class ReplayRequest(BaseModel):
    """POST /exploration/learned-paths/{path_id}/replay body."""

    url: str
    slot_overrides: dict[str, str] = Field(default_factory=dict)


# ──────────────────────────────────────────────────────────────────────────────
# Action (reconstructed from stored LearnedPath.actions dicts)
# ──────────────────────────────────────────────────────────────────────────────


class ReplayAction(BaseModel):
    """Single action deserialized from a LearnedPath record.

    ``step`` defaults to the list index when missing in storage.
    ``action_type`` is accepted as a string here; the service layer decides
    whether it is supported.
    """

    step: int
    action_type: str
    target_selector: str | None = None
    target_description: str | None = None
    value: str | None = None
    value_slot: str | None = None


# ──────────────────────────────────────────────────────────────────────────────
# Status enums
# ──────────────────────────────────────────────────────────────────────────────

ReplayStatus = Literal[
    "succeeded",
    "observed",
    "drifted",
    "failed",
    "unsupported",
    "candidate_not_found",
    "runtime_error",
]

ReplayDriftStatus = Literal[
    "none",
    "signature_changed",
    "target_missing",
    "page_mismatch",
    "unsupported_action",
    "no_candidate",
]


ObservationSignalKind = Literal[
    "url_changed",
    "title_changed",
    "page_load_finished",
    "network_idle_observed",
]

WaitStatus = Literal[
    "observed",
    "timeout",
    "skipped",
    "not_required",
]

ReplayObservationStatus = Literal[
    "observed",
    "no_primary_observation",
    "partial_observation",
    "not_applicable",
]


# ──────────────────────────────────────────────────────────────────────────────
# Replay Observation Summary (M11.2.3)
# ──────────────────────────────────────────────────────────────────────────────


class StepObservationRef(BaseModel):
    """Minimal reference to a step's observation outcome.

    Does not copy full step log, screenshot, raw HTML, DOM dump, or
    reporter wording.
    """

    step_index: int
    wait_id: str = ""
    wait_status: WaitStatus | None = None
    primary_signal_kind: ObservationSignalKind | None = None
    signal_kinds: list[ObservationSignalKind] = Field(default_factory=list)
    has_primary_signal: bool = False
    has_supporting_signal: bool = False
    notes: str = ""


class ReplayObservationSummary(BaseModel):
    """Replay-level observation evidence aggregated from step wait_results.

    This is diagnostic evidence only — it does not imply business success,
    retry decisions, or recovery actions.
    """

    observation_summary_id: str = ""
    replay_id: str | None = None
    learned_path_id: str = ""
    status: ReplayObservationStatus
    step_count: int = 0
    wait_result_count: int = 0
    observed_step_count: int = 0
    timeout_step_count: int = 0
    skipped_step_count: int = 0
    not_required_step_count: int = 0
    primary_signal_kinds: list[ObservationSignalKind] = Field(default_factory=list)
    supporting_signal_kinds: list[ObservationSignalKind] = Field(default_factory=list)
    has_primary_observation: bool = False
    has_timeout: bool = False
    has_only_supporting_observation: bool = False
    has_uncertain_observation: bool = False
    observation_notes: str = ""
    step_observation_refs: list[StepObservationRef] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Observation signals (M11.2.2 Wait-for-change MVP)
# ──────────────────────────────────────────────────────────────────────────────


class ObservationSignal(BaseModel):
    """A single observation signal captured during a post-action wait window."""

    signal_id: str = ""
    kind: ObservationSignalKind
    scope: Literal["post_action", "passive_runtime"] = "post_action"
    observed_at: datetime | None = None
    source: str = "replay_runtime"
    trigger: str = ""
    related_action_id: str | None = None
    related_step_id: str | None = None
    url_before: str | None = None
    url_after: str | None = None
    title_before: str | None = None
    title_after: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence_weight: float = Field(default=1.0, ge=0.0)
    is_terminal_candidate: bool = False
    is_error_candidate: bool = False
    notes: str = ""


class WaitResult(BaseModel):
    """Outcome of a post-action wait-for-change window."""

    wait_id: str = ""
    related_action_id: str | None = None
    related_step_id: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_ms: int = 0
    status: WaitStatus
    observed_signals: list[ObservationSignal] = Field(default_factory=list)
    primary_signal: ObservationSignal | None = None
    timeout_ms: int = 1000
    wait_strategy: str = "short_stability_wait"
    notes: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# Per-step log
# ──────────────────────────────────────────────────────────────────────────────


class ReplayStepLog(BaseModel):
    """Log entry for one replayed action."""

    step: int
    action_type: str
    selector: str | None = None
    ok: bool = True
    error: str | None = None
    matched_count: int | None = None
    url_before: str | None = None
    title_before: str | None = None
    url_after: str | None = None
    title_after: str | None = None
    screenshot_ref: str | None = None
    wait_result: WaitResult | None = None
    value_slot: str | None = None
    override_applied: bool = False
    effective_value: str | None = None


# ──────────────────────────────────────────────────────────────────────────────
# Result
# ──────────────────────────────────────────────────────────────────────────────


class ReplayResult(BaseModel):
    """Full replay outcome for a single LearnedPath."""

    learned_path_id: str
    source_run_id: str | None = None
    trust: str
    status: ReplayStatus
    drift_status: ReplayDriftStatus
    drift_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    stored_signature: dict[str, Any] = Field(default_factory=dict)
    current_signature: dict[str, Any] = Field(default_factory=dict)
    steps: list[ReplayStepLog] = Field(default_factory=list)
    final_url: str | None = None
    final_title: str | None = None
    observation_summary: ReplayObservationSummary | None = None
