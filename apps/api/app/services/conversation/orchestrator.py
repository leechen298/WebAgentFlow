"""Conversation orchestrator / dispatcher for M11.0.

Pure scheduling skeleton: receives user input, parses commands,
performs state transitions, records messages/events, and returns
user-facing response hints. No replay side effects, no LLM calls,
no autonomous runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.repos.conversation_repo import ConversationRepository
from app.schemas.conversation import (
    ConversationCommandKind,
    ConversationEventType,
    ConversationStatus,
)
from app.services.conversation.commands import parse_command
from app.services.conversation.state import next_state


@dataclass
class DispatchResult:
    session_id: str
    previous_status: str
    next_status: str
    command_kind: str
    user_response: str
    events_appended: list[str] = field(default_factory=list)
    message_id: str | None = None
    allowed: bool = False
    error: str | None = None
    engine_command: dict[str, Any] | None = None


class ConversationOrchestrator:
    def __init__(self, repo: ConversationRepository) -> None:
        self._repo = repo

    def dispatch_user_input(self, session_id: str, raw_input: str) -> DispatchResult:
        """Dispatch a raw user input through the orchestrator.

        Flow:
        1. Load session (raise ValueError if missing).
        2. Append user message.
        3. Parse command.
        4. Compute next state.
        5. Append ``command_parsed`` audit event.
        6. If transition allowed, update session status and append transition
           / ``state_changed`` events.
        7. Return ``DispatchResult``.
        """
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")

        previous_status = session.status
        current_status = ConversationStatus(previous_status)

        # 1. Record user message
        message = self._repo.append_message(
            session_id=session_id,
            role="user",
            content=raw_input,
        )

        # 2. Parse command
        command = parse_command(raw_input)

        # 3. Compute next state
        transition = next_state(current_status, command)

        # 4. Append command_parsed event
        command_parsed_payload: dict[str, Any] = {
            "raw": raw_input,
            "command_kind": command.kind.value,
            "args": command.args,
            "learned_path_id": command.learned_path_id,
            "url": command.url,
            "text": command.text,
            "parse_error": command.error,
            "allowed": transition.allowed,
            "transition_error": transition.error,
        }
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.COMMAND_PARSED,
            payload=command_parsed_payload,
        )
        events_appended: list[str] = [ConversationEventType.COMMAND_PARSED.value]

        # 5. Handle allowed transitions
        if transition.allowed:
            next_status_value = transition.next_status.value

            if next_status_value != previous_status:
                self._update_session_status(
                    session_id, previous_status, next_status_value, command.kind
                )

            # Append transition event when it is not merely COMMAND_PARSED
            if transition.event_type != ConversationEventType.COMMAND_PARSED:
                transition_payload: dict[str, Any] = {
                    "from": previous_status,
                    "to": next_status_value,
                    "command_kind": command.kind.value,
                    "transition_event_type": transition.event_type.value,
                    "allowed": transition.allowed,
                    "error": transition.error,
                }
                self._repo.append_event(
                    session_id=session_id,
                    type=transition.event_type,
                    payload=transition_payload,
                )
                events_appended.append(transition.event_type.value)

                # Append state_changed when status changed and transition event
                # is not already STATE_CHANGED
                if (
                    next_status_value != previous_status
                    and transition.event_type != ConversationEventType.STATE_CHANGED
                ):
                    state_changed_payload: dict[str, Any] = {
                        "from": previous_status,
                        "to": next_status_value,
                        "command_kind": command.kind.value,
                        "transition_event_type": transition.event_type.value,
                        "allowed": transition.allowed,
                        "error": transition.error,
                    }
                    self._repo.append_event(
                        session_id=session_id,
                        type=ConversationEventType.STATE_CHANGED,
                        payload=state_changed_payload,
                    )
                    events_appended.append(ConversationEventType.STATE_CHANGED.value)

        return DispatchResult(
            session_id=session_id,
            previous_status=previous_status,
            next_status=transition.next_status.value,
            command_kind=command.kind.value,
            user_response=transition.response_hint,
            events_appended=events_appended,
            message_id=message.id,
            allowed=transition.allowed,
            error=transition.error,
        )

    def dispatch_engine_event(
        self,
        session_id: str,
        event_type: ConversationEventType,
        payload: dict[str, Any] | None = None,
    ) -> DispatchResult:
        """Placeholder contract for engine event dispatch.

        11.0.5 records the event but does **not** execute engine side effects,
        browser actions, or Agent routing.
        """
        session = self._repo.get_session(session_id)
        if session is None:
            raise ValueError(f"session not found: {session_id}")

        previous_status = session.status

        self._repo.append_event(
            session_id=session_id,
            type=event_type,
            payload=payload or {},
        )

        return DispatchResult(
            session_id=session_id,
            previous_status=previous_status,
            next_status=previous_status,
            command_kind="engine_event",
            user_response="Engine event received.",
            events_appended=[event_type.value],
            allowed=True,
        )

    def _update_session_status(
        self,
        session_id: str,
        current_status: str,
        next_status: str,
        command_kind: ConversationCommandKind,
    ) -> None:
        """Update session status with special handling for pause/resume/cancel."""
        if command_kind == ConversationCommandKind.PAUSE:
            self._repo.update_session_status(
                session_id=session_id,
                status=next_status,
                previous_status=current_status,
            )
        elif command_kind in {
            ConversationCommandKind.RESUME,
            ConversationCommandKind.CANCEL,
        }:
            self._repo.update_session_status(
                session_id=session_id,
                status=next_status,
                previous_status=None,
            )
        else:
            self._repo.update_session_status(
                session_id=session_id,
                status=next_status,
            )
