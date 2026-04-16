"""
Tests for the post-action observer (Phase 7E).

Covers:
1.  click changes title → title_changed=True, screenshot captured
2.  fill changes HTML → html_changed=True
3.  navigate changes URL → url_changed=True
4.  click removes target → still_present=False
5.  hover shows hidden element → target still present/visible
6.  no change scenario → all *_changed=False
7.  snapshot failure → structured warning, not crash
8.  observation serializable
9.  execute_and_observe full pipeline
10. elapsed_since_action_ms populated

All tests use data: URLs — no real websites, no LLM calls.
"""

import hashlib
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.schemas.execution import (
    ActionTarget,
    ExecutionRequest,
    ExecutionResult,
    LocatorHint,
    PageSnapshot,
    PageStateChange,
)
from app.schemas.locator import ResolvedLocator, SelectorDescriptor
from app.schemas.observation import PostActionObservation
from app.services.execution_runtime import create_execution_runtime
from app.services.post_action_observer import execute_and_observe, observe_post_action


# ---------------------------------------------------------------------------
# Test pages
# ---------------------------------------------------------------------------

TITLE_CHANGE_PAGE = """data:text/html,
<html><head><title>Before</title></head><body>
  <button id="btn" onclick="document.title='After'">Click me</button>
</body></html>"""

FILL_PAGE = """data:text/html,
<html><head><title>Fill Test</title></head><body>
  <input id="inp" value="" />
</body></html>"""

DOM_CHANGE_PAGE = """data:text/html,
<html><head><title>DOM Change</title></head><body>
  <button id="add-btn" onclick="document.body.appendChild(document.createElement('p')).textContent='Added'">Add</button>
</body></html>"""

REMOVE_PAGE = """data:text/html,
<html><head><title>Remove Test</title></head><body>
  <button id="vanish" onclick="this.remove()">I will vanish</button>
</body></html>"""

HOVER_PAGE = """data:text/html,
<html><head><title>Hover Test</title></head><body>
  <div id="trigger" onmouseenter="document.getElementById('msg').style.display='block'">Hover</div>
  <div id="msg" style="display:none">Visible!</div>
</body></html>"""

