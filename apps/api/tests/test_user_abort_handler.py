"""Tests for M12.2 user abort / stop handler."""

from __future__ import annotations

import copy
import inspect

from app.services.recovery import abort_handler as handler_module
from app.services.recovery.abort_handler import handle_user_abort


def _make_signal(source: str = "slash_abort", raw_text: str = "/abort") -> dict[str, object]:
    return {"source": source, "raw_text": raw_text}


def _make_state(**kwargs: object) -> dict[str, object]:
    defaults: dict[str, object] = {
        "session_status": "executing",
        "active_command": "replay",
        "has_inflight_action": False,
    }
    defaults.update(kwargs)
    return defaults


def handle(signal: dict[str, object], state: dict[str, object]):
    return handle_user_abort(signal, state)


def test_abort_while_executing_returns_accepted_stop() -> None:
    result = handle(
        _make_signal("slash_abort", "/abort"),
        _make_state(session_status="executing", has_inflight_action=False),
    )

    assert result.decision == "accepted_stop"
    assert result.no_new_actions_after is True
    assert result.inflight_caveat is False
    assert "abort accepted" in result.message.lower()
    assert "no new browser actions" in result.message.lower()


def test_abort_with_inflight_action_returns_cannot_interrupt() -> None:
    result = handle(
        _make_signal("ui_stop_button"),
        _make_state(session_status="executing", has_inflight_action=True),
    )

    assert result.decision == "cannot_interrupt_inflight_action"
    assert result.no_new_actions_after is True
    assert result.inflight_caveat is True
    assert "in flight" in result.message.lower()
    assert "no new actions" in result.message.lower()


def test_abort_after_finished_returns_already_finished() -> None:
    result = handle(
        _make_signal("slash_stop", "/stop"),
        _make_state(session_status="execution_finished", has_inflight_action=False),
    )

    assert result.decision == "already_finished"
    assert result.no_new_actions_after is False
    assert result.inflight_caveat is False
    assert "already finished" in result.message.lower()


def test_abort_after_failed_returns_already_failed() -> None:
    result = handle(
        _make_signal("user_message", "stop"),
        _make_state(session_status="execution_failed", has_inflight_action=False),
    )

    assert result.decision == "already_failed"
    assert result.no_new_actions_after is False
    assert result.inflight_caveat is False
    assert "already failed" in result.message.lower()


def test_abort_when_not_running_returns_not_running() -> None:
    result = handle(
        _make_signal("slash_abort"),
        _make_state(session_status="idle", has_inflight_action=False),
    )

    assert result.decision == "not_running"
    assert result.no_new_actions_after is False
    assert result.inflight_caveat is False
    assert "no active automation" in result.message.lower()


def test_abort_when_no_status_returns_not_running() -> None:
    result = handle(
        _make_signal("external_scheduler"),
        _make_state(session_status=None, has_inflight_action=False),
    )

    assert result.decision == "not_running"


def test_unknown_status_returns_needs_manual_review_fail_closed() -> None:
    result = handle(
        _make_signal("user_message", "halt"),
        _make_state(session_status="unknown_state", has_inflight_action=False),
    )

    assert result.decision == "needs_manual_review"
    assert result.no_new_actions_after is True
    assert result.inflight_caveat is False
    assert "manual review" in result.message.lower()


def test_repeated_abort_is_idempotent() -> None:
    signal = _make_signal("slash_abort")
    state = _make_state(session_status="executing", has_inflight_action=False)

    r1 = handle(signal, state)
    r2 = handle(signal, state)

    assert r1.decision == r2.decision
    assert r1.message == r2.message
    assert r1.no_new_actions_after == r2.no_new_actions_after
    assert r1.inflight_caveat == r2.inflight_caveat


def test_abort_does_not_mutate_input() -> None:
    signal = _make_signal("slash_abort", "/abort")
    state = _make_state(session_status="executing")
    signal_orig = copy.deepcopy(signal)
    state_orig = copy.deepcopy(state)

    handle(signal, state)

    assert signal == signal_orig
    assert state == state_orig


