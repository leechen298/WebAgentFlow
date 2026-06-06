"""Attempt-level ingest evaluation schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AttemptIngestStatus = Literal["eligible", "ineligible", "unverified"]
AttemptOutcome = Literal[
    "success_candidate",
    "failed",
    "unverified",
    "not_terminal",
]
AttemptFailureCategory = Literal[
    "terminal_unverified",
    "terminal_failed",
    "terminal_not_reached",
    "pass_gate_not_pass",
    "no_effective_actions",
    "missing_terminal_evidence",
    "none",
]
AttemptEvaluationSource = Literal["deterministic"]


class AttemptIngestEvaluation(BaseModel):
    ingest_status: AttemptIngestStatus
    attempt_outcome: AttemptOutcome
    failure_category: AttemptFailureCategory = "none"
    reasons: list[str] = Field(default_factory=list)
    terminal_outcome: str | None = None
    terminal_type: str | None = None
    evidence_strength: str | None = None
    stop_decision: str | None = None
    pass_gate_status: str | None = None
    effective_action_count: int = 0
    source: AttemptEvaluationSource = "deterministic"
