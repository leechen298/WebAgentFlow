"""Post-action observer (Phase 7E).

Captures page facts immediately after a single-step action has been
executed by Phase 7D.  Provides lightweight change detection and
optional target-element status.

Scope — Phase 7E is ONLY immediate post-action fact sampling:
  - NOT wait-until-expected-change   (Phase 8)
  - NOT retry / recovery
  - NOT DOM diff
  - NOT next-action planning
"""

from __future__ import annotations

import hashlib
import logging
import time

from app.schemas.execution import ExecutionResult
from app.schemas.locator import ResolvedLocator
from app.schemas.observation import PostActionObservation, TargetPostState
from app.services.execution_runtime import ExecutionRuntime, PageObservationError
from app.services.locator_resolver import to_playwright_locator

logger = logging.getLogger(__name__)


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def observe_post_action(
    *,
    runtime: ExecutionRuntime,
    execution_result: ExecutionResult,
    resolved_locator: ResolvedLocator | None = None,
    before_url: str = "",
    before_title: str = "",
    before_html_hash: str = "",
) -> PostActionObservation:
    """Capture page state immediately after action execution.

    This is the **single entry point** for post-action observation.
    It never raises — all errors are captured as warnings.

    Parameters
    ----------
    runtime : ExecutionRuntime
        The live Playwright runtime (page must still be usable).
    execution_result : ExecutionResult
        The result from ``execute_action()``.
    resolved_locator : ResolvedLocator, optional
        The locator used by the action, for target post-state checks.
    before_url : str
        URL before the action (from execution_result.page_change or caller).
    before_title : str
        Title before the action.
    before_html_hash : str
        MD5 of HTML before the action, for change detection.
    """
    trace: list[str] = []
    warnings: list[str] = []
    t0 = time.monotonic()
    now_ms = int(time.time() * 1000)

    # Derive before-state from execution_result if not explicitly provided
    if not before_url:
        before_url = execution_result.page_change.url_before
    if not before_title:
        before_title = execution_result.page_change.title_before

    # --- A. Page state snapshot ---
    url = ""
    title = ""
    html = ""
    screenshot_ref: str | None = None
    html_snapshot_ref: str | None = None

    try:
        snap = runtime.snapshot()
        url = snap.url
        title = snap.title
        html = snap.html
        trace.append(f"snapshot: url={url!r}, title={title!r}, html_len={len(html)}")
    except (PageObservationError, Exception) as exc:
        warnings.append(f"Snapshot failed: {exc!r}"[:200])
        trace.append("snapshot: failed")

    # Screenshot
    try:
        screenshot_ref = runtime.screenshot()
        trace.append(f"screenshot: {screenshot_ref}")
    except (PageObservationError, Exception) as exc:
        warnings.append(f"Screenshot failed: {exc!r}"[:200])
        trace.append("screenshot: failed")

    # HTML snapshot ref — store the hash as a lightweight reference
    html_hash = _md5(html) if html else ""
    html_snapshot_ref = f"html:{html_hash}" if html_hash else None

    # --- B. Change detection ---
    url_changed = bool(before_url and url and before_url != url)
    title_changed = bool(before_title and title and before_title != title)
    html_changed = bool(before_html_hash and html_hash and before_html_hash != html_hash)

    if url_changed:
        trace.append(f"change: url {before_url!r} → {url!r}")
    if title_changed:
        trace.append(f"change: title {before_title!r} → {title!r}")
    if html_changed:
        trace.append("change: html content changed")

    # --- D. Target element post-state ---
    target = TargetPostState()
    if resolved_locator and resolved_locator.ok and resolved_locator.descriptor:
        page = runtime.page
        if page and not page.is_closed():
            try:
                loc = to_playwright_locator(page, resolved_locator.descriptor)
                count = loc.count()
                target.still_present = count > 0
                if count > 0:
                    target.still_visible = loc.first.is_visible()
                else:
                    target.still_visible = False
                trace.append(
                    f"target: present={target.still_present}, visible={target.still_visible}"
                )
            except Exception as exc:
                warnings.append(f"Target state check failed: {exc!r}"[:200])
                trace.append("target: check failed")

    elapsed = int((time.monotonic() - t0) * 1000)

    return PostActionObservation(
        url=url,
        title=title,
        screenshot_ref=screenshot_ref,
        html_snapshot_ref=html_snapshot_ref,
        url_changed=url_changed,
        title_changed=title_changed,
        html_changed=html_changed,
        html_length=len(html),
        html_hash=html_hash,
        timestamp_ms=now_ms,
        elapsed_since_action_ms=elapsed,
        target=target,
        warnings=warnings,
        trace=trace,
    )


def execute_and_observe(
    request,
    runtime: ExecutionRuntime,
) -> ExecutionResult:
    """Execute a single action and attach post-action observation.

    Convenience wrapper that chains 7D ``execute_action`` with 7E
    ``observe_post_action`` and attaches the observation to the
    ``ExecutionResult``.

    This is the recommended entry point for the full execute→observe
    pipeline.
    """
    from app.services.action_executor import execute_action
    from app.services.locator_resolver import resolve_locator

    # Capture before-state HTML hash for change detection
    before_html_hash = ""
    try:
        before_html = runtime.current_html()
        before_html_hash = _md5(before_html)
    except Exception:
        pass

    # Resolve locator (needed for target post-state)
    resolved = None
    if request.action.action_type != "navigate" and request.locator_hints:
        try:
            resolved = resolve_locator(request, runtime)
        except Exception:
            pass

    # Execute (pass pre-resolved locator to avoid double resolution)
    result = execute_action(request, runtime, _resolved_locator=resolved)

    # Observe
    obs = observe_post_action(
        runtime=runtime,
        execution_result=result,
        resolved_locator=resolved,
        before_html_hash=before_html_hash,
    )

    # Attach observation to result
    result.observation = obs.model_dump()
    result.screenshot_ref = obs.screenshot_ref
    result.html_snapshot_ref = obs.html_snapshot_ref

    return result