def test_abort_preserves_evidence() -> None:
    signal = _make_signal("ui_stop_button")
    state = _make_state(
        session_status="replay_running",
        active_command="replay",
        active_plan_id="plan-001",
        active_step_index=3,
        replay_status="in_progress",
        has_inflight_action=True,
    )

    result = handle(signal, state)

    assert result.evidence.signal.source == "ui_stop_button"
    assert result.evidence.state.session_status == "replay_running"
    assert result.evidence.state.active_plan_id == "plan-001"
    assert result.evidence.state.active_step_index == 3
    assert result.evidence.state.replay_status == "in_progress"


def test_accepted_stop_blocks_new_actions() -> None:
    for status in ("executing", "replay_running", "plan_confirmed", "paused"):
        result = handle(
            _make_signal("slash_abort"),
            _make_state(session_status=status, has_inflight_action=False),
        )
        assert result.decision == "accepted_stop"
        assert result.no_new_actions_after is True


def test_pre_execution_states_are_not_active() -> None:
    """awaiting_confirmation and task_intake are pre-execution states."""
    for status in ("awaiting_confirmation", "task_intake"):
        result = handle(
            _make_signal("slash_abort"),
            _make_state(session_status=status, has_inflight_action=False),
        )
        assert result.decision == "needs_manual_review"
        assert result.no_new_actions_after is True


def test_needs_manual_review_preserves_inflight_caveat() -> None:
    """Unknown state + has_inflight_action must still record the caveat."""
    result = handle(
        _make_signal("slash_abort"),
        _make_state(session_status="unknown_state", has_inflight_action=True),
    )

    assert result.decision == "needs_manual_review"
    assert result.no_new_actions_after is True
    assert result.inflight_caveat is True


def test_inflight_caveat_only_for_has_inflight_action() -> None:
    result_with = handle(
        _make_signal("slash_abort"),
        _make_state(session_status="executing", has_inflight_action=True),
    )
    result_without = handle(
        _make_signal("slash_abort"),
        _make_state(session_status="executing", has_inflight_action=False),
    )

    assert result_with.inflight_caveat is True
    assert result_without.inflight_caveat is False


def test_abort_does_not_call_recovery_classifier() -> None:
    """Abort handler must not import or invoke 12.1 recovery boundary classifier."""
    source = inspect.getsource(handler_module)
    forbidden = [
        "RecoveryBoundaryClassifier",
        "classify_recovery_boundary",
        "RecoveryBoundary",
        "suggest_reteach",
        "retry_possible_requires_confirmation",
    ]
    for token in forbidden:
        assert token not in source, f"abort_handler.py must not reference {token}"


def test_abort_handler_has_no_forbidden_dependencies() -> None:
    """Scan for runtime side-effect imports in the handler module."""
    source = inspect.getsource(handler_module)
    import app.services.recovery as recovery_module

    init_source = inspect.getsource(recovery_module)
    combined = source + init_source
    forbidden_tokens = [
        "learned_path_replay",
        "run_replay",
        "autonomous_explorer",
        "/exploration/autonomous-runs",
        "llm_provider",
        "OpenAI",
        "sqlalchemy",
        "Session",
        "playwright",
        "requests",
        "httpx",
        "ConversationOrchestrator",
    ]
    for token in forbidden_tokens:
        assert token not in combined


def test_pause_status_returns_accepted_stop() -> None:
    """Paused sessions are still active; abort should be accepted."""
    result = handle(
        _make_signal("slash_abort"),
        _make_state(session_status="paused", has_inflight_action=False),
    )

    assert result.decision == "accepted_stop"


def test_replay_requested_status_returns_accepted_stop() -> None:
    result = handle(
        _make_signal("slash_abort"),
        _make_state(session_status="replay_requested", has_inflight_action=False),
    )

    assert result.decision == "accepted_stop"
