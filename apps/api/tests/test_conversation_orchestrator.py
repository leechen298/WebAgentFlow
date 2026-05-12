"""Tests for M11.0 conversation orchestrator / dispatcher."""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy.orm import Session

from app.repos.conversation_repo import ConversationRepository
from app.schemas.conversation import (
    ConversationEventType,
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
