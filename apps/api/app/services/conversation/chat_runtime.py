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
from app.schemas.conversation_intake import (
    ConversationIntakeResult,
    ConversationIntakeSlot,
)
from app.services.conversation.intake import (
    ConversationIntakeService,
    redact_sensitive_payload,
)
from app.services.conversation.orchestrator import DispatchResult
from app.services.conversation.provenance import (
    AGENT_PRODUCER_CONVERSATION_INTAKE,
    CODE_PRODUCER_INTERACTIVE_CHAT,
    agent_response_provenance,
    code_response_provenance,
)
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


def _chat_headless(session: Any) -> bool:
    metadata = session.metadata_json or {}
    return metadata.get("browser_visibility") == "headless"


def parse_chat_intent(raw_input: str) -> ChatIntent:
    text = raw_input.strip()
    if not text:
        return ChatIntent(kind="unknown", raw_text=raw_input)
    url = _extract_url(text)
    lowered = text.lower()
    if url and any(keyword in lowered or keyword in text for keyword in _LEARN_KEYWORDS):
        return ChatIntent(kind="learn_page", raw_text=raw_input, url=url)
    return ChatIntent(kind="execute_task", raw_text=raw_input)


class InteractiveChatRuntime:
    def __init__(
        self,
        repo: ConversationRepository,
        *,
        learning_handler: Any | None = None,
        replay_handler: Any | None = None,
        intake_service: Any | None = None,
    ) -> None:
        self._repo = repo
        self._learning_handler = learning_handler
        self._replay_handler = replay_handler
        self._intake_service = intake_service or ConversationIntakeService()

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
        intake = self._intake_service.analyze(
            raw_input,
            session_metadata=session.metadata_json or {},
        )
        trace_context = self._record_intake_trace(
            session_id,
            fallback=bool(getattr(self._intake_service, "provider_fallback", False)),
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
    ) -> DispatchResult:
        events = self._append_chat_command_event(
            session_id=session_id,
            raw_input=intent.raw_text,
            command_kind="learn_page",
            metadata=metadata,
            intake=intake,
        )

        self._append_agent_message(session_id, "开始学习页面操作。")
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
            if user_url and not self._has_learned_target(session_id, user_url):
                return self._handle_unlearned_target(
                    session_id=session_id,
                    command_kind="execute_task",
                    message_id=message_id,
                    metadata=metadata,
                    existing_events=events,
                    previous_status=previous_status,
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

        self._append_agent_message(session_id, "执行中。")
        self._append_event(
            session_id,
            ConversationEventType.CHAT_EXECUTION_STARTED,
            {
                "learned_path_id": action["learned_path_id"],
                "target_url": action["target_url"],
                "alias": action["alias"],
                "browser_visibility": "headless" if headless else "visible",
            },
            events,
        )
        replay_summary = self._replay_handler(
            action["learned_path_id"],
            action["target_url"],
            headless=headless,
        )
        alias = action.get("alias", "")
        if replay_summary.replay_status in ("succeeded", "observed"):
            final_message = f"{alias}完成。" if alias else "执行完成。"
            event_type = ConversationEventType.CHAT_EXECUTION_COMPLETED
            error = None
            allowed = True
        else:
            final_message = "执行失败。"
            event_type = ConversationEventType.CHAT_EXECUTION_FAILED
            error = replay_summary.error or replay_summary.replay_status
            allowed = False

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

    def _handle_unlearned_target(
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
        self._append_agent_message(session_id, _UNLEARNED_TARGET_RESPONSE)
        self._append_event(
            session_id,
            ConversationEventType.CHAT_NO_PATH,
            {"reason": "unlearned_target_url"},
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
            payload=redact_sensitive_payload(payload),
        )
        return IntakeTraceContext([trace_id], [event.id], fallback=fallback)

    def _trace_event_types(self, trace_context: IntakeTraceContext) -> list[str]:
        if not trace_context.event_ids:
            return []
        return [ConversationEventType.LLM_TRACE_RECORDED.value]

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
        self._replace_session_metadata(session_id, metadata)

    def _clear_pending_intake(self, session_id: str) -> None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        metadata = dict(session.metadata_json or {})
        metadata.pop("pending_intake", None)
        clear_pending_sensitive_values(session_id)
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
        if slot.value and slot.semantic_type in {"username", "password"}:
            values[slot.semantic_type] = slot.value
    return values or None


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
    return values if values else None


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
