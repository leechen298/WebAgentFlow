"""Schemas for automatic capability composition candidates."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CompositionCandidateStatus(StrEnum):
    GENERATED = "generated"
    REJECTED_STATIC = "rejected_static"
    READY_FOR_EXECUTION = "ready_for_execution"
    EXECUTING = "executing"
    EXECUTION_PASSED = "execution_passed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_UNVERIFIED = "execution_unverified"
    PROMOTED_TO_LEARNED_PATH = "promoted_to_learned_path"
    NEGATIVE_EVIDENCE_RECORDED = "negative_evidence_recorded"


class CompositionCandidateGenerationRequest(BaseModel):
    target_url: str
    page_template: str
    query_signature: dict[str, Any] = Field(default_factory=dict)
    dom_fingerprint: str | None = None
    user_goal: str
    slot_bindings: dict[str, str] = Field(default_factory=dict)
    required_families: list[str] = Field(default_factory=list)
    learning_batch_id: str | None = None
    source_run_id: str | None = None


class CompositionCoverageMetrics(BaseModel):
    requested_required_families: int
    generated_required_families: int
    generated_candidates: int
    ready_for_execution_candidates: int
    required_family_coverage: float | None
    null_metric_reasons: dict[str, str] = Field(default_factory=dict)


class CompositionCandidatePublic(BaseModel):
    candidate_id: str
    target_scope_ref: str
    page_template: str
    candidate_family: str
    source_capability_refs: list[str] = Field(default_factory=list)
    ordered_capability_kinds: list[str] = Field(default_factory=list)
    expected_terminal_target: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "medium"
    confidence: str = "medium"
    generation_reason: str = ""
    status: CompositionCandidateStatus
    static_rejection_reason: str | None = None


class CompositionCandidateGenerationResult(BaseModel):
    candidates: list[CompositionCandidatePublic]
    coverage: CompositionCoverageMetrics
