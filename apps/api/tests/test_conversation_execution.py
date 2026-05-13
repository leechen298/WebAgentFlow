"""Tests for M11.1.6 plan execution service."""

from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from app.repos.conversation_repo import ConversationRepository
from app.schemas.conversation import ConversationEventType, ConversationReplaySummary
from app.services.conversation.execution import PlanExecutionService


@pytest.fixture
def service() -> PlanExecutionService:
    return PlanExecutionService()


@pytest.fixture
def repo(db_session: Session) -> ConversationRepository:
    return ConversationRepository(db_session)


# ── Classification ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "token",
    ["execute", "run", "start", "执行", "开始", "  execute  ", "RUN"],
)
def test_classify_execution_tokens(service: PlanExecutionService, token: str) -> None:
    decision = service.classify(token)
    assert decision.is_execution_intent is True
    assert decision.raw_input == token


def test_classify_non_execution_text(service: PlanExecutionService) -> None:
    decision = service.classify("hello world")
    assert decision.is_execution_intent is False


def test_classify_empty_string(service: PlanExecutionService) -> None:
    decision = service.classify("")
    assert decision.is_execution_intent is False


def test_classify_fuzzy_text_rejected(service: PlanExecutionService) -> None:
    decision = service.classify("please execute the plan")
    assert decision.is_execution_intent is False


def test_classify_chinese_fuzzy_rejected(service: PlanExecutionService) -> None:
    decision = service.classify("开始执行")
    assert decision.is_execution_intent is False


# ── Confirmed plan context extraction ─────────────────────────────────────────


def _make_event(type_val: str, payload: dict[str, Any]) -> Any:
    """Build a minimal mock event."""
    ev = MagicMock()
    ev.type = type_val
    ev.payload_json = payload
    return ev


def test_extract_confirmed_plan_context_requires_both_events(
    service: PlanExecutionService,
) -> None:
    events = [
        _make_event(
            "plan_preview_proposed",
            {
                "selected_path_id": "lp-001",
                "target_url": "http://example.com/users",
            },
        ),
        _make_event(
            "plan_confirmed", {"decision": "confirm", "selected_path_id": "lp-001"}
        ),
    ]
    ctx = service.extract_confirmed_plan_context(events)
    assert ctx is not None
    assert ctx["learned_path_id"] == "lp-001"
    assert ctx["target_url"] == "http://example.com/users"
    assert ctx["confirmed_decision"] == "confirm"


def test_extract_confirmed_plan_context_missing_preview_returns_none(
    service: PlanExecutionService,
) -> None:
    events = [_make_event("plan_confirmed", {"decision": "confirm"})]
    ctx = service.extract_confirmed_plan_context(events)
    assert ctx is None


def test_extract_confirmed_plan_context_missing_confirmed_returns_none(
    service: PlanExecutionService,
) -> None:
    events = [
        _make_event(
            "plan_preview_proposed",
            {"selected_path_id": "lp-001", "target_url": "http://example.com"},
        ),
    ]
    ctx = service.extract_confirmed_plan_context(events)
    assert ctx is None


def test_extract_confirmed_plan_context_reads_most_recent(
    service: PlanExecutionService,
) -> None:
    events = [
        _make_event(
            "plan_preview_proposed",
            {"selected_path_id": "lp-old", "target_url": "http://old.com"},
        ),
        _make_event(
            "plan_confirmed",
            {"decision": "confirm", "selected_path_id": "lp-old"},
        ),
        _make_event(
            "plan_preview_proposed",
            {"selected_path_id": "lp-new", "target_url": "http://new.com"},
        ),
        _make_event(
            "plan_confirmed",
            {"decision": "confirm", "selected_path_id": "lp-new"},
        ),
    ]
    ctx = service.extract_confirmed_plan_context(events)
    assert ctx is not None
    assert ctx["learned_path_id"] == "lp-new"


# ── Validate: blocked cases ───────────────────────────────────────────────────


def test_validate_non_execution_intent(service: PlanExecutionService) -> None:
    result = service.validate("hello", confirmed_plan_context=None)
    assert result.is_execution_intent is False
    assert result.status == "not_execution_intent"


