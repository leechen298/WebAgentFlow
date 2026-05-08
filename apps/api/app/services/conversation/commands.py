"""Slash command parser for M11.0 runtime conversation.

The parser is deliberately pure: it performs no I/O, no API calls, and no
browser or provider interaction.
"""

from __future__ import annotations

from app.schemas.conversation import ConversationCommand, ConversationCommandKind

_SIMPLE_COMMANDS: dict[str, ConversationCommandKind] = {
    "/status": ConversationCommandKind.STATUS,
    "/pause": ConversationCommandKind.PAUSE,
    "/resume": ConversationCommandKind.RESUME,
    "/abort": ConversationCommandKind.ABORT,
    "/takeover": ConversationCommandKind.TAKEOVER,
    "/cancel": ConversationCommandKind.CANCEL,
}

_REPLAY_USAGE = "Usage: /replay <learned_path_id> <url>"


def parse_command(raw: str) -> ConversationCommand:
    """Parse user text into a conversation command.

    Unknown slash input is treated as free text in 11.0.1. Only malformed known
    commands return ``kind=error``.
    """

    normalized = raw.strip()
    if not normalized:
        return ConversationCommand(
            kind=ConversationCommandKind.ERROR,
            raw=normalized,
            error="Input is empty",
        )

    parts = normalized.split()
    command_name = parts[0]
    args = parts[1:]

    if command_name in _SIMPLE_COMMANDS:
        return ConversationCommand(
            kind=_SIMPLE_COMMANDS[command_name],
            raw=normalized,
            args=args,
        )

    if command_name == "/replay":
        if len(args) != 2:
            return ConversationCommand(
                kind=ConversationCommandKind.ERROR,
                raw=normalized,
                args=args,
                error=_REPLAY_USAGE,
            )
        learned_path_id, url = args
        return ConversationCommand(
            kind=ConversationCommandKind.REPLAY,
            raw=normalized,
            args=args,
            learned_path_id=learned_path_id,
            url=url,
        )

    return ConversationCommand(
        kind=ConversationCommandKind.FREE_TEXT,
        raw=normalized,
        args=parts if command_name.startswith("/") else [],
        text=normalized,
    )
