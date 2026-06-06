"""Terminal-state verdict schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TerminalOutcome = Literal[
    "terminal_detected",
    "terminal_unverified",
    "not_terminal_yet",
    "terminal_failed",
]
TerminalStateType = Literal[
    "navigation",
    "list_refresh",
    "network_completion",
    "modal_or_popup_opened",
    "browser_dialog",
    "download_started",
    "artifact_available",
    "toast_or_status_message",
    "region_changed",
    "no_observable_change",
    "terminal_failed",
]
EvidenceStrength = Literal["strong", "medium", "weak", "none"]
StopDecision = Literal["stop", "wait", "continue", "unverified_stop"]
TerminalStateSource = Literal["deterministic"]


class TerminalStateVerdict(BaseModel):
    terminal_outcome: TerminalOutcome
    terminal_type: TerminalStateType
    evidence_strength: EvidenceStrength
    evidence_summary: str
    stop_decision: StopDecision
    warnings: list[str] = Field(default_factory=list)
    matched_event_ids: list[str] = Field(default_factory=list)
    matched_action_ids: list[str] = Field(default_factory=list)
    matched_step_indices: list[int] = Field(default_factory=list)
    matched_action_types: list[str] = Field(default_factory=list)
    matched_hint_ids: list[str] = Field(default_factory=list)
    matched_evidence: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    needs_more_wait: bool = False
    max_wait_reached: bool = False
    source: TerminalStateSource = "deterministic"
