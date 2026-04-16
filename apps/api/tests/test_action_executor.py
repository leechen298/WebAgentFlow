"""
Tests for the action executor (Phase 7D).

Covers:
1.  click succeeds
2.  fill succeeds
3.  select succeeds
4.  check / uncheck succeed
5.  hover succeeds
6.  press succeeds
7.  navigate succeeds (page-level, no locator)
8.  locator resolution failure → structured error
9.  unsupported action type → structured error
10. fill without value → structured error
11. press without key → structured error
12. before/after URL and title captured
13. degraded locator warning propagated
14. result serializable
15. elapsed_ms populated

All tests use data: URLs — no real websites, no LLM calls.
"""

import pytest

from app.schemas.execution import (
    ActionTarget,
    ExecutionRequest,
    ExecutionResult,
    LocatorHint,
    PageSnapshot,
)
from app.services.action_executor import execute_action
from app.services.execution_runtime import create_execution_runtime


# ---------------------------------------------------------------------------
# Test page HTML fixtures
# ---------------------------------------------------------------------------

ACTION_PAGE = """data:text/html,
<html><head><title>Action Test</title></head><body>
  <button id="btn-save" onclick="document.title='Saved'">Save</button>
  <input id="name-input" placeholder="Your name" value="" />
  <select id="color-select">
    <option value="red">Red</option>
    <option value="blue">Blue</option>
    <option value="green">Green</option>
  </select>
  <input type="checkbox" id="agree-cb" />
  <label for="agree-cb">I agree</label>
  <div id="hover-target" onmouseenter="document.getElementById('hover-msg').style.display='block'">Hover me</div>
  <div id="hover-msg" style="display:none">Hovered!</div>
  <input id="key-input" value="" onkeydown="if(event.key==='Enter')document.title='Pressed'" />
</body></html>"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _req(
    *,
    action_type: str = "click",
    target_desc: str = '<button> "Save"',
    value: str | None = None,
    hints: list[LocatorHint] | None = None,
) -> ExecutionRequest:
    if hints is None:
        # Default: provide an id-based hint for #btn-save
        hints = [LocatorHint(
            strategy="STRONG_ATTRIBUTE",
            value="id=btn-save",
            confidence="high",
            meta={"attribute": "id"},
        )]
    return ExecutionRequest(
        page=PageSnapshot(url="about:blank"),
        action=ActionTarget(
            action_type=action_type,
            target_description=target_desc,
            value=value,
        ),
        locator_hints=hints,
        recording_id="test",
    )


def _hint_for_id(element_id: str) -> list[LocatorHint]:
    return [LocatorHint(
        strategy="STRONG_ATTRIBUTE",
        value=f"id={element_id}",
        confidence="high",
        meta={"attribute": "id"},
    )]


# ---------------------------------------------------------------------------
# 1. click succeeds
# ---------------------------------------------------------------------------

class TestClick:
    def test_click_button(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            req = _req(action_type="click", hints=_hint_for_id("btn-save"))
            result = execute_action(req, rt)
            assert result.ok
            assert result.action_type == "click"
            # The onclick handler changes the title to "Saved"
            assert rt.current_title() == "Saved"

    def test_click_records_before_after(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            req = _req(action_type="click", hints=_hint_for_id("btn-save"))
            result = execute_action(req, rt)
            assert result.page_change.title_before == "Action Test"
            assert result.page_change.title_after == "Saved"


# ---------------------------------------------------------------------------
# 2. fill succeeds
# ---------------------------------------------------------------------------

class TestFill:
    def test_fill_input(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            req = _req(
                action_type="fill",
                target_desc='<input> "name"',
                value="Alice",
                hints=_hint_for_id("name-input"),
            )
            result = execute_action(req, rt)
            assert result.ok
            assert result.action_type == "fill"
            # Verify the value was actually filled
            val = rt.page.locator("#name-input").input_value()
            assert val == "Alice"

    def test_fill_without_value_fails(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            req = _req(
                action_type="fill",
                value=None,
                hints=_hint_for_id("name-input"),
            )
            result = execute_action(req, rt)
            assert not result.ok
            assert "value" in result.error.lower()


# ---------------------------------------------------------------------------
# 3. select succeeds
# ---------------------------------------------------------------------------

class TestSelect:
    def test_select_option(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            req = _req(
                action_type="select",
                target_desc="<select>",
                value="blue",
                hints=_hint_for_id("color-select"),
            )
            result = execute_action(req, rt)
            assert result.ok
            assert result.action_type == "select"

    def test_select_without_value_fails(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            req = _req(
                action_type="select",
                value=None,
                hints=_hint_for_id("color-select"),
            )
            result = execute_action(req, rt)
            assert not result.ok
            assert "value" in result.error.lower()


# ---------------------------------------------------------------------------
# 4. check / uncheck succeed
# ---------------------------------------------------------------------------

class TestCheckUncheck:
    def test_check_checkbox(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            req = _req(
                action_type="check",
                target_desc="<input> checkbox",
                hints=_hint_for_id("agree-cb"),
            )
            result = execute_action(req, rt)
            assert result.ok
            assert rt.page.locator("#agree-cb").is_checked()

    def test_uncheck_checkbox(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            # First check it
            rt.page.locator("#agree-cb").check()
            assert rt.page.locator("#agree-cb").is_checked()
            # Then uncheck
            req = _req(
                action_type="uncheck",
                target_desc="<input> checkbox",
                hints=_hint_for_id("agree-cb"),
            )
            result = execute_action(req, rt)
            assert result.ok
            assert not rt.page.locator("#agree-cb").is_checked()


# ---------------------------------------------------------------------------
# 5. hover succeeds
# ---------------------------------------------------------------------------

class TestHover:
    def test_hover_shows_element(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            req = _req(
                action_type="hover",
                target_desc="<div> hover target",
                hints=_hint_for_id("hover-target"),
            )
            result = execute_action(req, rt)
            assert result.ok
            assert result.action_type == "hover"
            # The onmouseenter handler shows the hover-msg div
            assert rt.page.locator("#hover-msg").is_visible()


# ---------------------------------------------------------------------------
# 6. press succeeds
# ---------------------------------------------------------------------------

class TestPress:
    def test_press_enter(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            # Focus the input first
            rt.page.locator("#key-input").focus()
            req = _req(
                action_type="press",
                target_desc="<input> key input",
                value="Enter",
                hints=_hint_for_id("key-input"),
            )
            result = execute_action(req, rt)
            assert result.ok
            assert rt.current_title() == "Pressed"

    def test_press_without_key_fails(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            req = _req(
                action_type="press",
                value=None,
                hints=_hint_for_id("key-input"),
            )
            result = execute_action(req, rt)
            assert not result.ok
            assert "key" in result.error.lower() or "value" in result.error.lower()


# ---------------------------------------------------------------------------
# 7. navigate succeeds
# ---------------------------------------------------------------------------

class TestNavigate:
    def test_navigate_to_url(self):
        target_url = 'data:text/html,<html><head><title>New Page</title></head><body>OK</body></html>'
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            req = _req(
                action_type="navigate",
                value=target_url,
                hints=[],  # navigate doesn't need locator hints
            )
            result = execute_action(req, rt)
            assert result.ok
            assert result.action_type == "navigate"
            assert result.page_change.title_before == "Action Test"
            assert rt.current_title() == "New Page"


# ---------------------------------------------------------------------------
# 8. locator resolution failure
# ---------------------------------------------------------------------------

class TestLocatorFailure:
    def test_no_matching_element(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            req = _req(
                action_type="click",
                hints=_hint_for_id("nonexistent-element"),
            )
            result = execute_action(req, rt)
            assert not result.ok
            assert "Locator resolution failed" in result.error
            assert result.locator.strategy_used == ""


# ---------------------------------------------------------------------------
# 9. unsupported action type
# ---------------------------------------------------------------------------

class TestUnsupportedAction:
    def test_unknown_action_type_rejected_by_schema(self):
        """Invalid action types are caught by Pydantic Literal validation."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="literal_error"):
            ActionTarget(action_type="drag", target_description="something")


