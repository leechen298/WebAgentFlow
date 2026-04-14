"""Action executor (Phase 7D).

Executes a single atomic action on the Playwright page using the
locator resolved by Phase 7C.

Pipeline: ExecutionRequest → resolve_locator (7C) → execute action → ExecutionResult

Scope — Phase 7D is ONLY single-step action execution:
  - NOT post-action observation / DOM diff  (7E)
  - NOT wait-until-expected-change           (7E)
  - NOT retry / recovery
  - NOT multi-step orchestration
  - NOT task planning
"""

from __future__ import annotations

import logging
import time
from typing import Any

from playwright.sync_api import Error as PlaywrightError

from app.schemas.execution import (
    ExecutionRequest,
    ExecutionResult,
    LocatorResult,
    PageStateChange,
)
from app.services.execution_runtime import ExecutionRuntime, PageObservationError
from app.services.locator_resolver import resolve_locator, to_playwright_locator

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────
# Action handlers
# ───────────────────────────────────────────────────────────────────

def _do_click(page, locator, request: ExecutionRequest) -> None:
    locator.click()


def _do_fill(page, locator, request: ExecutionRequest) -> None:
    value = request.action.value
    if value is None:
        raise ValueError("fill requires a value but action.value is None")
    locator.fill(value)


def _do_select(page, locator, request: ExecutionRequest) -> None:
    value = request.action.value
    if value is None:
        raise ValueError("select requires a value but action.value is None")
    locator.select_option(value)


def _do_check(page, locator, request: ExecutionRequest) -> None:
    locator.check()


def _do_uncheck(page, locator, request: ExecutionRequest) -> None:
    locator.uncheck()


def _do_hover(page, locator, request: ExecutionRequest) -> None:
    locator.hover()


def _do_press(page, locator, request: ExecutionRequest) -> None:
    key = request.action.value
    if not key:
        raise ValueError("press requires a key value (e.g. 'Enter') but action.value is empty")
    locator.press(key)


def _do_navigate(page, locator, request: ExecutionRequest) -> None:
    # navigate is a page-level action, not a locator action
    url = request.action.value or request.page.url
    if not url:
        raise ValueError("navigate requires a URL in action.value or page.url")
    page.goto(url, wait_until="load")


def _do_scroll(page, locator, request: ExecutionRequest) -> None:
    locator.scroll_into_view_if_needed()


_ACTION_HANDLERS: dict[str, Any] = {
    "click": _do_click,
    "fill": _do_fill,
    "select": _do_select,
    "check": _do_check,
    "uncheck": _do_uncheck,
    "hover": _do_hover,
    "press": _do_press,
    "navigate": _do_navigate,
    "scroll": _do_scroll,
}
"""Centralized action type → handler mapping."""


# ───────────────────────────────────────────────────────────────────
# Internal helpers
# ───────────────────────────────────────────────────────────────────

def _capture_page_state(runtime: ExecutionRuntime) -> tuple[str, str]:
    """Capture current URL and title, tolerating errors."""
    try:
        url = runtime.current_url()
    except (PageObservationError, Exception):
        url = ""
    try:
        title = runtime.current_title()
    except (PageObservationError, Exception):
        title = ""
    return url, title


# ───────────────────────────────────────────────────────────────────
# Public API
# ───────────────────────────────────────────────────────────────────

