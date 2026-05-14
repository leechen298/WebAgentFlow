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


# ──────────────────────────────────────────────────────────────────────────────
# Observation signals (M11.2.2 Wait-for-change MVP)
# ──────────────────────────────────────────────────────────────────────────────

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
