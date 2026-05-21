"""Tests for M11.1.7 Task Result Reporter."""

from __future__ import annotations

import inspect

import pytest

from app.schemas.conversation import ConversationReplaySummary
from app.services.task_planning.result_reporter import TaskResultReporter


@pytest.fixture
def reporter() -> TaskResultReporter:
    return TaskResultReporter()


# ── Outcome derivation ────────────────────────────────────────────────────────


def test_blocked_execution_returns_blocked(reporter: TaskResultReporter) -> None:
    report = reporter.build_report(
        execution_status="blocked",
        execution_payload={"reason": "missing_context", "missing_fields": ["url"]},
        replay_summary=None,
        confirmed_plan_context=None,
    )
    assert report.outcome == "blocked"
    assert report.needs_review is False
    assert report.event_type == "task_result_reported"


def test_replay_failed_returns_failed(reporter: TaskResultReporter) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="failed",
        drift_status="none",
        error="element not found",
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={},
        replay_summary=summary,
        confirmed_plan_context={"learned_path_id": "lp-001"},
    )
    assert report.outcome == "failed"
    assert report.needs_review is False


def test_replay_drifted_returns_failed(reporter: TaskResultReporter) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="succeeded",
        drift_status="page_mismatch",
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={},
        replay_summary=summary,
        confirmed_plan_context={"learned_path_id": "lp-001"},
    )
    assert report.outcome == "failed"
    assert report.needs_review is False


def test_replay_error_returns_failed(reporter: TaskResultReporter) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="succeeded",
        drift_status="none",
        error="timeout",
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={},
        replay_summary=summary,
        confirmed_plan_context={"learned_path_id": "lp-001"},
    )
    assert report.outcome == "failed"
    assert report.needs_review is False


def test_replay_succeeded_no_postcondition_returns_uncertain(
    reporter: TaskResultReporter,
) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="succeeded",
        drift_status="none",
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={},
        replay_summary=summary,
        confirmed_plan_context={"learned_path_id": "lp-001"},
    )
    assert report.outcome == "uncertain"
    assert report.needs_review is True


def test_verified_when_structured_dom_text_evidence_matches_item_name(
    reporter: TaskResultReporter,
) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://localhost:5176/items",
        replay_status="succeeded",
        drift_status="none",
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={
            "slot_overrides": {"item_name": "测试项目B-001"},
            "execution_evidence": [
                {
                    "kind": "dom_text_present",
                    "target": "测试项目B-001",
                    "status": "verified",
                    "confidence": 0.95,
                    "summary": "列表中出现了名称为“测试项目B-001”的项目行。",
                }
            ],
        },
        replay_summary=summary,
        confirmed_plan_context={
            "learned_path_id": "lp-001",
            "slot_overrides": {"item_name": "测试项目B-001"},
            "postcondition_evidence": [
                {
                    "kind": "dom_text_present",
                    "target": "测试项目B-001",
                    "status": "verified",
                    "confidence": 0.95,
                    "summary": "列表中出现了名称为“测试项目B-001”的项目行。",
                }
            ],
        },
    )

    assert report.outcome == "verified"
    assert report.needs_review is False
    assert report.event_payload["task_verified"] is True
    assert report.event_payload["execution_evidence"][0]["target"] == "测试项目B-001"


def test_not_verified_when_dom_text_evidence_missing(
    reporter: TaskResultReporter,
) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://localhost:5176/items",
        replay_status="succeeded",
        drift_status="none",
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={
            "slot_overrides": {"item_name": "测试项目B-001"},
            "execution_evidence": [
                {
                    "kind": "dom_text_present",
                    "target": "测试项目B-001",
                    "status": "missing",
                    "confidence": 0.7,
                    "summary": "操作执行后，列表中没有确认看到“测试项目B-001”。",
                }
            ],
        },
        replay_summary=summary,
        confirmed_plan_context={
            "learned_path_id": "lp-001",
            "slot_overrides": {"item_name": "测试项目B-001"},
        },
    )

    assert report.outcome == "needs_review"
    assert report.needs_review is True
    assert report.event_payload["task_verified"] is False


def test_not_verified_when_evidence_target_mismatches_item_name(
    reporter: TaskResultReporter,
) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://localhost:5176/items",
        replay_status="succeeded",
        drift_status="none",
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={
            "slot_overrides": {"item_name": "测试项目B-001"},
            "execution_evidence": [
                {
                    "kind": "dom_text_present",
                    "target": "测试项目A",
                    "status": "verified",
                    "confidence": 0.95,
                    "summary": "列表中出现了名称为“测试项目A”的项目行。",
                }
            ],
        },
        replay_summary=summary,
        confirmed_plan_context={"learned_path_id": "lp-001"},
    )

    assert report.outcome == "uncertain"
    assert report.event_payload["task_verified"] is False


