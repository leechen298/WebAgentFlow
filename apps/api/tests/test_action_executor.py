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
