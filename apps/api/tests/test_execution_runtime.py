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
from playwright.sync_api import Error as PlaywrightError

from app.services.execution.execution_runtime import (
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


# ---------------------------------------------------------------------------
# 9. Mocked tests — non-Playwright code paths
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock, patch, PropertyMock


class TestRuntimeConfigValidation:
    """Test config fields and edge values without launching a browser."""

    def test_user_agent_set(self):
        cfg = RuntimeConfig(user_agent="TestBot/1.0")
        assert cfg.user_agent == "TestBot/1.0"

    def test_storage_state_as_dict(self):
        state = {"cookies": [{"name": "tok", "value": "abc", "url": "http://ex.com"}]}
        cfg = RuntimeConfig(storage_state=state)
        assert cfg.storage_state == state

    def test_storage_state_as_string(self):
        cfg = RuntimeConfig(storage_state="/tmp/state.json")
        assert cfg.storage_state == "/tmp/state.json"

    def test_default_timeout(self):
        cfg = RuntimeConfig(default_timeout_ms=5000)
        assert cfg.default_timeout_ms == 5000


class TestRuntimePropertiesBeforeStart:
    """Property access on an unstarted runtime returns None / False."""

    def test_browser_is_none(self):
        rt = ExecutionRuntime()
        assert rt.browser is None

    def test_context_is_none(self):
        rt = ExecutionRuntime()
        assert rt.context is None

    def test_page_is_none(self):
        rt = ExecutionRuntime()
        assert rt.page is None

    def test_is_started_false(self):
        rt = ExecutionRuntime()
        assert rt.is_started is False

    def test_config_returns_default(self):
        rt = ExecutionRuntime()
        assert rt.config.headless is True
        assert rt.config.browser_type == "chromium"


class TestEnsurePageRaises:
    """_ensure_page raises PageObservationError when page is None or closed."""

    def test_ensure_page_none(self):
        rt = ExecutionRuntime()
        with pytest.raises(PageObservationError, match="No usable page"):
            rt._ensure_page()

    def test_ensure_page_closed(self):
        rt = ExecutionRuntime()
        mock_page = MagicMock()
        mock_page.is_closed.return_value = True
        rt._page = mock_page
        with pytest.raises(PageObservationError, match="No usable page"):
            rt._ensure_page()


class TestNavigateWithoutPage:
    """navigate raises PageNavigationError when page is None or closed."""

    def test_navigate_page_none(self):
        rt = ExecutionRuntime()
        rt._started = True  # pretend started but page is None
        with pytest.raises(PageNavigationError, match="No usable page"):
            rt.navigate("about:blank")

    def test_navigate_page_closed(self):
        rt = ExecutionRuntime()
        rt._started = True
        mock_page = MagicMock()
        mock_page.is_closed.return_value = True
        rt._page = mock_page
        with pytest.raises(PageNavigationError, match="No usable page"):
            rt.navigate("about:blank")


class TestSnapshotAndScreenshotPageNone:
    """snapshot() and screenshot() raise when page is missing."""

    def test_snapshot_no_page(self):
        rt = ExecutionRuntime()
        with pytest.raises(PageObservationError):
            rt.snapshot()

    def test_screenshot_no_page(self):
        rt = ExecutionRuntime()
        with pytest.raises(PageObservationError):
            rt.screenshot()

    def test_current_html_no_page(self):
        rt = ExecutionRuntime()
        with pytest.raises(PageObservationError):
            rt.current_html()

    def test_current_title_no_page(self):
        rt = ExecutionRuntime()
        with pytest.raises(PageObservationError):
            rt.current_title()


class TestCleanupHelpers:
    """Internal cleanup methods should not raise even if objects are in odd states."""

    def test_close_page_when_none(self):
        rt = ExecutionRuntime()
        rt._page = None
        rt._close_page()  # should not raise
        assert rt._page is None

    def test_close_page_when_already_closed(self):
        rt = ExecutionRuntime()
        mock_page = MagicMock()
        mock_page.is_closed.return_value = True
        rt._page = mock_page
        rt._close_page()
        assert rt._page is None
        mock_page.close.assert_not_called()

    def test_close_page_when_close_raises(self):
        rt = ExecutionRuntime()
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.close.side_effect = Exception("already gone")
        rt._page = mock_page
        rt._close_page()  # should not raise
        assert rt._page is None

    def test_close_context_when_none(self):
        rt = ExecutionRuntime()
        rt._context = None
        rt._close_context()  # should not raise

    def test_close_context_when_close_raises(self):
        rt = ExecutionRuntime()
        mock_ctx = MagicMock()
        mock_ctx.close.side_effect = Exception("gone")
        rt._context = mock_ctx
        rt._close_context()
        assert rt._context is None

    def test_cleanup_browser_when_none(self):
        rt = ExecutionRuntime()
        rt._browser = None
        rt._cleanup_browser()  # should not raise

    def test_cleanup_browser_when_close_raises(self):
        rt = ExecutionRuntime()
        mock_browser = MagicMock()
        mock_browser.close.side_effect = Exception("gone")
        rt._browser = mock_browser
        rt._cleanup_browser()
        assert rt._browser is None

    def test_cleanup_pw_when_none(self):
        rt = ExecutionRuntime()
        rt._pw = None
        rt._cleanup_pw()  # should not raise

    def test_cleanup_pw_when_stop_raises(self):
        rt = ExecutionRuntime()
        mock_pw = MagicMock()
        mock_pw.stop.side_effect = Exception("gone")
        rt._pw = mock_pw
        rt._cleanup_pw()
        assert rt._pw is None


class TestStartErrorBranches:
    """Test error paths during start() that don't require a real browser."""

    def test_start_playwright_fails(self):
        rt = ExecutionRuntime()
        with patch("app.services.execution.execution_runtime.sync_playwright") as mock_sp:
            mock_sp.return_value.start.side_effect = Exception("no pw")
            with pytest.raises(RuntimeInitError, match="Failed to start Playwright"):
                rt.start()

    def test_start_browser_launch_fails(self):
        rt = ExecutionRuntime()
        mock_pw = MagicMock()
        mock_launcher = MagicMock()
        mock_launcher.launch.side_effect = Exception("launch fail")
        mock_pw.chromium = mock_launcher
        with patch("app.services.execution.execution_runtime.sync_playwright") as mock_sp:
            mock_sp.return_value.start.return_value = mock_pw
            with pytest.raises(RuntimeInitError, match="Failed to launch browser"):
                rt.start()

    def test_start_context_creation_fails(self):
        rt = ExecutionRuntime()
        mock_pw = MagicMock()
        mock_browser = MagicMock()
        mock_browser.new_context.side_effect = Exception("ctx fail")
        mock_launcher = MagicMock()
        mock_launcher.launch.return_value = mock_browser
        mock_pw.chromium = mock_launcher
        with patch("app.services.execution.execution_runtime.sync_playwright") as mock_sp:
            mock_sp.return_value.start.return_value = mock_pw
            with pytest.raises(RuntimeInitError, match="Failed to create context"):
                rt.start()

    def test_create_context_passes_optional_kwargs(self):
        cfg = RuntimeConfig(
            user_agent="TestBot/1.0",
            storage_state={"cookies": []},
            default_timeout_ms=4321,
        )
        rt = ExecutionRuntime(cfg)
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_context
        rt._browser = mock_browser

        rt._create_context()

        mock_browser.new_context.assert_called_once_with(
            viewport={"width": 1280, "height": 720},
            user_agent="TestBot/1.0",
            storage_state={"cookies": []},
        )
        mock_context.set_default_timeout.assert_called_once_with(4321)
        assert rt.page is mock_page


class TestIsPageUsableEdge:
    """Edge cases for is_page_usable."""

    def test_page_is_closed_raises(self):
        """If is_closed() itself raises, return False."""
        rt = ExecutionRuntime()
        mock_page = MagicMock()
        mock_page.is_closed.side_effect = Exception("detached")
        rt._page = mock_page
        assert rt.is_page_usable() is False


class TestPlaywrightErrorWrapping:
    def test_navigate_wraps_playwright_error(self):
        rt = ExecutionRuntime()
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.goto.side_effect = PlaywrightError("bad nav")
        rt._page = mock_page

        with pytest.raises(PageNavigationError, match="Navigation to 'about:blank' failed"):
            rt.navigate("about:blank")

    def test_current_url_wraps_playwright_error(self):
        rt = ExecutionRuntime()
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        type(mock_page).url = PropertyMock(side_effect=PlaywrightError("url boom"))
        rt._page = mock_page

        with pytest.raises(PageObservationError, match="Failed to read URL"):
            rt.current_url()

    def test_current_title_wraps_playwright_error(self):
        rt = ExecutionRuntime()
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.title.side_effect = PlaywrightError("title boom")
        rt._page = mock_page

        with pytest.raises(PageObservationError, match="Failed to read title"):
            rt.current_title()

    def test_current_html_wraps_playwright_error(self):
        rt = ExecutionRuntime()
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.content.side_effect = PlaywrightError("html boom")
        rt._page = mock_page

        with pytest.raises(PageObservationError, match="Failed to read HTML"):
            rt.current_html()

    def test_snapshot_wraps_playwright_error(self):
        rt = ExecutionRuntime()
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        type(mock_page).url = PropertyMock(return_value="about:blank")
        mock_page.title.side_effect = PlaywrightError("snap boom")
        rt._page = mock_page

        with pytest.raises(PageObservationError, match="Snapshot failed"):
            rt.snapshot()

    def test_screenshot_wraps_playwright_error(self):
        rt = ExecutionRuntime()
        mock_page = MagicMock()
        mock_page.is_closed.return_value = False
        mock_page.screenshot.side_effect = PlaywrightError("shot boom")
        rt._page = mock_page

        with pytest.raises(PageObservationError, match="Screenshot failed"):
            rt.screenshot()


class TestScreenshotDirCreation:
    """screenshot_dir is created during start()."""

    def test_screenshot_dir_set_during_start(self, tmp_path):
        sdir = tmp_path / "shots"
        cfg = RuntimeConfig(screenshot_dir=str(sdir))
        rt = ExecutionRuntime(cfg)
        # Simulate a successful start by mocking Playwright internals
        mock_pw = MagicMock()
        mock_browser = MagicMock()
        mock_ctx = MagicMock()
        mock_page = MagicMock()
        mock_ctx.new_page.return_value = mock_page
        mock_browser.new_context.return_value = mock_ctx
        mock_launcher = MagicMock()
        mock_launcher.launch.return_value = mock_browser
        mock_pw.chromium = mock_launcher

        with patch("app.services.execution.execution_runtime.sync_playwright") as mock_sp:
            mock_sp.return_value.start.return_value = mock_pw
            rt.start()

        assert rt._screenshot_dir == sdir
        assert sdir.exists()
        rt.stop()


class TestPageSnapshotModel:
    """PageSnapshot model basic sanity."""

    def test_default_values(self):
        from app.services.execution.execution_runtime import PageSnapshot
        snap = PageSnapshot()
        assert snap.url == ""
        assert snap.title == ""
        assert snap.html == ""


class TestCreateExecutionRuntimeFactory:
    """Factory returns a fresh ExecutionRuntime."""

    def test_returns_runtime(self):
        rt = create_execution_runtime()
        assert isinstance(rt, ExecutionRuntime)
        assert not rt.is_started

    def test_with_config(self):
        cfg = RuntimeConfig(headless=False, browser_type="firefox")
        rt = create_execution_runtime(cfg)
        assert rt.config.headless is False
        assert rt.config.browser_type == "firefox"
