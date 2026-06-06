"""Target-agnostic page capability discovery for filter/search pages."""

from __future__ import annotations

import hashlib
import itertools
import re
from dataclasses import dataclass, field
from typing import Literal

from app.schemas.capability_hints import ControlCapabilityHint, DependencyHintGroup
from app.schemas.page_analysis import DiscoveredElement, PageAnalysis
from app.services.learning.capability_hints import resolve_control_hint

ScenarioKind = Literal["single_filter", "pairwise_filter", "all_supported_filters_smoke"]


@dataclass(frozen=True)
class FilterCapability:
    capability_id: str
    kind: str
    human_label: str
    control_ref: str
    control_type: str
    adapter_type: str
    supported: bool
    support_reason: str
    default_test_value_source: str | None
    submit_ref: str | None
    observation_target: dict[str, str]
    binding_key: str
    binding_value: str


@dataclass(frozen=True)
class PageCapabilityInventory:
    page_url: str
    page_title: str
    supported_capabilities: list[FilterCapability] = field(default_factory=list)
    unsupported_capabilities: list[FilterCapability] = field(default_factory=list)
    dependency_pairs: list[tuple[str, str]] | None = None

    @property
    def candidate_capabilities(self) -> list[FilterCapability]:
        return [*self.supported_capabilities, *self.unsupported_capabilities]


@dataclass(frozen=True)
class CapabilityScenario:
    scenario_id: str
    capability_id: str
    scenario_kind: ScenarioKind
    human_label: str
    input_bindings: list[dict[str, str]]
    expected_observation_target: dict[str, str]
    discovery_batch_id: str
    source_capability_ids: list[str]
    fill_values: dict[str, str] = field(default_factory=dict)
    toggle_values: dict[str, str] = field(default_factory=dict)


def build_filter_inventory(analysis: PageAnalysis) -> PageCapabilityInventory:
    """Build a filter/search capability inventory from PageAnalysis."""
    if analysis.capability_hints.controls:
        return _build_filter_inventory_from_hints(analysis)

    submit_ref = _submit_ref(analysis)
    supported: list[FilterCapability] = []
    unsupported: list[FilterCapability] = []
    used_keys: set[str] = set()

    for index, element in enumerate(analysis.fillable):
        if not _has_filter_signal(element):
            continue
        key = _unique_binding_key(_binding_key_for(element, fallback=f"text_{index}"), used_keys)
        label = _human_label(element, fallback=f"Text filter {index + 1}")
        control_type = _fillable_control_type(element)
        adapter_type = _adapter_type_for_fillable(control_type, element)
        target = unsupported if adapter_type == "unsupported" else supported
        target.append(
            _capability(
                analysis=analysis,
                element=element,
                index=index,
                kind="filter",
                human_label=label,
                control_type=control_type,
                adapter_type=adapter_type,
                supported=adapter_type != "unsupported",
                support_reason=(
                    "combobox adapter is not supported by capability ingest"
                    if adapter_type == "unsupported"
                    else "fillable control supported by action planner"
                ),
                submit_ref=submit_ref,
                binding_key=key,
                binding_value=(
                    ""
                    if adapter_type == "unsupported"
                    else _default_value_for(element, label)
                ),
            )
        )

    offset = len(supported)
    for index, element in enumerate(analysis.toggle):
        key = _unique_binding_key(
            _binding_key_for(element, fallback=f"toggle_{index}"),
            used_keys,
        )
        value = str(element.element_value or element.text or element.aria_label or "").strip()
        label = _human_label(element, fallback=f"Toggle filter {index + 1}")
        if key and value:
            supported.append(
                _capability(
                    analysis=analysis,
                    element=element,
                    index=offset + index,
                    kind="filter",
                    human_label=f"{label}: {value}" if value not in label else label,
                    control_type="toggle",
                    adapter_type="toggle",
                    supported=True,
                    support_reason="toggle control supported by action planner",
                    submit_ref=submit_ref,
                    binding_key=key,
                    binding_value=value,
                )
            )
        else:
            unsupported.append(
                _capability(
                    analysis=analysis,
                    element=element,
                    index=offset + index,
                    kind="filter",
                    human_label=label,
                    control_type="toggle",
                    adapter_type="unsupported",
                    supported=False,
                    support_reason="toggle control lacks stable role or value binding",
                    submit_ref=submit_ref,
                    binding_key=key or f"toggle_{index}",
                    binding_value=value,
                )
            )

    select_offset = offset + len(analysis.toggle)
    for index, element in enumerate(analysis.select):
        key = _unique_binding_key(
            _binding_key_for(element, fallback=f"select_{index}"),
            used_keys,
        )
        label = _human_label(element, fallback=f"Select filter {index + 1}")
        if element.tag == "select" and element.element_value:
            supported.append(
                _capability(
                    analysis=analysis,
                    element=element,
                    index=select_offset + index,
                    kind="filter",
                    human_label=label,
                    control_type="select",
                    adapter_type="select",
                    supported=True,
                    support_reason="native select value supported by action planner select path",
                    submit_ref=submit_ref,
                    binding_key=key,
                    binding_value=str(element.element_value),
                )
            )
        else:
            unsupported.append(
                _capability(
                    analysis=analysis,
                    element=element,
                    index=select_offset + index,
                    kind="filter",
                    human_label=label,
                    control_type="select",
                    adapter_type="unsupported",
                    supported=False,
                    support_reason=(
                        "select option inventory is not available in current PageAnalysis"
                    ),
                    submit_ref=submit_ref,
                    binding_key=key,
                    binding_value="",
                )
            )

    return PageCapabilityInventory(
        page_url=analysis.url,
        page_title=analysis.title,
        supported_capabilities=supported,
        unsupported_capabilities=unsupported,
    )