STATIC_PAGE = """data:text/html,
<html><head><title>Static</title></head><body>
  <button id="noop">Nothing happens</button>
</body></html>"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _req(*, action_type="click", target_desc="<button>", value=None, hints=None):
    if hints is None:
        hints = [LocatorHint(strategy="STRONG_ATTRIBUTE", value="id=btn",
                             confidence="high", meta={"attribute": "id"})]
    return ExecutionRequest(
        page=PageSnapshot(url="about:blank"),
        action=ActionTarget(action_type=action_type, target_description=target_desc, value=value),
        locator_hints=hints,
        recording_id="test",
    )


def _hint_id(eid: str) -> list[LocatorHint]:
    return [LocatorHint(strategy="STRONG_ATTRIBUTE", value=f"id={eid}",
                        confidence="high", meta={"attribute": "id"})]


def _exec_result(*, url_before="", url_after="", title_before="", title_after=""):
    return ExecutionResult(
        ok=True, action_type="click", target_summary="test",
        page_change=PageStateChange(
            url_before=url_before, url_after=url_after,
            title_before=title_before, title_after=title_after,
        ),
    )


def _resolved(selector: str) -> ResolvedLocator:
    return ResolvedLocator(
        ok=True, source="STRONG_ATTRIBUTE", confidence="high",
        descriptor=SelectorDescriptor(selector_type="css", selector=selector),
        matched_count=1,
    )


# ---------------------------------------------------------------------------
# 1. click changes title
# ---------------------------------------------------------------------------

class TestTitleChange:
    def test_title_changed_after_click(self):
        with create_execution_runtime() as rt:
            rt.navigate(TITLE_CHANGE_PAGE)
            before_html = rt.current_html()
            rt.page.locator("#btn").click()

            obs = observe_post_action(
                runtime=rt,
                execution_result=_exec_result(title_before="Before", title_after="After"),
                resolved_locator=_resolved("#btn"),
                before_title="Before",
                before_html_hash=_md5(before_html),
            )
            assert obs.title_changed
            assert obs.title == "After"
            assert obs.screenshot_ref is not None
            assert os.path.exists(obs.screenshot_ref)
            os.unlink(obs.screenshot_ref)


# ---------------------------------------------------------------------------
# 2. fill changes HTML
# ---------------------------------------------------------------------------

class TestHtmlChange:
    def test_html_changed_after_dom_mutation(self):
        """Click that appends a DOM element → HTML content changes."""
        with create_execution_runtime() as rt:
            rt.navigate(DOM_CHANGE_PAGE)
            before_html = rt.current_html()
            before_hash = _md5(before_html)
            rt.page.locator("#add-btn").click()

            obs = observe_post_action(
                runtime=rt,
                execution_result=_exec_result(),
                resolved_locator=_resolved("#add-btn"),
                before_html_hash=before_hash,
            )
            assert obs.html_changed
            assert obs.html_length > 0
            assert obs.html_hash != before_hash

    def test_fill_does_not_change_html_source(self):
        """fill() changes input value property, not HTML source — html_changed=False is correct."""
        with create_execution_runtime() as rt:
            rt.navigate(FILL_PAGE)
            before_hash = _md5(rt.current_html())
            rt.page.locator("#inp").fill("hello")

            obs = observe_post_action(
                runtime=rt,
                execution_result=_exec_result(),
                before_html_hash=before_hash,
            )
            # Input value is a DOM property, not reflected in page.content()
            assert not obs.html_changed


# ---------------------------------------------------------------------------
# 3. navigate changes URL
# ---------------------------------------------------------------------------

class TestUrlChange:
    def test_url_changed_after_navigate(self):
        target = 'data:text/html,<html><head><title>New</title></head><body>OK</body></html>'
        with create_execution_runtime() as rt:
            rt.navigate(STATIC_PAGE)
            before_url = rt.current_url()
            before_hash = _md5(rt.current_html())
            rt.navigate(target)

            obs = observe_post_action(
                runtime=rt,
                execution_result=_exec_result(url_before=before_url),
                before_url=before_url,
                before_html_hash=before_hash,
            )
            assert obs.url_changed
            assert obs.title == "New"


# ---------------------------------------------------------------------------
# 4. click removes target
# ---------------------------------------------------------------------------

class TestTargetRemoved:
    def test_target_gone_after_click(self):
        with create_execution_runtime() as rt:
            rt.navigate(REMOVE_PAGE)
            rt.page.locator("#vanish").click()

            obs = observe_post_action(
                runtime=rt,
                execution_result=_exec_result(),
                resolved_locator=_resolved("#vanish"),
            )
            assert obs.target.still_present is False
            assert obs.target.still_visible is False


# ---------------------------------------------------------------------------
# 5. hover shows hidden element — target still present/visible
# ---------------------------------------------------------------------------

class TestHoverTarget:
    def test_hover_target_still_present(self):
        with create_execution_runtime() as rt:
            rt.navigate(HOVER_PAGE)
            rt.page.locator("#trigger").hover()

            obs = observe_post_action(
                runtime=rt,
                execution_result=_exec_result(),
                resolved_locator=_resolved("#trigger"),
            )
            assert obs.target.still_present is True
            assert obs.target.still_visible is True


# ---------------------------------------------------------------------------
# 6. no change scenario
# ---------------------------------------------------------------------------

class TestNoChange:
    def test_no_change(self):
        with create_execution_runtime() as rt:
            rt.navigate(STATIC_PAGE)
            before_hash = _md5(rt.current_html())
            # Click the noop button (no JS handler)
            rt.page.locator("#noop").click()

            obs = observe_post_action(
                runtime=rt,
                execution_result=_exec_result(
                    title_before="Static", url_before=rt.current_url(),
                ),
                resolved_locator=_resolved("#noop"),
                before_title="Static",
                before_url=rt.current_url(),
                before_html_hash=before_hash,
            )
            assert not obs.url_changed
            assert not obs.title_changed
            assert not obs.html_changed
            assert obs.target.still_present is True


# ---------------------------------------------------------------------------
# 7. snapshot failure → warning, not crash
# ---------------------------------------------------------------------------

class TestSnapshotFailure:
    def test_closed_page_produces_warnings(self):
        rt = create_execution_runtime()
        rt.start()
        rt.page.close()

        obs = observe_post_action(
            runtime=rt,
            execution_result=_exec_result(),
        )
        # Should not crash, but produce warnings
        assert len(obs.warnings) > 0
        assert obs.url == ""
        assert obs.screenshot_ref is None
        rt.stop()

    def test_target_state_check_failure_adds_warning(self):
        with create_execution_runtime() as rt:
            rt.navigate(STATIC_PAGE)
            with patch(
                "app.services.execution.post_action_observer.to_playwright_locator",
                side_effect=Exception("locator boom"),
            ):
                obs = observe_post_action(
                    runtime=rt,
                    execution_result=_exec_result(),
                    resolved_locator=_resolved("#noop"),
                )
            assert any("Target state check failed" in w for w in obs.warnings)
            assert "target: check failed" in obs.trace
            if obs.screenshot_ref and os.path.exists(obs.screenshot_ref):
                os.unlink(obs.screenshot_ref)


# ---------------------------------------------------------------------------
# 8. observation serializable
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_round_trip(self):
        with create_execution_runtime() as rt:
            rt.navigate(TITLE_CHANGE_PAGE)
            rt.page.locator("#btn").click()

            obs = observe_post_action(
                runtime=rt,
                execution_result=_exec_result(title_before="Before"),
                before_title="Before",
            )
            data = obs.model_dump()
            restored = PostActionObservation.model_validate(data)
            assert restored.title_changed == obs.title_changed
            assert restored.html_hash == obs.html_hash
            # Cleanup screenshot
            if obs.screenshot_ref and os.path.exists(obs.screenshot_ref):
                os.unlink(obs.screenshot_ref)


# ---------------------------------------------------------------------------
# 9. execute_and_observe full pipeline
# ---------------------------------------------------------------------------

class TestExecuteAndObserve:
    def test_full_pipeline_click(self):
        with create_execution_runtime() as rt:
            rt.navigate(TITLE_CHANGE_PAGE)
            req = _req(action_type="click", hints=_hint_id("btn"))
            result = execute_and_observe(req, rt)

            assert result.ok
            assert result.observation is not None
            assert result.observation["title_changed"] is True
            assert result.observation["title"] == "After"
            assert result.screenshot_ref is not None
            # Cleanup
            if result.screenshot_ref and os.path.exists(result.screenshot_ref):
                os.unlink(result.screenshot_ref)

    def test_full_pipeline_dom_change(self):
        """Click that adds DOM element → html_changed=True in observation."""
        with create_execution_runtime() as rt:
            rt.navigate(DOM_CHANGE_PAGE)
            req = _req(action_type="click", hints=_hint_id("add-btn"))
            result = execute_and_observe(req, rt)

            assert result.ok
            assert result.observation is not None
            assert result.observation["html_changed"] is True
            if result.screenshot_ref and os.path.exists(result.screenshot_ref):
                os.unlink(result.screenshot_ref)

    def test_full_pipeline_navigate(self):
        target = 'data:text/html,<html><head><title>Dest</title></head><body>OK</body></html>'
        with create_execution_runtime() as rt:
            rt.navigate(STATIC_PAGE)
            req = _req(action_type="navigate", value=target, hints=[])
            result = execute_and_observe(req, rt)

            assert result.ok
            assert result.observation is not None
            assert result.observation["url_changed"] is True
            if result.screenshot_ref and os.path.exists(result.screenshot_ref):
                os.unlink(result.screenshot_ref)

    def test_full_pipeline_ignores_before_html_hash_failure(self):
        with create_execution_runtime() as rt:
            rt.navigate(STATIC_PAGE)
            req = _req(action_type="click", hints=_hint_id("noop"))
            with patch.object(rt, "current_html", side_effect=Exception("html boom")):
                result = execute_and_observe(req, rt)

            assert result.ok
            assert result.observation is not None
            assert result.observation["html_hash"] != ""
            if result.screenshot_ref and os.path.exists(result.screenshot_ref):
                os.unlink(result.screenshot_ref)

    def test_full_pipeline_ignores_locator_resolution_failure(self):
        with create_execution_runtime() as rt:
            rt.navigate(STATIC_PAGE)
            req = _req(action_type="click", hints=_hint_id("noop"))
            with patch(
                "app.services.execution.locator_resolver.resolve_locator",
                side_effect=Exception("resolve boom"),
            ):
                result = execute_and_observe(req, rt)

            assert result.ok
            assert result.observation is not None
            assert result.observation["target"]["still_present"] is None
            if result.screenshot_ref and os.path.exists(result.screenshot_ref):
                os.unlink(result.screenshot_ref)


# ---------------------------------------------------------------------------
# 10. timing
# ---------------------------------------------------------------------------

class TestTiming:
    def test_elapsed_populated(self):
        with create_execution_runtime() as rt:
            rt.navigate(STATIC_PAGE)
            obs = observe_post_action(
                runtime=rt,
                execution_result=_exec_result(),
            )
            assert obs.elapsed_since_action_ms is not None
            assert obs.elapsed_since_action_ms >= 0
            assert obs.timestamp_ms > 0
