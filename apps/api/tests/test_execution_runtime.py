"""
Tests for the Playwright execution runtime (Phase 7B).

Covers:
1. Runtime initialisation and teardown
2. Browser / context / page lifecycle
3. Navigation to data URLs and about:blank
4. Page observation: URL, title, HTML, snapshot
5. Screenshot capability
6. Page health checks (is_page_usable)
7. Error handling: closed page, bad navigation, uninitialised runtime
8. Context manager protocol
9. Double start / double stop idempotency
10. RuntimeConfig defaults

All tests use data: URLs or about:blank — no real websites.
No LLM calls, no locator resolver, no action executor.
"""

import os

import pytest

from app.services.execution_runtime import (
    ExecutionRuntime,
    ExecutionRuntimeError,
    PageNavigationError,
    PageObservationError,
    RuntimeConfig,
    RuntimeInitError,
    create_execution_runtime,
)


# ---------------------------------------------------------------------------
# Shared HTML fixture
# ---------------------------------------------------------------------------

DATA_URL = 'data:text/html,<html><head><title>Test Page</title></head><body><h1>Hello</h1></body></html>'


# ---------------------------------------------------------------------------
# 1. Initialisation and teardown
# ---------------------------------------------------------------------------

class TestLifecycle:
    def test_start_and_stop(self):
        rt = create_execution_runtime()
        assert not rt.is_started
        rt.start()
        assert rt.is_started
        assert rt.browser is not None
        assert rt.context is not None
        assert rt.page is not None
        rt.stop()
        assert not rt.is_started

    def test_double_start_is_idempotent(self):
        rt = create_execution_runtime()
        rt.start()
        rt.start()  # should not raise
        assert rt.is_started
        rt.stop()

    def test_double_stop_is_idempotent(self):
        rt = create_execution_runtime()
        rt.start()
        rt.stop()
        rt.stop()  # should not raise
        assert not rt.is_started

    def test_stop_without_start(self):
        rt = create_execution_runtime()
        rt.stop()  # should not raise


# ---------------------------------------------------------------------------
# 2. Context manager
# ---------------------------------------------------------------------------

class TestContextManager:
    def test_context_manager_basic(self):
        with create_execution_runtime() as rt:
            assert rt.is_started
            assert rt.page is not None
        assert not rt.is_started

    def test_context_manager_exception_still_stops(self):
        rt = create_execution_runtime()
        with pytest.raises(ValueError):
            with rt:
                raise ValueError("boom")
        assert not rt.is_started


# ---------------------------------------------------------------------------
# 3. Navigation
# ---------------------------------------------------------------------------

class TestNavigation:
    def test_navigate_data_url(self):
        with create_execution_runtime() as rt:
            rt.navigate(DATA_URL)
            assert "Test Page" in rt.current_title()

    def test_navigate_about_blank(self):
        with create_execution_runtime() as rt:
            rt.navigate("about:blank")
            url = rt.current_url()
            assert url == "about:blank"

    def test_navigate_invalid_url_raises(self):
        with create_execution_runtime() as rt:
            with pytest.raises(PageNavigationError):
                rt.navigate("http://localhost:1/nonexistent", wait_until="commit")


# ---------------------------------------------------------------------------
# 4. Observation: URL, title, HTML
# ---------------------------------------------------------------------------

class TestObservation:
    def test_current_url(self):
        with create_execution_runtime() as rt:
            rt.navigate(DATA_URL)
            url = rt.current_url()
            assert url.startswith("data:")

    def test_current_title(self):
        with create_execution_runtime() as rt:
            rt.navigate(DATA_URL)
            assert rt.current_title() == "Test Page"

    def test_current_html(self):
        with create_execution_runtime() as rt:
            rt.navigate(DATA_URL)
            html = rt.current_html()
            assert "<h1>Hello</h1>" in html

    def test_snapshot(self):
        with create_execution_runtime() as rt:
            rt.navigate(DATA_URL)
            snap = rt.snapshot()
            assert snap.url.startswith("data:")
            assert snap.title == "Test Page"
            assert "<h1>Hello</h1>" in snap.html


# ---------------------------------------------------------------------------
# 5. Screenshot
# ---------------------------------------------------------------------------

class TestScreenshot:
    def test_screenshot_returns_path(self):
        with create_execution_runtime() as rt:
            rt.navigate(DATA_URL)
            path = rt.screenshot()
            assert path.endswith(".png")
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
            # Cleanup
            os.unlink(path)

    def test_screenshot_full_page(self):
        with create_execution_runtime() as rt:
            rt.navigate(DATA_URL)
            path = rt.screenshot(full_page=True)
            assert os.path.exists(path)
            os.unlink(path)

    def test_screenshot_custom_dir(self, tmp_path):
        cfg = RuntimeConfig(screenshot_dir=str(tmp_path))
        with create_execution_runtime(cfg) as rt:
            rt.navigate(DATA_URL)
            path = rt.screenshot()
            assert path.startswith(str(tmp_path))
            assert os.path.exists(path)


# ---------------------------------------------------------------------------
# 6. Page health
# ---------------------------------------------------------------------------

class TestPageHealth:
    def test_is_page_usable_after_start(self):
        with create_execution_runtime() as rt:
            assert rt.is_page_usable()

    def test_is_page_usable_after_close(self):
        rt = create_execution_runtime()
        rt.start()
        rt.page.close()
        assert not rt.is_page_usable()
        rt.stop()

    def test_is_page_usable_before_start(self):
        rt = create_execution_runtime()
        assert not rt.is_page_usable()


# ---------------------------------------------------------------------------
# 7. Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_observation_on_closed_page(self):
        rt = create_execution_runtime()
        rt.start()
        rt.page.close()
        with pytest.raises(PageObservationError):
            rt.current_url()
        with pytest.raises(PageObservationError):
            rt.current_title()
        with pytest.raises(PageObservationError):
            rt.current_html()
        with pytest.raises(PageObservationError):
            rt.snapshot()
        with pytest.raises(PageObservationError):
            rt.screenshot()
        rt.stop()

    def test_observation_before_start(self):
        rt = create_execution_runtime()
        with pytest.raises(PageObservationError):
            rt.current_url()

    def test_navigate_before_start(self):
        rt = create_execution_runtime()
        with pytest.raises(PageNavigationError):
            rt.navigate("about:blank")

    def test_invalid_browser_type(self):
        cfg = RuntimeConfig(browser_type="netscape")
        rt = create_execution_runtime(cfg)
        with pytest.raises(RuntimeInitError, match="Unknown browser type"):
            rt.start()


# ---------------------------------------------------------------------------
# 8. RuntimeConfig defaults
# ---------------------------------------------------------------------------

class TestRuntimeConfig:
    def test_defaults(self):
        cfg = RuntimeConfig()
        assert cfg.headless is True
        assert cfg.browser_type == "chromium"
        assert cfg.viewport_width == 1280
        assert cfg.viewport_height == 720
        assert cfg.user_agent is None
        assert cfg.storage_state is None
        assert cfg.default_timeout_ms == 30_000
        assert cfg.screenshot_dir is None

    def test_custom_viewport(self):
        cfg = RuntimeConfig(viewport_width=800, viewport_height=600)
        rt = create_execution_runtime(cfg)
        rt.start()
        try:
            rt.navigate(DATA_URL)
            assert rt.is_page_usable()
        finally:
            rt.stop()
