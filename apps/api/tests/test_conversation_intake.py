"""Tests for M11.3.4 conversation intake contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.conversation_intake import ConversationIntakeResult
from app.services.conversation.intake import (
    ConversationIntakeService,
    redact_sensitive_payload,
)


@pytest.mark.parametrize(
    "utterance",
    [
        (
            "学习一下这个工作台登录页怎么进入，地址是 "
            "http://localhost:5176/workspace-login，操作员账号是 demo，访问口令是 123456"
        ),
        "学习这个登录页：http://localhost:5176/workspace-login，用户名 demo，密码 123456",
        "学习这个页面怎么登录，http://localhost:5176/workspace-login，账号 demo，口令 123456",
        "学习这个入口：http://localhost:5176/workspace-login，demo / 123456",
    ],
)
def test_deterministic_intake_extracts_product_login_learning_slots(
    utterance: str,
) -> None:
    result = ConversationIntakeService().analyze(utterance)

    assert result.intent == "learn_operation"
    assert result.target.url == "http://localhost:5176/workspace-login"
    assert result.target.site_origin == "http://localhost:5176"
    assert result.action.goal
    assert result.action.canonical_goal == "进入工作台"
    assert result.should_ask_user is False
    assert result.missing_fields == []

    slots = {slot.semantic_type: slot for slot in result.slots}
    assert slots["username"].value == "demo"
    assert slots["username"].sensitive is False
    assert slots["password"].value == "123456"
    assert slots["password"].sensitive is True


def test_deterministic_intake_marks_missing_login_fields() -> None:
    result = ConversationIntakeService().analyze(
        "学习一下这个登录页：http://localhost:5176/workspace-login"
    )

    assert result.intent == "learn_operation"
    assert result.target.url == "http://localhost:5176/workspace-login"
    assert result.should_ask_user is True
    assert {field.semantic_type for field in result.missing_fields} == {
        "username",
        "password",
    }


def test_provider_unavailable_falls_back_to_deterministic_intake() -> None:
    def provider_down(raw_message: str, context: dict[str, object]) -> dict[str, object]:
        raise RuntimeError("provider down")

    result = ConversationIntakeService(provider=provider_down).analyze(
        "学习这个入口：http://localhost:5176/workspace-login，demo / 123456"
    )

    assert result.intent == "learn_operation"
    assert result.target.url == "http://localhost:5176/workspace-login"
    assert {slot.semantic_type: slot.value for slot in result.slots} == {
        "username": "demo",
        "password": "123456",
    }


def test_provider_success_without_source_is_marked_llm_when_trace_exists() -> None:
    def provider(raw_message: str, context: dict[str, object]) -> dict[str, object]:
        return {
            "intake": {
                "intent": "learn_operation",
                "target": {"url": "http://localhost:5176/workspace-login"},
                "action": {"goal": "进入工作台"},
                "confidence": 0.88,
                "should_ask_user": True,
                "ask_user_message_hint": "请提供登录用的用户名和密码。",
            },
            "llm_trace": {
                "trace_id": "trace-provider-success",
                "purpose": "conversation_intake",
                "agent_role": "conversation_intake_agent",
                "provider": "fake-provider",
                "model": "fake-model",
                "raw_request": {"content": raw_message},
                "raw_response": {"text": '{"intent":"learn_operation"}'},
                "token_usage": {"total_tokens": 8},
                "redaction": {"applied": True},
            },
        }

    service = ConversationIntakeService(provider=provider)
    result = service.analyze("学习这个工作台入口：http://localhost:5176/workspace-login")

    assert result.source == "llm"
    trace = service.consume_last_trace_payload()
    assert trace is not None
    assert trace["trace_id"] == "trace-provider-success"


def test_schema_rejects_learned_path_or_browser_action_authorization() -> None:
    with pytest.raises(ValidationError):
        ConversationIntakeResult.model_validate(
            {
                "intent": "execute_operation",
                "target": {"url": "http://localhost:5176/workspace-login"},
                "action": {
                    "goal": "进入工作台",
                    "canonical_goal": "进入工作台",
                    "aliases": ["进入工作台"],
                },
                "slots": [],
                "missing_fields": [],
                "confidence": 0.9,
                "should_ask_user": False,
                "learned_path_id": "lp-should-not-be-authorized-by-llm",
            }
        )


def test_redact_sensitive_payload_recursively_redacts_slot_values_and_text() -> None:
    payload = {
        "raw": "学习这个登录页：http://localhost:5176/workspace-login，用户名 demo，密码 123456",
        "slots": [
            {
                "semantic_type": "username",
                "value": "demo",
                "sensitive": False,
            },
            {
                "semantic_type": "password",
                "value": "123456",
                "sensitive": True,
            },
        ],
        "nested": {"access_secret": "123456"},
    }

    redacted = redact_sensitive_payload(payload)

    assert "123456" not in str(redacted)
    assert redacted["slots"][0]["value"] == "demo"
    assert redacted["slots"][1]["value"] == "[REDACTED]"
    assert redacted["nested"]["access_secret"] == "[REDACTED]"


def test_redact_sensitive_payload_redacts_positional_product_credentials() -> None:
    text = "学习这个入口：http://localhost:5176/workspace-login，demo / 123456"

    redacted = redact_sensitive_payload(text)

    assert "demo / 123456" not in redacted
    assert "123456" not in redacted
    assert "demo / [REDACTED]" in redacted


def test_redact_sensitive_payload_redacts_json_string_sensitive_slot() -> None:
    payload = {
        "raw_response": {
            "text": (
                '{"slots":[{"semantic_type":"password","value":"123456",'
                '"sensitive":true}]}'
            )
        }
    }

    redacted = redact_sensitive_payload(payload)

    assert "123456" not in str(redacted)
    assert "[REDACTED]" in redacted["raw_response"]["text"]
