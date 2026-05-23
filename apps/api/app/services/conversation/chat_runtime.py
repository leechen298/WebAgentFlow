"""Interactive chat happy path for M11.3."""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlparse

from app.repos.conversation_repo import ConversationRepository
from app.repos.learned_paths_repo import LearnedPathRepository
from app.schemas.conversation import (
    ConversationCommandKind,
    ConversationEventType,
    ConversationReplaySummary,
    ConversationStatus,
)
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
)
from app.schemas.learned_path_replay import ExecutionEvidenceTarget
from app.schemas.task_planning import (
    AgentDPlannerOutput,
    LearnedPathCandidate,
    TaskIntent,
)
from app.services.conversation.context import (
    ConversationContextCollector,
    PendingTarget,
    make_pending_target,
)
from app.services.conversation.entry_gate import ConversationEntryGateService
from app.services.conversation.intake import (
    ConversationIntakeService,
    redact_sensitive_payload,
)
from app.services.conversation.orchestrator import DispatchResult
from app.services.conversation.page_understanding import PageUnderstandingService
from app.services.conversation.provenance import (
    AGENT_PRODUCER_CONVERSATION_INTAKE,
    AGENT_PRODUCER_CUSTOMER_FACING_ROUTER,
    CODE_PRODUCER_INTERACTIVE_CHAT,
    agent_response_provenance,
    code_response_provenance,
)
from app.services.conversation.router_agent import CustomerFacingAgentRouterService
from app.services.conversation.skills import ApplicationSkillRegistry
from app.services.conversation.trace_sanitizer import sanitize_provider_thinking
from app.services.learning.learning_run_service import LearningRunResult
from app.services.task_planning.planner import TaskPathPlanner

ChatIntentKind = Literal["learn_page", "execute_task", "unknown"]

_URL_RE = re.compile(r"https?://[^\s，。]+")
_LEARN_KEYWORDS = ("学习", "学一下", "learn", "teach")
_NO_PATH_RESPONSE = "还没学过这个操作，需要先学习。"
_UNLEARNED_TARGET_RESPONSE = "还没学过这个站点或页面，需要先学习。"
_AMBIGUOUS_TARGET_RESPONSE = "这个操作在多个站点学过，请带上要操作的页面地址。"
_VALUE_PATTERN = r"([^\s，。,.；;!！?？]+)"
_PENDING_SENSITIVE_VALUES: dict[str, dict[str, str]] = {}
_CHOICE_IDS = ("A", "B", "C", "D")
_RECOVERY_SIDE_EFFECT_CLASSES = {"evidence_missing", "needs_review", "uncertain"}
_LIVE_ACTIVE_TASK_STATUSES = {"waiting_for_user_input"}
_EVAL_FAILURE_RECOVERY_CASE_ID = "failure_recovery_menu_safety"
_EVAL_ALLOWED_REPORTER_OUTCOMES = {"needs_review"}
_EVAL_PENDING_CHOICE_CASE_ID = "pending_choice_multi_candidate"
_EVAL_CANDIDATE_SETUP_TYPES = {"eval_only_candidate_binding"}


def clear_pending_sensitive_values(session_id: str) -> None:
    _PENDING_SENSITIVE_VALUES.pop(session_id, None)


def clear_pending_runtime_context(repo: ConversationRepository, session_id: str) -> None:
    session = repo.get_session(session_id)
    if session is None:
        raise ValueError(f"session not found: {session_id}")
    metadata = dict(session.metadata_json or {})
    changed = False
    for key in (
        "pending_intake",
        "pending_target",
        "pending_choice",
        "pending_choice_private_map",
        "last_no_path_reason",
        "active_task",
    ):
        if key in metadata:
            metadata.pop(key, None)
            changed = True
    clear_pending_sensitive_values(session_id)
    if changed:
        session.metadata_json = metadata
        repo.session.commit()
        repo.session.refresh(session)


@dataclass(frozen=True)
class ChatIntent:
    kind: ChatIntentKind
    raw_text: str
    url: str | None = None


@dataclass(frozen=True)
class IntakeTraceContext:
    trace_ids: list[str]
    event_ids: list[str]
    fallback: bool = False
    event_types: list[str] | None = None


def _chat_headless(session: Any) -> bool:
    metadata = session.metadata_json or {}
    return metadata.get("browser_visibility") == "headless"


def _is_items_target(action: dict[str, Any]) -> bool:
    if action.get("page_template") == "/items":
        return True
    target_url = action.get("target_url") or ""
    return urlparse(target_url).path.rstrip("/") == "/items"


def _build_execution_evidence_targets(
    action: dict[str, Any],
    slot_overrides: dict[str, str],
) -> list[ExecutionEvidenceTarget]:
    item_name = slot_overrides.get("item_name")
    if not item_name or not _is_items_target(action):
        return []
    return [
        ExecutionEvidenceTarget(
            kind="dom_text_present",
            text=item_name,
            source_slot="item_name",
            selector="[data-testid='item-list']",
        )
    ]


def _execution_evidence_dicts(
    replay_summary: ConversationReplaySummary,
) -> list[dict[str, Any]]:
    return [
        item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item)
        for item in replay_summary.execution_evidence
        if item is not None
    ]


