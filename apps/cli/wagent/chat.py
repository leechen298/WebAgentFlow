"""Interactive ``wagent chat`` product entry."""

from __future__ import annotations

import argparse
import os
import sys
import termios
import threading
import tty
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
                _print_agent(
                    f"本次会话 ID：{session_id}。调试详情：/conversation/history/{session_id}"
                )
            _print_agent(_WELCOME)
            while True:
                try:
                    user_input = input("You > ")
                except EOFError:
                    print()
                    _record_client_exit(client, session_id, reason="eof")
                    return 0
                except KeyboardInterrupt:
                    print()
                    _record_client_exit(client, session_id, reason="keyboard_interrupt")
                    return 0
                if user_input.strip().lower() in _EXIT_COMMANDS:
                    _record_client_exit(client, session_id, reason="exit_command")
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
                    _record_client_exit(client, session_id, reason="keyboard_interrupt")
                    return 0
                if response is None:
                    return 2
                visible_response = _dedupe_response(
                    str(response.get("user_response") or ""),
                    progress_message=progress_message,
                )
                if visible_response:
                    _print_agent(visible_response)
                selected_option = _prompt_action_option(
                    response.get("action_options"),
                    visible_response,
                )
                if selected_option is None:
                    continue
                progress_message = _progress_message(selected_option, headless=headless)
                try:
                    response = _dispatch_with_working_indicator(
                        client,
                        session_id,
                        selected_option,
                        headless=headless,
                        progress_message=progress_message,
                    )
                except KeyboardInterrupt:
                    print()
                    _record_client_exit(client, session_id, reason="keyboard_interrupt")
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


def _record_client_exit(
    client: httpx.Client,
    session_id: str,
    *,
    reason: str,
) -> None:
    try:
        client.post(
            f"/conversation/sessions/{session_id}/events",
            json={
                "type": "chat_progress_recorded",
                "payload": {
                    "progress_kind": "chat_client_exited",
                    "reason": reason,
                    "client": "wagent_chat",
                },
            },
        )
    except Exception:
        return


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


def _prompt_action_option(options: Any, visible_response: str) -> str | None:
    if not isinstance(options, list) or not options:
        return None
    normalized_options: list[dict[str, str]] = []
    for option in options:
        if not isinstance(option, dict):
            continue
        label = str(option.get("label") or "").strip()
        option_id = str(option.get("id") or "").strip()
        if not label or not option_id:
            continue
        description = str(option.get("description") or "").strip()
        normalized_options.append(
            {
                "id": option_id,
                "label": label,
                "description": description,
            }
        )
    if not normalized_options:
        return None

    question = _last_non_empty_line(visible_response) or "请选择下一步"
    selected = _select_action_option(normalized_options, question)
    if selected is None:
        return None
    return selected["label"]


def _select_action_option(
    options: list[dict[str, str]],
    question: str,
    *,
    input_stream: Any | None = None,
    output_stream: Any | None = None,
    read_key: Any | None = None,
) -> dict[str, str] | None:
    input_stream = input_stream or sys.stdin
    output_stream = output_stream or sys.stdout
    if read_key is None and not _can_use_interactive_select(input_stream, output_stream):
        _print_agent("请在交互式终端中用上下键选择下一步。")
        return None

    index = 0
    rendered_lines = 0
    old_settings = None
    input_fd = None
    if read_key is None:
        input_fd = input_stream.fileno()
        old_settings = termios.tcgetattr(input_fd)
        tty.setcbreak(input_fd)

    try:
        while True:
            rendered_lines = _render_action_option_select(
                options,
                question,
                selected_index=index,
                output_stream=output_stream,
                previous_line_count=rendered_lines,
            )
            key = read_key() if read_key is not None else _read_select_key(input_stream)
            key = _normalize_select_key(key)
            if key == "up":
                index = (index - 1) % len(options)
            elif key == "down":
                index = (index + 1) % len(options)
            elif key == "enter":
                _render_selected_action_option(
                    question,
                    options[index],
                    output_stream=output_stream,
                    previous_line_count=rendered_lines,
                )
                return options[index]
            elif key in {"cancel", "eof"}:
                _clear_rendered_select(output_stream, rendered_lines)
                return None
    finally:
        if old_settings is not None and input_fd is not None:
            termios.tcsetattr(input_fd, termios.TCSADRAIN, old_settings)


def _can_use_interactive_select(input_stream: Any, output_stream: Any) -> bool:
    return bool(
        hasattr(input_stream, "isatty")
        and hasattr(output_stream, "isatty")
        and input_stream.isatty()
        and output_stream.isatty()
        and hasattr(input_stream, "fileno")
    )


def _render_action_option_select(
    options: list[dict[str, str]],
    question: str,
    *,
    selected_index: int,
    output_stream: Any,
    previous_line_count: int,
) -> int:
    if previous_line_count:
        _clear_rendered_select(output_stream, previous_line_count)
    lines = [f"WAgent ? {question}"]
    for index, option in enumerate(options):
        prefix = "> " if index == selected_index else "  "
        lines.append(f"{prefix}{option['label']}")
    description = options[selected_index].get("description") or ""
    if description:
        lines.append(f"  {description}")
    lines.append("使用上下键移动，Enter 确认。")
    output_stream.write("\n".join(lines) + "\n")
    output_stream.flush()
    return len(lines)


def _render_selected_action_option(
    question: str,
    selected: dict[str, str],
    *,
    output_stream: Any,
    previous_line_count: int,
) -> None:
    if previous_line_count:
        _clear_rendered_select(output_stream, previous_line_count)
    output_stream.write(f"WAgent ? {question} {selected['label']}\n")
    output_stream.flush()


def _clear_rendered_select(output_stream: Any, line_count: int) -> None:
    if line_count <= 0:
        return
    output_stream.write(f"\x1b[{line_count}A\x1b[J")
    output_stream.flush()


def _read_select_key(input_stream: Any) -> str:
    char = input_stream.read(1)
    if char == "\x1b":
        second = input_stream.read(1)
        if second == "[":
            third = input_stream.read(1)
            if third == "A":
                return "up"
            if third == "B":
                return "down"
        return "cancel"
    return char


def _normalize_select_key(value: Any) -> str | None:
    key = str(value or "")
    if key in {"up", "down", "enter", "cancel", "eof"}:
        return key
    if key in {"\r", "\n"}:
        return "enter"
    if key in {"\x03"}:
        raise KeyboardInterrupt
    if key in {"\x04", ""}:
        return "eof"
    if key.lower() == "k":
        return "up"
    if key.lower() == "j":
        return "down"
    return None


def _last_non_empty_line(value: str) -> str:
    for line in reversed(value.splitlines()):
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _print_agent(message: str) -> None:
    lines = message.splitlines() or [""]
    for line in lines:
        print(f"WAgent > {line}")