def generate_filter_scenarios(
    inventory: PageCapabilityInventory,
    *,
    discovery_batch_id: str,
) -> list[CapabilityScenario]:
    """Generate single, pairwise, and all-supported smoke scenarios."""
    capabilities = inventory.supported_capabilities
    scenarios: list[CapabilityScenario] = []

    for capability in capabilities:
        scenarios.append(
            _scenario(
                discovery_batch_id=discovery_batch_id,
                scenario_kind="single_filter",
                capabilities=[capability],
            )
        )

    pairs = _dependency_pairs_for_inventory(inventory)
    for left, right in pairs:
        scenarios.append(
            _scenario(
                discovery_batch_id=discovery_batch_id,
                scenario_kind="pairwise_filter",
                capabilities=[left, right],
            )
        )

    if capabilities:
        scenarios.append(
            _scenario(
                discovery_batch_id=discovery_batch_id,
                scenario_kind="all_supported_filters_smoke",
                capabilities=capabilities,
            )
        )

    return scenarios


def _build_filter_inventory_from_hints(analysis: PageAnalysis) -> PageCapabilityInventory:
    submit_ref = _submit_ref(analysis)
    supported: list[FilterCapability] = []
    unsupported: list[FilterCapability] = []
    used_keys: set[str] = set()
    controls_by_ref = {
        control.control_ref: control
        for control in analysis.capability_hints.controls
    }

    for index, hint in enumerate(analysis.capability_hints.controls):
        if hint.capability_kind not in {
            "control_input",
            "control_select",
            "control_toggle",
        }:
            continue
        element = resolve_control_hint(analysis, hint.control_ref)
        if element is None:
            unsupported.append(_unsupported_hint_capability(analysis, hint, index))
            continue
        capability = _capability_from_hint(
            analysis=analysis,
            hint=hint,
            element=element,
            index=index,
            submit_ref=submit_ref,
            used_keys=used_keys,
        )
        if capability.supported:
            supported.append(capability)
        else:
            unsupported.append(capability)

    return PageCapabilityInventory(
        page_url=analysis.url,
        page_title=analysis.title,
        supported_capabilities=supported,
        unsupported_capabilities=unsupported,
        dependency_pairs=_hint_dependency_pairs(
            analysis.capability_hints.dependency_groups,
            controls_by_ref,
        ),
    )


def _capability_from_hint(
    *,
    analysis: PageAnalysis,
    hint: ControlCapabilityHint,
    element: DiscoveredElement,
    index: int,
    submit_ref: str | None,
    used_keys: set[str],
) -> FilterCapability:
    control_type = _control_type_from_hint(hint, element)
    adapter_type = _adapter_type_from_hint(hint, element)
    binding_key = _unique_binding_key(
        _binding_key_for(element, fallback=f"hint_{index}"),
        used_keys,
    )
    binding_value = _binding_value_from_hint(hint, element)
    supported = (
        hint.support_status == "supported"
        and bool(element.selector)
        and adapter_type != "unsupported"
        and bool(binding_key)
        and (hint.capability_kind == "control_input" or bool(binding_value))
    )
    support_reason = "capability hint resolved to executable binding"
    if not supported:
        support_reason = "capability hint could not be resolved to an executable binding"

    return FilterCapability(
        capability_id=hint.hint_id,
        kind="filter",
        human_label=_human_label(element, fallback=f"Capability hint {index + 1}"),
        control_ref=element.selector,
        control_type=control_type,
        adapter_type=adapter_type,
        supported=supported,
        support_reason=support_reason,
        default_test_value_source=_default_source_from_hint(hint),
        submit_ref=submit_ref,
        observation_target={"kind": "generic_result_change"},
        binding_key=binding_key,
        binding_value=binding_value,
    )


