"""Tests for autonomous_explorer._assess_outcome.

The rule-based self-verdict is the first line of outcome assessment —
it runs before the LLM supervisor and seeds the supervisor's context.
When it mis-fires (e.g. missing an SPA URL change), everything
downstream — scorecard, history display, supervisor agreement —
inherits the wrong signal.

Regression focus: SPA flows where the click step's url_after is
still the pre-route URL (the async router hasn't pushed yet) and
only the subsequent observe step sees the final URL. Before the G
fix that meant a login that LANDED on /dashboard got verdicted as
no_progress.
"""

from __future__ import annotations

from app.services.learning.autonomous_explorer import _assess_outcome


def _fill_step(**overrides: object) -> dict:
    base = {
        "step_index": 0,
        "action_type": "fill",
        "ok": True,
        "url_before": "http://t/login",
        "url_after": "http://t/login",
        "title_before": "Sign in",
        "title_after": "Sign in",
        "url_changed": False,
        "title_changed": False,
    }
    base.update(overrides)
    return base


def _click_step(**overrides: object) -> dict:
    base = {
        "step_index": 1,
        "action_type": "click",
        "ok": True,
        "url_before": "http://t/login",
        "url_after": "http://t/login",
        "title_before": "Sign in",
        "title_after": "Sign in",
        "url_changed": False,
        "title_changed": False,
    }
    base.update(overrides)
    return base


def _observe_step(**overrides: object) -> dict:
    base = {
        "step_index": 99,
        "action_type": "observe",
        "ok": True,
        "url": "http://t/login",
        "title": "Sign in",
        "result_signals": {
            "result_row_count": 0,
            "has_captcha": False,
            "has_login_wall": False,
            "visible_text_length": 100,
        },
    }
    base.update(overrides)
    return base


# ───────────────────────────────────────────────────────────────────
# SPA URL change folds in via the observe step
# ───────────────────────────────────────────────────────────────────


def test_spa_url_change_detected_via_observe() -> None:
    # Mirrors the login/valid_credentials flow: click step sees
    # url_before=url_after=/login (router hasn't pushed yet), but
    # observe step sees /dashboard.
    steps = [
        _fill_step(step_index=0),
        _fill_step(step_index=1, action_type="fill"),
        _click_step(step_index=2, url_before="http://t/login", url_after="http://t/login"),
        _observe_step(step_index=3, url="http://t/dashboard", title="Dashboard"),
    ]
    verdict, summary = _assess_outcome(steps)
    assert verdict == "success"
    assert "URL" in summary


def test_spa_title_change_detected_via_observe() -> None:
    # Click step registers no title change but observe sees a
    # different title (SPA swapped document.title after the waits).
    steps = [
        _click_step(
            step_index=0,
            url_before="http://t/a",
            url_after="http://t/a",
            title_before="Before",
            title_after="Before",
        ),
        _observe_step(step_index=1, url="http://t/a", title="After"),
    ]
    verdict, summary = _assess_outcome(steps)
    assert verdict == "success"


def test_no_change_when_observe_matches_initial() -> None:
    # SPA-like shape but observe URL still matches initial URL, and
    # no click-step-local change — should still be no_progress (the
    # filter search-but-URL-unchanged scenario).
    steps = [
        _fill_step(step_index=0),
        _click_step(step_index=1),
        _observe_step(step_index=2, url="http://t/login", title="Sign in"),
    ]
    verdict, summary = _assess_outcome(steps)
    assert verdict == "no_progress"


def test_click_step_local_change_still_counts() -> None:
    # Regression: the existing url_changed/title_changed detection
    # via the click step itself must still work when the click step
    # DID observe the change in-place.
    steps = [
        _click_step(
            step_index=0,
            url_before="http://t/a",
            url_after="http://t/b",
            url_changed=True,
        ),
        _observe_step(step_index=1, url="http://t/b", title="Sign in"),
    ]
    verdict, _ = _assess_outcome(steps)
    assert verdict == "success"


# ───────────────────────────────────────────────────────────────────
# Pre-existing signal paths — regression guards
# ───────────────────────────────────────────────────────────────────


def test_login_wall_still_no_progress() -> None:
    # Observe sees login wall → blocker wins over any URL check.
    steps = [
        _fill_step(step_index=0),
        _click_step(step_index=1),
        _observe_step(
            step_index=2,
            url="http://t/login",
            title="Sign in",
            result_signals={
                "result_row_count": 0,
                "has_captcha": False,
                "has_login_wall": True,
                "visible_text_length": 100,
            },
        ),
    ]
    verdict, summary = _assess_outcome(steps)
    assert verdict == "no_progress"
    assert "login wall" in summary


def test_all_actions_failed_is_incomplete() -> None:
    steps = [
        _fill_step(step_index=0, ok=False, error="not found"),
        _click_step(step_index=1, ok=False, error="no element"),
        _observe_step(step_index=2),
    ]
    verdict, _ = _assess_outcome(steps)
    assert verdict == "incomplete"


def test_only_fill_no_submit_is_no_progress() -> None:
    # Fill succeeded but there's no click/press → no state trigger.
    steps = [
        _fill_step(step_index=0),
        _observe_step(step_index=1),
    ]
    verdict, _ = _assess_outcome(steps)
    assert verdict == "no_progress"
