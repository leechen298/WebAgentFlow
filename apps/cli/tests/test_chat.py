"""Tests for top-level ``wagent chat`` interactive CLI."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import time
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
            "学习一下这个登录页怎么登录，地址是 https://example.invalid/entry",
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
            "browser_visibility": "visible",
        },
    }

    first_dispatch = client.post.call_args_list[1]
    assert first_dispatch.args[0] == "/conversation/sessions/sess-1/dispatch"
    assert first_dispatch.kwargs["json"]["metadata"] == {
        "client": "wagent_chat",
        "browser_visibility": "visible",
    }
    output = stdout.getvalue()
    assert "WAgent > 你好，我可以学习页面操作，也可以执行已经学会的操作。" in output
    assert output.count("WAgent · 正在理解你的需求 ...") == 2
    assert "WAgent > 正在理解你的需求" not in output
    assert "WAgent > 我会打开浏览器学习" not in output
    assert "WAgent > 我会打开浏览器执行" not in output
    assert "WAgent > 开始学习页面操作。" in output
    assert "WAgent > 执行中。" in output
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
    assert "WAgent · 正在理解你的需求 ..." in output
    assert "WAgent > 正在理解你的需求" not in output
    assert "WAgent > 我会打开浏览器执行" not in output
    assert "WAgent > 还没学过这个操作，需要先学习。" in output


def test_chat_tty_waiting_indicator_is_transient() -> None:
    class TtyBuffer(StringIO):
        def isatty(self) -> bool:
            return True

    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)

    def post(path, **kwargs):
        if path.endswith("/dispatch"):
            time.sleep(0.18)
            return _mock_response({"user_response": "处理完成。"})
        return _mock_response({"id": "sess-1", "status": "idle"})

    client.post.side_effect = post

    with patch.object(chat_module.httpx, "Client", return_value=client), patch(
        "builtins.input",
        side_effect=["你好", "exit"],
    ):
        stdout = TtyBuffer()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            rc = wagent_main.main(["chat"])

    assert rc == 0
    output = stdout.getvalue()
    assert "\rWAgent " in output
    assert "正在理解你的需求" in output
    assert "WAgent > 正在理解你的需求" not in output
    assert "WAgent > 处理完成。" in output


def test_chat_virtual_target_progress_labels() -> None:
    client = _mock_client()
    client.post.side_effect = [
        _mock_response({"id": "sess-1", "status": "idle"}),
        _mock_response({"user_response": "学习完成：我学会了进入工作台操作。之后你可以说“帮我进入工作台”。"}),
        _mock_response({"user_response": "进入工作台完成。"}),
    ]
    with patch.object(chat_module.httpx, "Client", return_value=client), patch(
        "builtins.input",
        side_effect=[
            (
                "学习一下这个虚拟页面怎么提交表单，地址是 "
                "https://example.invalid/form，字段 A 是 alpha，字段 B 是 beta"
            ),
            "帮我提交表单",
            "exit",
        ],
    ):
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            rc = wagent_main.main(["chat"])

    assert rc == 0
    output = stdout.getvalue()
    assert output.count("WAgent · 正在理解你的需求 ...") == 2
    assert "WAgent > 正在理解你的需求" not in output
    assert "WAgent > 我会打开浏览器学习" not in output
    assert "WAgent > 我会打开浏览器执行" not in output


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


def test_chat_default_visible_payload() -> None:
    client = _mock_client()
    with patch.object(chat_module.httpx, "Client", return_value=client), patch(
        "builtins.input",
        side_effect=["exit"],
    ):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            rc = wagent_main.main(["chat"])

    assert rc == 0
    create_call = client.post.call_args_list[0]
    assert create_call.kwargs["json"]["metadata"]["browser_visibility"] == "visible"


def test_chat_headless_opt_out_payload() -> None:
    client = _mock_client()
    client.post.side_effect = [
        _mock_response({"id": "sess-1", "status": "idle"}),
        _mock_response({"user_response": "执行中。\n登录完成。"}),
    ]
    with patch.object(chat_module.httpx, "Client", return_value=client), patch(
        "builtins.input",
        side_effect=["帮我登录", "exit"],
    ):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            rc = wagent_main.main(["chat", "--headless"])

    assert rc == 0
    create_call = client.post.call_args_list[0]
    assert create_call.kwargs["json"]["metadata"]["browser_visibility"] == "headless"
    dispatch_call = client.post.call_args_list[1]
    assert dispatch_call.kwargs["json"]["metadata"]["browser_visibility"] == "headless"


def test_chat_headless_shows_backend_wording() -> None:
    client = _mock_client()
    client.post.side_effect = [
        _mock_response({"id": "sess-1", "status": "idle"}),
        _mock_response({"user_response": "执行中。\n登录完成。"}),
    ]
    with patch.object(chat_module.httpx, "Client", return_value=client), patch(
        "builtins.input",
        side_effect=["帮我登录", "exit"],
    ):
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            rc = wagent_main.main(["chat", "--headless"])

    assert rc == 0
    output = stdout.getvalue()
    assert "WAgent · 正在理解你的需求 ..." in output
    assert "WAgent > 正在理解你的需求" not in output
    assert "WAgent > 我会在后台执行" not in output
    assert "WAgent > 我会打开浏览器执行" not in output


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


# ── 11.3.2 session id output + resume ─────────────────────────────────────────


def test_chat_prints_session_id_after_create() -> None:
    client = _mock_client()
    with patch.object(chat_module.httpx, "Client", return_value=client), patch(
        "builtins.input",
        side_effect=["exit"],
    ):
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            rc = wagent_main.main(["chat"])

    assert rc == 0
    output = stdout.getvalue()
    assert "WAgent > 本次会话 ID：sess-1。需要调试时可以在管理后台查看。" in output


def test_chat_resume_valid_session() -> None:
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.get.return_value = _mock_response(
        {"id": "sess-resume", "status": "idle", "current_mode": "interactive_chat"}
    )
    client.post.return_value = _mock_response({"user_response": "ok"})

    with patch.object(chat_module.httpx, "Client", return_value=client), patch(
        "builtins.input",
        side_effect=["hello", "exit"],
    ):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            rc = wagent_main.main(["chat", "--resume", "sess-resume"])

    assert rc == 0
    client.get.assert_called_once_with("/conversation/sessions/sess-resume")
    # Should dispatch to existing session, not create
    dispatch_calls = [c for c in client.post.call_args_list if "/dispatch" in c.args[0]]
    assert len(dispatch_calls) == 1
    assert dispatch_calls[0].args[0] == "/conversation/sessions/sess-resume/dispatch"


def test_chat_resume_rejects_non_chat_session() -> None:
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.get.return_value = _mock_response(
        {"id": "sess-replay", "status": "idle", "current_mode": "replay"}
    )

    stderr = StringIO()
    with patch.object(chat_module.httpx, "Client", return_value=client), patch(
        "builtins.input",
        side_effect=["exit"],
    ):
        with redirect_stdout(StringIO()), redirect_stderr(stderr):
            rc = wagent_main.main(["chat", "--resume", "sess-replay"])

    assert rc == 2
    assert "not an interactive_chat session" in stderr.getvalue()


def test_chat_resume_rejects_headless_combo() -> None:
    stderr = StringIO()
    with redirect_stdout(StringIO()), redirect_stderr(stderr):
        rc = wagent_main.main(["chat", "--resume", "sess-1", "--headless"])

    assert rc == 2
    assert "--headless only applies when creating a new chat session" in stderr.getvalue()
