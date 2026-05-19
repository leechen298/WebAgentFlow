"""Tests for M11.3.5.1 Conversation Entry Gate."""

from __future__ import annotations

import time
from typing import Any

import pytest

from app.schemas.conversation_entry_gate import (
    ConversationEntryGateCategory,
    ConversationEntryGateResult,
)
from app.services.conversation.entry_gate import (
    ConversationEntryGateService,
    deterministic_entry_gate,
)
from app.services.conversation.prompt_assets import load_prompt_asset


def test_entry_gate_classifies_non_web_chat_without_execution_details() -> None:
    result = deterministic_entry_gate("你好")

    assert result.category == ConversationEntryGateCategory.NON_WEB_CHAT
    assert result.requires_agent_runtime is False
    assert result.confidence >= 0.6
    assert "selector" not in result.model_dump_json().lower()


def test_entry_gate_classifies_web_task_candidate() -> None:
    result = deterministic_entry_gate("学习 http://localhost:5176/login 怎么登录")

    assert result.category == ConversationEntryGateCategory.WEB_TASK_CANDIDATE
    assert result.requires_agent_runtime is True


def test_entry_gate_classifies_capability_question() -> None:
    result = deterministic_entry_gate("你能做什么？")

    assert result.category == ConversationEntryGateCategory.CAPABILITY_QUESTION
    assert result.requires_agent_runtime is False


def test_entry_gate_rejects_web_task_without_runtime_flag() -> None:
    with pytest.raises(ValueError, match="requires_agent_runtime"):
        ConversationEntryGateResult(
            category=ConversationEntryGateCategory.WEB_TASK_CANDIDATE,
            requires_agent_runtime=False,
            confidence=0.9,
        )


def test_entry_gate_rejects_non_web_with_runtime_flag() -> None:
    with pytest.raises(ValueError, match="requires_agent_runtime"):
        ConversationEntryGateResult(
            category=ConversationEntryGateCategory.NON_WEB_CHAT,
            requires_agent_runtime=True,
            confidence=0.9,
        )


def test_entry_gate_provider_schema_error_fails_closed() -> None:
    def provider(payload: dict[str, Any]) -> dict[str, Any]:
        assert payload["raw_message"] == "hello"
        return {
            "category": "web_task_candidate",
            "requires_agent_runtime": True,
            "confidence": 0.9,
            "reason_summary": "use target_selector #submit",
        }

    service = ConversationEntryGateService(provider=provider, timeout_ms=100)

    result = service.evaluate("hello")

    assert result.requires_agent_runtime is False
    assert result.category == ConversationEntryGateCategory.NEEDS_CLARIFICATION
    assert result.error_kind == "schema_error"
    trace = service.consume_last_trace_payload()
    assert trace is not None
    assert trace["parsed_output"]["error_kind"] == "schema_error"


def test_entry_gate_low_confidence_fails_closed() -> None:
    def provider(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "category": "web_task_candidate",
            "requires_agent_runtime": True,
            "confidence": 0.2,
            "reason_summary": "uncertain",
        }

    service = ConversationEntryGateService(provider=provider, timeout_ms=100)

    result = service.evaluate("http://localhost:5176/login")

    assert result.requires_agent_runtime is False
    assert result.category == ConversationEntryGateCategory.NEEDS_CLARIFICATION
    assert result.error_kind == "low_confidence"


def test_entry_gate_provider_timeout_does_not_wait_for_slow_provider() -> None:
    def provider(payload: dict[str, Any]) -> dict[str, Any]:
        time.sleep(0.4)
        return {
            "category": "web_task_candidate",
            "requires_agent_runtime": True,
            "confidence": 0.9,
        }

    service = ConversationEntryGateService(provider=provider, timeout_ms=25)
    started = time.perf_counter()

    result = service.evaluate("学习 http://localhost:5176/login")
    elapsed = time.perf_counter() - started

    assert elapsed < 0.25
    assert result.requires_agent_runtime is False
    assert result.error_kind == "timeout"
    assert result.timeout_ms == 25


def test_entry_gate_prompt_asset_loads() -> None:
    asset = load_prompt_asset("conversation_entry_gate", version="v1")

    assert asset.schema_name == "ConversationEntryGateResult"
    assert "Conversation Entry Gate" in asset.prompt_body
