"""Interactive ``wagent chat`` product entry."""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
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
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode (no visible window).",
    )
    parser.add_argument(
        "--resume",
        dest="resume_session_id",
        default=None,
        help="Resume an existing interactive_chat session by ID.",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    api_base = args.api_base.rstrip("/")
    headless = bool(args.headless)
    resume_session_id = args.resume_session_id

    if resume_session_id is not None and headless:
        print(
            "wagent chat: --headless only applies when creating a new chat session. "
            "Use --resume without --headless.",
            file=sys.stderr,
        )
        return 2

    try:
        with httpx.Client(base_url=api_base, timeout=float(args.timeout)) as client:
            if resume_session_id is not None:
                session = _get_session(client, resume_session_id)
                if session is None:
                    return 2
                if session.get("current_mode") != "interactive_chat":
                    print(
                        f"wagent chat: session {resume_session_id} is not an "
                        f"interactive_chat session (current_mode={session.get('current_mode')}).",
                        file=sys.stderr,
                    )
                    return 2
                session_id = session["id"]
                headless = _session_headless(session)
            else:
                session = _create_session(client, headless=headless)
                if session is None:
                    return 2
                session_id = session["id"]
                _print_agent(f"本次会话 ID：{session_id}。需要调试时可以在管理后台查看。")
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
                progress_message = _progress_message(user_input, headless=headless)
                try:
                    response = _dispatch_with_working_indicator(
                        client,
                        session_id,
                        user_input,
                        headless=headless,
                        progress_message=progress_message,
                    )
                except KeyboardInterrupt:
                    print()
                    return 0
                if response is None:
                    return 2
                visible_response = _dedupe_response(
                    str(response.get("user_response") or ""),
                    progress_message=progress_message,
                )
                if visible_response:
                    _print_agent(visible_response)
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


def _create_session(
    client: httpx.Client,
    *,
    headless: bool = False,
) -> dict[str, Any] | None:
    visibility = "headless" if headless else "visible"
    return _api_post(
        client,
        "/conversation/sessions",
        {
            "current_mode": "interactive_chat",
            "metadata": {
                "client": "wagent_chat",
                "runtime_policy": "auto_execute_happy_path",
                "browser_visibility": visibility,
            },
        },
    )


def _session_headless(session: dict[str, Any]) -> bool:
    metadata = session.get("metadata") or {}
    return metadata.get("browser_visibility") == "headless"


def _get_session(client: httpx.Client, session_id: str) -> dict[str, Any] | None:
    response = client.get(f"/conversation/sessions/{session_id}")
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


def _dispatch(
    client: httpx.Client,
    session_id: str,
    user_input: str,
    *,
    headless: bool = False,
) -> dict[str, Any] | None:
    visibility = "headless" if headless else "visible"
    return _api_post(
        client,
        f"/conversation/sessions/{session_id}/dispatch",
        {
            "input": user_input,
            "metadata": {
                "client": "wagent_chat",
                "browser_visibility": visibility,
            },
        },
    )


def _dispatch_with_working_indicator(
    client: httpx.Client,
    session_id: str,
    user_input: str,
    *,
    headless: bool = False,
    progress_message: str,
) -> dict[str, Any] | None:
    box: dict[str, Any] = {}

    def run_request() -> None:
        try:
            box["response"] = _dispatch(
                client,
                session_id,
                user_input,
                headless=headless,
            )
        except BaseException as exc:  # noqa: BLE001 - hand back to main thread
            box["error"] = exc

    worker = threading.Thread(target=run_request, daemon=True)
    worker.start()
    _show_working_indicator(worker, progress_message)
    if "error" in box:
        raise box["error"]
    return box.get("response")


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


def _progress_message(user_input: str, *, headless: bool = False) -> str:
    _ = (user_input, headless)
    return "正在理解你的需求"


def _show_working_indicator(worker: threading.Thread, label: str) -> None:
    if not label:
        worker.join()
        return
    if not sys.stdout.isatty():
        print(f"WAgent · {label} ...")
        worker.join()
        return

    frames = ("|", "/", "-", "\\")
    index = 0
    try:
        while worker.is_alive():
            frame = frames[index % len(frames)]
            sys.stdout.write(f"\rWAgent {frame} {label} ...")
            sys.stdout.flush()
            index += 1
            worker.join(0.1)
    finally:
        sys.stdout.write("\r" + " " * (len(label) + 16) + "\r")
        sys.stdout.flush()


def _dedupe_response(message: str, *, progress_message: str) -> str:
    lines = message.splitlines()
    if "学习" in progress_message and progress_message.startswith("我会"):
        lines = [line for line in lines if line.strip() != "开始学习页面操作。"]
    if "执行" in progress_message and progress_message.startswith("我会"):
        lines = [line for line in lines if line.strip() != "执行中。"]
    return "\n".join(lines)


def _print_agent(message: str) -> None:
    lines = message.splitlines() or [""]
    for line in lines:
        print(f"WAgent > {line}")
