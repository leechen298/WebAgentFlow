"""Wait-for-change service for post-action observation (M11.2.2 MVP).

Provides a minimal post-action short wait that records structured wait results
and observation signals without judging business success.
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

from app.schemas.learned_path_replay import ObservationSignal, WaitResult

PRIMARY_SIGNAL_KINDS = {"url_changed", "title_changed"}


def _now() -> datetime:
    return datetime.now(UTC)


def _short_wait(page, timeout_ms: int) -> None:
    """Perform a short wait using the page when possible."""
    if page is not None and hasattr(page, "wait_for_timeout"):
        try:
            page.wait_for_timeout(timeout_ms)
            return
        except Exception:
            pass
    # Fallback for mock pages or closed pages
    time.sleep(timeout_ms / 1000.0)


def _read_page_state(page) -> tuple[str | None, str | None]:
    """Read current URL and title from *page*, returning (url, title)."""
    if page is None:
        return None, None
    try:
        url = page.url if hasattr(page, "url") else None
        if callable(url):
            url = url()
    except Exception:
        url = None
    try:
        title = page.title if hasattr(page, "title") else None
        if callable(title):
            title = title()
    except Exception:
        title = None
    return url, title


def _try_network_idle(page, timeout_ms: int) -> bool:
    """Attempt to observe network idle within *timeout_ms*.

    Returns True if network idle was observed.  Always returns False for mock
    pages that do not expose ``wait_for_load_state``.
    """
    if page is None or not hasattr(page, "wait_for_load_state"):
        return False
    try:
        page.wait_for_load_state("networkidle", timeout=timeout_ms)
        return True
    except Exception:
        return False


def _make_signal(
    *,
    kind: str,
    url_before: str | None = None,
    url_after: str | None = None,
    title_before: str | None = None,
    title_after: str | None = None,
    related_action_id: str | None = None,
    related_step_id: str | None = None,
    notes: str = "",
) -> ObservationSignal:
    return ObservationSignal(
        signal_id=str(uuid.uuid4()),
        kind=kind,  # type: ignore[arg-type]
        scope="post_action",
        observed_at=_now(),
        url_before=url_before,
        url_after=url_after,
        title_before=title_before,
        title_after=title_after,
        related_action_id=related_action_id,
        related_step_id=related_step_id,
        notes=notes,
    )


def wait_for_change_after_action(
    *,
    page,
    action,
    step_log: dict[str, Any],
    timeout_ms: int = 1000,
    wait_strategy: str = "short_stability_wait",
) -> WaitResult:
    """Run a minimal post-action wait and return a structured ``WaitResult``.

    The service never raises; on internal failure it returns a conservative
    ``skipped`` or ``timeout`` result so that replay status is unaffected.
    """
    action_type = getattr(action, "action_type", "").lower()
    action_ok = step_log.get("ok", False)
    step_index = step_log.get("step_index", getattr(action, "step", 0))

    # Action policy (M11.2.2 MVP)
    if not action_ok and action_type != "observe":
        return WaitResult(
            wait_id=str(uuid.uuid4()),
            related_step_id=str(step_index),
            status="skipped",
            wait_strategy=wait_strategy,
            notes="action failed before wait",
        )

    if action_type == "observe":
        return WaitResult(
            wait_id=str(uuid.uuid4()),
            related_step_id=str(step_index),
            status="not_required",
            wait_strategy=wait_strategy,
            notes="observe action does not require post-action wait",
        )

    if action_type == "fill":
        return WaitResult(
            wait_id=str(uuid.uuid4()),
            related_step_id=str(step_index),
            status="skipped",
            wait_strategy=wait_strategy,
            notes="fill action skipped for MVP (input actions not waited)",
        )

    if action_type == "press":
        return WaitResult(
            wait_id=str(uuid.uuid4()),
            related_step_id=str(step_index),
            status="skipped",
            wait_strategy=wait_strategy,
            notes="press action skipped for MVP (submit/search scenarios deferred)",
        )

    if action_type != "click":
        # Unknown action types are treated conservatively
        return WaitResult(
            wait_id=str(uuid.uuid4()),
            related_step_id=str(step_index),
            status="skipped",
            wait_strategy=wait_strategy,
            notes=f"unsupported action type '{action_type}' skipped for wait",
        )

    # ------------------------------------------------------------------
    # short_stability_wait for click
    # ------------------------------------------------------------------
    started_at = _now()
    observed_signals: list[ObservationSignal] = []
    notes_parts: list[str] = []

    try:
        url_before = step_log.get("url_before")
        title_before = step_log.get("title_before")

        # Budget splitting: stability wait uses a bounded fraction,
        # network idle uses the remaining positive budget.
        stability_wait_ms = min(300, max(0, timeout_ms // 2))
        network_idle_budget_ms = max(0, timeout_ms - stability_wait_ms)

        # Run the short stability wait
        _short_wait(page, stability_wait_ms)

        current_url, current_title = _read_page_state(page)

        # Detect URL change
        if url_before is not None and current_url is not None and current_url != url_before:
            observed_signals.append(
                _make_signal(
                    kind="url_changed",
                    url_before=url_before,
                    url_after=current_url,
                    title_before=title_before,
                    title_after=current_title,
                    related_step_id=str(step_index),
                )
            )

        # Detect title change
        if title_before is not None and current_title is not None and current_title != title_before:
            observed_signals.append(
                _make_signal(
                    kind="title_changed",
                    url_before=url_before,
                    url_after=current_url,
                    title_before=title_before,
                    title_after=current_title,
                    related_step_id=str(step_index),
                )
            )

        # Network idle as supporting signal — uses remaining budget.
        # Skip when budget is exhausted: Playwright treats timeout=0 as
        # "disable timeout", which would hang indefinitely.
        if network_idle_budget_ms > 0 and _try_network_idle(
            page, timeout_ms=network_idle_budget_ms
        ):
            observed_signals.append(
                _make_signal(
                    kind="network_idle_observed",
                    url_before=url_before,
                    url_after=current_url,
                    title_before=title_before,
                    title_after=current_title,
                    related_step_id=str(step_index),
                    notes="supporting signal only",
                )
            )

        # Determine primary signal and status
        effective_primary = None
        for s in observed_signals:
            if s.kind in PRIMARY_SIGNAL_KINDS:
                effective_primary = s
                break

        if effective_primary is not None:
            status = "observed"
        else:
            # No primary/target signal observed
            if any(s.kind == "network_idle_observed" for s in observed_signals):
                status = "timeout"
                notes_parts.append(
                    "network idle observed without primary page-change signal"
                )
            else:
                status = "timeout"
                notes_parts.append(
                    "no primary page-change signal observed within window"
                )

    except Exception as exc:
        ended_at = _now()
        duration_ms = int((ended_at - started_at).total_seconds() * 1000)
        return WaitResult(
            wait_id=str(uuid.uuid4()),
            related_step_id=str(step_index),
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=duration_ms,
            status="skipped",
            timeout_ms=timeout_ms,
            wait_strategy=wait_strategy,
            notes=f"wait failed: {exc}"[:300],
        )

    ended_at = _now()
    duration_ms = int((ended_at - started_at).total_seconds() * 1000)

    if notes_parts:
        notes = "; ".join(notes_parts)
    else:
        notes = ""

    return WaitResult(
        wait_id=str(uuid.uuid4()),
        related_step_id=str(step_index),
        started_at=started_at,
        ended_at=ended_at,
        duration_ms=duration_ms,
        status=status,  # type: ignore[arg-type]
        observed_signals=observed_signals,
        primary_signal=effective_primary,
        timeout_ms=timeout_ms,
        wait_strategy=wait_strategy,
        notes=notes,
    )
