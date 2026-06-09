"""Derive bounded composition requirements from user goal and graph."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.learning.capability_graph import CapabilityGraph

FAMILY_REQUIRED_KINDS: dict[str, list[str]] = {
    "filters_then_submit": ["control_input", "submit_search"],
    "filters_then_export": ["control_input", "export_download"],
    "filter_then_open_detail": ["control_input", "open_detail"],
    "reset_after_filters": ["control_input", "reset_filters"],
}


@dataclass(frozen=True)
class CompositionRequirements:
    required_families: list[str] = field(default_factory=list)
    required_capability_kinds_by_family: dict[str, list[str]] = field(default_factory=dict)
    slot_requirements_by_family: dict[str, list[str]] = field(default_factory=dict)
    risk_constraints_by_family: dict[str, str] = field(default_factory=dict)
    rejection_reasons: list[str] = field(default_factory=list)


class CompositionRequirementDeriver:
    def derive(
        self,
        *,
        user_goal: str,
        graph: CapabilityGraph,
        requested_families: list[str] | None = None,
    ) -> CompositionRequirements:
        families = list(
            dict.fromkeys(requested_families or _derive_required_families(user_goal))
        )
        accepted: list[str] = []
        required_kinds: dict[str, list[str]] = {}
        slot_requirements: dict[str, list[str]] = {}
        risk_constraints: dict[str, str] = {}
        rejection_reasons: list[str] = []

        for family in families:
            kinds = FAMILY_REQUIRED_KINDS.get(family)
            if not kinds:
                rejection_reasons.append(f"unsupported candidate family: {family}")
                continue
            missing_terminal = [
                kind
                for kind in kinds
                if _is_terminal_kind(kind) and not graph.capabilities_by_kind.get(kind)
            ]
            if missing_terminal:
                rejection_reasons.append(
                    f"missing terminal capability for required family: {family}"
                )
                continue
            accepted.append(family)
            required_kinds[family] = kinds
            slot_requirements[family] = _slot_requirements_for_family(graph, kinds)
            risk_constraints[family] = "low"

        return CompositionRequirements(
            required_families=accepted,
            required_capability_kinds_by_family=required_kinds,
            slot_requirements_by_family=slot_requirements,
            risk_constraints_by_family=risk_constraints,
            rejection_reasons=rejection_reasons,
        )


def _derive_required_families(user_goal: str) -> list[str]:
    normalized = user_goal.lower()
    if _contains_any(normalized, ("export", "download", "导出", "下载")):
        return ["filters_then_export"]
    if _contains_any(normalized, ("detail", "open", "详情", "打开", "查看")):
        return ["filter_then_open_detail"]
    if _contains_any(normalized, ("reset", "重置", "清空")):
        return ["reset_after_filters"]
    if _contains_any(
        normalized,
        ("filter", "search", "submit", "搜索", "查询", "筛选", "过滤", "提交"),
    ):
        return ["filters_then_submit"]
    return []


def _contains_any(value: str, terms: tuple[str, ...]) -> bool:
    return any(term in value for term in terms)


def _slot_requirements_for_family(
    graph: CapabilityGraph,
    kinds: list[str],
) -> list[str]:
    slots: dict[str, None] = {}
    for kind in kinds:
        for capability in graph.capabilities_by_kind.get(kind, []):
            for slot in (capability.action_schema_json or {}).get("required_slots", []):
                slots[str(slot)] = None
    return list(slots)


def _is_terminal_kind(kind: str) -> bool:
    return kind in {
        "submit_search",
        "reset_filters",
        "open_detail",
        "export_download",
        "show_modal_or_toast",
    }
