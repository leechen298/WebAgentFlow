"""Page-scoped graph projection for composition candidate generation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from app.models.learned_capability import LearnedCapability

TERMINAL_CAPABILITY_KINDS = frozenset(
    {
        "submit_search",
        "reset_filters",
        "open_detail",
        "export_download",
        "show_modal_or_toast",
    }
)


@dataclass(frozen=True)
class CapabilityGraph:
    capabilities: list[LearnedCapability] = field(default_factory=list)
    capabilities_by_kind: dict[str, list[LearnedCapability]] = field(default_factory=dict)
    terminal_action_candidates: list[LearnedCapability] = field(default_factory=list)
    rejected_capability_reasons: dict[str, str] = field(default_factory=dict)

    def public_summary(self) -> dict[str, Any]:
        return {
            "capability_count": len(self.capabilities),
            "capability_kind_counts": {
                kind: len(rows) for kind, rows in self.capabilities_by_kind.items()
            },
            "terminal_action_candidate_count": len(self.terminal_action_candidates),
            "rejected_capability_count": len(self.rejected_capability_reasons),
            "rejected_capability_reasons": dict(self.rejected_capability_reasons),
        }


class CapabilityGraphBuilder:
    def build(
        self,
        *,
        page_template: str,
        query_signature: dict[str, Any],
        dom_fingerprint: str | None,
        capabilities: list[LearnedCapability],
    ) -> CapabilityGraph:
        accepted: list[LearnedCapability] = []
        rejected: dict[str, str] = {}
        for index, capability in enumerate(capabilities, start=1):
            reason = _scope_rejection_reason(
                capability,
                page_template=page_template,
                query_signature=query_signature,
                dom_fingerprint=dom_fingerprint,
            )
            if reason is not None:
                rejected[f"capability_ref_{index}"] = reason
                continue
            accepted.append(capability)

        grouped: dict[str, list[LearnedCapability]] = {}
        for capability in accepted:
            grouped.setdefault(str(capability.capability_kind), []).append(capability)

        terminal = [
            capability
            for capability in accepted
            if str(capability.capability_kind) in TERMINAL_CAPABILITY_KINDS
        ]
        return CapabilityGraph(
            capabilities=accepted,
            capabilities_by_kind=grouped,
            terminal_action_candidates=terminal,
            rejected_capability_reasons=rejected,
        )


def _scope_rejection_reason(
    capability: LearnedCapability,
    *,
    page_template: str,
    query_signature: dict[str, Any],
    dom_fingerprint: str | None,
) -> str | None:
    if capability.page_template != page_template:
        return "cross-page capability rejected"
    if dict(capability.query_signature or {}) != dict(query_signature or {}):
        return "query-signature mismatch rejected"
    if dom_fingerprint is not None and capability.dom_fingerprint != dom_fingerprint:
        return "dom-fingerprint mismatch rejected"
    return None


def redacted_capability_ref(capability_id: str) -> str:
    digest = hashlib.sha256(capability_id.encode("utf-8")).hexdigest()[:12]
    return f"capability_ref_{digest}"