def test_validate_missing_confirmed_plan_blocked(
    service: PlanExecutionService,
) -> None:
    result = service.validate("execute", confirmed_plan_context=None)
    assert result.is_execution_intent is True
    assert result.status == "blocked"
    assert result.event_type == "plan_execution_blocked"
    assert result.next_status == "plan_confirmed"
    assert "missing" in result.payload["reason"]


def test_validate_missing_learned_path_id_blocked(
    service: PlanExecutionService,
) -> None:
    result = service.validate(
        "execute",
        confirmed_plan_context={"target_url": "http://example.com"},
    )
    assert result.status == "blocked"
    assert "learned_path_id" in result.payload["missing_fields"]


def test_validate_missing_target_url_blocked(
    service: PlanExecutionService,
) -> None:
    result = service.validate(
        "execute",
        confirmed_plan_context={"learned_path_id": "lp-001"},
    )
    assert result.status == "blocked"
    assert "target_url" in result.payload["missing_fields"]


def test_validate_multi_step_route_blocked(
    service: PlanExecutionService,
) -> None:
    result = service.validate(
        "execute",
        confirmed_plan_context={
            "learned_path_id": "lp-001",
            "target_url": "http://example.com",
            "route_steps": [
                {"order": 1, "learned_path_id": "lp-001"},
                {"order": 2, "learned_path_id": "lp-002"},
            ],
        },
    )
    assert result.status == "blocked"
    assert result.payload["reason"] == "unsupported_multi_step_route"


def test_validate_ready_exposes_context(service: PlanExecutionService) -> None:
    result = service.validate(
        "execute",
        confirmed_plan_context={
            "learned_path_id": "lp-001",
            "target_url": "http://example.com",
            "route_summary": "Fill form",
        },
    )
    assert result.status == "ready"
    assert result.payload["learned_path_id"] == "lp-001"
    assert result.payload["target_url"] == "http://example.com"
    assert result.payload["route_summary"] == "Fill form"
    assert result.payload["no_result_verification"] is True
    assert result.payload["no_autonomous"] is True


# ── Build result from replay ──────────────────────────────────────────────────


def test_build_result_from_replay_success(service: PlanExecutionService) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="succeeded",
        drift_status="none",
    )
    ctx = {"learned_path_id": "lp-001", "target_url": "http://example.com"}
    result = service.build_result_from_replay("execute", ctx, summary)
    assert result.status == "completed"
    assert result.event_type == "plan_execution_completed"
    assert result.next_status == "execution_finished"
    assert result.payload["no_result_verification"] is True
    assert result.payload["task_verified"] is False
    assert result.payload["no_autonomous"] is True


def test_build_result_from_replay_observed(service: PlanExecutionService) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="observed",
        drift_status="none",
    )
    ctx = {"learned_path_id": "lp-001", "target_url": "http://example.com"}
    result = service.build_result_from_replay("execute", ctx, summary)
    assert result.status == "completed"


def test_build_result_from_replay_drift(service: PlanExecutionService) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="drifted",
        drift_status="page_mismatch",
        error="Page did not match",
    )
    ctx = {"learned_path_id": "lp-001", "target_url": "http://example.com"}
    result = service.build_result_from_replay("execute", ctx, summary)
    assert result.status == "failed"
    assert result.event_type == "plan_execution_failed"
    assert result.next_status == "execution_failed"
    assert result.payload["task_verified"] is False


# ── Build result from error ───────────────────────────────────────────────────


def test_build_result_from_error(service: PlanExecutionService) -> None:
    ctx = {"learned_path_id": "lp-001", "target_url": "http://example.com"}
    result = service.build_result_from_error(
        "execute", ctx, RuntimeError("browser exploded")
    )
    assert result.status == "failed"
    assert "browser exploded" in result.payload["error_summary"]
    assert result.event_type == "plan_execution_failed"
    assert result.next_status == "execution_failed"


# ── Payload boundaries ────────────────────────────────────────────────────────


def test_completed_user_response_does_not_claim_task_success(
    service: PlanExecutionService,
) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="succeeded",
        drift_status="none",
    )
    ctx = {"learned_path_id": "lp-001", "target_url": "http://example.com"}
    result = service.build_result_from_replay("execute", ctx, summary)
    assert "completed" in result.user_response.lower()
    assert "not implemented" in result.user_response.lower()
    assert "succeeded" not in result.user_response.lower()


