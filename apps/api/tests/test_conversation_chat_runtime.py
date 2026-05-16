"""Tests for M11.3 interactive chat closed loop."""

from __future__ import annotations

import hashlib
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.models.exploration_run import ExplorationRun
from app.repos.conversation_repo import ConversationRepository
from app.repos.exploration_run_repo import ExplorationRunRepository
from app.repos.learned_paths_repo import LearnedPathRepository
from app.schemas.conversation import ConversationReplaySummary
from app.services.conversation.chat_runtime import parse_chat_intent
from app.services.conversation.orchestrator import ConversationOrchestrator
from app.services.learning.learning_run_service import LearningRunResult


@pytest.fixture
def repo(db_session: Session) -> ConversationRepository:
    return ConversationRepository(db_session)


def _create_interactive_chat_session(
    repo: ConversationRepository,
    *,
    metadata: dict[str, Any] | None = None,
) -> str:
    session = repo.create_session(
        current_mode="interactive_chat",
        metadata={
            "client": "wagent_chat",
            "runtime_policy": "auto_execute_happy_path",
            **(metadata or {}),
        },
    )
    return session.id


def _ingest_login_path(db_session: Session, *, source_run_id: str | None = None) -> str:
    if source_run_id is not None and db_session.get(ExplorationRun, source_run_id) is None:
        ExplorationRunRepository(db_session).create(
            ExplorationRun(
                id=source_run_id,
                page_signature="/login",
                status="completed",
                summary="test run",
                result_snapshot_json={},
            )
        )

    fingerprint = hashlib.sha256((source_run_id or "default").encode()).hexdigest()
    path, _created = LearnedPathRepository(db_session).ingest_run(
        page_template="/login",
        query_signature={},
        dom_fingerprint=fingerprint,
        scenario="valid_credentials",
        actions=[
            {
                "step": 1,
                "action_type": "fill",
                "target_selector": "#username",
                "target_description": "Username",
                "value": "admin",
            },
            {
                "step": 2,
                "action_type": "fill",
                "target_selector": "#password",
                "target_description": "Password",
                "value": "123456",
            },
            {
                "step": 3,
                "action_type": "click",
                "target_selector": "button[type=submit]",
                "target_description": "Sign in",
            },
        ],
        source_run_id=source_run_id,
    )
    return str(path.id)


def test_parse_chat_intent_learn_page_extracts_url() -> None:
    intent = parse_chat_intent(
        "学习一下这个登录页怎么登录，地址是 http://localhost:5175/login"
    )

    assert intent.kind == "learn_page"
    assert intent.url == "http://localhost:5175/login"


def test_parse_chat_intent_execute_task_for_regular_text() -> None:
    intent = parse_chat_intent("帮我登录")

    assert intent.kind == "execute_task"
    assert intent.url is None


