"""Redacted provider-evaluable learning evidence bundle schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BundleOperatorAction(BaseModel):
    surface: str
    command: str
    cwd: str


class BundleCompositionCandidate(BaseModel):
    candidate_ref: str
    target_scope_ref: str
    page_template: str
    candidate_family: str
    source_capability_refs: list[str] = Field(default_factory=list)
    ordered_capability_kinds: list[str] = Field(default_factory=list)
    expected_terminal_target_summary: dict[str, Any] = Field(default_factory=dict)
    status: str
    static_rejection_reason: str | None = None
    execution_summary: dict[str, Any] = Field(default_factory=dict)
    promotion_decision_summary: dict[str, Any] = Field(default_factory=dict)


class BundleRedactionSummary(BaseModel):
    schema_version: str = "bundle_redaction.v1"
    raw_ids_redacted: bool = True
    private_payloads_excluded: bool = True
    provider_oracle_excluded: bool = True
    warnings: list[str] = Field(default_factory=list)


class LearningEvidenceBundle(BaseModel):
    schema_version: str = "waf.learning_evidence_bundle.v1"
    operator_actions: list[BundleOperatorAction]
    page_analysis_summary: dict[str, Any] = Field(default_factory=dict)
    learning_batches: list[dict[str, Any]] = Field(default_factory=list)
    learned_capabilities: list[dict[str, Any]] = Field(default_factory=list)
    learned_paths: list[dict[str, Any]] = Field(default_factory=list)
    runs: list[dict[str, Any]] = Field(default_factory=list)
    composition_summary: dict[str, Any] = Field(default_factory=dict)
    composition: list[BundleCompositionCandidate]
    redaction: BundleRedactionSummary = Field(default_factory=BundleRedactionSummary)