def _build_replay_reporter_context(
    *,
    action: dict[str, Any],
    slot_overrides: dict[str, str],
    replay_summary: ConversationReplaySummary,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    evidence = _execution_evidence_dicts(replay_summary)
    execution_payload = {
        "learned_path_id": replay_summary.learned_path_id,
        "target_url": action["target_url"],
        "alias": action.get("alias", ""),
        "slot_overrides": slot_overrides,
        "execution_evidence": evidence,
    }
    confirmed_plan_context = {
        "learned_path_id": replay_summary.learned_path_id,
        "target_url": action["target_url"],
        "slot_overrides": slot_overrides,
        "postcondition_evidence": evidence,
    }
    return "completed", execution_payload, confirmed_plan_context


def _chat_report_user_response(report: Any, slot_overrides: dict[str, str]) -> str:
    item_name = slot_overrides.get("item_name", "")
    if report.outcome == "verified" and item_name:
        return f"执行完成。我在列表中看到了“{item_name}”，所以可以确认新增项目成功。"
    if report.outcome == "uncertain" and item_name:
        return (
            "操作已经执行，但我还没有拿到足够页面证据确认结果。"
            f"建议你查看列表是否出现了“{item_name}”。"
        )
    if report.outcome == "needs_review" and item_name:
        return (
            f"操作执行后，我没有在列表中确认看到“{item_name}”。"
            "可能页面更新较慢，也可能操作没有成功。"
        )
    if report.outcome == "blocked":
        return (
            "我找到了已学习路径，但当前页面和学习时的页面不匹配，"
            "所以没有继续执行。请确认是否打开了正确的页面。"
        )
    if report.outcome == "failed":
        return "执行过程中遇到问题，这次没有完成新增项目。"
    return report.user_response


def _basic_failure_class(
    replay_summary: ConversationReplaySummary,
    report: Any | None,
) -> str | None:
    drift_status = replay_summary.drift_status or "none"
    if drift_status != "none":
        return "blocked"
    if replay_summary.replay_status not in {"succeeded", "observed"}:
        return "replay_failed"
    if report is None:
        return None
    if report.outcome == "verified":
        return None
    if report.outcome == "blocked":
        return "blocked"
    if report.outcome == "failed":
        return "replay_failed"
    if report.outcome == "needs_review":
        return "needs_review"
    if report.outcome == "uncertain":
        return "evidence_missing" if not _execution_evidence_dicts(replay_summary) else "uncertain"
    return "uncertain"


def _eval_fault_reporter_outcome(
    *,
    session_metadata: dict[str, Any],
    dispatch_metadata: dict[str, Any] | None,
) -> str | None:
    metadata = dispatch_metadata or {}
    client = metadata.get("client") or session_metadata.get("client")
    injection = metadata.get("eval_fault_injection")
    if injection is None:
        injection = session_metadata.get("eval_fault_injection")
    if client != "wagent_eval" or not isinstance(injection, dict):
        return None
    if injection.get("case_id") != _EVAL_FAILURE_RECOVERY_CASE_ID:
        return None
    outcome = injection.get("reporter_outcome")
    if outcome not in _EVAL_ALLOWED_REPORTER_OUTCOMES:
        return None
    return str(outcome)


def _with_eval_fault_report(report: Any, outcome: str) -> Any:
    event_payload = dict(report.event_payload)
    event_payload.update(
        {
            "verification_outcome": outcome,
            "task_verified": False,
            "needs_review": True,
            "eval_fault_injection": {
                "case_id": _EVAL_FAILURE_RECOVERY_CASE_ID,
                "fault_class": outcome,
            },
        }
    )
    return replace(
        report,
        outcome=outcome,
        needs_review=True,
        missing_evidence_summary="eval fault injection forced needs_review",
        event_payload=event_payload,
    )


def _recovery_failure_message(
    *,
    failure_class: str,
    report: Any | None,
    slot_overrides: dict[str, str],
) -> str:
    item_name = slot_overrides.get("item_name", "")
    if failure_class == "replay_failed":
        return "执行失败：这次操作没有完成。"
    if failure_class == "blocked":
        return "我找到了已学习路径，但当前页面和学习时的页面不匹配，所以没有继续确认执行结果。"
    if failure_class == "evidence_missing":
        if item_name:
            return (
                "操作已经执行，但我还没有拿到足够页面证据确认结果。"
                f"我没有在列表中确认看到“{item_name}”。"
            )
        return "操作已经执行，但我还没有拿到足够页面证据确认结果。"
    if report is not None:
        return _chat_report_user_response(report, slot_overrides)
    return "操作结果不确定，我还不能确认目标是否完成。"


def parse_chat_intent(raw_input: str) -> ChatIntent:
    text = raw_input.strip()
    if not text:
        return ChatIntent(kind="unknown", raw_text=raw_input)
    url = _extract_url(text)
    lowered = text.lower()
    if url and any(keyword in lowered or keyword in text for keyword in _LEARN_KEYWORDS):
        return ChatIntent(kind="learn_page", raw_text=raw_input, url=url)
    return ChatIntent(kind="execute_task", raw_text=raw_input)


def _entry_gate_user_response(category: ConversationEntryGateCategory) -> str:
    if category == ConversationEntryGateCategory.CAPABILITY_QUESTION:
        return (
            "我主要可以帮你学习网页操作、执行已经学会的网页操作，并查看会话历史。"
            "你可以发一个目标页面 URL，并说明想学习或执行什么。"
        )
    if category == ConversationEntryGateCategory.UNSUPPORTED:
        return (
            "这个请求不属于当前网页操作范围。你可以提供目标网页 URL，并说明要学习或执行的页面操作。"
        )
    if category == ConversationEntryGateCategory.NEEDS_CLARIFICATION:
        return "我还需要确认这是不是网页操作任务。请提供目标页面 URL，或说明要学习/执行的网页操作。"
    return (
        "你好，我主要处理网页操作任务。你可以发给我目标页面 URL，"
        "并说明要学习哪个操作，或让我执行已经学会的操作。"
    )


class InteractiveChatRuntime:
    def __init__(
        self,
        repo: ConversationRepository,
        *,
        learning_handler: Any | None = None,
        replay_handler: Any | None = None,
        intake_service: Any | None = None,
        entry_gate_service: Any | None = None,
        router_service: Any | None = None,
        skill_registry: ApplicationSkillRegistry | None = None,
        page_context_provider: Any | None = None,
        page_understanding_service: Any | None = None,
    ) -> None:
        self._repo = repo
        self._learning_handler = learning_handler
        self._replay_handler = replay_handler
        self._entry_gate_service = entry_gate_service or ConversationEntryGateService()
        self._intake_service = intake_service or ConversationIntakeService()
        self._router_service = router_service or CustomerFacingAgentRouterService()
        self._skill_registry = skill_registry or ApplicationSkillRegistry()
        self._page_context_provider = page_context_provider
        self._page_understanding_service = page_understanding_service or PageUnderstandingService()

    def try_handle(
        self,
        *,
        session: Any,
        session_id: str,
        raw_input: str,
        command: Any,
        message_id: str | None,
        metadata: dict[str, Any] | None,
    ) -> DispatchResult | None:
        if session.current_mode != "interactive_chat":
            return None
        if command.kind != ConversationCommandKind.FREE_TEXT:
            return None

        previous_status = str(session.status or ConversationStatus.IDLE.value)
        headless = _chat_headless(session)
        entry_gate = self._entry_gate_service.evaluate(
            raw_input,
            session_metadata=session.metadata_json or {},
            session_mode=session.current_mode,
        )
        entry_gate_context = self._record_entry_gate_trace(
            session_id,
            entry_gate=entry_gate,
            skipped_intake_router=not entry_gate.requires_agent_runtime,
        )
        if not entry_gate.requires_agent_runtime:
            return self._handle_entry_gate_reply(
                session_id=session_id,
                raw_input=raw_input,
                entry_gate=entry_gate,
                entry_gate_context=entry_gate_context,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
            )
        pending_choice_result = self._maybe_handle_pending_choice(
            session_id=session_id,
            raw_input=raw_input,
            message_id=message_id,
            metadata=metadata,
            previous_status=previous_status,
            headless=headless,
        )
        if pending_choice_result is not None:
            return pending_choice_result
        if _is_cancel_text(raw_input) and self._has_pending_runtime_context(session_id):
            return self._handle_runtime_cancel(
                session_id=session_id,
                raw_input=raw_input,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
            )
        intake = self._intake_service.analyze(
            raw_input,
            session_metadata=session.metadata_json or {},
        )
        trace_context = self._record_intake_trace(
            session_id,
            fallback=bool(getattr(self._intake_service, "provider_fallback", False)),
        )
        context = ConversationContextCollector(self._repo).collect(
            session_id,
            current_message=raw_input,
        )
        self._record_skill_call(
            session_id,
            ApplicationSkillName.COLLECT_CONVERSATION_CONTEXT,
            status="completed",
            input_summary={"current_message_url": context.current_message_url},
            output_summary={
                "pending_target": (
                    context.pending_target.model_dump(mode="json")
                    if context.pending_target
                    else None
                ),
                "pending_choice": (
                    context.pending_choice.model_dump(mode="json")
                    if context.pending_choice
                    else None
                ),
                "active_task": (
                    context.active_task.model_dump(mode="json") if context.active_task else None
                ),
                "learned_action_count": len(context.learned_actions),
            },
        )
        route_decision = self._router_service.route(
            raw_message=raw_input,
            intake=intake,
            context=context,
        )
        router_llm_trace_context = self._record_router_llm_trace(session_id)
        router_trace_context = self._record_router_trace(
            session_id,
            route_decision=route_decision,
            llm_trace_context=router_llm_trace_context,
        )
        if _is_bare_url_input(
            raw_input,
            intake.target.url or route_decision.target.url or context.current_message_url,
        ):
            return self._handle_pending_target_question(
                session_id=session_id,
                raw_input=raw_input,
                intake=intake,
                route_decision=route_decision,
                trace_context=trace_context,
                router_trace_context=router_trace_context,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
            )
        if (
            intake.intent == "learn_operation"
            and intake.confidence >= self._intake_confidence_threshold()
        ):
            if intake.should_ask_user or intake.missing_fields:
                return self._handle_pending_intake_question(
                    session_id=session_id,
                    intake=intake,
                    trace_context=trace_context,
                    message_id=message_id,
                    metadata=metadata,
                    previous_status=previous_status,
                )
            return self._handle_learn_page(
                session_id=session_id,
                intent=_chat_intent_from_intake(raw_input, intake),
                intake=intake,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
                headless=headless,
                route_decision=route_decision,
            )
        if (
            intake.intent == "execute_operation"
            and intake.confidence >= self._intake_confidence_threshold()
            and context.learned_actions
            and any(slot.value for slot in intake.slots)
        ):
            return self._handle_execute_task(
                session_id=session_id,
                intent=_chat_intent_from_intake(raw_input, intake),
                intake=intake,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
                headless=headless,
                route_decision=route_decision,
            )
        if route_decision.route_decision in {
            RouteDecisionKind.INSPECT_PAGE,
            RouteDecisionKind.UNDERSTAND_PAGE,
        }:
            return self._handle_page_understanding_request(
                session_id=session_id,
                raw_input=raw_input,
                intake=intake,
                route_decision=route_decision,
                trace_context=trace_context,
                router_trace_context=router_trace_context,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
                headless=headless,
            )
        if (
            route_decision.route_decision == RouteDecisionKind.ASK_USER
            and route_decision.target.url
            and any(
                field.semantic_type == "operation_goal" for field in route_decision.missing_fields
            )
        ):
            return self._handle_pending_target_question(
                session_id=session_id,
                raw_input=raw_input,
                intake=intake,
                route_decision=route_decision,
                trace_context=trace_context,
                router_trace_context=router_trace_context,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
            )
        if intake.confidence < self._intake_confidence_threshold():
            return self._handle_low_confidence_intake(
                session_id=session_id,
                intake=intake,
                trace_context=trace_context,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
            )
        if intake.intent == "learn_operation":
            if intake.should_ask_user or intake.missing_fields:
                return self._handle_pending_intake_question(
                    session_id=session_id,
                    intake=intake,
                    trace_context=trace_context,
                    message_id=message_id,
                    metadata=metadata,
                    previous_status=previous_status,
                )
            return self._handle_learn_page(
                session_id=session_id,
                intent=_chat_intent_from_intake(raw_input, intake),
                intake=intake,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
                headless=headless,
                route_decision=route_decision,
            )
        if intake.intent == "provide_missing_info":
            return self._handle_provide_missing_info(
                session_id=session_id,
                raw_input=raw_input,
                intake=intake,
                trace_context=trace_context,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
                headless=headless,
                route_decision=route_decision,
            )
        if intake.intent == "execute_operation":
            return self._handle_execute_task(
                session_id=session_id,
                intent=_chat_intent_from_intake(raw_input, intake),
                intake=intake,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
                headless=headless,
                route_decision=route_decision,
            )
        return self._handle_no_path(
            session_id=session_id,
            command_kind="unknown",
            message_id=message_id,
            metadata=metadata,
            previous_status=previous_status,
        )

    def _intake_confidence_threshold(self) -> float:
        return float(getattr(self._intake_service, "confidence_threshold", 0.6))

    def _maybe_handle_pending_choice(
        self,
        *,
        session_id: str,
        raw_input: str,
        message_id: str | None,
        metadata: dict[str, Any] | None,
        previous_status: str,
        headless: bool,
    ) -> DispatchResult | None:
        pending = self._pending_choice(session_id)
        if pending is None:
            return None
        if _is_cancel_text(raw_input):
            return self._handle_runtime_cancel(
                session_id=session_id,
                raw_input=raw_input,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
            )
        choice_id = _parse_choice_reply(raw_input, pending)
        if choice_id:
            return self._handle_pending_choice_selection(
                session_id=session_id,
                raw_input=raw_input,
                choice_id=choice_id,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
                headless=headless,
            )
        if _looks_like_choice_revision(raw_input):
            self._clear_pending_choice(session_id)
            self._clear_active_task(session_id)
            return None
        return self._handle_pending_choice_miss(
            session_id=session_id,
            raw_input=raw_input,
            pending=pending,
            message_id=message_id,
            metadata=metadata,
            previous_status=previous_status,
        )

    def _handle_pending_choice_selection(
        self,
        *,
        session_id: str,
        raw_input: str,
        choice_id: str,
        message_id: str | None,
        metadata: dict[str, Any] | None,
        previous_status: str,
        headless: bool,
    ) -> DispatchResult:
        events = self._append_chat_command_event(
            session_id=session_id,
            raw_input=raw_input,
            command_kind="pending_choice_select",
            metadata=metadata,
        )
        private_map = self._pending_choice_private_map(session_id)
        selected = private_map.get(choice_id)
        self._clear_pending_choice(session_id)
        if not isinstance(selected, dict):
            return self._handle_choice_unavailable(
                session_id=session_id,
                reason="pending_choice_private_map_missing",
                events=events,
                message_id=message_id,
                previous_status=previous_status,
            )
        if selected.get("kind") == "cancel":
            self._append_event(
                session_id,
                ConversationEventType.CHAT_PROGRESS_RECORDED,
                {
                    "progress_kind": "failure_recovery_selected",
                    "selected_choice_id": choice_id,
                    "recovery_kind": "cancel",
                    "failure_class": selected.get("failure_reason"),
                },
                events,
            )
            self._append_event(
                session_id,
                ConversationEventType.CHAT_PROGRESS_RECORDED,
                {
                    "progress_kind": "failure_recovery_cancelled",
                    "recovery_kind": "cancel",
                    "failure_class": selected.get("failure_reason"),
                },
                events,
            )
            return self._handle_runtime_cancel(
                session_id=session_id,
                raw_input=raw_input,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
                existing_events=events,
            )
        if selected.get("kind") == "retry_replay":
            return self._handle_recovery_retry_selection(
                session_id=session_id,
                selected=selected,
                events=events,
                message_id=message_id,
                previous_status=previous_status,
                headless=headless,
            )
        if selected.get("kind") == "relearn_operation":
            return self._handle_recovery_relearn_selection(
                session_id=session_id,
                selected=selected,
                events=events,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
                headless=headless,
            )
        selected_kind = selected.get("kind")
        if selected_kind == "planner_route_choice":
            planner_summary = selected.get("planner_summary")
            self._append_event(
                session_id,
                ConversationEventType.CHAT_PROGRESS_RECORDED,
                {
                    "progress_kind": "planner_choice_selected",
                    "selected_choice_id": choice_id,
                    "planner_warning_count": _count_summary_items(planner_summary, "warnings"),
                    "planner_risk_count": _count_summary_items(planner_summary, "risk_hints"),
                    "confirmation_required": (
                        bool(planner_summary.get("confirmation_required"))
                        if isinstance(planner_summary, dict)
                        else False
                    ),
                },
                events,
            )
        elif selected_kind != "learned_action":
            return self._handle_choice_unavailable(
                session_id=session_id,
                reason="pending_choice_kind_unsupported",
                events=events,
                message_id=message_id,
                previous_status=previous_status,
            )
        action = self._learned_action_by_path_id(
            session_id,
            str(selected.get("learned_path_id") or ""),
        )
        if action is None and selected_kind == "planner_route_choice":
            action = self._action_from_private_choice(selected)
        if action is None:
            return self._handle_choice_unavailable(
                session_id=session_id,
                reason="pending_choice_learned_action_unavailable",
                events=events,
                message_id=message_id,
                previous_status=previous_status,
            )
        return self._execute_matched_action(
            session_id=session_id,
            action=action,
            intake=None,
            slot_overrides_override=_slot_overrides_from_choice_selection(selected),
            events=events,
            message_id=message_id,
            previous_status=previous_status,
            headless=headless,
            command_kind="execute_task",
        )

    def _handle_recovery_relearn_selection(
        self,
        *,
        session_id: str,
        selected: dict[str, Any],
        events: list[str],
        message_id: str | None,
        metadata: dict[str, Any] | None,
        previous_status: str,
        headless: bool,
    ) -> DispatchResult:
        target_url = str(selected.get("target_url") or "").strip()
        action_alias = str(selected.get("action_alias") or "").strip()
        failure_class = selected.get("failure_reason")
        self._append_event(
            session_id,
            ConversationEventType.CHAT_PROGRESS_RECORDED,
            {
                "progress_kind": "failure_recovery_selected",
                "selected_choice_id": "B",
                "recovery_kind": "relearn_operation",
                "failure_class": failure_class,
                "action_alias": action_alias or None,
            },
            events,
        )
        self._append_event(
            session_id,
            ConversationEventType.CHAT_PROGRESS_RECORDED,
            {
                "progress_kind": "failure_recovery_relearn_started",
                "recovery_kind": "relearn_operation",
                "failure_class": failure_class,
                "action_alias": action_alias or None,
            },
            events,
        )
        if not target_url or not action_alias:
            if target_url:
                self._save_pending_target(session_id, make_pending_target(target_url))
            self._set_active_task(
                session_id,
                kind="clarify",
                owner="runtime",
                status="waiting_for_user_input",
                target_url=target_url or None,
                goal=action_alias or None,
            )
            response = "我还需要确认要重新学习的页面和操作。"
            self._append_agent_message(session_id, response)
            self._append_event(
                session_id,
                ConversationEventType.CHAT_NO_PATH,
                {"reason": "failure_recovery_relearn_missing_info"},
                events,
            )
            return self._result(
                session_id=session_id,
                command_kind="learn_page",
                user_response=response,
                events=events,
                message_id=message_id,
                previous_status=previous_status,
            )

        fill_values = _fill_values_from_recovery_choice(selected)
        intake = ConversationIntakeResult(
            intent="learn_operation",
            target=ConversationIntakeTarget(url=target_url),
            action=ConversationIntakeAction(
                goal=action_alias,
                canonical_goal=action_alias,
                aliases=[action_alias],
            ),
            slots=[
                ConversationIntakeSlot(
                    name=key,
                    semantic_type=key,
                    value=value,
                )
                for key, value in fill_values.items()
            ],
            confidence=1.0,
        )
        return self._handle_learn_page(
            session_id=session_id,
            intent=ChatIntent(
                kind="learn_page",
                raw_text=f"重新学习{action_alias}",
                url=target_url,
            ),
            intake=intake,
            message_id=message_id,
            metadata=metadata,
            previous_status=previous_status,
            headless=headless,
        )

    def _handle_recovery_retry_selection(
        self,
        *,
        session_id: str,
        selected: dict[str, Any],
        events: list[str],
        message_id: str | None,
        previous_status: str,
        headless: bool,
    ) -> DispatchResult:
        action = self._learned_action_by_path_id(
            session_id,
            str(selected.get("learned_path_id") or ""),
        )
        if action is None:
            return self._handle_choice_unavailable(
                session_id=session_id,
                reason="failure_recovery_retry_unavailable",
                events=events,
                message_id=message_id,
                previous_status=previous_status,
            )
        retry_count = int(selected.get("retry_count") or 0) + 1
        self._append_event(
            session_id,
            ConversationEventType.CHAT_PROGRESS_RECORDED,
            {
                "progress_kind": "failure_recovery_selected",
                "selected_choice_id": "A",
                "recovery_kind": "retry_replay",
                "failure_class": selected.get("failure_reason"),
                "retry_count": retry_count,
                "action_alias": action.get("alias"),
            },
            events,
        )
        self._append_event(
            session_id,
            ConversationEventType.CHAT_PROGRESS_RECORDED,
            {
                "progress_kind": "failure_recovery_retry_started",
                "recovery_kind": "retry_replay",
                "failure_class": selected.get("failure_reason"),
                "retry_count": retry_count,
                "action_alias": action.get("alias"),
            },
            events,
        )
        return self._execute_matched_action(
            session_id=session_id,
            action=action,
            intake=None,
            slot_overrides_override=_slot_overrides_from_choice_selection(selected),
            events=events,
            message_id=message_id,
            previous_status=previous_status,
            headless=headless,
            command_kind="execute_task",
            retry_count_override=retry_count,
        )

    def _handle_pending_choice_miss(
        self,
        *,
        session_id: str,
        raw_input: str,
        pending: dict[str, Any],
        message_id: str | None,
        metadata: dict[str, Any] | None,
        previous_status: str,
    ) -> DispatchResult:
        events = self._append_chat_command_event(
            session_id=session_id,
            raw_input=raw_input,
            command_kind="pending_choice_clarify",
            metadata=metadata,
        )
        remaining = int(pending.get("turns_remaining") or 0) - 1
        if remaining <= 0:
            self._clear_pending_choice(session_id)
            self._clear_active_task(session_id)
            response = "选择已过期，请重新说明你想让我执行哪个网页操作。"
            self._append_agent_message(session_id, response)
            self._append_event(
                session_id,
                ConversationEventType.CHAT_NO_PATH,
                {"reason": "pending_choice_expired"},
                events,
            )
            return self._result(
                session_id=session_id,
                command_kind="pending_choice_clarify",
                user_response=response,
                events=events,
                message_id=message_id,
                previous_status=previous_status,
            )
        pending = {**pending, "turns_remaining": remaining}
        slot_overrides = _slot_overrides_from_pending_choice_clarification(raw_input)
        if slot_overrides:
            self._merge_pending_choice_private_slot_overrides(
                session_id,
                slot_overrides,
            )
        self._save_pending_choice_payload(session_id, pending)
        self._update_active_task(session_id, status="waiting_for_user_input")
        response = _pending_choice_response(pending, prefix="我没有识别出你的选择。")
        self._append_agent_message(session_id, response)
        self._append_event(
            session_id,
            ConversationEventType.CHAT_PROGRESS_RECORDED,
            {
                "progress_kind": "pending_choice_retry",
                "pending_choice": pending,
            },
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind="pending_choice_clarify",
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _merge_pending_choice_private_slot_overrides(
        self,
        session_id: str,
        slot_overrides: dict[str, str],
    ) -> None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        metadata = dict(session.metadata_json or {})
        private_map = metadata.get("pending_choice_private_map")
        if not isinstance(private_map, dict):
            return
        changed = False
        merged_map: dict[str, Any] = {}
        for choice_id, raw_choice in private_map.items():
            if not isinstance(raw_choice, dict):
                continue
            choice = dict(raw_choice)
            if choice.get("kind") not in {
                "learned_action",
                "planner_route_choice",
                "retry_replay",
            }:
                merged_map[str(choice_id)] = choice
                continue
            existing = choice.get("slot_overrides")
            merged_slots = dict(existing) if isinstance(existing, dict) else {}
            for key, value in slot_overrides.items():
                if key and value is not None:
                    merged_slots[str(key)] = str(value)
            if merged_slots:
                choice["slot_overrides"] = merged_slots
                changed = True
            merged_map[str(choice_id)] = choice
        if not changed:
            return
        metadata["pending_choice_private_map"] = redact_sensitive_payload(merged_map)
        self._replace_session_metadata(session_id, metadata)

    def _handle_choice_unavailable(
        self,
        *,
        session_id: str,
        reason: str,
        events: list[str],
        message_id: str | None,
        previous_status: str,
    ) -> DispatchResult:
        self._clear_active_task(session_id)
        response = "这个选择已经不可用，请重新说明你想让我执行哪个操作。"
        self._append_agent_message(session_id, response)
        self._append_event(
            session_id,
            ConversationEventType.CHAT_NO_PATH,
            {"reason": reason},
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind="pending_choice_select",
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _handle_runtime_cancel(
        self,
        *,
        session_id: str,
        raw_input: str,
        message_id: str | None,
        metadata: dict[str, Any] | None,
        previous_status: str,
        existing_events: list[str] | None = None,
    ) -> DispatchResult:
        events = existing_events or self._append_chat_command_event(
            session_id=session_id,
            raw_input=raw_input,
            command_kind="cancel",
            metadata=metadata,
        )
        self._mark_active_task_cancelled(session_id)
        clear_pending_runtime_context(self._repo, session_id)
        response = "已取消当前任务。"
        self._append_agent_message(
            session_id,
            response,
            provenance=code_response_provenance(CODE_PRODUCER_INTERACTIVE_CHAT),
        )
        self._append_event(
            session_id,
            ConversationEventType.CHAT_PROGRESS_RECORDED,
            {"progress_kind": "runtime_context_cancelled"},
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind="cancel",
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _handle_entry_gate_reply(
        self,
        *,
        session_id: str,
        raw_input: str,
        entry_gate: ConversationEntryGateResult,
        entry_gate_context: IntakeTraceContext,
        message_id: str | None,
        metadata: dict[str, Any] | None,
        previous_status: str,
    ) -> DispatchResult:
        command_kind = entry_gate.category.value
        events = self._trace_event_types(entry_gate_context) + self._append_chat_command_event(
            session_id=session_id,
            raw_input=raw_input,
            command_kind=command_kind,
            metadata=metadata,
        )
        response = _entry_gate_user_response(entry_gate.category)
        self._append_agent_message(
            session_id,
            response,
            provenance=code_response_provenance(
                CODE_PRODUCER_INTERACTIVE_CHAT,
                generated_from_event_ids=entry_gate_context.event_ids,
                fallback=entry_gate.fallback,
            ),
        )
        self._append_event(
            session_id,
            ConversationEventType.CHAT_NO_PATH,
            {
                "reason": "entry_gate_skipped_runtime",
                "category": entry_gate.category.value,
                "error_kind": entry_gate.error_kind,
            },
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind=command_kind,
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _handle_low_confidence_intake(
        self,
        *,
        session_id: str,
        intake: ConversationIntakeResult,
        trace_context: IntakeTraceContext,
        message_id: str | None,
        metadata: dict[str, Any] | None,
        previous_status: str,
    ) -> DispatchResult:
        events = self._trace_event_types(trace_context) + self._append_chat_command_event(
            session_id=session_id,
            raw_input="",
            command_kind="unknown",
            metadata=metadata,
            intake=intake,
        )
        response = intake.ask_user_message_hint or "我还需要再确认一下你的意思。"
        self._append_agent_message(
            session_id,
            response,
            provenance=self._intake_reply_provenance(intake, trace_context),
        )
        self._append_event(
            session_id,
            ConversationEventType.CHAT_NO_PATH,
            {"reason": "low_confidence_intake"},
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind="unknown",
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _handle_pending_intake_question(
        self,
        *,
        session_id: str,
        intake: ConversationIntakeResult,
        trace_context: IntakeTraceContext | None = None,
        message_id: str | None,
        metadata: dict[str, Any] | None,
        previous_status: str,
        turns_remaining: int | None = None,
    ) -> DispatchResult:
        trace_context = trace_context or IntakeTraceContext([], [])
        events = self._trace_event_types(trace_context) + self._append_chat_command_event(
            session_id=session_id,
            raw_input="",
            command_kind="learn_page",
            metadata=metadata,
            intake=intake,
        )
        self._save_pending_intake(
            session_id,
            intake,
            message_id,
            turns_remaining=turns_remaining,
        )
        self._set_active_task(
            session_id,
            kind="clarify",
            owner="runtime",
            status="waiting_for_user_input",
            target_url=intake.target.url,
            goal=intake.action.goal,
        )
        response = _question_for_missing_fields(intake)
        self._append_agent_message(
            session_id,
            response,
            provenance=self._intake_reply_provenance(intake, trace_context),
        )
        self._append_event(
            session_id,
            ConversationEventType.CHAT_NO_PATH,
            {"reason": "pending_intake_missing_fields"},
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind="learn_page",
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _handle_pending_target_question(
        self,
        *,
        session_id: str,
        raw_input: str,
        intake: ConversationIntakeResult,
        route_decision: RouteDecision,
        trace_context: IntakeTraceContext,
        router_trace_context: IntakeTraceContext,
        message_id: str | None,
        metadata: dict[str, Any] | None,
        previous_status: str,
    ) -> DispatchResult:
        events = (
            self._trace_event_types(trace_context)
            + self._trace_event_types(router_trace_context)
            + self._append_chat_command_event(
                session_id=session_id,
                raw_input=raw_input,
                command_kind="ask_user",
                metadata=metadata,
                intake=intake,
            )
        )
        target = make_pending_target(route_decision.target.url or raw_input)
        self._save_pending_target(session_id, target)
        self._set_active_task(
            session_id,
            kind="clarify",
            owner="runtime",
            status="waiting_for_user_input",
            target_url=target.url,
            goal=route_decision.user_goal,
        )
        self._record_skill_call(
            session_id,
            ApplicationSkillName.ASK_USER_FOR_MISSING_INFO,
            status="completed",
            input_summary={"missing_fields": ["operation_goal"]},
            output_summary={"target_url": target.url},
        )
        response = "我已经记住这个页面地址。你想让我学习或执行哪个操作？"
        self._append_agent_message(
            session_id,
            response,
            provenance=code_response_provenance(
                CODE_PRODUCER_INTERACTIVE_CHAT,
                llm_trace_ids=router_trace_context.trace_ids,
                generated_from_event_ids=router_trace_context.event_ids,
            ),
        )
        self._append_event(
            session_id,
            ConversationEventType.CHAT_NO_PATH,
            {
                "reason": "pending_target_missing_goal",
                "target": target.model_dump(mode="json"),
                "route_decision": route_decision.model_dump(mode="json"),
            },
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind="ask_user",
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _handle_page_understanding_request(
        self,
        *,
        session_id: str,
        raw_input: str,
        intake: ConversationIntakeResult,
        route_decision: RouteDecision,
        trace_context: IntakeTraceContext,
        router_trace_context: IntakeTraceContext,
        message_id: str | None,
        metadata: dict[str, Any] | None,
        previous_status: str,
        headless: bool,
    ) -> DispatchResult:
        events = (
            self._trace_event_types(trace_context)
            + self._trace_event_types(router_trace_context)
            + self._append_chat_command_event(
                session_id=session_id,
                raw_input=raw_input,
                command_kind=route_decision.route_decision.value,
                metadata=metadata,
                intake=intake,
            )
        )
        target_url = route_decision.target.url or intake.target.url
        provider = self._page_context_provider
        if not target_url or not callable(provider):
            self._record_skill_call(
                session_id,
                ApplicationSkillName.INSPECT_TARGET_PAGE,
                status="blocked",
                input_summary=route_decision.model_dump(mode="json"),
                output_summary={"reason": "page_context_unavailable"},
            )
            response = "我还不能确认这个页面的实时结构。请补充你想学习或执行的操作。"
            self._append_agent_message(
                session_id,
                response,
                provenance=code_response_provenance(
                    CODE_PRODUCER_INTERACTIVE_CHAT,
                    llm_trace_ids=router_trace_context.trace_ids,
                    generated_from_event_ids=router_trace_context.event_ids,
                ),
            )
            self._append_event(
                session_id,
                ConversationEventType.CHAT_NO_PATH,
                {
                    "reason": "page_context_unavailable",
                    "route_decision": route_decision.model_dump(mode="json"),
                },
                events,
            )
            return self._result(
                session_id=session_id,
                command_kind=route_decision.route_decision.value,
                user_response=response,
                events=events,
                message_id=message_id,
                previous_status=previous_status,
            )

        try:
            page_context = provider(
                route_decision=route_decision,
                intake=intake,
                headless=headless,
            )
        except Exception:
            page_context = None
        if page_context is None:
            self._record_skill_call(
                session_id,
                ApplicationSkillName.INSPECT_TARGET_PAGE,
                status="blocked",
                input_summary={"target_url": target_url, "headless": headless},
                output_summary={"reason": "page_context_provider_failed"},
            )
            response = "我还不能确认这个页面的实时结构。请补充你想学习或执行的操作。"
            self._append_agent_message(
                session_id,
                response,
                provenance=code_response_provenance(
                    CODE_PRODUCER_INTERACTIVE_CHAT,
                    llm_trace_ids=router_trace_context.trace_ids,
                    generated_from_event_ids=router_trace_context.event_ids,
                ),
            )
            self._append_event(
                session_id,
                ConversationEventType.CHAT_NO_PATH,
                {"reason": "page_context_provider_failed"},
                events,
            )
            return self._result(
                session_id=session_id,
                command_kind=route_decision.route_decision.value,
                user_response=response,
                events=events,
                message_id=message_id,
                previous_status=previous_status,
            )
        self._record_skill_call(
            session_id,
            ApplicationSkillName.INSPECT_TARGET_PAGE,
            status="completed",
            input_summary={"target_url": target_url, "headless": headless},
            output_summary={
                "url": page_context.url,
                "title": page_context.title,
                "interactive_element_count": len(page_context.interactive_elements),
            },
        )
        page_understanding = self._page_understanding_service.understand(page_context)
        self._record_skill_call(
            session_id,
            ApplicationSkillName.UNDERSTAND_PAGE,
            status="completed",
            input_summary={"url": page_context.url},
            output_summary=page_understanding.model_dump(mode="json"),
        )
        page_trace_context = self._record_page_understanding_trace(
            session_id,
            page_understanding=page_understanding.model_dump(mode="json"),
            router_trace_context=router_trace_context,
        )
        events += self._trace_event_types(page_trace_context)
        self._save_pending_target(
            session_id,
            make_pending_target(page_context.url or target_url),
        )
        self._set_active_task(
            session_id,
            kind="clarify",
            owner="page_understanding",
            status="waiting_for_user_input",
            target_url=page_context.url or target_url,
            goal=route_decision.user_goal,
        )
        response = (
            f"我已查看页面：{page_understanding.observed_page_summary} 你想让我学习或执行哪个操作？"
        )
        self._append_agent_message(
            session_id,
            response,
            provenance=code_response_provenance(
                CODE_PRODUCER_INTERACTIVE_CHAT,
                llm_trace_ids=router_trace_context.trace_ids,
                generated_from_event_ids=[
                    *router_trace_context.event_ids,
                    *page_trace_context.event_ids,
                ],
            ),
        )
        self._append_event(
            session_id,
            ConversationEventType.CHAT_PROGRESS_RECORDED,
            {
                "progress_kind": "page_understanding_recorded",
                "route_decision": route_decision.model_dump(mode="json"),
                "page_context": {
                    "url": page_context.url,
                    "title": page_context.title,
                    "interactive_element_count": len(page_context.interactive_elements),
                    "page_signature": page_context.page_signature,
                },
                "page_understanding": page_understanding.model_dump(mode="json"),
            },
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind=route_decision.route_decision.value,
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _handle_provide_missing_info(
        self,
        *,
        session_id: str,
        raw_input: str,
        intake: ConversationIntakeResult,
        trace_context: IntakeTraceContext,
        message_id: str | None,
        metadata: dict[str, Any] | None,
        previous_status: str,
        headless: bool,
        route_decision: RouteDecision | None = None,
    ) -> DispatchResult:
        pending = self._pending_intake(session_id)
        if pending is None:
            return self._handle_missing_info_without_pending(
                session_id=session_id,
                intake=intake,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
            )

        pending_url = ((pending.get("target") or {}).get("url")) or None
        intake_url = intake.target.url
        if intake_url and pending_url and _normalize_url(intake_url) != _normalize_url(pending_url):
            return self._handle_pending_target_changed(
                session_id=session_id,
                intake=intake,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
            )

        merged = _merge_pending_intake(session_id, pending, intake)
        if merged.missing_fields:
            turns_remaining = int(pending.get("turns_remaining") or 3) - 1
            if turns_remaining <= 0:
                return self._handle_pending_intake_expired(
                    session_id=session_id,
                    intake=merged,
                    message_id=message_id,
                    metadata=metadata,
                    previous_status=previous_status,
                )
            return self._handle_pending_intake_question(
                session_id=session_id,
                intake=merged,
                trace_context=trace_context,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
                turns_remaining=turns_remaining,
            )

        return self._handle_learn_page(
            session_id=session_id,
            intent=_chat_intent_from_intake(raw_input, merged),
            intake=merged,
            message_id=message_id,
            metadata=metadata,
            previous_status=previous_status,
            headless=headless,
            route_decision=route_decision,
        )

    def _handle_missing_info_without_pending(
        self,
        *,
        session_id: str,
        intake: ConversationIntakeResult,
        message_id: str | None,
        metadata: dict[str, Any] | None,
        previous_status: str,
    ) -> DispatchResult:
        events = self._append_chat_command_event(
            session_id=session_id,
            raw_input="",
            command_kind="provide_missing_info",
            metadata=metadata,
            intake=intake,
        )
        response = "请先说明要学习或执行什么操作。"
        self._append_agent_message(session_id, response)
        self._append_event(
            session_id,
            ConversationEventType.CHAT_NO_PATH,
            {"reason": "missing_info_without_pending_intake"},
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind="provide_missing_info",
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _handle_pending_target_changed(
        self,
        *,
        session_id: str,
        intake: ConversationIntakeResult,
        message_id: str | None,
        metadata: dict[str, Any] | None,
        previous_status: str,
    ) -> DispatchResult:
        events = self._append_chat_command_event(
            session_id=session_id,
            raw_input="",
            command_kind="provide_missing_info",
            metadata=metadata,
            intake=intake,
        )
        response = "页面地址变了，请重新说明要学习哪个页面和需要填写的信息。"
        self._append_agent_message(session_id, response)
        self._append_event(
            session_id,
            ConversationEventType.CHAT_NO_PATH,
            {"reason": "pending_intake_target_changed"},
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind="provide_missing_info",
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _handle_pending_intake_expired(
        self,
        *,
        session_id: str,
        intake: ConversationIntakeResult,
        message_id: str | None,
        metadata: dict[str, Any] | None,
        previous_status: str,
    ) -> DispatchResult:
        events = self._append_chat_command_event(
            session_id=session_id,
            raw_input="",
            command_kind="provide_missing_info",
            metadata=metadata,
            intake=intake,
        )
        self._clear_pending_intake(session_id)
        response = "补充信息超时，请重新说明要学习或执行什么操作。"
        self._append_agent_message(session_id, response)
        self._append_event(
            session_id,
            ConversationEventType.CHAT_NO_PATH,
            {"reason": "pending_intake_expired"},
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind="provide_missing_info",
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _handle_learn_page(
        self,
        *,
        session_id: str,
        intent: ChatIntent,
        intake: ConversationIntakeResult | None,
        message_id: str | None,
        metadata: dict[str, Any] | None,
        previous_status: str,
        headless: bool = True,
        route_decision: RouteDecision | None = None,
    ) -> DispatchResult:
        events = self._append_chat_command_event(
            session_id=session_id,
            raw_input=intent.raw_text,
            command_kind="learn_page",
            metadata=metadata,
            intake=intake,
        )
        self._set_active_task(
            session_id,
            kind="learn_operation",
            owner="learning_agent",
            status="learning",
            target_url=intent.url,
            goal=intake.action.goal if intake else intent.raw_text,
        )

        self._append_agent_message(session_id, "开始学习页面操作。")
        self._record_skill_call(
            session_id,
            ApplicationSkillName.START_LEARNING,
            status="started",
            input_summary={
                "target_url": intent.url,
                "user_goal": intake.action.goal if intake else None,
                "route_decision": (route_decision.route_decision.value if route_decision else None),
            },
        )
        self._append_event(
            session_id,
            ConversationEventType.CHAT_LEARNING_STARTED,
            {"url": intent.url, "browser_visibility": "headless" if headless else "visible"},
            events,
        )

        if self._learning_handler is None:
            return self._learning_failed(
                session_id,
                "Learning handler is not configured.",
                events,
                message_id,
                previous_status,
            )

        try:
            fill_values = _fill_values_from_intake(intake) or (
                _parse_product_inputs(intent.raw_text) if intent.url else None
            )
            learning_result: LearningRunResult = self._learning_handler(
                intent.url,
                intent.raw_text,
                headless=headless,
                fill_values=fill_values,
            )
        except Exception as exc:
            return self._learning_failed(
                session_id,
                str(exc),
                events,
                message_id,
                previous_status,
            )

        path = (
            LearnedPathRepository(self._repo.session).get(learning_result.learned_path_id)
            if learning_result.learned_path_id
            else None
        )
        if learning_result.status != "learned" or path is None:
            error = learning_result.error or "LearnedPath was not persisted."
            return self._learning_failed(
                session_id,
                error,
                events,
                message_id,
                previous_status,
            )

        action = _action_from_learning_result(learning_result)
        old_action = self._upsert_learned_action(session_id, action)
        self._record_skill_call(
            session_id,
            ApplicationSkillName.START_LEARNING,
            status="completed",
            output_summary={
                "run_id": learning_result.run_id,
                "learned_path_id": learning_result.learned_path_id,
                "target_url": action["target_url"],
            },
        )
        alias = action["alias"]
        complete_message = f"学习完成：我学会了{alias}操作。之后你可以说“帮我{alias}”。"
        self._append_agent_message(session_id, complete_message)
        self._append_event(
            session_id,
            ConversationEventType.CHAT_LEARNING_COMPLETED,
            {
                "run_id": learning_result.run_id,
                "old_learned_path_id": (old_action.get("learned_path_id") if old_action else None),
                "new_learned_path_id": learning_result.learned_path_id,
                "alias": action["alias"],
                "target_url": action["target_url"],
            },
            events,
        )
        self._clear_active_task(session_id)
        user_response = "开始学习页面操作。\n" + complete_message
        return self._result(
            session_id=session_id,
            command_kind="learn_page",
            user_response=user_response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _handle_execute_task(
        self,
        *,
        session_id: str,
        intent: ChatIntent,
        intake: ConversationIntakeResult | None,
        message_id: str | None,
        metadata: dict[str, Any] | None,
        previous_status: str,
        headless: bool = True,
        route_decision: RouteDecision | None = None,
    ) -> DispatchResult:
        events = self._append_chat_command_event(
            session_id=session_id,
            raw_input=intent.raw_text,
            command_kind="execute_task",
            metadata=metadata,
            intake=intake,
        )
        eval_non_planner_choice = self._maybe_apply_eval_candidate_setup(
            session_id=session_id,
            metadata=metadata,
            events=events,
        )
        if _looks_like_active_task_continuation(intent.raw_text):
            active_task = self._active_task(session_id)
            if active_task is not None:
                return self._handle_active_task_continuation(
                    session_id=session_id,
                    active_task=active_task,
                    events=events,
                    message_id=message_id,
                    previous_status=previous_status,
                )
        action = self._match_session_action(session_id, intent.raw_text, intake=intake)
        if action is None:
            user_url = _extract_url(intent.raw_text)
            candidates = self._matching_session_actions(
                session_id,
                intent.raw_text,
                intake=intake,
            )
            if len(candidates) > 1:
                if eval_non_planner_choice:
                    return self._handle_pending_choice_question(
                        session_id=session_id,
                        raw_input=intent.raw_text,
                        candidates=candidates,
                        slot_overrides=_slot_overrides_from_fill_values(
                            _fill_values_from_intake(intake) or {}
                        ),
                        events=events,
                        message_id=message_id,
                        previous_status=previous_status,
                        target_url=intent.url or user_url,
                        goal=intake.action.goal if intake else intent.raw_text,
                    )
                return self._handle_planner_pending_choice_question(
                    session_id=session_id,
                    raw_input=intent.raw_text,
                    candidates=candidates,
                    slot_overrides=_slot_overrides_from_fill_values(
                        _fill_values_from_intake(intake) or {}
                    ),
                    events=events,
                    message_id=message_id,
                    previous_status=previous_status,
                    target_url=intent.url or user_url,
                    goal=intake.action.goal if intake else intent.raw_text,
                    intake=intake,
                )
            if (
                route_decision is not None
                and route_decision.recommended_skill == ApplicationSkillName.LEARN_THEN_EXECUTE
            ):
                # M11.3.5 keeps learn-then-execute in guided mode: the Router may
                # recommend it, but runtime requires explicit learning first.
                self._save_last_no_path_reason(
                    session_id,
                    target_url=route_decision.target.url,
                    user_goal=route_decision.user_goal,
                    reason="learn_then_execute_requires_learning_first",
                    message_id=message_id,
                )
                self._save_pending_target(
                    session_id,
                    make_pending_target(route_decision.target.url)
                    if route_decision.target.url
                    else None,
                )
                self._record_skill_call(
                    session_id,
                    ApplicationSkillName.LEARN_THEN_EXECUTE,
                    status="blocked",
                    input_summary=route_decision.model_dump(mode="json"),
                    output_summary={"reason": "learning_confirmation_required_before_execution"},
                )
                response = "我还没学过这个操作。你可以先让我学习这个页面上的操作。"
                self._append_agent_message(session_id, response)
                self._append_event(
                    session_id,
                    ConversationEventType.CHAT_NO_PATH,
                    {"reason": "learn_then_execute_requires_learning_first"},
                    events,
                )
                return self._result(
                    session_id=session_id,
                    command_kind="execute_task",
                    user_response=response,
                    events=events,
                    message_id=message_id,
                    previous_status=previous_status,
                )
            if user_url and not self._has_learned_target(session_id, user_url):
                return self._handle_unlearned_target(
                    session_id=session_id,
                    command_kind="execute_task",
                    message_id=message_id,
                    metadata=metadata,
                    existing_events=events,
                    previous_status=previous_status,
                    target_url=user_url,
                    user_goal=intake.action.goal if intake else None,
                )
            return self._handle_no_path(
                session_id=session_id,
                command_kind="execute_task",
                message_id=message_id,
                metadata=metadata,
                existing_events=events,
                previous_status=previous_status,
            )

        return self._execute_matched_action(
            session_id=session_id,
            action=action,
            intake=intake,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
            headless=headless,
            command_kind="execute_task",
            dispatch_metadata=metadata,
        )

    def _execute_matched_action(
        self,
        *,
        session_id: str,
        action: dict[str, Any],
        intake: ConversationIntakeResult | None,
        slot_overrides_override: dict[str, str] | None = None,
        events: list[str],
        message_id: str | None,
        previous_status: str,
        headless: bool,
        command_kind: str,
        retry_count_override: int | None = None,
        dispatch_metadata: dict[str, Any] | None = None,
    ) -> DispatchResult:
        if self._replay_handler is None:
            response = "执行失败：replay handler 未配置。"
            self._update_active_task(session_id, status="failed")
            self._append_agent_message(session_id, response)
            self._append_event(
                session_id,
                ConversationEventType.CHAT_EXECUTION_FAILED,
                {
                    "reason": "missing_replay_handler",
                    "browser_visibility": "headless" if headless else "visible",
                },
                events,
            )
            return self._result(
                session_id=session_id,
                command_kind=command_kind,
                user_response=response,
                events=events,
                message_id=message_id,
                previous_status=previous_status,
                allowed=False,
                error="Replay handler is not configured.",
            )

        fill_values = _fill_values_from_intake(intake) or {}
        slot_overrides = (
            dict(slot_overrides_override)
            if slot_overrides_override is not None
            else _slot_overrides_from_fill_values(fill_values)
        )
        path = LearnedPathRepository(self._repo.session).get(action["learned_path_id"])
        supports_item_name = _learned_path_supports_value_slot(path, "item_name")
        if slot_overrides.get("item_name") and supports_item_name is False:
            return self._handle_missing_parameterized_path(
                session_id=session_id,
                action=action,
                slot_overrides=slot_overrides,
                events=events,
                message_id=message_id,
                previous_status=previous_status,
            )
        if supports_item_name is True and not slot_overrides.get("item_name"):
            return self._handle_missing_runtime_slot(
                session_id=session_id,
                action=action,
                slot_name="item_name",
                events=events,
                message_id=message_id,
                previous_status=previous_status,
            )

        self._set_active_task(
            session_id,
            kind="execute_operation",
            owner="web_operation_agent",
            status="executing",
            target_url=action.get("target_url"),
            goal=action.get("alias"),
        )
        self._append_agent_message(session_id, "执行中。")
        self._record_skill_call(
            session_id,
            ApplicationSkillName.START_REPLAY,
            status="started",
            input_summary={
                "learned_path_id": action["learned_path_id"],
                "target_url": action["target_url"],
                "alias": action["alias"],
                "slot_overrides": slot_overrides,
            },
        )
        execution_payload = {
            "learned_path_id": action["learned_path_id"],
            "target_url": action["target_url"],
            "alias": action["alias"],
            "browser_visibility": "headless" if headless else "visible",
        }
        if slot_overrides:
            execution_payload["slot_overrides"] = slot_overrides
        self._append_event(
            session_id,
            ConversationEventType.CHAT_EXECUTION_STARTED,
            execution_payload,
            events,
        )
        replay_kwargs: dict[str, Any] = {"headless": headless}
        if slot_overrides:
            replay_kwargs["slot_overrides"] = slot_overrides
        evidence_targets = _build_execution_evidence_targets(action, slot_overrides)
        if evidence_targets:
            replay_kwargs["evidence_targets"] = evidence_targets
        replay_summary = self._replay_handler(
            action["learned_path_id"],
            action["target_url"],
            **replay_kwargs,
        )
        alias = action.get("alias", "")
        report = None
        if evidence_targets:
            from app.services.task_planning.result_reporter import TaskResultReporter

            (
                report_execution_status,
                report_execution_payload,
                report_confirmed_context,
            ) = _build_replay_reporter_context(
                action=action,
                slot_overrides=slot_overrides,
                replay_summary=replay_summary,
            )
            report = TaskResultReporter().build_report(
                execution_status=report_execution_status,
                execution_payload=report_execution_payload,
                replay_summary=replay_summary,
                confirmed_plan_context=report_confirmed_context,
            )
            session = self._repo.get_session(session_id)
            session_metadata = session.metadata_json if session is not None else {}
            eval_outcome = _eval_fault_reporter_outcome(
                session_metadata=session_metadata or {},
                dispatch_metadata=dispatch_metadata,
            )
            if eval_outcome is not None:
                report = _with_eval_fault_report(report, eval_outcome)
                self._append_event(
                    session_id,
                    ConversationEventType.CHAT_PROGRESS_RECORDED,
                    {
                        "progress_kind": "eval_fault_injection_applied",
                        "case_id": _EVAL_FAILURE_RECOVERY_CASE_ID,
                        "fault_class": eval_outcome,
                    },
                    events,
                )
        failure_class = _basic_failure_class(replay_summary, report)
        if failure_class is None:
            if report is not None:
                final_message = _chat_report_user_response(report, slot_overrides)
            else:
                final_message = f"{alias}完成。" if alias else "执行完成。"
            event_type = ConversationEventType.CHAT_EXECUTION_COMPLETED
            error = None
            allowed = True
            self._clear_active_task(session_id)
            self._record_skill_call(
                session_id,
                ApplicationSkillName.START_REPLAY,
                status="completed",
                output_summary={
                    "learned_path_id": action["learned_path_id"],
                    "replay_status": replay_summary.replay_status,
                    "drift_status": replay_summary.drift_status,
                    "verification_outcome": report.outcome if report else None,
                },
            )

            self._append_agent_message(session_id, final_message)
            self._append_event(
                session_id,
                event_type,
                {
                    "learned_path_id": action["learned_path_id"],
                    "target_url": action["target_url"],
                    "alias": action["alias"],
                    "replay": replay_summary.model_dump(mode="json"),
                },
                events,
            )
            if report is not None:
                self._append_event(
                    session_id,
                    ConversationEventType.TASK_RESULT_REPORTED,
                    report.event_payload,
                    events,
                )
            return self._result(
                session_id=session_id,
                command_kind=command_kind,
                user_response="执行中。\n" + final_message,
                events=events,
                message_id=message_id,
                previous_status=previous_status,
                allowed=allowed,
                error=error,
                replay_result=replay_summary,
            )

        error = replay_summary.error or failure_class or replay_summary.replay_status
        allowed = failure_class in _RECOVERY_SIDE_EFFECT_CLASSES
        self._record_skill_call(
            session_id,
            ApplicationSkillName.START_REPLAY,
            status="completed" if allowed else "failed",
            output_summary={
                "learned_path_id": action["learned_path_id"],
                "replay_status": replay_summary.replay_status,
                "drift_status": replay_summary.drift_status,
                "verification_outcome": report.outcome if report else None,
                "failure_class": failure_class,
            },
        )
        self._append_event(
            session_id,
            ConversationEventType.CHAT_EXECUTION_FAILED,
            {
                "learned_path_id": action["learned_path_id"],
                "target_url": action["target_url"],
                "alias": action["alias"],
                "failure_class": failure_class,
                "replay": replay_summary.model_dump(mode="json"),
            },
            events,
        )
        if report is not None:
            self._append_event(
                session_id,
                ConversationEventType.TASK_RESULT_REPORTED,
                report.event_payload,
                events,
            )
        return self._offer_basic_failure_recovery(
            session_id=session_id,
            action=action,
            slot_overrides=slot_overrides,
            evidence_targets=evidence_targets,
            replay_summary=replay_summary,
            report=report,
            failure_class=failure_class,
            retry_count_override=retry_count_override,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
            command_kind=command_kind,
            allowed=allowed,
            error=error,
        )

    def _handle_missing_parameterized_path(
        self,
        *,
        session_id: str,
        action: dict[str, Any],
        slot_overrides: dict[str, str],
        events: list[str],
        message_id: str | None,
        previous_status: str,
    ) -> DispatchResult:
        self._update_active_task(session_id, status="failed")
        item_name = slot_overrides.get("item_name", "")
        response = (
            "我找到了已学习的“新增项目”路径，但它还不是可参数化路径，"
            f"不能安全地把项目名替换成“{item_name}”。请重新学习一次新增项目操作。"
        )
        self._record_skill_call(
            session_id,
            ApplicationSkillName.START_REPLAY,
            status="blocked",
            input_summary={
                "learned_path_id": action["learned_path_id"],
                "target_url": action["target_url"],
                "alias": action["alias"],
                "slot_overrides": slot_overrides,
            },
            output_summary={"reason": "missing_item_name_value_slot"},
        )
        self._append_agent_message(session_id, response)
        self._append_event(
            session_id,
            ConversationEventType.CHAT_EXECUTION_FAILED,
            {
                "reason": "missing_item_name_value_slot",
                "learned_path_id": action["learned_path_id"],
                "target_url": action["target_url"],
                "alias": action["alias"],
                "slot_overrides": slot_overrides,
            },
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind="execute_task",
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
            allowed=False,
            error="missing_item_name_value_slot",
        )

    def _handle_missing_runtime_slot(
        self,
        *,
        session_id: str,
        action: dict[str, Any],
        slot_name: str,
        events: list[str],
        message_id: str | None,
        previous_status: str,
    ) -> DispatchResult:
        self._set_active_task(
            session_id,
            kind="clarify",
            owner="runtime",
            status="waiting_for_user_input",
            target_url=action.get("target_url"),
            goal=action.get("alias"),
        )
        display_name = "项目名称" if slot_name == "item_name" else slot_name
        alias = action.get("alias", "网页操作")
        response = f"我找到了已学习的“{alias}”路径，但还需要{display_name}。"
        self._record_skill_call(
            session_id,
            ApplicationSkillName.ASK_USER_FOR_MISSING_INFO,
            status="completed",
            input_summary={"missing_fields": [slot_name]},
            output_summary={"target_url": action.get("target_url")},
        )
        self._append_agent_message(session_id, response)
        self._append_event(
            session_id,
            ConversationEventType.CHAT_NO_PATH,
            {
                "reason": "missing_runtime_slot",
                "slot": slot_name,
                "alias": action.get("alias"),
                "target_url": action.get("target_url"),
            },
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind="execute_task",
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _handle_active_task_continuation(
        self,
        *,
        session_id: str,
        active_task: dict[str, Any],
        events: list[str],
        message_id: str | None,
        previous_status: str,
    ) -> DispatchResult:
        goal = str(active_task.get("goal") or "").strip()
        suffix = f"：{goal}" if goal else ""
        response = (
            f"当前还有一个操作需要你补充或确认{suffix}。"
            "请直接补充需要的信息，或回复“取消”结束当前任务。"
        )
        self._append_agent_message(
            session_id,
            response,
            provenance=code_response_provenance(CODE_PRODUCER_INTERACTIVE_CHAT),
        )
        self._append_event(
            session_id,
            ConversationEventType.CHAT_PROGRESS_RECORDED,
            {
                "progress_kind": "active_task_continue_requested",
                "active_task": redact_sensitive_payload(active_task),
            },
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind="execute_task",
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _handle_planner_pending_choice_question(
        self,
        *,
        session_id: str,
        raw_input: str,
        candidates: list[dict[str, Any]],
        slot_overrides: dict[str, str],
        events: list[str],
        message_id: str | None,
        previous_status: str,
        target_url: str | None,
        goal: str | None,
        intake: ConversationIntakeResult | None,
    ) -> DispatchResult:
        learned_path_repo = LearnedPathRepository(self._repo.session)
        planner_candidates = _planner_candidates_from_session_actions(
            candidates,
            learned_path_repo=learned_path_repo,
        )
        valid_path_ids = {candidate.learned_path_id for candidate in planner_candidates}
        ranked_candidates = [
            action
            for action in candidates
            if str(action.get("learned_path_id") or "") in valid_path_ids
        ]
        self._append_event(
            session_id,
            ConversationEventType.CHAT_PROGRESS_RECORDED,
            {
                "progress_kind": "planner_candidates_generated",
                "candidate_count": len(ranked_candidates),
            },
            events,
        )
        if not planner_candidates or not ranked_candidates:
            return self._handle_planner_fallback_choice(
                session_id=session_id,
                raw_input=raw_input,
                candidates=candidates,
                slot_overrides=slot_overrides,
                events=events,
                message_id=message_id,
                previous_status=previous_status,
                target_url=target_url,
                goal=goal,
                reason="planner_candidates_empty",
            )

        task_intent = _build_task_intent_for_planner(
            raw_input,
            intake,
            target_url=target_url,
        )
        try:
            planner_output = TaskPathPlanner().plan(task_intent, planner_candidates)
        except Exception:
            return self._handle_planner_fallback_choice(
                session_id=session_id,
                raw_input=raw_input,
                candidates=ranked_candidates,
                slot_overrides=slot_overrides,
                events=events,
                message_id=message_id,
                previous_status=previous_status,
                target_url=target_url,
                goal=goal,
                reason="planner_unavailable",
            )

        route_plan = planner_output.route_plan
        if route_plan is None or not route_plan.steps:
            return self._handle_planner_unable_to_plan(
                session_id=session_id,
                raw_input=raw_input,
                planner_output=planner_output,
                events=events,
                message_id=message_id,
                previous_status=previous_status,
                target_url=target_url,
                goal=goal,
            )

        top_learned_path_id = str(route_plan.steps[0].learned_path_id or "")
        top_choice_index = next(
            (
                index
                for index, action in enumerate(ranked_candidates)
                if str(action.get("learned_path_id") or "") == top_learned_path_id
            ),
            None,
        )
        if top_choice_index is None:
            return self._handle_planner_fallback_choice(
                session_id=session_id,
                raw_input=raw_input,
                candidates=ranked_candidates,
                slot_overrides=slot_overrides,
                events=events,
                message_id=message_id,
                previous_status=previous_status,
                target_url=target_url,
                goal=goal,
                reason="planner_top_candidate_not_in_session",
            )

        pending_choice, private_map = _build_planner_pending_choice(
            ranked_candidates,
            slot_overrides=slot_overrides,
            planner_output=planner_output,
            top_choice_index=top_choice_index,
        )
        self._save_pending_choice(
            session_id,
            pending_choice=pending_choice,
            private_map=private_map,
        )
        self._set_active_task(
            session_id,
            kind="clarify",
            owner="runtime",
            status="waiting_for_user_input",
            target_url=target_url,
            goal=goal or raw_input,
        )
        response = _pending_choice_response(pending_choice)
        self._append_agent_message(
            session_id,
            response,
            provenance=code_response_provenance(CODE_PRODUCER_INTERACTIVE_CHAT),
        )
        self._append_event(
            session_id,
            ConversationEventType.CHAT_PROGRESS_RECORDED,
            _planner_choice_created_event_payload(
                pending_choice,
                planner_output=planner_output,
                candidate_count=len(ranked_candidates),
            ),
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind="pending_choice",
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _handle_planner_unable_to_plan(
        self,
        *,
        session_id: str,
        raw_input: str,
        planner_output: AgentDPlannerOutput,
        events: list[str],
        message_id: str | None,
        previous_status: str,
        target_url: str | None,
        goal: str | None,
    ) -> DispatchResult:
        self._save_last_no_path_reason(
            session_id,
            target_url=target_url,
            user_goal=goal or raw_input,
            reason="planner_unable_to_plan",
            message_id=message_id,
        )
        self._set_active_task(
            session_id,
            kind="clarify",
            owner="runtime",
            status="waiting_for_user_input",
            target_url=target_url,
            goal=goal or raw_input,
        )
        response = "我还不能可靠判断要执行哪个已学习操作。你可以说得更具体，或者重新学习一个操作。"
        self._append_agent_message(
            session_id,
            response,
            provenance=code_response_provenance(CODE_PRODUCER_INTERACTIVE_CHAT),
        )
        self._append_event(
            session_id,
            ConversationEventType.CHAT_PROGRESS_RECORDED,
            {
                "progress_kind": "planner_unable_to_plan",
                "planner_warning_count": len(planner_output.warnings),
                "planner_risk_count": len(planner_output.risk_hints),
                "uncertainty_count": len(planner_output.uncertainty),
            },
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind="pending_choice",
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
            allowed=False,
            error="planner_unable_to_plan",
        )

    def _handle_planner_fallback_choice(
        self,
        *,
        session_id: str,
        raw_input: str,
        candidates: list[dict[str, Any]],
        slot_overrides: dict[str, str],
        events: list[str],
        message_id: str | None,
        previous_status: str,
        target_url: str | None,
        goal: str | None,
        reason: str,
    ) -> DispatchResult:
        self._append_event(
            session_id,
            ConversationEventType.CHAT_PROGRESS_RECORDED,
            {
                "progress_kind": "planner_fallback_used",
                "reason": reason,
                "candidate_count": len(candidates),
            },
            events,
        )
        return self._handle_pending_choice_question(
            session_id=session_id,
            raw_input=raw_input,
            candidates=candidates,
            slot_overrides=slot_overrides,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
            target_url=target_url,
            goal=goal,
        )

    def _handle_pending_choice_question(
        self,
        *,
        session_id: str,
        raw_input: str,
        candidates: list[dict[str, Any]],
        slot_overrides: dict[str, str],
        events: list[str],
        message_id: str | None,
        previous_status: str,
        target_url: str | None,
        goal: str | None,
    ) -> DispatchResult:
        pending_choice, private_map = _build_pending_choice(
            candidates,
            slot_overrides=slot_overrides,
        )
        self._save_pending_choice(
            session_id,
            pending_choice=pending_choice,
            private_map=private_map,
        )
        self._set_active_task(
            session_id,
            kind="clarify",
            owner="runtime",
            status="waiting_for_user_input",
            target_url=target_url,
            goal=goal or raw_input,
        )
        response = _pending_choice_response(pending_choice)
        self._append_agent_message(
            session_id,
            response,
            provenance=code_response_provenance(CODE_PRODUCER_INTERACTIVE_CHAT),
        )
        self._append_event(
            session_id,
            ConversationEventType.CHAT_PROGRESS_RECORDED,
            {
                "progress_kind": "pending_choice_created",
                "pending_choice": pending_choice,
            },
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind="pending_choice",
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _offer_basic_failure_recovery(
        self,
        *,
        session_id: str,
        action: dict[str, Any],
        slot_overrides: dict[str, str],
        evidence_targets: list[ExecutionEvidenceTarget],
        replay_summary: ConversationReplaySummary,
        report: Any | None,
        failure_class: str,
        events: list[str],
        message_id: str | None,
        previous_status: str,
        command_kind: str,
        allowed: bool,
        error: str | None,
        retry_count_override: int | None = None,
    ) -> DispatchResult:
        retry_count = (
            retry_count_override
            if retry_count_override is not None
            else _retry_count_from_replay_summary(replay_summary)
        )
        pending_choice, private_map = _build_recovery_pending_choice(
            action=action,
            slot_overrides=slot_overrides,
            evidence_targets=evidence_targets,
            failure_class=failure_class,
            retry_count=retry_count,
        )
        self._save_pending_choice(
            session_id,
            pending_choice=pending_choice,
            private_map=private_map,
        )
        self._set_active_task(
            session_id,
            kind="execute_operation",
            owner="runtime",
            status="waiting_for_user_input",
            target_url=action.get("target_url"),
            goal=action.get("alias"),
        )
        failure_message = _recovery_failure_message(
            failure_class=failure_class,
            report=report,
            slot_overrides=slot_overrides,
        )
        response = _pending_choice_response(pending_choice, prefix=failure_message)
        self._append_agent_message(
            session_id,
            response,
            provenance=code_response_provenance(CODE_PRODUCER_INTERACTIVE_CHAT),
        )
        self._append_event(
            session_id,
            ConversationEventType.CHAT_PROGRESS_RECORDED,
            {
                "progress_kind": "failure_recovery_offered",
                "failure_class": failure_class,
                "choice_group_id": pending_choice["choice_group_id"],
                "retry_count": retry_count,
                "choices": pending_choice["choices"],
                "action_alias": action.get("alias"),
            },
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind=command_kind,
            user_response="执行中。\n" + response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
            allowed=allowed,
            error=error,
            replay_result=replay_summary,
        )

    def _handle_unlearned_target(
        self,
        *,
        session_id: str,
        command_kind: str,
        message_id: str | None,
        metadata: dict[str, Any] | None,
        existing_events: list[str] | None = None,
        previous_status: str = ConversationStatus.TASK_INTAKE.value,
        target_url: str | None = None,
        user_goal: str | None = None,
    ) -> DispatchResult:
        events = existing_events or self._append_chat_command_event(
            session_id=session_id,
            raw_input="",
            command_kind=command_kind,
            metadata=metadata,
        )
        self._save_last_no_path_reason(
            session_id,
            target_url=target_url,
            user_goal=user_goal,
            reason="unlearned_target_url",
            message_id=message_id,
        )
        if target_url:
            self._save_pending_target(session_id, make_pending_target(target_url))
        self._append_agent_message(session_id, _UNLEARNED_TARGET_RESPONSE)
        self._append_event(
            session_id,
            ConversationEventType.CHAT_NO_PATH,
            {
                "reason": "unlearned_target_url",
                "target_url": target_url,
                "user_goal": user_goal,
            },
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind=command_kind,
            user_response=_UNLEARNED_TARGET_RESPONSE,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _handle_ambiguous_target(
        self,
        *,
        session_id: str,
        command_kind: str,
        message_id: str | None,
        metadata: dict[str, Any] | None,
        existing_events: list[str] | None = None,
        previous_status: str = ConversationStatus.TASK_INTAKE.value,
    ) -> DispatchResult:
        events = existing_events or self._append_chat_command_event(
            session_id=session_id,
            raw_input="",
            command_kind=command_kind,
            metadata=metadata,
        )
        self._save_last_no_path_reason(
            session_id,
            target_url=None,
            user_goal=None,
            reason="ambiguous_target_scope",
            message_id=message_id,
        )
        self._append_agent_message(session_id, _AMBIGUOUS_TARGET_RESPONSE)
        self._append_event(
            session_id,
            ConversationEventType.CHAT_NO_PATH,
            {"reason": "ambiguous_target_scope"},
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind=command_kind,
            user_response=_AMBIGUOUS_TARGET_RESPONSE,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _handle_no_path(
        self,
        *,
        session_id: str,
        command_kind: str,
        message_id: str | None,
        metadata: dict[str, Any] | None,
        existing_events: list[str] | None = None,
        previous_status: str = ConversationStatus.TASK_INTAKE.value,
    ) -> DispatchResult:
        events = existing_events or self._append_chat_command_event(
            session_id=session_id,
            raw_input="",
            command_kind=command_kind,
            metadata=metadata,
        )
        self._save_last_no_path_reason(
            session_id,
            target_url=None,
            user_goal=None,
            reason="no_session_learned_action",
            message_id=message_id,
        )
        self._append_agent_message(session_id, _NO_PATH_RESPONSE)
        self._append_event(
            session_id,
            ConversationEventType.CHAT_NO_PATH,
            {"reason": "no_session_learned_action"},
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind=command_kind,
            user_response=_NO_PATH_RESPONSE,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
        )

    def _learning_failed(
        self,
        session_id: str,
        error: str,
        events: list[str],
        message_id: str | None,
        previous_status: str,
    ) -> DispatchResult:
        response = f"学习失败：{error}"
        self._update_active_task(
            session_id,
            status="failed",
        )
        self._record_skill_call(
            session_id,
            ApplicationSkillName.START_LEARNING,
            status="failed",
            output_summary={"error": error},
        )
        self._append_agent_message(session_id, response)
        self._append_event(
            session_id,
            ConversationEventType.CHAT_LEARNING_FAILED,
            {"error": error},
            events,
        )
        return self._result(
            session_id=session_id,
            command_kind="learn_page",
            user_response=response,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
            allowed=False,
            error=error,
        )

    def _append_chat_command_event(
        self,
        *,
        session_id: str,
        raw_input: str,
        command_kind: str,
        metadata: dict[str, Any] | None,
        intake: ConversationIntakeResult | None = None,
    ) -> list[str]:
        payload: dict[str, Any] = {
            "raw": raw_input,
            "command_kind": command_kind,
            "dispatch_metadata": metadata or {},
            "mode": "interactive_chat",
            "allowed": True,
        }
        if intake is not None:
            payload["intake"] = intake.model_dump(mode="json")
        payload = redact_sensitive_payload(payload)
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.COMMAND_PARSED,
            payload=payload,
        )
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.MESSAGE_RECEIVED,
            payload={"mode": "interactive_chat", "command_kind": command_kind},
        )
        return [
            ConversationEventType.COMMAND_PARSED.value,
            ConversationEventType.MESSAGE_RECEIVED.value,
        ]

    def _append_agent_message(
        self,
        session_id: str,
        content: str,
        *,
        provenance: dict[str, Any] | None = None,
    ) -> None:
        self._repo.append_message(
            session_id=session_id,
            role="agent",
            content=content,
            metadata={
                "source": "interactive_chat",
                "response_provenance": provenance
                or code_response_provenance(CODE_PRODUCER_INTERACTIVE_CHAT),
            },
        )

    def _record_intake_trace(
        self,
        session_id: str,
        *,
        fallback: bool,
    ) -> IntakeTraceContext:
        consume_trace = getattr(self._intake_service, "consume_last_trace_payload", None)
        if not callable(consume_trace):
            return IntakeTraceContext([], [], fallback=fallback)
        payload = consume_trace()
        if not isinstance(payload, dict):
            return IntakeTraceContext([], [], fallback=fallback)
        trace_id = str(payload.get("trace_id") or f"trace-{session_id}")
        payload = {**payload, "trace_id": trace_id}
        event = self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.LLM_TRACE_RECORDED,
            payload=sanitize_provider_thinking(redact_sensitive_payload(payload)),
        )
        return IntakeTraceContext([trace_id], [event.id], fallback=fallback)

    def _record_entry_gate_trace(
        self,
        session_id: str,
        *,
        entry_gate: ConversationEntryGateResult,
        skipped_intake_router: bool,
    ) -> IntakeTraceContext:
        consume_trace = getattr(self._entry_gate_service, "consume_last_trace_payload", None)
        raw_trace = consume_trace() if callable(consume_trace) else None
        if not isinstance(raw_trace, dict):
            raw_trace = {}
        payload = sanitize_provider_thinking(
            redact_sensitive_payload(
                {
                    "entry_gate": entry_gate.model_dump(mode="json"),
                    "skipped_intake_router": skipped_intake_router,
                    "provider": entry_gate.provider or raw_trace.get("provider"),
                    "model": entry_gate.model or raw_trace.get("model"),
                    "prompt_template_id": raw_trace.get("prompt_template_id"),
                    "prompt_hash": raw_trace.get("prompt_hash"),
                    "latency_ms": entry_gate.latency_ms,
                    "timeout_ms": entry_gate.timeout_ms,
                    "fallback": entry_gate.fallback,
                    "error_kind": entry_gate.error_kind,
                    "raw": raw_trace,
                }
            )
        )
        event = self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.ENTRY_GATE_RECORDED,
            payload=payload,
        )
        return IntakeTraceContext(
            [],
            [event.id],
            fallback=entry_gate.fallback,
            event_types=[ConversationEventType.ENTRY_GATE_RECORDED.value],
        )

    def _record_router_trace(
        self,
        session_id: str,
        *,
        route_decision: RouteDecision,
        llm_trace_context: IntakeTraceContext,
    ) -> IntakeTraceContext:
        event = self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.AGENT_TRACE_RECORDED,
            payload=redact_sensitive_payload(
                {
                    "agent_role": AGENT_PRODUCER_CUSTOMER_FACING_ROUTER,
                    "trace_kind": "route_decision",
                    "route_decision": route_decision.model_dump(mode="json"),
                    "llm_trace_ids": llm_trace_context.trace_ids,
                    "generated_from_event_ids": llm_trace_context.event_ids,
                }
            ),
        )
        self._record_skill_call(
            session_id,
            ApplicationSkillName.RECORD_AGENT_TRACE,
            status="completed",
            input_summary={"agent_role": AGENT_PRODUCER_CUSTOMER_FACING_ROUTER},
            output_summary={"source_event_id": event.id},
        )
        return IntakeTraceContext(
            llm_trace_context.trace_ids,
            [*llm_trace_context.event_ids, event.id],
            event_types=[
                *self._trace_event_types(llm_trace_context),
                ConversationEventType.AGENT_TRACE_RECORDED.value,
            ],
        )

    def _record_router_llm_trace(self, session_id: str) -> IntakeTraceContext:
        consume_trace = getattr(self._router_service, "consume_last_trace_payload", None)
        if not callable(consume_trace):
            return IntakeTraceContext([], [])
        payload = consume_trace()
        if not isinstance(payload, dict):
            return IntakeTraceContext([], [])
        trace_id = str(payload.get("trace_id") or f"router-trace-{session_id}")
        payload = {**payload, "trace_id": trace_id}
        event = self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.LLM_TRACE_RECORDED,
            payload=sanitize_provider_thinking(redact_sensitive_payload(payload)),
        )
        return IntakeTraceContext([trace_id], [event.id])

    def _record_page_understanding_trace(
        self,
        session_id: str,
        *,
        page_understanding: dict[str, Any],
        router_trace_context: IntakeTraceContext,
    ) -> IntakeTraceContext:
        event = self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.AGENT_TRACE_RECORDED,
            payload=redact_sensitive_payload(
                {
                    "agent_role": "page_understanding_agent",
                    "trace_kind": "page_understanding",
                    "page_understanding": page_understanding,
                    "generated_from_event_ids": router_trace_context.event_ids,
                }
            ),
        )
        self._record_skill_call(
            session_id,
            ApplicationSkillName.RECORD_AGENT_TRACE,
            status="completed",
            input_summary={"agent_role": "page_understanding_agent"},
            output_summary={"source_event_id": event.id},
        )
        return IntakeTraceContext(
            [],
            [event.id],
            event_types=[ConversationEventType.AGENT_TRACE_RECORDED.value],
        )

    def _trace_event_types(self, trace_context: IntakeTraceContext) -> list[str]:
        if not trace_context.event_ids:
            return []
        if trace_context.event_types is not None:
            return trace_context.event_types
        return [ConversationEventType.LLM_TRACE_RECORDED.value]

    def _record_skill_call(
        self,
        session_id: str,
        skill_name: ApplicationSkillName,
        *,
        status: str,
        input_summary: dict[str, Any] | None = None,
        output_summary: dict[str, Any] | None = None,
    ) -> None:
        skill = self._skill_registry.get(skill_name)
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.SKILL_CALL_RECORDED,
            payload=redact_sensitive_payload(
                {
                    "skill": skill.name.value,
                    "status": status,
                    "executor_owner": skill.executor_owner,
                    "browser_access": skill.browser_access,
                    "changes_page": skill.changes_page,
                    "writes_learned_path": skill.writes_learned_path,
                    "input_summary": input_summary or {},
                    "output_summary": output_summary or {},
                }
            ),
        )

    def _intake_reply_provenance(
        self,
        intake: ConversationIntakeResult,
        trace_context: IntakeTraceContext,
    ) -> dict[str, Any]:
        fallback = trace_context.fallback or intake.source in {
            "provider_error",
            "provider_parse_error",
        }
        if fallback:
            return code_response_provenance(
                CODE_PRODUCER_INTERACTIVE_CHAT,
                llm_trace_ids=trace_context.trace_ids,
                generated_from_event_ids=trace_context.event_ids,
                fallback=True,
            )
        if trace_context.trace_ids:
            return agent_response_provenance(
                AGENT_PRODUCER_CONVERSATION_INTAKE,
                llm_trace_ids=trace_context.trace_ids,
                generated_from_event_ids=trace_context.event_ids,
            )
        return code_response_provenance(
            CODE_PRODUCER_INTERACTIVE_CHAT,
            llm_trace_ids=trace_context.trace_ids,
            generated_from_event_ids=trace_context.event_ids,
        )

    def _append_event(
        self,
        session_id: str,
        event_type: ConversationEventType,
        payload: dict[str, Any],
        events: list[str],
    ) -> None:
        self._repo.append_event(session_id=session_id, type=event_type, payload=payload)
        events.append(event_type.value)

    def _upsert_learned_action(
        self,
        session_id: str,
        action: dict[str, Any],
    ) -> dict[str, Any] | None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        metadata = dict(session.metadata_json or {})
        existing = list(metadata.get("learned_actions") or [])
        action_key = _action_scope_key(action)
        old_action = next(
            (item for item in existing if _action_scope_key(item) == action_key),
            None,
        )
        merged = [item for item in existing if _action_scope_key(item) != action_key]
        merged.append(action)
        metadata["learned_actions"] = merged
        metadata.pop("pending_intake", None)
        metadata.pop("pending_target", None)
        metadata.pop("pending_choice", None)
        metadata.pop("pending_choice_private_map", None)
        metadata.pop("last_no_path_reason", None)
        clear_pending_sensitive_values(session_id)
        self._replace_session_metadata(session_id, metadata)
        return old_action

    def _pending_intake(self, session_id: str) -> dict[str, Any] | None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        pending = (session.metadata_json or {}).get("pending_intake")
        return pending if isinstance(pending, dict) else None

    def _save_pending_intake(
        self,
        session_id: str,
        intake: ConversationIntakeResult,
        message_id: str | None,
        *,
        turns_remaining: int | None = None,
    ) -> None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        metadata = dict(session.metadata_json or {})
        pending = {
            "intent": intake.intent.value,
            "target": intake.target.model_dump(mode="json", exclude_none=True),
            "action": intake.action.model_dump(mode="json", exclude_none=True),
            "slots": [slot.model_dump(mode="json", exclude_none=True) for slot in intake.slots],
            "missing_fields": [field.semantic_type for field in intake.missing_fields],
            "created_from_message_id": message_id,
            "turns_remaining": turns_remaining if turns_remaining is not None else 3,
        }
        sensitive_values = {
            slot.semantic_type: slot.value for slot in intake.slots if slot.sensitive and slot.value
        }
        if sensitive_values:
            stored = dict(_PENDING_SENSITIVE_VALUES.get(session_id) or {})
            stored.update(sensitive_values)
            _PENDING_SENSITIVE_VALUES[session_id] = stored
        metadata["pending_intake"] = redact_sensitive_payload(pending)
        if intake.target.url:
            metadata["pending_target"] = redact_sensitive_payload(
                make_pending_target(intake.target.url).model_dump(mode="json")
            )
        self._replace_session_metadata(session_id, metadata)

    def _clear_pending_intake(self, session_id: str) -> None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        metadata = dict(session.metadata_json or {})
        metadata.pop("pending_intake", None)
        metadata.pop("pending_target", None)
        metadata.pop("pending_choice", None)
        metadata.pop("pending_choice_private_map", None)
        metadata.pop("last_no_path_reason", None)
        metadata.pop("active_task", None)
        clear_pending_sensitive_values(session_id)
        self._replace_session_metadata(session_id, metadata)

    def _save_pending_target(
        self,
        session_id: str,
        target: PendingTarget | None,
    ) -> None:
        if target is None:
            return
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        metadata = dict(session.metadata_json or {})
        metadata["pending_target"] = redact_sensitive_payload(target.model_dump(mode="json"))
        self._replace_session_metadata(session_id, metadata)

    def _save_last_no_path_reason(
        self,
        session_id: str,
        *,
        target_url: str | None,
        user_goal: str | None,
        reason: str,
        message_id: str | None,
    ) -> None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        metadata = dict(session.metadata_json or {})
        metadata["last_no_path_reason"] = redact_sensitive_payload(
            {
                "target_url": target_url,
                "user_goal": user_goal,
                "reason": reason,
                "created_from_message_id": message_id,
            }
        )
        self._replace_session_metadata(session_id, metadata)

    def _pending_choice(self, session_id: str) -> dict[str, Any] | None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        pending = (session.metadata_json or {}).get("pending_choice")
        if not _valid_pending_choice_payload(pending):
            if pending is not None:
                self._clear_pending_choice(session_id)
            return None
        return dict(pending)

    def _pending_choice_private_map(self, session_id: str) -> dict[str, dict[str, Any]]:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        private_map = (session.metadata_json or {}).get("pending_choice_private_map")
        if not isinstance(private_map, dict):
            return {}
        return {
            str(choice_id): dict(value)
            for choice_id, value in private_map.items()
            if isinstance(value, dict)
        }

    def _active_task(self, session_id: str) -> dict[str, Any] | None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        active_task = (session.metadata_json or {}).get("active_task")
        if not isinstance(active_task, dict):
            return None
        if active_task.get("status") not in _LIVE_ACTIVE_TASK_STATUSES:
            return None
        return dict(active_task)

    def _save_pending_choice(
        self,
        session_id: str,
        *,
        pending_choice: dict[str, Any],
        private_map: dict[str, dict[str, Any]],
    ) -> None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        metadata = dict(session.metadata_json or {})
        metadata["pending_choice"] = redact_sensitive_payload(pending_choice)
        metadata["pending_choice_private_map"] = redact_sensitive_payload(private_map)
        metadata.pop("last_no_path_reason", None)
        self._replace_session_metadata(session_id, metadata)

    def _save_pending_choice_payload(
        self,
        session_id: str,
        pending_choice: dict[str, Any],
    ) -> None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        metadata = dict(session.metadata_json or {})
        metadata["pending_choice"] = redact_sensitive_payload(pending_choice)
        self._replace_session_metadata(session_id, metadata)

    def _clear_pending_choice(self, session_id: str) -> None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        metadata = dict(session.metadata_json or {})
        metadata.pop("pending_choice", None)
        metadata.pop("pending_choice_private_map", None)
        self._replace_session_metadata(session_id, metadata)

    def _set_active_task(
        self,
        session_id: str,
        *,
        kind: str,
        owner: str,
        status: str,
        target_url: str | None = None,
        goal: str | None = None,
    ) -> None:
        now = _utc_now_iso()
        task = {
            "task_id": f"task-{uuid.uuid4()}",
            "kind": kind,
            "target_url": target_url,
            "goal": goal,
            "owner": owner,
            "status": status,
            "created_at": now,
            "updated_at": now,
        }
        task = {key: value for key, value in task.items() if value is not None}
        self._replace_active_task(session_id, task)
        self._record_active_task_progress(session_id, task)

    def _update_active_task(
        self,
        session_id: str,
        *,
        status: str,
    ) -> None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        task = (session.metadata_json or {}).get("active_task")
        if not isinstance(task, dict):
            return
        updated = {**task, "status": status, "updated_at": _utc_now_iso()}
        self._replace_active_task(session_id, updated)
        self._record_active_task_progress(session_id, updated)

    def _mark_active_task_cancelled(self, session_id: str) -> None:
        self._update_active_task(session_id, status="cancelled")

    def _clear_active_task(self, session_id: str) -> None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        metadata = dict(session.metadata_json or {})
        if "active_task" not in metadata:
            return
        metadata.pop("active_task", None)
        self._replace_session_metadata(session_id, metadata)
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.CHAT_PROGRESS_RECORDED,
            payload={"progress_kind": "active_task_cleared"},
        )

    def _replace_active_task(self, session_id: str, active_task: dict[str, Any]) -> None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        metadata = dict(session.metadata_json or {})
        metadata["active_task"] = redact_sensitive_payload(active_task)
        self._replace_session_metadata(session_id, metadata)

    def _record_active_task_progress(
        self,
        session_id: str,
        active_task: dict[str, Any],
    ) -> None:
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.CHAT_PROGRESS_RECORDED,
            payload={
                "progress_kind": "active_task_updated",
                "active_task": redact_sensitive_payload(active_task),
            },
        )

    def _replace_session_metadata(
        self,
        session_id: str,
        metadata: dict[str, Any],
    ) -> None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        session.metadata_json = metadata
        session.status = ConversationStatus.TASK_INTAKE.value
        self._repo.session.commit()
        self._repo.session.refresh(session)

    def _match_session_action(
        self,
        session_id: str,
        raw_input: str,
        *,
        intake: ConversationIntakeResult | None = None,
    ) -> dict[str, Any] | None:
        normalized = raw_input.strip()
        user_url = _extract_url(normalized)
        candidates = self._matching_session_actions(
            session_id,
            normalized,
            intake=intake,
        )

        if not candidates:
            return None

        if user_url:
            normalized_url = _normalize_url(user_url)
            url_matches = [
                action
                for action in candidates
                if _normalize_url(action.get("target_url")) == normalized_url
            ]
            if len(url_matches) == 1:
                return url_matches[0]
            return None

        if len(candidates) == 1:
            return candidates[0]

        return None

    def _matching_session_actions(
        self,
        session_id: str,
        raw_input: str,
        *,
        intake: ConversationIntakeResult | None = None,
    ) -> list[dict[str, Any]]:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        actions = [
            action
            for action in list((session.metadata_json or {}).get("learned_actions") or [])
            if isinstance(action, dict)
        ]
        normalized = raw_input.strip()
        user_url = _extract_url(normalized)
        candidates = _matching_actions(actions, normalized, intake=intake)
        if not candidates and _looks_like_vague_operation_request(normalized):
            candidates = _scope_actions_for_vague_request(actions, intake=intake)
        if user_url:
            normalized_url = _normalize_url(user_url)
            candidates = [
                action
                for action in candidates
                if _normalize_url(action.get("target_url")) == normalized_url
            ]
        return candidates

    def _maybe_apply_eval_candidate_setup(
        self,
        *,
        session_id: str,
        metadata: dict[str, Any] | None,
        events: list[str],
    ) -> bool:
        setup = self._valid_eval_candidate_setup(session_id, metadata)
        if setup is None:
            return False
        self._bind_eval_candidate_actions(session_id, setup)
        aliases = [str(action.get("alias") or "") for action in setup["actions"]]
        self._append_event(
            session_id,
            ConversationEventType.CHAT_PROGRESS_RECORDED,
            {
                "progress_kind": "eval_candidate_setup_applied",
                "case_id": _EVAL_PENDING_CHOICE_CASE_ID,
                "setup_type": setup["setup_type"],
                "candidate_count": len(setup["actions"]),
                "aliases": aliases,
                "path_hashes": [
                    _redacted_id_hash(str(action.get("learned_path_id") or ""))
                    for action in setup["actions"]
                ],
                "live_multi_action_capability": setup["live_multi_action_capability"],
            },
            events,
        )
        return True

    def _valid_eval_candidate_setup(
        self,
        session_id: str,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        dispatch_metadata = metadata or {}
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        session_metadata = session.metadata_json or {}
        client = dispatch_metadata.get("client") or session_metadata.get("client")
        raw_setup = dispatch_metadata.get("eval_candidate_setup")
        if client != "wagent_eval" or not isinstance(raw_setup, dict):
            return None
        if raw_setup.get("case_id") != _EVAL_PENDING_CHOICE_CASE_ID:
            return None
        setup_type = raw_setup.get("setup_type")
        if setup_type not in _EVAL_CANDIDATE_SETUP_TYPES:
            return None
        raw_actions = raw_setup.get("actions")
        if not isinstance(raw_actions, list) or len(raw_actions) < 3:
            return None
        existing_actions = [
            action
            for action in session_metadata.get("learned_actions") or []
            if isinstance(action, dict)
        ]
        existing_by_path = {
            str(action.get("learned_path_id") or ""): action
            for action in existing_actions
            if action.get("learned_path_id")
        }
        bound_actions: list[dict[str, Any]] = []
        for raw_action in raw_actions:
            if not isinstance(raw_action, dict):
                return None
            alias = str(raw_action.get("alias") or "").strip()
            learned_path_id = str(raw_action.get("learned_path_id") or "").strip()
            existing = existing_by_path.get(learned_path_id)
            if not alias or existing is None:
                return None
            if LearnedPathRepository(self._repo.session).get(learned_path_id) is None:
                return None
            bound_actions.append(
                {
                    "choice_id": str(raw_action.get("choice_id") or ""),
                    "alias": alias,
                    "utterances": [alias, f"帮我{alias}"],
                    "learned_path_id": learned_path_id,
                    "target_url": existing.get("target_url"),
                    "site_origin": existing.get("site_origin"),
                    "page_template": existing.get("page_template"),
                    "scenario": existing.get("scenario"),
                }
            )
        return {
            "setup_type": str(setup_type),
            "live_multi_action_capability": bool(
                raw_setup.get("live_multi_action_capability", False)
            ),
            "actions": bound_actions,
        }

    def _bind_eval_candidate_actions(
        self,
        session_id: str,
        setup: dict[str, Any],
    ) -> None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        metadata = dict(session.metadata_json or {})
        existing = [
            action for action in metadata.get("learned_actions") or [] if isinstance(action, dict)
        ]
        setup_actions = [
            action for action in setup.get("actions") or [] if isinstance(action, dict)
        ]
        setup_keys = {_action_scope_key(action) for action in setup_actions}
        metadata["learned_actions"] = [
            action for action in existing if _action_scope_key(action) not in setup_keys
        ] + setup_actions
        self._replace_session_metadata(session_id, metadata)

    def _learned_action_by_path_id(
        self,
        session_id: str,
        learned_path_id: str,
    ) -> dict[str, Any] | None:
        if not learned_path_id:
            return None
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        for action in (session.metadata_json or {}).get("learned_actions") or []:
            if (
                isinstance(action, dict)
                and str(action.get("learned_path_id") or "") == learned_path_id
            ):
                return action
        return None

    def _action_from_private_choice(self, selected: dict[str, Any]) -> dict[str, Any] | None:
        learned_path_id = str(selected.get("learned_path_id") or "").strip()
        if not learned_path_id:
            return None
        row = LearnedPathRepository(self._repo.session).get(learned_path_id)
        if row is None:
            return None
        target_url = str(selected.get("target_url") or "").strip()
        parsed = urlparse(target_url)
        site_origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme else parsed.netloc
        alias = str(selected.get("action_alias") or "").strip() or str(row.scenario or "")
        return {
            "alias": alias or "已学习操作",
            "utterances": [alias] if alias else [],
            "learned_path_id": learned_path_id,
            "target_url": target_url,
            "site_origin": site_origin,
            "page_template": selected.get("page_template") or row.page_template,
            "scenario": row.scenario,
        }

    def _has_pending_runtime_context(self, session_id: str) -> bool:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        metadata = session.metadata_json or {}
        return any(
            key in metadata
            for key in (
                "pending_intake",
                "pending_target",
                "pending_choice",
                "active_task",
            )
        )

    def _has_learned_target(self, session_id: str, url: str) -> bool:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        normalized_url = _normalize_url(url)
        actions = list((session.metadata_json or {}).get("learned_actions") or [])
        return any(_normalize_url(action.get("target_url")) == normalized_url for action in actions)

    def _has_ambiguous_action_match(self, session_id: str, raw_input: str) -> bool:
        if _extract_url(raw_input):
            return False
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        actions = list((session.metadata_json or {}).get("learned_actions") or [])
        intake = self._intake_service.analyze(
            raw_input,
            session_metadata=session.metadata_json or {},
        )
        return len(_matching_actions(actions, raw_input.strip(), intake=intake)) > 1

    def _result(
        self,
        *,
        session_id: str,
        command_kind: str,
        user_response: str,
        events: list[str],
        message_id: str | None,
        previous_status: str,
        allowed: bool = True,
        error: str | None = None,
        replay_result: ConversationReplaySummary | None = None,
    ) -> DispatchResult:
        self._repo.update_session_status(
            session_id=session_id,
            status=ConversationStatus.TASK_INTAKE,
        )
        return DispatchResult(
            session_id=session_id,
            previous_status=previous_status,
            next_status=ConversationStatus.TASK_INTAKE.value,
            command_kind=command_kind,
            user_response=user_response,
            events_appended=events,
            message_id=message_id,
            allowed=allowed,
            error=error,
            replay_result=replay_result,
        )


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _valid_pending_choice_payload(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if value.get("type") != "pending_choice":
        return False
    choices = value.get("choices")
    if not isinstance(choices, list) or not choices:
        return False
    return all(
        isinstance(choice, dict)
        and isinstance(choice.get("choice_id"), str)
        and isinstance(choice.get("label"), str)
        for choice in choices
    )


def _build_pending_choice(
    candidates: list[dict[str, Any]],
    *,
    slot_overrides: dict[str, str] | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    choices: list[dict[str, Any]] = []
    private_map: dict[str, dict[str, Any]] = {}
    for index, action in enumerate(candidates[: len(_CHOICE_IDS)]):
        choice_id = _CHOICE_IDS[index]
        choices.append(
            {
                "choice_id": choice_id,
                "label": _choice_label(action),
                "description": _choice_description(action),
                "intent": "execute_operation",
            }
        )
        private_map[choice_id] = {
            "kind": "learned_action",
            "learned_path_id": action.get("learned_path_id"),
            "action_alias": action.get("alias"),
            "target_url": action.get("target_url"),
            "page_template": action.get("page_template"),
        }
        if slot_overrides:
            private_map[choice_id]["slot_overrides"] = dict(slot_overrides)
    pending_choice = {
        "type": "pending_choice",
        "choice_group_id": f"choice-group-{uuid.uuid4()}",
        "question": "我找到了多个可能的操作，你想让我执行哪一个？",
        "choices": choices,
        "turns_remaining": 2,
        "created_at": _utc_now_iso(),
    }
    return pending_choice, private_map


def _build_task_intent_for_planner(
    raw_input: str,
    intake: ConversationIntakeResult | None,
    *,
    target_url: str | None,
) -> TaskIntent:
    normalized_goal = None
    scenario_hint = None
    target_page_hint = target_url
    if intake is not None:
        normalized_goal = intake.action.canonical_goal or intake.action.goal
        scenario_hint = intake.action.canonical_goal or intake.action.goal
        target_page_hint = intake.target.url or intake.target.page_hint or target_url
    uncertainty: list[str] = []
    if _looks_like_vague_operation_request(raw_input):
        uncertainty.append("vague_goal")
    return TaskIntent(
        raw_text=raw_input,
        normalized_goal=normalized_goal,
        normalization_source="deterministic" if normalized_goal else "none",
        target_page_hint=target_page_hint,
        scenario_hint=scenario_hint,
        uncertainty=uncertainty,
    )


def _planner_candidates_from_session_actions(
    actions: list[dict[str, Any]],
    *,
    learned_path_repo: LearnedPathRepository,
) -> list[LearnedPathCandidate]:
    candidates: list[LearnedPathCandidate] = []
    seen: set[str] = set()
    for action in actions:
        learned_path_id = str(action.get("learned_path_id") or "").strip()
        if not learned_path_id or learned_path_id in seen:
            continue
        seen.add(learned_path_id)
        row = learned_path_repo.get(learned_path_id)
        trust = str(getattr(row, "trust", None) or "provisional")
        if trust not in {"provisional", "confirmed", "flaky", "deprecated"}:
            trust = "provisional"
        if trust == "deprecated":
            continue
        page_template = (
            str(getattr(row, "page_template", "") or "")
            or str(action.get("page_template") or "")
            or _path_template_from_url(action.get("target_url"))
        )
        scenario = (
            str(getattr(row, "scenario", "") or "")
            or str(action.get("scenario") or "")
            or str(action.get("alias") or "")
            or page_template
            or "session_action"
        )
        match_reasons = _planner_candidate_match_reasons(action, page_template)
        warnings: list[str] = []
        trust_reason = getattr(row, "trust_reason", None) if row is not None else None
        if trust_reason:
            warnings.append(str(trust_reason))
        if row is None:
            warnings.append(
                "Session learned action metadata used because LearnedPath row was unavailable."
            )
        candidates.append(
            LearnedPathCandidate(
                learned_path_id=learned_path_id,
                scenario=scenario,
                page_template=page_template or "/",
                trust=trust,  # type: ignore[arg-type]
                hit_count=int(getattr(row, "hit_count", 0) or 0),
                match_reasons=match_reasons,
                warnings=warnings,
                drift_evidence_summary=trust_reason if trust == "flaky" else None,
            )
        )
    return candidates


def _planner_candidate_match_reasons(
    action: dict[str, Any],
    page_template: str,
) -> list[str]:
    reasons: list[str] = []
    alias = str(action.get("alias") or "").strip()
    if alias:
        reasons.append(f"Session action alias: {alias}")
    scenario = str(action.get("scenario") or "").strip()
    if scenario:
        reasons.append(f"Session scenario: {scenario}")
    if page_template:
        reasons.append(f"Session page: {page_template}")
    return reasons


def _path_template_from_url(value: Any) -> str:
    parsed = urlparse(str(value or ""))
    return parsed.path.rstrip("/") or parsed.path or "/"


def _build_planner_pending_choice(
    candidates: list[dict[str, Any]],
    *,
    slot_overrides: dict[str, str] | None,
    planner_output: AgentDPlannerOutput,
    top_choice_index: int,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    planner_summary = _planner_summary(
        planner_output,
        candidate_index=top_choice_index,
    )
    choices: list[dict[str, Any]] = []
    private_map: dict[str, dict[str, Any]] = {}
    for index, action in enumerate(candidates[: len(_CHOICE_IDS)]):
        choice_id = _CHOICE_IDS[index]
        description = _choice_description(action)
        if index == top_choice_index:
            description = _planner_choice_description(
                description,
                planner_summary=planner_summary,
            )
        choice = {
            "choice_id": choice_id,
            "label": _choice_label(action),
            "description": description,
            "intent": "execute_operation",
        }
        choices.append({key: value for key, value in choice.items() if value is not None})
        private_choice: dict[str, Any] = {
            "kind": "planner_route_choice",
            "learned_path_id": action.get("learned_path_id"),
            "target_url": action.get("target_url"),
            "action_alias": action.get("alias"),
            "page_template": action.get("page_template"),
            "planner_summary": (
                planner_summary if index == top_choice_index else {"candidate_index": index}
            ),
        }
        if slot_overrides:
            private_choice["slot_overrides"] = dict(slot_overrides)
        private_map[choice_id] = private_choice
    pending_choice = {
        "type": "pending_choice",
        "choice_group_id": f"choice-group-{uuid.uuid4()}",
        "question": "我找到了多个可能的操作，你想让我执行哪一个？",
        "choices": choices,
        "turns_remaining": 2,
        "created_at": _utc_now_iso(),
    }
    return pending_choice, private_map


def _planner_summary(
    planner_output: AgentDPlannerOutput,
    *,
    candidate_index: int,
) -> dict[str, Any]:
    route_plan = planner_output.route_plan
    purpose = None
    confirmation_required = bool(planner_output.confirmation_requirements)
    if route_plan is not None:
        confirmation_required = confirmation_required or bool(route_plan.confirmation_required)
        if route_plan.steps:
            purpose = _sanitize_planner_text(route_plan.steps[0].purpose)
    return {
        "candidate_index": candidate_index,
        "purpose": purpose,
        "confirmation_required": confirmation_required,
        "warnings": [
            _sanitize_planner_text(item)
            for item in planner_output.warnings[:3]
            if _sanitize_planner_text(item)
        ],
        "risk_hints": [
            {
                "type": _sanitize_planner_text(getattr(item, "risk_type", "")),
                "reason": _sanitize_planner_text(getattr(item, "reason", "")),
                "severity": _sanitize_planner_text(getattr(item, "severity", "")),
            }
            for item in planner_output.risk_hints[:3]
        ],
        "uncertainty": [
            _sanitize_planner_text(item)
            for item in planner_output.uncertainty[:3]
            if _sanitize_planner_text(item)
        ],
    }


def _planner_choice_description(
    base_description: str | None,
    *,
    planner_summary: dict[str, Any],
) -> str | None:
    parts = [base_description] if base_description else []
    warnings = planner_summary.get("warnings")
    uncertainty = planner_summary.get("uncertainty")
    risk_hints = planner_summary.get("risk_hints")
    if planner_summary.get("confirmation_required"):
        parts.append("需要你确认后执行")
    if isinstance(warnings, list) and warnings:
        parts.append("存在 Planner 警告")
    if isinstance(risk_hints, list) and risk_hints:
        parts.append("存在风险提示")
    if isinstance(uncertainty, list) and uncertainty:
        parts.append("存在不确定性")
    return " · ".join(parts) if parts else None


def _planner_choice_created_event_payload(
    pending_choice: dict[str, Any],
    *,
    planner_output: AgentDPlannerOutput,
    candidate_count: int,
) -> dict[str, Any]:
    route_plan = planner_output.route_plan
    return {
        "progress_kind": "planner_choice_created",
        "candidate_count": candidate_count,
        "choice_group_id": pending_choice.get("choice_group_id"),
        "confirmation_required": bool(
            planner_output.confirmation_requirements
            or (route_plan and route_plan.confirmation_required)
        ),
        "planner_warning_count": len(planner_output.warnings),
        "planner_risk_count": len(planner_output.risk_hints),
        "uncertainty_count": len(planner_output.uncertainty),
    }


def _sanitize_planner_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return re.sub(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        "[internal-id]",
        text,
        flags=re.I,
    )


def _count_summary_items(summary: Any, key: str) -> int:
    if not isinstance(summary, dict):
        return 0
    value = summary.get(key)
    return len(value) if isinstance(value, list) else 0


def _build_recovery_pending_choice(
    *,
    action: dict[str, Any],
    slot_overrides: dict[str, str],
    evidence_targets: list[ExecutionEvidenceTarget],
    failure_class: str,
    retry_count: int,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    retry_description = (
        "重试会再次执行该操作，可能重复新增 / 提交。"
        if failure_class in _RECOVERY_SIDE_EFFECT_CLASSES
        else None
    )
    choices = [
        {
            "choice_id": "A",
            "label": "重试执行该操作",
            "description": retry_description,
            "intent": "execute_operation",
        },
        {
            "choice_id": "B",
            "label": "重新学习",
            "intent": "learn_operation",
        },
        {"choice_id": "C", "label": "取消", "intent": "cancel"},
    ]
    choices = [
        {key: value for key, value in choice.items() if value is not None} for choice in choices
    ]
    fill_values = {key: value for key, value in slot_overrides.items() if key and value is not None}
    private_map: dict[str, dict[str, Any]] = {
        "A": {
            "kind": "retry_replay",
            "learned_path_id": action.get("learned_path_id"),
            "target_url": action.get("target_url"),
            "action_alias": action.get("alias"),
            "slot_overrides": dict(slot_overrides),
            "evidence_targets": [target.model_dump(mode="json") for target in evidence_targets],
            "retry_count": retry_count,
            "failure_reason": failure_class,
        },
        "B": {
            "kind": "relearn_operation",
            "target_url": action.get("target_url"),
            "action_alias": action.get("alias"),
            "fill_values": fill_values,
            "failure_reason": failure_class,
        },
        "C": {"kind": "cancel", "failure_reason": failure_class},
    }
    pending_choice = {
        "type": "pending_choice",
        "choice_group_id": f"choice-group-{uuid.uuid4()}",
        "question": "你可以选择：",
        "choices": choices,
        "turns_remaining": 2,
        "created_at": _utc_now_iso(),
    }
    return pending_choice, private_map


def _retry_count_from_replay_summary(replay_summary: ConversationReplaySummary) -> int:
    retry_count = getattr(replay_summary, "retry_count", None)
    if isinstance(retry_count, int):
        return max(retry_count, 0)
    return 0


def _slot_overrides_from_choice_selection(selected: dict[str, Any]) -> dict[str, str]:
    slot_overrides = selected.get("slot_overrides")
    if not isinstance(slot_overrides, dict):
        return {}
    return {
        str(key): str(value) for key, value in slot_overrides.items() if key and value is not None
    }


def _slot_overrides_from_pending_choice_clarification(raw_input: str) -> dict[str, str]:
    values = _parse_product_inputs(raw_input) or {}
    item_name = values.get("item_name")
    return {"item_name": item_name} if item_name else {}


def _fill_values_from_recovery_choice(selected: dict[str, Any]) -> dict[str, str]:
    fill_values = selected.get("fill_values")
    if not isinstance(fill_values, dict):
        return {}
    return {str(key): str(value) for key, value in fill_values.items() if key and value is not None}


def _choice_label(action: dict[str, Any]) -> str:
    return str(action.get("alias") or action.get("page_template") or "网页操作")


def _choice_description(action: dict[str, Any]) -> str | None:
    target_url = action.get("target_url")
    page_template = action.get("page_template")
    if target_url and page_template:
        return f"{page_template} · {target_url}"
    if target_url:
        return str(target_url)
    return str(page_template) if page_template else None


def _pending_choice_response(
    pending_choice: dict[str, Any],
    *,
    prefix: str | None = None,
) -> str:
    lines: list[str] = []
    if prefix:
        lines.append(prefix)
    lines.append(str(pending_choice.get("question") or "你想让我执行哪一个？"))
    for choice in pending_choice.get("choices") or []:
        if not isinstance(choice, dict):
            continue
        label = str(choice.get("label") or "")
        description = choice.get("description")
        suffix = f" - {description}" if description else ""
        lines.append(f"{choice.get('choice_id')}. {label}{suffix}")
    lines.append("请回复 A、1 或选项名称。")
    return "\n".join(lines)


def _parse_choice_reply(raw_input: str, pending_choice: dict[str, Any]) -> str | None:
    text = raw_input.strip()
    if not text:
        return None
    choices = [
        choice
        for choice in pending_choice.get("choices") or []
        if isinstance(choice, dict) and choice.get("choice_id")
    ]
    by_id = {str(choice["choice_id"]).upper(): str(choice["choice_id"]) for choice in choices}
    upper = text.upper()
    if upper in by_id:
        return by_id[upper]
    if text.isdigit():
        index = int(text) - 1
        if 0 <= index < len(choices):
            return str(choices[index]["choice_id"])
    ordinal = _chinese_ordinal_index(text)
    if ordinal is not None and 0 <= ordinal < len(choices):
        return str(choices[ordinal]["choice_id"])
    for choice in choices:
        if text == str(choice.get("choice_id")):
            return str(choice["choice_id"])
    normalized_text = _normalize_choice_text(text)
    for choice in choices:
        label = str(choice.get("label") or "")
        if normalized_text and normalized_text == _normalize_choice_text(label):
            return str(choice["choice_id"])
    return None


def _chinese_ordinal_index(text: str) -> int | None:
    mapping = {
        "第一个": 0,
        "第一项": 0,
        "第1个": 0,
        "第1项": 0,
        "第二个": 1,
        "第二项": 1,
        "第2个": 1,
        "第2项": 1,
        "第三个": 2,
        "第三项": 2,
        "第3个": 2,
        "第3项": 2,
        "第四个": 3,
        "第四项": 3,
        "第4个": 3,
        "第4项": 3,
    }
    return mapping.get(text.strip())


def _normalize_choice_text(text: str) -> str:
    return re.sub(r"[\s，。,.；;:：!！?？、\-_/]+", "", text).lower()


def _looks_like_choice_revision(text: str) -> bool:
    stripped = text.strip()
    if _extract_url(stripped):
        return True
    return any(
        token in stripped
        for token in (
            "不是",
            "不对",
            "我要",
            "我想",
            "换成",
            "改成",
            "重新",
        )
    )


def _is_cancel_text(text: str) -> bool:
    stripped = text.strip().lower()
    return stripped in {
        "/cancel",
        "cancel",
        "stop",
        "算了",
        "取消",
        "不用了",
        "不要了",
        "先取消",
        "停止",
    }


def _extract_url(text: str) -> str | None:
    match = _URL_RE.search(text)
    return match.group(0) if match else None


def _is_bare_url_input(raw_input: str, target_url: str | None) -> bool:
    text = raw_input.strip()
    if not text or not target_url:
        return False
    return _normalize_url(text) == _normalize_url(target_url)


def _chat_intent_from_intake(
    raw_input: str,
    intake: ConversationIntakeResult,
) -> ChatIntent:
    if intake.intent == "learn_operation":
        return ChatIntent(
            kind="learn_page",
            raw_text=raw_input,
            url=intake.target.url,
        )
    if intake.intent == "execute_operation":
        return ChatIntent(
            kind="execute_task",
            raw_text=raw_input,
            url=intake.target.url,
        )
    if intake.intent == "provide_missing_info":
        return ChatIntent(
            kind="learn_page",
            raw_text=raw_input,
            url=intake.target.url,
        )
    return parse_chat_intent(raw_input)


def _fill_values_from_intake(
    intake: ConversationIntakeResult | None,
) -> dict[str, str] | None:
    if intake is None:
        return None
    values: dict[str, str] = {}
    for slot in intake.slots:
        semantic_type = "item_name" if slot.semantic_type == "project_name" else slot.semantic_type
        if slot.value and semantic_type in {"username", "password", "item_name"}:
            values[semantic_type] = slot.value
    return values or None


def _slot_overrides_from_fill_values(fill_values: dict[str, str]) -> dict[str, str]:
    item_name = fill_values.get("item_name")
    return {"item_name": item_name} if item_name else {}


def _learned_path_supports_value_slot(path: Any | None, slot_name: str) -> bool | None:
    if path is None:
        return None
    for raw_action in path.actions or []:
        if (
            isinstance(raw_action, dict)
            and str(raw_action.get("action_type") or "").lower() == "fill"
            and raw_action.get("value_slot") == slot_name
        ):
            return True
    return False


def _parse_product_inputs(text: str) -> dict[str, str] | None:
    """Extract credential-like inputs from user utterance for product-level learning."""
    values: dict[str, str] = {}
    for label in ("操作员账号", "用户名", "账号"):
        m = re.search(rf"{label}[是为]?\s*[:：]?\s*{_VALUE_PATTERN}", text)
        if m:
            values["username"] = m.group(1)
            break
    for label in ("访问口令", "登录口令", "密码"):
        m = re.search(rf"{label}[是为]?\s*[:：]?\s*{_VALUE_PATTERN}", text)
        if m:
            values["password"] = m.group(1)
            break
    item_name = _parse_item_name_input(text)
    if item_name:
        values["item_name"] = item_name
    return values if values else None


def _parse_item_name_input(text: str) -> str | None:
    for label in ("项目名称", "项目名", "名称", "name"):
        if label == "name":
            label_pattern = r"(?<![A-Za-z0-9_])name(?![A-Za-z0-9_])"
        else:
            label_pattern = re.escape(label)
        match = re.search(
            rf"{label_pattern}\s*(?:叫|是|为|=|:|：)?\s*{_VALUE_PATTERN}",
            text,
            re.I,
        )
        if not match:
            continue
        value = match.group(1)
        if label in ("项目名称", "项目名") or "项目" in value:
            return value
    if "名称" in text or "项目名" in text or "name" in text.lower():
        return None
    match = re.search(
        rf"(?:新增|创建|添加)\s*(?!项目(?:$|[\s，。,.；;!！?？])){_VALUE_PATTERN}",
        text,
        re.I,
    )
    return match.group(1) if match else None


def _question_for_missing_fields(intake: ConversationIntakeResult) -> str:
    if intake.ask_user_message_hint:
        return intake.ask_user_message_hint
    names = [field.display_name for field in intake.missing_fields]
    if names:
        return "我需要" + "、".join(names) + "。"
    return "我还需要补充信息后才能继续。"


def _merge_pending_intake(
    session_id: str,
    pending: dict[str, Any],
    intake: ConversationIntakeResult,
) -> ConversationIntakeResult:
    target_payload = dict(pending.get("target") or {})
    if intake.target.url:
        target_payload.update(intake.target.model_dump(mode="json", exclude_none=True))
    action_payload = dict(pending.get("action") or {})
    action_payload.update(intake.action.model_dump(mode="json", exclude_none=True))

    slots_by_type: dict[str, ConversationIntakeSlot] = {}
    missing_sensitive_from_runtime: set[str] = set()
    for slot_payload in pending.get("slots") or []:
        try:
            slot = ConversationIntakeSlot.model_validate(slot_payload)
        except ValueError:
            continue
        if slot.value and slot.value != "[REDACTED]":
            slots_by_type[slot.semantic_type] = slot
        elif slot.value == "[REDACTED]":
            sensitive_value = (_PENDING_SENSITIVE_VALUES.get(session_id) or {}).get(
                slot.semantic_type
            )
            if sensitive_value:
                slots_by_type[slot.semantic_type] = slot.model_copy(
                    update={"value": sensitive_value}
                )
            elif slot.sensitive:
                missing_sensitive_from_runtime.add(slot.semantic_type)
    for slot in intake.slots:
        if slot.value:
            slots_by_type[slot.semantic_type] = slot
            missing_sensitive_from_runtime.discard(slot.semantic_type)

    missing = {
        semantic_type
        for semantic_type in (pending.get("missing_fields") or [])
        if semantic_type not in slots_by_type
    }
    missing.update(missing_sensitive_from_runtime)

    return ConversationIntakeResult(
        intent="learn_operation",
        target=target_payload,
        action=action_payload,
        slots=list(slots_by_type.values()),
        missing_fields=[
            {
                "semantic_type": semantic_type,
                "display_name": _display_name_for_missing_field(semantic_type),
            }
            for semantic_type in sorted(missing)
        ],
        confidence=max(intake.confidence, 0.78),
        should_ask_user=bool(missing),
        ask_user_message_hint=None,
        source=intake.source,
    )


def _display_name_for_missing_field(semantic_type: str) -> str:
    if semantic_type == "username":
        return "用户名或账号"
    if semantic_type == "password":
        return "密码或口令"
    return semantic_type


def _action_from_learning_result(result: LearningRunResult) -> dict[str, Any]:
    parsed = urlparse(result.target_url or "")
    return {
        "alias": result.action_label,
        "utterances": result.suggested_utterances,
        "learned_path_id": result.learned_path_id,
        "target_url": result.target_url,
        "site_origin": f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme else parsed.netloc,
        "page_template": result.page_template,
        "scenario": result.scenario,
    }


def _normalize_url(url: str | None) -> str:
    if not url:
        return ""
    value = url.strip()
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return value.rstrip("/")
    path = parsed.path.rstrip("/") or "/"
    normalized = parsed._replace(path=path, fragment="")
    return normalized.geturl()


def _redacted_id_hash(value: str) -> str:
    if not value:
        return "sha256:"
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()[:12]


def _action_scope_key(action: dict[str, Any]) -> tuple[str, str]:
    return (str(action.get("alias") or ""), _normalize_url(action.get("target_url")))


def _matching_actions(
    actions: list[dict[str, Any]],
    normalized_input: str,
    *,
    intake: ConversationIntakeResult | None = None,
) -> list[dict[str, Any]]:
    intake_terms = _intake_match_terms(intake)
    candidates: list[dict[str, Any]] = []
    for action in actions:
        utterances = action.get("utterances") or []
        alias = action.get("alias") or ""
        action_terms = {str(item) for item in utterances if item}
        if alias:
            action_terms.add(str(alias))
        if (
            normalized_input in action_terms
            or (alias and alias in normalized_input)
            or (intake_terms and action_terms.intersection(intake_terms))
        ):
            candidates.append(action)
    return candidates


def _looks_like_vague_operation_request(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    return any(
        token in stripped
        for token in (
            "处理",
            "搞一下",
            "弄一下",
            "继续",
            "这个页面",
            "当前页面",
            "this page",
        )
    )


def _scope_actions_for_vague_request(
    actions: list[dict[str, Any]],
    *,
    intake: ConversationIntakeResult | None = None,
) -> list[dict[str, Any]]:
    target_url = intake.target.url if intake else None
    if target_url:
        scoped = [
            action
            for action in actions
            if _normalize_url(action.get("target_url")) == _normalize_url(target_url)
        ]
        if scoped:
            return scoped
    return actions


def _looks_like_active_task_continuation(text: str) -> bool:
    return text.strip() in {"继续", "继续执行", "接着", "接着做", "下一步"}


def _intake_match_terms(intake: ConversationIntakeResult | None) -> set[str]:
    if intake is None:
        return set()
    terms = set(intake.action.aliases)
    if intake.action.goal:
        terms.add(intake.action.goal)
    if intake.action.canonical_goal:
        terms.add(intake.action.canonical_goal)
    return {term for term in terms if term}