def execute_action(
    request: ExecutionRequest,
    runtime: ExecutionRuntime,
    *,
    _resolved_locator=None,
) -> ExecutionResult:
    """Execute a single atomic action on the Playwright page.

    This is the **single entry point** for action execution.

    Pipeline:
      1. Capture before-state (URL, title)
      2. Resolve locator via 7C ``resolve_locator()``
      3. Execute the action using the appropriate Playwright API
      4. Capture after-state (URL, title)
      5. Return a unified ``ExecutionResult``

    This function never raises — all errors are captured in the
    returned ``ExecutionResult``.
    """
    trace: list[str] = []
    warnings: list[str] = []
    action_type = request.action.action_type
    target_summary = request.action.target_description
    t0 = time.monotonic()

    # --- 1. Before-state ---
    url_before, title_before = _capture_page_state(runtime)
    trace.append(f"before: url={url_before!r}")

    # --- 2. Resolve locator (delegate to 7C) ---
    # Navigate is page-level, doesn't need element locator
    if action_type == "navigate":
        trace.append("action=navigate, skipping locator resolution")
        resolved = None
        locator_result = LocatorResult()
    else:
        resolved = _resolved_locator or resolve_locator(request, runtime)
        trace.extend(resolved.trace)

        locator_result = LocatorResult(
            resolved_locator=resolved.descriptor.selector if resolved.descriptor else "",
            strategy_used=resolved.source,
            confidence=resolved.confidence,
            candidates_considered=resolved.matched_count,
        )

        if not resolved.ok:
            url_after, title_after = _capture_page_state(runtime)
            return ExecutionResult(
                ok=False,
                action_type=action_type,
                target_summary=target_summary,
                locator=locator_result,
                page_change=PageStateChange(
                    url_before=url_before, url_after=url_after,
                    title_before=title_before, title_after=title_after,
                ),
                error=f"Locator resolution failed: {resolved.trace[-1] if resolved.trace else 'unknown'}",
                warnings=warnings,
                trace=trace,
                elapsed_ms=int((time.monotonic() - t0) * 1000),
            )

        if resolved.fallback_used:
            warnings.append(f"Degraded locator used (source={resolved.source})")

    # --- 3. Execute action ---
    handler = _ACTION_HANDLERS.get(action_type)
    if handler is None:
        url_after, title_after = _capture_page_state(runtime)
        return ExecutionResult(
            ok=False,
            action_type=action_type,
            target_summary=target_summary,
            locator=locator_result,
            page_change=PageStateChange(
                url_before=url_before, url_after=url_after,
                title_before=title_before, title_after=title_after,
            ),
            error=f"Unsupported action type: {action_type!r}",
            warnings=warnings,
            trace=trace,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

    page = runtime.page
    try:
        if action_type == "navigate":
            trace.append(f"executing: navigate to {request.action.value or request.page.url!r}")
            handler(page, None, request)
        else:
            pw_locator = to_playwright_locator(page, resolved.descriptor)
            trace.append(f"executing: {action_type}")
            handler(page, pw_locator, request)
    except ValueError as exc:
        # Missing value / invalid args
        url_after, title_after = _capture_page_state(runtime)
        return ExecutionResult(
            ok=False,
            action_type=action_type,
            target_summary=target_summary,
            locator=locator_result,
            page_change=PageStateChange(
                url_before=url_before, url_after=url_after,
                title_before=title_before, title_after=title_after,
            ),
            error=str(exc),
            warnings=warnings,
            trace=trace,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )
    except PlaywrightError as exc:
        url_after, title_after = _capture_page_state(runtime)
        error_msg = str(exc)
        # Classify common Playwright errors
        if "detached" in error_msg.lower():
            trace.append("element detached from DOM")
        elif "not visible" in error_msg.lower() or "hidden" in error_msg.lower():
            trace.append("element not visible")
        elif "timeout" in error_msg.lower():
            trace.append("action timed out")
        return ExecutionResult(
            ok=False,
            action_type=action_type,
            target_summary=target_summary,
            locator=locator_result,
            page_change=PageStateChange(
                url_before=url_before, url_after=url_after,
                title_before=title_before, title_after=title_after,
            ),
            error=error_msg[:500],
            warnings=warnings,
            trace=trace,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception as exc:
        url_after, title_after = _capture_page_state(runtime)
        return ExecutionResult(
            ok=False,
            action_type=action_type,
            target_summary=target_summary,
            locator=locator_result,
            page_change=PageStateChange(
                url_before=url_before, url_after=url_after,
                title_before=title_before, title_after=title_after,
            ),
            error=f"Unexpected error: {exc!r}"[:500],
            warnings=warnings,
            trace=trace,
            elapsed_ms=int((time.monotonic() - t0) * 1000),
        )

    # --- 4. After-state ---
    url_after, title_after = _capture_page_state(runtime)
    trace.append(f"after: url={url_after!r}")

    return ExecutionResult(
        ok=True,
        action_type=action_type,
        target_summary=target_summary,
        locator=locator_result,
        page_change=PageStateChange(
            url_before=url_before,
            url_after=url_after,
            title_before=title_before,
            title_after=title_after,
        ),
        warnings=warnings,
        trace=trace,
        elapsed_ms=int((time.monotonic() - t0) * 1000),
    )
