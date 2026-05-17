"""Tests for top-level ``wagent chat`` interactive CLI."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import MagicMock, patch

from wagent import chat as chat_module
from wagent import main as wagent_main


def _mock_response(data):
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"code": 0, "msg": "ok", "data": data}
    resp.text = "ok"
    return resp


def _mock_client() -> MagicMock:
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.post.side_effect = [
        _mock_response({"id": "sess-1", "status": "idle"}),
        _mock_response({"user_response": "开始学习页面操作。\n学习完成：我学会了登录页的登录操作。之后你可以说“帮我登录”。"}),
        _mock_response({"user_response": "执行中。\n登录完成。"}),
    ]
    return client


def test_chat_is_top_level_command_and_creates_interactive_session() -> None:
    client = _mock_client()
    with patch.object(chat_module.httpx, "Client", return_value=client), patch(
        "builtins.input",
        side_effect=[
            "学习一下这个登录页怎么登录，地址是 http://localhost:5175/login",
            "帮我登录",
            "exit",
        ],
    ):
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            rc = wagent_main.main(["chat"])

    assert rc == 0
    create_call = client.post.call_args_list[0]
    assert create_call.args[0] == "/conversation/sessions"
    assert create_call.kwargs["json"] == {
        "current_mode": "interactive_chat",
        "metadata": {
            "client": "wagent_chat",
            "runtime_policy": "auto_execute_happy_path",
        },
    }

    first_dispatch = client.post.call_args_list[1]
    assert first_dispatch.args[0] == "/conversation/sessions/sess-1/dispatch"
    assert first_dispatch.kwargs["json"]["metadata"] == {"client": "wagent_chat"}
    output = stdout.getvalue()
    assert "WAgent > 你好，我可以学习页面操作，也可以执行已经学会的操作。" in output
    assert "WAgent > 我会学习：在登录页输入账号密码，并点击“登录”按钮。" in output
    assert "WAgent > 我会执行：输入账号密码，并点击“登录”按钮完成登录。" in output
    assert "WAgent > 开始学习页面操作。" not in output
    assert "WAgent > 执行中。" not in output
    assert "LearnedPath" not in output
    assert "learned_path" not in output
    assert "run_id" not in output
    assert "#username" not in output
    assert "button.btn" not in output
    assert "WAgent > 学习完成：我学会了登录页的登录操作。之后你可以说“帮我登录”。" in output
    assert "WAgent > 登录完成。" in output


def test_chat_explains_unknown_task_before_no_path_fallback() -> None:
    client = _mock_client()
    client.post.side_effect = [
        _mock_response({"id": "sess-1", "status": "idle"}),
        _mock_response({"user_response": "还没学过这个操作，需要先学习。"}),
    ]
    with patch.object(chat_module.httpx, "Client", return_value=client), patch(
        "builtins.input",
        side_effect=["帮我导出报表", "exit"],
    ):
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            rc = wagent_main.main(["chat"])

    assert rc == 0
    output = stdout.getvalue()
    assert "WAgent > 我会执行：导出报表。" in output
    assert "WAgent > 还没学过这个操作，需要先学习。" in output


def test_chat_default_timeout_is_180_seconds() -> None:
    client = _mock_client()
    with patch.object(chat_module.httpx, "Client", return_value=client) as client_cls, patch(
        "builtins.input",
        side_effect=["exit"],
    ):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            rc = wagent_main.main(["chat"])

    assert rc == 0
    assert client_cls.call_args.kwargs["timeout"] == 180.0


def test_chat_timeout_can_be_overridden() -> None:
    client = _mock_client()
    with patch.object(chat_module.httpx, "Client", return_value=client) as client_cls, patch(
        "builtins.input",
        side_effect=["quit"],
    ):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            rc = wagent_main.main(["chat", "--timeout", "240"])

    assert rc == 0
    assert client_cls.call_args.kwargs["timeout"] == 240.0


def test_chat_colon_q_exits_without_dispatch() -> None:
    client = _mock_client()
    with patch.object(chat_module.httpx, "Client", return_value=client), patch(
        "builtins.input",
        side_effect=[":q"],
    ):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            rc = wagent_main.main(["chat"])

    assert rc == 0
    assert client.post.call_count == 1
