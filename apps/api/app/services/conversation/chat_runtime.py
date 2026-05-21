"""Interactive chat happy path for M11.3."""

from __future__ import annotations

import re
from dataclasses import dataclass
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
    ConversationIntakeResult,
    ConversationIntakeSlot,
)
from app.schemas.conversation_router import (
    ApplicationSkillName,
    RouteDecision,
    RouteDecisionKind,
)
from app.schemas.learned_path_replay import ExecutionEvidenceTarget
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

ChatIntentKind = Literal["learn_page", "execute_task", "unknown"]

_URL_RE = re.compile(r"https?://[^\s，。]+")
_LEARN_KEYWORDS = ("学习", "学一下", "learn", "teach")
_NO_PATH_RESPONSE = "还没学过这个操作，需要先学习。"
_UNLEARNED_TARGET_RESPONSE = "还没学过这个站点或页面，需要先学习。"
_AMBIGUOUS_TARGET_RESPONSE = "这个操作在多个站点学过，请带上要操作的页面地址。"
_VALUE_PATTERN = r"([^\s，。,.；;!！?？]+)"
_PENDING_SENSITIVE_VALUES: dict[str, dict[str, str]] = {}


def clear_pending_sensitive_values(session_id: str) -> None:
    _PENDING_SENSITIVE_VALUES.pop(session_id, None)


