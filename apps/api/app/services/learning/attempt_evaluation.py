"""Deterministic attempt ingest gate."""

from __future__ import annotations

from typing import Any

from app.schemas.attempt_evaluation import AttemptIngestEvaluation

_EFFECTIVE_ACTION_TYPES = {
    "fill",
    "set_value",
    "select",
    "select_first_option",
    "click",
    "press",
}
_ACTION_CORRELATED_TERMINAL_TYPES = {
    "navigation",
    "list_refresh",
    "network_completion",
    "modal_or_popup_opened",
    "browser_dialog",
    "download_started",
    "artifact_available",
    "region_changed",
}


def evaluate_attempt_ingest(
    *,
    pass_gate_status: str | None,
    terminal_state_verdict: dict[str, Any] | None,
    actions: list[dict[str, Any]] | None,
) -> AttemptIngestEvaluation:
    """Evaluate whether an attempt may be ingested as a successful LearnedPath."""
    effective_action_count = _effective_action_count(actions)
    if pass_gate_status != "pass":
        ingest_status = (
            "unverified" if pass_gate_status in {None, "unverified"} else "ineligible"
        )
        return AttemptIngestEvaluation(
            ingest_status=ingest_status,
            attempt_outcome="unverified" if pass_gate_status != "fail" else "failed",
            failure_category="pass_gate_not_pass",
            reasons=["pass_gate_status_is_not_pass"],
            pass_gate_status=pass_gate_status,
            effective_action_count=effective_action_count,
        )

    if not isinstance(terminal_state_verdict, dict):
        return AttemptIngestEvaluation(
            ingest_status="unverified",
            attempt_outcome="unverified",
            failure_category="missing_terminal_evidence",
            reasons=["terminal_state_verdict_missing"],
            pass_gate_status=pass_gate_status,
            effective_action_count=effective_action_count,
        )

    terminal_outcome = _str_or_none(terminal_state_verdict.get("terminal_outcome"))
    terminal_type = _str_or_none(terminal_state_verdict.get("terminal_type"))
    evidence_strength = _str_or_none(terminal_state_verdict.get("evidence_strength"))
    stop_decision = _str_or_none(terminal_state_verdict.get("stop_decision"))

    base = {
        "terminal_outcome": terminal_outcome,
        "terminal_type": terminal_type,
        "evidence_strength": evidence_strength,
        "stop_decision": stop_decision,
        "pass_gate_status": pass_gate_status,
        "effective_action_count": effective_action_count,
    }

    if terminal_outcome == "terminal_failed":
        return AttemptIngestEvaluation(
            ingest_status="ineligible",
            attempt_outcome="failed",
            failure_category="terminal_failed",
            reasons=["terminal_state_failed"],
            **base,
        )

    if terminal_outcome == "not_terminal_yet" or stop_decision in {"wait", "continue"}:
        return AttemptIngestEvaluation(
            ingest_status="unverified",
            attempt_outcome="not_terminal",
            failure_category="terminal_not_reached",
            reasons=["terminal_state_not_reached"],
            **base,
        )

    if terminal_outcome == "terminal_unverified" or stop_decision == "unverified_stop":
        return AttemptIngestEvaluation(
            ingest_status="unverified",
            attempt_outcome="unverified",
            failure_category="terminal_unverified",
            reasons=["terminal_state_unverified"],
            **base,
        )

    if terminal_outcome != "terminal_detected" or stop_decision != "stop":
        return AttemptIngestEvaluation(
            ingest_status="unverified",
            attempt_outcome="unverified",
            failure_category="missing_terminal_evidence",
            reasons=["terminal_state_not_detected_with_stop"],
            **base,
        )

    if evidence_strength not in {"medium", "strong"}:
        return AttemptIngestEvaluation(
            ingest_status="unverified",
            attempt_outcome="unverified",
            failure_category="missing_terminal_evidence",
            reasons=["terminal_evidence_strength_too_weak"],
            **base,
        )

    if (
        terminal_type in _ACTION_CORRELATED_TERMINAL_TYPES
        and not _has_action_correlation(terminal_state_verdict)
    ):
        return AttemptIngestEvaluation(
            ingest_status="unverified",
            attempt_outcome="unverified",
            failure_category="missing_terminal_evidence",
            reasons=["terminal_evidence_not_action_correlated"],
            **base,
        )

    if effective_action_count <= 0:
        return AttemptIngestEvaluation(
            ingest_status="ineligible",
            attempt_outcome="failed",
            failure_category="no_effective_actions",
            reasons=["no_effective_actions"],
            **base,
        )

    return AttemptIngestEvaluation(
        ingest_status="eligible",
        attempt_outcome="success_candidate",
        failure_category="none",
        reasons=[],
        **base,
    )


def _effective_action_count(actions: list[dict[str, Any]] | None) -> int:
    if not isinstance(actions, list):
        return 0
    count = 0
    for action in actions:
        if not isinstance(action, dict):
            continue
        action_type = str(action.get("action_type") or "").lower()
        if action_type in _EFFECTIVE_ACTION_TYPES:
            count += 1
    return count


def _has_action_correlation(terminal_state_verdict: dict[str, Any]) -> bool:
    for key in ("matched_action_ids", "matched_step_indices", "matched_action_types"):
        value = terminal_state_verdict.get(key)
        if isinstance(value, list) and len(value) > 0:
            return True
    return False


def _str_or_none(value: object) -> str | None:
    return str(value) if value is not None else None
