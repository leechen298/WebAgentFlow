"""Conversation orchestrator / dispatcher for M11.0.

Pure scheduling skeleton: receives user input, parses commands,
performs state transitions, records messages/events, and returns
user-facing response hints. 11.0.6 adds replay hook integration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.repos.conversation_repo import ConversationRepository
from app.schemas.conversation import (
    ConversationCommandKind,
    ConversationEventType,
    ConversationReplaySummary,
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
    replay_result: ConversationReplaySummary | None = None


class ConversationOrchestrator:
    def __init__(
        self,
        repo: ConversationRepository,
        replay_handler: Any | None = None,
    ) -> None:
        self._repo = repo
        self._replay_handler = replay_handler

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
        7. For replay commands, run the replay hook and record lifecycle.
        8. Return ``DispatchResult``.
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

        next_status_value = transition.next_status.value
        user_response = transition.response_hint
        replay_result: ConversationReplaySummary | None = None

        # 5. Handle allowed transitions
        if transition.allowed:
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

            # 6. Replay hook integration (11.0.6)
            if (
                command.kind == ConversationCommandKind.REPLAY
                and self._replay_handler is not None
            ):
                replay_result, next_status_value = self._execute_replay_hook(
                    session_id=session_id,
                    learned_path_id=command.learned_path_id,
                    url=command.url,
                    current_status=next_status_value,
                )
                events_appended.extend(
                    [
                        ConversationEventType.STATE_CHANGED.value,
                        (
                            ConversationEventType.REPLAY_COMPLETED.value
                            if next_status_value == "completed"
                            else ConversationEventType.REPLAY_FAILED.value
                        ),
                        ConversationEventType.STATE_CHANGED.value,
                    ]
                )
                user_response = (
                    f"Replay completed ({replay_result.replay_status})."
                    if next_status_value == "completed"
                    else f"Replay failed ({replay_result.replay_status})."
                )

        return DispatchResult(
            session_id=session_id,
            previous_status=previous_status,
            next_status=next_status_value,
            command_kind=command.kind.value,
            user_response=user_response,
            events_appended=events_appended,
            message_id=message.id,
            allowed=transition.allowed,
            error=transition.error,
            replay_result=replay_result,
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

    def _execute_replay_hook(
        self,
        session_id: str,
        learned_path_id: str | None,
        url: str | None,
        current_status: str,
    ) -> tuple[ConversationReplaySummary, str]:
        """Execute replay hook and update session status/events.

        Returns ``(summary, final_status)`` where final_status is
        ``completed`` or ``failed``.
        """
        # Move to replay_running
        self._repo.update_session_status(
            session_id=session_id,
            status="replay_running",
        )
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.STATE_CHANGED,
            payload={
                "from": current_status,
                "to": "replay_running",
                "command_kind": "replay",
            },
        )

        # Run replay
        try:
            assert learned_path_id is not None and url is not None
            summary: ConversationReplaySummary = self._replay_handler(
                learned_path_id, url
            )
        except Exception as exc:
            summary = ConversationReplaySummary(
                learned_path_id=learned_path_id or "",
                url=url or "",
                replay_status="runtime_error",
                drift_status="none",
                error=str(exc),
            )

        # Determine final status
        if summary.replay_status in ("succeeded", "observed"):
            final_status = "completed"
            lifecycle_event = ConversationEventType.REPLAY_COMPLETED
        else:
            final_status = "failed"
            lifecycle_event = ConversationEventType.REPLAY_FAILED

        # Move to final status
        self._repo.update_session_status(
            session_id=session_id,
            status=final_status,
        )
        self._repo.append_event(
            session_id=session_id,
            type=ConversationEventType.STATE_CHANGED,
            payload={
                "from": "replay_running",
                "to": final_status,
                "command_kind": "replay",
            },
        )

        # Append replay lifecycle event
        self._repo.append_event(
            session_id=session_id,
            type=lifecycle_event,
            payload=summary.model_dump(mode="json"),
        )

        return summary, final_status