def test_replay_observed_no_postcondition_returns_uncertain(
    reporter: TaskResultReporter,
) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="observed",
        drift_status="none",
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={},
        replay_summary=summary,
        confirmed_plan_context={"learned_path_id": "lp-001"},
    )
    assert report.outcome == "uncertain"
    assert report.needs_review is True


def test_completed_no_replay_summary_returns_uncertain(
    reporter: TaskResultReporter,
) -> None:
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={},
        replay_summary=None,
        confirmed_plan_context=None,
    )
    assert report.outcome == "uncertain"
    assert report.needs_review is True


def test_execution_failed_from_error_returns_failed(
    reporter: TaskResultReporter,
) -> None:
    report = reporter.build_report(
        execution_status="failed",
        execution_payload={"error_summary": "browser crashed"},
        replay_summary=None,
        confirmed_plan_context=None,
    )
    assert report.outcome == "failed"
    assert report.needs_review is False


# ── Event payload boundaries ──────────────────────────────────────────────────


def test_event_payload_contains_markers(reporter: TaskResultReporter) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="succeeded",
        drift_status="none",
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={},
        replay_summary=summary,
        confirmed_plan_context={"learned_path_id": "lp-001"},
    )
    payload = report.event_payload
    assert payload["no_recovery"] is True
    assert payload["no_autonomous"] is True
    assert payload["no_llm"] is True
    assert payload["task_verified"] is False
    assert payload["needs_review"] is True
    assert payload["verification_outcome"] == "uncertain"


def test_event_payload_has_evidence_fields(reporter: TaskResultReporter) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="failed",
        drift_status="none",
        error="element not found",
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={},
        replay_summary=summary,
        confirmed_plan_context={"learned_path_id": "lp-001"},
    )
    payload = report.event_payload
    assert "evidence_summary" in payload
    assert "missing_evidence_summary" in payload
    assert payload["learned_path_id"] == "lp-001"


def test_event_payload_falls_back_to_execution_payload_for_path_id(
    reporter: TaskResultReporter,
) -> None:
    report = reporter.build_report(
        execution_status="blocked",
        execution_payload={"learned_path_id": "lp-002"},
        replay_summary=None,
        confirmed_plan_context=None,
    )
    assert report.event_payload["learned_path_id"] == "lp-002"


# ── User response semantics ───────────────────────────────────────────────────


def test_uncertain_response_does_not_claim_success(reporter: TaskResultReporter) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="succeeded",
        drift_status="none",
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={},
        replay_summary=summary,
        confirmed_plan_context={"learned_path_id": "lp-001"},
    )
    assert report.outcome == "uncertain"
    response = report.user_response.lower()
    assert "could not verify" in response
    assert "succeeded" not in response
    assert "success" not in response


def test_failed_response_does_not_claim_recovery(reporter: TaskResultReporter) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="failed",
        drift_status="none",
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={},
        replay_summary=summary,
        confirmed_plan_context={"learned_path_id": "lp-001"},
    )
    response = report.user_response.lower()
    assert "failed" in response
    assert "no recovery was attempted" in response


def test_blocked_response_is_safe(reporter: TaskResultReporter) -> None:
    report = reporter.build_report(
        execution_status="blocked",
        execution_payload={},
        replay_summary=None,
        confirmed_plan_context=None,
    )
    response = report.user_response.lower()
    assert "could not run" in response or "blocked" in response
    assert "success" not in response


# ── Evidence summary construction ─────────────────────────────────────────────


def test_evidence_summary_for_successful_replay(reporter: TaskResultReporter) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="succeeded",
        drift_status="none",
        final_url="http://example.com/done",
        final_title="Done",
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={},
        replay_summary=summary,
        confirmed_plan_context=None,
    )
    assert "succeeded" in report.evidence_summary
    assert "none" in report.evidence_summary
    assert "http://example.com/done" in report.evidence_summary
    assert "Done" in report.evidence_summary


def test_evidence_summary_for_blocked(reporter: TaskResultReporter) -> None:
    report = reporter.build_report(
        execution_status="blocked",
        execution_payload={"reason": "missing_target_url"},
        replay_summary=None,
        confirmed_plan_context=None,
    )
    assert "blocked" in report.evidence_summary
    assert "missing_target_url" in report.evidence_summary


