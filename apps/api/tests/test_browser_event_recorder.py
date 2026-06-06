from __future__ import annotations

from types import SimpleNamespace

from app.schemas.page_analysis import PageAnalysis
from app.services.execution.browser_event_recorder import BrowserEventRecorder
from app.services.learning import autonomous_explorer as ae


class FakeTarget:
    def __init__(self) -> None:
        self.listeners: dict[str, object] = {}

    def on(self, event_name: str, handler) -> None:
        self.listeners[event_name] = handler


def test_attach_registers_page_and_context_listeners() -> None:
    page = FakeTarget()
    context = FakeTarget()

    recorder = BrowserEventRecorder(correlation_id="corr-001")
    recorder.attach(page=page, context=context)

    assert "request" in page.listeners
    assert "response" in page.listeners
    assert "download" in page.listeners
    assert "dialog" in page.listeners
    assert "console" in page.listeners
    assert "pageerror" in page.listeners
    assert "page" in context.listeners
    assert recorder.snapshot()["status"] == "recording_available"


def test_request_event_redacts_secret_query_headers_and_body() -> None:
    request = SimpleNamespace(
        url="https://example.invalid/users?token=secret-token&status=active",
        method="POST",
        resource_type="xhr",
        headers={
            "Authorization": "Bearer secret-token",
            "Cookie": "sid=secret",
            "Content-Type": "application/json",
        },
    )
    recorder = BrowserEventRecorder(correlation_id="corr-001", attempt_id="attempt-001")
    recorder.bind_action(action_id="action-001", step_index=1, action_type="click")

    recorder.record_request(request)

    event = recorder.snapshot()["events"][0]
    assert event["correlation_id"] == "corr-001"
    assert event["attempt_id"] == "attempt-001"
    assert event["action_id"] == "action-001"
    assert event["step_index"] == 1
    metadata = event["metadata"]
    assert metadata["url"]["host"] == "example.invalid"
    assert metadata["url"]["path"] == "/users"
    assert metadata["url"]["query_keys"] == ["status", "token"]
    assert metadata["url"]["secret_query_keys"] == ["token"]
    assert metadata["headers"] == {"content-type": "application/json"}
    assert metadata["body_stored"] is False
    assert "secret-token" not in str(event)
    assert "sid=secret" not in str(event)


def test_dialog_console_and_pageerror_messages_are_bounded_and_redacted() -> None:
    recorder = BrowserEventRecorder(correlation_id="corr-001")

    recorder.record_dialog(SimpleNamespace(type="alert", message="密码 123456"))
    recorder.record_console(SimpleNamespace(type="error", text="token=abc123 user=a@example.com"))
    recorder.record_pageerror("Authorization Bearer abc123 failed for 13800138000")

    snapshot = recorder.snapshot()
    text = str(snapshot)
    assert "123456" not in text
    assert "abc123" not in text
    assert "a@example.com" not in text
    assert "13800138000" not in text
    assert snapshot["events"][0]["event_type"] == "dialog"
    assert snapshot["events"][1]["event_type"] == "console"
    assert snapshot["events"][2]["event_type"] == "pageerror"


def test_timeline_truncates_deterministically() -> None:
    recorder = BrowserEventRecorder(correlation_id="corr-001", max_events=2)

    recorder.record_page_event("load")
    recorder.record_page_event("domcontentloaded")
    recorder.record_page_event("load")

    snapshot = recorder.snapshot()
    assert snapshot["status"] == "recording_partial"
    assert snapshot["event_count"] == 2
    assert snapshot["truncated"] is True
    assert snapshot["truncated_count"] == 1
    assert [event["event_id"] for event in snapshot["events"]] == ["event-1", "event-2"]


