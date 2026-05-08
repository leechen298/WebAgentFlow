"""Pure state transition helpers for M11.0 runtime conversation."""

from __future__ import annotations

from app.schemas.conversation import (
    ConversationCommand,
    ConversationCommandKind,
    ConversationEventType,
    ConversationStatus,
    ConversationTransitionResult,
)

_TERMINAL_STATUSES = frozenset(
    {
        ConversationStatus.COMPLETED,
        ConversationStatus.FAILED,
    }
)

_NON_TERMINAL_STATUSES = frozenset(set(ConversationStatus) - set(_TERMINAL_STATUSES))


def next_state(
    current_status: ConversationStatus,
    command: ConversationCommand,
) -> ConversationTransitionResult:
    """Return the next conversation state without performing side effects."""

    if command.kind == ConversationCommandKind.STATUS:
        return _allowed(
            current_status,
            ConversationEventType.COMMAND_PARSED,
            "Current conversation status is available.",
        )

    if command.kind == ConversationCommandKind.ERROR:
        return _blocked(current_status, command.error or "Command parse error.")

    if current_status in _TERMINAL_STATUSES:
        return _blocked(current_status, "Conversation is already terminal.")

    if command.kind == ConversationCommandKind.FREE_TEXT:
        if current_status in {ConversationStatus.IDLE, ConversationStatus.TASK_INTAKE}:
            return _allowed(
                ConversationStatus.TASK_INTAKE,
                ConversationEventType.MESSAGE_RECEIVED,
                "Task input recorded.",
            )
        return _blocked(current_status, f"Free text is not accepted from {current_status}.")

    if command.kind == ConversationCommandKind.REPLAY:
        if current_status in {ConversationStatus.IDLE, ConversationStatus.TASK_INTAKE}:
            return _allowed(
                ConversationStatus.REPLAY_REQUESTED,
                ConversationEventType.REPLAY_REQUESTED,
                "Replay command requested.",
            )
        return _blocked(current_status, f"Replay is not allowed from {current_status}.")

    if command.kind == ConversationCommandKind.PAUSE:
        if current_status in {ConversationStatus.TASK_INTAKE, ConversationStatus.REPLAY_RUNNING}:
            return _allowed(
                ConversationStatus.PAUSED,
                ConversationEventType.PAUSE_REQUESTED,
                "Conversation paused.",
            )
        return _blocked(current_status, f"Pause is not allowed from {current_status}.")

    if command.kind == ConversationCommandKind.RESUME:
        if current_status == ConversationStatus.PAUSED:
            return _allowed(
                ConversationStatus.TASK_INTAKE,
                ConversationEventType.RESUME_REQUESTED,
                "Conversation resumed to task intake.",
            )
        return _blocked(current_status, f"Resume is not allowed from {current_status}.")

    if command.kind == ConversationCommandKind.ABORT:
        if current_status in _NON_TERMINAL_STATUSES:
            return _allowed(
                ConversationStatus.ABORT_REQUESTED,
                ConversationEventType.ABORT_REQUESTED,
                "Abort requested.",
            )

    if command.kind == ConversationCommandKind.TAKEOVER:
        if current_status in _NON_TERMINAL_STATUSES:
            return _allowed(
                ConversationStatus.TAKEOVER_REQUESTED,
                ConversationEventType.TAKEOVER_REQUESTED,
                "Takeover requested.",
            )

    if command.kind == ConversationCommandKind.CANCEL:
        if current_status in _NON_TERMINAL_STATUSES:
            return _allowed(
                ConversationStatus.IDLE,
                ConversationEventType.STATE_CHANGED,
                "Conversation cancelled.",
            )

    return _blocked(current_status, f"{command.kind} is not allowed from {current_status}.")


def _allowed(
    next_status: ConversationStatus,
    event_type: ConversationEventType,
    response_hint: str,
) -> ConversationTransitionResult:
    return ConversationTransitionResult(
        next_status=next_status,
        response_hint=response_hint,
        event_type=event_type,
        allowed=True,
    )


def _blocked(
    current_status: ConversationStatus,
    error: str,
) -> ConversationTransitionResult:
    return ConversationTransitionResult(
        next_status=current_status,
        response_hint="Command was not applied.",
        event_type=ConversationEventType.COMMAND_PARSED,
        allowed=False,
        error=error,
    )
