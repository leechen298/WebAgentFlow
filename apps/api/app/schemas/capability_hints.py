"""Target-agnostic capability hint schemas for PageAnalysis."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

PagePurposeHint = Literal[
    "list_management",
    "detail_view",
    "form_entry",
    "settings",
    "unknown",
]

RegionRoleHint = Literal[
    "filter_region",
    "result_region",
    "action_bar",
    "tab_region",
    "modal_region",
    "detail_region",
    "form_region",
    "pagination_region",
    "unknown",
]

ControlCapabilityKind = Literal[
    "control_input",
    "control_select",
    "control_toggle",
    "submit_search",
    "reset_filters",
    "switch_tab",
    "open_detail",
    "export_download",
    "show_modal_or_toast",
]

TerminalTargetKind = Literal[
    "list_refresh",
    "empty_result",
    "query_persisted",
    "url_query_changed",
    "modal_opened",
    "toast_shown",
    "download_started",
    "detail_visible",
    "unknown",
]

SampleValueSourceKind = Literal[
    "generated_by_type",
    "static_safe_default",
    "empty_safe_probe",
    "existing_option_value_redacted",
    "operator_supplied",
]

DependencyHintKind = Literal[
    "range_pair",
    "cascader_chain",
    "tab_scoped_controls",
    "filter_requires_submit",
    "modal_requires_open",
]

HintConfidence = Literal["high", "medium", "low"]
CapabilitySupportStatus = Literal["supported", "unsupported", "unknown"]

_REDACTED_REF_RE = re.compile(r"^[a-z]+_[0-9a-f]{16}$")


def _validate_redacted_ref(value: str | None) -> str | None:
    if value is None:
        return value
    if not _REDACTED_REF_RE.fullmatch(value):
        raise ValueError("ref must be a stable redacted id")
    return value


def _validate_redacted_ref_list(values: list[str]) -> list[str]:
    for value in values:
        _validate_redacted_ref(value)
    return values


class RegionHint(BaseModel):
    region_id: str
    role: RegionRoleHint
    confidence: HintConfidence = "medium"
    source_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("region_id")
    @classmethod
    def _region_id_is_redacted(cls, value: str) -> str:
        return _validate_redacted_ref(value) or value

    @field_validator("source_refs")
    @classmethod
    def _source_refs_are_redacted(cls, values: list[str]) -> list[str]:
        return _validate_redacted_ref_list(values)


class TerminalTargetHint(BaseModel):
    target_id: str
    target_kind: TerminalTargetKind
    confidence: HintConfidence = "medium"
    source_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("target_id")
    @classmethod
    def _target_id_is_redacted(cls, value: str) -> str:
        return _validate_redacted_ref(value) or value

    @field_validator("source_refs")
    @classmethod
    def _source_refs_are_redacted(cls, values: list[str]) -> list[str]:
        return _validate_redacted_ref_list(values)


class SampleValueSourceHint(BaseModel):
    source_id: str
    source_kind: SampleValueSourceKind
    control_ref: str
    materializable_from_serialized_hint: bool = False
    redacted: bool = True
    warnings: list[str] = Field(default_factory=list)

    @field_validator("source_id", "control_ref")
    @classmethod
    def _refs_are_redacted(cls, value: str) -> str:
        return _validate_redacted_ref(value) or value


class ControlCapabilityHint(BaseModel):
    hint_id: str
    capability_kind: ControlCapabilityKind
    region_ref: str
    control_ref: str
    adapter_type: str
    confidence: HintConfidence = "medium"
    support_status: CapabilitySupportStatus = "unknown"
    terminal_target_ref: str | None = None
    sample_value_source_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("hint_id", "region_ref", "control_ref", "terminal_target_ref")
    @classmethod
    def _refs_are_redacted(cls, value: str | None) -> str | None:
        return _validate_redacted_ref(value)

    @field_validator("sample_value_source_refs")
    @classmethod
    def _sample_refs_are_redacted(cls, values: list[str]) -> list[str]:
        return _validate_redacted_ref_list(values)


class DependencyHintGroup(BaseModel):
    group_id: str
    dependency_kind: DependencyHintKind
    source_refs: list[str] = Field(default_factory=list)
    confidence: HintConfidence = "medium"
    warnings: list[str] = Field(default_factory=list)

    @field_validator("group_id")
    @classmethod
    def _group_id_is_redacted(cls, value: str) -> str:
        return _validate_redacted_ref(value) or value

    @field_validator("source_refs")
    @classmethod
    def _source_refs_are_redacted(cls, values: list[str]) -> list[str]:
        return _validate_redacted_ref_list(values)


class CapabilityHintSet(BaseModel):
    version: str = "capability_hints.v1"
    page_purpose: PagePurposeHint = "unknown"
    regions: list[RegionHint] = Field(default_factory=list)
    controls: list[ControlCapabilityHint] = Field(default_factory=list)
    terminal_targets: list[TerminalTargetHint] = Field(default_factory=list)
    sample_value_sources: list[SampleValueSourceHint] = Field(default_factory=list)
    dependency_groups: list[DependencyHintGroup] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
