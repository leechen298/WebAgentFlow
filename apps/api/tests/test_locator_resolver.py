"""
Tests for the locator resolver (Phase 7C).

Covers:
1. SERVER_AST_MATCH strategy — role-based and CSS :has-text
2. STRONG_ATTRIBUTE strategy — id, name, placeholder
3. TAG_TEXT_LABEL strategy — tag + text, role + name
4. REGION_SCOPED strategy — narrow search to a named region
5. FALLBACK_SELECTOR strategy — recorded CSS selector
6. CLIENT_AST_MATCH strategy — degraded path, always last
7. Priority ordering — higher priority wins even when lower would match
8. Multiple same-text elements — disambiguation
9. Resolution failure — structured failure result
10. No locator hints — graceful failure
11. Output serialization round-trip

All tests use data: URLs — no real websites, no LLM calls.
"""

import pytest

from app.schemas.execution import (
    ActionTarget,
    ExecutionRequest,
    LocatorHint,
    LocatorPriority,
    PageSnapshot,
)
from app.schemas.locator import ResolvedLocator, SelectorDescriptor
from app.services.execution_runtime import create_execution_runtime
from app.services.locator_resolver import resolve_locator


# ---------------------------------------------------------------------------
# Test page HTML fixtures
# ---------------------------------------------------------------------------

SIMPLE_PAGE = """data:text/html,
<html><head><title>Test</title></head><body>
  <button id="btn-save">Save</button>
  <button id="btn-cancel">Cancel</button>
  <a href="/home">Home</a>
  <input name="username" placeholder="Enter username" />
  <select name="country"><option>China</option><option>USA</option></select>
</body></html>"""

FORM_PAGE = """data:text/html,
<html><head><title>Form</title></head><body>
  <section aria-label="User Info">
    <h2>User Info</h2>
    <input placeholder="First name" />
    <input placeholder="Last name" />
    <button>Save</button>
  </section>
  <section aria-label="Settings">
    <h2>Settings</h2>
    <input placeholder="Email" />
    <button>Save</button>
  </section>
</body></html>"""