def test_missing_evidence_summary_for_uncertain(reporter: TaskResultReporter) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="succeeded",
        drift_status="none",
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={},
        replay_summary=summary,
        confirmed_plan_context=None,
    )
    assert "no explicit postcondition evidence" in report.missing_evidence_summary


def test_missing_evidence_summary_for_failed_replay(reporter: TaskResultReporter) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="failed",
        drift_status="none",
        error="element not found",
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={},
        replay_summary=summary,
        confirmed_plan_context=None,
    )
    assert "Replay did not complete successfully" in report.missing_evidence_summary


def test_missing_evidence_summary_for_drift(reporter: TaskResultReporter) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="succeeded",
        drift_status="page_mismatch",
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={},
        replay_summary=summary,
        confirmed_plan_context=None,
    )
    assert "Page drift detected" in report.missing_evidence_summary


# ── Structured payload fields (follow-up fix) ─────────────────────────────────


def test_completed_replay_with_final_url_but_missing_title_remains_uncertain(
    reporter: TaskResultReporter,
) -> None:
    """Final URL alone must not shift outcome from uncertain to verified."""
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="succeeded",
        drift_status="none",
        final_url="http://example.com/done",
        final_title=None,
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={},
        replay_summary=summary,
        confirmed_plan_context=None,
    )
    assert report.outcome == "uncertain"
    assert report.needs_review is True
    assert report.event_payload["task_verified"] is False

    # Structured fields preserved
    assert report.event_payload["execution_status"] == "completed"
    assert report.event_payload["replay_status"] == "succeeded"
    assert report.event_payload["drift_status"] == "none"
    assert report.event_payload["final_url"] == "http://example.com/done"
    assert report.event_payload["final_title"] is None
    assert report.event_payload["error_summary"] is None

    # Evidence summary must not say replay was unavailable
    assert "Replay summary was not available" not in report.evidence_summary
    assert "Final URL: http://example.com/done" in report.evidence_summary

    # Missing evidence must point to postcondition gap, not replay gap
    assert "no explicit postcondition evidence" in report.missing_evidence_summary


def test_structured_payload_fields_populated_from_replay_summary(
    reporter: TaskResultReporter,
) -> None:
    summary = ConversationReplaySummary(
        learned_path_id="lp-001",
        url="http://example.com",
        replay_status="failed",
        drift_status="target_missing",
        error="element not found",
        final_url="http://example.com/error",
        final_title="Error",
    )
    report = reporter.build_report(
        execution_status="completed",
        execution_payload={},
        replay_summary=summary,
        confirmed_plan_context=None,
    )
    payload = report.event_payload
    assert payload["execution_status"] == "completed"
    assert payload["replay_status"] == "failed"
    assert payload["drift_status"] == "target_missing"
    assert payload["error_summary"] == "element not found"
    assert payload["final_url"] == "http://example.com/error"
    assert payload["final_title"] == "Error"


def test_structured_payload_fields_null_when_no_replay_summary(
    reporter: TaskResultReporter,
) -> None:
    report = reporter.build_report(
        execution_status="blocked",
        execution_payload={"reason": "missing_context"},
        replay_summary=None,
        confirmed_plan_context=None,
    )
    payload = report.event_payload
    assert payload["execution_status"] == "blocked"
    assert payload["replay_status"] is None
    assert payload["drift_status"] is None
    assert payload["final_url"] is None
    assert payload["final_title"] is None
    assert payload["error_summary"] is None


def test_error_summary_falls_back_to_execution_payload(
    reporter: TaskResultReporter,
) -> None:
    report = reporter.build_report(
        execution_status="failed",
        execution_payload={"error_summary": "browser crashed"},
        replay_summary=None,
        confirmed_plan_context=None,
    )
    assert report.event_payload["error_summary"] == "browser crashed"
    assert report.event_payload["execution_status"] == "failed"


# ── Forbidden imports ─────────────────────────────────────────────────────────


def test_reporter_module_does_not_import_replay_autonomous_or_llm() -> None:
    from app.services.task_planning import result_reporter as reporter_module

    source = inspect.getsource(reporter_module)
    forbidden_tokens = [
        "learned_path_replay",
        "run_replay",
        "autonomous_explorer",
        "/exploration/autonomous-runs",
        "llm_provider",
        "OpenAI",
        "apps.cli",
        "page_understanding",
    ]
    for token in forbidden_tokens:
        assert token not in source
