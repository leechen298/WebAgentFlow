"""Tests for M11.0 conversation orchestrator / dispatcher."""

from __future__ import annotations

import inspect
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.repos.conversation_repo import ConversationRepository
from app.schemas.conversation import (
    ConversationEventType,
    ConversationReplaySummary,
)
from app.services.conversation.orchestrator import ConversationOrchestrator


@pytest.fixture
def orchestrator(db_session: Session) -> ConversationOrchestrator:
    repo = ConversationRepository(db_session)
    return ConversationOrchestrator(repo)


@pytest.fixture
def repo(db_session: Session) -> ConversationRepository:
    return ConversationRepository(db_session)


def _create_session(repo: ConversationRepository, status: str = "idle") -> str:
    session = repo.create_session(initial_status=status)
    return session.id


# ── Happy path: free text ─────────────────────────────────────────────────────


def test_free_text_from_idle_records_user_message_and_events_and_status_task_intake(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_session(repo, status="idle")

    result = orchestrator.dispatch_user_input(session_id, "run the user export")

    assert result.allowed is True
    assert result.previous_status == "idle"
    assert result.next_status == "task_intake"
    assert result.command_kind == "free_text"
    assert result.message_id is not None
    assert result.user_response == "Task input recorded."
    assert result.error is None
    assert result.engine_command is None

    # Verify session status updated
    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "task_intake"

    # Verify user message recorded
    messages = repo.list_messages(session_id)
    assert len(messages) == 1
    assert messages[0].role == "user"
    assert messages[0].content == "run the user export"

    # Verify events: command_parsed, message_received, state_changed
    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert ConversationEventType.COMMAND_PARSED.value in event_types
    assert ConversationEventType.MESSAGE_RECEIVED.value in event_types
    assert ConversationEventType.STATE_CHANGED.value in event_types


def test_free_text_from_task_intake_stays_task_intake(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_session(repo, status="task_intake")

    result = orchestrator.dispatch_user_input(session_id, "also export admins")

    assert result.allowed is True
    assert result.next_status == "task_intake"
    assert result.command_kind == "free_text"

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "task_intake"


# ── /status command ────────────────────────────────────────────────────────────


def test_status_records_audit_and_does_not_mutate_status(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_session(repo, status="idle")

    result = orchestrator.dispatch_user_input(session_id, "/status")

    assert result.allowed is True
    assert result.previous_status == "idle"
    assert result.next_status == "idle"
    assert result.command_kind == "status"

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "idle"

    events = repo.list_events(session_id)
    assert len(events) == 1
    assert events[0].type == ConversationEventType.COMMAND_PARSED.value
    assert events[0].payload_json["command_kind"] == "status"


# ── /pause command ─────────────────────────────────────────────────────────────


def test_pause_updates_status_to_paused_and_stores_previous_status(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_session(repo, status="task_intake")

    result = orchestrator.dispatch_user_input(session_id, "/pause")

    assert result.allowed is True
    assert result.previous_status == "task_intake"
    assert result.next_status == "paused"
    assert result.command_kind == "pause"
    assert result.user_response == "Conversation paused."

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "paused"
    assert session.previous_status == "task_intake"

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert ConversationEventType.COMMAND_PARSED.value in event_types
    assert ConversationEventType.PAUSE_REQUESTED.value in event_types
    assert ConversationEventType.STATE_CHANGED.value in event_types


# ── /resume command ────────────────────────────────────────────────────────────


def test_resume_from_paused_returns_to_task_intake_and_clears_previous_status(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_session(repo, status="task_intake")
    orchestrator.dispatch_user_input(session_id, "/pause")

    result = orchestrator.dispatch_user_input(session_id, "/resume")

    assert result.allowed is True
    assert result.previous_status == "paused"
    assert result.next_status == "task_intake"
    assert result.command_kind == "resume"
    assert result.user_response == "Conversation resumed to task intake."

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "task_intake"
    assert session.previous_status is None

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert ConversationEventType.RESUME_REQUESTED.value in event_types
    assert ConversationEventType.STATE_CHANGED.value in event_types


# ── /abort command ─────────────────────────────────────────────────────────────


def test_abort_updates_status_to_abort_requested(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_session(repo, status="task_intake")

    result = orchestrator.dispatch_user_input(session_id, "/abort")

    assert result.allowed is True
    assert result.previous_status == "task_intake"
    assert result.next_status == "abort_requested"
    assert result.command_kind == "abort"
    assert result.user_response == "Abort requested."

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "abort_requested"

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert ConversationEventType.ABORT_REQUESTED.value in event_types
    assert ConversationEventType.STATE_CHANGED.value in event_types


# ── /takeover command ──────────────────────────────────────────────────────────


def test_takeover_updates_status_to_takeover_requested(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_session(repo, status="task_intake")

    result = orchestrator.dispatch_user_input(session_id, "/takeover")

    assert result.allowed is True
    assert result.previous_status == "task_intake"
    assert result.next_status == "takeover_requested"
    assert result.command_kind == "takeover"
    assert result.user_response == "Takeover requested."

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "takeover_requested"

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert ConversationEventType.TAKEOVER_REQUESTED.value in event_types
    assert ConversationEventType.STATE_CHANGED.value in event_types


# ── /cancel command ────────────────────────────────────────────────────────────


def test_cancel_returns_status_to_idle(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_session(repo, status="task_intake")

    result = orchestrator.dispatch_user_input(session_id, "/cancel")

    assert result.allowed is True
    assert result.previous_status == "task_intake"
    assert result.next_status == "idle"
    assert result.command_kind == "cancel"
    assert result.user_response == "Conversation cancelled."

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "idle"
    assert session.previous_status is None

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert ConversationEventType.STATE_CHANGED.value in event_types


# ── Invalid transition ─────────────────────────────────────────────────────────


def test_invalid_transition_returns_allowed_false_and_does_not_update_status(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_session(repo, status="idle")

    result = orchestrator.dispatch_user_input(session_id, "/resume")

    assert result.allowed is False
    assert result.previous_status == "idle"
    assert result.next_status == "idle"
    assert result.command_kind == "resume"
    assert result.error is not None

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "idle"


# ── /replay command ────────────────────────────────────────────────────────────


def test_replay_moves_to_replay_requested_and_does_not_call_replay(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_session(repo, status="idle")

    result = orchestrator.dispatch_user_input(
        session_id, "/replay 11111111-1111-1111-1111-111111111111 http://127.0.0.1:5175/users"
    )

    assert result.allowed is True
    assert result.previous_status == "idle"
    assert result.next_status == "replay_requested"
    assert result.command_kind == "replay"
    assert result.user_response == "Replay command requested."
    assert result.engine_command is None

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "replay_requested"

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert ConversationEventType.REPLAY_REQUESTED.value in event_types
    assert ConversationEventType.STATE_CHANGED.value in event_types


def test_malformed_replay_records_parse_error_and_does_not_update_status(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_session(repo, status="idle")

    result = orchestrator.dispatch_user_input(session_id, "/replay")

    assert result.allowed is False
    assert result.next_status == "idle"
    assert result.command_kind == "error"
    assert result.error is not None

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "idle"

    events = repo.list_events(session_id)
    assert len(events) == 1
    assert events[0].type == ConversationEventType.COMMAND_PARSED.value
    assert events[0].payload_json["parse_error"] is not None
    assert events[0].payload_json["allowed"] is False


# ── Missing session ────────────────────────────────────────────────────────────


def test_missing_session_raises_value_error(
    orchestrator: ConversationOrchestrator,
) -> None:
    with pytest.raises(ValueError, match="session not found: non-existent-id"):
        orchestrator.dispatch_user_input("non-existent-id", "hello")


# ── dispatch_engine_event placeholder ──────────────────────────────────────────


def test_dispatch_engine_event_records_event_and_does_not_mutate_status(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_session(repo, status="idle")

    result = orchestrator.dispatch_engine_event(
        session_id,
        ConversationEventType.MESSAGE_RECEIVED,
        payload={"source": "engine"},
    )

    assert result.allowed is True
    assert result.previous_status == "idle"
    assert result.next_status == "idle"
    assert result.command_kind == "engine_event"
    assert result.user_response == "Engine event received."

    events = repo.list_events(session_id)
    assert len(events) == 1
    assert events[0].type == ConversationEventType.MESSAGE_RECEIVED.value
    assert events[0].payload_json == {"source": "engine"}


def test_dispatch_engine_event_missing_session_raises_value_error(
    orchestrator: ConversationOrchestrator,
) -> None:
    with pytest.raises(ValueError, match="session not found: missing-id"):
        orchestrator.dispatch_engine_event("missing-id", ConversationEventType.MESSAGE_RECEIVED)


# ── Event payload inspection ───────────────────────────────────────────────────


def test_command_parsed_event_contains_full_audit_payload(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_session(repo, status="task_intake")

    orchestrator.dispatch_user_input(session_id, "/pause")

    events = repo.list_events(session_id)
    command_parsed = [e for e in events if e.type == ConversationEventType.COMMAND_PARSED.value][0]
    payload = command_parsed.payload_json

    assert payload["raw"] == "/pause"
    assert payload["command_kind"] == "pause"
    assert payload["args"] == []
    assert payload["allowed"] is True
    assert "transition_error" in payload


def test_state_changed_event_contains_from_to_and_command_kind(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_session(repo, status="task_intake")

    orchestrator.dispatch_user_input(session_id, "/pause")

    events = repo.list_events(session_id)
    state_changed = [e for e in events if e.type == ConversationEventType.STATE_CHANGED.value][0]
    payload = state_changed.payload_json

    assert payload["from"] == "task_intake"
    assert payload["to"] == "paused"
    assert payload["command_kind"] == "pause"


# ── No forbidden imports ───────────────────────────────────────────────────────


def test_orchestrator_does_not_import_replay_autonomous_llm_agent_or_cli() -> None:
    from app.services.conversation import orchestrator as orchestrator_module

    source = inspect.getsource(orchestrator_module)
    forbidden_tokens = [
        "learned_path_replay",
        "run_replay",
        "autonomous_explorer",
        "/exploration/autonomous-runs",
        "llm_provider",
        "OpenAI",
        "apps.cli",
    ]
    for token in forbidden_tokens:
        assert token not in source


# ── 11.1.4 Planning Preview Integration ───────────────────────────────────────


@pytest.fixture
def mock_planning_handler():
    def _handler(raw_input: str):
        from app.services.task_planning.preview import PlanningPreviewResult
        return PlanningPreviewResult(
            user_response=f"Preview for: {raw_input}",
            event_type="plan_preview_proposed",
            event_payload={"task_intent_raw_text": raw_input, "candidate_count": 1},
            confirmation_required=True,
            selected_path_id="lp-001",
        )
    return _handler


def test_free_text_without_planning_handler_keeps_original_behavior(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_session(repo, status="idle")
    result = orchestrator.dispatch_user_input(session_id, "run export")

    assert result.allowed is True
    assert result.next_status == "task_intake"
    assert result.user_response == "Task input recorded."
    assert result.planning_result is None


def test_free_text_with_planning_handler_triggers_preview(
    repo: ConversationRepository,
    mock_planning_handler,
) -> None:
    session_id = _create_session(repo, status="idle")
    orch = ConversationOrchestrator(repo, planning_handler=mock_planning_handler)

    result = orch.dispatch_user_input(session_id, "run export")

    assert result.allowed is True
    assert result.next_status == "awaiting_confirmation"
    assert result.user_response == "Preview for: run export"
    assert result.planning_result is not None
    assert result.planning_result.selected_path_id == "lp-001"

    # Assistant message recorded
    messages = repo.list_messages(session_id)
    assert any(m.role == "agent" and "Preview for:" in m.content for m in messages)

    # Preview event recorded
    events = repo.list_events(session_id)
    assert any(e.type == "plan_preview_proposed" for e in events)

    # State changed to awaiting_confirmation
    assert any(
        e.type == ConversationEventType.STATE_CHANGED.value
        and e.payload_json.get("to") == "awaiting_confirmation"
        for e in events
    )

    # Session status updated
    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "awaiting_confirmation"


def test_free_text_preview_unable_keeps_task_intake(
    repo: ConversationRepository,
) -> None:
    from app.services.task_planning.preview import PlanningPreviewResult

    def unable_handler(raw_input: str):
        return PlanningPreviewResult(
            user_response="Unable to plan: no paths found",
            event_type="plan_preview_unable",
            event_payload={"task_intent_raw_text": raw_input, "candidate_count": 0},
            confirmation_required=False,
        )

    session_id = _create_session(repo, status="idle")
    orch = ConversationOrchestrator(repo, planning_handler=unable_handler)

    result = orch.dispatch_user_input(session_id, "do the impossible")

    assert result.allowed is True
    assert result.next_status == "task_intake"
    assert result.user_response == "Unable to plan: no paths found"

    # Preview event recorded
    events = repo.list_events(session_id)
    assert any(e.type == "plan_preview_unable" for e in events)

    # No state change to awaiting_confirmation
    assert not any(
        e.type == ConversationEventType.STATE_CHANGED.value
        and e.payload_json.get("to") == "awaiting_confirmation"
        for e in events
    )


def test_explicit_replay_ignores_planning_handler(
    repo: ConversationRepository,
    mock_planning_handler,
) -> None:
    session_id = _create_session(repo, status="idle")
    orch = ConversationOrchestrator(
        repo, planning_handler=mock_planning_handler
    )

    result = orch.dispatch_user_input(
        session_id, "/replay 11111111-1111-1111-1111-111111111111 http://127.0.0.1:5175/users"
    )

    assert result.allowed is True
    assert result.next_status == "replay_requested"
    assert result.command_kind == "replay"
    assert result.planning_result is None

    # No planning preview events
    events = repo.list_events(session_id)
    assert not any("plan_preview" in e.type for e in events)


def test_malformed_slash_command_does_not_trigger_planning_preview(
    repo: ConversationRepository,
    mock_planning_handler,
) -> None:
    session_id = _create_session(repo, status="idle")
    orch = ConversationOrchestrator(
        repo, planning_handler=mock_planning_handler
    )

    result = orch.dispatch_user_input(session_id, "/replay")

    assert result.allowed is False
    assert result.planning_result is None

    # No planning preview events
    events = repo.list_events(session_id)
    assert not any("plan_preview" in e.type for e in events)


# ── 11.1.5 Confirmation Gate ──────────────────────────────────────────────────


def _create_awaiting_confirmation_session(
    repo: ConversationRepository,
) -> str:
    """Create a session and seed a plan_preview_proposed event."""
    session = repo.create_session(initial_status="awaiting_confirmation")
    session_id = session.id
    # Seed the pending preview event so _get_pending_plan can find it
    repo.append_event(
        session_id=session_id,
        type=ConversationEventType.PLAN_PREVIEW_PROPOSED,
        payload={
            "task_intent_raw_text": "run export",
            "candidate_count": 1,
            "selected_path_id": "lp-001",
            "selected_purpose": "Export users",
            "warnings": [],
            "risk_hints": [],
            "confirmation_requirements": [],
            "confirmation_required": True,
        },
    )
    return session_id


def test_confirm_from_awaiting_confirmation_moves_to_plan_confirmed(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_awaiting_confirmation_session(repo)

    result = orchestrator.dispatch_user_input(session_id, "confirm")

    assert result.allowed is True
    assert result.previous_status == "awaiting_confirmation"
    assert result.next_status == "plan_confirmed"
    assert result.command_kind == "free_text"
    assert "ready for future execution" in result.user_response

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "plan_confirmed"

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert "plan_confirmed" in event_types
    assert ConversationEventType.STATE_CHANGED.value in event_types

    # Verify event payload
    confirmed_event = [e for e in events if e.type == "plan_confirmed"][0]
    assert confirmed_event.payload_json["decision"] == "confirm"
    assert confirmed_event.payload_json["selected_path_id"] == "lp-001"
    assert confirmed_event.payload_json["replay_executed"] is False


def test_cancel_from_awaiting_confirmation_returns_to_task_intake(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_awaiting_confirmation_session(repo)

    result = orchestrator.dispatch_user_input(session_id, "cancel")

    assert result.allowed is True
    assert result.next_status == "task_intake"
    assert "cancelled" in result.user_response
    assert "No execution occurred" in result.user_response

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "task_intake"

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert "plan_cancelled" in event_types
    assert ConversationEventType.STATE_CHANGED.value in event_types


@pytest.mark.parametrize(
    (
        "input_text",
        "expected_status",
        "expected_event",
        "expected_decision",
        "expected_command_kind",
    ),
    [
        ("/confirm", "plan_confirmed", "plan_confirmed", "confirm", "free_text"),
        ("/cancel", "task_intake", "plan_cancelled", "cancel", "cancel"),
        ("/abort", "task_intake", "plan_cancelled", "cancel", "abort"),
        ("/stop", "task_intake", "plan_cancelled", "cancel", "free_text"),
        ("/reject", "task_intake", "plan_rejected", "reject", "free_text"),
    ],
)
def test_slash_confirmation_commands_use_confirmation_gate(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
    input_text: str,
    expected_status: str,
    expected_event: str,
    expected_decision: str,
    expected_command_kind: str,
) -> None:
    session_id = _create_awaiting_confirmation_session(repo)

    result = orchestrator.dispatch_user_input(session_id, input_text)

    assert result.allowed is True
    assert result.next_status == expected_status
    assert result.command_kind == expected_command_kind

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == expected_status

    events = repo.list_events(session_id)
    assert expected_event in [e.type for e in events]
    decision_event = [e for e in events if e.type == expected_event][0]
    assert decision_event.payload_json["decision"] == expected_decision
    assert decision_event.payload_json["replay_executed"] is False
    assert not any(
        e.type == ConversationEventType.STATE_CHANGED.value
        and e.payload_json.get("to") == "idle"
        for e in events
    )


def test_reject_from_awaiting_confirmation_returns_to_task_intake(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_awaiting_confirmation_session(repo)

    result = orchestrator.dispatch_user_input(session_id, "reject")

    assert result.allowed is True
    assert result.next_status == "task_intake"
    assert "not accepted" in result.user_response
    assert "not executed" in result.user_response

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "task_intake"

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert "plan_rejected" in event_types
    assert ConversationEventType.STATE_CHANGED.value in event_types


def test_ambiguous_from_awaiting_confirmation_stays_awaiting_confirmation(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_awaiting_confirmation_session(repo)

    result = orchestrator.dispatch_user_input(session_id, "maybe")

    assert result.allowed is True
    assert result.next_status == "awaiting_confirmation"
    assert "confirm, cancel, reject" in result.user_response

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "awaiting_confirmation"

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert "confirmation_clarification_requested" in event_types
    # No state change because status stays the same
    state_changes = [e for e in events if e.type == ConversationEventType.STATE_CHANGED.value]
    assert len(state_changes) == 0


def test_replay_blocked_while_awaiting_confirmation(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_awaiting_confirmation_session(repo)

    result = orchestrator.dispatch_user_input(
        session_id, "/replay 11111111-1111-1111-1111-111111111111 http://127.0.0.1:5175/users"
    )

    assert result.allowed is False
    assert result.next_status == "awaiting_confirmation"
    assert result.command_kind == "replay"
    assert "confirm, cancel, or reject" in result.user_response

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "awaiting_confirmation"

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert "explicit_replay_blocked_by_pending_confirmation" in event_types
    blocked_event = [
        e for e in events
        if e.type == "explicit_replay_blocked_by_pending_confirmation"
    ][0]
    assert blocked_event.payload_json["reason"] == "replay_blocked_by_pending_confirmation"


def test_confirmation_gate_does_not_affect_normal_commands(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    """Non-FREE_TEXT / non-REPLAY commands while awaiting_confirmation fall through."""
    session_id = _create_awaiting_confirmation_session(repo)

    result = orchestrator.dispatch_user_input(session_id, "/status")

    assert result.allowed is True
    assert result.next_status == "awaiting_confirmation"
    assert result.command_kind == "status"


def test_confirmation_gate_records_no_replay_executed(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_awaiting_confirmation_session(repo)

    orchestrator.dispatch_user_input(session_id, "confirm")

    events = repo.list_events(session_id)
    confirmed = [e for e in events if e.type == "plan_confirmed"][0]
    assert confirmed.payload_json["replay_executed"] is False


# ── 11.1.6 Execution Gate ─────────────────────────────────────────────────────


def _create_plan_confirmed_session(
    repo: ConversationRepository,
    *,
    with_target_url: bool = True,
) -> str:
    """Create a session in plan_confirmed with seeded plan events."""
    session = repo.create_session(initial_status="plan_confirmed")
    session_id = session.id
    payload: dict[str, Any] = {
        "task_intent_raw_text": "run export",
        "candidate_count": 1,
        "selected_path_id": "lp-001",
        "selected_purpose": "Export users",
        "warnings": [],
        "risk_hints": [],
        "confirmation_requirements": [],
        "confirmation_required": True,
        "route_steps": [{"order": 1, "learned_path_id": "lp-001"}],
    }
    if with_target_url:
        payload["target_url"] = "http://127.0.0.1:5175/users"
    repo.append_event(
        session_id=session_id,
        type=ConversationEventType.PLAN_PREVIEW_PROPOSED,
        payload=payload,
    )
    repo.append_event(
        session_id=session_id,
        type=ConversationEventType.PLAN_CONFIRMED,
        payload={
            "user_decision_input": "confirm",
            "decision": "confirm",
            "selected_path_id": "lp-001",
            "replay_executed": False,
        },
    )
    return session_id


def test_execute_from_plan_confirmed_with_context_moves_to_execution_finished(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_plan_confirmed_session(repo)

    def handler(lid: str, url: str) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    orch = ConversationOrchestrator(
        repo, execution_handler=handler
    )

    result = orch.dispatch_user_input(session_id, "execute")

    assert result.allowed is True
    assert result.previous_status == "plan_confirmed"
    assert result.next_status == "execution_finished"
    assert result.command_kind == "free_text"
    # 11.1.7: user_response now comes from Task Result Reporter, not raw execution result
    assert "could not verify" in result.user_response.lower()

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "execution_finished"

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert "plan_execution_started" in event_types
    assert "plan_execution_completed" in event_types
    assert "task_result_reported" in event_types
    assert ConversationEventType.STATE_CHANGED.value in event_types

    started = [e for e in events if e.type == "plan_execution_started"][0]
    assert started.payload_json["learned_path_id"] == "lp-001"
    assert started.payload_json["no_result_verification"] is True
    assert started.payload_json["no_autonomous"] is True

    completed = [e for e in events if e.type == "plan_execution_completed"][0]
    assert completed.payload_json["task_verified"] is False
    assert completed.payload_json["no_result_verification"] is True

    reported = [e for e in events if e.type == "task_result_reported"][0]
    assert reported.payload_json["verification_outcome"] == "uncertain"
    assert reported.payload_json["needs_review"] is True
    assert reported.payload_json["no_recovery"] is True
    assert reported.payload_json["no_autonomous"] is True
    assert reported.payload_json["no_llm"] is True


def test_execute_from_plan_confirmed_missing_context_blocked(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_plan_confirmed_session(repo, with_target_url=False)

    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        raise AssertionError("handler should not be called")

    orch = ConversationOrchestrator(
        repo, execution_handler=handler
    )

    result = orch.dispatch_user_input(session_id, "execute")

    assert result.allowed is False
    assert result.previous_status == "plan_confirmed"
    assert result.next_status == "plan_confirmed"
    # 11.1.7: blocked user_response now comes from Task Result Reporter
    response = result.user_response.lower()
    assert "blocked" in response or "could not run" in response

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "plan_confirmed"

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert "plan_execution_blocked" in event_types
    assert "task_result_reported" in event_types
    blocked = [e for e in events if e.type == "plan_execution_blocked"][0]
    assert blocked.payload_json["reason"] == "missing_execution_context"
    assert (
        "learned_path_id" in blocked.payload_json["missing_fields"]
        or "target_url" in blocked.payload_json["missing_fields"]
    )
    reported = [e for e in events if e.type == "task_result_reported"][0]
    assert reported.payload_json["verification_outcome"] == "blocked"


def test_execute_replay_failure_moves_to_execution_failed(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_plan_confirmed_session(repo)

    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id="lp-001",
            url="http://127.0.0.1:5175/users",
            replay_status="drifted",
            drift_status="target_missing",
            error="Target missing",
        )

    orch = ConversationOrchestrator(
        repo, execution_handler=handler
    )

    result = orch.dispatch_user_input(session_id, "run")

    assert result.allowed is True
    assert result.next_status == "execution_failed"
    assert "failed" in result.user_response.lower()

    session = repo.get_session(session_id)
    assert session.status == "execution_failed"

    events = repo.list_events(session_id)
    assert "plan_execution_failed" in [e.type for e in events]


def test_non_execution_free_text_in_plan_confirmed_does_not_trigger_replay(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_plan_confirmed_session(repo)

    calls: list[Any] = []

    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        calls.append(True)
        return ConversationReplaySummary(
            learned_path_id="lp-001",
            url="http://127.0.0.1:5175/users",
            replay_status="succeeded",
            drift_status="none",
        )

    orch = ConversationOrchestrator(
        repo, execution_handler=handler
    )

    result = orch.dispatch_user_input(session_id, "hello")

    assert len(calls) == 0
    assert result.allowed is False
    assert result.next_status == "plan_confirmed"


def test_replay_outside_awaiting_confirmation_still_uses_explicit_path(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_plan_confirmed_session(repo)

    def handler(lid: str, url: str) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    orch = ConversationOrchestrator(
        repo, replay_handler=handler
    )

    # explicit /replay from plan_confirmed goes through normal state machine
    # (state machine blocks replay from plan_confirmed, but let's verify)
    result = orch.dispatch_user_input(
        session_id, "/replay lp-002 http://other.com"
    )

    # State machine blocks replay from plan_confirmed
    assert result.allowed is False
    assert result.next_status == "plan_confirmed"


def test_replay_while_awaiting_confirmation_still_blocked(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_awaiting_confirmation_session(repo)

    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id="lp-001",
            url="http://127.0.0.1:5175/users",
            replay_status="succeeded",
            drift_status="none",
        )

    orch = ConversationOrchestrator(
        repo, replay_handler=handler, execution_handler=handler
    )

    result = orch.dispatch_user_input(
        session_id, "/replay lp-001 http://127.0.0.1:5175/users"
    )

    assert result.allowed is False
    assert result.next_status == "awaiting_confirmation"
    assert "confirm, cancel, or reject" in result.user_response


def test_execution_gate_records_replay_result_in_dispatch_result(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    session_id = _create_plan_confirmed_session(repo)

    def handler(lid: str, url: str) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
            step_count=3,
        )

    orch = ConversationOrchestrator(
        repo, execution_handler=handler
    )

    result = orch.dispatch_user_input(session_id, "start")

    assert result.replay_result is not None
    assert result.replay_result.replay_status == "succeeded"
    assert result.replay_result.step_count == 3


def test_replay_handler_called_after_executing_state_and_started_event(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    """P1 fix: replay handler must run only after executing + started event."""
    session_id = _create_plan_confirmed_session(repo)

    call_log: list[str] = []

    def handler(lid: str, url: str) -> ConversationReplaySummary:
        # Verify session is already executing when handler runs
        session = repo.get_session(session_id)
        assert session is not None
        assert session.status == "executing"
        # Verify started event already exists
        events = repo.list_events(session_id)
        assert any(e.type == "plan_execution_started" for e in events)
        call_log.append("handler_called")
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    orch = ConversationOrchestrator(repo, execution_handler=handler)
    orch.dispatch_user_input(session_id, "execute")

    assert call_log == ["handler_called"]


def test_execute_blocked_when_plan_confirmed_event_is_missing(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    """P2 fix: no plan_confirmed event means no auditable consent -> blocked."""
    session = repo.create_session(initial_status="plan_confirmed")
    session_id = session.id
    # Only seed preview — no confirmed event
    repo.append_event(
        session_id=session_id,
        type=ConversationEventType.PLAN_PREVIEW_PROPOSED,
        payload={
            "selected_path_id": "lp-001",
            "target_url": "http://127.0.0.1:5175/users",
            "route_steps": [{"order": 1}],
        },
    )

    calls: list[Any] = []

    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        calls.append(True)
        raise AssertionError("handler should not be called")

    orch = ConversationOrchestrator(repo, execution_handler=handler)
    result = orch.dispatch_user_input(session_id, "execute")

    assert len(calls) == 0
    assert result.allowed is False
    assert result.next_status == "plan_confirmed"
    # 11.1.7: blocked user_response now comes from Task Result Reporter
    response = result.user_response.lower()
    assert "blocked" in response or "could not run" in response

    events = repo.list_events(session_id)
    assert any(e.type == "plan_execution_blocked" for e in events)
    assert any(e.type == "task_result_reported" for e in events)
    blocked = [e for e in events if e.type == "plan_execution_blocked"][0]
    assert blocked.payload_json["reason"] == "missing_confirmed_plan"
    reported = [e for e in events if e.type == "task_result_reported"][0]
    assert reported.payload_json["verification_outcome"] == "blocked"


def test_execute_blocked_when_confirmed_path_id_mismatches_preview(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    """P2: confirmed selected_path_id must match preview selected_path_id."""
    session = repo.create_session(initial_status="plan_confirmed")
    session_id = session.id
    repo.append_event(
        session_id=session_id,
        type=ConversationEventType.PLAN_PREVIEW_PROPOSED,
        payload={
            "selected_path_id": "lp-001",
            "target_url": "http://127.0.0.1:5175/users",
            "route_steps": [{"order": 1}],
        },
    )
    repo.append_event(
        session_id=session_id,
        type=ConversationEventType.PLAN_CONFIRMED,
        payload={
            "decision": "confirm",
            "selected_path_id": "lp-999",  # mismatch
        },
    )

    calls: list[Any] = []

    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        calls.append(True)
        raise AssertionError("handler should not be called")

    orch = ConversationOrchestrator(repo, execution_handler=handler)
    result = orch.dispatch_user_input(session_id, "execute")

    assert len(calls) == 0
    assert result.allowed is False
    assert result.next_status == "plan_confirmed"

    events = repo.list_events(session_id)
    assert any(e.type == "plan_execution_blocked" for e in events)


def test_execute_binds_to_confirmed_preview_not_newer_unconfirmed_preview(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    """P2: execution must bind to the preview confirmed by plan_confirmed,
    ignoring newer unconfirmed previews."""
    session = repo.create_session(initial_status="plan_confirmed")
    session_id = session.id
    repo.append_event(
        session_id=session_id,
        type=ConversationEventType.PLAN_PREVIEW_PROPOSED,
        payload={
            "selected_path_id": "lp-001",
            "target_url": "http://old.com",
            "route_steps": [{"order": 1}],
        },
    )
    repo.append_event(
        session_id=session_id,
        type=ConversationEventType.PLAN_CONFIRMED,
        payload={"decision": "confirm", "selected_path_id": "lp-001"},
    )
    # Newer preview but no confirm for it — must be ignored
    repo.append_event(
        session_id=session_id,
        type=ConversationEventType.PLAN_PREVIEW_PROPOSED,
        payload={
            "selected_path_id": "lp-999",
            "target_url": "http://new.com",
            "route_steps": [{"order": 1}],
        },
    )

    calls: list[str] = []

    def handler(lid: str, _url: str) -> ConversationReplaySummary:
        calls.append(lid)
        return ConversationReplaySummary(
            learned_path_id=lid,
            url="http://old.com",
            replay_status="succeeded",
            drift_status="none",
        )

    orch = ConversationOrchestrator(repo, execution_handler=handler)
    result = orch.dispatch_user_input(session_id, "execute")

    # Must execute the confirmed path (lp-001), not the newer unconfirmed one
    assert calls == ["lp-001"]
    assert result.allowed is True
    assert result.next_status == "execution_finished"


def test_execution_success_records_final_agent_message_not_empty(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    """Execution success must append the final response, not an empty message."""
    session_id = _create_plan_confirmed_session(repo)

    def handler(lid: str, url: str) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    orch = ConversationOrchestrator(repo, execution_handler=handler)
    orch.dispatch_user_input(session_id, "execute")

    messages = repo.list_messages(session_id)
    agent_messages = [m for m in messages if m.role == "agent"]
    # Should have exactly one agent message: the final verification report
    assert len(agent_messages) == 1
    assert "could not verify" in agent_messages[0].content.lower()
    assert agent_messages[0].metadata_json.get("source") == "execution_gate"
    assert agent_messages[0].metadata_json.get("status") == "completed"
    assert agent_messages[0].metadata_json.get("verification_outcome") == "uncertain"
    assert agent_messages[0].metadata_json.get("needs_review") is True


def test_execution_failure_records_final_agent_message_not_empty(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    """Execution failure must append the final response, not an empty message."""
    session_id = _create_plan_confirmed_session(repo)

    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id="lp-001",
            url="http://127.0.0.1:5175/users",
            replay_status="drifted",
            drift_status="target_missing",
            error="Target missing",
        )

    orch = ConversationOrchestrator(repo, execution_handler=handler)
    orch.dispatch_user_input(session_id, "run")

    messages = repo.list_messages(session_id)
    agent_messages = [m for m in messages if m.role == "agent"]
    assert len(agent_messages) == 1
    assert "failed" in agent_messages[0].content.lower()
    assert agent_messages[0].metadata_json.get("status") == "failed"


def test_execution_blocked_records_agent_message_not_empty(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    """Blocked execution must append the blocked response message from reporter."""
    session_id = _create_plan_confirmed_session(repo, with_target_url=False)

    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        raise AssertionError("handler should not be called")

    orch = ConversationOrchestrator(repo, execution_handler=handler)
    orch.dispatch_user_input(session_id, "execute")

    messages = repo.list_messages(session_id)
    agent_messages = [m for m in messages if m.role == "agent"]
    assert len(agent_messages) == 1
    content = agent_messages[0].content.lower()
    assert "could not run" in content or "blocked" in content
    assert agent_messages[0].metadata_json.get("status") == "blocked"
    assert agent_messages[0].metadata_json.get("verification_outcome") == "blocked"


def test_all_event_type_values_fit_in_database_column(
    repo: ConversationRepository,
) -> None:
    """Verify every ConversationEventType value can be persisted.

    The ORM column is String(64); this test guards against enum values
    that exceed the width on PostgreSQL.
    """
    from app.schemas.conversation import ConversationEventType

    session_id = _create_session(repo, status="idle")
    for evt in ConversationEventType:
        repo.append_event(session_id=session_id, type=evt, payload={"test": True})

    events = repo.list_events(session_id)
    persisted_types = {e.type for e in events}
    assert persisted_types == {e.value for e in ConversationEventType}


# ── 11.1.7 Result Verification and Task Result Reporter ───────────────────────


def test_execute_success_includes_task_result_reported_event(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    """Successful replay must append task_result_reported event after execution."""
    session_id = _create_plan_confirmed_session(repo)

    def handler(lid: str, url: str) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    orch = ConversationOrchestrator(repo, execution_handler=handler)
    orch.dispatch_user_input(session_id, "execute")

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert "task_result_reported" in event_types

    reported = [e for e in events if e.type == "task_result_reported"][0]
    assert reported.payload_json["verification_outcome"] == "uncertain"
    assert reported.payload_json["task_verified"] is False
    assert reported.payload_json["needs_review"] is True
    assert reported.payload_json["no_recovery"] is True
    assert reported.payload_json["no_autonomous"] is True
    assert reported.payload_json["no_llm"] is True
    assert "evidence_summary" in reported.payload_json
    assert "missing_evidence_summary" in reported.payload_json


def test_execute_failure_includes_task_result_reported_event(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    """Failed replay must append task_result_reported event with failed outcome."""
    session_id = _create_plan_confirmed_session(repo)

    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id="lp-001",
            url="http://127.0.0.1:5175/users",
            replay_status="drifted",
            drift_status="target_missing",
            error="Target missing",
        )

    orch = ConversationOrchestrator(repo, execution_handler=handler)
    result = orch.dispatch_user_input(session_id, "run")

    assert result.next_status == "execution_failed"
    assert "failed" in result.user_response.lower()

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert "task_result_reported" in event_types

    reported = [e for e in events if e.type == "task_result_reported"][0]
    assert reported.payload_json["verification_outcome"] == "failed"
    assert reported.payload_json["task_verified"] is False
    assert reported.payload_json["needs_review"] is False


def test_execute_blocked_includes_task_result_reported(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    """Blocked execution must append task_result_reported with blocked outcome."""
    session_id = _create_plan_confirmed_session(repo, with_target_url=False)

    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        raise AssertionError("handler should not be called")

    orch = ConversationOrchestrator(repo, execution_handler=handler)
    result = orch.dispatch_user_input(session_id, "execute")

    assert result.allowed is False
    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert "plan_execution_blocked" in event_types
    assert "task_result_reported" in event_types

    reported = [e for e in events if e.type == "task_result_reported"][0]
    assert reported.payload_json["verification_outcome"] == "blocked"
    assert reported.payload_json["needs_review"] is False
    assert reported.payload_json["no_recovery"] is True


def test_execute_success_report_user_response_is_evidence_bound(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    """Reporter user response must not claim success when outcome is uncertain."""
    session_id = _create_plan_confirmed_session(repo)

    def handler(lid: str, url: str) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    orch = ConversationOrchestrator(repo, execution_handler=handler)
    result = orch.dispatch_user_input(session_id, "execute")

    response = result.user_response.lower()
    assert "could not verify" in response
    assert "success" not in response
    assert "succeeded" not in response


def test_execute_failure_report_user_response_does_not_claim_recovery(
    orchestrator: ConversationOrchestrator,
    repo: ConversationRepository,
) -> None:
    """Reporter user response for failed execution must state no recovery."""
    session_id = _create_plan_confirmed_session(repo)

    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id="lp-001",
            url="http://127.0.0.1:5175/users",
            replay_status="failed",
            drift_status="none",
            error="element not found",
        )

    orch = ConversationOrchestrator(repo, execution_handler=handler)
    result = orch.dispatch_user_input(session_id, "run")

    response = result.user_response.lower()
    assert "failed" in response
    assert "no recovery was attempted" in response
