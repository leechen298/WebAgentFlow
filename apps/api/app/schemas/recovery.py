"""M12.1 recovery boundary schema contracts.

These contracts model deterministic failure classification and recovery
boundary recommendations. They intentionally contain no runtime behavior.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

FailureClassification = Literal[
    "success_no_recovery_needed",
    "failure",
    "blocked",
    "uncertain",
    "needs_review",
]

BoundaryRecommendation = Literal[
    "no_recovery_needed",
    "stop",
    "ask_user",
    "needs_review",
    "suggest_reteach",
    "retry_possible_requires_confirmation",
]

ClassificationReason = Literal[
    "task_succeeded",
    "replay_failed",
    "replay_drifted",
    "execution_error",
    "target_missing",
    "unsupported_action",
    "missing_context",
    "permission_or_auth_blocked",
    "unsafe_or_unknown_state",
    "insufficient_postcondition_evidence",
    "explicit_needs_review",
    "stale_or_missing_path_coverage",
    "result_reporter_failed",
    "result_reporter_blocked",
    "result_reporter_uncertain",
]


class EvidenceReference(BaseModel):
    """Reference to structured evidence used by the classifier."""

    source: str
    key: str
    value: Any | None = None
    description: str | None = None


class RecoveryEvidence(BaseModel):
    """Minimal M11.1-compatible input evidence for M12.1 classification."""

    model_config = ConfigDict(extra="allow")

    execution_status: str | None = None
    verification_outcome: str | None = None
    needs_review: bool = False
    task_verified: bool = False
    replay_status: str | None = None
    drift_status: str | None = None
    drift_reasons: list[str] = Field(default_factory=list)
    error_summary: str | None = None
    blocked_reason: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    postcondition_evidence: list[EvidenceReference] = Field(default_factory=list)
    retry_candidate: bool = False
    learned_path_id: str | None = None
    target_url: str | None = None
    final_url: str | None = None
    final_title: str | None = None


class RecoveryBoundary(BaseModel):
    """Classifier output: a boundary recommendation, not an execution command."""

    classification: FailureClassification
    recommendation: BoundaryRecommendation
    reason: ClassificationReason
    evidence: list[EvidenceReference] = Field(default_factory=list)
    message: str | None = None


# ---------------------------------------------------------------------------
# M12.2 user abort / stop handling schema contracts
# ---------------------------------------------------------------------------

AbortSource = Literal[
    "slash_abort",
    "slash_stop",
    "user_message",
    "ui_stop_button",
    "external_scheduler",
]

StopHandlingDecision = Literal[
    "accepted_stop",
    "already_finished",
    "already_failed",
    "not_running",
    "cannot_interrupt_inflight_action",
    "needs_manual_review",
]


class UserAbortSignal(BaseModel):
    """User control intent to stop current automation."""

    model_config = ConfigDict(extra="allow")

    source: AbortSource
    raw_text: str | None = None
    timestamp: str | None = None


class UserAbortState(BaseModel):
    """Runtime state snapshot at the moment the abort signal is received."""

    model_config = ConfigDict(extra="allow")

    session_status: str | None = None
    active_command: str | None = None
    active_plan_id: str | None = None
    active_step_index: int | None = None
    last_execution_event: str | None = None
    replay_status: str | None = None
    reporter_outcome: str | None = None
    task_verified: bool = False
    has_inflight_action: bool = False
    user_message: str | None = None


class AbortEvidence(BaseModel):
    """Evidence captured at interruption time."""

    model_config = ConfigDict(extra="allow")

    signal: UserAbortSignal
    state: UserAbortState
    captured_at: str | None = None


class AbortAcknowledgement(BaseModel):
    """Pure acknowledgement of a user abort — no proposal, no retry, no browser action."""

    decision: StopHandlingDecision
    message: str
    evidence: AbortEvidence
    no_new_actions_after: bool = Field(
        default=True,
        description=(
            "Stop boundary flag: True means the caller must not start new browser "
            "actions. False means no active automation was running to stop. "
            "This is NOT an invitation to start new actions — it only describes "
            "whether the stop boundary applies."
        ),
    )
    inflight_caveat: bool = Field(
        default=False,
        description=(
            "True when a browser action may already be in flight at abort time. "
            "The caller must not assume external side effects are reversible."
        ),
    )
