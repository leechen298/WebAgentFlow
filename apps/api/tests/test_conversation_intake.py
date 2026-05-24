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
            "学习一下这个登录页怎么登录，地址是 "
            "http://localhost:8080/login，操作员账号是 demo，访问口令是 123456"
        ),
        "学习这个登录页：http://localhost:8080/login，用户名 demo，密码 123456",
        "学习这个页面怎么登录，http://localhost:8080/login，账号 demo，口令 123456",
        "学习这个入口：http://localhost:8080/login，demo / 123456",
    ],
)
def test_deterministic_intake_extracts_product_login_learning_slots(
    utterance: str,
) -> None:
    result = ConversationIntakeService().analyze(utterance)

    assert result.intent == "learn_operation"
    assert result.target.url == "http://localhost:8080/login"
    assert result.target.site_origin == "http://localhost:8080"
    assert result.action.goal
    assert result.action.canonical_goal == "登录"
    assert result.should_ask_user is False
    assert result.missing_fields == []

    slots = {slot.semantic_type: slot for slot in result.slots}
    assert slots["username"].value == "demo"
    assert slots["username"].sensitive is False
    assert slots["password"].value == "123456"
    assert slots["password"].sensitive is True


def test_deterministic_intake_marks_missing_login_fields() -> None:
    result = ConversationIntakeService().analyze(
        "学习一下这个登录页：http://localhost:8080/login"
    )

    assert result.intent == "learn_operation"
    assert result.target.url == "http://localhost:8080/login"
    assert result.should_ask_user is True
    assert {field.semantic_type for field in result.missing_fields} == {
        "username",
        "password",
    }


def test_deterministic_intake_extracts_item_name_learning_slot() -> None:
    result = ConversationIntakeService().analyze("学习新增项目，名称叫测试项目A")

    assert result.intent == "learn_operation"
    assert result.action.goal == "学习新增项目，名称叫测试项目A"
    assert result.action.canonical_goal is None
    slots = {slot.semantic_type: slot for slot in result.slots}
    assert slots["entity_name"].value == "测试项目A"
    assert slots["entity_name"].sensitive is False


def test_deterministic_intake_extracts_item_name_execute_slot() -> None:
    result = ConversationIntakeService().analyze("帮我新增项目，名称叫测试项目B")

    assert result.intent == "execute_operation"
    assert result.action.goal == "帮我新增项目，名称叫测试项目B"
    assert result.action.canonical_goal is None
    slots = {slot.semantic_type: slot.value for slot in result.slots}
    assert slots["entity_name"] == "测试项目B"


def test_deterministic_intake_does_not_extract_item_name_from_username() -> None:
    result = ConversationIntakeService().analyze(
        "学习这个登录页：http://localhost:8080/login，username 是 demo，密码 123456"
    )

    slots = {slot.semantic_type: slot.value for slot in result.slots}
    assert "item_name" not in slots


@pytest.mark.parametrize(
        ("utterance", "expected"),
        [
            ("name 是测试项目A", "测试项目A"),
            ("名称是测试项目A", "测试项目A"),
        ],
)
def test_deterministic_intake_normalizes_item_name_aliases(
    utterance: str,
    expected: str,
) -> None:
    result = ConversationIntakeService().analyze(utterance)

    slots = {slot.semantic_type: slot.value for slot in result.slots}
    assert slots["entity_name"] == expected


def test_provider_unavailable_falls_back_to_deterministic_intake() -> None:
    def provider_down(raw_message: str, context: dict[str, object]) -> dict[str, object]:
        raise RuntimeError("provider down")

    result = ConversationIntakeService(provider=provider_down).analyze(
        "学习这个入口：http://localhost:8080/login，demo / 123456"
    )

    assert result.intent == "learn_operation"
    assert result.target.url == "http://localhost:8080/login"
    assert {slot.semantic_type: slot.value for slot in result.slots} == {
        "username": "demo",
        "password": "123456",
    }


def test_provider_parse_error_falls_back_to_deterministic_pending_target() -> None:
    def provider_parse_error(
        raw_message: str,
        context: dict[str, object],
    ) -> dict[str, object]:
        return {
            "intake": {
                "intent": "unknown",
                "confidence": 0.0,
                "should_ask_user": True,
                "ask_user_message_hint": "我还需要再确认一下你的意思。",
                "source": "provider_parse_error",
            },
            "llm_trace": {
                "trace_id": "trace-provider-parse-error",
                "purpose": "conversation_intake",
                "agent_role": "conversation_intake_agent",
                "provider": "fake-provider",
                "model": "fake-model",
                "raw_request": {"content": raw_message, "context": context},
                "raw_response": {"text": '{"intent":"learn_operation"'},
                "token_usage": {"total_tokens": 8},
                "schema_validation": {"ok": False, "error_kind": "parse_error"},
                "redaction": {"applied": True},
            },
        }

    service = ConversationIntakeService(provider=provider_parse_error)

    result = service.analyze(
        "学习新增项目，名称叫测试项目A",
        session_metadata={
            "pending_target": {
                "url": "http://localhost:5176/items",
                "site_origin": "http://localhost:5176",
                "page_hint": "/items",
            }
        },
    )

    assert service.provider_fallback is True
    assert result.intent == "learn_operation"
    assert result.target.url == "http://localhost:5176/items"
    assert result.action.canonical_goal is None
    assert {slot.semantic_type: slot.value for slot in result.slots} == {
        "entity_name": "测试项目A"
    }
    trace = service.consume_last_trace_payload()
    assert trace is not None
    assert trace["trace_id"] == "trace-provider-parse-error"
    assert trace["schema_validation"]["error_kind"] == "parse_error"


