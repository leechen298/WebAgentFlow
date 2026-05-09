"""``wagent conversation`` — runtime conversation CLI.

Thin client around the 11.0.3 Conversation API.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import httpx

_DEFAULT_TIMEOUT_SEC = 30.0


# ───────────────────────────────────────────────────────────────────
# Argument parsing
# ───────────────────────────────────────────────────────────────────


def configure_parser(parser: argparse.ArgumentParser) -> None:
    """Attach ``conversation`` subcommands to a subparser.

    Called by the top-level ``wagent`` dispatcher in ``main.py``.
    """
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--api-base",
        default=os.environ.get("WBAF_API_BASE", "http://localhost:8001"),
        help=(
            "Base URL of the WebAgentFlow API "
            "(env: WBAF_API_BASE, default http://localhost:8001)."
        ),
    )
    shared.add_argument(
        "--pretty",
        action="store_true",
        help="Indent the JSON output for human reading.",
    )

    sub = parser.add_subparsers(dest="conversation_command", required=True)

    start_parser = sub.add_parser(
        "start",
        parents=[shared],
        help="Create a new conversation session (status=idle).",
    )
    start_parser.set_defaults(func=_run_start)

    status_parser = sub.add_parser(
        "status",
        parents=[shared],
        help="Get session status.",
    )
    status_parser.add_argument("session_id", help="Session UUID.")
    status_parser.set_defaults(func=_run_status)

    send_parser = sub.add_parser(
        "send",
        parents=[shared],
        help="Send a user message.",
    )
    send_parser.add_argument("session_id", help="Session UUID.")
    send_parser.add_argument(
        "--content",
        required=True,
        help="Message content.",
    )
    send_parser.set_defaults(func=_run_send)

    messages_parser = sub.add_parser(
        "messages",
        parents=[shared],
        help="List session messages.",
    )
    messages_parser.add_argument("session_id", help="Session UUID.")
    messages_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Max items (default 100).",
    )
    messages_parser.set_defaults(func=_run_messages)

    transcript_parser = sub.add_parser(
        "transcript",
        parents=[shared],
        help="Get session transcript (messages only).",
    )
    transcript_parser.add_argument("session_id", help="Session UUID.")
    transcript_parser.set_defaults(func=_run_transcript)

    events_parser = sub.add_parser(
        "events",
        parents=[shared],
        help="List session events.",
    )
    events_parser.add_argument("session_id", help="Session UUID.")
    events_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Max items (default 100).",
    )
    events_parser.set_defaults(func=_run_events)


# ───────────────────────────────────────────────────────────────────
# HTTP helpers
# ───────────────────────────────────────────────────────────────────


def _client(args: argparse.Namespace) -> httpx.Client:
    return httpx.Client(
        base_url=args.api_base.rstrip("/"),
        timeout=_DEFAULT_TIMEOUT_SEC,
    )


def _output(data: Any, pretty: bool) -> None:
    if pretty:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(data, ensure_ascii=False))


def _api_request(
    method: str,
    path: str,
    args: argparse.Namespace,
    **kwargs,
) -> Any:
    """Make an API request and return the data payload, or None on error.

    On error, prints to stderr and returns None.
    """
    api_base = args.api_base.rstrip("/")
    try:
        with _client(args) as client:
            fn = getattr(client, method)
            response = fn(path, **kwargs)
    except httpx.ConnectError as exc:
        print(
            f"wagent conversation: cannot reach API at {api_base}. "
            f"Is WebAgentFlow running? ({exc})",
            file=sys.stderr,
        )
        return None
    except httpx.HTTPError as exc:
        print(
            f"wagent conversation: HTTP error — {exc}",
            file=sys.stderr,
        )
        return None

    if response.status_code >= 400:
        try:
            body = response.json()
            msg = body.get("msg", response.text[:300])
        except Exception:
            msg = response.text[:300]
        print(
            f"wagent conversation: API returned {response.status_code} — {msg}",
            file=sys.stderr,
        )
        return None

    try:
        envelope = response.json()
    except json.JSONDecodeError as exc:
        print(
            f"wagent conversation: malformed response — {exc}",
            file=sys.stderr,
        )
        return None

    if envelope.get("code") != 0:
        print(
            f"wagent conversation: API error code={envelope.get('code')} "
            f"msg={envelope.get('msg')!r}",
            file=sys.stderr,
        )
        return None

    return envelope.get("data")


# ───────────────────────────────────────────────────────────────────
# Subcommand runners
# ───────────────────────────────────────────────────────────────────


def _run_start(args: argparse.Namespace) -> int:
    data = _api_request("post", "/conversation/sessions", args, json={})
    if data is None:
        return 2
    _output(data, args.pretty)
    return 0


def _run_status(args: argparse.Namespace) -> int:
    data = _api_request(
        "get", f"/conversation/sessions/{args.session_id}", args,
    )
    if data is None:
        return 2
    _output(data, args.pretty)
    return 0


def _run_send(args: argparse.Namespace) -> int:
    payload = {
        "role": "user",
        "content": args.content,
        "metadata": {},
    }
    data = _api_request(
        "post",
        f"/conversation/sessions/{args.session_id}/messages",
        args,
        json=payload,
    )
    if data is None:
        return 2
    _output(data, args.pretty)
    return 0


def _run_messages(args: argparse.Namespace) -> int:
    data = _api_request(
        "get",
        f"/conversation/sessions/{args.session_id}/messages",
        args,
        params={"limit": args.limit},
    )
    if data is None:
        return 2
    _output(data, args.pretty)
    return 0


def _run_transcript(args: argparse.Namespace) -> int:
    data = _api_request(
        "get",
        f"/conversation/sessions/{args.session_id}/transcript",
        args,
    )
    if data is None:
        return 2
    _output(data, args.pretty)
    return 0


def _run_events(args: argparse.Namespace) -> int:
    data = _api_request(
        "get",
        f"/conversation/sessions/{args.session_id}/events",
        args,
        params={"limit": args.limit},
    )
    if data is None:
        return 2
    _output(data, args.pretty)
    return 0