def test_blocked_payload_contains_no_result_verification_marker(
    service: PlanExecutionService,
) -> None:
    result = service.validate("execute", confirmed_plan_context=None)
    assert result.payload["no_result_verification"] is True
    assert result.payload["no_autonomous"] is True


# ── Forbidden imports ─────────────────────────────────────────────────────────


def test_execution_module_does_not_import_replay_autonomous_or_llm() -> None:
    from app.services.conversation import execution as execution_module

    source = inspect.getsource(execution_module)
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


# ── Extract context from repo events ──────────────────────────────────────────


def test_extract_context_from_real_repo_events(repo: ConversationRepository) -> None:
    session = repo.create_session(initial_status="plan_confirmed")
    repo.append_event(
        session_id=session.id,
        type=ConversationEventType.PLAN_PREVIEW_PROPOSED,
        payload={
            "selected_path_id": "lp-001",
            "target_url": "http://example.com/users",
            "route_steps": [{"order": 1}],
        },
    )
    repo.append_event(
        session_id=session.id,
        type=ConversationEventType.PLAN_CONFIRMED,
        payload={"decision": "confirm", "selected_path_id": "lp-001"},
    )

    service = PlanExecutionService()
    events = repo.list_events(session.id)
    ctx = service.extract_confirmed_plan_context(events)
    assert ctx is not None
    assert ctx["learned_path_id"] == "lp-001"
    assert ctx["target_url"] == "http://example.com/users"
    assert ctx["confirmed_decision"] == "confirm"


def test_extract_context_missing_confirmed_from_repo_returns_none(
    repo: ConversationRepository,
) -> None:
    session = repo.create_session(initial_status="plan_confirmed")
    repo.append_event(
        session_id=session.id,
        type=ConversationEventType.PLAN_PREVIEW_PROPOSED,
        payload={"selected_path_id": "lp-001", "target_url": "http://example.com"},
    )
    # No plan_confirmed event

    service = PlanExecutionService()
    events = repo.list_events(session.id)
    ctx = service.extract_confirmed_plan_context(events)
    assert ctx is None


def test_extract_confirmed_plan_context_mismatch_path_id_returns_none(
    service: PlanExecutionService,
) -> None:
    """P2: confirmed selected_path_id must match preview selected_path_id."""
    events = [
        _make_event(
            "plan_preview_proposed",
            {"selected_path_id": "lp-001", "target_url": "http://a.com"},
        ),
        _make_event(
            "plan_confirmed",
            {"decision": "confirm", "selected_path_id": "lp-002"},
        ),
    ]
    ctx = service.extract_confirmed_plan_context(events)
    assert ctx is None


def test_extract_confirmed_plan_context_preview_after_confirm_ignored(
    service: PlanExecutionService,
) -> None:
    """P2: preview after confirm must not be used as execution context."""
    events = [
        _make_event(
            "plan_preview_proposed",
            {"selected_path_id": "lp-001", "target_url": "http://old.com"},
        ),
        _make_event(
            "plan_confirmed",
            {"decision": "confirm", "selected_path_id": "lp-001"},
        ),
        # Newer preview without corresponding confirm
        _make_event(
            "plan_preview_proposed",
            {"selected_path_id": "lp-999", "target_url": "http://new.com"},
        ),
    ]
    ctx = service.extract_confirmed_plan_context(events)
    assert ctx is not None
    # Must bind to the preview that precedes the confirmed event
    assert ctx["learned_path_id"] == "lp-001"
    assert ctx["target_url"] == "http://old.com"


def test_extract_confirmed_plan_context_confirmed_missing_path_id_returns_none(
    service: PlanExecutionService,
) -> None:
    """P2: plan_confirmed must carry selected_path_id to be auditable."""
    events = [
        _make_event(
            "plan_preview_proposed",
            {"selected_path_id": "lp-001", "target_url": "http://a.com"},
        ),
        _make_event("plan_confirmed", {"decision": "confirm"}),
    ]
    ctx = service.extract_confirmed_plan_context(events)
    assert ctx is None
