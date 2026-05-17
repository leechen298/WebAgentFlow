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
from app.services.conversation.orchestrator import DispatchResult
from app.services.learning.learning_run_service import LearningRunResult

ChatIntentKind = Literal["learn_page", "execute_task", "unknown"]

_URL_RE = re.compile(r"https?://[^\s，。]+")
_LEARN_KEYWORDS = ("学习", "学一下", "learn", "teach")
_NO_PATH_RESPONSE = "还没学过这个操作，需要先学习。"
_UNLEARNED_TARGET_RESPONSE = "还没学过这个站点或页面，需要先学习。"
_AMBIGUOUS_TARGET_RESPONSE = "这个操作在多个站点学过，请带上要操作的页面地址。"
_VALUE_PATTERN = r"([^\s，。,.；;!！?？]+)"


@dataclass(frozen=True)
class ChatIntent:
    kind: ChatIntentKind
    raw_text: str
    url: str | None = None


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
    ) -> None:
        self._repo = repo
        self._learning_handler = learning_handler
        self._replay_handler = replay_handler

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
        intent = parse_chat_intent(raw_input)
        if intent.kind == "learn_page":
            return self._handle_learn_page(
                session_id=session_id,
                intent=intent,
                message_id=message_id,
                metadata=metadata,
                previous_status=previous_status,
                headless=headless,
            )
        if intent.kind == "execute_task":
            return self._handle_execute_task(
                session_id=session_id,
                intent=intent,
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

    def _handle_learn_page(
        self,
        *,
        session_id: str,
        intent: ChatIntent,
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
            fill_values = _parse_product_inputs(intent.raw_text) if intent.url else None
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
        )
        action = self._match_session_action(session_id, intent.raw_text)
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
    ) -> list[str]:
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.COMMAND_PARSED,
            payload={
                "raw": raw_input,
                "command_kind": command_kind,
                "dispatch_metadata": metadata or {},
                "mode": "interactive_chat",
                "allowed": True,
            },
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

    def _append_agent_message(self, session_id: str, content: str) -> None:
        self._repo.append_message(
            session_id=session_id,
            role="agent",
            content=content,
            metadata={"source": "interactive_chat"},
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
        self._repo.update_session_status(
            session_id=session_id,
            status=ConversationStatus.TASK_INTAKE,
            metadata_patch={"learned_actions": merged},
        )
        return old_action

    def _match_session_action(
        self,
        session_id: str,
        raw_input: str,
    ) -> dict[str, Any] | None:
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")
        actions = list((session.metadata_json or {}).get("learned_actions") or [])
        normalized = raw_input.strip()
        user_url = _extract_url(normalized)
        candidates = _matching_actions(actions, normalized)

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
        return len(_matching_actions(actions, raw_input.strip())) > 1

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
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for action in actions:
        utterances = action.get("utterances") or []
        alias = action.get("alias") or ""
        if normalized_input in utterances or (alias and alias in normalized_input):
            candidates.append(action)
    return candidates