# ---------------------------------------------------------------------------
# 10. degraded locator warning propagated
# ---------------------------------------------------------------------------

class TestDegradedWarning:
    def test_fallback_selector_produces_warning(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            req = _req(
                action_type="click",
                hints=[LocatorHint(
                    strategy="FALLBACK_SELECTOR",
                    value="#btn-save",
                    confidence="low",
                    meta={},
                )],
            )
            result = execute_action(req, rt)
            assert result.ok
            assert any("Degraded" in w or "degraded" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# 11. result serializable
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_success_round_trip(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            req = _req(action_type="click", hints=_hint_for_id("btn-save"))
            result = execute_action(req, rt)
            data = result.model_dump()
            restored = ExecutionResult.model_validate(data)
            assert restored.ok == result.ok
            assert restored.action_type == "click"
            assert restored.locator.strategy_used == result.locator.strategy_used

    def test_failure_round_trip(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            req = _req(action_type="click", hints=_hint_for_id("ghost"))
            result = execute_action(req, rt)
            data = result.model_dump()
            restored = ExecutionResult.model_validate(data)
            assert not restored.ok
            assert restored.error is not None


# ---------------------------------------------------------------------------
# 12. elapsed_ms populated
# ---------------------------------------------------------------------------

class TestTiming:
    def test_elapsed_ms_present(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            req = _req(action_type="click", hints=_hint_for_id("btn-save"))
            result = execute_action(req, rt)
            assert result.elapsed_ms is not None
            assert result.elapsed_ms >= 0


# ---------------------------------------------------------------------------
# 13. Mocked tests — action handler edge cases
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock, patch, PropertyMock
from app.schemas.execution import LocatorResult, PageStateChange


class TestScrollAction:
    """scroll action type."""

    def test_scroll_succeeds(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            req = _req(
                action_type="scroll",
                target_desc="<button> save",
                hints=_hint_for_id("btn-save"),
            )
            result = execute_action(req, rt)
            assert result.ok
            assert result.action_type == "scroll"


class TestSelectWithoutValue:
    """select action with None value."""

    def test_select_none_value_fails(self):
        with create_execution_runtime() as rt:
            rt.navigate(ACTION_PAGE)
            req = _req(
                action_type="select",
                target_desc="<select>",
                value=None,
                hints=_hint_for_id("color-select"),
            )
            result = execute_action(req, rt)
            assert not result.ok
            assert "value" in result.error.lower()


class TestCapturePageState:
    """Test _capture_page_state error tolerance."""

    def test_capture_state_url_error(self):
        from app.services.action_executor import _capture_page_state
        rt = MagicMock()
        rt.current_url.side_effect = Exception("no url")
        rt.current_title.return_value = "Title"
        url, title = _capture_page_state(rt)
        assert url == ""
        assert title == "Title"

    def test_capture_state_title_error(self):
        from app.services.action_executor import _capture_page_state
        rt = MagicMock()
        rt.current_url.return_value = "http://ex.com"
        rt.current_title.side_effect = Exception("no title")
        url, title = _capture_page_state(rt)
        assert url == "http://ex.com"
        assert title == ""

    def test_capture_state_both_error(self):
        from app.services.action_executor import _capture_page_state
        rt = MagicMock()
        rt.current_url.side_effect = Exception("no url")
        rt.current_title.side_effect = Exception("no title")
        url, title = _capture_page_state(rt)
        assert url == ""
        assert title == ""


class TestUnsupportedActionMocked:
    """Test unsupported action type via mocked locator to bypass schema validation."""

    def test_unknown_action_handler_returns_error(self):
        """If action_type is not in _ACTION_HANDLERS, returns error result."""
        from app.services.action_executor import execute_action

        rt = MagicMock()
        rt.current_url.return_value = "http://example.com"
        rt.current_title.return_value = "Test"
        rt.page = MagicMock()
        rt.page.is_closed.return_value = False

        # Build a valid request but monkey-patch the action_type after creation
        req = _req(action_type="click")
        req.action.action_type = "drag_and_drop"  # not in handlers

        # Mock resolve_locator to succeed
        from app.schemas.locator import ResolvedLocator, SelectorDescriptor
        mock_resolved = ResolvedLocator(
            ok=True, source="STRONG_ATTRIBUTE", confidence="high",
            descriptor=SelectorDescriptor(selector_type="css", selector="#btn"),
            matched_count=1, fallback_used=False,
        )
        with patch("app.services.execution.action_executor.resolve_locator", return_value=mock_resolved):
            result = execute_action(req, rt)
        assert not result.ok
        assert "Unsupported action type" in result.error


class TestPlaywrightErrorHandling:
    """Test Playwright error classification in execute_action."""

    def _make_pw_error(self, msg):
        from playwright.sync_api import Error as PlaywrightError
        return PlaywrightError(msg)

    def test_detached_element_error(self):
        from app.services.action_executor import execute_action
        from app.schemas.locator import ResolvedLocator, SelectorDescriptor

        rt = MagicMock()
        rt.current_url.return_value = "http://ex.com"
        rt.current_title.return_value = "Test"
        rt.page = MagicMock()
        rt.page.is_closed.return_value = False

        mock_resolved = ResolvedLocator(
            ok=True, source="STRONG_ATTRIBUTE", confidence="high",
            descriptor=SelectorDescriptor(selector_type="css", selector="#btn"),
            matched_count=1, fallback_used=False,
        )

        mock_locator = MagicMock()
        mock_locator.click.side_effect = self._make_pw_error("Element is detached from DOM")

        with patch("app.services.execution.action_executor.resolve_locator", return_value=mock_resolved):
            with patch("app.services.execution.action_executor.to_playwright_locator", return_value=mock_locator):
                req = _req(action_type="click")
                result = execute_action(req, rt)
        assert not result.ok
        assert any("detached" in t for t in result.trace)

    def test_not_visible_error(self):
        from app.services.action_executor import execute_action
        from app.schemas.locator import ResolvedLocator, SelectorDescriptor

        rt = MagicMock()
        rt.current_url.return_value = ""
        rt.current_title.return_value = ""
        rt.page = MagicMock()
        rt.page.is_closed.return_value = False

        mock_resolved = ResolvedLocator(
            ok=True, source="STRONG_ATTRIBUTE", confidence="high",
            descriptor=SelectorDescriptor(selector_type="css", selector="#btn"),
            matched_count=1, fallback_used=False,
        )
        mock_locator = MagicMock()
        mock_locator.click.side_effect = self._make_pw_error("Element is not visible or hidden")

        with patch("app.services.execution.action_executor.resolve_locator", return_value=mock_resolved):
            with patch("app.services.execution.action_executor.to_playwright_locator", return_value=mock_locator):
                result = execute_action(_req(action_type="click"), rt)
        assert not result.ok
        assert any("not visible" in t for t in result.trace)

    def test_timeout_error(self):
        from app.services.action_executor import execute_action
        from app.schemas.locator import ResolvedLocator, SelectorDescriptor

        rt = MagicMock()
        rt.current_url.return_value = ""
        rt.current_title.return_value = ""
        rt.page = MagicMock()
        rt.page.is_closed.return_value = False

        mock_resolved = ResolvedLocator(
            ok=True, source="STRONG_ATTRIBUTE", confidence="high",
            descriptor=SelectorDescriptor(selector_type="css", selector="#btn"),
            matched_count=1, fallback_used=False,
        )
        mock_locator = MagicMock()
        mock_locator.click.side_effect = self._make_pw_error("Timeout 30000ms exceeded")

        with patch("app.services.execution.action_executor.resolve_locator", return_value=mock_resolved):
            with patch("app.services.execution.action_executor.to_playwright_locator", return_value=mock_locator):
                result = execute_action(_req(action_type="click"), rt)
        assert not result.ok
        assert any("timed out" in t for t in result.trace)

    def test_generic_playwright_error(self):
        """A Playwright error that doesn't match detached/visible/timeout."""
        from app.services.action_executor import execute_action
        from app.schemas.locator import ResolvedLocator, SelectorDescriptor

        rt = MagicMock()
        rt.current_url.return_value = ""
        rt.current_title.return_value = ""
        rt.page = MagicMock()
        rt.page.is_closed.return_value = False

        mock_resolved = ResolvedLocator(
            ok=True, source="STRONG_ATTRIBUTE", confidence="high",
            descriptor=SelectorDescriptor(selector_type="css", selector="#btn"),
            matched_count=1, fallback_used=False,
        )
        mock_locator = MagicMock()
        mock_locator.click.side_effect = self._make_pw_error("Some other Playwright error")

        with patch("app.services.execution.action_executor.resolve_locator", return_value=mock_resolved):
            with patch("app.services.execution.action_executor.to_playwright_locator", return_value=mock_locator):
                result = execute_action(_req(action_type="click"), rt)
        assert not result.ok
        assert "Some other Playwright error" in result.error

    def test_unexpected_exception(self):
        """A non-Playwright, non-ValueError exception."""
        from app.services.action_executor import execute_action
        from app.schemas.locator import ResolvedLocator, SelectorDescriptor

        rt = MagicMock()
        rt.current_url.return_value = ""
        rt.current_title.return_value = ""
        rt.page = MagicMock()
        rt.page.is_closed.return_value = False

        mock_resolved = ResolvedLocator(
            ok=True, source="STRONG_ATTRIBUTE", confidence="high",
            descriptor=SelectorDescriptor(selector_type="css", selector="#btn"),
            matched_count=1, fallback_used=False,
        )
        mock_locator = MagicMock()
        mock_locator.click.side_effect = RuntimeError("something went wrong")

        with patch("app.services.execution.action_executor.resolve_locator", return_value=mock_resolved):
            with patch("app.services.execution.action_executor.to_playwright_locator", return_value=mock_locator):
                result = execute_action(_req(action_type="click"), rt)
        assert not result.ok
        assert "Unexpected error" in result.error


class TestValueErrorInAction:
    """ValueErrors raised during fill/press/select are captured."""

    def test_fill_value_error_captured(self):
        from app.services.action_executor import execute_action
        from app.schemas.locator import ResolvedLocator, SelectorDescriptor

        rt = MagicMock()
        rt.current_url.return_value = ""
        rt.current_title.return_value = ""
        rt.page = MagicMock()
        rt.page.is_closed.return_value = False

        mock_resolved = ResolvedLocator(
            ok=True, source="STRONG_ATTRIBUTE", confidence="high",
            descriptor=SelectorDescriptor(selector_type="css", selector="#inp"),
            matched_count=1, fallback_used=False,
        )
        mock_locator = MagicMock()
        # fill calls locator.fill(value), but value is None
        mock_locator.fill.side_effect = ValueError("fill requires a value")

        with patch("app.services.execution.action_executor.resolve_locator", return_value=mock_resolved):
            with patch("app.services.execution.action_executor.to_playwright_locator", return_value=mock_locator):
                req = _req(action_type="fill", value="test")
                result = execute_action(req, rt)
        assert not result.ok
        assert "fill requires a value" in result.error


class TestNavigateActionMocked:
    """Mocked navigate action edge cases."""

    def test_navigate_uses_page_url_fallback(self):
        """When action.value is None, navigate falls back to request.page.url."""
        from app.services.action_executor import execute_action

        rt = MagicMock()
        rt.current_url.return_value = "http://old.com"
        rt.current_title.return_value = "Old"
        rt.page = MagicMock()
        rt.page.is_closed.return_value = False

        req = _req(action_type="navigate", value=None, hints=[])
        req.page.url = "http://target.com"

        result = execute_action(req, rt)
        assert result.ok
        rt.page.goto.assert_called_with("http://target.com", wait_until="load")

    def test_navigate_no_url_at_all(self):
        """navigate with both action.value=None and page.url empty raises ValueError."""
        from app.services.action_executor import execute_action

        rt = MagicMock()
        rt.current_url.return_value = ""
        rt.current_title.return_value = ""
        rt.page = MagicMock()
        rt.page.is_closed.return_value = False

        req = _req(action_type="navigate", value=None, hints=[])
        req.page.url = ""

        result = execute_action(req, rt)
        assert not result.ok
        assert "URL" in result.error or "url" in result.error.lower()
