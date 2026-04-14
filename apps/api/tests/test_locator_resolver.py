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
