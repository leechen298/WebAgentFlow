"""Deterministic runtime composition of LearnedCapability assets."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from app.models.learned_capability import LearnedCapability
from app.models.learned_path import LearnedPath, TrustStatus
from app.schemas.capability_composition import (
    CapabilityCompositionPlan,
    CapabilityCompositionPolicy,
    CapabilityCompositionRequest,
    CapabilityCompositionResult,
    CapabilityCompositionStep,
    CapabilityExecutionHandoff,
    CapabilityPromotionDecision,
)

ADAPTER_OPERATION_MAP = {
    "input": "set_value",
    "text": "set_value",
    "date": "set_value",
    "month": "set_value",
    "toggle": "click",
}


@dataclass(frozen=True)
class CandidateReview:
    accepted: list[LearnedCapability] = field(default_factory=list)
    missing_kinds: list[str] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)
    ambiguous: bool = False
    unsafe: bool = False


class CapabilityComposer:
    def __init__(self, policy: CapabilityCompositionPolicy | None = None) -> None:
        self.policy = policy or CapabilityCompositionPolicy()

    def compose(
        self,
        request: CapabilityCompositionRequest,
        *,
        candidates: list[LearnedCapability],
        preferred_learned_path: LearnedPath | None = None,
    ) -> CapabilityCompositionResult:
        if not request.required_capability_kinds:
            return CapabilityCompositionResult(
                plan=_base_plan(
                    request,
                    status="unsupported",
                    rejection_reasons=["no required capability kinds requested"],
                    confidence="low",
                    risk_level="medium",
                )
            )

        if _is_preferred_learned_path(preferred_learned_path, request):
            return CapabilityCompositionResult(
                plan=_base_plan(
                    request,
                    status="prefer_learned_path",
                    preferred_learned_path_id=str(preferred_learned_path.id),
                    confidence="high",
                    risk_level="low",
                    warnings=["existing high-confidence LearnedPath preferred"],
                )
            )

        review = self._review_candidates(request, candidates)
        if review.unsafe:
            return CapabilityCompositionResult(
                plan=_base_plan(
                    request,
                    status="unsafe",
                    rejection_reasons=review.rejection_reasons,
                    confidence="low",
                    risk_level="high",
                )
            )
        if review.ambiguous:
            return CapabilityCompositionResult(
                plan=_base_plan(
                    request,
                    status="ambiguous",
                    rejection_reasons=review.rejection_reasons,
                    confidence="low",
                    risk_level="medium",
                )
            )
        if review.missing_kinds:
            return CapabilityCompositionResult(
                plan=_base_plan(
                    request,
                    status="missing_capability",
                    missing_capabilities=review.missing_kinds,
                    rejection_reasons=review.rejection_reasons,
                    confidence="low",
                    risk_level="medium",
                )
            )

        ordered = _order_capabilities(review.accepted)
        plan = _ready_plan(request, ordered)
        return CapabilityCompositionResult(
            plan=plan,
            execution_handoff=CapabilityExecutionHandoff(
                composition_id=plan.composition_id,
                source_capability_ids=plan.source_capability_ids,
                ordered_action_schemas=[
                    _execution_action_schema(capability) for capability in ordered
                ],
                slot_bindings=dict(request.slot_bindings),
                expected_terminal_target=dict(plan.expected_terminal_target),
            ),
        )

    def _review_candidates(
        self,
        request: CapabilityCompositionRequest,
        candidates: list[LearnedCapability],
    ) -> CandidateReview:
        required = list(dict.fromkeys(request.required_capability_kinds))
        accepted_by_kind: dict[str, list[LearnedCapability]] = {kind: [] for kind in required}
        rejection_reasons: list[str] = []
        unsafe = False

        for capability in candidates:
            reason = self._candidate_rejection_reason(request, capability)
            if reason is not None:
                rejection_reasons.append(reason)
                if (
                    reason.startswith("cross-page")
                    or reason.startswith("query-signature")
                    or reason.startswith("dom-fingerprint")
                ):
                    unsafe = True
                continue
            kind = str(capability.capability_kind)
            if kind in accepted_by_kind:
                accepted_by_kind[kind].append(capability)

        missing = [kind for kind, rows in accepted_by_kind.items() if not rows]
        ambiguous = any(len(rows) > 1 for rows in accepted_by_kind.values())
        if ambiguous:
            rejection_reasons.append("ambiguous candidate capabilities for required kind")
        accepted = [rows[0] for rows in accepted_by_kind.values() if rows]
        if _has_control_conflict(accepted):
            return CandidateReview(
                rejection_reasons=[
                    *rejection_reasons,
                    "conflicting capabilities write to the same control",
                ],
                unsafe=True,
            )
        return CandidateReview(
            accepted=accepted,
            missing_kinds=missing,
            rejection_reasons=rejection_reasons,
            ambiguous=ambiguous,
            unsafe=unsafe,
        )

    def _candidate_rejection_reason(
        self,
        request: CapabilityCompositionRequest,
        capability: LearnedCapability,
    ) -> str | None:
        if capability.page_template != request.page_template:
            return f"cross-page capability rejected: {capability.id}"
        if dict(capability.query_signature or {}) != dict(request.query_signature or {}):
            return f"query-signature mismatch rejected: {capability.id}"
        if self.policy.require_dom_fingerprint_match:
            if not request.dom_fingerprint:
                return f"dom-fingerprint missing from request: {capability.id}"
            if capability.dom_fingerprint != request.dom_fingerprint:
                return f"dom-fingerprint mismatch rejected: {capability.id}"
        if (
            str(capability.trust) == TrustStatus.PROVISIONAL
            and not self.policy.allow_provisional_trust
        ):
            return f"provisional capability rejected by policy: {capability.id}"
        if str(capability.trust) in {TrustStatus.FLAKY, TrustStatus.DEPRECATED}:
            return f"low-trust capability rejected: {capability.id}"
        action_schema = dict(capability.action_schema_json or {})
        if action_schema.get("version") not in set(self.policy.supported_action_versions):
            return f"unsupported action schema version: {capability.id}"
        adapter_type = str(action_schema.get("adapter_type") or capability.adapter_type or "")
        if adapter_type not in set(self.policy.supported_adapter_types):
            return f"unsupported adapter type: {capability.id}"
        operation = _executable_operation(action_schema, adapter_type)
        if operation not in set(self.policy.supported_operations):
            return f"unsupported operation: {capability.id}"
        missing_slots = [
            slot
            for slot in action_schema.get("required_slots", [])
            if str(slot) not in request.slot_bindings
        ]
        if missing_slots:
            missing = ", ".join(str(slot) for slot in missing_slots)
            return f"missing required slot {missing}: {capability.id}"
        evidence = dict(capability.evidence_json or {})
        terminal_outcome = str(evidence.get("terminal_outcome") or "")
        if terminal_outcome in {"terminal_unverified", "terminal_failed"}:
            return f"insufficient terminal evidence: {capability.id}"
        if terminal_outcome not in {"terminal_detected", "success"}:
            return f"missing successful terminal evidence: {capability.id}"
        if not str(evidence.get("evidence_strength") or ""):
            return f"missing evidence strength: {capability.id}"
        terminal_target = dict(capability.terminal_target_json or {})
        if not terminal_target or not str(terminal_target.get("kind") or ""):
            return f"missing terminal target: {capability.id}"
        return None


def evaluate_composition_promotion(
    plan: CapabilityCompositionPlan,
    execution_evidence: dict[str, Any],
) -> CapabilityPromotionDecision:
    reasons: list[str] = []
    if plan.status != "ready":
        reasons.append("composition plan is not ready")
    if execution_evidence.get("composition_id") != plan.composition_id:
        reasons.append("execution evidence composition_id mismatch")
    if execution_evidence.get("status") != "success":
        reasons.append("execution evidence is not successful")
    terminal = execution_evidence.get("terminal_target") or {}
    if not terminal:
        reasons.append("missing terminal evidence")
    elif not _terminal_target_matches(plan.expected_terminal_target, terminal):
        reasons.append("terminal evidence is incompatible with composition plan")
    source_ids = list(execution_evidence.get("source_capability_ids") or [])
    if not source_ids:
        reasons.append("missing source capability ids")
    if reasons:
        return CapabilityPromotionDecision(
            promotable=False,
            composition_id=plan.composition_id,
            source_capability_ids=source_ids,
            rejection_reasons=reasons,
        )
    return CapabilityPromotionDecision(
        promotable=True,
        composition_id=plan.composition_id,
        source_capability_ids=source_ids,
        learned_path_metadata={
            "composition_id": plan.composition_id,
            "composition_policy_version": "capability_composition_policy.v1",
            "source_capability_ids": source_ids,
            "terminal_target": terminal,
        },
    )


def _is_preferred_learned_path(
    path: LearnedPath | None,
    request: CapabilityCompositionRequest,
) -> bool:
    if path is None or str(path.trust) != TrustStatus.CONFIRMED:
        return False
    if path.page_template != request.page_template:
        return False
    if dict(path.query_signature or {}) != dict(request.query_signature or {}):
        return False
    if not request.dom_fingerprint:
        return False
    if path.dom_fingerprint != request.dom_fingerprint:
        return False
    return True


def _terminal_target_matches(
    expected: dict[str, Any],
    observed: dict[str, Any],
) -> bool:
    expected_kind = str(expected.get("kind") or "")
    observed_kind = str(observed.get("kind") or "")
    if not expected_kind or expected_kind == "unknown":
        return bool(observed_kind)
    return expected_kind == observed_kind


def _base_plan(
    request: CapabilityCompositionRequest,
    *,
    status: str,
    source_capability_ids: list[str] | None = None,
    ordered_steps: list[CapabilityCompositionStep] | None = None,
    expected_terminal_target: dict[str, Any] | None = None,
    missing_capabilities: list[str] | None = None,
    rejection_reasons: list[str] | None = None,
    warnings: list[str] | None = None,
    preferred_learned_path_id: str | None = None,
    risk_level: str = "medium",
    confidence: str = "medium",
) -> CapabilityCompositionPlan:
    return CapabilityCompositionPlan(
        composition_id=_composition_id(request, *(source_capability_ids or [])),
        target_url=request.target_url,
        page_template=request.page_template,
        user_goal=request.user_goal,
        status=status,  # type: ignore[arg-type]
        source_capability_ids=source_capability_ids or [],
        ordered_steps=ordered_steps or [],
        expected_terminal_target=expected_terminal_target or {},
        missing_capabilities=missing_capabilities or [],
        rejection_reasons=rejection_reasons or [],
        warnings=warnings or [],
        preferred_learned_path_id=preferred_learned_path_id,
        risk_level=risk_level,  # type: ignore[arg-type]
        confidence=confidence,  # type: ignore[arg-type]
    )


def _ready_plan(
    request: CapabilityCompositionRequest,
    capabilities: list[LearnedCapability],
) -> CapabilityCompositionPlan:
    steps = [
        CapabilityCompositionStep(
            step_id=_step_id(index, capability),
            source_capability_id=str(capability.id),
            capability_kind=str(capability.capability_kind),
            action_kind=_executable_operation(
                dict(capability.action_schema_json or {}),
                str(
                    (capability.action_schema_json or {}).get("adapter_type")
                    or capability.adapter_type
                    or ""
                ),
            ),
            required_slots=[
                str(slot)
                for slot in (capability.action_schema_json or {}).get("required_slots", [])
            ],
            slot_refs=[
                str(slot)
                for slot in (capability.action_schema_json or {}).get("required_slots", [])
            ],
            terminal_target_kind=str((capability.terminal_target_json or {}).get("kind") or ""),
        )
        for index, capability in enumerate(capabilities, start=1)
    ]
    source_ids = [str(capability.id) for capability in capabilities]
    terminal_target = dict(capabilities[-1].terminal_target_json or {}) if capabilities else {}
    return _base_plan(
        request,
        status="ready",
        source_capability_ids=source_ids,
        ordered_steps=steps,
        expected_terminal_target={"kind": terminal_target.get("kind", "unknown")},
        risk_level="low" if len(capabilities) <= 2 else "medium",
        confidence="high",
    )


def _order_capabilities(capabilities: list[LearnedCapability]) -> list[LearnedCapability]:
    order = {
        "switch_tab": 0,
        "control_input": 10,
        "control_select": 10,
        "control_toggle": 10,
        "submit_search": 20,
        "reset_filters": 20,
        "export_download": 20,
        "open_detail": 20,
        "show_modal_or_toast": 20,
    }
    return sorted(
        capabilities,
        key=lambda row: (order.get(str(row.capability_kind), 50), str(row.id)),
    )


def _has_control_conflict(capabilities: list[LearnedCapability]) -> bool:
    seen: set[str] = set()
    for capability in capabilities:
        control_ref = str(capability.control_ref or "")
        if capability.capability_kind in {"submit_search", "reset_filters"}:
            continue
        if control_ref in seen:
            return True
        seen.add(control_ref)
    return False


def _execution_action_schema(capability: LearnedCapability) -> dict[str, Any]:
    action_schema = dict(capability.action_schema_json or {})
    adapter_type = str(action_schema.get("adapter_type") or capability.adapter_type or "")
    action_schema["operation"] = _executable_operation(action_schema, adapter_type)
    return action_schema


def _executable_operation(action_schema: dict[str, Any], adapter_type: str) -> str:
    operation = str(action_schema.get("operation") or "").strip()
    mapped = ADAPTER_OPERATION_MAP.get(adapter_type)
    if mapped and operation == adapter_type:
        return mapped
    return mapped or operation


def _composition_id(
    request: CapabilityCompositionRequest,
    *source_capability_ids: str,
) -> str:
    payload = "\n".join(
        [
            request.page_template,
            request.user_goal,
            *request.required_capability_kinds,
            *source_capability_ids,
        ]
    )
    return f"composition_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _step_id(index: int, capability: LearnedCapability) -> str:
    payload = f"{index}\n{capability.id}\n{capability.capability_kind}"
    return f"step_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"
