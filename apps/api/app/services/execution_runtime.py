"""Playwright execution runtime (Phase 7B).

Provides a unified ``ExecutionRuntime`` that manages the Playwright
browser → context → page lifecycle.  All subsequent Phase 7 modules
(7C locator, 7D executor, 7E observer) work through this single
runtime instance — they do NOT create their own browsers/contexts/pages.

Scope — Phase 7B is ONLY the browser environment layer:
  - NOT a locator resolver          (7C)
  - NOT an action executor          (7D)
  - NOT a post-action observer      (7E)
  - NOT an API/debug entry point    (7F)
  - NOT a wait/retry/recovery system
  - NOT a task planner

Capabilities provided:
  1. Browser / context / page lifecycle management
  2. Page navigation
  3. Basic page observation (URL, title, HTML, screenshot)
  4. Page health checks
  5. Unified error handling
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Page,
    Playwright,
    sync_playwright,
)
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────
# Error types
# ───────────────────────────────────────────────────────────────────

class ExecutionRuntimeError(Exception):
    """Base for all execution-runtime errors."""


class RuntimeInitError(ExecutionRuntimeError):
    """Browser or context failed to initialise."""


class PageNavigationError(ExecutionRuntimeError):
    """Page navigation failed."""


class PageObservationError(ExecutionRuntimeError):
    """Failed to observe page state (URL, title, HTML, screenshot)."""


# ───────────────────────────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────────────────────────

class RuntimeConfig(BaseModel):
    """Configuration for ``ExecutionRuntime``.

    All fields have sensible defaults so a bare ``RuntimeConfig()``
    gives a working headless Chromium session.
    """

    headless: bool = True
    browser_type: str = Field(
        default="chromium",
        description="Playwright browser type: chromium, firefox, webkit.",
    )
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: str | None = None
    storage_state: str | dict[str, Any] | None = Field(
        default=None,
        description="Path or dict for BrowserContext.storage_state (cookies, localStorage).",
    )
    default_timeout_ms: int = 30_000
    screenshot_dir: str | None = Field(
        default=None,
        description="Directory for screenshots.  Uses a temp dir when None.",
    )


# ───────────────────────────────────────────────────────────────────
# Page observation result
# ───────────────────────────────────────────────────────────────────

class PageSnapshot(BaseModel):
    """Lightweight snapshot of page state at a point in time."""

    url: str = ""
    title: str = ""
    html: str = ""


# ───────────────────────────────────────────────────────────────────
# Runtime
# ───────────────────────────────────────────────────────────────────

class ExecutionRuntime:
    """Unified Playwright execution runtime.

    Manages one browser → one context → one active page.  Provides
    navigation, observation, and screenshot capabilities that 7C/7D/7E
    build on top of.

    Usage::

        rt = create_execution_runtime()
        rt.start()
        try:
            rt.navigate("https://example.com")
            snap = rt.snapshot()
            path = rt.screenshot()
        finally:
            rt.stop()

    Or as a context manager::

        with create_execution_runtime() as rt:
            rt.navigate("https://example.com")
    """

    def __init__(self, config: RuntimeConfig | None = None) -> None:
        self._config = config or RuntimeConfig()
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._screenshot_dir: Path | None = None
        self._started = False

    # ── Properties ────────────────────────────────────────────────

    @property
    def config(self) -> RuntimeConfig:
        return self._config

    @property
    def browser(self) -> Browser | None:
        return self._browser

    @property
    def context(self) -> BrowserContext | None:
        return self._context

    @property
    def page(self) -> Page | None:
        return self._page

    @property
    def is_started(self) -> bool:
        return self._started

    # ── Lifecycle ─────────────────────────────────────────────────

    def start(self) -> None:
        """Start the Playwright runtime: browser → context → page.

        Raises ``RuntimeInitError`` if any step fails.
        """
        if self._started:
            return

        try:
            self._pw = sync_playwright().start()
        except Exception as exc:
            raise RuntimeInitError(f"Failed to start Playwright: {exc}") from exc

        try:
            launcher = getattr(self._pw, self._config.browser_type, None)
            if launcher is None:
                self._cleanup_pw()
                raise RuntimeInitError(
                    f"Unknown browser type: {self._config.browser_type}"
                )
            self._browser = launcher.launch(headless=self._config.headless)
        except RuntimeInitError:
            raise
        except Exception as exc:
            self._cleanup_pw()
            raise RuntimeInitError(f"Failed to launch browser: {exc}") from exc

        try:
            self._create_context()
        except RuntimeInitError:
            self._cleanup_browser()
            raise
        except Exception as exc:
            self._cleanup_browser()
            raise RuntimeInitError(f"Failed to create context: {exc}") from exc

        # Resolve screenshot directory
        if self._config.screenshot_dir:
            self._screenshot_dir = Path(self._config.screenshot_dir)
            self._screenshot_dir.mkdir(parents=True, exist_ok=True)

        self._started = True
        logger.info(
            "ExecutionRuntime started (browser=%s, headless=%s)",
            self._config.browser_type,
            self._config.headless,
        )

    def stop(self) -> None:
        """Tear down everything: page → context → browser → Playwright."""
        if not self._started:
            return
        self._close_page()
        self._close_context()
        self._cleanup_browser()
        self._cleanup_pw()
        self._started = False
        logger.info("ExecutionRuntime stopped")

    def _create_context(self) -> None:
        """Create a new BrowserContext (and an initial page)."""
        if self._browser is None:
            raise RuntimeInitError("Browser not available — call start() first")

        ctx_kwargs: dict[str, Any] = {
            "viewport": {
                "width": self._config.viewport_width,
                "height": self._config.viewport_height,
            },
        }
        if self._config.user_agent:
            ctx_kwargs["user_agent"] = self._config.user_agent
        if self._config.storage_state:
            ctx_kwargs["storage_state"] = self._config.storage_state

        try:
            self._context = self._browser.new_context(**ctx_kwargs)
            self._context.set_default_timeout(self._config.default_timeout_ms)
            self._page = self._context.new_page()
        except Exception as exc:
            self._close_context()
            raise RuntimeInitError(f"Context/page creation failed: {exc}") from exc

    # ── Navigation ────────────────────────────────────────────────

    def navigate(self, url: str, *, wait_until: str = "load") -> None:
        """Navigate the active page to *url*.

        Raises ``PageNavigationError`` on failure or if no usable page.
        """
        if self._page is None or self._page.is_closed():
            raise PageNavigationError(
                "No usable page — runtime not started or page was closed."
            )
        page = self._page
        try:
            page.goto(url, wait_until=wait_until)
        except PlaywrightError as exc:
            raise PageNavigationError(f"Navigation to {url!r} failed: {exc}") from exc

    # ── Observation ───────────────────────────────────────────────

    def current_url(self) -> str:
        """Return the active page's URL."""
        page = self._ensure_page()
        try:
            return page.url
        except PlaywrightError as exc:
            raise PageObservationError(f"Failed to read URL: {exc}") from exc

    def current_title(self) -> str:
        """Return the active page's title."""
        page = self._ensure_page()
        try:
            return page.title()
        except PlaywrightError as exc:
            raise PageObservationError(f"Failed to read title: {exc}") from exc

    def current_html(self) -> str:
        """Return the active page's full HTML content."""
        page = self._ensure_page()
        try:
            return page.content()
        except PlaywrightError as exc:
            raise PageObservationError(f"Failed to read HTML: {exc}") from exc

    def snapshot(self) -> PageSnapshot:
        """Capture URL + title + HTML in one call."""
        page = self._ensure_page()
        try:
            return PageSnapshot(
                url=page.url,
                title=page.title(),
                html=page.content(),
            )
        except PlaywrightError as exc:
            raise PageObservationError(f"Snapshot failed: {exc}") from exc

    def screenshot(self, *, full_page: bool = False) -> str:
        """Take a screenshot and return the file path.

        Uses ``screenshot_dir`` from config, or a temp directory.
        """
        page = self._ensure_page()
        try:
            if self._screenshot_dir:
                import time
                path = self._screenshot_dir / f"screenshot_{int(time.time() * 1000)}.png"
            else:
                fd, tmp = tempfile.mkstemp(suffix=".png", prefix="exec_screenshot_")
                import os
                os.close(fd)
                path = Path(tmp)
            page.screenshot(path=str(path), full_page=full_page)
            return str(path)
        except PlaywrightError as exc:
            raise PageObservationError(f"Screenshot failed: {exc}") from exc

    # ── Health ────────────────────────────────────────────────────

    def is_page_usable(self) -> bool:
        """Check whether the active page is still usable."""
        if self._page is None:
            return False
        try:
            return not self._page.is_closed()
        except Exception:
            return False

    # ── Context manager ───────────────────────────────────────────

    def __enter__(self) -> ExecutionRuntime:
        self.start()
        return self

    def __exit__(self, *_: Any) -> None:
        self.stop()

    # ── Internal helpers ──────────────────────────────────────────

    def _ensure_page(self) -> Page:
        """Return the active page or raise."""
        if self._page is None or self._page.is_closed():
            raise PageObservationError(
                "No usable page — runtime not started or page was closed."
            )
        return self._page

    def _close_page(self) -> None:
        if self._page and not self._page.is_closed():
            try:
                self._page.close()
            except Exception:
                pass
        self._page = None

    def _close_context(self) -> None:
        self._close_page()
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None

    def _cleanup_browser(self) -> None:
        self._close_context()
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None

    def _cleanup_pw(self) -> None:
        if self._pw:
            try:
                self._pw.stop()
            except Exception:
                pass
            self._pw = None


# ───────────────────────────────────────────────────────────────────
# Factory
# ───────────────────────────────────────────────────────────────────

def create_execution_runtime(
    config: RuntimeConfig | None = None,
) -> ExecutionRuntime:
    """Create an ``ExecutionRuntime`` instance.

    This is the single entry point for obtaining a runtime.  Subsequent
    Phase 7 modules (7C, 7D, 7E) receive the runtime — they do NOT
    construct their own.
    """
    return ExecutionRuntime(config)
