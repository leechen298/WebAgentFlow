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
