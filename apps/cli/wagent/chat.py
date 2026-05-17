"""Interactive ``wagent chat`` product entry."""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Any
from urllib.parse import urlparse

import httpx

_DEFAULT_TIMEOUT_SEC = 180.0
_EXIT_COMMANDS = {"exit", "quit", ":q"}
_WELCOME = "你好，我可以学习页面操作，也可以执行已经学会的操作。"
_URL_RE = re.compile(r"https?://[^\s，。]+")
_LEARN_KEYWORDS = ("学习", "学一下", "learn", "teach")


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
                if progress_message:
                    _print_agent(progress_message)
                response = _dispatch(client, session_id, user_input, headless=headless)
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
    text = user_input.strip()
    url = _extract_url(text)
    prefix = "我会在后台" if headless else "我会打开浏览器"
    if url and _is_learn_input(text):
        return f"{prefix}学习：{_learning_target_label(url)}。"
    return f"{prefix}执行：{_task_label(text)}。"


def _dedupe_response(message: str, *, progress_message: str) -> str:
    lines = message.splitlines()
    if "学习" in progress_message and progress_message.startswith("我会"):
        lines = [line for line in lines if line.strip() != "开始学习页面操作。"]
    if "执行" in progress_message and progress_message.startswith("我会"):
        lines = [line for line in lines if line.strip() != "执行中。"]
    return "\n".join(lines)


def _extract_url(text: str) -> str | None:
    match = _URL_RE.search(text)
    return match.group(0) if match else None


def _is_learn_input(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered or keyword in text for keyword in _LEARN_KEYWORDS)


def _learning_target_label(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    if path == "/login":
        return "在登录页输入账号密码，并点击“登录”按钮"
    return "这个页面上的主要操作"


def _task_label(text: str) -> str:
    task = text.strip()
    prefixes = (
        "麻烦你帮我",
        "麻烦帮我",
        "请帮我",
        "你帮我",
        "帮我",
        "麻烦你",
        "麻烦",
        "请",
        "我要",
        "我想要",
        "我想",
    )
    for prefix in prefixes:
        if task.startswith(prefix):
            task = task.removeprefix(prefix).strip()
            break
    task = task.strip(" ，,。.!！?？")
    for suffix in ("一下吧", "一下", "吧"):
        if task.endswith(suffix):
            task = task.removesuffix(suffix).strip()
            break
    task = task.strip(" ，,。.!！?？")
    if task == "登录" or task.endswith("登录"):
        return "输入账号密码，并点击“登录”按钮完成登录"
    return task or text.strip()


def _print_agent(message: str) -> None:
    lines = message.splitlines() or [""]
    for line in lines:
        print(f"WAgent > {line}")
