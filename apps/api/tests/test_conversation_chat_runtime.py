"""Tests for M11.3 interactive chat closed loop."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.models.exploration_run import ExplorationRun
from app.repos.conversation_repo import ConversationRepository
from app.repos.exploration_run_repo import ExplorationRunRepository
from app.repos.learned_paths_repo import LearnedPathRepository
from app.schemas.conversation import ConversationReplaySummary
from app.schemas.conversation_entry_gate import (
    ConversationEntryGateCategory,
    ConversationEntryGateResult,
)
from app.schemas.conversation_intake import (
    ConversationIntakeAction,
    ConversationIntakeResult,
    ConversationIntakeSlot,
    ConversationIntakeTarget,
)
from app.schemas.conversation_router import (
    ApplicationSkillName,
    RouteDecision,
    RouteDecisionKind,
    RouterAgentRole,
)
from app.schemas.task_planning import (
    AgentDPlannerOutput,
    ConfirmationRequirement,
    RiskHint,
    RoutePlan,
    RouteStep,
)
from app.services.conversation.chat_runtime import (
    _PENDING_SENSITIVE_VALUES,
    _fill_values_from_intake,
    _parse_choice_reply,
    _parse_product_inputs,
    parse_chat_intent,
)
from app.services.conversation.entry_gate import ConversationEntryGateService
from app.services.conversation.orchestrator import ConversationOrchestrator
from app.services.conversation.page_context import PageContextBuilder
from app.services.learning.learning_run_service import LearningRunResult
from app.services.task_planning.planner import TaskPathPlanner


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


GENERIC_WORKFLOW_URL = "http://example.test/workflow"
GENERIC_RECORDS_URL = "http://example.test/records"
GENERIC_ALT_WORKFLOW_URL = "http://alt.example.test/workflow"
GENERIC_ALT_RECORDS_URL = "http://alt.example.test/records"


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


def _ingest_workspace_path(
    db_session: Session,
    *,
    source_run_id: str | None = None,
    page_template: str = "/workflow",
) -> str:
    if source_run_id is not None and db_session.get(ExplorationRun, source_run_id) is None:
        ExplorationRunRepository(db_session).create(
            ExplorationRun(
                id=source_run_id,
                page_signature=page_template,
                status="completed",
                summary="workflow test run",
                result_snapshot_json={},
            )
        )

    fingerprint = hashlib.sha256((source_run_id or page_template).encode()).hexdigest()
    path, _created = LearnedPathRepository(db_session).ingest_run(
        page_template=page_template,
        query_signature={},
        dom_fingerprint=fingerprint,
        scenario="product_level",
        actions=[
            {
                "step": 1,
                "action_type": "fill",
                "target_selector": "#operator-id",
                "target_description": "Operator account",
                "value": "demo",
            },
            {
                "step": 2,
                "action_type": "fill",
                "target_selector": "#access-code",
                "target_description": "Access secret",
                "value": "123456",
            },
            {
                "step": 3,
                "action_type": "click",
                "target_selector": "button[type=submit]",
                "target_description": "Complete workflow",
            },
        ],
        source_run_id=source_run_id,
    )
    return str(path.id)


def _ingest_items_path(
    db_session: Session,
    *,
    source_run_id: str | None = None,
    value_slot: str | None = None,
) -> str:
    if source_run_id is not None and db_session.get(ExplorationRun, source_run_id) is None:
        ExplorationRunRepository(db_session).create(
            ExplorationRun(
                id=source_run_id,
                page_signature="/records",
                status="completed",
                summary="records test run",
                result_snapshot_json={},
            )
        )

    fingerprint = hashlib.sha256(
        (source_run_id or f"records-{value_slot or 'fixed'}").encode()
    ).hexdigest()
    fill_action: dict[str, Any] = {
        "step": 1,
        "action_type": "fill",
        "target_selector": "#record-name",
        "target_description": "Record name",
        "value": "Alpha Record",
    }
    if value_slot:
        fill_action["value_slot"] = value_slot
    path, _created = LearnedPathRepository(db_session).ingest_run(
        page_template="/records",
        query_signature={},
        dom_fingerprint=fingerprint,
        scenario="product_level",
        actions=[
            fill_action,
            {
                "step": 2,
                "action_type": "click",
                "target_selector": "#record-submit",
                "target_description": "Create record",
            },
        ],
        source_run_id=source_run_id,
    )
    return str(path.id)


def _ingest_record_path(
    db_session: Session,
    *,
    source_run_id: str | None = None,
    value_slot: str | None = "entity_name",
    page_template: str = "/records",
) -> str:
    if source_run_id is not None and db_session.get(ExplorationRun, source_run_id) is None:
        ExplorationRunRepository(db_session).create(
            ExplorationRun(
                id=source_run_id,
                page_signature=page_template,
                status="completed",
                summary="records test run",
                result_snapshot_json={},
            )
        )

    fingerprint = hashlib.sha256(
        (source_run_id or f"records-{value_slot or 'fixed'}").encode()
    ).hexdigest()
    fill_action: dict[str, Any] = {
        "step": 1,
        "action_type": "fill",
        "target_selector": "#record-name",
        "target_description": "Name",
        "value": "Alpha",
    }
    if value_slot:
        fill_action["value_slot"] = value_slot
    path, _created = LearnedPathRepository(db_session).ingest_run(
        page_template=page_template,
        query_signature={},
        dom_fingerprint=fingerprint,
        scenario="product_level",
        actions=[
            fill_action,
            {
                "step": 2,
                "action_type": "click",
                "target_selector": "button[type=submit]",
                "target_description": "Create",
            },
        ],
        source_run_id=source_run_id,
    )
    return str(path.id)


def test_parse_chat_intent_learn_page_extracts_url() -> None:
    intent = parse_chat_intent("学习一下这个登录页怎么登录，地址是 http://localhost:5175/login")

    assert intent.kind == "learn_page"
    assert intent.url == "http://localhost:5175/login"


def test_parse_chat_intent_execute_task_for_regular_text() -> None:
    intent = parse_chat_intent("帮我登录")

    assert intent.kind == "execute_task"
    assert intent.url is None


def test_pending_choice_parser_accepts_deterministic_aliases() -> None:
    pending_choice = {
        "type": "pending_choice",
        "choice_group_id": "choice-group-test",
        "question": "你想让我做哪个操作？",
        "choices": [
            {"choice_id": "A", "label": "create record", "intent": "execute_operation"},
            {"choice_id": "B", "label": "complete workflow", "intent": "execute_operation"},
        ],
        "turns_remaining": 2,
        "created_at": "2026-05-21T00:00:00+00:00",
    }

    assert _parse_choice_reply("A", pending_choice) == "A"
    assert _parse_choice_reply("1", pending_choice) == "A"
    assert _parse_choice_reply("第一个", pending_choice) == "A"
    assert _parse_choice_reply("complete workflow", pending_choice) == "B"


def test_fill_values_from_intake_includes_record_name_and_credentials() -> None:
    intake = ConversationIntakeResult(
        intent="learn_operation",
        slots=[
            {
                "name": "operator_account",
                "semantic_type": "username",
                "value": "demo",
            },
            {
                "name": "access_secret",
                "semantic_type": "password",
                "value": "123456",
                "sensitive": True,
            },
            {
                "name": "record_name",
                "semantic_type": "record_name",
                "value": "Alpha Record",
            },
        ],
    )

    assert _fill_values_from_intake(intake) == {
        "username": "demo",
        "password": "123456",
        "record_name": "Alpha Record",
    }


def test_fill_values_from_intake_preserves_project_name_slot() -> None:
    intake = ConversationIntakeResult(
        intent="execute_operation",
        slots=[
            {
                "name": "project_name",
                "semantic_type": "project_name",
                "value": "Beta Record",
            }
        ],
    )

    assert _fill_values_from_intake(intake) == {"project_name": "Beta Record"}


def test_parse_product_inputs_does_not_extract_record_name_from_username() -> None:
    assert (
        _parse_product_inputs(
            f"学习 create record：{GENERIC_RECORDS_URL}，username 是 demo"
        )
        is None
    )


def _fake_llm_trace_payload(trace_id: str = "trace-intake-1") -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "purpose": "conversation_intake",
        "agent_role": "conversation_intake_agent",
        "provider": "fake-provider",
        "model": "fake-model",
        "request_id": "req-intake-1",
        "prompt_template_id": "conversation_intake_agent.v1",
        "prompt_hash": "hash-intake-1",
        "schema_name": "ConversationIntakeResult",
        "schema_version": "m11.3.4",
        "schema_validation": {"ok": True},
        "latency_ms": 12,
        "token_usage": {
            "prompt_tokens": 7,
            "completion_tokens": 5,
            "total_tokens": 12,
        },
        "raw_request": {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"学习这个入口：{GENERIC_WORKFLOW_URL}，demo / 123456"
                    ),
                }
            ],
        },
        "raw_response": {"text": '{"intent":"learn_operation"}'},
        "parsed_output": {"intent": "learn_operation"},
        "redaction": {"applied": True},
    }


def test_interactive_chat_learns_login_and_writes_session_action(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo, metadata={"keep": "yes"})

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
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
        "学习一下这个登录页怎么登录，地址是 http://localhost:5175/login，用户名 admin，密码 123456",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is True
    assert result.command_kind == "learn_page"
    assert result.previous_status == "idle"
    assert result.next_status == "task_intake"
    assert "开始学习页面操作。" in result.user_response
    assert "学习完成：我学会了登录操作" in result.user_response

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


def test_interactive_chat_code_reply_writes_response_provenance(
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)
    orch = ConversationOrchestrator(repo)

    orch.dispatch_user_input(
        session_id,
        "帮我登录",
        metadata={"client": "wagent_chat"},
    )

    agent_message = next(
        message for message in repo.list_messages(session_id) if message.role == "agent"
    )
    provenance = agent_message.metadata_json["response_provenance"]
    assert provenance["source_type"] == "code"
    assert provenance["producer"]["type"] == "code"
    assert provenance["producer"]["id"] == "interactive_chat_runtime_code"
    assert provenance["producer"]["internal_agent_role"] is None
    assert provenance["llm_trace_ids"] == []
    assert provenance["generated_from_event_ids"] == []
    assert provenance["fallback"] is False


def test_interactive_chat_entry_gate_skips_intake_and_router_for_non_web(
    repo: ConversationRepository,
) -> None:
    class CountingIntake:
        confidence_threshold = 0.6

        def __init__(self) -> None:
            self.called = False

        def analyze(self, *args, **kwargs):
            self.called = True
            raise AssertionError("non-web chat must not call intake")

    class CountingRouter:
        def __init__(self) -> None:
            self.called = False

        def route(self, *args, **kwargs):
            self.called = True
            raise AssertionError("non-web chat must not call router")

    intake = CountingIntake()
    router = CountingRouter()
    session_id = _create_interactive_chat_session(repo)
    orch = ConversationOrchestrator(
        repo,
        intake_service=intake,
        router_service=router,
    )

    result = orch.dispatch_user_input(
        session_id,
        "你好",
        metadata={"client": "wagent_chat"},
    )

    assert result.command_kind == "non_web_chat"
    assert "网页操作" in result.user_response
    assert intake.called is False
    assert router.called is False
    events = repo.list_events(session_id)
    entry_gate_event = next(e for e in events if e.type == "entry_gate_recorded")
    assert entry_gate_event.payload_json["entry_gate"]["category"] == "non_web_chat"
    assert entry_gate_event.payload_json["skipped_intake_router"] is True
    assert not any(e.type == "llm_trace_recorded" for e in events)
    assert not any(e.type == "chat_learning_started" for e in events)
    assert not any(e.type == "chat_execution_started" for e in events)


def test_interactive_chat_entry_gate_allows_web_task_to_reach_runtime(
    repo: ConversationRepository,
) -> None:
    class WebGate:
        def evaluate(self, raw_message, **kwargs):
            return ConversationEntryGateResult(
                category=ConversationEntryGateCategory.WEB_TASK_CANDIDATE,
                requires_agent_runtime=True,
                confidence=0.9,
                reason_summary="web task",
                latency_ms=3,
                timeout_ms=1500,
            )

        def consume_last_trace_payload(self):
            return None

    class Intake:
        confidence_threshold = 0.6

        def __init__(self) -> None:
            self.called = False

        def analyze(self, raw_message, *, session_metadata=None):
            self.called = True
            return ConversationIntakeResult(
                intent="execute_operation",
                target=ConversationIntakeTarget(url=GENERIC_WORKFLOW_URL),
                action=ConversationIntakeAction(goal="complete workflow"),
                confidence=0.82,
            )

        def consume_last_trace_payload(self):
            return None

    class Router:
        def __init__(self) -> None:
            self.called = False

        def route(self, *, raw_message, intake, context, page_understanding=None):
            self.called = True
            return RouteDecision(
                route_decision=RouteDecisionKind.ASK_USER,
                next_agent=RouterAgentRole.CONVERSATION_ORCHESTRATOR,
                recommended_skill=ApplicationSkillName.ASK_USER_FOR_MISSING_INFO,
                target={"url": GENERIC_WORKFLOW_URL},
                missing_fields=[
                    {
                        "semantic_type": "operation_goal",
                        "display_name": "要学习或执行的操作",
                    }
                ],
                confidence=0.8,
                reason_summary="needs goal",
            )

        def consume_last_trace_payload(self):
            return None

    intake = Intake()
    router = Router()
    session_id = _create_interactive_chat_session(repo)
    orch = ConversationOrchestrator(
        repo,
        entry_gate_service=WebGate(),
        intake_service=intake,
        router_service=router,
    )

    result = orch.dispatch_user_input(
        session_id,
        GENERIC_WORKFLOW_URL,
        metadata={"client": "wagent_chat"},
    )

    assert result.command_kind == "ask_user"
    assert intake.called is True
    assert router.called is True
    events = repo.list_events(session_id)
    event_types = [event.type for event in events]
    assert event_types.index("entry_gate_recorded") < event_types.index("agent_trace_recorded")
    entry_gate_event = next(e for e in events if e.type == "entry_gate_recorded")
    assert entry_gate_event.payload_json["skipped_intake_router"] is False


def test_interactive_chat_entry_gate_preflight_preserves_explicit_url_task(
    repo: ConversationRepository,
) -> None:
    def provider(payload: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("explicit URL should be classified before provider")

    class Intake:
        confidence_threshold = 0.6

        def __init__(self) -> None:
            self.called = False

        def analyze(self, raw_message, *, session_metadata=None):
            self.called = True
            return ConversationIntakeResult(
                intent="execute_operation",
                target=ConversationIntakeTarget(url=GENERIC_WORKFLOW_URL),
                action=ConversationIntakeAction(goal="complete workflow"),
                confidence=0.82,
            )

        def consume_last_trace_payload(self):
            return None

    class Router:
        def __init__(self) -> None:
            self.called = False

        def route(self, *, raw_message, intake, context, page_understanding=None):
            self.called = True
            return RouteDecision(
                route_decision=RouteDecisionKind.ASK_USER,
                next_agent=RouterAgentRole.CONVERSATION_ORCHESTRATOR,
                recommended_skill=ApplicationSkillName.ASK_USER_FOR_MISSING_INFO,
                target={"url": GENERIC_WORKFLOW_URL},
                missing_fields=[],
                confidence=0.8,
                reason_summary="runtime reached",
            )

        def consume_last_trace_payload(self):
            return None

    intake = Intake()
    router = Router()
    session_id = _create_interactive_chat_session(repo)
    orch = ConversationOrchestrator(
        repo,
        entry_gate_service=ConversationEntryGateService(
            provider=provider,
            timeout_ms=100,
        ),
        intake_service=intake,
        router_service=router,
    )

    result = orch.dispatch_user_input(
        session_id,
        f"{GENERIC_WORKFLOW_URL} complete workflow",
        metadata={"client": "wagent_chat"},
    )

    assert result.command_kind == "execute_task"
    assert intake.called is True
    assert router.called is True
    events = repo.list_events(session_id)
    entry_gate_event = next(e for e in events if e.type == "entry_gate_recorded")
    assert entry_gate_event.payload_json["entry_gate"]["category"] == "web_task_candidate"
    assert entry_gate_event.payload_json["skipped_intake_router"] is False


def test_interactive_chat_llm_intake_question_writes_agent_provenance_and_trace(
    repo: ConversationRepository,
) -> None:
    class LlmBackedQuestionIntake:
        confidence_threshold = 0.6

        def __init__(self) -> None:
            self._trace_payload: dict[str, Any] | None = _fake_llm_trace_payload()

        def analyze(
            self,
            raw_message: str,
            *,
            session_metadata: dict[str, Any] | None = None,
        ) -> ConversationIntakeResult:
            return ConversationIntakeResult(
                intent="learn_operation",
                target=ConversationIntakeTarget(
                    url=GENERIC_WORKFLOW_URL,
                    site_origin="http://example.test",
                ),
                action=ConversationIntakeAction(
                    goal="complete workflow",
                    canonical_goal="complete workflow",
                    aliases=["complete workflow"],
                ),
                missing_fields=[
                    {"semantic_type": "username", "display_name": "用户名或账号"},
                    {"semantic_type": "password", "display_name": "密码或口令"},
                ],
                confidence=0.88,
                should_ask_user=True,
                ask_user_message_hint="请提供登录用的用户名和密码。",
            )

        def consume_last_trace_payload(self) -> dict[str, Any] | None:
            payload = self._trace_payload
            self._trace_payload = None
            return payload

    session_id = _create_interactive_chat_session(repo)
    orch = ConversationOrchestrator(
        repo,
        intake_service=LlmBackedQuestionIntake(),
    )

    result = orch.dispatch_user_input(
        session_id,
        f"学习这个工作流入口：{GENERIC_WORKFLOW_URL}",
        metadata={"client": "wagent_chat"},
    )

    assert result.user_response == "请提供登录用的用户名和密码。"
    trace_events = [
        event for event in repo.list_events(session_id) if event.type == "llm_trace_recorded"
    ]
    assert len(trace_events) == 1
    assert trace_events[0].payload_json["trace_id"] == "trace-intake-1"
    assert "123456" not in str(trace_events[0].payload_json)

    agent_message = next(
        message for message in repo.list_messages(session_id) if message.role == "agent"
    )
    provenance = agent_message.metadata_json["response_provenance"]
    assert provenance["source_type"] == "agent"
    assert provenance["producer"]["type"] == "agent"
    assert provenance["producer"]["id"] == "conversation_intake_agent"
    assert provenance["producer"]["internal_agent_role"] == "conversation_intake_agent"
    assert provenance["llm_trace_ids"] == ["trace-intake-1"]
    assert provenance["generated_from_event_ids"] == [trace_events[0].id]
    assert provenance["fallback"] is False


def test_interactive_chat_provider_failure_fallback_provenance_references_trace(
    repo: ConversationRepository,
) -> None:
    class ParseFailureIntake:
        confidence_threshold = 0.6
        provider_fallback = True

        def __init__(self) -> None:
            self._trace_payload: dict[str, Any] | None = _fake_llm_trace_payload(
                "trace-parse-failure"
            )

        def analyze(
            self,
            raw_message: str,
            *,
            session_metadata: dict[str, Any] | None = None,
        ) -> ConversationIntakeResult:
            return ConversationIntakeResult(
                intent="unknown",
                confidence=0.0,
                should_ask_user=True,
                ask_user_message_hint="我还需要再确认一下你的意思。",
                source="provider_parse_error",
            )

        def consume_last_trace_payload(self) -> dict[str, Any] | None:
            payload = self._trace_payload
            self._trace_payload = None
            return payload

    session_id = _create_interactive_chat_session(repo)
    orch = ConversationOrchestrator(repo, intake_service=ParseFailureIntake())

    orch.dispatch_user_input(
        session_id,
        "学习这个页面",
        metadata={"client": "wagent_chat"},
    )

    trace_events = [
        event for event in repo.list_events(session_id) if event.type == "llm_trace_recorded"
    ]
    agent_message = next(
        message for message in repo.list_messages(session_id) if message.role == "agent"
    )
    provenance = agent_message.metadata_json["response_provenance"]
    assert provenance["source_type"] == "code"
    assert provenance["producer"]["id"] == "interactive_chat_runtime_code"
    assert provenance["llm_trace_ids"] == ["trace-parse-failure"]
    assert provenance["generated_from_event_ids"] == [trace_events[0].id]
    assert provenance["fallback"] is True


def test_product_learning_uses_user_url_and_utterance_inputs(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
        calls.append((url, raw_input, kwargs))
        learned_path_id = _ingest_workspace_path(
            db_session,
            source_run_id="run-workspace",
        )
        return LearningRunResult(
            status="learned",
            run_id="run-workspace",
            learned_path_id=learned_path_id,
            target_url=url,
            page_template="/workspace-login",
            scenario=None,
            action_label="进入工作台",
            suggested_utterances=["帮我进入工作台", "进入工作台一下"],
        )

    orch = ConversationOrchestrator(repo, learning_handler=learning_handler)
    result = orch.dispatch_user_input(
        session_id,
        (
            "学习一下这个工作台登录页怎么进入，地址是 "
            "http://localhost:5176/workspace-login，操作员账号是 demo，访问口令是 123456"
        ),
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is True
    assert "学习完成：我学会了进入工作台操作" in result.user_response
    assert calls == [
        (
            "http://localhost:5176/workspace-login",
            (
                "学习一下这个工作台登录页怎么进入，地址是 "
                "http://localhost:5176/workspace-login，操作员账号是 demo，访问口令是 123456"
            ),
            {"headless": False, "fill_values": {"username": "demo", "password": "123456"}},
        )
    ]

    session = repo.get_session(session_id)
    assert session is not None
    actions = session.metadata_json["learned_actions"]
    assert len(actions) == 1
    assert actions[0]["alias"] == "进入工作台"
    assert actions[0]["target_url"] == "http://localhost:5176/workspace-login"
    assert actions[0]["site_origin"] == "http://localhost:5176"
    assert actions[0]["page_template"] == "/workspace-login"


def test_interactive_chat_missing_learning_info_saves_pending_intake(
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)
    learning_called = False

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
        nonlocal learning_called
        learning_called = True
        raise AssertionError("missing fields must not start learning")

    orch = ConversationOrchestrator(repo, learning_handler=learning_handler)
    result = orch.dispatch_user_input(
        session_id,
        "学习一下这个登录页：http://localhost:5176/workspace-login",
        metadata={"client": "wagent_chat"},
    )

    assert learning_called is False
    assert result.allowed is True
    assert result.command_kind == "learn_page"
    assert "用户名" in result.user_response
    assert "密码" in result.user_response

    session = repo.get_session(session_id)
    assert session is not None
    pending = session.metadata_json["pending_intake"]
    assert pending["intent"] == "learn_operation"
    assert pending["target"]["url"] == "http://localhost:5176/workspace-login"
    assert pending["missing_fields"] == ["username", "password"]

    events = repo.list_events(session_id)
    assert not any(e.type == "chat_learning_started" for e in events)


def test_interactive_chat_bare_url_saves_pending_target_without_browser_action(
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)
    learning_called = False
    replay_called = False

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
        nonlocal learning_called
        learning_called = True
        raise AssertionError("bare URL must not start learning")

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        nonlocal replay_called
        replay_called = True
        raise AssertionError("bare URL must not start replay")

    orch = ConversationOrchestrator(
        repo,
        learning_handler=learning_handler,
        replay_handler=replay_handler,
    )
    result = orch.dispatch_user_input(
        session_id,
        "http://localhost:5176/workspace-login",
        metadata={"client": "wagent_chat"},
    )

    assert learning_called is False
    assert replay_called is False
    assert result.command_kind == "ask_user"
    assert "还没学过这个页面" in result.user_response
    assert "学习" in result.user_response
    assert "查看" in result.user_response
    assert "取消" in result.user_response

    session = repo.get_session(session_id)
    assert session is not None
    assert session.metadata_json["pending_target"]["url"] == (
        "http://localhost:5176/workspace-login"
    )
    assert "pending_intake" not in session.metadata_json

    events = repo.list_events(session_id)
    assert any(e.type == "agent_trace_recorded" for e in events)
    assert any(
        e.type == "skill_call_recorded" and e.payload_json["skill"] == "ask_user_for_missing_info"
        for e in events
    )
    assert not any(e.type == "chat_learning_started" for e in events)
    assert not any(e.type == "chat_execution_started" for e in events)


def test_interactive_chat_bare_url_with_learned_actions_does_not_plan(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    path_id = _ingest_items_path(
        db_session,
        source_run_id="run-bare-url-existing-action",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": path_id,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                }
            ]
        },
    )

    class UrlIntake:
        confidence_threshold = 0.6

        def analyze(
            self,
            raw_message: str,
            *,
            session_metadata: dict[str, Any] | None = None,
        ) -> ConversationIntakeResult:
            return ConversationIntakeResult(
                intent="execute_operation",
                target=ConversationIntakeTarget(
                    url="http://localhost:5176/items",
                    site_origin="http://localhost:5176",
                ),
                action=ConversationIntakeAction(
                    goal="新增项目",
                    aliases=["新增项目", "帮我新增项目"],
                ),
                confidence=0.9,
            )

        def consume_last_trace_payload(self):
            return None

    class MisroutingRouter:
        def route(self, *, raw_message, intake, context, page_understanding=None):
            return RouteDecision(
                route_decision=RouteDecisionKind.DELEGATE_TO_WEB_OPERATION_AGENT,
                next_agent=RouterAgentRole.WEB_OPERATION_AGENT,
                recommended_skill=ApplicationSkillName.START_REPLAY,
                target={"url": "http://localhost:5176/items"},
                user_goal="新增项目",
                confidence=0.9,
                reason_summary="incorrectly treats bare URL as execution",
            )

        def consume_last_trace_payload(self):
            return None

    replay_called = False

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        nonlocal replay_called
        replay_called = True
        raise AssertionError("bare URL must not start replay")

    orch = ConversationOrchestrator(
        repo,
        intake_service=UrlIntake(),
        router_service=MisroutingRouter(),
        replay_handler=replay_handler,
    )
    result = orch.dispatch_user_input(
        session_id,
        "http://localhost:5176/items",
        metadata={"client": "wagent_chat"},
    )

    assert replay_called is False
    assert result.command_kind == "ask_user"
    assert "新增项目" in result.user_response
    assert "学习" in result.user_response
    assert "执行" in result.user_response
    events = repo.list_events(session_id)
    assert not any(
        e.type == "chat_progress_recorded"
        and e.payload_json.get("progress_kind") == "planner_candidates_generated"
        for e in events
    )
    assert not any(e.type == "chat_execution_started" for e in events)


def test_interactive_chat_unknown_url_choose_learn_starts_learning_flow(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
        calls.append((url, raw_input, kwargs))
        learned_path_id = _ingest_record_path(
            db_session,
            source_run_id="run-url-unknown-choose-learn",
        )
        return LearningRunResult(
            status="learned",
            run_id="run-url-unknown-choose-learn",
            learned_path_id=learned_path_id,
            target_url=url,
            page_template="/records",
            scenario="product_level",
            action_label="创建记录",
            suggested_utterances=["帮我创建记录", "创建记录一下"],
        )

    orch = ConversationOrchestrator(repo, learning_handler=learning_handler)
    first = orch.dispatch_user_input(
        session_id,
        "http://localhost:5176/records",
        metadata={"client": "wagent_chat"},
    )
    result = orch.dispatch_user_input(
        session_id,
        "学习创建记录，名称叫 Alpha",
        metadata={"client": "wagent_chat"},
    )

    assert "还没学过这个页面" in first.user_response
    assert result.allowed is True
    assert result.command_kind == "learn_page"
    assert len(calls) == 1
    assert calls[0] == (
        "http://localhost:5176/records",
        "学习创建记录，名称叫 Alpha",
        {"headless": False, "fill_values": {"entity_name": "Alpha"}},
    )
    events = repo.list_events(session_id)
    assert any(e.type == "chat_learning_started" for e in events)
    assert any(
        e.type == "chat_learning_completed"
        and e.payload_json.get("run_id") == "run-url-unknown-choose-learn"
        for e in events
    )
    assert not any(e.type == "chat_execution_started" for e in events)


def test_interactive_chat_inspect_route_uses_page_understanding_runtime(
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)

    class InspectRouter:
        def route(self, *, raw_message, intake, context, page_understanding=None):
            return RouteDecision(
                route_decision=RouteDecisionKind.UNDERSTAND_PAGE,
                next_agent=RouterAgentRole.PAGE_UNDERSTANDING_AGENT,
                recommended_skill=ApplicationSkillName.INSPECT_TARGET_PAGE,
                target={"url": "http://localhost:5176/workspace-login"},
                user_goal="登录",
                confidence=0.91,
                reason_summary="needs page context",
                source="llm",
            )

        def consume_last_trace_payload(self):
            return {
                "trace_id": "router-trace-page-1",
                "purpose": "customer_facing_agent_router",
                "agent_role": "customer_facing_agent_router",
                "provider": "openai_compatible",
                "model": "m-test",
                "request_id": "req-router-page-1",
                "prompt_template_id": "customer_facing_agent_router.v1",
                "prompt_hash": "abc",
                "schema_name": "RouteDecision",
                "schema_version": "m11.3.5",
                "schema_validation": {"ok": True},
                "latency_ms": 1,
                "token_usage": {},
                "raw_request": {},
                "raw_response": {},
                "parsed_output": {},
                "redaction": {"applied": True},
            }

    def page_context_provider(*, route_decision, intake, headless):
        return PageContextBuilder().build_from_html(
            url=route_decision.target.url,
            title="Workspace Login",
            html="""
            <main>
              <h1>Workspace Login</h1>
              <label>用户名<input name="username" /></label>
              <label>密码<input name="password" type="password" /></label>
              <button>登录</button>
            </main>
            """,
            learned_actions=[],
        )

    orch = ConversationOrchestrator(
        repo,
        router_service=InspectRouter(),
        page_context_provider=page_context_provider,
    )
    result = orch.dispatch_user_input(
        session_id,
        "看一下 http://localhost:5176/workspace-login 能做什么",
        metadata={"client": "wagent_chat"},
    )

    assert result.command_kind == "understand_page"
    assert result.allowed is True
    assert "我已查看页面" in result.user_response
    session = repo.get_session(session_id)
    assert session is not None
    assert session.metadata_json["pending_target"]["url"] == (
        "http://localhost:5176/workspace-login"
    )

    events = repo.list_events(session_id)
    assert any(
        e.type == "skill_call_recorded"
        and e.payload_json["skill"] == "inspect_target_page"
        and e.payload_json["status"] == "completed"
        for e in events
    )
    assert any(
        e.type == "skill_call_recorded"
        and e.payload_json["skill"] == "understand_page"
        and e.payload_json["status"] == "completed"
        for e in events
    )
    assert any(
        e.type == "llm_trace_recorded" and e.payload_json["trace_id"] == "router-trace-page-1"
        for e in events
    )
    assert any(
        e.type == "agent_trace_recorded"
        and e.payload_json.get("trace_kind") == "page_understanding"
        for e in events
    )
    from app.services.conversation.history import ConversationHistoryService

    history = ConversationHistoryService(repo.session).get_history(session_id)
    assert history is not None
    assert any(
        trace.trace_id == "router-trace-page-1" and trace.schema_name == "RouteDecision"
        for trace in history.llm_traces
    )
    assert not any(e.type == "chat_learning_started" for e in events)
    assert not any(e.type == "chat_execution_started" for e in events)


def test_interactive_chat_learn_intent_overrides_router_inspect_route(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "pending_target": {
                "url": "http://localhost:5176/items",
                "site_origin": "http://localhost:5176",
                "page_hint": "/items",
            }
        },
    )
    learning_calls: list[tuple[str, str, dict[str, Any]]] = []

    class LearnIntake:
        confidence_threshold = 0.6

        def analyze(
            self,
            raw_message: str,
            *,
            session_metadata: dict[str, Any] | None = None,
        ) -> ConversationIntakeResult:
            return ConversationIntakeResult(
                intent="learn_operation",
                target=ConversationIntakeTarget(
                    url="http://localhost:5176/items",
                    site_origin="http://localhost:5176",
                    page_hint="/items",
                ),
                action=ConversationIntakeAction(
                    goal="新增项目",
                    canonical_goal="新增项目",
                    aliases=["新增项目"],
                ),
                slots=[
                    ConversationIntakeSlot(
                        name="item_name",
                        semantic_type="item_name",
                        value="测试项目A",
                    )
                ],
                confidence=0.95,
            )

        def consume_last_trace_payload(self):
            return None

    class MisroutingRouter:
        def route(self, *, raw_message, intake, context, page_understanding=None):
            return RouteDecision(
                route_decision=RouteDecisionKind.UNDERSTAND_PAGE,
                next_agent=RouterAgentRole.PAGE_UNDERSTANDING_AGENT,
                recommended_skill=ApplicationSkillName.INSPECT_TARGET_PAGE,
                target={"url": "http://localhost:5176/items"},
                user_goal="新增项目",
                confidence=0.9,
                reason_summary="incorrectly asks for page understanding",
            )

        def consume_last_trace_payload(self):
            return None

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
        learning_calls.append((url, raw_input, kwargs))
        learned_path_id = _ingest_items_path(
            db_session,
            source_run_id="run-learn-overrides-router-inspect",
            value_slot="item_name",
        )
        return LearningRunResult(
            status="learned",
            run_id="run-learn-overrides-router-inspect",
            learned_path_id=learned_path_id,
            target_url=url,
            page_template="/items",
            scenario="product_level",
            action_label="新增项目",
            suggested_utterances=["帮我新增项目"],
        )

    orch = ConversationOrchestrator(
        repo,
        intake_service=LearnIntake(),
        router_service=MisroutingRouter(),
        learning_handler=learning_handler,
    )

    result = orch.dispatch_user_input(
        session_id,
        "学习新增项目，名称叫 测试项目A",
        metadata={"client": "wagent_chat"},
    )

    assert result.command_kind == "learn_page"
    assert "学习完成：我学会了新增项目操作" in result.user_response
    assert len(learning_calls) == 1
    assert learning_calls[0][2]["fill_values"] == {"item_name": "测试项目A"}
    events = repo.list_events(session_id)
    assert any(e.type == "chat_learning_started" for e in events)
    assert not any(
        e.type == "skill_call_recorded" and e.payload_json["skill"] == "understand_page"
        for e in events
    )


def test_interactive_chat_execute_intent_with_slot_overrides_router_inspect_route(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    path_id = _ingest_items_path(
        db_session,
        source_run_id="run-execute-overrides-router-inspect",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": path_id,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                }
            ]
        },
    )
    calls: list[tuple[str, str, dict[str, Any]]] = []

    class ExecuteIntake:
        confidence_threshold = 0.6

        def analyze(
            self,
            raw_message: str,
            *,
            session_metadata: dict[str, Any] | None = None,
        ) -> ConversationIntakeResult:
            return ConversationIntakeResult(
                intent="execute_operation",
                target=ConversationIntakeTarget(
                    url="http://localhost:5176/items",
                    site_origin="http://localhost:5176",
                    page_hint="/items",
                ),
                action=ConversationIntakeAction(
                    goal="新增项目",
                    canonical_goal="新增项目",
                    aliases=["新增项目", "添加项目"],
                ),
                slots=[
                    ConversationIntakeSlot(
                        name="item_name",
                        semantic_type="item_name",
                        value="测试项目PlannerA",
                    )
                ],
                confidence=0.9,
            )

        def consume_last_trace_payload(self):
            return None

    class MisroutingRouter:
        def route(self, *, raw_message, intake, context, page_understanding=None):
            return RouteDecision(
                route_decision=RouteDecisionKind.UNDERSTAND_PAGE,
                next_agent=RouterAgentRole.PAGE_UNDERSTANDING_AGENT,
                recommended_skill=ApplicationSkillName.INSPECT_TARGET_PAGE,
                target={"url": "http://localhost:5176/items"},
                user_goal="新增项目",
                confidence=0.9,
                reason_summary="incorrectly asks for page understanding",
            )

        def consume_last_trace_payload(self):
            return None

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        calls.append((lid, url, kwargs))
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
            execution_evidence=[
                {
                    "kind": "dom_text_present",
                    "target": "测试项目PlannerA",
                    "status": "verified",
                    "confidence": 0.95,
                    "summary": "列表中出现了名称为“测试项目PlannerA”的项目行。",
                }
            ],
        )

    orch = ConversationOrchestrator(
        repo,
        intake_service=ExecuteIntake(),
        router_service=MisroutingRouter(),
        replay_handler=replay_handler,
    )

    result = orch.dispatch_user_input(
        session_id,
        "帮我处理一下这个页面，名称叫 测试项目PlannerA",
        metadata={"client": "wagent_chat"},
    )

    assert result.command_kind == "execute_task"
    assert "页面证据已确认目标值“测试项目PlannerA”" in result.user_response
    assert len(calls) == 1
    assert calls[0][0] == path_id
    assert calls[0][2]["slot_overrides"] == {"item_name": "测试项目PlannerA"}
    events = repo.list_events(session_id)
    assert any(e.type == "chat_execution_started" for e in events)
    assert not any(
        e.type == "skill_call_recorded" and e.payload_json["skill"] == "understand_page"
        for e in events
    )


def test_interactive_chat_short_learn_uses_pending_target_and_asks_slots(
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)
    orch = ConversationOrchestrator(repo)

    orch.dispatch_user_input(
        session_id,
        "http://localhost:5176/workspace-login",
        metadata={"client": "wagent_chat"},
    )
    result = orch.dispatch_user_input(
        session_id,
        "学习",
        metadata={"client": "wagent_chat"},
    )

    assert result.command_kind == "learn_page"
    assert "用户名" in result.user_response
    assert "密码" in result.user_response
    session = repo.get_session(session_id)
    assert session is not None
    pending = session.metadata_json["pending_intake"]
    assert pending["target"]["url"] == "http://localhost:5176/workspace-login"
    assert pending["missing_fields"] == ["username", "password"]


def test_interactive_chat_merges_pending_intake_and_starts_learning(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
        calls.append((url, raw_input, kwargs))
        learned_path_id = _ingest_workspace_path(
            db_session,
            source_run_id="run-pending-intake",
        )
        return LearningRunResult(
            status="learned",
            run_id="run-pending-intake",
            learned_path_id=learned_path_id,
            target_url=url,
            page_template="/workspace-login",
            scenario=None,
            action_label="进入工作台",
            suggested_utterances=["帮我进入工作台", "打开工作台"],
        )

    orch = ConversationOrchestrator(repo, learning_handler=learning_handler)
    orch.dispatch_user_input(
        session_id,
        "学习一下这个登录页：http://localhost:5176/workspace-login",
        metadata={"client": "wagent_chat"},
    )
    result = orch.dispatch_user_input(
        session_id,
        "用户名 demo，密码 123456",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is True
    assert result.command_kind == "learn_page"
    assert len(calls) == 1
    assert calls[0] == (
        "http://localhost:5176/workspace-login",
        "用户名 demo，密码 123456",
        {"headless": False, "fill_values": {"username": "demo", "password": "123456"}},
    )

    session = repo.get_session(session_id)
    assert session is not None
    assert "pending_intake" not in session.metadata_json


def test_interactive_chat_merges_sensitive_slot_saved_before_missing_info(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)
    calls: list[dict[str, Any]] = []

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
        calls.append(kwargs)
        learned_path_id = _ingest_workspace_path(
            db_session,
            source_run_id="run-sensitive-pending",
        )
        return LearningRunResult(
            status="learned",
            run_id="run-sensitive-pending",
            learned_path_id=learned_path_id,
            target_url=url,
            page_template="/workspace-login",
            scenario=None,
            action_label="进入工作台",
            suggested_utterances=["帮我进入工作台"],
        )

    orch = ConversationOrchestrator(repo, learning_handler=learning_handler)
    first = orch.dispatch_user_input(
        session_id,
        "学习一下这个登录页：http://localhost:5176/workspace-login，密码 123456",
        metadata={"client": "wagent_chat"},
    )
    assert "用户名" in first.user_response

    session = repo.get_session(session_id)
    assert session is not None
    assert session.metadata_json["pending_intake"]["slots"][0]["value"] == "[REDACTED]"

    orch.dispatch_user_input(
        session_id,
        "用户名 demo",
        metadata={"client": "wagent_chat"},
    )

    assert calls == [{"headless": False, "fill_values": {"username": "demo", "password": "123456"}}]


def test_interactive_chat_reasks_when_pending_sensitive_cache_is_missing(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)
    calls: list[dict[str, Any]] = []

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
        calls.append(kwargs)
        learned_path_id = _ingest_workspace_path(
            db_session,
            source_run_id="run-sensitive-cache-missing",
        )
        return LearningRunResult(
            status="learned",
            run_id="run-sensitive-cache-missing",
            learned_path_id=learned_path_id,
            target_url=url,
            page_template="/workspace-login",
            scenario=None,
            action_label="进入工作台",
            suggested_utterances=["帮我进入工作台"],
        )

    orch = ConversationOrchestrator(repo, learning_handler=learning_handler)
    orch.dispatch_user_input(
        session_id,
        "学习一下这个登录页：http://localhost:5176/workspace-login，密码 123456",
        metadata={"client": "wagent_chat"},
    )
    _PENDING_SENSITIVE_VALUES.pop(session_id, None)

    result = orch.dispatch_user_input(
        session_id,
        "用户名 demo",
        metadata={"client": "wagent_chat"},
    )

    assert calls == []
    assert "密码" in result.user_response
    session = repo.get_session(session_id)
    assert session is not None
    assert session.metadata_json["pending_intake"]["missing_fields"] == ["password"]


def test_interactive_chat_cancel_clears_runtime_sensitive_cache(
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)
    orch = ConversationOrchestrator(repo)
    orch.dispatch_user_input(
        session_id,
        "学习一下这个登录页：http://localhost:5176/workspace-login，密码 123456",
        metadata={"client": "wagent_chat"},
    )
    assert _PENDING_SENSITIVE_VALUES.get(session_id) == {"password": "123456"}

    orch.dispatch_user_input(
        session_id,
        "/cancel",
        metadata={"client": "wagent_chat"},
    )

    assert session_id not in _PENDING_SENSITIVE_VALUES


def test_interactive_chat_rejects_missing_info_without_pending_intake(
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)
    learning_called = False

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
        nonlocal learning_called
        learning_called = True
        raise AssertionError("missing info alone must not start learning")

    orch = ConversationOrchestrator(repo, learning_handler=learning_handler)
    result = orch.dispatch_user_input(
        session_id,
        "用户名 demo，密码 123456",
        metadata={"client": "wagent_chat"},
    )

    assert learning_called is False
    assert "先说明要学习或执行什么操作" in result.user_response


def test_interactive_chat_rejects_pending_intake_target_change(
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)
    learning_called = False

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
        nonlocal learning_called
        learning_called = True
        raise AssertionError("changed target must not auto-merge pending intake")

    orch = ConversationOrchestrator(repo, learning_handler=learning_handler)
    orch.dispatch_user_input(
        session_id,
        "学习一下这个登录页：http://localhost:5176/workspace-login",
        metadata={"client": "wagent_chat"},
    )
    result = orch.dispatch_user_input(
        session_id,
        f"{GENERIC_ALT_WORKFLOW_URL} 用户名 demo，密码 123456",
        metadata={"client": "wagent_chat"},
    )

    assert learning_called is False
    assert "页面地址变了" in result.user_response
    session = repo.get_session(session_id)
    assert session is not None
    assert session.metadata_json["pending_intake"]["target"]["url"] == (
        "http://localhost:5176/workspace-login"
    )


def test_interactive_chat_cancel_clears_pending_intake(
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)
    orch = ConversationOrchestrator(repo)
    orch.dispatch_user_input(
        session_id,
        "学习一下这个登录页：http://localhost:5176/workspace-login",
        metadata={"client": "wagent_chat"},
    )
    assert repo.get_session(session_id).metadata_json.get("pending_intake")

    orch.dispatch_user_input(
        session_id,
        "/cancel",
        metadata={"client": "wagent_chat"},
    )

    session = repo.get_session(session_id)
    assert session is not None
    assert "pending_intake" not in session.metadata_json


def test_interactive_chat_pending_intake_expires_after_turns_remaining(
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)
    orch = ConversationOrchestrator(repo)
    orch.dispatch_user_input(
        session_id,
        "学习一下这个登录页：http://localhost:5176/workspace-login",
        metadata={"client": "wagent_chat"},
    )

    for _ in range(3):
        result = orch.dispatch_user_input(
            session_id,
            "用户名 demo",
            metadata={"client": "wagent_chat"},
        )

    assert "补充信息超时" in result.user_response
    session = repo.get_session(session_id)
    assert session is not None
    assert "pending_intake" not in session.metadata_json


def test_interactive_chat_invalid_provider_output_preserves_pending_intake(
    repo: ConversationRepository,
) -> None:
    class InvalidProviderIntake:
        confidence_threshold = 0.6

        def __init__(self) -> None:
            self.calls = 0

        def analyze(
            self,
            raw_message: str,
            *,
            session_metadata: dict[str, Any] | None = None,
        ) -> ConversationIntakeResult:
            self.calls += 1
            if self.calls == 1:
                return ConversationIntakeResult(
                    intent="learn_operation",
                    target=ConversationIntakeTarget(
                        url="http://localhost:5176/workspace-login",
                        site_origin="http://localhost:5176",
                    ),
                    action=ConversationIntakeAction(
                        goal="登录",
                        canonical_goal="进入工作台",
                        aliases=["登录", "进入工作台"],
                    ),
                    missing_fields=[
                        {"semantic_type": "username", "display_name": "用户名或账号"},
                        {"semantic_type": "password", "display_name": "密码或口令"},
                    ],
                    confidence=0.8,
                    should_ask_user=True,
                )
            return ConversationIntakeResult(
                intent="unknown",
                confidence=0.0,
                should_ask_user=True,
                ask_user_message_hint="我还需要再确认一下你的意思。",
                source="provider_error",
            )

    session_id = _create_interactive_chat_session(repo)
    learning_called = False

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
        nonlocal learning_called
        learning_called = True
        raise AssertionError("invalid provider output must not start learning")

    orch = ConversationOrchestrator(
        repo,
        learning_handler=learning_handler,
        intake_service=InvalidProviderIntake(),
    )
    orch.dispatch_user_input(
        session_id,
        "学习一下这个登录页：http://localhost:5176/workspace-login",
        metadata={"client": "wagent_chat"},
    )
    result = orch.dispatch_user_input(
        session_id,
        "用户名 demo，密码 123456",
        metadata={"client": "wagent_chat"},
    )

    assert learning_called is False
    assert "我还需要再确认" in result.user_response
    session = repo.get_session(session_id)
    assert session is not None
    assert session.metadata_json.get("pending_intake")


def test_interactive_chat_low_confidence_intake_does_not_start_browser_action(
    repo: ConversationRepository,
) -> None:
    class LowConfidenceIntake:
        def analyze(
            self,
            raw_message: str,
            *,
            session_metadata: dict[str, Any] | None = None,
        ) -> ConversationIntakeResult:
            return ConversationIntakeResult(
                intent="learn_operation",
                target=ConversationIntakeTarget(
                    url="http://localhost:5176/workspace-login",
                    site_origin="http://localhost:5176",
                ),
                action=ConversationIntakeAction(
                    goal="登录",
                    canonical_goal="进入工作台",
                    aliases=["登录", "进入工作台"],
                ),
                confidence=0.2,
                should_ask_user=False,
            )

    session_id = _create_interactive_chat_session(repo)
    learning_called = False

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
        nonlocal learning_called
        learning_called = True
        raise AssertionError("low confidence intake must not start learning")

    orch = ConversationOrchestrator(
        repo,
        learning_handler=learning_handler,
        intake_service=LowConfidenceIntake(),
    )
    result = orch.dispatch_user_input(
        session_id,
        "学习这个页面",
        metadata={"client": "wagent_chat"},
    )

    assert learning_called is False
    assert "我还需要再确认" in result.user_response
    assert result.allowed is True


def test_learning_does_not_claim_success_when_path_is_not_queryable(
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
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
        "学习一下这个登录页怎么登录，地址是 http://localhost:5175/login，用户名 admin，密码 123456",
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

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
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
        "学习一下这个登录页怎么登录，地址是 http://localhost:5175/login，用户名 admin，密码 123456",
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
    active_updates = [
        e.payload_json["active_task"]
        for e in events
        if e.type == "chat_progress_recorded"
        and e.payload_json.get("progress_kind") == "active_task_updated"
    ]
    assert any(
        task["kind"] == "learn_operation" and task["status"] == "learning"
        for task in active_updates
    )
    assert any(
        e.type == "chat_progress_recorded"
        and e.payload_json.get("progress_kind") == "active_task_cleared"
        for e in events
    )
    assert "active_task" not in session.metadata_json


def test_same_alias_learning_keeps_different_target_urls(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)
    run_count = 0

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
        nonlocal run_count
        run_count += 1
        source_run_id = f"run-workspace-{run_count}"
        learned_path_id = _ingest_workspace_path(
            db_session,
            source_run_id=source_run_id,
        )
        return LearningRunResult(
            status="learned",
            run_id=source_run_id,
            learned_path_id=learned_path_id,
            target_url=url,
            page_template="/workspace-login",
            scenario=None,
            action_label="进入工作台",
            suggested_utterances=["帮我进入工作台"],
        )

    orch = ConversationOrchestrator(repo, learning_handler=learning_handler)
    orch.dispatch_user_input(
        session_id,
        (
            "学习一下这个工作台登录页怎么进入，地址是 "
            "http://localhost:5176/workspace-login，操作员账号是 demo，访问口令是 123456"
        ),
        metadata={"client": "wagent_chat"},
    )
    orch.dispatch_user_input(
        session_id,
        (
            "学习一下这个工作台登录页怎么进入，地址是 "
            f"{GENERIC_ALT_WORKFLOW_URL}，操作员账号是 demo，访问口令是 123456"
        ),
        metadata={"client": "wagent_chat"},
    )

    session = repo.get_session(session_id)
    assert session is not None
    actions = session.metadata_json["learned_actions"]
    assert len(actions) == 2
    assert {action["target_url"] for action in actions} == {
        "http://localhost:5176/workspace-login",
        GENERIC_ALT_WORKFLOW_URL,
    }


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

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
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
    execution_updates = [
        e.payload_json["active_task"]
        for e in events
        if e.type == "chat_progress_recorded"
        and e.payload_json.get("progress_kind") == "active_task_updated"
    ]
    assert any(
        task["kind"] == "execute_operation" and task["status"] == "executing"
        for task in execution_updates
    )
    assert any(
        e.type == "chat_progress_recorded"
        and e.payload_json.get("progress_kind") == "active_task_cleared"
        for e in events
    )

    agent_messages = [m.content for m in repo.list_messages(session_id) if m.role == "agent"]
    assert "执行中。" in agent_messages
    assert "登录完成。" in agent_messages


def test_interactive_chat_execute_passes_item_name_slot_overrides(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_items_path(
        db_session,
        source_run_id="run-items-param",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                    "scenario": None,
                }
            ]
        },
    )
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        calls.append((lid, url, kwargs))
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    result = orch.dispatch_user_input(
        session_id,
        "帮我新增项目，名称叫测试项目B",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is True
    assert "还没有拿到足够页面证据确认结果" in result.user_response
    assert len(calls) == 1
    assert calls[0][0] == learned_path_id
    assert calls[0][1] == "http://localhost:5176/items"
    assert calls[0][2]["headless"] is False
    assert calls[0][2]["slot_overrides"] == {"item_name": "测试项目B"}
    target = calls[0][2]["evidence_targets"][0]
    assert target.kind == "dom_text_present"
    assert target.text == "测试项目B"
    assert target.source_slot == "item_name"
    assert target.selector is None
    events = repo.list_events(session_id)
    started = next(e for e in events if e.type == "chat_execution_started")
    assert started.payload_json["slot_overrides"] == {"item_name": "测试项目B"}
    reported = next(e for e in events if e.type == "task_result_reported")
    assert reported.payload_json["verification_outcome"] == "uncertain"
    assert reported.payload_json["task_verified"] is False


def test_interactive_chat_execute_uses_reporter_verified_response(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_items_path(
        db_session,
        source_run_id="run-items-evidence",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                    "scenario": None,
                }
            ]
        },
    )

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
            execution_evidence=[
                {
                    "kind": "dom_text_present",
                    "target": "测试项目B",
                    "status": "verified",
                    "confidence": 0.95,
                    "summary": "列表中出现了名称为“测试项目B”的项目行。",
                }
            ],
        )

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    result = orch.dispatch_user_input(
        session_id,
        "帮我新增项目，名称叫测试项目B",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is True
    assert "页面证据已确认目标值“测试项目B”" in result.user_response
    events = repo.list_events(session_id)
    reported = next(e for e in events if e.type == "task_result_reported")
    assert reported.payload_json["verification_outcome"] == "verified"
    assert reported.payload_json["task_verified"] is True


def test_interactive_chat_execute_does_not_claim_success_without_evidence(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_items_path(
        db_session,
        source_run_id="run-items-no-evidence",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                    "scenario": None,
                }
            ]
        },
    )

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    result = orch.dispatch_user_input(
        session_id,
        "帮我新增项目，名称叫测试项目B",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is True
    assert "新增项目成功" not in result.user_response
    assert "还没有拿到足够页面证据确认结果" in result.user_response


def test_interactive_chat_replay_failed_offers_basic_recovery(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_items_path(
        db_session,
        source_run_id="run-items-replay-failed",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                }
            ]
        },
    )

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="failed",
            drift_status="none",
            error="button not found",
        )

    result = ConversationOrchestrator(repo, replay_handler=replay_handler).dispatch_user_input(
        session_id,
        "帮我新增项目，名称叫测试项目B",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is False
    assert "执行失败" in result.user_response
    assert "A. 重试执行该操作" in result.user_response
    assert "B. 重新学习" in result.user_response
    assert "C. 取消" in result.user_response
    assert learned_path_id not in result.user_response
    session = repo.get_session(session_id)
    assert session is not None
    pending_choice = session.metadata_json["pending_choice"]
    assert "learned_path_id" not in json.dumps(pending_choice, ensure_ascii=False)
    private_map = session.metadata_json["pending_choice_private_map"]
    assert private_map["A"]["kind"] == "retry_replay"
    assert private_map["A"]["learned_path_id"] == learned_path_id
    assert private_map["A"]["slot_overrides"] == {"item_name": "测试项目B"}
    assert private_map["B"]["kind"] == "relearn_operation"
    assert private_map["C"]["kind"] == "cancel"
    active_task = session.metadata_json["active_task"]
    assert active_task["kind"] == "execute_operation"
    assert active_task["owner"] == "runtime"
    assert active_task["status"] == "waiting_for_user_input"
    events = repo.list_events(session_id)
    offered = [
        e
        for e in events
        if e.type == "chat_progress_recorded"
        and e.payload_json.get("progress_kind") == "failure_recovery_offered"
    ][-1]
    offered_text = json.dumps(offered.payload_json, ensure_ascii=False)
    assert "learned_path_id" not in offered_text
    assert "slot_overrides" not in offered_text
    assert "evidence_targets" not in offered_text


def test_interactive_chat_eval_fault_injection_forces_needs_review_recovery(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_items_path(
        db_session,
        source_run_id="run-items-eval-fault",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "client": "wagent_eval",
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                }
            ],
        },
    )

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
            execution_evidence=[
                {
                    "kind": "dom_text_present",
                    "target": "测试项目B",
                    "status": "verified",
                    "confidence": 0.95,
                    "summary": "列表中出现了名称为“测试项目B”的项目行。",
                }
            ],
        )

    result = ConversationOrchestrator(repo, replay_handler=replay_handler).dispatch_user_input(
        session_id,
        "帮我新增项目，名称叫测试项目B",
        metadata={
            "client": "wagent_eval",
            "eval_fault_injection": {
                "case_id": "failure_recovery_menu_safety",
                "reporter_outcome": "needs_review",
            },
        },
    )

    assert result.allowed is True
    assert "A. 重试执行该操作" in result.user_response
    assert "重试会再次执行该操作" in result.user_response
    session = repo.get_session(session_id)
    assert session is not None
    assert session.metadata_json["pending_choice_private_map"]["A"]["kind"] == "retry_replay"
    events = repo.list_events(session_id)
    hook_event = [
        e for e in events if e.payload_json.get("progress_kind") == "eval_fault_injection_applied"
    ][-1]
    assert hook_event.payload_json == {
        "progress_kind": "eval_fault_injection_applied",
        "case_id": "failure_recovery_menu_safety",
        "fault_class": "needs_review",
    }
    hook_text = json.dumps(hook_event.payload_json, ensure_ascii=False)
    assert "learned_path_id" not in hook_text
    assert "slot_overrides" not in hook_text
    assert "evidence_targets" not in hook_text


@pytest.mark.parametrize(
    ("metadata", "session_client"),
    [
        ({}, "wagent_eval"),
        (
            {
                "client": "wagent_chat",
                "eval_fault_injection": {
                    "case_id": "failure_recovery_menu_safety",
                    "reporter_outcome": "needs_review",
                },
            },
            "wagent_chat",
        ),
        (
            {
                "client": "wagent_eval",
                "eval_fault_injection": {
                    "case_id": "failure_recovery_menu_safety",
                    "reporter_outcome": "verified",
                },
            },
            "wagent_eval",
        ),
    ],
)
def test_interactive_chat_eval_fault_injection_ignored_unless_valid_opt_in(
    db_session: Session,
    repo: ConversationRepository,
    metadata: dict[str, Any],
    session_client: str,
) -> None:
    learned_path_id = _ingest_items_path(
        db_session,
        source_run_id=f"run-items-eval-fault-ignored-{session_client}",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "client": session_client,
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                }
            ],
        },
    )

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
            execution_evidence=[
                {
                    "kind": "dom_text_present",
                    "target": "测试项目B",
                    "status": "verified",
                    "confidence": 0.95,
                    "summary": "列表中出现了名称为“测试项目B”的项目行。",
                }
            ],
        )

    result = ConversationOrchestrator(repo, replay_handler=replay_handler).dispatch_user_input(
        session_id,
        "帮我新增项目，名称叫测试项目B",
        metadata=metadata,
    )

    assert result.allowed is True
    assert "页面证据已确认目标值“测试项目B”" in result.user_response
    assert "A. 重试执行该操作" not in result.user_response
    events = repo.list_events(session_id)
    assert not [
        e for e in events if e.payload_json.get("progress_kind") == "eval_fault_injection_applied"
    ]


def test_interactive_chat_eval_candidate_binding_creates_non_planner_pending_choice(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_items_path(
        db_session,
        source_run_id="run-items-eval-choice-binding",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "client": "wagent_eval",
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                }
            ],
        },
    )
    replay_calls: list[tuple[str, str, dict[str, Any]]] = []

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        replay_calls.append((lid, url, kwargs))
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
            execution_evidence=[
                {
                    "kind": "dom_text_present",
                    "target": "测试项目ChoiceA",
                    "status": "verified",
                    "confidence": 0.95,
                    "summary": "列表中出现了名称为“测试项目ChoiceA”的项目行。",
                }
            ],
        )

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    first = orch.dispatch_user_input(
        session_id,
        "帮我处理一下这个页面：http://localhost:5176/items，名称叫测试项目ChoiceA",
        metadata={
            "client": "wagent_eval",
            "eval_candidate_setup": {
                "case_id": "pending_choice_multi_candidate",
                "setup_type": "eval_only_candidate_binding",
                "live_multi_action_capability": False,
                "actions": [
                    {
                        "choice_id": "A",
                        "alias": "新增项目",
                        "learned_path_id": learned_path_id,
                    },
                    {
                        "choice_id": "B",
                        "alias": "添加项目",
                        "learned_path_id": learned_path_id,
                    },
                    {
                        "choice_id": "C",
                        "alias": "录入项目",
                        "learned_path_id": learned_path_id,
                    },
                ],
            },
        },
    )

    assert replay_calls == []
    assert "我找到了多个可能的操作" in first.user_response
    assert "A. 新增项目" in first.user_response
    assert "B. 添加项目" in first.user_response
    assert "C. 录入项目" in first.user_response
    assert learned_path_id not in first.user_response

    session = repo.get_session(session_id)
    assert session is not None
    pending_choice_text = json.dumps(
        session.metadata_json["pending_choice"],
        ensure_ascii=False,
    )
    assert learned_path_id not in pending_choice_text
    assert "learned_path_id" not in pending_choice_text
    assert session.metadata_json["pending_choice_private_map"]["A"]["kind"] == "learned_action"
    assert session.metadata_json["pending_choice_private_map"]["A"]["slot_overrides"] == {
        "entity_name": "测试项目ChoiceA"
    }

    result = orch.dispatch_user_input(
        session_id,
        "A",
        metadata={"client": "wagent_eval"},
    )

    assert result.allowed is True
    assert "页面证据已确认目标值“测试项目ChoiceA”" in result.user_response
    assert len(replay_calls) == 1
    assert replay_calls[0][0] == learned_path_id
    assert replay_calls[0][1] == "http://localhost:5176/items"
    assert replay_calls[0][2]["headless"] is False
    assert replay_calls[0][2]["slot_overrides"] == {"item_name": "测试项目ChoiceA"}
    assert replay_calls[0][2]["evidence_targets"]
    session = repo.get_session(session_id)
    assert session is not None
    assert "pending_choice" not in session.metadata_json
    assert "pending_choice_private_map" not in session.metadata_json
    events = repo.list_events(session_id)
    assert any(
        e.payload_json.get("progress_kind") == "eval_candidate_setup_applied" for e in events
    )
    assert any(e.payload_json.get("progress_kind") == "pending_choice_created" for e in events)
    assert not any(e.payload_json.get("progress_kind") == "planner_choice_created" for e in events)
    hook_event = [
        e for e in events if e.payload_json.get("progress_kind") == "eval_candidate_setup_applied"
    ][-1]
    hook_text = json.dumps(hook_event.payload_json, ensure_ascii=False)
    assert learned_path_id not in hook_text
    assert "learned_path_id" not in hook_text
    assert "pending_choice_private_map" not in hook_text
    assert "selector" not in hook_text


def test_interactive_chat_history_strips_pending_choice_private_path_ids(
    repo: ConversationRepository,
) -> None:
    from app.services.conversation.history import ConversationHistoryService

    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "pending_choice": {
                "type": "pending_choice",
                "choice_group_id": "choice-group-leaky",
                "question": "你想让我执行哪一个？",
                "choices": [
                    {
                        "choice_id": "A",
                        "label": "新增项目",
                        "intent": "execute_operation",
                        "learned_path_id": "lp-private-choice",
                    }
                ],
                "turns_remaining": 2,
                "created_at": "2026-05-21T00:00:00+00:00",
            },
            "pending_choice_private_map": {
                "A": {
                    "kind": "learned_action",
                    "learned_path_id": "lp-private-choice",
                    "slot_overrides": {"item_name": "测试项目B"},
                }
            },
        },
    )
    repo.append_event(
        session_id=session_id,
        type="chat_progress_recorded",
        payload={
            "progress_kind": "pending_choice_created",
            "pending_choice": {
                "type": "pending_choice",
                "choices": [
                    {
                        "choice_id": "A",
                        "label": "新增项目",
                        "learned_path_id": "lp-private-event",
                    }
                ],
            },
            "pending_choice_private_map": {"A": {"learned_path_id": "lp-private-event"}},
        },
    )

    history = ConversationHistoryService(repo.session).get_history(session_id)

    assert history is not None
    payload_text = json.dumps(history.model_dump(mode="json"), ensure_ascii=False)
    assert "pending_choice" in payload_text
    assert "pending_choice_private_map" not in payload_text
    assert "learned_path_id" not in payload_text
    assert "lp-private-choice" not in payload_text
    assert "lp-private-event" not in payload_text


@pytest.mark.parametrize(
    ("metadata", "session_client"),
    [
        ({}, "wagent_eval"),
        (
            {
                "client": "wagent_chat",
                "eval_candidate_setup": {
                    "case_id": "pending_choice_multi_candidate",
                    "setup_type": "eval_only_candidate_binding",
                    "actions": [],
                },
            },
            "wagent_chat",
        ),
        (
            {
                "client": "wagent_eval",
                "eval_candidate_setup": {
                    "case_id": "unknown",
                    "setup_type": "eval_only_candidate_binding",
                    "actions": [],
                },
            },
            "wagent_eval",
        ),
    ],
)
def test_interactive_chat_eval_candidate_binding_ignored_unless_valid_opt_in(
    db_session: Session,
    repo: ConversationRepository,
    metadata: dict[str, Any],
    session_client: str,
) -> None:
    learned_path_id = _ingest_workspace_path(
        db_session,
        source_run_id=f"run-workspace-eval-choice-ignored-{session_client}",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "client": session_client,
            "learned_actions": [
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/workspace-login",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/workspace-login",
                }
            ],
        },
    )
    replay_calls: list[str] = []

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        replay_calls.append(lid)
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    result = ConversationOrchestrator(repo, replay_handler=replay_handler).dispatch_user_input(
        session_id,
        "帮我处理一下这个页面：http://localhost:5176/workspace-login",
        metadata=metadata,
    )

    assert result.allowed is True
    assert replay_calls == [learned_path_id]
    events = repo.list_events(session_id)
    assert not [
        e for e in events if e.payload_json.get("progress_kind") == "eval_candidate_setup_applied"
    ]
    session = repo.get_session(session_id)
    assert session is not None
    assert "pending_choice" not in session.metadata_json
    assert "pending_choice_private_map" not in session.metadata_json


def test_interactive_chat_blocked_drift_offers_basic_recovery(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_items_path(
        db_session,
        source_run_id="run-items-recovery-drift",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                }
            ]
        },
    )

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="page_mismatch",
        )

    result = ConversationOrchestrator(repo, replay_handler=replay_handler).dispatch_user_input(
        session_id,
        "帮我新增项目，名称叫测试项目B",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is False
    assert "当前页面和学习时的页面不匹配" in result.user_response
    assert "A. 重试执行该操作" in result.user_response
    session = repo.get_session(session_id)
    assert session is not None
    assert session.metadata_json["pending_choice_private_map"]["A"]["failure_reason"] == "blocked"


def test_interactive_chat_recovery_retry_replays_once_with_original_payload(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_items_path(
        db_session,
        source_run_id="run-items-recovery-retry",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                }
            ]
        },
    )
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        calls.append((lid, url, kwargs))
        if len(calls) == 1:
            return ConversationReplaySummary(
                learned_path_id=lid,
                url=url,
                replay_status="succeeded",
                drift_status="none",
            )
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
            execution_evidence=[
                {
                    "kind": "dom_text_present",
                    "target": "测试项目B",
                    "status": "verified",
                    "confidence": 0.95,
                    "summary": "列表中出现了名称为“测试项目B”的项目行。",
                }
            ],
        )

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    first = orch.dispatch_user_input(
        session_id,
        "帮我新增项目，名称叫测试项目B",
        metadata={"client": "wagent_chat"},
    )

    assert "重试会再次执行该操作" in first.user_response

    retry = orch.dispatch_user_input(
        session_id,
        "A",
        metadata={"client": "wagent_chat"},
    )

    assert "页面证据已确认目标值“测试项目B”" in retry.user_response
    assert len(calls) == 2
    assert calls[1][0] == learned_path_id
    assert calls[1][1] == "http://localhost:5176/items"
    assert calls[1][2]["slot_overrides"] == {"item_name": "测试项目B"}
    assert calls[1][2]["evidence_targets"][0].text == "测试项目B"
    session = repo.get_session(session_id)
    assert session is not None
    assert "pending_choice" not in session.metadata_json
    assert "pending_choice_private_map" not in session.metadata_json
    events = repo.list_events(session_id)
    selected = [
        e
        for e in events
        if e.type == "chat_progress_recorded"
        and e.payload_json.get("progress_kind") == "failure_recovery_selected"
    ][-1]
    started = [
        e
        for e in events
        if e.type == "chat_progress_recorded"
        and e.payload_json.get("progress_kind") == "failure_recovery_retry_started"
    ][-1]
    for event in (selected, started):
        event_text = json.dumps(event.payload_json, ensure_ascii=False)
        assert "learned_path_id" not in event_text
        assert "slot_overrides" not in event_text
        assert "evidence_targets" not in event_text


def test_interactive_chat_recovery_retry_failure_does_not_auto_loop(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_items_path(
        db_session,
        source_run_id="run-items-recovery-retry-fails",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                }
            ]
        },
    )
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        calls.append((lid, url, kwargs))
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="failed",
            drift_status="none",
            error="button not found",
        )

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    orch.dispatch_user_input(
        session_id,
        "帮我新增项目，名称叫测试项目B",
        metadata={"client": "wagent_chat"},
    )
    retry = orch.dispatch_user_input(
        session_id,
        "A",
        metadata={"client": "wagent_chat"},
    )

    assert len(calls) == 2
    assert retry.allowed is False
    assert "A. 重试执行该操作" in retry.user_response
    session = repo.get_session(session_id)
    assert session is not None
    assert session.metadata_json["pending_choice_private_map"]["A"]["retry_count"] == 1


def test_interactive_chat_recovery_relearn_starts_learning_without_replay(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_items_path(
        db_session,
        source_run_id="run-items-recovery-relearn-old",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                }
            ]
        },
    )
    replay_calls: list[tuple[str, str, dict[str, Any]]] = []
    learning_calls: list[tuple[str, str, dict[str, Any]]] = []

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        replay_calls.append((lid, url, kwargs))
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
        learning_calls.append((url, raw_input, kwargs))
        new_path_id = _ingest_items_path(
            db_session,
            source_run_id="run-items-recovery-relearn-new",
            value_slot="item_name",
        )
        return LearningRunResult(
            status="learned",
            run_id="run-items-recovery-relearn-new",
            learned_path_id=new_path_id,
            target_url=url,
            page_template="/items",
            scenario="product_level",
            action_label="新增项目",
            suggested_utterances=["帮我新增项目"],
        )

    orch = ConversationOrchestrator(
        repo,
        replay_handler=replay_handler,
        learning_handler=learning_handler,
    )
    orch.dispatch_user_input(
        session_id,
        "帮我新增项目，名称叫测试项目B",
        metadata={"client": "wagent_chat"},
    )
    result = orch.dispatch_user_input(
        session_id,
        "B",
        metadata={"client": "wagent_chat"},
    )

    assert "学习完成" in result.user_response
    assert len(replay_calls) == 1
    assert len(learning_calls) == 1
    assert learning_calls[0][0] == "http://localhost:5176/items"
    assert learning_calls[0][2]["fill_values"] == {"item_name": "测试项目B"}
    session = repo.get_session(session_id)
    assert session is not None
    assert "pending_choice" not in session.metadata_json
    assert "pending_choice_private_map" not in session.metadata_json
    events = repo.list_events(session_id)
    started = [
        e
        for e in events
        if e.type == "chat_progress_recorded"
        and e.payload_json.get("progress_kind") == "failure_recovery_relearn_started"
    ][-1]
    started_text = json.dumps(started.payload_json, ensure_ascii=False)
    assert "learned_path_id" not in started_text
    assert "slot_overrides" not in started_text


def test_interactive_chat_recovery_cancel_clears_state_and_records_event(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_items_path(
        db_session,
        source_run_id="run-items-recovery-cancel",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                }
            ],
        },
    )

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="failed",
            drift_status="none",
            error="button not found",
        )

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    orch.dispatch_user_input(
        session_id,
        "帮我新增项目，名称叫测试项目B",
        metadata={"client": "wagent_chat"},
    )
    repo.update_session_status(
        session_id,
        "task_intake",
        metadata_patch={
            "pending_intake": {"intent": "execute_operation"},
            "pending_target": {"url": "http://localhost:5176/items"},
            "last_no_path_reason": {"reason": "test"},
        },
    )
    result = orch.dispatch_user_input(
        session_id,
        "C",
        metadata={"client": "wagent_chat"},
    )

    assert result.user_response == "已取消当前任务。"
    session = repo.get_session(session_id)
    assert session is not None
    for key in (
        "pending_intake",
        "pending_target",
        "pending_choice",
        "pending_choice_private_map",
        "last_no_path_reason",
        "active_task",
    ):
        assert key not in session.metadata_json
    events = repo.list_events(session_id)
    cancelled = [
        e
        for e in events
        if e.type == "chat_progress_recorded"
        and e.payload_json.get("progress_kind") == "failure_recovery_cancelled"
    ][-1]
    cancelled_text = json.dumps(cancelled.payload_json, ensure_ascii=False)
    assert "learned_path_id" not in cancelled_text
    assert "slot_overrides" not in cancelled_text


def test_interactive_chat_blocks_item_name_replay_without_value_slot(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_items_path(db_session, source_run_id="run-items-fixed")
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                    "scenario": None,
                }
            ]
        },
    )
    replay_called = False

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        nonlocal replay_called
        replay_called = True
        raise AssertionError("non-parameterized item path must not replay")

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    result = orch.dispatch_user_input(
        session_id,
        "帮我新增项目，名称叫测试项目B",
        metadata={"client": "wagent_chat"},
    )

    assert replay_called is False
    assert result.allowed is False
    assert "还不支持这次输入里的参数替换" in result.user_response
    events = repo.list_events(session_id)
    assert any(
        e.type == "chat_execution_failed"
        and e.payload_json["reason"] == "unsupported_value_slot"
        for e in events
    )
    assert not any(e.type == "chat_execution_started" for e in events)


def test_interactive_chat_rejects_unlearned_target_url(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_workspace_path(db_session)
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/workspace-login",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/workspace-login",
                    "scenario": None,
                }
            ]
        },
    )
    replay_called = False

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
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
        "帮我在 http://localhost:5176/orders 进入工作台",
        metadata={"client": "wagent_chat"},
    )

    assert "还没学过这个页面" in result.user_response
    assert "学习" in result.user_response
    assert "查看" in result.user_response
    assert "取消" in result.user_response
    assert replay_called is False


def test_interactive_chat_requires_url_for_same_alias_multiple_targets(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    path_a = _ingest_workspace_path(db_session, source_run_id="run-a")
    path_b = _ingest_workspace_path(db_session, source_run_id="run-b")
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": path_a,
                    "target_url": "http://localhost:5176/workspace-login",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/workspace-login",
                    "scenario": None,
                },
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": path_b,
                    "target_url": GENERIC_ALT_WORKFLOW_URL,
                    "site_origin": "http://alt.example.test",
                    "page_template": "/workspace-login",
                    "scenario": None,
                },
            ]
        },
    )
    replay_called = False

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
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
        "帮我进入工作台",
        metadata={"client": "wagent_chat"},
    )

    assert "我找到了多个可能的操作" in result.user_response
    assert "A. 进入工作台" in result.user_response
    assert "B. 进入工作台" in result.user_response
    assert replay_called is False
    session = repo.get_session(session_id)
    assert session is not None
    pending_choice = session.metadata_json["pending_choice"]
    assert pending_choice["choices"][0]["choice_id"] == "A"
    assert "learned_path_id" not in json.dumps(pending_choice, ensure_ascii=False)
    private_map = session.metadata_json["pending_choice_private_map"]
    assert private_map["A"]["kind"] == "planner_route_choice"
    assert private_map["A"]["learned_path_id"] == path_a
    assert private_map["B"]["kind"] == "planner_route_choice"
    assert private_map["B"]["learned_path_id"] == path_b
    assert session.metadata_json["active_task"]["kind"] == "clarify"
    assert session.metadata_json["active_task"]["status"] == "waiting_for_user_input"
    events = repo.list_events(session_id)
    created = [
        e
        for e in events
        if e.type == "chat_progress_recorded"
        and e.payload_json.get("progress_kind") == "planner_choice_created"
    ][-1]
    assert created.payload_json["candidate_count"] == 2
    assert "learned_path_id" not in json.dumps(created.payload_json, ensure_ascii=False)


def test_interactive_chat_multi_candidate_invokes_task_path_planner_and_sanitizes_choice(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    path_a = _ingest_workspace_path(db_session, source_run_id="run-planner-a")
    path_b = _ingest_workspace_path(db_session, source_run_id="run-planner-b")
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": path_a,
                    "target_url": "http://localhost:5176/workspace-login",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/workspace-login",
                    "scenario": "product_level",
                },
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": path_b,
                    "target_url": GENERIC_ALT_WORKFLOW_URL,
                    "site_origin": "http://alt.example.test",
                    "page_template": "/workspace-login",
                    "scenario": "product_level",
                },
            ]
        },
    )
    planner_calls: list[tuple[str, list[str]]] = []

    def plan(
        self: TaskPathPlanner,
        task_intent: Any,
        candidates: list[Any],
    ) -> AgentDPlannerOutput:
        planner_calls.append(
            (task_intent.raw_text, [candidate.learned_path_id for candidate in candidates])
        )
        return AgentDPlannerOutput(
            route_plan=RoutePlan(
                task_intent=task_intent,
                steps=[
                    RouteStep(
                        order=0,
                        learned_path_id=path_a,
                        purpose="Execute workspace entry after user confirmation.",
                    )
                ],
                confirmation_required=True,
            ),
            confirmation_requirements=[
                ConfirmationRequirement(
                    reason="ambiguous_selection",
                    message="Please confirm the selected operation.",
                    severity="info",
                )
            ],
            risk_hints=[
                RiskHint(
                    risk_type="flaky_path",
                    reason="This path has historical warning signals.",
                    severity="warning",
                )
            ],
            uncertainty=["multiple matching operations"],
            warnings=["top candidate requires confirmation"],
        )

    monkeypatch.setattr(TaskPathPlanner, "plan", plan)
    replay_called = False

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        nonlocal replay_called
        replay_called = True
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    result = ConversationOrchestrator(repo, replay_handler=replay_handler).dispatch_user_input(
        session_id,
        "帮我进入工作台",
        metadata={"client": "wagent_chat"},
    )

    assert planner_calls == [("帮我进入工作台", [path_a, path_b])]
    assert replay_called is False
    assert "我找到了多个可能的操作" in result.user_response
    assert "learned_path_id" not in result.user_response
    assert path_a not in result.user_response
    assert path_b not in result.user_response

    session = repo.get_session(session_id)
    assert session is not None
    pending_choice = session.metadata_json["pending_choice"]
    pending_choice_text = json.dumps(pending_choice, ensure_ascii=False)
    assert path_a not in pending_choice_text
    assert path_b not in pending_choice_text
    assert "learned_path_id" not in pending_choice_text
    assert "存在 Planner 警告" in pending_choice_text
    assert "top candidate requires confirmation" not in pending_choice_text

    private_map = session.metadata_json["pending_choice_private_map"]
    assert private_map["A"]["kind"] == "planner_route_choice"
    assert private_map["A"]["learned_path_id"] == path_a
    assert private_map["A"]["planner_summary"]["confirmation_required"] is True
    assert private_map["B"]["kind"] == "planner_route_choice"
    assert private_map["B"]["learned_path_id"] == path_b

    events = repo.list_events(session_id)
    created = [
        e
        for e in events
        if e.type == "chat_progress_recorded"
        and e.payload_json.get("progress_kind") == "planner_choice_created"
    ][-1]
    created_text = json.dumps(created.payload_json, ensure_ascii=False)
    assert created.payload_json["candidate_count"] == 2
    assert created.payload_json["planner_warning_count"] == 1
    assert created.payload_json["planner_risk_count"] == 1
    assert path_a not in created_text
    assert path_b not in created_text
    assert "learned_path_id" not in created_text


def test_interactive_chat_planner_warning_uses_generic_visible_text(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    path_a = _ingest_workspace_path(db_session, source_run_id="run-planner-warning-a")
    path_b = _ingest_workspace_path(db_session, source_run_id="run-planner-warning-b")
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": path_a,
                    "target_url": "http://localhost:5176/workspace-login",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/workspace-login",
                    "scenario": "product_level",
                },
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": path_b,
                    "target_url": GENERIC_ALT_WORKFLOW_URL,
                    "site_origin": "http://alt.example.test",
                    "page_template": "/workspace-login",
                    "scenario": "product_level",
                },
            ]
        },
    )
    private_warning = (
        f"selector=[data-testid='item-name-input']; item_name=测试项目B; selected_path_id={path_a}"
    )

    def plan(
        self: TaskPathPlanner,
        task_intent: Any,
        candidates: list[Any],
    ) -> AgentDPlannerOutput:
        return AgentDPlannerOutput(
            route_plan=RoutePlan(
                task_intent=task_intent,
                steps=[
                    RouteStep(
                        order=0,
                        learned_path_id=path_a,
                        purpose="Execute top candidate.",
                    )
                ],
            ),
            warnings=[private_warning],
        )

    monkeypatch.setattr(TaskPathPlanner, "plan", plan)

    result = ConversationOrchestrator(repo).dispatch_user_input(
        session_id,
        "帮我进入工作台",
        metadata={"client": "wagent_chat"},
    )

    session = repo.get_session(session_id)
    assert session is not None
    pending_choice_text = json.dumps(
        session.metadata_json["pending_choice"],
        ensure_ascii=False,
    )
    visible_text = result.user_response + "\n" + pending_choice_text
    assert "存在 Planner 警告" in visible_text
    assert "data-testid" not in visible_text
    assert "item-name-input" not in visible_text
    assert "测试项目B" not in visible_text
    assert "selected_path_id" not in visible_text
    assert path_a not in visible_text
    private_map_text = json.dumps(
        session.metadata_json["pending_choice_private_map"],
        ensure_ascii=False,
    )
    assert "item-name-input" in private_map_text
    assert "测试项目B" in private_map_text


def test_interactive_chat_continue_with_active_task_does_not_enter_planner(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    path_a = _ingest_workspace_path(db_session, source_run_id="run-active-task-a")
    path_b = _ingest_workspace_path(db_session, source_run_id="run-active-task-b")
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "active_task": {
                "task_id": "task-active",
                "kind": "clarify",
                "owner": "runtime",
                "status": "waiting_for_user_input",
                "target_url": "http://localhost:5176/workspace-login",
                "goal": "进入工作台",
                "created_at": "2026-05-22T00:00:00+08:00",
                "updated_at": "2026-05-22T00:00:00+08:00",
            },
            "learned_actions": [
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": path_a,
                    "target_url": "http://localhost:5176/workspace-login",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/workspace-login",
                    "scenario": "product_level",
                },
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": path_b,
                    "target_url": GENERIC_ALT_WORKFLOW_URL,
                    "site_origin": "http://alt.example.test",
                    "page_template": "/workspace-login",
                    "scenario": "product_level",
                },
            ],
        },
    )

    def plan(
        self: TaskPathPlanner,
        task_intent: Any,
        candidates: list[Any],
    ) -> AgentDPlannerOutput:
        raise AssertionError("active_task continuation must run before Planner")

    monkeypatch.setattr(TaskPathPlanner, "plan", plan)

    result = ConversationOrchestrator(repo).dispatch_user_input(
        session_id,
        "继续",
        metadata={"client": "wagent_chat"},
    )

    assert "当前还有一个操作需要你补充或确认" in result.user_response
    session = repo.get_session(session_id)
    assert session is not None
    assert "pending_choice" not in session.metadata_json
    assert "pending_choice_private_map" not in session.metadata_json
    events = repo.list_events(session_id)
    assert not any(
        e.type == "chat_progress_recorded"
        and e.payload_json.get("progress_kind") == "planner_choice_created"
        for e in events
    )


def test_interactive_chat_completed_active_task_does_not_block_planner(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    path_a = _ingest_workspace_path(
        db_session,
        source_run_id="run-completed-active-task-a",
    )
    path_b = _ingest_workspace_path(
        db_session,
        source_run_id="run-completed-active-task-b",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "active_task": {
                "task_id": "task-completed",
                "kind": "clarify",
                "owner": "runtime",
                "status": "completed",
                "target_url": "http://localhost:5176/workspace-login",
                "goal": "进入工作台",
                "created_at": "2026-05-22T00:00:00+08:00",
                "updated_at": "2026-05-22T00:00:00+08:00",
            },
            "learned_actions": [
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": path_a,
                    "target_url": "http://localhost:5176/workspace-login",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/workspace-login",
                    "scenario": "product_level",
                },
                {
                    "alias": "查看工作台",
                    "utterances": ["帮我查看工作台"],
                    "learned_path_id": path_b,
                    "target_url": GENERIC_ALT_WORKFLOW_URL,
                    "site_origin": "http://alt.example.test",
                    "page_template": "/workspace-login",
                    "scenario": "product_level",
                },
            ],
        },
    )
    planner_calls = 0

    def plan(
        self: TaskPathPlanner,
        task_intent: Any,
        candidates: list[Any],
    ) -> AgentDPlannerOutput:
        nonlocal planner_calls
        planner_calls += 1
        return AgentDPlannerOutput(
            route_plan=RoutePlan(
                task_intent=task_intent,
                steps=[
                    RouteStep(
                        order=0,
                        learned_path_id=path_a,
                        purpose="Continue with a fresh planner choice.",
                    )
                ],
            )
        )

    monkeypatch.setattr(TaskPathPlanner, "plan", plan)

    result = ConversationOrchestrator(repo).dispatch_user_input(
        session_id,
        "继续",
        metadata={"client": "wagent_chat"},
    )

    assert planner_calls == 1
    assert "我找到了多个可能的操作" in result.user_response
    session = repo.get_session(session_id)
    assert session is not None
    assert session.metadata_json["pending_choice"]["type"] == "pending_choice"
    events = repo.list_events(session_id)
    assert not any(
        e.type == "chat_progress_recorded"
        and e.payload_json.get("progress_kind") == "active_task_continue_requested"
        for e in events
    )


def test_interactive_chat_url_plus_vague_request_invokes_planner_instead_of_guessing(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    path_a = _ingest_workspace_path(
        db_session,
        source_run_id="run-planner-url-a",
        page_template="/items",
    )
    path_b = _ingest_workspace_path(
        db_session,
        source_run_id="run-planner-url-b",
        page_template="/items",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": path_a,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                    "scenario": "product_level",
                },
                {
                    "alias": "查看项目",
                    "utterances": ["帮我查看项目"],
                    "learned_path_id": path_b,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                    "scenario": "product_level",
                },
            ]
        },
    )
    planner_calls = 0

    def plan(
        self: TaskPathPlanner,
        task_intent: Any,
        candidates: list[Any],
    ) -> AgentDPlannerOutput:
        nonlocal planner_calls
        planner_calls += 1
        assert task_intent.target_page_hint == "http://localhost:5176/items"
        return AgentDPlannerOutput(
            route_plan=RoutePlan(
                task_intent=task_intent,
                steps=[
                    RouteStep(
                        order=0,
                        learned_path_id=path_a,
                        purpose="Execute top same-page candidate.",
                    )
                ],
            ),
        )

    monkeypatch.setattr(TaskPathPlanner, "plan", plan)
    replay_called = False

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        nonlocal replay_called
        replay_called = True
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    result = ConversationOrchestrator(repo, replay_handler=replay_handler).dispatch_user_input(
        session_id,
        "http://localhost:5176/items 帮我处理一下这个页面",
        metadata={"client": "wagent_chat"},
    )

    assert planner_calls == 1
    assert replay_called is False
    assert "我找到了多个可能的操作" in result.user_response
    assert "A. 新增项目" in result.user_response
    assert "B. 查看项目" in result.user_response


def test_interactive_chat_single_candidate_skips_task_path_planner(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_workspace_path(db_session, source_run_id="run-single-no-plan")
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/workspace-login",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/workspace-login",
                    "scenario": "product_level",
                }
            ]
        },
    )

    def plan(
        self: TaskPathPlanner,
        task_intent: Any,
        candidates: list[Any],
    ) -> AgentDPlannerOutput:
        raise AssertionError("single-candidate execution must not call TaskPathPlanner")

    monkeypatch.setattr(TaskPathPlanner, "plan", plan)
    calls: list[tuple[str, str]] = []

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        calls.append((lid, url))
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    result = ConversationOrchestrator(repo, replay_handler=replay_handler).dispatch_user_input(
        session_id,
        "帮我进入工作台",
        metadata={"client": "wagent_chat"},
    )

    assert result.user_response == "执行中。\n进入工作台完成。"
    assert calls == [(learned_path_id, "http://localhost:5176/workspace-login")]


def test_interactive_chat_planner_unable_does_not_create_executable_private_map(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    path_a = _ingest_workspace_path(db_session, source_run_id="run-unable-a")
    path_b = _ingest_workspace_path(db_session, source_run_id="run-unable-b")
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": path_a,
                    "target_url": "http://localhost:5176/workspace-login",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/workspace-login",
                    "scenario": "product_level",
                },
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": path_b,
                    "target_url": GENERIC_ALT_WORKFLOW_URL,
                    "site_origin": "http://alt.example.test",
                    "page_template": "/workspace-login",
                    "scenario": "product_level",
                },
            ]
        },
    )

    def plan(
        self: TaskPathPlanner,
        task_intent: Any,
        candidates: list[Any],
    ) -> AgentDPlannerOutput:
        return AgentDPlannerOutput(
            route_plan=None,
            uncertainty=["No reliable top route."],
            warnings=["Unable to plan safely."],
        )

    monkeypatch.setattr(TaskPathPlanner, "plan", plan)
    replay_called = False

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        nonlocal replay_called
        replay_called = True
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    result = ConversationOrchestrator(repo, replay_handler=replay_handler).dispatch_user_input(
        session_id,
        "帮我进入工作台",
        metadata={"client": "wagent_chat"},
    )

    assert replay_called is False
    assert "还不能可靠判断" in result.user_response
    session = repo.get_session(session_id)
    assert session is not None
    assert "pending_choice_private_map" not in session.metadata_json
    events = repo.list_events(session_id)
    unable = [
        e
        for e in events
        if e.type == "chat_progress_recorded"
        and e.payload_json.get("progress_kind") == "planner_unable_to_plan"
    ][-1]
    unable_text = json.dumps(unable.payload_json, ensure_ascii=False)
    assert path_a not in unable_text
    assert path_b not in unable_text
    assert "learned_path_id" not in unable_text


def test_interactive_chat_pending_choice_selects_first_action_and_clears_state(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    path_a = _ingest_workspace_path(db_session, source_run_id="run-select-a")
    path_b = _ingest_workspace_path(db_session, source_run_id="run-select-b")
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": path_a,
                    "target_url": "http://localhost:5176/workspace-login",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/workspace-login",
                    "scenario": None,
                },
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": path_b,
                    "target_url": GENERIC_ALT_WORKFLOW_URL,
                    "site_origin": "http://alt.example.test",
                    "page_template": "/workspace-login",
                    "scenario": None,
                },
            ]
        },
    )
    calls: list[tuple[str, str]] = []

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        calls.append((lid, url))
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    orch.dispatch_user_input(
        session_id,
        "帮我进入工作台",
        metadata={"client": "wagent_chat"},
    )
    result = orch.dispatch_user_input(
        session_id,
        "A",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is True
    assert result.user_response == "执行中。\n进入工作台完成。"
    assert calls == [(path_a, "http://localhost:5176/workspace-login")]
    session = repo.get_session(session_id)
    assert session is not None
    assert "pending_choice" not in session.metadata_json
    assert "pending_choice_private_map" not in session.metadata_json
    assert "active_task" not in session.metadata_json


def test_interactive_chat_pending_choice_selection_preserves_item_name_override(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    path_a = _ingest_items_path(
        db_session,
        source_run_id="run-choice-items-a",
        value_slot="item_name",
    )
    path_b = _ingest_items_path(
        db_session,
        source_run_id="run-choice-items-b",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": path_a,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                },
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": path_b,
                    "target_url": GENERIC_ALT_RECORDS_URL,
                    "site_origin": "http://alt.example.test",
                    "page_template": "/items",
                },
            ]
        },
    )
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        calls.append((lid, url, kwargs))
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
            execution_evidence=[
                {
                    "kind": "dom_text_present",
                    "target": "测试项目B",
                    "status": "verified",
                    "confidence": 0.95,
                    "summary": "列表中出现了名称为“测试项目B”的项目行。",
                }
            ],
        )

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    first = orch.dispatch_user_input(
        session_id,
        "帮我新增项目，名称叫测试项目B",
        metadata={"client": "wagent_chat"},
    )

    assert "我找到了多个可能的操作" in first.user_response
    session = repo.get_session(session_id)
    assert session is not None
    pending_choice_text = json.dumps(
        session.metadata_json["pending_choice"],
        ensure_ascii=False,
    )
    assert "测试项目B" not in pending_choice_text
    assert (
        session.metadata_json["pending_choice_private_map"]["A"]["kind"] == "planner_route_choice"
    )
    assert session.metadata_json["pending_choice_private_map"]["A"]["slot_overrides"] == {
        "entity_name": "测试项目B"
    }

    result = orch.dispatch_user_input(
        session_id,
        "A",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is True
    assert "页面证据已确认目标值“测试项目B”" in result.user_response
    assert len(calls) == 1
    assert calls[0][0] == path_a
    assert calls[0][1] == "http://localhost:5176/items"
    assert calls[0][2]["slot_overrides"] == {"item_name": "测试项目B"}
    target = calls[0][2]["evidence_targets"][0]
    assert target.text == "测试项目B"
    assert target.source_slot == "item_name"
    events = repo.list_events(session_id)
    selected = [
        e
        for e in events
        if e.type == "chat_progress_recorded"
        and e.payload_json.get("progress_kind") == "planner_choice_selected"
    ][-1]
    selected_text = json.dumps(selected.payload_json, ensure_ascii=False)
    assert path_a not in selected_text
    assert "测试项目B" not in selected_text
    assert "slot_overrides" not in selected_text


def test_interactive_chat_planner_choice_selection_executes_private_choice_when_action_missing(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    path_a = _ingest_items_path(
        db_session,
        source_run_id="run-choice-private-fallback-a",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "pending_choice": {
                "type": "pending_choice",
                "choice_group_id": "choice-group-private-fallback",
                "question": "我找到了多个可能的操作，你想让我执行哪一个？",
                "choices": [
                    {
                        "choice_id": "A",
                        "label": "新增项目",
                        "description": "在当前页面新增项目",
                        "intent": "execute_operation",
                    }
                ],
                "turns_remaining": 2,
                "created_at": "2026-05-21T00:00:00+00:00",
            },
            "pending_choice_private_map": {
                "A": {
                    "kind": "planner_route_choice",
                    "learned_path_id": path_a,
                    "target_url": "http://localhost:5176/items",
                    "action_alias": "新增项目",
                    "page_template": "/items",
                    "slot_overrides": {"item_name": "测试项目PrivateA"},
                    "planner_summary": {"confirmation_required": True},
                }
            },
        },
    )
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        calls.append((lid, url, kwargs))
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
            execution_evidence=[
                {
                    "kind": "dom_text_present",
                    "target": "测试项目PrivateA",
                    "status": "verified",
                    "confidence": 0.95,
                    "summary": "列表中出现了名称为“测试项目PrivateA”的项目行。",
                }
            ],
        )

    result = ConversationOrchestrator(repo, replay_handler=replay_handler).dispatch_user_input(
        session_id,
        "A",
        metadata={"client": "wagent_eval"},
    )

    assert result.allowed is True
    assert "页面证据已确认目标值“测试项目PrivateA”" in result.user_response
    assert len(calls) == 1
    assert calls[0][0] == path_a
    assert calls[0][1] == "http://localhost:5176/items"
    assert calls[0][2]["slot_overrides"] == {"item_name": "测试项目PrivateA"}
    events = repo.list_events(session_id)
    progress = [e.payload_json.get("progress_kind") for e in events]
    assert "planner_choice_selected" in progress
    assert any(e.type == "chat_execution_started" for e in events)


def test_interactive_chat_pending_choice_clarify_preserves_item_name_privately(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    path_a = _ingest_items_path(
        db_session,
        source_run_id="run-choice-clarify-private-slot-a",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "pending_choice": {
                "type": "pending_choice",
                "choice_group_id": "choice-group-clarify-slot",
                "question": "我找到了多个可能的操作，你想让我执行哪一个？",
                "choices": [
                    {
                        "choice_id": "A",
                        "label": "新增项目",
                        "description": "在当前页面新增项目",
                        "intent": "execute_operation",
                    }
                ],
                "turns_remaining": 2,
                "created_at": "2026-05-21T00:00:00+00:00",
            },
            "pending_choice_private_map": {
                "A": {
                    "kind": "planner_route_choice",
                    "learned_path_id": path_a,
                    "target_url": "http://localhost:5176/items",
                    "action_alias": "新增项目",
                    "page_template": "/items",
                    "planner_summary": {"confirmation_required": True},
                }
            },
        },
    )
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        calls.append((lid, url, kwargs))
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
            execution_evidence=[
                {
                    "kind": "dom_text_present",
                    "target": "测试项目PlannerA",
                    "status": "verified",
                    "confidence": 0.95,
                    "summary": "列表中出现了名称为“测试项目PlannerA”的项目行。",
                }
            ],
        )

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    retry = orch.dispatch_user_input(
        session_id,
        "名称叫 测试项目PlannerA",
        metadata={"client": "wagent_eval"},
    )

    assert retry.command_kind == "pending_choice_clarify"
    session = repo.get_session(session_id)
    assert session is not None
    private_map = session.metadata_json["pending_choice_private_map"]
    assert private_map["A"]["slot_overrides"] == {"entity_name": "测试项目PlannerA"}
    public_text = json.dumps(session.metadata_json["pending_choice"], ensure_ascii=False)
    assert "测试项目PlannerA" not in public_text
    events = repo.list_events(session_id)
    retry_event = [
        e
        for e in events
        if e.type == "chat_progress_recorded"
        and e.payload_json.get("progress_kind") == "pending_choice_retry"
    ][-1]
    retry_event_text = json.dumps(retry_event.payload_json, ensure_ascii=False)
    assert "测试项目PlannerA" not in retry_event_text
    assert "slot_overrides" not in retry_event_text

    result = orch.dispatch_user_input(
        session_id,
        "A",
        metadata={"client": "wagent_eval"},
    )

    assert result.allowed is True
    assert "页面证据已确认目标值“测试项目PlannerA”" in result.user_response
    assert calls[0][0] == path_a
    assert calls[0][2]["slot_overrides"] == {"item_name": "测试项目PlannerA"}


def test_interactive_chat_parameterized_path_requires_runtime_item_name(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_items_path(
        db_session,
        source_run_id="run-items-needs-runtime-slot",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                }
            ]
        },
    )
    replay_called = False

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        nonlocal replay_called
        replay_called = True
        raise AssertionError("parameterized path must wait for item_name")

    result = ConversationOrchestrator(repo, replay_handler=replay_handler).dispatch_user_input(
        session_id,
        "帮我新增项目",
        metadata={"client": "wagent_chat"},
    )

    assert replay_called is False
    assert "还需要参数 item_name" in result.user_response
    session = repo.get_session(session_id)
    assert session is not None
    assert session.metadata_json["active_task"]["kind"] == "clarify"
    assert session.metadata_json["active_task"]["status"] == "waiting_for_user_input"


def test_interactive_chat_pending_choice_invalid_answer_expires(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    path_a = _ingest_workspace_path(db_session, source_run_id="run-expire-a")
    path_b = _ingest_workspace_path(db_session, source_run_id="run-expire-b")
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": path_a,
                    "target_url": "http://localhost:5176/workspace-login",
                    "page_template": "/workspace-login",
                },
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": path_b,
                    "target_url": GENERIC_ALT_WORKFLOW_URL,
                    "page_template": "/workspace-login",
                },
            ]
        },
    )
    orch = ConversationOrchestrator(repo)
    orch.dispatch_user_input(
        session_id,
        "帮我进入工作台",
        metadata={"client": "wagent_chat"},
    )

    retry = orch.dispatch_user_input(
        session_id,
        "Z",
        metadata={"client": "wagent_chat"},
    )
    session = repo.get_session(session_id)
    assert session is not None
    assert retry.user_response.startswith("我没有识别出你的选择")
    assert session.metadata_json["pending_choice"]["turns_remaining"] == 1

    expired = orch.dispatch_user_input(
        session_id,
        "还是不懂",
        metadata={"client": "wagent_chat"},
    )

    assert "选择已过期" in expired.user_response
    session = repo.get_session(session_id)
    assert session is not None
    assert "pending_choice" not in session.metadata_json
    assert "pending_choice_private_map" not in session.metadata_json
    assert "active_task" not in session.metadata_json


def test_interactive_chat_pending_choice_revision_reruns_intake(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    workspace_path = _ingest_workspace_path(db_session, source_run_id="run-revise-ws")
    items_path = _ingest_items_path(
        db_session,
        source_run_id="run-revise-items",
        value_slot="item_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "进入工作台",
                    "utterances": ["帮我进入工作台"],
                    "learned_path_id": workspace_path,
                    "target_url": "http://localhost:5176/workspace-login",
                    "page_template": "/workspace-login",
                },
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": items_path,
                    "target_url": "http://localhost:5176/items",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/items",
                },
            ]
        },
    )
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        calls.append((lid, url, kwargs))
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
            execution_evidence=[
                {
                    "kind": "dom_text_present",
                    "target": "测试项目B",
                    "status": "verified",
                    "confidence": 0.95,
                    "summary": "列表中出现了名称为“测试项目B”的项目行。",
                }
            ],
        )

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    orch.dispatch_user_input(
        session_id,
        "帮我处理一下这个页面",
        metadata={"client": "wagent_chat"},
    )
    result = orch.dispatch_user_input(
        session_id,
        "不是，我要新增项目，名称叫测试项目B",
        metadata={"client": "wagent_chat"},
    )

    assert "页面证据已确认目标值“测试项目B”" in result.user_response
    assert len(calls) == 1
    assert calls[0][0] == items_path
    assert calls[0][1] == "http://localhost:5176/items"
    assert calls[0][2]["headless"] is False
    assert calls[0][2]["slot_overrides"] == {"item_name": "测试项目B"}
    assert calls[0][2]["evidence_targets"][0].text == "测试项目B"
    session = repo.get_session(session_id)
    assert session is not None
    assert "pending_choice" not in session.metadata_json
    assert "pending_choice_private_map" not in session.metadata_json


def test_interactive_chat_chinese_cancel_clears_pending_choice_and_active_task(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    path_id = _ingest_workspace_path(db_session, source_run_id="run-cancel-choice")
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "pending_intake": {"intent": "learn_operation"},
            "pending_target": {"url": "http://localhost:5176/workspace-login"},
            "pending_choice": {
                "type": "pending_choice",
                "choice_group_id": "choice-group-test",
                "question": "你想让我做哪个操作？",
                "choices": [
                    {
                        "choice_id": "A",
                        "label": "进入工作台",
                        "intent": "execute_operation",
                    }
                ],
                "turns_remaining": 2,
                "created_at": "2026-05-21T00:00:00+00:00",
            },
            "pending_choice_private_map": {
                "A": {"kind": "learned_action", "learned_path_id": path_id}
            },
            "last_no_path_reason": {"reason": "test"},
            "active_task": {
                "task_id": "task-test",
                "kind": "clarify",
                "owner": "runtime",
                "status": "waiting_for_user_input",
                "created_at": "2026-05-21T00:00:00+00:00",
                "updated_at": "2026-05-21T00:00:00+00:00",
            },
        },
    )

    result = ConversationOrchestrator(repo).dispatch_user_input(
        session_id,
        "算了",
        metadata={"client": "wagent_chat"},
    )

    assert result.user_response == "已取消当前任务。"
    session = repo.get_session(session_id)
    assert session is not None
    for key in (
        "pending_intake",
        "pending_target",
        "pending_choice",
        "pending_choice_private_map",
        "last_no_path_reason",
        "active_task",
    ):
        assert key not in session.metadata_json


def test_interactive_chat_execute_uses_canonical_goal_aliases(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_workspace_path(db_session)
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "打开目标页面",
                    "utterances": ["帮我打开目标页面"],
                    "learned_path_id": learned_path_id,
                    "target_url": GENERIC_WORKFLOW_URL,
                    "site_origin": "http://example.test",
                    "page_template": "/workflow",
                    "scenario": None,
                }
            ]
        },
    )
    calls: list[tuple[str, str]] = []

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        calls.append((lid, url))
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    result = orch.dispatch_user_input(
        session_id,
        "帮我打开目标页面",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is True
    assert result.user_response == "执行中。\n打开目标页面完成。"
    assert calls == [(learned_path_id, GENERIC_WORKFLOW_URL)]


def test_interactive_chat_execute_matches_value_specific_learned_alias_generically(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_record_path(
        db_session,
        source_run_id="run-value-specific-alias",
        value_slot="entity_name",
    )
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "创建记录名称叫 Alpha",
                    "utterances": ["帮我创建记录名称叫 Alpha"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/records",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/records",
                    "scenario": None,
                }
            ]
        },
    )
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        calls.append((lid, url, kwargs))
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
            execution_evidence=[
                {
                    "kind": "dom_text_present",
                    "target": "Beta",
                    "status": "verified",
                    "confidence": 0.95,
                    "summary": "页面文本中出现了目标值“Beta”。",
                }
            ],
        )

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    result = orch.dispatch_user_input(
        session_id,
        "帮我创建记录，名称叫 Beta",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is True
    assert "页面证据已确认目标值“Beta”" in result.user_response
    assert len(calls) == 1
    assert calls[0][0] == learned_path_id
    assert calls[0][1] == "http://localhost:5176/records"
    assert calls[0][2]["slot_overrides"] == {"entity_name": "Beta"}
    assert calls[0][2]["evidence_targets"][0].text == "Beta"
    events = repo.list_events(session_id)
    assert any(e.type == "chat_execution_started" for e in events)
    assert any(
        e.type == "task_result_reported"
        and e.payload_json.get("verification_outcome") == "verified"
        for e in events
    )


def test_interactive_chat_single_candidate_conflicting_action_does_not_execute(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_record_path(db_session, source_run_id="run-conflict-action")
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "创建记录",
                    "utterances": ["帮我创建记录"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/records",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/records",
                    "scenario": None,
                }
            ]
        },
    )
    replay_called = False

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        nonlocal replay_called
        replay_called = True
        raise AssertionError("conflicting explicit action must not replay the only candidate")

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    result = orch.dispatch_user_input(
        session_id,
        "帮我删除记录，页面 http://localhost:5176/records",
        metadata={"client": "wagent_chat"},
    )

    assert replay_called is False
    assert "学过这个页面的一些操作" in result.user_response
    assert "还没学过你要做的这个操作" in result.user_response
    events = repo.list_events(session_id)
    assert not any(e.type == "chat_execution_started" for e in events)


def test_interactive_chat_execute_unknown_page_guidance_does_not_replay(
    repo: ConversationRepository,
) -> None:
    session_id = _create_interactive_chat_session(repo)
    replay_called = False

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        nonlocal replay_called
        replay_called = True
        raise AssertionError("unknown page must not replay")

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    result = orch.dispatch_user_input(
        session_id,
        "帮我创建记录，名称叫 Alpha，页面 http://localhost:5176/records",
        metadata={"client": "wagent_chat"},
    )

    assert replay_called is False
    assert "还没学过这个页面" in result.user_response
    assert "学习" in result.user_response
    assert "查看" in result.user_response
    assert "取消" in result.user_response
    events = repo.list_events(session_id)
    assert not any(e.type == "chat_execution_started" for e in events)


def test_interactive_chat_execute_learned_page_unmatched_operation_guidance(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    learned_path_id = _ingest_record_path(db_session, source_run_id="run-unmatched-operation")
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "创建记录",
                    "utterances": ["帮我创建记录"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5176/records",
                    "site_origin": "http://localhost:5176",
                    "page_template": "/records",
                    "scenario": None,
                }
            ]
        },
    )
    replay_called = False

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        nonlocal replay_called
        replay_called = True
        raise AssertionError("unmatched operation must not replay unrelated action")

    orch = ConversationOrchestrator(repo, replay_handler=replay_handler)
    result = orch.dispatch_user_input(
        session_id,
        "帮我删除记录，页面 http://localhost:5176/records",
        metadata={"client": "wagent_chat"},
    )

    assert replay_called is False
    assert "学过这个页面的一些操作" in result.user_response
    assert "创建记录" in result.user_response
    assert "还没学过你要做的这个操作" in result.user_response
    assert "学习" in result.user_response
    assert "取消" in result.user_response
    events = repo.list_events(session_id)
    assert not any(e.type == "chat_execution_started" for e in events)


def test_interactive_chat_missing_session_action_does_not_use_global_paths(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    _ingest_login_path(db_session)
    session_id = _create_interactive_chat_session(repo)
    replay_called = False

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
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
    assert "还没学过这个页面" in result.user_response
    assert "学习" in result.user_response
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

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
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


# ── 11.3.1 visible browser operation ─────────────────────────────────────────


def test_visible_session_passes_headless_false_to_learning_handler(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    """API-1: visible session calls learning handler with headless=False."""
    session_id = _create_interactive_chat_session(repo, metadata={"browser_visibility": "visible"})
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
        calls.append((url, raw_input, kwargs))
        learned_path_id = _ingest_login_path(db_session, source_run_id="run-vis")
        return LearningRunResult(
            status="learned",
            run_id="run-vis",
            learned_path_id=learned_path_id,
            target_url=url,
            page_template="/login",
            scenario="valid_credentials",
            action_label="登录",
            suggested_utterances=["帮我登录"],
        )

    orch = ConversationOrchestrator(repo, learning_handler=learning_handler)
    result = orch.dispatch_user_input(
        session_id,
        "学习一下这个登录页怎么登录，地址是 http://localhost:5175/login，用户名 admin，密码 123456",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is True
    assert len(calls) == 1
    assert calls[0][2].get("headless") is False


def test_visible_session_passes_headless_false_to_replay_handler(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    """API-2: visible session calls replay handler with headless=False."""
    learned_path_id = _ingest_login_path(db_session)
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "browser_visibility": "visible",
            "learned_actions": [
                {
                    "alias": "登录",
                    "utterances": ["帮我登录"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5175/login",
                    "page_template": "/login",
                    "scenario": "valid_credentials",
                }
            ],
        },
    )
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        calls.append((lid, url, kwargs))
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
    assert len(calls) == 1
    assert calls[0][2].get("headless") is False


def test_headless_session_passes_headless_true_to_handlers(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    """API-3: headless session passes headless=True to learning and replay."""
    session_id = _create_interactive_chat_session(repo, metadata={"browser_visibility": "headless"})
    learn_calls: list[dict[str, Any]] = []

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
        learn_calls.append(kwargs)
        learned_path_id = _ingest_login_path(db_session, source_run_id="run-hl")
        return LearningRunResult(
            status="learned",
            run_id="run-hl",
            learned_path_id=learned_path_id,
            target_url=url,
            page_template="/login",
            scenario="valid_credentials",
            action_label="登录",
            suggested_utterances=["帮我登录"],
        )

    orch = ConversationOrchestrator(repo, learning_handler=learning_handler)
    orch.dispatch_user_input(
        session_id,
        "学习一下这个登录页怎么登录，地址是 http://localhost:5175/login，用户名 admin，密码 123456",
        metadata={"client": "wagent_chat"},
    )

    assert len(learn_calls) == 1
    assert learn_calls[0].get("headless") is True

    # replay
    replay_calls: list[dict[str, Any]] = []

    def replay_handler(lid: str, url: str, **kwargs: Any) -> ConversationReplaySummary:
        replay_calls.append(kwargs)
        return ConversationReplaySummary(
            learned_path_id=lid,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    # seed learned action for replay
    session = repo.get_session(session_id)
    assert session is not None
    path_id = _ingest_login_path(db_session, source_run_id="run-hl-2")
    repo.update_session_status(
        session_id=session_id,
        status="task_intake",
        metadata_patch={
            "learned_actions": [
                {
                    "alias": "登录",
                    "utterances": ["帮我登录"],
                    "learned_path_id": path_id,
                    "target_url": "http://localhost:5175/login",
                    "page_template": "/login",
                    "scenario": "valid_credentials",
                }
            ]
        },
    )

    orch2 = ConversationOrchestrator(repo, replay_handler=replay_handler)
    orch2.dispatch_user_input(
        session_id,
        "帮我登录",
        metadata={"client": "wagent_chat"},
    )

    assert len(replay_calls) == 1
    assert replay_calls[0].get("headless") is True


def test_missing_browser_visibility_defaults_to_visible(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    """API-4: missing browser_visibility defaults to visible for interactive chat."""
    session_id = _create_interactive_chat_session(repo)
    calls: list[dict[str, Any]] = []

    def learning_handler(url: str, raw_input: str, **kwargs: Any) -> LearningRunResult:
        calls.append(kwargs)
        learned_path_id = _ingest_login_path(db_session, source_run_id="run-def")
        return LearningRunResult(
            status="learned",
            run_id="run-def",
            learned_path_id=learned_path_id,
            target_url=url,
            page_template="/login",
            scenario="valid_credentials",
            action_label="登录",
            suggested_utterances=["帮我登录"],
        )

    orch = ConversationOrchestrator(repo, learning_handler=learning_handler)
    orch.dispatch_user_input(
        session_id,
        "学习一下这个登录页怎么登录，地址是 http://localhost:5175/login，用户名 admin，密码 123456",
        metadata={"client": "wagent_chat"},
    )

    assert len(calls) == 1
    assert calls[0].get("headless") is False


def test_missing_replay_handler_emits_execution_failed_event(
    db_session: Session,
    repo: ConversationRepository,
) -> None:
    """Missing replay handler must emit CHAT_EXECUTION_FAILED, not CHAT_EXECUTION_STARTED."""
    learned_path_id = _ingest_login_path(db_session)
    session_id = _create_interactive_chat_session(
        repo,
        metadata={
            "learned_actions": [
                {
                    "alias": "登录",
                    "utterances": ["帮我登录"],
                    "learned_path_id": learned_path_id,
                    "target_url": "http://localhost:5175/login",
                    "page_template": "/login",
                    "scenario": "valid_credentials",
                }
            ]
        },
    )

    orch = ConversationOrchestrator(repo, replay_handler=None)
    result = orch.dispatch_user_input(
        session_id,
        "帮我登录",
        metadata={"client": "wagent_chat"},
    )

    assert result.allowed is False
    assert "replay handler 未配置" in result.user_response

    events = repo.list_events(session_id)
    assert any(e.type == "chat_execution_failed" for e in events)
    assert not any(e.type == "chat_execution_started" for e in events)
