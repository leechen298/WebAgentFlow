"""Tests for the LearnedPath replay drift checker."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.models.learned_path import LearnedPath, TrustStatus
from app.schemas.page_analysis import PageAnalysis
from app.services.learning.learned_path_replay import (
    SUPPORTED_ACTION_TYPES,
    _build_replay_actions,
    run_drift_precheck,
)
from app.services.learning.page_signature import (
    dom_fingerprint,
    path_template,
    query_signature,
)

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_learned_path(**overrides) -> LearnedPath:
    defaults = dict(
        id="lp-001",
        page_template="/users",
        query_signature={},
        dom_fingerprint="abc123",
        scenario="test",
        actions=[],
        trust=TrustStatus.CONFIRMED,
        hit_count=1,
        source_run_id=None,
        dedup_key="dk1",
    )
    defaults.update(overrides)
    return LearnedPath(**defaults)


def _make_page_analysis(**overrides) -> PageAnalysis:
    defaults = dict(
        url="http://127.0.0.1:5175/users",
        title="Users",
    )
    defaults.update(overrides)
    return PageAnalysis(**defaults)


def _make_page(selector_counts: dict[str, int] | None = None) -> MagicMock:
    """Return a mock Playwright Page whose ``locator(selector).count()``
    obeys the *selector_counts* map."""
    counts = selector_counts or {}

    def _locator(selector: str):
        locator_mock = MagicMock()
        locator_mock.count.return_value = counts.get(selector, 0)
        return locator_mock

    page = MagicMock()
    page.locator.side_effect = _locator
    return page


# ── _build_replay_actions ────────────────────────────────────────────────────


def test_build_replay_actions_fills_missing_step() -> None:
    raw = [
        {"action_type": "fill", "target_selector": "#a"},
        {"action_type": "click", "target_selector": "#b"},
    ]
    actions = _build_replay_actions(raw)
    assert [a.step for a in actions] == [0, 1]
    assert actions[0].action_type == "fill"
    assert actions[1].action_type == "click"


def test_build_replay_actions_preserves_provided_step() -> None:
    raw = [
        {"step": 5, "action_type": "press", "target_selector": "#x", "value": "Enter"},
    ]
    actions = _build_replay_actions(raw)
    assert len(actions) == 1
    assert actions[0].step == 5
    assert actions[0].value == "Enter"


# ── page_mismatch ────────────────────────────────────────────────────────────


def test_page_mismatch_blocks_replay() -> None:
    path = _make_learned_path(page_template="/users")
    analysis = _make_page_analysis(url="http://127.0.0.1:5175/orders")
    page = _make_page()

    result = run_drift_precheck(path, analysis.url, analysis, page)

    assert result.drift_status == "page_mismatch"
    assert result.blocked is True
    assert result.blocked_status == "drifted"
    assert "template mismatch" in result.drift_reasons[0].lower()


# ── unsupported_action ───────────────────────────────────────────────────────


def test_unsupported_action_blocks_replay() -> None:
    path = _make_learned_path(
        actions=[
            {"step": 0, "action_type": "swipe", "target_selector": "#x"},
        ]
    )
    analysis = _make_page_analysis()
    page = _make_page()

    result = run_drift_precheck(path, analysis.url, analysis, page)

    assert result.drift_status == "unsupported_action"
    assert result.blocked is True
    assert result.blocked_status == "unsupported"
    assert "swipe" in result.drift_reasons[0]


def test_all_supported_action_types_accepted() -> None:
    for typ in SUPPORTED_ACTION_TYPES:
        path = _make_learned_path(
            actions=[{"step": 0, "action_type": typ, "target_selector": "#x"}]
        )
        analysis = _make_page_analysis()
        page = _make_page({"#x": 1})

        result = run_drift_precheck(path, analysis.url, analysis, page)
        assert result.drift_status != "unsupported_action", f"{typ} should be supported"


# ── target_missing ───────────────────────────────────────────────────────────


def test_target_missing_blocks_replay() -> None:
    path = _make_learned_path(
        actions=[
            {"step": 0, "action_type": "fill", "target_selector": "#missing"},
        ]
    )
    analysis = _make_page_analysis()
    page = _make_page({"#missing": 0})

    result = run_drift_precheck(path, analysis.url, analysis, page)

    assert result.drift_status == "target_missing"
    assert result.blocked is True
    assert result.blocked_status == "drifted"
    assert "#missing" in result.drift_reasons[0]


def test_target_missing_skips_observe_actions() -> None:
    """observe actions do not require a locatable selector."""
    analysis = _make_page_analysis()
    fp = dom_fingerprint(analysis)
    path = _make_learned_path(
        dom_fingerprint=fp,
        actions=[
            {"step": 0, "action_type": "observe", "target_selector": "#gone"},
        ],
    )
    page = _make_page({"#gone": 0})

    result = run_drift_precheck(path, analysis.url, analysis, page)

    assert result.drift_status == "none"
    assert result.blocked is False


# ── signature_changed ────────────────────────────────────────────────────────


def test_signature_changed_query_mismatch() -> None:
    path = _make_learned_path(
        query_signature={"status": "active"},
    )
    url = "http://127.0.0.1:5175/users?status=draft"
    analysis = _make_page_analysis(url=url)
    page = _make_page()

    result = run_drift_precheck(path, url, analysis, page)

    assert result.drift_status == "signature_changed"
    assert result.blocked is False
    assert any("signature" in w.lower() for w in result.warnings)


def test_signature_changed_dom_mismatch() -> None:
    real_fp = dom_fingerprint(_make_page_analysis())
    path = _make_learned_path(
        dom_fingerprint="different-fingerprint",
    )
    url = "http://127.0.0.1:5175/users"
    analysis = _make_page_analysis(url=url)
    page = _make_page()

    result = run_drift_precheck(path, url, analysis, page)

    assert result.drift_status == "signature_changed"
    assert result.blocked is False
    assert result.warnings


def test_signature_changed_allows_replay_when_selectors_present() -> None:
    path = _make_learned_path(
        dom_fingerprint="old",
        actions=[
            {"step": 0, "action_type": "fill", "target_selector": "#name"},
        ],
    )
    url = "http://127.0.0.1:5175/users"
    analysis = _make_page_analysis(url=url)
    page = _make_page({"#name": 1})

    result = run_drift_precheck(path, url, analysis, page)

    assert result.drift_status == "signature_changed"
    assert result.blocked is False
    assert len(result.actions) == 1


# ── none (no drift) ──────────────────────────────────────────────────────────


def test_none_when_everything_aligns() -> None:
    analysis = _make_page_analysis()
    fp = dom_fingerprint(analysis)
    path = _make_learned_path(
        dom_fingerprint=fp,
        actions=[
            {"step": 0, "action_type": "click", "target_selector": "#btn"},
        ],
    )
    page = _make_page({"#btn": 1})

    result = run_drift_precheck(path, analysis.url, analysis, page)

    assert result.drift_status == "none"
    assert result.blocked is False
    assert len(result.actions) == 1
    assert not result.warnings


# ── observational paths (actions=[]) ─────────────────────────────────────────


def test_observational_path_no_drift() -> None:
    analysis = _make_page_analysis()
    fp = dom_fingerprint(analysis)
    path = _make_learned_path(
        dom_fingerprint=fp,
        actions=[],
    )
    page = _make_page()

    result = run_drift_precheck(path, analysis.url, analysis, page)

    assert result.drift_status == "none"
    assert result.blocked is False
    assert result.actions == []


def test_observational_path_signature_changed() -> None:
    path = _make_learned_path(
        dom_fingerprint="old-fp",
        actions=[],
    )
    analysis = _make_page_analysis()
    page = _make_page()

    result = run_drift_precheck(path, analysis.url, analysis, page)

    assert result.drift_status == "signature_changed"
    assert result.blocked is False
    assert result.warnings
    assert result.actions == []


def test_observational_path_page_mismatch() -> None:
    path = _make_learned_path(
        page_template="/users",
        actions=[],
    )
    analysis = _make_page_analysis(url="http://127.0.0.1:5175/orders")
    page = _make_page()

    result = run_drift_precheck(path, analysis.url, analysis, page)

    assert result.drift_status == "page_mismatch"
    assert result.blocked is True
    assert result.blocked_status == "drifted"