def test_provider_result_drops_missing_field_when_slot_value_is_present() -> None:
    def provider(
        raw_message: str,
        context: dict[str, object],
    ) -> dict[str, object]:
        return {
            "intake": {
                "intent": "learn_operation",
                "target": {
                    "url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_hint": "/items",
                },
                "action": {
                    "goal": "新增项目",
                    "canonical_goal": "add_item",
                    "aliases": ["新增项目", "添加项目", "创建项目"],
                },
                "slots": [
                    {
                        "name": "project_name",
                        "semantic_type": "project_name",
                        "value": "测试项目A",
                        "sensitive": False,
                        "source": "user_message",
                    }
                ],
                "missing_fields": [
                    {
                        "semantic_type": "project_name",
                        "display_name": "项目名称",
                    }
                ],
                "confidence": 0.85,
                "should_ask_user": True,
                "ask_user_message_hint": "我需要项目名称。",
            },
            "llm_trace": {
                "trace_id": "trace-provider-slot-conflict",
                "purpose": "conversation_intake",
                "agent_role": "conversation_intake_agent",
                "provider": "fake-provider",
                "model": "fake-model",
                "raw_request": {"content": raw_message, "context": context},
                "raw_response": {"text": "{}"},
                "token_usage": {"total_tokens": 8},
                "redaction": {"applied": True},
            },
        }

    result = ConversationIntakeService(provider=provider).analyze("学习新增项目，名称叫测试项目A")

    assert result.missing_fields == []
    assert result.should_ask_user is False
    assert result.ask_user_message_hint is None
    assert {slot.semantic_type: slot.value for slot in result.slots} == {
        "project_name": "测试项目A"
    }


def test_provider_result_clears_spurious_ask_when_item_learning_is_complete() -> None:
    def provider(
        raw_message: str,
        context: dict[str, object],
    ) -> dict[str, object]:
        return {
            "intent": "learn_operation",
            "target": {
                "url": "http://localhost:5176/items",
                "site_origin": "http://localhost:5176",
                "page_hint": "/items",
            },
            "action": {
                "goal": "新增项目",
                "canonical_goal": "新增项目",
                "aliases": ["添加项目", "创建项目"],
            },
            "slots": [
                {
                    "name": "project_name",
                    "semantic_type": "project_name",
                    "label_seen": "名称",
                    "value": "测试项目A",
                    "sensitive": False,
                    "source": "user_message",
                }
            ],
            "missing_fields": [],
            "confidence": 0.95,
            "should_ask_user": True,
            "ask_user_message_hint": "好的，请开始执行新增项目操作，我将学习您的操作步骤。",
        }

    result = ConversationIntakeService(provider=provider).analyze("学习新增项目，名称叫 测试项目A")

    assert result.intent == "learn_operation"
    assert result.missing_fields == []
    assert result.should_ask_user is False
    assert result.ask_user_message_hint is None
    assert {slot.semantic_type: slot.value for slot in result.slots} == {
        "project_name": "测试项目A"
    }


@pytest.mark.parametrize("semantic_type", ["entity_name", "name"])
def test_provider_result_maps_generic_items_name_slot_to_item_name(
    semantic_type: str,
) -> None:
    def provider(
        raw_message: str,
        context: dict[str, object],
    ) -> dict[str, object]:
        return {
            "intent": "execute_operation",
            "target": {
                "url": "http://localhost:5176/items",
                "site_origin": "http://localhost:5176",
                "page_hint": "/items",
            },
            "action": {
                "goal": "创建项目",
                "canonical_goal": "create_item",
                "aliases": ["新增项目", "添加项目", "录入项目"],
            },
            "slots": [
                {
                    "name": "name",
                    "semantic_type": semantic_type,
                    "value": "测试项目ChoiceA",
                    "sensitive": False,
                    "source": "user_message",
                }
            ],
            "missing_fields": [],
            "confidence": 0.85,
            "should_ask_user": False,
        }

    result = ConversationIntakeService(provider=provider).analyze(
        "帮我处理一下这个页面，名称叫 测试项目ChoiceA"
    )

    assert {slot.semantic_type: slot.value for slot in result.slots} == {
        semantic_type: "测试项目ChoiceA"
    }


def test_provider_success_without_source_is_marked_llm_when_trace_exists() -> None:
    def provider(raw_message: str, context: dict[str, object]) -> dict[str, object]:
        return {
            "intake": {
                "intent": "learn_operation",
                "target": {"url": "http://localhost:8080/login"},
                "action": {"goal": "登录"},
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
    result = service.analyze("学习这个登录入口：http://localhost:8080/login")

    assert result.source == "llm"
    trace = service.consume_last_trace_payload()
    assert trace is not None
    assert trace["trace_id"] == "trace-provider-success"


def test_schema_rejects_learned_path_or_browser_action_authorization() -> None:
    with pytest.raises(ValidationError):
        ConversationIntakeResult.model_validate(
            {
                "intent": "execute_operation",
                "target": {"url": "http://localhost:8080/login"},
                "action": {
                    "goal": "登录",
                    "canonical_goal": "登录",
                    "aliases": ["登录"],
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
        "raw": "学习这个登录页：http://localhost:8080/login，用户名 demo，密码 123456",
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
    text = "学习这个入口：http://localhost:8080/login，demo / 123456"

    redacted = redact_sensitive_payload(text)

    assert "demo / 123456" not in redacted
    assert "123456" not in redacted
    assert "demo / [REDACTED]" in redacted


def test_redact_sensitive_payload_redacts_json_string_sensitive_slot() -> None:
    payload = {
        "raw_response": {
            "text": ('{"slots":[{"semantic_type":"password","value":"123456","sensitive":true}]}')
        }
    }

    redacted = redact_sensitive_payload(payload)

    assert "123456" not in str(redacted)
    assert "[REDACTED]" in redacted["raw_response"]["text"]