def test_interactive_chat_learns_login_and_writes_session_action(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo, metadata={"keep": "yes"})

    def learning_handler(url: str, raw_input: str) -> LearningRunResult:
        learned_path_id = _ingest_login_path(db_session, source_run_id="run-001")
        return LearningRunResult(
            status="learned",
            run_id="run-001",
            learned_path_id=learned_path_id,
            target_url=url,
            page_template="/login",
            scenario="valid_credentials",
            action_label="登录",
            suggested_utterances=["帮我登录", "登录一下"],
        )

    orch = ConversationOrchestrator(repo, learning_handler=learning_handler)

    result = orch.dispatch_user_input(
        session_id,
        "学习一下这个登录页怎么登录，地址是 http://localhost:5175/login",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is True
    assert result.command_kind == "learn_page"
    assert result.previous_status == "idle"
    assert result.next_status == "task_intake"
    assert "开始学习页面操作。" in result.user_response
    assert "学习完成：我学会了登录页的登录操作" in result.user_response

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "task_intake"
    assert session.metadata_json["keep"] == "yes"
    actions = session.metadata_json["learned_actions"]
    assert len(actions) == 1
    assert actions[0]["alias"] == "登录"
    assert actions[0]["utterances"] == ["帮我登录", "登录一下"]
    assert actions[0]["target_url"] == "http://localhost:5175/login"

    messages = repo.list_messages(session_id)
    agent_messages = [m.content for m in messages if m.role == "agent"]
    assert "开始学习页面操作。" in agent_messages
    assert any("之后你可以说“帮我登录”" in m for m in agent_messages)

    events = repo.list_events(session_id)
    completed = [e for e in events if e.type == "chat_learning_completed"]
    assert len(completed) == 1
    assert completed[0].payload_json["old_learned_path_id"] is None
    assert completed[0].payload_json["new_learned_path_id"] == actions[0]["learned_path_id"]


def test_learning_does_not_claim_success_when_path_is_not_queryable(
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)

    def learning_handler(url: str, raw_input: str) -> LearningRunResult:
        return LearningRunResult(
            status="learned",
            run_id="run-001",
            learned_path_id="missing-path",
            target_url=url,
            page_template="/login",
            scenario="valid_credentials",
            action_label="登录",
            suggested_utterances=["帮我登录"],
        )

    orch = ConversationOrchestrator(repo, learning_handler=learning_handler)

    result = orch.dispatch_user_input(
        session_id,
        "学习一下这个登录页怎么登录，地址是 http://localhost:5175/login",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is False
    assert result.command_kind == "learn_page"
    assert "学习失败" in result.user_response
    assert "学习完成" not in result.user_response


def test_same_alias_learning_overwrites_session_action(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    old_path_id = _ingest_login_path(db_session, source_run_id="run-old")
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "登录",
                    "utterances": ["帮我登录"],
                    "learned_path_id": old_path_id,
                    "target_url": "http://localhost:5175/login",
                    "page_template": "/login",
                    "scenario": "valid_credentials",
                }
            ]
        },
    )

    def learning_handler(url: str, raw_input: str) -> LearningRunResult:
        new_path_id = _ingest_login_path(db_session, source_run_id="run-new")
        return LearningRunResult(
            status="learned",
            run_id="run-new",
            learned_path_id=new_path_id,
            target_url=url,
            page_template="/login",
            scenario="valid_credentials",
            action_label="登录",
            suggested_utterances=["帮我登录", "登录一下"],
        )

    orch = ConversationOrchestrator(repo, learning_handler=learning_handler)
    result = orch.dispatch_user_input(
        session_id,
        "学习一下这个登录页怎么登录，地址是 http://localhost:5175/login",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is True
    session = repo.get_session(session_id)
    assert session is not None
    actions = session.metadata_json["learned_actions"]
    assert len(actions) == 1
    assert actions[0]["learned_path_id"] != old_path_id

    events = repo.list_events(session_id)
    completed = [e for e in events if e.type == "chat_learning_completed"][-1]
    assert completed.payload_json["old_learned_path_id"] == old_path_id
    assert completed.payload_json["new_learned_path_id"] == actions[0]["learned_path_id"]


def test_interactive_chat_executes_current_session_action_without_confirmation(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_login_path(db_session)
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "登录",
                    "utterances": ["帮我登录", "登录一下"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5175/login",
                    "page_template": "/login",
                    "scenario": "valid_credentials",
                }
            ]
        },
    )
    calls: list[tuple[str, str]] = []

    def replay_handler(lid: str, url: str) -> ConversationReplaySummary:
        calls.append((lid, url))
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
            final_url="http://localhost:5175/dashboard",
            final_title="Dashboard",
        )

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    result = orch.dispatch_user_input(
        session_id,
        "帮我登录",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is True
    assert result.command_kind == "execute_task"
    assert result.previous_status == "idle"
    assert result.next_status == "task_intake"
    assert result.user_response == "执行中。\n登录完成。"
    assert calls == [(learned_path_id, "http://localhost:5175/login")]

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "task_intake"

    events = repo.list_events(session_id)
    assert not any(e.type == "plan_preview_proposed" for e in events)
    assert not any(e.type == "plan_confirmed" for e in events)
    assert any(e.type == "chat_execution_completed" for e in events)

    agent_messages = [m.content for m in repo.list_messages(session_id) if m.role == "agent"]
    assert "执行中。" in agent_messages
    assert "登录完成。" in agent_messages


def test_interactive_chat_missing_session_action_does_not_use_global_paths(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    _ingest_login_path(db_session)
    session_id = _create_interactive_chat_session(repo)
    replay_called = False

    def replay_handler(lid: str, url: str) -> ConversationReplaySummary:
        nonlocal replay_called
        replay_called = True
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    result = orch.dispatch_user_input(
        session_id,
        "帮我登录",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is True
    assert result.command_kind == "execute_task"
    assert result.previous_status == "idle"
    assert result.next_status == "task_intake"
    assert result.user_response == "还没学过这个操作，需要先学习。"
    assert replay_called is False


def test_non_interactive_chat_session_keeps_existing_confirmation_flow(
    repo: ConversationRepository,
) -> None:
    session = repo.create_session(current_mode=None)

    def planning_handler(raw_input: str):
        from app.services.task_planning.preview import PlanningPreviewResult

        return PlanningPreviewResult(
            user_response=f"Preview for: {raw_input}",
            event_type="plan_preview_proposed",
            event_payload={"task_intent_raw_text": raw_input, "candidate_count": 1},
            confirmation_required=True,
            selected_path_id="lp-001",
        )

    learning_called = False

    def learning_handler(url: str, raw_input: str) -> LearningRunResult:
        nonlocal learning_called
        learning_called = True
        raise AssertionError("non-chat session must not call learning handler")

    orch = ConversationOrchestrator(
        repo,
        planning_handler=planning_handler,
        learning_handler=learning_handler,
    )

    result = orch.dispatch_user_input(
        session.id,
        "学习一下这个登录页怎么登录，地址是 http://localhost:5175/login",
        metadata={"client": "wagent_chat"},
    )

    assert learning_called is False
    assert result.next_status == "awaiting_confirmation"
    assert result.user_response.startswith("Preview for:")
