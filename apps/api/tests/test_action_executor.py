"""Tests for the shared action executor."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.services.execution.action_executor import (
    execute_action,
    observe_step,
    safe_screenshot,
)
from app.services.execution.execution_runtime import create_execution_runtime

# ── Helpers ──────────────────────────────────────────────────────────────────

DATA_URL = (
    'data:text/html,<html><head><title>Test Page</title></head>'
    '<body><input id="name" type="text">'
    '<select id="status"><option value="">All</option>'
    '<option value="active">Active</option></select>'
    '<button id="btn">Click</button>'
    '<form id="form"><input id="field" type="text"></form>'
    '</body></html>'
)


def _make_action(**kwargs):
    class _FakeAction:
        pass

    a = _FakeAction()
    a.step = kwargs.get("step", 0)
    a.action_type = kwargs.get("action_type", "click")
    a.target_selector = kwargs.get("target_selector", "#btn")
    a.target_description = kwargs.get("target_description", "")
    a.value = kwargs.get("value", None)
    a.reason = kwargs.get("reason", "")
    return a


# ── safe_screenshot ──────────────────────────────────────────────────────────


def test_safe_screenshot_returns_path_when_runtime_active() -> None:
    rt = create_execution_runtime()
    rt.start()
    try:
        rt.navigate(DATA_URL)
        path = safe_screenshot(rt)
        assert path is not None
        assert path.endswith(".png")
    finally:
        rt.stop()


def test_safe_screenshot_returns_none_when_runtime_not_started() -> None:
    rt = create_execution_runtime()
    # runtime not started — screenshot should fail gracefully
    path = safe_screenshot(rt)
    assert path is None


# ── execute_action: fill ─────────────────────────────────────────────────────


def test_execute_action_fill() -> None:
    rt = create_execution_runtime()
    rt.start()
    try:
        rt.navigate(DATA_URL)
        action = _make_action(
            action_type="fill",
            target_selector="#name",
            value="Alice",
        )
        log = execute_action(action, rt)

        assert log["ok"] is True
        assert log["action_type"] == "fill"
        assert log["actual_value"] == "Alice"
        assert log["matched_count"] == 1
        assert "url_before" in log
        assert "url_after" in log
    finally:
        rt.stop()


# ── execute_action: select ───────────────────────────────────────────────────


def test_execute_action_select() -> None:
    page = MagicMock()
    page.is_closed.return_value = False
    page.url = "https://example.invalid/users"
    page.title.return_value = "Users"

    locator = MagicMock()
    locator.count.return_value = 1
    locator.first = MagicMock()
    locator.first.input_value.return_value = "active"
    page.locator.return_value = locator

    rt = MagicMock()
    rt.page = page
    rt.screenshot.return_value = None

    action = _make_action(
        action_type="select",
        target_selector="#status",
        value="active",
    )
    log = execute_action(action, rt)

    assert log["ok"] is True
    assert log["action_type"] == "select"
    assert log["actual_value"] == "active"
    assert log["matched_count"] == 1
    locator.first.select_option.assert_called_once_with("active")


def test_execute_action_set_value_dispatches_dom_events() -> None:
    page = MagicMock()
    page.is_closed.return_value = False
    page.url = "https://example.invalid/users"
    page.title.return_value = "Users"

    locator = MagicMock()
    locator.count.return_value = 1
    locator.first = MagicMock()
    locator.first.input_value.return_value = "2026-01-01"
    page.locator.return_value = locator

    rt = MagicMock()
    rt.page = page
    rt.screenshot.return_value = None

    action = _make_action(
        action_type="set_value",
        target_selector="#registered",
        value="2026-01-01",
    )
    log = execute_action(action, rt)

    assert log["ok"] is True
    assert log["actual_value"] == "2026-01-01"
    locator.first.evaluate.assert_called_once()


def test_execute_action_select_first_option_uses_popup_option() -> None:
    page = MagicMock()
    page.is_closed.return_value = False
    page.url = "https://example.invalid/users"
    page.title.return_value = "Users"
    page.evaluate.return_value = {"selected": True, "text": "Admin"}

    locator = MagicMock()
    locator.count.return_value = 1
    locator.first = MagicMock()
    page.locator.return_value = locator

    rt = MagicMock()
    rt.page = page
    rt.screenshot.return_value = None

    action = _make_action(
        action_type="select_first_option",
        target_selector="#role",
        value="admin",
    )
    log = execute_action(action, rt)

    assert log["ok"] is True
    assert log["selected_option"] == {"selected": True, "text": "Admin"}
    locator.first.click.assert_called_once()


# ── execute_action: click ────────────────────────────────────────────────────


def test_execute_action_click() -> None:
    rt = create_execution_runtime()
    rt.start()
    try:
        rt.navigate(DATA_URL)
        action = _make_action(
            action_type="click",
            target_selector="#btn",
        )
        log = execute_action(action, rt)

        assert log["ok"] is True
        assert log["action_type"] == "click"
        assert log["matched_count"] == 1
    finally:
        rt.stop()


# ── execute_action: press ────────────────────────────────────────────────────


def test_execute_action_press() -> None:
    rt = create_execution_runtime()
    rt.start()
    try:
        rt.navigate(DATA_URL)
        # focus the input first via click, then press
        click_action = _make_action(
            action_type="click",
            target_selector="#name",
        )
        execute_action(click_action, rt)

        press_action = _make_action(
            action_type="press",
            target_selector="#name",
            value="Enter",
        )
        log = execute_action(press_action, rt)

        assert log["ok"] is True
        assert log["action_type"] == "press"
    finally:
        rt.stop()


# ── execute_action: observe ──────────────────────────────────────────────────


def test_execute_action_observe() -> None:
    rt = create_execution_runtime()
    rt.start()
    try:
        rt.navigate(DATA_URL)
        action = _make_action(
            action_type="observe",
            target_selector="",
        )
        log = execute_action(action, rt)

        assert log["ok"] is True
        assert log["action_type"] == "observe"
        assert "url" in log
        assert "title" in log
        assert "screenshot_ref" in log
    finally:
        rt.stop()


def test_observe_step_standalone() -> None:
    rt = create_execution_runtime()
    rt.start()
    try:
        rt.navigate(DATA_URL)
        log = observe_step(rt, step_index=3)

        assert log["ok"] is True
        assert log["step_index"] == 3
        assert log["action_type"] == "observe"
        assert log["url"] == DATA_URL
        assert "screenshot_ref" in log
    finally:
        rt.stop()


# ── execute_action: selector missing ─────────────────────────────────────────


def test_execute_action_selector_missing() -> None:
    rt = create_execution_runtime()
    rt.start()
    try:
        rt.navigate(DATA_URL)
        action = _make_action(
            action_type="click",
            target_selector="#does-not-exist",
        )
        log = execute_action(action, rt)

        assert log["ok"] is False
        assert "matched 0 elements" in log["error"]
        assert log.get("screenshot_ref") is not None or log.get("screenshot_ref") is None
    finally:
        rt.stop()


# ── execute_action: unknown action ───────────────────────────────────────────


def test_execute_action_unknown_action() -> None:
    rt = create_execution_runtime()
    rt.start()
    try:
        rt.navigate(DATA_URL)
        action = _make_action(
            action_type="swipe",
            target_selector="#btn",
        )
        log = execute_action(action, rt)

        assert log["ok"] is False
        assert "Unknown action type" in log["error"]
    finally:
        rt.stop()


# ── execute_action: no page available ────────────────────────────────────────


def test_execute_action_no_page() -> None:
    rt = create_execution_runtime()
    # Do not start — page is None
    action = _make_action(action_type="click")
    log = execute_action(action, rt)

    assert log["ok"] is False
    assert "No page available" in log["error"]


def test_execute_action_after_page_closed() -> None:
    rt = create_execution_runtime()
    rt.start()
    rt.stop()
    action = _make_action(action_type="click")
    log = execute_action(action, rt)

    assert log["ok"] is False
    assert "No page available" in log["error"]


# ── execute_action: step log fields compatible ───────────────────────────────


def test_execute_action_step_log_fields() -> None:
    rt = create_execution_runtime()
    rt.start()
    try:
        rt.navigate(DATA_URL)
        action = _make_action(
            step=5,
            action_type="fill",
            target_selector="#name",
            target_description="Name input",
            value="Bob",
            reason="Enter name",
        )
        log = execute_action(action, rt)

        assert log["step_index"] == 5
        assert log["action_type"] == "fill"
        assert log["target_selector"] == "#name"
        assert log["target_description"] == "Name input"
        assert log["value"] == "Bob"
        assert log["plan_reason"] == "Enter name"
        assert "timestamp_ms" in log
        assert "url_before" in log
        assert "url_after" in log
        assert "title_before" in log
        assert "title_after" in log
        assert "url_changed" in log
        assert "title_changed" in log
        assert "screenshot_ref" in log
    finally:
        rt.stop()
