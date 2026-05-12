"""Tests for M11.1.5 plan confirmation / consent gate service."""

from __future__ import annotations

import inspect

import pytest

from app.services.conversation.confirmation import PlanConfirmationService


@pytest.fixture
def service() -> PlanConfirmationService:
    return PlanConfirmationService()


# ── Classification ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "input_text",
    ["confirm", "yes", "proceed", "continue", "确认", "继续"],
)
def test_classify_confirm_keywords(service: PlanConfirmationService, input_text: str) -> None:
    decision = service.classify(input_text)
    assert decision.kind == "confirm"
    assert decision.raw_input == input_text


@pytest.mark.parametrize(
    "input_text",
    ["cancel", "abort", "stop", "取消", "停止"],
)
def test_classify_cancel_keywords(service: PlanConfirmationService, input_text: str) -> None:
    decision = service.classify(input_text)
    assert decision.kind == "cancel"
    assert decision.raw_input == input_text


@pytest.mark.parametrize(
    "input_text",
    ["reject", "no", "不要"],
)
def test_classify_reject_keywords(service: PlanConfirmationService, input_text: str) -> None:
    decision = service.classify(input_text)
    assert decision.kind == "reject"
    assert decision.raw_input == input_text


@pytest.mark.parametrize(
    "input_text",
    [
        "maybe",
        "looks ok?",
        "hello",
        "run the export",
        "",
        "  ",
        "maybe not",
        "I think so",
    ],
)
def test_classify_ambiguous_input(service: PlanConfirmationService, input_text: str) -> None:
    decision = service.classify(input_text)
    assert decision.kind == "ambiguous"
    assert decision.raw_input == input_text


# ── Process result ────────────────────────────────────────────────────────────


def test_process_confirm_result(service: PlanConfirmationService) -> None:
    result = service.process("confirm")
    assert result.decision == "confirm"
    assert result.event_type == "plan_confirmed"
    assert result.next_status == "plan_confirmed"
    assert "ready for future execution" in result.user_response
    assert "Replay has not run yet" in result.user_response


def test_process_cancel_result(service: PlanConfirmationService) -> None:
    result = service.process("cancel")
    assert result.decision == "cancel"
    assert result.event_type == "plan_cancelled"
    assert result.next_status == "task_intake"
    assert "cancelled" in result.user_response
    assert "No execution occurred" in result.user_response


def test_process_reject_result(service: PlanConfirmationService) -> None:
    result = service.process("reject")
    assert result.decision == "reject"
    assert result.event_type == "plan_rejected"
    assert result.next_status == "task_intake"
    assert "not accepted" in result.user_response
    assert "not executed" in result.user_response
    assert "revised task" in result.user_response


def test_process_ambiguous_result(service: PlanConfirmationService) -> None:
    result = service.process("maybe")
    assert result.decision == "ambiguous"
    assert result.event_type == "confirmation_clarification_requested"
    assert result.next_status == "awaiting_confirmation"
    assert "confirm, cancel, reject" in result.user_response


# ── Boundary ──────────────────────────────────────────────────────────────────


def test_confirmation_module_does_not_import_replay_autonomous_or_llm() -> None:
    from app.services.conversation import confirmation as confirmation_module

    source = inspect.getsource(confirmation_module)
    forbidden_tokens = [
        "learned_path_replay",
        "run_replay",
        "autonomous_explorer",
        "/exploration/autonomous-runs",
        "llm_provider",
        "OpenAI",
        "ConversationRepository",
        "Playwright",
        "Browser",
    ]
    for token in forbidden_tokens:
        assert token not in source