CONFLICT_PAGE = """data:text/html,
<html><head><title>Conflict</title></head><body>
  <button>Submit</button>
  <button>Submit</button>
  <button>Submit</button>
</body></html>"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _req(
    *,
    hints: list[LocatorHint] | None = None,
    action_type: str = "click",
    target_desc: str = '<button> "Save"',
) -> ExecutionRequest:
    return ExecutionRequest(
        page=PageSnapshot(url="about:blank"),
        action=ActionTarget(action_type=action_type, target_description=target_desc),
        locator_hints=hints or [],
        recording_id="test",
    )


def _hint(
    strategy: str,
    value: str,
    confidence: str = "high",
    meta: dict | None = None,
) -> LocatorHint:
    return LocatorHint(
        strategy=strategy,
        value=value,
        confidence=confidence,
        meta=meta or {},
    )


# ---------------------------------------------------------------------------
# 1. SERVER_AST_MATCH — role-based and CSS :has-text
# ---------------------------------------------------------------------------

class TestServerAstMatch:
    def test_role_based_match(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hint = _hint(
                "SERVER_AST_MATCH", "0.0",
                meta={"tag": "button", "label": "Save", "match_type": "exact"},
            )
            result = resolve_locator(_req(hints=[hint]), rt)
            assert result.ok
            assert result.source == "SERVER_AST_MATCH"
            assert result.matched_tag == "button"

    def test_no_tag_skips(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hint = _hint("SERVER_AST_MATCH", "0.0", meta={"match_type": "exact"})
            result = resolve_locator(_req(hints=[hint]), rt)
            assert not result.ok
            assert any("no tag" in t for t in result.trace)


# ---------------------------------------------------------------------------
# 2. STRONG_ATTRIBUTE — id, name, placeholder
# ---------------------------------------------------------------------------

class TestStrongAttribute:
    def test_id_match(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hint = _hint("STRONG_ATTRIBUTE", "id=btn-save", meta={"attribute": "id"})
            result = resolve_locator(_req(hints=[hint]), rt)
            assert result.ok
            assert result.source == "STRONG_ATTRIBUTE"
            assert result.confidence == "high"

    def test_name_match(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hint = _hint("STRONG_ATTRIBUTE", "name=username", meta={"attribute": "name", "tag": "input"})
            result = resolve_locator(_req(hints=[hint]), rt)
            assert result.ok
            assert result.source == "STRONG_ATTRIBUTE"

    def test_placeholder_match(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hint = _hint("STRONG_ATTRIBUTE", "placeholder=Enter username", meta={"attribute": "placeholder"})
            result = resolve_locator(_req(hints=[hint]), rt)
            assert result.ok
            assert result.descriptor is not None
            assert result.descriptor.selector_type == "placeholder"

    def test_nonexistent_id(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hint = _hint("STRONG_ATTRIBUTE", "id=does-not-exist", meta={"attribute": "id"})
            result = resolve_locator(_req(hints=[hint]), rt)
            assert not result.ok


# ---------------------------------------------------------------------------
# 3. TAG_TEXT_LABEL — tag + text, role + name
# ---------------------------------------------------------------------------

class TestTagTextLabel:
    def test_button_text(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hint = _hint("TAG_TEXT_LABEL", "button::Save", meta={"tag": "button"})
            result = resolve_locator(_req(hints=[hint]), rt)
            assert result.ok
            assert result.source == "TAG_TEXT_LABEL"

    def test_link_text(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hint = _hint("TAG_TEXT_LABEL", "a::Home", meta={"tag": "a"})
            result = resolve_locator(_req(hints=[hint]), rt)
            assert result.ok

    def test_no_match(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hint = _hint("TAG_TEXT_LABEL", "button::NonExistent", meta={"tag": "button"})
            result = resolve_locator(_req(hints=[hint]), rt)
            assert not result.ok


# ---------------------------------------------------------------------------
# 4. REGION_SCOPED — narrow search to a named region
# ---------------------------------------------------------------------------

class TestRegionScoped:
    def test_disambiguate_save_buttons(self):
        """Two 'Save' buttons in different sections — region narrows it."""
        with create_execution_runtime() as rt:
            rt.navigate(FORM_PAGE)
            hint = _hint("REGION_SCOPED", "Settings")
            req = _req(hints=[hint], target_desc='<button> "Save"')
            result = resolve_locator(req, rt)
            # Should find a match scoped to the Settings section
            assert result.ok
            assert result.source == "REGION_SCOPED"

    def test_region_not_found(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hint = _hint("REGION_SCOPED", "NonExistentRegion")
            result = resolve_locator(_req(hints=[hint], target_desc='<button> "Save"'), rt)
            assert not result.ok


# ---------------------------------------------------------------------------
# 5. FALLBACK_SELECTOR — recorded CSS selector
# ---------------------------------------------------------------------------

class TestFallbackSelector:
    def test_css_selector_match(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hint = _hint("FALLBACK_SELECTOR", "#btn-save")
            result = resolve_locator(_req(hints=[hint]), rt)
            assert result.ok
            assert result.source == "FALLBACK_SELECTOR"
            assert result.fallback_used

    def test_empty_selector(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hint = _hint("FALLBACK_SELECTOR", "")
            result = resolve_locator(_req(hints=[hint]), rt)
            assert not result.ok


# ---------------------------------------------------------------------------
# 6. CLIENT_AST_MATCH — degraded, always last
# ---------------------------------------------------------------------------

class TestClientAstMatch:
    def test_text_match(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hint = _hint(
                "CLIENT_AST_MATCH", "n42",
                meta={"source": "client_ast_match", "nodeLabel": "Save"},
            )
            result = resolve_locator(_req(hints=[hint]), rt)
            assert result.ok
            assert result.source == "CLIENT_AST_MATCH"
            assert result.fallback_used
            assert any("degraded" in t.lower() or "CLIENT_AST_MATCH" in t for t in result.trace)

    def test_no_node_label(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hint = _hint("CLIENT_AST_MATCH", "n42", meta={})
            result = resolve_locator(_req(hints=[hint]), rt)
            assert not result.ok


# ---------------------------------------------------------------------------
# 7. Priority ordering — higher wins
# ---------------------------------------------------------------------------

class TestPriorityOrdering:
    def test_server_ast_match_wins_over_strong_attribute(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hints = [
                _hint("SERVER_AST_MATCH", "0.0", meta={"tag": "button", "label": "Save", "match_type": "exact"}),
                _hint("STRONG_ATTRIBUTE", "id=btn-save", meta={"attribute": "id"}),
            ]
            result = resolve_locator(_req(hints=hints), rt)
            assert result.ok
            assert result.source == "SERVER_AST_MATCH"

    def test_fallback_to_lower_priority(self):
        """SERVER_AST_MATCH fails, STRONG_ATTRIBUTE succeeds."""
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hints = [
                _hint("SERVER_AST_MATCH", "0.0", meta={"tag": "div", "label": "NoSuchDiv"}),
                _hint("STRONG_ATTRIBUTE", "id=btn-save", meta={"attribute": "id"}),
            ]
            result = resolve_locator(_req(hints=hints), rt)
            assert result.ok
            assert result.source == "STRONG_ATTRIBUTE"
            assert len(result.trace) >= 2  # tried AST first, then fell back


# ---------------------------------------------------------------------------
# 8. Multiple same-text elements
# ---------------------------------------------------------------------------

class TestConflict:
    def test_multiple_submit_buttons_ambiguous(self):
        """Three identical Submit buttons — TAG_TEXT_LABEL can't uniquely resolve."""
        with create_execution_runtime() as rt:
            rt.navigate(CONFLICT_PAGE)
            hint = _hint("TAG_TEXT_LABEL", "button::Submit", meta={"tag": "button"})
            result = resolve_locator(_req(hints=[hint]), rt)
            # Ambiguous — role match returns >1, :has-text returns >1
            assert not result.ok
            assert any("ambiguous" in t or "matches" in t for t in result.trace)


