"""Tests for ``wagent conversation``.

The conversation subcommand is a thin HTTP client around the 11.0.3
Conversation API. These tests pin its contract:

    - stdout is exactly one JSON object (or array)
    - stderr carries errors
    - exit codes: 0 success / 2 CLI or network or API error
    - --pretty toggles indented JSON
    - role is fixed to "user" for send
"""

from __future__ import annotations

import inspect
import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import MagicMock, patch


from wagent import main as wagent_main
from wagent import conversation as conv_module


def _run(argv: list[str]) -> int:
    """Invoke the top-level wagent dispatcher with 'conversation' prefixed."""
    return wagent_main.main(["conversation", *argv])


# ── Helpers ───────────────────────────────────────────────────────────────────


def _mock_client(
    *,
    status_code: int = 200,
    data: dict | list | None = None,
    code: int = 0,
    msg: str = "ok",
) -> MagicMock:
    """Build a context-manager-friendly mock httpx.Client."""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    resp = MagicMock(status_code=status_code)
    resp.json = MagicMock(return_value={"code": code, "data": data, "msg": msg})
    resp.text = json.dumps({"code": code, "data": data, "msg": msg})
    client.post = MagicMock(return_value=resp)
    client.get = MagicMock(return_value=resp)
    return client


# ── start ─────────────────────────────────────────────────────────────────────


def test_start_calls_post_sessions_and_prints_json() -> None:
    client = _mock_client(data={"id": "sess-1", "status": "idle"})
    with patch.object(conv_module.httpx, "Client", return_value=client):
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            rc = _run(["start"])

    assert rc == 0
    parsed = json.loads(stdout.getvalue())
    assert parsed["id"] == "sess-1"
    assert parsed["status"] == "idle"
    client.post.assert_called_once_with("/conversation/sessions", json={})


def test_start_pretty_outputs_indented_json() -> None:
    client = _mock_client(data={"id": "sess-1", "status": "idle"})
    with patch.object(conv_module.httpx, "Client", return_value=client):
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            rc = _run(["start", "--pretty"])

    assert rc == 0
    # Pretty output should contain newlines (indentation).
    assert "\n" in stdout.getvalue()


# ── status ────────────────────────────────────────────────────────────────────


def test_status_calls_get_session() -> None:
    client = _mock_client(data={"id": "sess-1", "status": "idle"})
    with patch.object(conv_module.httpx, "Client", return_value=client):
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            rc = _run(["status", "sess-1"])

    assert rc == 0
    parsed = json.loads(stdout.getvalue())
    assert parsed["id"] == "sess-1"
    client.get.assert_called_once_with("/conversation/sessions/sess-1")


# ── send ──────────────────────────────────────────────────────────────────────


def test_send_calls_post_dispatch_with_input() -> None:
    client = _mock_client(data={"session_id": "sess-1", "command_kind": "free_text"})
    with patch.object(conv_module.httpx, "Client", return_value=client):
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            rc = _run(["send", "sess-1", "--content", "hello"])

    assert rc == 0
    parsed = json.loads(stdout.getvalue())
    assert parsed["session_id"] == "sess-1"
    call_kwargs = client.post.call_args.kwargs
    assert call_kwargs["json"]["input"] == "hello"
    assert call_kwargs["json"]["metadata"] == {}
    # Verify it calls dispatch endpoint, not messages endpoint
    assert "/dispatch" in client.post.call_args.args[0]


# ── messages ──────────────────────────────────────────────────────────────────


def test_messages_calls_get_messages() -> None:
    client = _mock_client(data=[{"id": "m1", "content": "hi"}])
    with patch.object(conv_module.httpx, "Client", return_value=client):
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            rc = _run(["messages", "sess-1"])

    assert rc == 0
    parsed = json.loads(stdout.getvalue())
    assert parsed[0]["content"] == "hi"
    client.get.assert_called_once()
    call_args = client.get.call_args
    assert call_args.args[0] == "/conversation/sessions/sess-1/messages"
    assert call_args.kwargs["params"]["limit"] == 100


def test_messages_passes_limit() -> None:
    client = _mock_client(data=[])
    with patch.object(conv_module.httpx, "Client", return_value=client):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            _run(["messages", "sess-1", "--limit", "5"])

    call_kwargs = client.get.call_args.kwargs
    assert call_kwargs["params"]["limit"] == 5


# ── transcript ────────────────────────────────────────────────────────────────