def clear_pending_runtime_context(repo: ConversationRepository, session_id: str) -> None:
    session = repo.get_session(session_id)
    if session is None:
        raise ValueError(f"session not found: {session_id}")
    metadata = dict(session.metadata_json or {})
    changed = False
    for key in ("pending_intake", "pending_target", "last_no_path_reason"):
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
        item.model_dump(mode="json")
        if hasattr(item, "model_dump")
        else dict(item)
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
            "这个请求不属于当前网页操作范围。你可以提供目标网页 URL，"
            "并说明要学习或执行的页面操作。"
        )
    if category == ConversationEntryGateCategory.NEEDS_CLARIFICATION:
        return (
            "我还需要确认这是不是网页操作任务。请提供目标页面 URL，"
            "或说明要学习/执行的网页操作。"
        )
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
        self._page_understanding_service = (
            page_understanding_service or PageUnderstandingService()
        )

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
                field.semantic_type == "operation_goal"
                for field in route_decision.missing_fields
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
        events = (
            self._trace_event_types(trace_context)
            + self._append_chat_command_event(
                session_id=session_id,
                raw_input="",
                command_kind="unknown",
                metadata=metadata,
                intake=intake,
            )
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
        events = (
            self._trace_event_types(trace_context)
            + self._append_chat_command_event(
                session_id=session_id,
                raw_input="",
                command_kind="learn_page",
                metadata=metadata,
                intake=intake,
            )
        )
        self._save_pending_intake(
            session_id,
            intake,
            message_id,
            turns_remaining=turns_remaining,
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
        response = (
            f"我已查看页面：{page_understanding.observed_page_summary}"
            " 你想让我学习或执行哪个操作？"
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

        self._append_agent_message(session_id, "开始学习页面操作。")
        self._record_skill_call(
            session_id,
            ApplicationSkillName.START_LEARNING,
            status="started",
            input_summary={
                "target_url": intent.url,
                "user_goal": intake.action.goal if intake else None,
                "route_decision": (
                    route_decision.route_decision.value if route_decision else None
                ),
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
            LearnedPathRepository(self._repo.session).get(
                learning_result.learned_path_id
            )
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
                "old_learned_path_id": (
                    old_action.get("learned_path_id") if old_action else None
                ),
                "new_learned_path_id": learning_result.learned_path_id,
                "alias": action["alias"],
                "target_url": action["target_url"],
            },
            events,
        )
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
        action = self._match_session_action(session_id, intent.raw_text, intake=intake)
        if action is None:
            user_url = _extract_url(intent.raw_text)
            if (
                route_decision is not None
                and route_decision.recommended_skill
                == ApplicationSkillName.LEARN_THEN_EXECUTE
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
                    output_summary={
                        "reason": "learning_confirmation_required_before_execution"
                    },
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
            if self._has_ambiguous_action_match(session_id, intent.raw_text):
                return self._handle_ambiguous_target(
                    session_id=session_id,
                    command_kind="execute_task",
                    message_id=message_id,
                    metadata=metadata,
                    existing_events=events,
                    previous_status=previous_status,
                )
            return self._handle_no_path(
                session_id=session_id,
                command_kind="execute_task",
                message_id=message_id,
                metadata=metadata,
                existing_events=events,
                previous_status=previous_status,
            )

        if self._replay_handler is None:
            response = "执行失败：replay handler 未配置。"
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
                command_kind="execute_task",
                user_response=response,
                events=events,
                message_id=message_id,
                previous_status=previous_status,
                allowed=False,
                error="Replay handler is not configured.",
            )

        fill_values = _fill_values_from_intake(intake) or {}
        slot_overrides = _slot_overrides_from_fill_values(fill_values)
        if slot_overrides.get("item_name"):
            path = LearnedPathRepository(self._repo.session).get(
                action["learned_path_id"]
            )
            supports_item_name = _learned_path_supports_value_slot(path, "item_name")
            if supports_item_name is False:
                return self._handle_missing_parameterized_path(
                    session_id=session_id,
                    action=action,
                    slot_overrides=slot_overrides,
                    events=events,
                    message_id=message_id,
                    previous_status=previous_status,
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
        report_blocks_completion = (
            report is not None and report.outcome in {"failed", "blocked"}
        )
        if (
            replay_summary.replay_status in ("succeeded", "observed")
            and not report_blocks_completion
        ):
            if report is not None:
                final_message = _chat_report_user_response(report, slot_overrides)
            else:
                final_message = f"{alias}完成。" if alias else "执行完成。"
            event_type = ConversationEventType.CHAT_EXECUTION_COMPLETED
            error = None
            allowed = True
        else:
            if report is not None:
                final_message = _chat_report_user_response(report, slot_overrides)
            else:
                final_message = "执行失败。"
            event_type = ConversationEventType.CHAT_EXECUTION_FAILED
            error = replay_summary.error or replay_summary.replay_status
            allowed = False

        self._record_skill_call(
            session_id,
            ApplicationSkillName.START_REPLAY,
            status="completed" if allowed else "failed",
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
            command_kind="execute_task",
            user_response="执行中。\n" + final_message,
            events=events,
            message_id=message_id,
            previous_status=previous_status,
            allowed=allowed,
            error=error,
            replay_result=replay_summary,
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
        fallback = (
            trace_context.fallback
            or intake.source in {"provider_error", "provider_parse_error"}
        )
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
        merged = [
            item for item in existing if _action_scope_key(item) != action_key
        ]
        merged.append(action)
        metadata["learned_actions"] = merged
        metadata.pop("pending_intake", None)
        metadata.pop("pending_target", None)
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
            "slots": [
                slot.model_dump(mode="json", exclude_none=True)
                for slot in intake.slots
            ],
            "missing_fields": [
                field.semantic_type for field in intake.missing_fields
            ],
            "created_from_message_id": message_id,
            "turns_remaining": turns_remaining if turns_remaining is not None else 3,
        }
        sensitive_values = {
            slot.semantic_type: slot.value
            for slot in intake.slots
            if slot.sensitive and slot.value
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
        metadata.pop("last_no_path_reason", None)
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
        metadata["pending_target"] = redact_sensitive_payload(
            target.model_dump(mode="json")
        )
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
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        actions = list((session.metadata_json or {}).get("learned_actions") or [])
        normalized = raw_input.strip()
        user_url = _extract_url(normalized)
        candidates = _matching_actions(actions, normalized, intake=intake)

        if not candidates:
            return None

        if user_url:
            normalized_url = _normalize_url(user_url)
            for action in candidates:
                if _normalize_url(action.get("target_url")) == normalized_url:
                    return action
            return None

        if len(candidates) == 1:
            return candidates[0]

        return None

    def _has_learned_target(self, session_id: str, url: str) -> bool:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        normalized_url = _normalize_url(url)
        actions = list((session.metadata_json or {}).get("learned_actions") or [])
        return any(
            _normalize_url(action.get("target_url")) == normalized_url
            for action in actions
        )

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


def _extract_url(text: str) -> str | None:
    match = _URL_RE.search(text)
    return match.group(0) if match else None


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


def _intake_match_terms(intake: ConversationIntakeResult | None) -> set[str]:
    if intake is None:
        return set()
    terms = set(intake.action.aliases)
    if intake.action.goal:
        terms.add(intake.action.goal)
    if intake.action.canonical_goal:
        terms.add(intake.action.canonical_goal)
    return {term for term in terms if term}