def _unsupported_hint_capability(
    analysis: PageAnalysis,
    hint: ControlCapabilityHint,
    index: int,
) -> FilterCapability:
    return FilterCapability(
        capability_id=_stable_id(analysis.url, hint.hint_id, "missing_binding", str(index)),
        kind="filter",
        human_label=f"Capability hint {index + 1}",
        control_ref=hint.control_ref,
        control_type=_control_type_from_hint(hint, None),
        adapter_type="unsupported",
        supported=False,
        support_reason="capability hint has no current executable binding",
        default_test_value_source=None,
        submit_ref=None,
        observation_target={"kind": "generic_result_change"},
        binding_key=f"hint_{index}",
        binding_value="",
    )


def _dependency_pairs_for_inventory(
    inventory: PageCapabilityInventory,
) -> list[tuple[FilterCapability, FilterCapability]]:
    if inventory.dependency_pairs is None:
        return list(itertools.combinations(inventory.supported_capabilities, 2))
    by_id = {
        capability.capability_id: capability
        for capability in inventory.supported_capabilities
    }
    pairs: list[tuple[FilterCapability, FilterCapability]] = []
    for left_id, right_id in inventory.dependency_pairs:
        left = by_id.get(left_id)
        right = by_id.get(right_id)
        if left is not None and right is not None:
            pairs.append((left, right))
    return pairs


def _hint_dependency_pairs(
    dependency_groups: list[DependencyHintGroup],
    controls_by_ref: dict[str, ControlCapabilityHint],
) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for group in dependency_groups:
        if group.dependency_kind not in {"range_pair", "cascader_chain", "tab_scoped_controls"}:
            continue
        refs = [
            ref
            for ref in group.source_refs
            if ref in controls_by_ref
        ]
        for left_ref, right_ref in itertools.combinations(refs, 2):
            left = controls_by_ref[left_ref]
            right = controls_by_ref[right_ref]
            pairs.append((left.hint_id, right.hint_id))
    return pairs


def _control_type_from_hint(
    hint: ControlCapabilityHint,
    element: DiscoveredElement | None,
) -> str:
    if hint.capability_kind == "control_select":
        return "select"
    if hint.capability_kind == "control_toggle":
        return "toggle"
    if element is not None:
        return _fillable_control_type(element)
    return "text_input"


def _adapter_type_from_hint(
    hint: ControlCapabilityHint,
    element: DiscoveredElement,
) -> str:
    if hint.adapter_type == "unsupported":
        return "unsupported"
    if hint.capability_kind == "control_select":
        return "select" if element.tag == "select" and element.element_value else "unsupported"
    if hint.capability_kind == "control_toggle":
        return "toggle" if element.element_value else "unsupported"
    control_type = _fillable_control_type(element)
    return _adapter_type_for_fillable(control_type, element)


def _binding_value_from_hint(
    hint: ControlCapabilityHint,
    element: DiscoveredElement,
) -> str:
    if hint.capability_kind in {"control_select", "control_toggle"}:
        return str(element.element_value or "").strip()
    return _default_value_for(element, _human_label(element, fallback=hint.hint_id))


def _default_source_from_hint(hint: ControlCapabilityHint) -> str | None:
    if hint.sample_value_source_refs:
        return "capability_hint"
    return None


def _scenario(
    *,
    discovery_batch_id: str,
    scenario_kind: ScenarioKind,
    capabilities: list[FilterCapability],
) -> CapabilityScenario:
    source_ids = [capability.capability_id for capability in capabilities]
    label = _scenario_label(scenario_kind, capabilities)
    scenario_id = _stable_id(discovery_batch_id, scenario_kind, *source_ids)
    fill_values: dict[str, str] = {}
    toggle_values: dict[str, str] = {}
    bindings: list[dict[str, str]] = []
    for capability in capabilities:
        binding = {
            "capability_id": capability.capability_id,
            "adapter_type": capability.adapter_type,
            "binding_key": capability.binding_key,
            "value": capability.binding_value,
            "selector": capability.control_ref,
            "label": capability.human_label,
        }
        bindings.append(binding)
        if capability.adapter_type == "toggle":
            toggle_values[capability.binding_key] = capability.binding_value
        else:
            fill_values[capability.binding_key] = capability.binding_value

    return CapabilityScenario(
        scenario_id=scenario_id,
        capability_id=source_ids[0] if len(source_ids) == 1 else scenario_id,
        scenario_kind=scenario_kind,
        human_label=label,
        input_bindings=bindings,
        expected_observation_target={"kind": "generic_result_change"},
        discovery_batch_id=discovery_batch_id,
        source_capability_ids=source_ids,
        fill_values=fill_values,
        toggle_values=toggle_values,
    )