def test_download_and_popup_store_safe_metadata_only() -> None:
    recorder = BrowserEventRecorder(correlation_id="corr-001")

    recorder.record_download(SimpleNamespace(suggested_filename="../report-token=abc.csv"))
    recorder.record_popup(SimpleNamespace(url="https://example.invalid/popup?password=123456"))

    snapshot = recorder.snapshot()
    download = snapshot["events"][0]
    popup = snapshot["events"][1]
    assert download["metadata"]["content_stored"] is False
    assert "/" not in download["metadata"]["suggested_filename"]
    assert "\\" not in download["metadata"]["suggested_filename"]
    assert "report" in download["metadata"]["suggested_filename"]
    assert download["metadata"]["suggested_filename"] != "[empty]"
    assert popup["metadata"]["url"]["secret_query_keys"] == ["password"]
    assert "123456" not in str(snapshot)


def test_attach_without_supported_targets_is_unavailable() -> None:
    recorder = BrowserEventRecorder(correlation_id="corr-001")

    recorder.attach(page=object(), context=None)

    snapshot = recorder.snapshot()
    assert snapshot["status"] == "recording_unavailable"
    assert "no_supported_event_target" in snapshot["recorder_warnings"]


def test_autonomous_explorer_result_includes_action_scoped_timeline(monkeypatch) -> None:
    page = FakeTarget()
    page.url = "https://example.invalid/start"
    page.title = lambda: "Start"
    page.is_closed = lambda: False
    context = FakeTarget()

    class FakeRuntime:
        def __init__(self) -> None:
            self.page = page
            self.context = context

        def navigate(self, _url: str) -> None:
            page.listeners["load"]()
            return None

        def current_url(self) -> str:
            return "https://example.invalid/done"

        def current_title(self) -> str:
            return "Done"

    analysis = PageAnalysis(
        url="https://example.invalid/start",
        title="Start",
        total_visible=0,
        total_hidden=0,
        fillable=[],
        submit=[],
        clickable=[],
        navigation=[],
        select=[],
        toggle=[],
        other=[],
    )
    action = SimpleNamespace(
        step=0,
        action_type="click",
        target_selector="button",
        target_description="Search",
        value=None,
        reason="test",
        model_dump=lambda: {
            "step": 0,
            "action_type": "click",
            "target_selector": "button",
        },
    )

    def fake_execute_action(_action, runtime):
        runtime.page.listeners["request"](
            SimpleNamespace(
                url="https://example.invalid/search?token=secret&status=active",
                method="GET",
                resource_type="xhr",
                headers={},
            )
        )
        return {
            "step_index": 0,
            "action_type": "click",
            "ok": True,
            "url_changed": True,
            "title_changed": False,
        }

    monkeypatch.setattr(ae.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(ae, "analyze_page", lambda _runtime: analysis)
    monkeypatch.setattr(ae, "plan_actions", lambda *_args, **_kwargs: [action])
    monkeypatch.setattr(ae, "execute_action", fake_execute_action)
    monkeypatch.setattr(ae, "safe_screenshot", lambda _runtime: None)
    monkeypatch.setattr(ae, "_capture_final_state", lambda _runtime: {})
    monkeypatch.setattr(ae, "_run_supervisor", lambda *_args, **_kwargs: {"verdict": "success"})

    result = ae.run_autonomous_exploration(
        "https://example.invalid/start",
        FakeRuntime(),
    )

    timeline = result.browser_event_timeline
    assert timeline is not None
    assert timeline["status"] == "recording_available"
    assert timeline["event_count"] == 1
    event = timeline["events"][0]
    assert event["event_type"] == "request"
    assert event["action_id"] == "action-step-0"
    assert event["step_index"] == 0
    assert event["action_type"] == "click"
    assert event["metadata"]["url"]["secret_query_keys"] == ["token"]
    assert "token=secret" not in str(timeline)
    assert "status=active" not in str(timeline)

    terminal_state = result.terminal_state_verdict
    assert terminal_state is not None
    assert terminal_state["terminal_outcome"] == "not_terminal_yet"
    assert terminal_state["terminal_type"] == "network_completion"
    assert terminal_state["stop_decision"] == "wait"
    assert terminal_state["needs_more_wait"] is True
