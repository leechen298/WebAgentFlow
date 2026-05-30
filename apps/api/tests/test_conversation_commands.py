"""Tests for M11.0 conversation command parsing."""

from __future__ import annotations

import inspect

from app.schemas.conversation import (
    ConversationCommandKind,
    ConversationEvent,
    ConversationMessage,
    ConversationSession,
    ConversationStatus,
)
from app.services.conversation import commands as command_module
from app.services.conversation import state as state_module
from app.services.conversation.commands import parse_command


def test_parse_basic_slash_commands() -> None:
    cases = {
        "/status": ConversationCommandKind.STATUS,
        "/pause": ConversationCommandKind.PAUSE,
        "/resume": ConversationCommandKind.RESUME,
        "/abort": ConversationCommandKind.ABORT,
        "/takeover": ConversationCommandKind.TAKEOVER,
        "/cancel": ConversationCommandKind.CANCEL,
    }

    for raw, expected_kind in cases.items():
        command = parse_command(raw)

        assert command.kind == expected_kind
        assert command.raw == raw
        assert command.args == []
        assert command.error is None


def test_parse_replay_command_with_path_id_and_url() -> None:
    command = parse_command(
        "/replay 11111111-1111-1111-1111-111111111111 https://example.invalid/records"
    )

    assert command.kind == ConversationCommandKind.REPLAY
    assert command.learned_path_id == "11111111-1111-1111-1111-111111111111"
    assert command.url == "https://example.invalid/records"
    assert command.args == [
        "11111111-1111-1111-1111-111111111111",
        "https://example.invalid/records",
    ]
    assert command.error is None


def test_parse_replay_missing_path_id_or_url_returns_error_command() -> None:
    missing_all = parse_command("/replay")
    missing_url = parse_command("/replay 11111111-1111-1111-1111-111111111111")
    too_many = parse_command(
        "/replay 11111111-1111-1111-1111-111111111111 https://example.invalid/records extra"
    )

    for command in (missing_all, missing_url, too_many):
        assert command.kind == ConversationCommandKind.ERROR
        assert command.error is not None
        assert "usage" in command.error.lower()


def test_parse_free_text_for_non_slash_and_unknown_slash_input() -> None:
    free_text = parse_command("run the user export")
    unknown_slash = parse_command("/unknown value")

    assert free_text.kind == ConversationCommandKind.FREE_TEXT
    assert free_text.text == "run the user export"
    assert free_text.args == []
    assert unknown_slash.kind == ConversationCommandKind.FREE_TEXT
    assert unknown_slash.text == "/unknown value"
    assert unknown_slash.args == ["/unknown", "value"]


def test_parse_empty_input_returns_error_command() -> None:
    command = parse_command("   ")

    assert command.kind == ConversationCommandKind.ERROR
    assert command.raw == ""
    assert command.error is not None


def test_conversation_schemas_do_not_define_identity_or_tenant_fields() -> None:
    forbidden = {"user", "account", "tenant", "user_id", "account_id", "tenant_id"}
    schema_models = [ConversationSession, ConversationMessage, ConversationEvent]

    for model in schema_models:
        assert forbidden.isdisjoint(model.model_fields)


def test_session_schema_defaults_to_idle_status() -> None:
    session = ConversationSession(id="session-1")

    assert session.status == ConversationStatus.IDLE
    assert session.current_mode is None
    assert session.metadata == {}


def test_parser_and_state_modules_do_not_reference_replay_autonomous_or_llm() -> None:
    combined_source = "\n".join(
        [
            inspect.getsource(command_module),
            inspect.getsource(state_module),
        ]
    )

    forbidden_tokens = [
        "learned_path_replay",
        "run_replay",
        "autonomous_explorer",
        "/exploration/autonomous-runs",
        "llm_provider",
        "OpenAI",
    ]
    for token in forbidden_tokens:
        assert token not in combined_source
