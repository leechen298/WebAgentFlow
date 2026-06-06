"""Deterministic capability hints derived from PageAnalysis."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

from app.schemas.capability_hints import (
    CapabilityHintSet,
    ControlCapabilityHint,
    DependencyHintGroup,
    RegionHint,
    SampleValueSourceHint,
    TerminalTargetHint,
)
from app.schemas.page_analysis import DiscoveredElement, PageAnalysis

ElementBucket = tuple[str, list[DiscoveredElement]]


def build_capability_hints(analysis: PageAnalysis) -> CapabilityHintSet:
    """Build a redacted public capability hint projection.

    Selectors, labels, option values, and raw DOM paths stay out of the returned
    model. Runtime code can resolve refs back to current PageAnalysis elements
    by using the helpers below.
    """
    buckets = _element_buckets(analysis)
    control_regions = _control_regions(analysis, buckets)
    terminal_targets = _terminal_targets(analysis)
    target_ref = terminal_targets[0].target_id if terminal_targets else None
    sample_sources: list[SampleValueSourceHint] = []
    controls: list[ControlCapabilityHint] = []

    for bucket_name, elements in buckets:
        for index, element in enumerate(elements):
            hint = _control_hint_for(
                analysis=analysis,
                bucket_name=bucket_name,
                index=index,
                element=element,
                region_ref=_region_ref_for_bucket(control_regions, bucket_name),
                terminal_target_ref=target_ref,
            )
            if hint is None:
                continue
            controls.append(hint)
            source = _sample_source_for(hint=hint, element=element)
            if source is not None:
                sample_sources.append(source)
                hint.sample_value_source_refs.append(source.source_id)

    return CapabilityHintSet(
        page_purpose=_page_purpose(controls),
        regions=control_regions,
        controls=controls,
        terminal_targets=terminal_targets,
        sample_value_sources=sample_sources,
        dependency_groups=_dependency_groups(analysis, controls),
    )


def resolve_control_hint(analysis: PageAnalysis, control_ref: str) -> DiscoveredElement | None:
    """Resolve a redacted control ref to the current PageAnalysis element."""
    for bucket_name, elements in _element_buckets(analysis):
        for index, element in enumerate(elements):
            if control_ref == control_ref_for_element(analysis, bucket_name, index, element):
                return element
    return None


def control_ref_for_element(
    analysis: PageAnalysis,
    bucket_name: str,
    index: int,
    element: DiscoveredElement,
) -> str:
    return _redacted_ref(
        "control",
        bucket_name,
        str(index),
        analysis.url,
        element.selector,
        element.tag,
        element.element_type or "",
    )


def _element_buckets(analysis: PageAnalysis) -> list[ElementBucket]:
    return [
        ("fillable", analysis.fillable),
        ("select", analysis.select),
        ("toggle", analysis.toggle),
        ("submit", analysis.submit),
        ("clickable", analysis.clickable),
        ("navigation", analysis.navigation),
    ]


def _control_regions(
    analysis: PageAnalysis,
    buckets: list[ElementBucket],
) -> list[RegionHint]:
    roles: list[str] = []
    if analysis.fillable or analysis.select or analysis.toggle:
        roles.append("filter_region")
    if analysis.submit or analysis.clickable:
        roles.append("action_bar")
    if analysis.navigation:
        roles.append("tab_region")
    if not roles and analysis.total_visible:
        roles.append("unknown")

    regions: list[RegionHint] = []
    for role in roles:
        source_refs = [
            control_ref_for_element(analysis, bucket_name, index, element)
            for bucket_name, elements in buckets
            for index, element in enumerate(elements[:3])
            if _bucket_region_role(bucket_name, element) == role
        ]
        regions.append(
            RegionHint(
                region_id=_redacted_ref("region", role, analysis.url, str(len(source_refs))),
                role=role,  # type: ignore[arg-type]
                confidence="medium" if role == "unknown" else "high",
                source_refs=source_refs,
            )
        )
    return regions


def _terminal_targets(analysis: PageAnalysis) -> list[TerminalTargetHint]:
    if analysis.fillable or analysis.select or analysis.toggle or analysis.submit:
        return [
            TerminalTargetHint(
                target_id=_redacted_ref("terminal", "list_refresh", analysis.url),
                target_kind="list_refresh",
                confidence="medium",
            )
        ]
    return []


def _control_hint_for(
    *,
    analysis: PageAnalysis,
    bucket_name: str,
    index: int,
    element: DiscoveredElement,
    region_ref: str | None,
    terminal_target_ref: str | None,
) -> ControlCapabilityHint | None:
    capability_kind = _capability_kind(bucket_name, element)
    if capability_kind is None:
        return None
    control_ref = control_ref_for_element(analysis, bucket_name, index, element)
    support_status, warnings = _support_for(bucket_name, element)
    return ControlCapabilityHint(
        hint_id=_redacted_ref("hint", capability_kind, analysis.url, bucket_name, str(index)),
        capability_kind=capability_kind,  # type: ignore[arg-type]
        region_ref=region_ref or _redacted_ref("region", "unknown", analysis.url),
        control_ref=control_ref,
        adapter_type=_adapter_type(bucket_name, element),
        confidence="high" if support_status == "supported" else "medium",
        support_status=support_status,  # type: ignore[arg-type]
        terminal_target_ref=terminal_target_ref,
        warnings=warnings,
    )


def _sample_source_for(
    *,
    hint: ControlCapabilityHint,
    element: DiscoveredElement,
) -> SampleValueSourceHint | None:
    if hint.capability_kind == "control_input":
        source_kind = "generated_by_type"
        materializable = True
    elif hint.capability_kind in {"control_select", "control_toggle"} and element.element_value:
        source_kind = "existing_option_value_redacted"
        materializable = False
    elif hint.capability_kind in {"control_select", "control_toggle"}:
        source_kind = "empty_safe_probe"
        materializable = True
    else:
        return None
    return SampleValueSourceHint(
        source_id=_redacted_ref("sample", hint.control_ref, source_kind),
        source_kind=source_kind,  # type: ignore[arg-type]
        control_ref=hint.control_ref,
        materializable_from_serialized_hint=materializable,
        redacted=not materializable or source_kind == "operator_supplied",
    )


def _dependency_groups(
    analysis: PageAnalysis,
    controls: list[ControlCapabilityHint],
) -> list[DependencyHintGroup]:
    input_refs_by_index = {
        index: control.control_ref
        for index, control in enumerate(controls)
        if control.capability_kind == "control_input"
    }
    range_pairs: list[str] = []
    for left, right in _range_index_pairs(analysis.fillable):
        left_ref = input_refs_by_index.get(left)
        right_ref = input_refs_by_index.get(right)
        if left_ref and right_ref:
            range_pairs.extend([left_ref, right_ref])
    if not range_pairs:
        return []
    return [
        DependencyHintGroup(
            group_id=_redacted_ref("dependency", "range_pair", analysis.url, *range_pairs),
            dependency_kind="range_pair",
            source_refs=range_pairs,
            confidence="high",
        )
    ]


def _range_index_pairs(elements: list[DiscoveredElement]) -> list[tuple[int, int]]:
    starts: list[int] = []
    ends: list[int] = []
    for index, element in enumerate(elements):
        text = _element_text(element)
        if any(token in text for token in ("from", "start", "begin", "开始", "起始")):
            starts.append(index)
        if any(token in text for token in ("to", "end", "结束", "截止")):
            ends.append(index)
    return [(left, right) for left in starts for right in ends if left != right]


def _page_purpose(controls: list[ControlCapabilityHint]) -> str:
    kinds = {control.capability_kind for control in controls}
    if kinds.intersection({"control_input", "control_select", "control_toggle", "submit_search"}):
        return "list_management"
    if "open_detail" in kinds:
        return "detail_view"
    return "unknown"


def _region_ref_for_bucket(regions: list[RegionHint], bucket_name: str) -> str | None:
    role = _bucket_region_role(bucket_name, None)
    for region in regions:
        if region.role == role:
            return region.region_id
    return regions[0].region_id if regions else None


def _bucket_region_role(bucket_name: str, element: DiscoveredElement | None) -> str:
    if bucket_name in {"fillable", "select", "toggle"}:
        return "filter_region"
    if bucket_name in {"submit", "clickable"}:
        return "action_bar"
    if bucket_name == "navigation":
        role = str(getattr(element, "role", "") or "").lower()
        if role == "tab":
            return "tab_region"
    return "unknown"


def _capability_kind(bucket_name: str, element: DiscoveredElement) -> str | None:
    if bucket_name == "fillable":
        return "control_input"
    if bucket_name == "select":
        return "control_select"
    if bucket_name == "toggle":
        return "control_toggle"
    if bucket_name == "submit":
        return "submit_search"
    if bucket_name == "navigation" and (element.role or "").lower() == "tab":
        return "switch_tab"
    text = _element_text(element)
    if bucket_name == "clickable" and any(
        token in text for token in ("export", "download", "导出", "下载")
    ):
        return "export_download"
    if bucket_name == "clickable" and any(
        token in text for token in ("detail", "view", "详情", "查看")
    ):
        return "open_detail"
    return None


def _support_for(bucket_name: str, element: DiscoveredElement) -> tuple[str, list[str]]:
    if bucket_name == "fillable":
        if (element.role or "").lower() == "combobox":
            return "unsupported", ["combobox adapter is not supported by capability ingest"]
        if element.readonly and not _looks_like_picker(element):
            return "unknown", ["readonly input requires adapter confirmation"]
        return "supported", []
    if bucket_name == "select":
        if element.tag == "select" and element.element_value:
            return "supported", []
        return "unsupported", ["select option value is not available in PageAnalysis"]
    if bucket_name == "toggle":
        if element.element_value:
            return "supported", []
        return "unsupported", ["toggle value binding is not available in PageAnalysis"]
    if bucket_name in {"submit", "clickable", "navigation"}:
        return "supported", []
    return "unknown", []


def _adapter_type(bucket_name: str, element: DiscoveredElement) -> str:
    if bucket_name == "fillable":
        element_type = str(element.element_type or "").lower()
        if (element.role or "").lower() == "combobox":
            return "unsupported"
        if element_type in {"date", "month"} or element.readonly:
            return "set_value"
        return "fill"
    if bucket_name == "select":
        return "select" if element.tag == "select" and element.element_value else "unsupported"
    if bucket_name == "toggle":
        return "toggle" if element.element_value else "unsupported"
    return "click"


def _looks_like_picker(element: DiscoveredElement) -> bool:
    text = _element_text(element)
    return any(token in text for token in ("date", "month", "日期", "月份"))


def _element_text(element: DiscoveredElement) -> str:
    values = (
        element.element_type,
        element.role,
        element.semantic_role,
        element.label_text,
        element.placeholder,
        element.aria_label,
        element.text,
        element.name,
        element.id,
    )
    return " ".join(str(value or "").strip().lower() for value in values if value)


def _redacted_ref(prefix: str, *parts: str) -> str:
    payload = "\n".join(str(part or "") for part in parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def assert_redacted_refs(values: Iterable[str]) -> bool:
    """Return True when all refs avoid common raw selector / DOM markers."""
    raw_marker = re.compile(r"(#|//|\[|\]|>|\s|xpath|css=)")
    return all(not raw_marker.search(value or "") for value in values)