def _capability(
    *,
    analysis: PageAnalysis,
    element: DiscoveredElement,
    index: int,
    kind: str,
    human_label: str,
    control_type: str,
    adapter_type: str,
    supported: bool,
    support_reason: str,
    submit_ref: str | None,
    binding_key: str,
    binding_value: str,
) -> FilterCapability:
    capability_id = _stable_id(
        analysis.url,
        element.selector,
        human_label,
        control_type,
        str(index),
    )
    return FilterCapability(
        capability_id=capability_id,
        kind=kind,
        human_label=human_label,
        control_ref=element.selector,
        control_type=control_type,
        adapter_type=adapter_type,
        supported=supported,
        support_reason=support_reason,
        default_test_value_source=("generated" if binding_value else None),
        submit_ref=submit_ref,
        observation_target={"kind": "generic_result_change"},
        binding_key=binding_key,
        binding_value=binding_value,
    )


def _scenario_label(kind: ScenarioKind, capabilities: list[FilterCapability]) -> str:
    labels = [capability.human_label for capability in capabilities]
    if kind == "single_filter":
        return f"Search by {labels[0]}"
    if kind == "pairwise_filter":
        return "Search by " + " + ".join(labels)
    return "Search with all supported filters"


def _submit_ref(analysis: PageAnalysis) -> str | None:
    if analysis.submit:
        return analysis.submit[0].selector
    for element in analysis.clickable:
        text = (element.text or element.aria_label or "").lower()
        if any(token in text for token in ("search", "submit", "apply", "搜索", "查询")):
            return element.selector
    return None


def _human_label(element: DiscoveredElement, *, fallback: str) -> str:
    for raw in (
        element.label_text,
        element.placeholder,
        element.aria_label,
        element.text,
        element.name,
        element.id,
    ):
        value = str(raw or "").strip()
        if value:
            return value[:80]
    return fallback


def _binding_key_for(element: DiscoveredElement, *, fallback: str) -> str:
    if element.semantic_role and element.semantic_role != "text":
        return element.semantic_role
    for raw in (element.name, element.id, element.label_text, element.placeholder):
        key = _slug(raw)
        if key:
            return key
    return fallback


def _unique_binding_key(key: str, used: set[str]) -> str:
    base = _slug(key) or "filter"
    candidate = base
    index = 2
    while candidate in used:
        candidate = f"{base}_{index}"
        index += 1
    used.add(candidate)
    return candidate


def _slug(value: str | None) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    asciiish = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    if asciiish:
        return asciiish[:60]
    compact = re.sub(r"[\s，。,.；;!！?？:：\"'“”‘’（）()\[\]{}]+", "", text)
    return compact[:20]


def _fillable_control_type(element: DiscoveredElement) -> str:
    role = (element.role or "").lower()
    element_type = (element.element_type or "").lower()
    if role == "combobox":
        return "combobox"
    if role == "searchbox" or element_type == "search":
        return "search_input"
    if element_type in {"date", "month"}:
        return f"{element_type}_picker"
    if element.readonly and _looks_like_month_picker(element):
        return "month_picker"
    if element.readonly and _looks_like_date_picker(element):
        return "date_picker"
    return "text_input"


def _adapter_type_for_fillable(control_type: str, element: DiscoveredElement) -> str:
    if control_type == "combobox":
        return "unsupported"
    if control_type in {"date_picker", "month_picker"} or element.readonly:
        return "set_value"
    return "fill"


def _default_value_for(element: DiscoveredElement, label: str) -> str:
    element_type = (element.element_type or "").lower()
    role = (element.semantic_role or "").lower()
    if element_type == "email" or role == "email":
        return "user@example.test"
    if element_type == "date" or _looks_like_date_picker(element):
        return "2026-01-01"
    if element_type == "month" or _looks_like_month_picker(element):
        return "2026-01"
    seed = _slug(label) or _slug(element.name) or _slug(element.id) or "filter"
    return f"test_{seed}"[:80]


def _has_filter_signal(element: DiscoveredElement) -> bool:
    if element.label_text or element.placeholder or element.name:
        return True
    if element.semantic_role and element.semantic_role != "text":
        return True
    element_id = str(element.id or "")
    if element_id and not re.fullmatch(r"rc_select_\d+", element_id):
        return True
    return False


def _looks_like_date_picker(element: DiscoveredElement) -> bool:
    text = " ".join(
        str(value or "")
        for value in (element.element_type, element.placeholder, element.label_text, element.id)
    ).lower()
    return any(token in text for token in ("date", "日期", "请选择日期"))


def _looks_like_month_picker(element: DiscoveredElement) -> bool:
    text = " ".join(
        str(value or "")
        for value in (element.element_type, element.placeholder, element.label_text, element.id)
    ).lower()
    return any(token in text for token in ("month", "月份", "请选择月份"))


def _stable_id(*parts: str) -> str:
    payload = "\n".join(str(part or "") for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
