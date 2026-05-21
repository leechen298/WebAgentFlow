"""Tests for the LearnedPath replay drift checker and full replay."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.models.learned_path import LearnedPath, TrustStatus
from app.schemas.learned_path_replay import (
    ExecutionEvidence,
    ExecutionEvidenceTarget,
    ReplayRequest,
    WaitResult,
)
from app.schemas.page_analysis import PageAnalysis
from app.services.learning.learned_path_replay import (
    SUPPORTED_ACTION_TYPES,
    _build_replay_actions,
    capture_execution_evidence,
    run_drift_precheck,
    run_replay,
)
from app.services.learning.page_signature import (
    dom_fingerprint,
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


def _make_text_page(selector_text: dict[str, str | Exception]) -> MagicMock:
    def _locator(selector: str):
        locator_mock = MagicMock()
        value = selector_text.get(selector, "")
        if isinstance(value, Exception):
            locator_mock.inner_text.side_effect = value
        else:
            locator_mock.inner_text.return_value = value
        locator_mock.count.return_value = 1
        return locator_mock

    page = MagicMock()
    page.is_closed.return_value = False
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


def test_replay_request_slot_overrides_defaults_to_empty_dict() -> None:
    request = ReplayRequest(url="http://127.0.0.1:5175/users")

    assert request.slot_overrides == {}
    assert request.evidence_targets == []


def test_replay_request_accepts_slot_overrides() -> None:
    request = ReplayRequest(
        url="http://127.0.0.1:5176/items",
        slot_overrides={"item_name": "测试项目B"},
    )

    assert request.slot_overrides == {"item_name": "测试项目B"}


def test_replay_request_accepts_evidence_targets() -> None:
    request = ReplayRequest(
        url="http://127.0.0.1:5176/items",
        evidence_targets=[
            {
                "kind": "dom_text_present",
                "text": "测试项目B-001",
                "source_slot": "item_name",
                "selector": "[data-testid='item-list']",
            }
        ],
    )

    target = request.evidence_targets[0]
    assert target.kind == "dom_text_present"
    assert target.text == "测试项目B-001"
    assert target.source_slot == "item_name"
    assert target.selector == "[data-testid='item-list']"


def test_replay_request_rejects_blank_evidence_target_text() -> None:
    with pytest.raises(ValidationError):
        ReplayRequest(
            url="http://127.0.0.1:5176/items",
            evidence_targets=[
                {
                    "kind": "dom_text_present",
                    "text": "   ",
                    "source_slot": "item_name",
                    "selector": "[data-testid='item-list']",
                }
            ],
        )


def test_execution_evidence_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        ExecutionEvidence(
            kind="dom_text_present",
            target="测试项目B-001",
            status="verified",
            confidence=1.1,
            summary="invalid",
        )


def test_capture_execution_evidence_finds_text_inside_selector() -> None:
    target = ExecutionEvidenceTarget(
        kind="dom_text_present",
        text="测试项目B-001",
        source_slot="item_name",
        selector="[data-testid='item-list']",
    )
    page = _make_text_page(
        {"[data-testid='item-list']": "测试项目A\n测试项目B-001"}
    )

    evidence = capture_execution_evidence(page, [target])

    assert evidence[0].kind == "dom_text_present"
    assert evidence[0].target == "测试项目B-001"
    assert evidence[0].status == "verified"
    assert evidence[0].confidence == 0.95


def test_capture_execution_evidence_missing_text_inside_selector() -> None:
    target = ExecutionEvidenceTarget(
        kind="dom_text_present",
        text="测试项目B-001",
        source_slot="item_name",
        selector="[data-testid='item-list']",
    )
    page = _make_text_page({"[data-testid='item-list']": "测试项目A"})

    evidence = capture_execution_evidence(page, [target])

    assert evidence[0].kind == "dom_text_present"
    assert evidence[0].target == "测试项目B-001"
    assert evidence[0].status == "missing"
    assert evidence[0].confidence == 0.7


def test_capture_execution_evidence_unknown_when_page_unavailable() -> None:
    target = ExecutionEvidenceTarget(
        kind="dom_text_present",
        text="测试项目B-001",
        source_slot="item_name",
        selector="[data-testid='item-list']",
    )

    evidence = capture_execution_evidence(None, [target])

    assert evidence[0].kind == "unknown"
    assert evidence[0].target == "测试项目B-001"
    assert evidence[0].status == "unknown"
    assert evidence[0].confidence == 0.0


def test_capture_execution_evidence_does_not_verify_blank_target_text() -> None:
    target = ExecutionEvidenceTarget.model_construct(
        kind="dom_text_present",
        text="",
        source_slot="item_name",
        selector="body",
    )
    page = _make_text_page({"body": "any page text"})

    evidence = capture_execution_evidence(page, [target])

    assert evidence[0].kind == "unknown"
    assert evidence[0].target == ""
    assert evidence[0].status == "unknown"
    assert evidence[0].confidence == 0.0


def test_build_replay_actions_reads_value_slot() -> None:
    raw = [
        {
            "step": 1,
            "action_type": "fill",
            "target_selector": "#name",
            "value": "测试项目A",
            "value_slot": "item_name",
        }
    ]

    actions = _build_replay_actions(raw)

    assert actions[0].value_slot == "item_name"


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


# ── run_replay ───────────────────────────────────────────────────────────────


def test_run_replay_runtime_error_on_navigate() -> None:
    path = _make_learned_path(actions=[])

    mock_runtime = MagicMock()
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock(side_effect=Exception("connection refused"))
    mock_runtime.stop = MagicMock()

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        result = run_replay(path, "http://127.0.0.1:5175/users")

    assert result.status == "runtime_error"
    assert "connection refused" in result.drift_reasons[0]
    mock_runtime.stop.assert_called_once()


def test_run_replay_success_with_structured_result() -> None:
    path = _make_learned_path(
        dom_fingerprint=dom_fingerprint(_make_page_analysis()),
        actions=[
            {
                "step": 0,
                "action_type": "fill",
                "target_selector": "#q",
                "value": "hello",
            }
        ],
    )

    mock_locator = MagicMock()
    mock_locator.count.return_value = 1
    mock_locator.first.fill = MagicMock()
    mock_locator.first.input_value.return_value = "hello"
    mock_locator.first.wait_for = MagicMock()

    mock_page = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_page.url = "http://127.0.0.1:5175/users"
    mock_page.title.return_value = "Users"
    mock_page.is_closed.return_value = False

    mock_runtime = MagicMock()
    mock_runtime.page = mock_page
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock()
    mock_runtime.stop = MagicMock()
    mock_runtime.current_url.return_value = "http://127.0.0.1:5175/users"
    mock_runtime.current_title.return_value = "Users"
    mock_runtime.screenshot.return_value = "/tmp/screenshot.png"

    mock_analysis = _make_page_analysis()

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        with patch(
            "app.services.learning.learned_path_replay.analyze_page",
            return_value=mock_analysis,
        ):
            result = run_replay(path, "http://127.0.0.1:5175/users")

    assert result.status == "succeeded"
    assert result.drift_status == "none"
    assert result.learned_path_id == path.id
    assert "page_template" in result.stored_signature
    assert "page_template" in result.current_signature
    assert len(result.steps) == 1
    assert result.steps[0].action_type == "fill"
    assert result.steps[0].ok is True
    assert result.final_url == "http://127.0.0.1:5175/users"
    assert result.final_title == "Users"
    mock_runtime.stop.assert_called_once()


def test_run_replay_applies_slot_override_to_execute_and_wait() -> None:
    path = _make_learned_path(
        dom_fingerprint=dom_fingerprint(_make_page_analysis(url="http://127.0.0.1:5176/items")),
        page_template="/items",
        actions=[
            {
                "step": 0,
                "action_type": "fill",
                "target_selector": "#name",
                "value": "测试项目A",
                "value_slot": "item_name",
            }
        ],
    )

    mock_locator = MagicMock()
    mock_locator.count.return_value = 1

    mock_page = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_page.is_closed.return_value = False

    mock_runtime = MagicMock()
    mock_runtime.page = mock_page
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock()
    mock_runtime.stop = MagicMock()
    mock_runtime.current_url.return_value = "http://127.0.0.1:5176/items"
    mock_runtime.current_title.return_value = "项目列表"

    executed_values: list[str | None] = []
    waited_values: list[str | None] = []

    def fake_execute(action, runtime):
        executed_values.append(action.value)
        return {
            "step_index": action.step,
            "action_type": action.action_type,
            "target_selector": action.target_selector,
            "value": action.value,
            "ok": True,
        }

    def fake_wait(*, page, action, step_log):
        waited_values.append(action.value)
        return WaitResult(status="skipped")

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        with patch(
            "app.services.learning.learned_path_replay.analyze_page",
            return_value=_make_page_analysis(url="http://127.0.0.1:5176/items"),
        ):
            with patch(
                "app.services.execution.action_executor.execute_action",
                side_effect=fake_execute,
            ):
                with patch(
                    "app.services.learning.learned_path_replay.wait_for_change_after_action",
                    side_effect=fake_wait,
                ):
                    result = run_replay(
                        path,
                        "http://127.0.0.1:5176/items",
                        slot_overrides={"item_name": "测试项目B"},
                    )

    assert result.status == "succeeded"
    assert executed_values == ["测试项目B"]
    assert waited_values == ["测试项目B"]
    step = result.steps[0]
    assert step.value_slot == "item_name"
    assert step.override_applied is True
    assert step.effective_value == "测试项目B"


def test_run_replay_captures_evidence_before_runtime_stop() -> None:
    path = _make_learned_path(
        dom_fingerprint=dom_fingerprint(
            _make_page_analysis(url="http://127.0.0.1:5176/items")
        ),
        page_template="/items",
        actions=[
            {
                "step": 0,
                "action_type": "fill",
                "target_selector": "#name",
                "value": "测试项目A",
            }
        ],
    )
    call_order: list[str] = []

    mock_locator = MagicMock()
    mock_locator.count.return_value = 1

    def inner_text(*, timeout: int) -> str:
        call_order.append("capture")
        assert timeout == 1000
        return "测试项目A\n测试项目B"

    mock_locator.inner_text.side_effect = inner_text

    mock_page = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_page.is_closed.return_value = False

    mock_runtime = MagicMock()
    mock_runtime.page = mock_page
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock()
    mock_runtime.stop.side_effect = lambda: call_order.append("stop")
    mock_runtime.current_url.return_value = "http://127.0.0.1:5176/items"
    mock_runtime.current_title.return_value = "项目列表"

    def fake_execute(action, runtime):
        return {
            "step_index": action.step,
            "action_type": action.action_type,
            "target_selector": action.target_selector,
            "ok": True,
        }

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        with patch(
            "app.services.learning.learned_path_replay.analyze_page",
            return_value=_make_page_analysis(url="http://127.0.0.1:5176/items"),
        ):
            with patch(
                "app.services.execution.action_executor.execute_action",
                side_effect=fake_execute,
            ):
                result = run_replay(
                    path,
                    "http://127.0.0.1:5176/items",
                    evidence_targets=[
                        ExecutionEvidenceTarget(
                            kind="dom_text_present",
                            text="测试项目B",
                            source_slot="item_name",
                            selector="[data-testid='item-list']",
                        )
                    ],
                )

    assert result.status == "succeeded"
    assert result.execution_evidence[0].target == "测试项目B"
    assert result.execution_evidence[0].status == "verified"
    assert call_order == ["capture", "stop"]


def test_run_replay_fails_without_required_slot_override() -> None:
    path = _make_learned_path(
        dom_fingerprint=dom_fingerprint(_make_page_analysis()),
        actions=[
            {
                "step": 0,
                "action_type": "fill",
                "target_selector": "#q",
                "value": "测试项目A",
                "value_slot": "item_name",
            }
        ],
    )

    mock_locator = MagicMock()
    mock_locator.count.return_value = 1

    mock_page = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_page.is_closed.return_value = False

    mock_runtime = MagicMock()
    mock_runtime.page = mock_page
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock()
    mock_runtime.stop = MagicMock()
    mock_runtime.current_url.return_value = "http://127.0.0.1:5175/users"
    mock_runtime.current_title.return_value = "Users"

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        with patch(
            "app.services.learning.learned_path_replay.analyze_page",
            return_value=_make_page_analysis(),
        ):
            with patch(
                "app.services.execution.action_executor.execute_action"
            ) as mock_execute:
                result = run_replay(path, "http://127.0.0.1:5175/users")

    assert result.status == "failed"
    assert "Missing slot override" in result.drift_reasons[0]
    assert result.steps == []
    mock_execute.assert_not_called()


def test_run_replay_leaves_unbound_action_value_unchanged() -> None:
    path = _make_learned_path(
        dom_fingerprint=dom_fingerprint(_make_page_analysis()),
        actions=[
            {
                "step": 0,
                "action_type": "fill",
                "target_selector": "#q",
                "value": "测试项目A",
            }
        ],
    )

    mock_locator = MagicMock()
    mock_locator.count.return_value = 1

    mock_page = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_page.is_closed.return_value = False

    mock_runtime = MagicMock()
    mock_runtime.page = mock_page
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock()
    mock_runtime.stop = MagicMock()
    mock_runtime.current_url.return_value = "http://127.0.0.1:5175/users"
    mock_runtime.current_title.return_value = "Users"

    executed_values: list[str | None] = []

    def fake_execute(action, runtime):
        executed_values.append(action.value)
        return {
            "step_index": action.step,
            "action_type": action.action_type,
            "target_selector": action.target_selector,
            "value": action.value,
            "ok": True,
        }

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        with patch(
            "app.services.learning.learned_path_replay.analyze_page",
            return_value=_make_page_analysis(),
        ):
            with patch(
                "app.services.execution.action_executor.execute_action",
                side_effect=fake_execute,
            ):
                result = run_replay(
                    path,
                    "http://127.0.0.1:5175/users",
                    slot_overrides={"item_name": "测试项目B"},
                )

    assert result.status == "succeeded"
    assert executed_values == ["测试项目A"]
    assert result.steps[0].override_applied is False
    assert result.steps[0].effective_value is None


def test_run_replay_observational_path() -> None:
    path = _make_learned_path(
        dom_fingerprint=dom_fingerprint(_make_page_analysis()),
        actions=[],
    )

    mock_page = MagicMock()
    mock_page.is_closed.return_value = False

    mock_runtime = MagicMock()
    mock_runtime.page = mock_page
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock()
    mock_runtime.stop = MagicMock()
    mock_runtime.current_url.return_value = "http://127.0.0.1:5175/users"
    mock_runtime.current_title.return_value = "Users"
    mock_runtime.screenshot.return_value = "/tmp/screenshot.png"

    mock_analysis = _make_page_analysis()

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        with patch(
            "app.services.learning.learned_path_replay.analyze_page",
            return_value=mock_analysis,
        ):
            result = run_replay(path, "http://127.0.0.1:5175/users")

    assert result.status == "observed"
    assert result.drift_status == "none"
    assert result.steps == []
    mock_runtime.stop.assert_called_once()


# ── Wait-for-change integration ─────────────────────────────────────────────


def test_replay_step_carries_wait_result_for_fill() -> None:
    """fill action produces a skipped wait_result in the replay step."""
    path = _make_learned_path(
        dom_fingerprint=dom_fingerprint(_make_page_analysis()),
        actions=[
            {
                "step": 0,
                "action_type": "fill",
                "target_selector": "#q",
                "value": "hello",
            }
        ],
    )

    mock_locator = MagicMock()
    mock_locator.count.return_value = 1
    mock_locator.first.fill = MagicMock()
    mock_locator.first.input_value.return_value = "hello"
    mock_locator.first.wait_for = MagicMock()

    mock_page = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_page.url = "http://127.0.0.1:5175/users"
    mock_page.title.return_value = "Users"
    mock_page.is_closed.return_value = False

    mock_runtime = MagicMock()
    mock_runtime.page = mock_page
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock()
    mock_runtime.stop = MagicMock()
    mock_runtime.current_url.return_value = "http://127.0.0.1:5175/users"
    mock_runtime.current_title.return_value = "Users"
    mock_runtime.screenshot.return_value = "/tmp/screenshot.png"

    mock_analysis = _make_page_analysis()

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        with patch(
            "app.services.learning.learned_path_replay.analyze_page",
            return_value=mock_analysis,
        ):
            result = run_replay(path, "http://127.0.0.1:5175/users")

    assert result.status == "succeeded"
    assert len(result.steps) == 1
    step = result.steps[0]
    assert step.wait_result is not None
    assert step.wait_result.status == "skipped"


def test_replay_click_action_triggers_wait_for_change() -> None:
    """click action triggers wait-for-change and produces a WaitResult."""
    path = _make_learned_path(
        dom_fingerprint=dom_fingerprint(_make_page_analysis()),
        actions=[
            {
                "step": 0,
                "action_type": "click",
                "target_selector": "#btn",
            }
        ],
    )

    mock_locator = MagicMock()
    mock_locator.count.return_value = 1
    mock_locator.first.click = MagicMock()
    mock_locator.first.wait_for = MagicMock()

    mock_page = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_page.url = "http://127.0.0.1:5175/users"
    mock_page.title.return_value = "Users"
    mock_page.is_closed.return_value = False

    mock_runtime = MagicMock()
    mock_runtime.page = mock_page
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock()
    mock_runtime.stop = MagicMock()
    mock_runtime.current_url.return_value = "http://127.0.0.1:5175/users"
    mock_runtime.current_title.return_value = "Users"
    mock_runtime.screenshot.return_value = "/tmp/screenshot.png"

    mock_analysis = _make_page_analysis()

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        with patch(
            "app.services.learning.learned_path_replay.analyze_page",
            return_value=mock_analysis,
        ):
            result = run_replay(path, "http://127.0.0.1:5175/users")

    assert result.status == "succeeded"
    assert len(result.steps) == 1
    step = result.steps[0]
    assert step.wait_result is not None
    # click with no URL/title change -> timeout
    assert step.wait_result.status in ("observed", "timeout")
    assert step.wait_result.wait_strategy == "short_stability_wait"


def test_replay_observe_action_does_not_force_business_wait() -> None:
    """observe action returns not_required wait_result, no forced wait."""
    path = _make_learned_path(
        dom_fingerprint=dom_fingerprint(_make_page_analysis()),
        actions=[
            {
                "step": 0,
                "action_type": "observe",
                "target_selector": "#info",
            }
        ],
    )

    mock_locator = MagicMock()
    mock_locator.count.return_value = 1
    mock_locator.first.wait_for = MagicMock()
    mock_locator.first.text_content.return_value = "some text"

    mock_page = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_page.url = "http://127.0.0.1:5175/users"
    mock_page.title.return_value = "Users"
    mock_page.is_closed.return_value = False

    mock_runtime = MagicMock()
    mock_runtime.page = mock_page
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock()
    mock_runtime.stop = MagicMock()
    mock_runtime.current_url.return_value = "http://127.0.0.1:5175/users"
    mock_runtime.current_title.return_value = "Users"
    mock_runtime.screenshot.return_value = "/tmp/screenshot.png"

    mock_analysis = _make_page_analysis()

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        with patch(
            "app.services.learning.learned_path_replay.analyze_page",
            return_value=mock_analysis,
        ):
            result = run_replay(path, "http://127.0.0.1:5175/users")

    assert result.status == "succeeded"
    assert len(result.steps) == 1
    step = result.steps[0]
    assert step.wait_result is not None
    assert step.wait_result.status == "not_required"


def test_replay_action_failure_wait_result_does_not_misreport_succeeded() -> None:
    """Failed action gets skipped wait_result, replay status stays failed."""
    path = _make_learned_path(
        dom_fingerprint=dom_fingerprint(_make_page_analysis()),
        actions=[
            {
                "step": 0,
                "action_type": "click",
                "target_selector": "#missing",
            }
        ],
    )

    mock_locator = MagicMock()
    mock_locator.count.return_value = 1
    mock_locator.first.click = MagicMock(side_effect=Exception("element detached"))
    mock_locator.first.wait_for = MagicMock()

    mock_page = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_page.url = "http://127.0.0.1:5175/users"
    mock_page.title.return_value = "Users"
    mock_page.is_closed.return_value = False

    mock_runtime = MagicMock()
    mock_runtime.page = mock_page
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock()
    mock_runtime.stop = MagicMock()
    mock_runtime.current_url.return_value = "http://127.0.0.1:5175/users"
    mock_runtime.current_title.return_value = "Users"
    mock_runtime.screenshot.return_value = "/tmp/screenshot.png"

    mock_analysis = _make_page_analysis()

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        with patch(
            "app.services.learning.learned_path_replay.analyze_page",
            return_value=mock_analysis,
        ):
            result = run_replay(path, "http://127.0.0.1:5175/users")

    assert result.status == "failed"
    assert len(result.steps) == 1
    step = result.steps[0]
    assert step.ok is False
    assert step.wait_result is not None
    assert step.wait_result.status == "skipped"


def test_replay_wait_service_exception_does_not_change_replay_status() -> None:
    """If wait service raises internally, replay status is unaffected."""
    path = _make_learned_path(
        dom_fingerprint=dom_fingerprint(_make_page_analysis()),
        actions=[
            {
                "step": 0,
                "action_type": "fill",
                "target_selector": "#q",
                "value": "hello",
            }
        ],
    )

    mock_locator = MagicMock()
    mock_locator.count.return_value = 1
    mock_locator.first.fill = MagicMock()
    mock_locator.first.input_value.return_value = "hello"
    mock_locator.first.wait_for = MagicMock()

    mock_page = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_page.url = "http://127.0.0.1:5175/users"
    mock_page.title.return_value = "Users"
    mock_page.is_closed.return_value = False

    mock_runtime = MagicMock()
    mock_runtime.page = mock_page
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock()
    mock_runtime.stop = MagicMock()
    mock_runtime.current_url.return_value = "http://127.0.0.1:5175/users"
    mock_runtime.current_title.return_value = "Users"
    mock_runtime.screenshot.return_value = "/tmp/screenshot.png"

    mock_analysis = _make_page_analysis()

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        with patch(
            "app.services.learning.learned_path_replay.analyze_page",
            return_value=mock_analysis,
        ):
            with patch(
                "app.services.learning.learned_path_replay.wait_for_change_after_action",
                side_effect=RuntimeError("wait service crash"),
            ):
                result = run_replay(path, "http://127.0.0.1:5175/users")

    # The action succeeded; wait service exception produces conservative result.
    assert result.status == "succeeded"
    assert result.learned_path_id == path.id
    assert len(result.steps) == 1
    assert result.steps[0].ok is True
    assert result.steps[0].wait_result is not None
    assert result.steps[0].wait_result.status == "skipped"
    assert "wait failed" in result.steps[0].wait_result.notes.lower()


# ── Observation summary integration ─────────────────────────────────────────


def test_replay_success_returns_observation_summary() -> None:
    """Successful replay carries an observation_summary."""
    path = _make_learned_path(
        dom_fingerprint=dom_fingerprint(_make_page_analysis()),
        actions=[
            {
                "step": 0,
                "action_type": "click",
                "target_selector": "#btn",
            }
        ],
    )

    mock_locator = MagicMock()
    mock_locator.count.return_value = 1
    mock_locator.first.click = MagicMock()
    mock_locator.first.wait_for = MagicMock()

    mock_page = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_page.url = "http://127.0.0.1:5175/users"
    mock_page.title.return_value = "Users"
    mock_page.is_closed.return_value = False

    mock_runtime = MagicMock()
    mock_runtime.page = mock_page
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock()
    mock_runtime.stop = MagicMock()
    mock_runtime.current_url.return_value = "http://127.0.0.1:5175/users"
    mock_runtime.current_title.return_value = "Users"
    mock_runtime.screenshot.return_value = "/tmp/screenshot.png"

    mock_analysis = _make_page_analysis()

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        with patch(
            "app.services.learning.learned_path_replay.analyze_page",
            return_value=mock_analysis,
        ):
            result = run_replay(path, "http://127.0.0.1:5175/users")

    assert result.status == "succeeded"
    assert result.observation_summary is not None
    assert result.observation_summary.step_count == 1
    assert result.observation_summary.learned_path_id == path.id


def test_replay_status_unchanged_by_observation_summary() -> None:
    """Observation summary does not alter ReplayResult.status."""
    path = _make_learned_path(
        dom_fingerprint=dom_fingerprint(_make_page_analysis()),
        actions=[
            {
                "step": 0,
                "action_type": "click",
                "target_selector": "#btn",
            }
        ],
    )

    mock_locator = MagicMock()
    mock_locator.count.return_value = 1
    mock_locator.first.click = MagicMock(side_effect=Exception("element detached"))
    mock_locator.first.wait_for = MagicMock()

    mock_page = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_page.url = "http://127.0.0.1:5175/users"
    mock_page.title.return_value = "Users"
    mock_page.is_closed.return_value = False

    mock_runtime = MagicMock()
    mock_runtime.page = mock_page
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock()
    mock_runtime.stop = MagicMock()
    mock_runtime.current_url.return_value = "http://127.0.0.1:5175/users"
    mock_runtime.current_title.return_value = "Users"
    mock_runtime.screenshot.return_value = "/tmp/screenshot.png"

    mock_analysis = _make_page_analysis()

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        with patch(
            "app.services.learning.learned_path_replay.analyze_page",
            return_value=mock_analysis,
        ):
            result = run_replay(path, "http://127.0.0.1:5175/users")

    assert result.status == "failed"
    assert result.observation_summary is not None
    # summary is diagnostic, replay status is "failed" regardless
    assert result.observation_summary.step_count == 1


def test_replay_blocked_returns_no_observation_summary() -> None:
    """Blocked/drifted precheck returns observation_summary=None."""
    path = _make_learned_path(
        page_template="/users",
        actions=[
            {"step": 0, "action_type": "fill", "target_selector": "#q"}
        ],
    )

    mock_locator = MagicMock()
    mock_locator.count.return_value = 0

    mock_page = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_page.is_closed.return_value = False

    mock_runtime = MagicMock()
    mock_runtime.page = mock_page
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock()
    mock_runtime.stop = MagicMock()
    mock_runtime.current_url.return_value = "http://127.0.0.1:5175/orders"
    mock_runtime.current_title.return_value = "Orders"
    mock_runtime.screenshot.return_value = "/tmp/screenshot.png"

    mock_analysis = _make_page_analysis(url="http://127.0.0.1:5175/orders")

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        with patch(
            "app.services.learning.learned_path_replay.analyze_page",
            return_value=mock_analysis,
        ):
            result = run_replay(path, "http://127.0.0.1:5175/orders")

    assert result.status == "drifted"
    assert result.observation_summary is None


def test_replay_observational_path_returns_not_applicable_summary() -> None:
    """actions=[] observational path returns status=not_applicable summary."""
    path = _make_learned_path(
        dom_fingerprint=dom_fingerprint(_make_page_analysis()),
        actions=[],
    )

    mock_page = MagicMock()
    mock_page.is_closed.return_value = False

    mock_runtime = MagicMock()
    mock_runtime.page = mock_page
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock()
    mock_runtime.stop = MagicMock()
    mock_runtime.current_url.return_value = "http://127.0.0.1:5175/users"
    mock_runtime.current_title.return_value = "Users"
    mock_runtime.screenshot.return_value = "/tmp/screenshot.png"

    mock_analysis = _make_page_analysis()

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        with patch(
            "app.services.learning.learned_path_replay.analyze_page",
            return_value=mock_analysis,
        ):
            result = run_replay(path, "http://127.0.0.1:5175/users")

    assert result.status == "observed"
    assert result.observation_summary is not None
    assert result.observation_summary.status == "not_applicable"
    assert result.observation_summary.step_count == 0


def test_replay_wait_exception_produces_skipped_in_summary() -> None:
    """Wait service exception produces skipped wait_result in summary."""
    path = _make_learned_path(
        dom_fingerprint=dom_fingerprint(_make_page_analysis()),
        actions=[
            {
                "step": 0,
                "action_type": "fill",
                "target_selector": "#q",
                "value": "hello",
            }
        ],
    )

    mock_locator = MagicMock()
    mock_locator.count.return_value = 1
    mock_locator.first.fill = MagicMock()
    mock_locator.first.input_value.return_value = "hello"
    mock_locator.first.wait_for = MagicMock()

    mock_page = MagicMock()
    mock_page.locator.return_value = mock_locator
    mock_page.url = "http://127.0.0.1:5175/users"
    mock_page.title.return_value = "Users"
    mock_page.is_closed.return_value = False

    mock_runtime = MagicMock()
    mock_runtime.page = mock_page
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock()
    mock_runtime.stop = MagicMock()
    mock_runtime.current_url.return_value = "http://127.0.0.1:5175/users"
    mock_runtime.current_title.return_value = "Users"
    mock_runtime.screenshot.return_value = "/tmp/screenshot.png"

    mock_analysis = _make_page_analysis()

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        with patch(
            "app.services.learning.learned_path_replay.analyze_page",
            return_value=mock_analysis,
        ):
            with patch(
                "app.services.learning.learned_path_replay.wait_for_change_after_action",
                side_effect=RuntimeError("wait service crash"),
            ):
                result = run_replay(path, "http://127.0.0.1:5175/users")

    assert result.status == "succeeded"
    assert result.observation_summary is not None
    assert result.observation_summary.skipped_step_count == 1
    assert result.observation_summary.wait_result_count == 1


def test_replay_runtime_error_returns_no_observation_summary() -> None:
    """Runtime error returns observation_summary=None."""
    path = _make_learned_path(actions=[])

    mock_runtime = MagicMock()
    mock_runtime.start = MagicMock()
    mock_runtime.navigate = MagicMock(side_effect=Exception("connection refused"))
    mock_runtime.stop = MagicMock()

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        return_value=mock_runtime,
    ):
        result = run_replay(path, "http://127.0.0.1:5175/users")

    assert result.status == "runtime_error"
    assert result.observation_summary is None


# ── 11.3.1 visible browser operation ─────────────────────────────────────────


def test_run_replay_passes_headless_to_runtime_factory() -> None:
    """run_replay passes headless flag to create_execution_runtime via RuntimeConfig."""
    path = _make_learned_path(actions=[])

    mock_runtime = MagicMock()
    mock_runtime.page = None
    mock_runtime.start = MagicMock()
    mock_runtime.stop = MagicMock()

    captured_configs: list[Any] = []

    def _capture_create_execution_runtime(config=None):
        captured_configs.append(config)
        return mock_runtime

    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        side_effect=_capture_create_execution_runtime,
    ):
        run_replay(path, "http://127.0.0.1:5175/users")

    assert len(captured_configs) == 1
    assert captured_configs[0].headless is True

    captured_configs.clear()
    with patch(
        "app.services.learning.learned_path_replay.create_execution_runtime",
        side_effect=_capture_create_execution_runtime,
    ):
        run_replay(path, "http://127.0.0.1:5175/users", headless=False)

    assert len(captured_configs) == 1
    assert captured_configs[0].headless is False