def test_transcript_calls_get_transcript() -> None:
    client = _mock_client(data=[{"id": "m1", "content": "hi"}])
    with patch.object(conv_module.httpx, "Client", return_value=client):
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            rc = _run(["transcript", "sess-1"])

    assert rc == 0
    parsed = json.loads(stdout.getvalue())
    assert parsed[0]["content"] == "hi"
    client.get.assert_called_once_with("/conversation/sessions/sess-1/transcript")


# ── events ────────────────────────────────────────────────────────────────────


def test_events_calls_get_events() -> None:
    client = _mock_client(data=[{"id": "e1", "type": "state_changed"}])
    with patch.object(conv_module.httpx, "Client", return_value=client):
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            rc = _run(["events", "sess-1"])

    assert rc == 0
    parsed = json.loads(stdout.getvalue())
    assert parsed[0]["type"] == "state_changed"
    call_kwargs = client.get.call_args.kwargs
    assert call_kwargs["params"]["limit"] == 100


def test_events_passes_limit() -> None:
    client = _mock_client(data=[])
    with patch.object(conv_module.httpx, "Client", return_value=client):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            _run(["events", "sess-1", "--limit", "10"])

    call_kwargs = client.get.call_args.kwargs
    assert call_kwargs["params"]["limit"] == 10


# ── Error handling ────────────────────────────────────────────────────────────


def test_api_404_exits_two() -> None:
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    resp = MagicMock(status_code=404)
    resp.text = "session not found"
    resp.json = MagicMock(return_value={"code": 404, "msg": "session not found", "data": None})
    client.get = MagicMock(return_value=resp)
    with patch.object(conv_module.httpx, "Client", return_value=client):
        stderr = StringIO()
        with redirect_stdout(StringIO()), redirect_stderr(stderr):
            rc = _run(["status", "bad-id"])

    assert rc == 2
    assert "404" in stderr.getvalue()


def test_api_business_error_exits_two() -> None:
    client = _mock_client(status_code=200, code=400, msg="bad request", data=None)
    with patch.object(conv_module.httpx, "Client", return_value=client):
        stderr = StringIO()
        with redirect_stdout(StringIO()), redirect_stderr(stderr):
            rc = _run(["start"])

    assert rc == 2
    assert "400" in stderr.getvalue()


def test_network_error_exits_two() -> None:
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.post = MagicMock(side_effect=conv_module.httpx.ConnectError("refused"))
    with patch.object(conv_module.httpx, "Client", return_value=client):
        stderr = StringIO()
        with redirect_stdout(StringIO()), redirect_stderr(stderr):
            rc = _run(["start"])

    assert rc == 2
    assert "cannot reach API" in stderr.getvalue()


# ── No forbidden imports ──────────────────────────────────────────────────────


def test_module_does_not_import_replay_autonomous_or_llm() -> None:
    source = inspect.getsource(conv_module)
    forbidden_tokens = [
        "learned_path_replay",
        "run_replay",
        "autonomous_explorer",
        "/exploration/autonomous-runs",
        "llm_provider",
        "OpenAI",
    ]
    for token in forbidden_tokens:
        assert token not in source


def test_module_does_not_import_db_repo_or_model() -> None:
    source = inspect.getsource(conv_module)
    forbidden = [
        "ConversationRepository",
        "ConversationSession",
        "ConversationMessage",
        "ConversationEvent",
        "from app.models",
        "from app.repos",
        "sqlalchemy",
    ]
    for token in forbidden:
        assert token not in source, f"found forbidden import: {token}"


# ── Existing verify unaffected ────────────────────────────────────────────────


def test_verify_still_works_after_conversation_added() -> None:
    # Sanity: the top-level dispatcher still routes to verify.
    from wagent import verify as vs

    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    resp = MagicMock(status_code=200)
    resp.json = MagicMock(
        return_value={
            "code": 0,
            "data": {
                "run_id": "r1",
                "verdict": "success",
                "success": True,
                "summary": "ok",
                "final_url": "http://t/",
                "final_title": "T",
                "total_steps": 1,
                "elapsed_ms": 1000,
                "supervisor": {},
                "verification": {"scorecard": {}},
            },
            "msg": "ok",
        }
    )
    client.post = MagicMock(return_value=resp)
    with patch.object(vs.httpx, "Client", return_value=client):
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            rc = wagent_main.main(["verify", "--url", "http://t/"])

    assert rc == 0
    parsed = json.loads(stdout.getvalue())
    assert parsed["run_id"] == "r1"