# ---------------------------------------------------------------------------
# 9. Resolution failure — structured result
# ---------------------------------------------------------------------------

class TestFailure:
    def test_all_strategies_fail(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hints = [
                _hint("SERVER_AST_MATCH", "0.0", meta={"tag": "span", "label": "Ghost"}),
                _hint("TAG_TEXT_LABEL", "span::Ghost"),
            ]
            result = resolve_locator(_req(hints=hints), rt)
            assert not result.ok
            assert result.source == ""
            assert result.confidence == "low"
            assert any("exhausted" in t for t in result.trace)

    def test_no_page(self):
        rt = create_execution_runtime()
        # Don't start — no page
        result = resolve_locator(_req(), rt)
        assert not result.ok
        assert any("No usable page" in t for t in result.trace)


# ---------------------------------------------------------------------------
# 10. No locator hints
# ---------------------------------------------------------------------------

class TestNoHints:
    def test_empty_hints(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            result = resolve_locator(_req(hints=[]), rt)
            assert not result.ok
            assert any("No locator hints" in t for t in result.trace)


# ---------------------------------------------------------------------------
# 11. Serialization
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_resolved_locator_round_trip(self):
        with create_execution_runtime() as rt:
            rt.navigate(SIMPLE_PAGE)
            hint = _hint("STRONG_ATTRIBUTE", "id=btn-save", meta={"attribute": "id"})
            result = resolve_locator(_req(hints=[hint]), rt)
            data = result.model_dump()
            restored = ResolvedLocator.model_validate(data)
            assert restored.ok == result.ok
            assert restored.source == result.source
            assert restored.descriptor is not None
            assert restored.descriptor.selector == result.descriptor.selector

    def test_failure_serializable(self):
        result = ResolvedLocator(ok=False, trace=["nothing worked"])
        data = result.model_dump()
        assert data["ok"] is False
        assert data["trace"] == ["nothing worked"]

    def test_selector_descriptor_round_trip(self):
        desc = SelectorDescriptor(
            selector_type="role",
            role="button",
            name="Save",
            exact=True,
            nth=2,
        )
        data = desc.model_dump()
        restored = SelectorDescriptor.model_validate(data)
        assert restored.selector_type == "role"
        assert restored.role == "button"
        assert restored.name == "Save"
        assert restored.nth == 2


# ---------------------------------------------------------------------------
# 12. Mocked tests — strategy branches without real Playwright
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock, patch
from app.services.locator_resolver import (
    _try_server_ast_match,
    _try_strong_attribute,
    _try_tag_text_label,
    _try_region_scoped,
    _try_fallback_selector,
    _try_client_ast_match,
    _scope_to_region,
    _parse_target_description,
    _css_escape,
    _css_escape_attr,
    _tag_to_role,
    _count_matches,
    _get_element_info,
    to_playwright_locator,
)


class TestHelperFunctions:
    """Unit tests for internal helper functions."""

    def test_tag_to_role_known(self):
        assert _tag_to_role("button") == "button"
        assert _tag_to_role("a") == "link"
        assert _tag_to_role("input") == "textbox"
        assert _tag_to_role("textarea") == "textbox"
        assert _tag_to_role("select") == "combobox"
        assert _tag_to_role("img") == "img"
        assert _tag_to_role("nav") == "navigation"
        assert _tag_to_role("dialog") == "dialog"
        assert _tag_to_role("table") == "table"
        assert _tag_to_role("th") == "columnheader"

    def test_tag_to_role_unknown(self):
        assert _tag_to_role("div") == ""
        assert _tag_to_role("span") == ""
        assert _tag_to_role("custom-element") == ""

    def test_tag_to_role_case_insensitive(self):
        assert _tag_to_role("BUTTON") == "button"
        assert _tag_to_role("Input") == "textbox"

    def test_css_escape(self):
        assert _css_escape("simple") == "simple"
        assert _css_escape("my-id") == "my-id"
        assert _css_escape("has.dot") == "has\\.dot"
        assert _css_escape("has space") == "has\\ space"

    def test_css_escape_attr(self):
        assert _css_escape_attr('normal') == 'normal'
        assert _css_escape_attr('has"quote') == 'has\\"quote'
        assert _css_escape_attr('back\\slash') == 'back\\\\slash'

    def test_parse_target_description_tag_text(self):
        tag, text = _parse_target_description('<button> "Save"')
        assert tag == "button"
        assert text == "Save"

    def test_parse_target_description_tag_other(self):
        tag, text = _parse_target_description('<div> some content here')
        assert tag == "div"
        assert text == "some content here"

    def test_parse_target_description_just_text(self):
        tag, text = _parse_target_description("plain text description")
        assert tag == ""
        assert text == "plain text description"

    def test_parse_target_description_empty(self):
        tag, text = _parse_target_description("")
        assert tag == ""
        assert text == ""


class TestCountMatchesMocked:
    """_count_matches returns 0 on exception."""

    def test_exception_returns_zero(self):
        page = MagicMock()
        page.locator.side_effect = Exception("boom")
        desc = SelectorDescriptor(selector_type="css", selector="div")
        assert _count_matches(page, desc) == 0


class TestGetElementInfoMocked:
    """_get_element_info returns ("", "") on exceptions or 0 matches."""

    def test_zero_matches(self):
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 0
        page.locator.return_value = loc
        tag, text = _get_element_info(page, SelectorDescriptor(selector_type="css", selector="x"))
        assert tag == ""
        assert text == ""

    def test_exception(self):
        page = MagicMock()
        page.locator.side_effect = Exception("boom")
        tag, text = _get_element_info(page, SelectorDescriptor(selector_type="css", selector="x"))
        assert tag == ""
        assert text == ""


class TestToPlaywrightLocatorTypes:
    """to_playwright_locator handles all selector_type branches."""

    def _mock_page(self):
        page = MagicMock()
        page.locator.return_value = MagicMock()
        page.get_by_role.return_value = MagicMock()
        page.get_by_text.return_value = MagicMock()
        page.get_by_label.return_value = MagicMock()
        page.get_by_placeholder.return_value = MagicMock()
        page.get_by_test_id.return_value = MagicMock()
        return page

    def test_css(self):
        page = self._mock_page()
        desc = SelectorDescriptor(selector_type="css", selector="#btn")
        to_playwright_locator(page, desc)
        page.locator.assert_called_with("#btn")

    def test_xpath(self):
        page = self._mock_page()
        desc = SelectorDescriptor(selector_type="xpath", selector="//button")
        to_playwright_locator(page, desc)
        page.locator.assert_called_with("xpath=//button")

    def test_role_with_name(self):
        page = self._mock_page()
        desc = SelectorDescriptor(selector_type="role", role="button", name="Save", exact=True)
        to_playwright_locator(page, desc)
        page.get_by_role.assert_called_with("button", name="Save", exact=True)

    def test_role_without_name(self):
        page = self._mock_page()
        desc = SelectorDescriptor(selector_type="role", role="button")
        to_playwright_locator(page, desc)
        page.get_by_role.assert_called_with("button")

    def test_text(self):
        page = self._mock_page()
        desc = SelectorDescriptor(selector_type="text", name="Click me", exact=False)
        to_playwright_locator(page, desc)
        page.get_by_text.assert_called_with("Click me", exact=False)

    def test_label(self):
        page = self._mock_page()
        desc = SelectorDescriptor(selector_type="label", name="Username", exact=True)
        to_playwright_locator(page, desc)
        page.get_by_label.assert_called_with("Username", exact=True)

    def test_placeholder(self):
        page = self._mock_page()
        desc = SelectorDescriptor(selector_type="placeholder", name="Enter email", exact=False)
        to_playwright_locator(page, desc)
        page.get_by_placeholder.assert_called_with("Enter email", exact=False)

    def test_test_id(self):
        page = self._mock_page()
        desc = SelectorDescriptor(selector_type="test_id", name="submit-btn")
        to_playwright_locator(page, desc)
        page.get_by_test_id.assert_called_with("submit-btn")

    def test_nth_applied(self):
        page = self._mock_page()
        inner_loc = MagicMock()
        page.locator.return_value = inner_loc
        desc = SelectorDescriptor(selector_type="css", selector="div", nth=3)
        to_playwright_locator(page, desc)
        inner_loc.nth.assert_called_with(3)

    def test_unknown_type_falls_back_to_locator(self):
        """Unknown selector_type falls through to page.locator(desc.selector)."""
        page = self._mock_page()
        # Use a Pydantic-invalid type via direct attribute setting
        desc = SelectorDescriptor(selector_type="css", selector=".foo")
        desc.selector_type = "unknown_type"
        to_playwright_locator(page, desc)
        page.locator.assert_called_with(".foo")


class TestServerAstMatchMocked:
    """Mocked tests for _try_server_ast_match edge cases."""

    def _mock_page_count(self, counts):
        """Return a page mock that returns successive count values."""
        page = MagicMock()
        loc = MagicMock()
        loc.count.side_effect = counts
        page.locator.return_value = loc
        page.get_by_role.return_value = loc
        return page

    def test_no_tag_in_meta(self):
        hint = LocatorHint(strategy="SERVER_AST_MATCH", value="0.0", meta={})
        trace = []
        result = _try_server_ast_match(hint, MagicMock(), trace)
        assert result is None
        assert any("no tag" in t for t in trace)

    def test_role_based_ambiguous_then_css_unique(self):
        """Role matches multiple but CSS :has-text matches 1."""
        page = MagicMock()
        role_loc = MagicMock()
        role_loc.count.return_value = 2
        page.get_by_role.return_value = role_loc

        css_loc = MagicMock()
        css_loc.count.return_value = 1
        page.locator.return_value = css_loc

        hint = LocatorHint(
            strategy="SERVER_AST_MATCH", value="0.0",
            meta={"tag": "button", "label": "Save", "match_type": "exact"},
        )
        trace = []
        result = _try_server_ast_match(hint, page, trace)
        assert result is not None
        assert result.selector_type == "css"

    def test_css_multiple_no_region(self):
        """CSS :has-text matches >1 but no region_hint, returns None."""
        page = MagicMock()
        role_loc = MagicMock()
        role_loc.count.return_value = 0
        page.get_by_role.return_value = role_loc

        css_loc = MagicMock()
        css_loc.count.return_value = 3
        page.locator.return_value = css_loc

        hint = LocatorHint(
            strategy="SERVER_AST_MATCH", value="0.0",
            meta={"tag": "button", "label": "Test", "match_type": "exact"},
        )
        trace = []
        result = _try_server_ast_match(hint, page, trace)
        assert result is None
        assert any("no unique" in t for t in trace)

    def test_css_zero_matches(self):
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 0
        page.get_by_role.return_value = loc
        page.locator.return_value = loc

        hint = LocatorHint(
            strategy="SERVER_AST_MATCH", value="0.0",
            meta={"tag": "button", "label": "Ghost"},
        )
        trace = []
        result = _try_server_ast_match(hint, page, trace)
        assert result is None
        assert any("0 matches" in t for t in trace)

    def test_no_label_exact_match(self):
        hint = LocatorHint(
            strategy="SERVER_AST_MATCH", value="0.0",
            meta={"tag": "button", "match_type": "exact"},
        )
        trace = []
        result = _try_server_ast_match(hint, MagicMock(), trace)
        assert result is None
        assert any("no label" in t for t in trace)

    def test_css_ambiguous_with_region_hint(self):
        """CSS :has-text matches >1 and region_hint exists — tries scoping."""
        page = MagicMock()
        role_loc = MagicMock()
        role_loc.count.return_value = 0
        page.get_by_role.return_value = role_loc

        css_loc = MagicMock()
        css_loc.count.return_value = 2
        page.locator.return_value = css_loc

        # region scoping: all region selectors also return 0
        region_loc = MagicMock()
        region_loc.count.return_value = 0

        hint = LocatorHint(
            strategy="SERVER_AST_MATCH", value="0.0",
            meta={"tag": "button", "label": "Save", "region_hint": "User Info"},
        )
        trace = []
        result = _try_server_ast_match(hint, page, trace)
        # Region scoping fails (all return 0), so overall None
        assert result is None

    def test_tag_without_role(self):
        """A tag that has no ARIA role mapping uses CSS directly."""
        page = MagicMock()
        css_loc = MagicMock()
        css_loc.count.return_value = 1
        page.locator.return_value = css_loc

        hint = LocatorHint(
            strategy="SERVER_AST_MATCH", value="0.0",
            meta={"tag": "div", "label": "Section Title"},
        )
        trace = []
        result = _try_server_ast_match(hint, page, trace)
        assert result is not None
        assert result.selector_type == "css"


class TestStrongAttributeMocked:
    """Mocked tests for _try_strong_attribute edge cases."""

    def test_unparseable_value(self):
        hint = LocatorHint(strategy="STRONG_ATTRIBUTE", value="noequals", meta={})
        trace = []
        result = _try_strong_attribute(hint, MagicMock(), trace)
        assert result is None
        assert any("cannot parse" in t for t in trace)

    def test_id_zero_matches(self):
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 0
        page.locator.return_value = loc
        hint = LocatorHint(strategy="STRONG_ATTRIBUTE", value="id=ghost", meta={"attribute": "id"})
        trace = []
        result = _try_strong_attribute(hint, page, trace)
        assert result is None
        assert any("0 matches" in t for t in trace)

    def test_placeholder_zero_matches(self):
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 0
        page.get_by_placeholder.return_value = loc
        hint = LocatorHint(strategy="STRONG_ATTRIBUTE", value="placeholder=ghost", meta={})
        trace = []
        result = _try_strong_attribute(hint, page, trace)
        assert result is None
        assert any("0 matches" in t for t in trace)

    def test_role_match(self):
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 1
        page.get_by_role.return_value = loc
        hint = LocatorHint(strategy="STRONG_ATTRIBUTE", value="role=button", meta={})
        trace = []
        result = _try_strong_attribute(hint, page, trace)
        assert result is not None
        assert result.selector_type == "role"
        assert result.role == "button"

    def test_role_zero_matches(self):
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 0
        page.get_by_role.return_value = loc
        hint = LocatorHint(strategy="STRONG_ATTRIBUTE", value="role=gridcell", meta={})
        trace = []
        result = _try_strong_attribute(hint, page, trace)
        assert result is None

    def test_generic_attribute_match(self):
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 1
        page.locator.return_value = loc
        hint = LocatorHint(strategy="STRONG_ATTRIBUTE", value="data-test=submit", meta={"tag": "button"})
        trace = []
        result = _try_strong_attribute(hint, page, trace)
        assert result is not None
        assert result.selector_type == "css"

    def test_generic_attribute_zero_matches(self):
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 0
        page.locator.return_value = loc
        hint = LocatorHint(strategy="STRONG_ATTRIBUTE", value="data-x=nope", meta={"tag": ""})
        trace = []
        result = _try_strong_attribute(hint, page, trace)
        assert result is None
        assert any("0 matches" in t for t in trace)


class TestTagTextLabelMocked:
    """Mocked tests for _try_tag_text_label edge cases."""

    def test_no_separator(self):
        hint = LocatorHint(strategy="TAG_TEXT_LABEL", value="nodelimiter", meta={})
        trace = []
        result = _try_tag_text_label(hint, MagicMock(), trace)
        assert result is None
        assert any("cannot parse" in t for t in trace)

    def test_empty_text(self):
        hint = LocatorHint(strategy="TAG_TEXT_LABEL", value="button::  ", meta={})
        trace = []
        result = _try_tag_text_label(hint, MagicMock(), trace)
        assert result is None
        assert any("empty text" in t for t in trace)

    def test_role_ambiguous_exact_resolves(self):
        """Role returns >1 but exact match returns 1."""
        page = MagicMock()
        inexact_loc = MagicMock()
        inexact_loc.count.return_value = 3
        exact_loc = MagicMock()
        exact_loc.count.return_value = 1

        page.get_by_role.side_effect = [inexact_loc, exact_loc]

        hint = LocatorHint(strategy="TAG_TEXT_LABEL", value="button::Save", meta={})
        trace = []
        result = _try_tag_text_label(hint, page, trace)
        assert result is not None
        assert result.exact is True

    def test_role_ambiguous_exact_also_ambiguous(self):
        """Both inexact and exact role match return >1."""
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 2
        page.get_by_role.return_value = loc

        css_loc = MagicMock()
        css_loc.count.return_value = 2
        page.locator.return_value = css_loc

        hint = LocatorHint(strategy="TAG_TEXT_LABEL", value="button::Submit", meta={})
        trace = []
        result = _try_tag_text_label(hint, page, trace)
        assert result is None
        assert any("ambiguous" in t for t in trace)

    def test_no_role_tag_css_match(self):
        """Tag with no ARIA role uses CSS directly."""
        page = MagicMock()
        css_loc = MagicMock()
        css_loc.count.return_value = 1
        page.locator.return_value = css_loc

        hint = LocatorHint(strategy="TAG_TEXT_LABEL", value="span::Info", meta={})
        trace = []
        result = _try_tag_text_label(hint, page, trace)
        assert result is not None
        assert result.selector_type == "css"


class TestRegionScopedMocked:
    """Mocked tests for _try_region_scoped."""

    def test_empty_region_name(self):
        hint = LocatorHint(strategy="REGION_SCOPED", value="", meta={})
        trace = []
        req = _req(hints=[hint])
        result = _try_region_scoped(hint, MagicMock(), trace, req)
        assert result is None
        assert any("empty region" in t for t in trace)

    def test_no_parseable_target(self):
        hint = LocatorHint(strategy="REGION_SCOPED", value="Settings", meta={})
        trace = []
        req = _req(hints=[hint], target_desc="")
        result = _try_region_scoped(hint, MagicMock(), trace, req)
        assert result is None
        assert any("no parseable target" in t for t in trace)

    def test_tag_and_text_target(self):
        """Region scoped with tag+text target builds css :has-text inner."""
        page = MagicMock()
        region_loc = MagicMock()
        region_loc.count.return_value = 1
        inner_loc = MagicMock()
        inner_loc.count.return_value = 1
        region_loc.first.locator.return_value = inner_loc
        page.locator.return_value = region_loc

        hint = LocatorHint(strategy="REGION_SCOPED", value="Form Area", meta={})
        trace = []
        req = _req(hints=[hint], target_desc='<button> "Submit"')
        result = _try_region_scoped(hint, page, trace, req)
        assert result is not None

    def test_text_only_target(self):
        """Region scoped with text-only target builds a text descriptor."""
        page = MagicMock()
        region_loc = MagicMock()
        region_loc.count.return_value = 1
        inner_loc = MagicMock()
        inner_loc.count.return_value = 1
        region_loc.first.locator.return_value = inner_loc
        page.locator.return_value = region_loc

        hint = LocatorHint(strategy="REGION_SCOPED", value="Sidebar", meta={})
        trace = []
        req = _req(hints=[hint], target_desc="some text content")
        result = _try_region_scoped(hint, page, trace, req)
        assert result is not None

    def test_tag_only_target(self):
        """Region scoped with tag-only target (no text)."""
        page = MagicMock()
        region_loc = MagicMock()
        region_loc.count.return_value = 1
        inner_loc = MagicMock()
        inner_loc.count.return_value = 1
        region_loc.first.locator.return_value = inner_loc
        page.locator.return_value = region_loc

        hint = LocatorHint(strategy="REGION_SCOPED", value="Panel", meta={})
        trace = []
        req = _req(hints=[hint], target_desc='<div> ""')
        result = _try_region_scoped(hint, page, trace, req)
        # tag="div", text="" -> tag only -> inner = SelectorDescriptor(css, "div")
        assert result is not None


class TestFallbackSelectorMocked:
    """Mocked tests for _try_fallback_selector."""

    def test_empty_selector(self):
        hint = LocatorHint(strategy="FALLBACK_SELECTOR", value="", meta={})
        trace = []
        result = _try_fallback_selector(hint, MagicMock(), trace)
        assert result is None
        assert any("empty selector" in t for t in trace)

    def test_selector_matches(self):
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 1
        page.locator.return_value = loc
        hint = LocatorHint(strategy="FALLBACK_SELECTOR", value="#btn", meta={})
        trace = []
        result = _try_fallback_selector(hint, page, trace)
        assert result is not None
        assert result.selector_type == "css"

    def test_selector_zero_matches(self):
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 0
        page.locator.return_value = loc
        hint = LocatorHint(strategy="FALLBACK_SELECTOR", value=".gone", meta={})
        trace = []
        result = _try_fallback_selector(hint, page, trace)
        assert result is None
        assert any("0 matches" in t for t in trace)


class TestClientAstMatchMocked:
    """Mocked tests for _try_client_ast_match."""

    def test_no_node_label(self):
        hint = LocatorHint(strategy="CLIENT_AST_MATCH", value="n1", meta={})
        trace = []
        result = _try_client_ast_match(hint, MagicMock(), trace)
        assert result is None
        assert any("no usable info" in t for t in trace)

    def test_unique_text_match(self):
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 1
        page.get_by_text.return_value = loc
        hint = LocatorHint(
            strategy="CLIENT_AST_MATCH", value="n42",
            meta={"nodeLabel": "Delete"},
        )
        trace = []
        result = _try_client_ast_match(hint, page, trace)
        assert result is not None
        assert result.selector_type == "text"

    def test_ambiguous_text_with_area_label_scope(self):
        """Multiple text matches but area_label helps scope."""
        page = MagicMock()
        text_loc = MagicMock()
        text_loc.count.return_value = 3
        page.get_by_text.return_value = text_loc

        # region scoping returns 1
        region_loc = MagicMock()
        region_loc.count.return_value = 1
        inner_loc = MagicMock()
        inner_loc.count.return_value = 1
        region_loc.first.locator.return_value = inner_loc
        page.locator.return_value = region_loc

        hint = LocatorHint(
            strategy="CLIENT_AST_MATCH", value="n42",
            meta={"nodeLabel": "Edit", "areaLabel": "User Profile"},
        )
        trace = []
        result = _try_client_ast_match(hint, page, trace)
        assert result is not None

    def test_ambiguous_text_no_area_label(self):
        """Multiple text matches and no area label — fails."""
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 5
        page.get_by_text.return_value = loc

        hint = LocatorHint(
            strategy="CLIENT_AST_MATCH", value="n42",
            meta={"nodeLabel": "OK"},
        )
        trace = []
        result = _try_client_ast_match(hint, page, trace)
        assert result is None


class TestScopeToRegionMocked:
    """Mocked tests for _scope_to_region helper."""

    def test_all_region_selectors_fail(self):
        page = MagicMock()
        loc = MagicMock()
        loc.count.return_value = 0
        page.locator.return_value = loc

        trace = []
        inner = SelectorDescriptor(selector_type="css", selector="button")
        result = _scope_to_region(page, "Header", inner, trace, "TEST")
        assert result is None
        assert any("not found" in t for t in trace)

    def test_region_found_but_inner_ambiguous(self):
        page = MagicMock()
        region_loc = MagicMock()
        region_loc.count.return_value = 1
        inner_loc = MagicMock()
        inner_loc.count.return_value = 3
        region_loc.first.locator.return_value = inner_loc
        page.locator.return_value = region_loc

        trace = []
        inner = SelectorDescriptor(selector_type="css", selector="button")
        result = _scope_to_region(page, "Form", inner, trace, "TEST")
        assert result is None
        assert any("still ambiguous" in t for t in trace)

    def test_region_locator_raises_exception(self):
        """Exception during region matching is caught."""
        page = MagicMock()
        page.locator.side_effect = Exception("boom")

        trace = []
        inner = SelectorDescriptor(selector_type="css", selector="button")
        result = _scope_to_region(page, "Nav", inner, trace, "TEST")
        assert result is None

    def test_region_with_text_inner_descriptor(self):
        """Inner descriptor is text type — uses text= expression."""
        page = MagicMock()
        region_loc = MagicMock()
        region_loc.count.return_value = 1
        inner_loc = MagicMock()
        inner_loc.count.return_value = 1
        region_loc.first.locator.return_value = inner_loc
        page.locator.return_value = region_loc

        trace = []
        inner = SelectorDescriptor(selector_type="text", name="Click me")
        result = _scope_to_region(page, "Main", inner, trace, "TEST")
        assert result is not None
        assert "text=Click me" in result.selector


class TestResolveLocatorUnknownStrategy:
    """Unknown strategy name in hints is logged and skipped."""

    def test_unknown_strategy_skipped(self):
        rt = MagicMock()
        rt.page = MagicMock()
        rt.page.is_closed.return_value = False

        req = _req(hints=[
            LocatorHint(strategy="TOTALLY_UNKNOWN", value="foo", confidence="low", meta={}),
        ])
        result = resolve_locator(req, rt)
        assert not result.ok
        assert any("Unknown strategy" in t for t in result.trace)
