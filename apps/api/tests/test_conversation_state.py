"""Tests for M11.0 conversation state transitions."""

from __future__ import annotations

import pytest

from app.schemas.conversation import (
    ConversationCommand,
    ConversationCommandKind,
    ConversationEventType,
    ConversationStatus,
)
from app.services.conversation.state import next_state


def _command(kind: ConversationCommandKind) -> ConversationCommand:
    return ConversationCommand(kind=kind, raw=f"/{kind.value}")


@pytest.mark.parametrize("status", list(ConversationStatus))
def test_status_command_is_allowed_from_any_state(status: ConversationStatus) -> None:
    result = next_state(status, _command(ConversationCommandKind.STATUS))

    assert result.allowed is True
    assert result.next_status == status
    assert result.event_type == ConversationEventType.COMMAND_PARSED
    assert result.error is None


def test_free_text_from_idle_enters_task_intake() -> None:
    result = next_state(
        ConversationStatus.IDLE,
        ConversationCommand(kind=ConversationCommandKind.FREE_TEXT, raw="do work", text="do work"),
    )

    assert result.allowed is True
    assert result.next_status == ConversationStatus.TASK_INTAKE
    assert result.event_type == ConversationEventType.MESSAGE_RECEIVED


def test_replay_from_idle_or_task_intake_enters_replay_requested() -> None:
    command = ConversationCommand(
        kind=ConversationCommandKind.REPLAY,
        raw="/replay path-1 http://127.0.0.1:5175/users",
        learned_path_id="path-1",
        url="http://127.0.0.1:5175/users",
    )

    for status in (ConversationStatus.IDLE, ConversationStatus.TASK_INTAKE):
        result = next_state(status, command)
        assert result.allowed is True
        assert result.next_status == ConversationStatus.REPLAY_REQUESTED
        assert result.event_type == ConversationEventType.REPLAY_REQUESTED


def test_pause_only_allowed_from_task_intake_or_replay_running() -> None:
    command = _command(ConversationCommandKind.PAUSE)

    for status in (ConversationStatus.TASK_INTAKE, ConversationStatus.REPLAY_RUNNING):
        result = next_state(status, command)
        assert result.allowed is True
        assert result.next_status == ConversationStatus.PAUSED
        assert result.event_type == ConversationEventType.PAUSE_REQUESTED

    disallowed = next_state(ConversationStatus.IDLE, command)
    assert disallowed.allowed is False
    assert disallowed.next_status == ConversationStatus.IDLE
    assert disallowed.error is not None


def test_resume_from_paused_returns_to_task_intake() -> None:
    result = next_state(
        ConversationStatus.PAUSED,
        _command(ConversationCommandKind.RESUME),
    )

    assert result.allowed is True
    assert result.next_status == ConversationStatus.TASK_INTAKE
    assert result.event_type == ConversationEventType.RESUME_REQUESTED


def test_resume_from_non_paused_state_is_invalid() -> None:
    result = next_state(
        ConversationStatus.IDLE,
        _command(ConversationCommandKind.RESUME),
    )

    assert result.allowed is False
    assert result.next_status == ConversationStatus.IDLE
    assert result.error is not None


def test_abort_from_non_terminal_state_enters_abort_requested() -> None:
    result = next_state(
        ConversationStatus.REPLAY_RUNNING,
        _command(ConversationCommandKind.ABORT),
    )

    assert result.allowed is True
    assert result.next_status == ConversationStatus.ABORT_REQUESTED
    assert result.event_type == ConversationEventType.ABORT_REQUESTED


def test_takeover_from_non_terminal_state_enters_takeover_requested() -> None:
    result = next_state(
        ConversationStatus.TASK_INTAKE,
        _command(ConversationCommandKind.TAKEOVER),
    )

    assert result.allowed is True
    assert result.next_status == ConversationStatus.TAKEOVER_REQUESTED
    assert result.event_type == ConversationEventType.TAKEOVER_REQUESTED


def test_cancel_from_non_terminal_state_returns_to_idle() -> None:
    result = next_state(
        ConversationStatus.TASK_INTAKE,
        _command(ConversationCommandKind.CANCEL),
    )

    assert result.allowed is True
    assert result.next_status == ConversationStatus.IDLE
    assert result.event_type == ConversationEventType.STATE_CHANGED


@pytest.mark.parametrize(
    "terminal_status",
    [ConversationStatus.COMPLETED, ConversationStatus.FAILED],
)
def test_terminal_states_reject_non_status_commands(
    terminal_status: ConversationStatus,
) -> None:
    result = next_state(
        terminal_status,
        _command(ConversationCommandKind.ABORT),
    )

    assert result.allowed is False
    assert result.next_status == terminal_status
    assert result.error is not None


def test_invalid_transition_returns_allowed_false_and_error() -> None:
    result = next_state(
        ConversationStatus.REPLAY_RUNNING,
        _command(ConversationCommandKind.REPLAY),
    )

    assert result.allowed is False
    assert result.next_status == ConversationStatus.REPLAY_RUNNING
    assert result.event_type == ConversationEventType.COMMAND_PARSED
    assert result.error is not None
