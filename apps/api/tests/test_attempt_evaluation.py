from __future__ import annotations

from app.services.learning.attempt_evaluation import evaluate_attempt_ingest


def _terminal(**overrides) -> dict:
    payload = {
        "terminal_outcome": "terminal_detected",
        "terminal_type": "list_refresh",
        "evidence_strength": "strong",
        "stop_decision": "stop",
        "matched_action_ids": ["action-step-1"],
        "matched_step_indices": [1],
        "matched_action_types": ["click"],
    }
    payload.update(overrides)
    return payload


def _actions() -> list[dict]:
    return [{"action_type": "click", "target_selector": "button[type=submit]"}]


def test_pass_gate_pass_terminal_detected_and_actions_are_eligible() -> None:
    result = evaluate_attempt_ingest(
        pass_gate_status="pass",
        terminal_state_verdict=_terminal(),
        actions=_actions(),
    )

    assert result.ingest_status == "eligible"
    assert result.attempt_outcome == "success_candidate"
    assert result.failure_category == "none"
    assert result.effective_action_count == 1


def test_terminal_unverified_is_not_eligible() -> None:
    result = evaluate_attempt_ingest(
        pass_gate_status="pass",
        terminal_state_verdict=_terminal(
            terminal_outcome="terminal_unverified",
            evidence_strength="weak",
            stop_decision="unverified_stop",
        ),
        actions=_actions(),
    )

    assert result.ingest_status == "unverified"
    assert result.attempt_outcome == "unverified"
    assert result.failure_category == "terminal_unverified"
    assert result.reasons == ["terminal_state_unverified"]


def test_not_terminal_yet_wait_is_not_eligible() -> None:
    result = evaluate_attempt_ingest(
        pass_gate_status="pass",
        terminal_state_verdict=_terminal(
            terminal_outcome="not_terminal_yet",
            evidence_strength="weak",
            stop_decision="wait",
        ),
        actions=_actions(),
    )

    assert result.ingest_status == "unverified"
    assert result.attempt_outcome == "not_terminal"
    assert result.failure_category == "terminal_not_reached"


def test_terminal_failed_is_not_eligible() -> None:
    result = evaluate_attempt_ingest(
        pass_gate_status="pass",
        terminal_state_verdict=_terminal(
            terminal_outcome="terminal_failed",
            terminal_type="terminal_failed",
            stop_decision="unverified_stop",
        ),
        actions=_actions(),
    )

    assert result.ingest_status == "ineligible"
    assert result.attempt_outcome == "failed"
    assert result.failure_category == "terminal_failed"


def test_pass_gate_not_pass_remains_blocking() -> None:
    result = evaluate_attempt_ingest(
        pass_gate_status="fail",
        terminal_state_verdict=_terminal(),
        actions=_actions(),
    )

    assert result.ingest_status == "ineligible"
    assert result.attempt_outcome == "failed"
    assert result.failure_category == "pass_gate_not_pass"


def test_missing_terminal_verdict_is_unverified() -> None:
    result = evaluate_attempt_ingest(
        pass_gate_status="pass",
        terminal_state_verdict=None,
        actions=_actions(),
    )

    assert result.ingest_status == "unverified"
    assert result.attempt_outcome == "unverified"
    assert result.failure_category == "missing_terminal_evidence"


def test_detected_terminal_without_action_correlation_is_unverified() -> None:
    result = evaluate_attempt_ingest(
        pass_gate_status="pass",
        terminal_state_verdict=_terminal(
            matched_action_ids=[],
            matched_step_indices=[],
            matched_action_types=[],
        ),
        actions=_actions(),
    )

    assert result.ingest_status == "unverified"
    assert result.attempt_outcome == "unverified"
    assert result.failure_category == "missing_terminal_evidence"
    assert result.reasons == ["terminal_evidence_not_action_correlated"]


def test_no_effective_actions_are_not_eligible() -> None:
    result = evaluate_attempt_ingest(
        pass_gate_status="pass",
        terminal_state_verdict=_terminal(),
        actions=[{"action_type": "observe"}],
    )

    assert result.ingest_status == "ineligible"
    assert result.attempt_outcome == "failed"
    assert result.failure_category == "no_effective_actions"
