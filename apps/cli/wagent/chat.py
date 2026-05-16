"""Interactive ``wagent chat`` product entry."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import httpx

_DEFAULT_TIMEOUT_SEC = 180.0
_EXIT_COMMANDS = {"exit", "quit", ":q"}
_WELCOME = "你好，我可以学习页面操作，也可以执行已经学会的操作。"


def configure_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--api-base",
        default=os.environ.get("WBAF_API_BASE", "http://localhost:8001"),
        help=(
            "Base URL of the WebAgentFlow API "
            "(env: WBAF_API_BASE, default http://localhost:8001)."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=_DEFAULT_TIMEOUT_SEC,
        help="HTTP timeout in seconds (default 180).",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    api_base = args.api_base.rstrip("/")
    try:
        with httpx.Client(base_url=api_base, timeout=float(args.timeout)) as client:
            session = _create_session(client)
            if session is None:
                return 2
            session_id = session["id"]
            _print_agent(_WELCOME)
            while True:
                try:
                    user_input = input("You > ")
                except (EOFError, KeyboardInterrupt):
                    print()
                    return 0
                if user_input.strip().lower() in _EXIT_COMMANDS:
                    return 0
                if not user_input.strip():
                    continue
                response = _dispatch(client, session_id, user_input)
                if response is None:
                    return 2
                _print_agent(str(response.get("user_response") or ""))
    except httpx.ConnectError as exc:
        print(
            f"wagent chat: cannot reach API at {api_base}. "
            f"Is WebAgentFlow running? ({exc})",
            file=sys.stderr,
        )
        return 2
    except httpx.HTTPError as exc:
        print(f"wagent chat: HTTP error - {exc}", file=sys.stderr)
        return 2


def _create_session(client: httpx.Client) -> dict[str, Any] | None:
    return _api_post(
        client,
        "/conversation/sessions",
        {
            "current_mode": "interactive_chat",
            "metadata": {
                "client": "wagent_chat",
                "runtime_policy": "auto_execute_happy_path",
            },
        },
    )


def _dispatch(
    client: httpx.Client,
    session_id: str,
    user_input: str,
) -> dict[str, Any] | None:
    return _api_post(
        client,
        f"/conversation/sessions/{session_id}/dispatch",
        {
            "input": user_input,
            "metadata": {"client": "wagent_chat"},
        },
    )


def _api_post(
    client: httpx.Client,
    path: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    response = client.post(path, json=payload)
    if response.status_code >= 400:
        print(
            f"wagent chat: API returned {response.status_code} - "
            f"{response.text[:300]}",
            file=sys.stderr,
        )
        return None
    envelope = response.json()
    if envelope.get("code") != 0:
        print(
            f"wagent chat: API error code={envelope.get('code')} "
            f"msg={envelope.get('msg')!r}",
            file=sys.stderr,
        )
        return None
    return envelope.get("data")


def _print_agent(message: str) -> None:
    lines = message.splitlines() or [""]
    for line in lines:
        print(f"WAgent > {line}")
