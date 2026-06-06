"""Terminal-state hint schemas for L1 autonomous learning."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

TerminalHintSource = Literal["deterministic", "provider", "fallback"]
TerminalTypeHint = Literal[
    "navigation",
    "list_refresh",
    "network_completion",
    "modal_or_popup_opened",
    "download_started",
    "toast_or_status_message",
    "region_changed",
    "no_observable_change",
]


class PageRegionHint(BaseModel):
    region_id: str
    region_type: str
    summary: str


class PossiblePageFunction(BaseModel):
    function_id: str
    function_type: str
    label: str
    related_regions: list[str] = Field(default_factory=list)


class CandidateTerminalStateHint(BaseModel):
    function_id: str
    terminal_type: TerminalTypeHint
    evidence_hint: str


class PageTerminalHintSet(BaseModel):
    page_purpose: str
    page_content_summary: str
    page_regions: list[PageRegionHint] = Field(default_factory=list)
    possible_functions: list[PossiblePageFunction] = Field(default_factory=list)
    candidate_terminal_states: list[CandidateTerminalStateHint] = Field(default_factory=list)
    confidence: float = 0.0
    reason_summary: str = ""
    source: TerminalHintSource = "deterministic"
