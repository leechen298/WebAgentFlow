"""Tests for the wait-for-change service (M11.2.2 MVP).

All tests use mock pages — no real Playwright browser is started.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.schemas.learned_path_replay import (
    ObservationSignal,
    ReplayStepLog,
    WaitResult,
)
from app.services.learning.wait_for_change import (
    wait_for_change_after_action,
)

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_action(action_type: str = "click", step: int = 0, **kwargs):
    action = MagicMock()
    action.action_type = action_type
    action.step = step
    for k, v in kwargs.items():
        setattr(action, k, v)
    return action


def _make_step_log(
    *,
    ok: bool = True,
    step_index: int = 0,
    url_before: str | None = "http://example.com/before",
    title_before: str | None = "Before",
    url_after: str | None = "http://example.com/before",
    title_after: str | None = "Before",
    **kwargs,
) -> dict:
    return {
        "ok": ok,
        "step_index": step_index,
        "url_before": url_before,
        "title_before": title_before,
        "url_after": url_after,
        "title_after": title_after,
        **kwargs,
    }


def _make_page(*, url: str = "http://example.com/before", title: str = "Before"):
    page = MagicMock()
    page.url = url
    page.title.return_value = title
    return page


# ── Schema validation ────────────────────────────────────────────────────────


def test_wait_status_observed_valid() -> None:
    wr = WaitResult(status="observed")
    assert wr.status == "observed"


def test_wait_status_timeout_valid() -> None:
    wr = WaitResult(status="timeout")
    assert wr.status == "timeout"


def test_wait_status_skipped_valid() -> None:
    wr = WaitResult(status="skipped")
    assert wr.status == "skipped"


def test_wait_status_not_required_valid() -> None:
    wr = WaitResult(status="not_required")
    assert wr.status == "not_required"


def test_wait_status_invalid_rejected() -> None:
    with pytest.raises(ValidationError):
        WaitResult(status="unknown_status")  # type: ignore[arg-type]


def test_replay_step_log_wait_result_optional() -> None:
    """ReplayStepLog without wait_result remains backward compatible."""
    log = ReplayStepLog(step=0, action_type="click")
    assert log.wait_result is None


def test_replay_step_log_with_wait_result() -> None:
    wr = WaitResult(status="observed")
    log = ReplayStepLog(step=0, action_type="click", wait_result=wr)
    assert log.wait_result is not None
    assert log.wait_result.status == "observed"


# ── Action policy ────────────────────────────────────────────────────────────


def test_observe_action_returns_not_required() -> None:
    action = _make_action("observe")
    step_log = _make_step_log(ok=True)
    page = _make_page()

    result = wait_for_change_after_action(page=page, action=action, step_log=step_log)

    assert result.status == "not_required"


def test_fill_action_returns_skipped() -> None:
    action = _make_action("fill")
    step_log = _make_step_log(ok=True)
    page = _make_page()

    result = wait_for_change_after_action(page=page, action=action, step_log=step_log)

    assert result.status == "skipped"
    notes = result.notes.lower()
    assert "fill" in notes or "input" in notes or "skipped" in notes


def test_press_action_returns_skipped() -> None:
    action = _make_action("press")
    step_log = _make_step_log(ok=True)
    page = _make_page()

    result = wait_for_change_after_action(page=page, action=action, step_log=step_log)

    assert result.status == "skipped"


def test_failed_action_returns_skipped() -> None:
    action = _make_action("click")
    step_log = _make_step_log(ok=False)
    page = _make_page()

    result = wait_for_change_after_action(page=page, action=action, step_log=step_log)

    assert result.status == "skipped"
    assert "failed" in result.notes.lower()


# ── Signal detection ─────────────────────────────────────────────────────────


def test_url_change_returns_observed_with_url_changed_primary() -> None:
    action = _make_action("click")
    step_log = _make_step_log(
        ok=True,
        url_before="http://example.com/before",
        title_before="Before",
    )
    page = _make_page(url="http://example.com/after", title="Before")

    result = wait_for_change_after_action(page=page, action=action, step_log=step_log)

    assert result.status == "observed"
    assert result.primary_signal is not None
    assert result.primary_signal.kind == "url_changed"
    assert any(s.kind == "url_changed" for s in result.observed_signals)


def test_title_change_returns_observed_with_title_changed_primary() -> None:
    action = _make_action("click")
    step_log = _make_step_log(
        ok=True,
        url_before="http://example.com/before",
        title_before="Before",
    )
    page = _make_page(url="http://example.com/before", title="After")

    result = wait_for_change_after_action(page=page, action=action, step_log=step_log)

    assert result.status == "observed"
    assert result.primary_signal is not None
    assert result.primary_signal.kind == "title_changed"
    assert any(s.kind == "title_changed" for s in result.observed_signals)


def test_page_load_finished_not_emitted_without_load_evidence() -> None:
    """page_load_finished is omitted in MVP — URL/title change alone is not
    load-completion evidence."""
    action = _make_action("click")
    step_log = _make_step_log(
        ok=True,
        url_before="http://example.com/before",
        title_before="Before",
    )
    page = _make_page(url="http://example.com/after", title="After")

    result = wait_for_change_after_action(page=page, action=action, step_log=step_log)

    assert result.status == "observed"
    assert not any(s.kind == "page_load_finished" for s in result.observed_signals)


def test_no_change_returns_timeout() -> None:
    action = _make_action("click")
    step_log = _make_step_log(
        ok=True,
        url_before="http://example.com/before",
        title_before="Before",
    )
    page = _make_page(url="http://example.com/before", title="Before")

    result = wait_for_change_after_action(page=page, action=action, step_log=step_log)

    assert result.status == "timeout"
    assert result.primary_signal is None


# ── Primary vs supporting signals ────────────────────────────────────────────


def test_network_idle_only_returns_timeout_not_observed() -> None:
    """network_idle_observed alone must not produce status=observed."""
    action = _make_action("click")
    step_log = _make_step_log(
        ok=True,
        url_before="http://example.com/before",
        title_before="Before",
    )
    page = _make_page(url="http://example.com/before", title="Before")
    page.wait_for_load_state = MagicMock()

    result = wait_for_change_after_action(page=page, action=action, step_log=step_log)

    assert result.status == "timeout"
    has_idle_note = (
        "network idle observed without primary page-change signal"
        in result.notes
    )
    assert has_idle_note or "no primary" in result.notes.lower()


def test_primary_signal_cannot_be_network_idle_observed() -> None:
    action = _make_action("click")
    step_log = _make_step_log(
        ok=True,
        url_before="http://example.com/before",
        title_before="Before",
    )
    page = _make_page(url="http://example.com/after", title="After")
    page.wait_for_load_state = MagicMock()

    result = wait_for_change_after_action(page=page, action=action, step_log=step_log)

    assert result.status == "observed"
    if result.primary_signal is not None:
        assert result.primary_signal.kind != "network_idle_observed"


# ── Budget splitting ─────────────────────────────────────────────────────────


def test_short_wait_uses_bounded_fraction() -> None:
    """_short_wait must receive a bounded fraction, not the full timeout_ms."""
    action = _make_action("click")
    step_log = _make_step_log(ok=True)
    page = _make_page()

    with patch(
        "app.services.learning.wait_for_change._short_wait"
    ) as mock_wait:
        with patch(
            "app.services.learning.wait_for_change._try_network_idle",
            return_value=False,
        ):
            wait_for_change_after_action(
                page=page, action=action, step_log=step_log, timeout_ms=1000
            )

    assert mock_wait.called
    stability_ms = mock_wait.call_args[0][1]
    assert stability_ms <= 300
    assert stability_ms >= 0


def test_network_idle_uses_remaining_budget() -> None:
    """_try_network_idle must receive the remaining positive budget."""
    action = _make_action("click")
    step_log = _make_step_log(ok=True)
    page = _make_page()

    with patch(
        "app.services.learning.wait_for_change._short_wait"
    ):
        with patch(
            "app.services.learning.wait_for_change._try_network_idle",
            return_value=False,
        ) as mock_idle:
            wait_for_change_after_action(
                page=page, action=action, step_log=step_log, timeout_ms=1000
            )

    assert mock_idle.called
    idle_ms = mock_idle.call_args[1]["timeout_ms"]
    assert idle_ms > 0
    assert idle_ms <= 1000


def test_network_idle_budget_sums_to_total() -> None:
    """stability + network idle budgets must equal timeout_ms."""
    action = _make_action("click")
    step_log = _make_step_log(ok=True)
    page = _make_page()

    with patch(
        "app.services.learning.wait_for_change._short_wait"
    ) as mock_wait:
        with patch(
            "app.services.learning.wait_for_change._try_network_idle",
            return_value=False,
        ) as mock_idle:
            wait_for_change_after_action(
                page=page, action=action, step_log=step_log, timeout_ms=1000
            )

    stability_ms = mock_wait.call_args[0][1]
    idle_ms = mock_idle.call_args[1]["timeout_ms"]
    assert stability_ms + idle_ms == 1000


def test_non_string_page_state_does_not_create_false_change_signal() -> None:
    """Mock or corrupted page state must not be treated as URL/title changes."""
    action = _make_action("click")
    step_log = _make_step_log(
        ok=True,
        url_before="http://example.com/before",
        title_before="Before",
    )
    page = MagicMock()
    page.wait_for_load_state.side_effect = TimeoutError("not idle")

    result = wait_for_change_after_action(page=page, action=action, step_log=step_log)

    assert result.status == "timeout"
    assert result.primary_signal is None
    assert not any(s.kind in ("url_changed", "title_changed") for s in result.observed_signals)
    assert "wait failed" not in result.notes.lower()


# ── Exception policy ─────────────────────────────────────────────────────────


def test_wait_service_exception_returns_conservative_result() -> None:
    """Internal wait failure must not propagate to replay."""
    action = _make_action("click")
    step_log = _make_step_log(ok=True)
    page = _make_page()

    with patch(
        "app.services.learning.wait_for_change._read_page_state",
        side_effect=RuntimeError("mock crash"),
    ):
        result = wait_for_change_after_action(page=page, action=action, step_log=step_log)

    assert result.status in ("skipped", "timeout")
    assert "wait failed" in result.notes.lower()


# ── No raw HTML / DOM dump ───────────────────────────────────────────────────


def test_signal_has_no_raw_html_field() -> None:
    sig = ObservationSignal(kind="url_changed")
    # Pydantic model fields should not include raw_html or dom_dump
    data = sig.model_dump()
    assert "raw_html" not in data
    assert "dom_dump" not in data
    assert "html" not in data


def test_wait_result_has_no_raw_html_field() -> None:
    wr = WaitResult(status="observed")
    data = wr.model_dump()
    assert "raw_html" not in data
    assert "dom_dump" not in data
    assert "html" not in data


# ── Scope and source ─────────────────────────────────────────────────────────


def test_observation_signal_scope_is_post_action() -> None:
    action = _make_action("click")
    step_log = _make_step_log(ok=True)
    page = _make_page(url="http://example.com/after", title="Before")

    result = wait_for_change_after_action(page=page, action=action, step_log=step_log)

    assert result.status == "observed"
    for sig in result.observed_signals:
        assert sig.scope == "post_action"
