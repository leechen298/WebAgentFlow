from __future__ import annotations

from app.services.learning.terminal_state import classify_terminal_state


def _timeline(*events: dict, status: str = "recording_available") -> dict:
    return {
        "status": status,
        "events": list(events),
    }


def _event(event_type: str, event_id: str = "event-1", *, scoped: bool = True) -> dict:
    event = {
        "event_id": event_id,
        "event_type": event_type,
        "metadata": {},
    }
    if scoped:
        event.update(
            {
                "action_id": "action-step-1",
                "step_index": 1,
                "action_type": "click",
            }
        )
    return event


def _hints(*terminal_types: str) -> dict:
    return {
        "source": "deterministic",
        "candidate_terminal_states": [
            {
                "terminal_type": terminal_type,
                "function_id": f"function-{index + 1}",
            }
            for index, terminal_type in enumerate(terminal_types)
        ],
    }


def test_download_event_with_hint_stops_strong() -> None:
    verdict = classify_terminal_state(
        browser_event_timeline=_timeline(_event("download")),
        page_terminal_hints=_hints("download_started"),
    )

    assert verdict.terminal_outcome == "terminal_detected"
    assert verdict.terminal_type == "download_started"
    assert verdict.evidence_strength == "strong"
    assert verdict.stop_decision == "stop"
    assert verdict.matched_event_ids == ["event-1"]
    assert verdict.matched_action_ids == ["action-step-1"]
    assert verdict.matched_step_indices == [1]
    assert verdict.matched_action_types == ["click"]
    assert verdict.matched_hint_ids == ["function-1"]
    assert verdict.matched_evidence == ["download_event"]
    assert verdict.needs_more_wait is False


def test_request_without_response_waits_until_bounded_timeout() -> None:
    verdict = classify_terminal_state(
        browser_event_timeline=_timeline(_event("request")),
        page_terminal_hints=_hints("network_completion"),
    )

    assert verdict.terminal_outcome == "not_terminal_yet"
    assert verdict.terminal_type == "network_completion"
    assert verdict.evidence_strength == "weak"
    assert verdict.stop_decision == "wait"
    assert verdict.needs_more_wait is True
    assert verdict.max_wait_reached is False
    assert verdict.matched_event_ids == ["event-1"]
    assert verdict.matched_action_ids == ["action-step-1"]
    assert verdict.matched_evidence == ["request_event"]
    assert verdict.missing_evidence == ["response_or_failure_event"]


def test_request_without_response_unverified_stop_at_max_wait() -> None:
    verdict = classify_terminal_state(
        browser_event_timeline=_timeline(_event("request")),
        page_terminal_hints=_hints("network_completion"),
        max_wait_reached=True,
    )

    assert verdict.terminal_outcome == "terminal_unverified"
    assert verdict.terminal_type == "network_completion"
    assert verdict.evidence_strength == "weak"
    assert verdict.stop_decision == "unverified_stop"
    assert verdict.needs_more_wait is False
    assert verdict.max_wait_reached is True


def test_requestfailed_is_terminal_failed_unverified_stop() -> None:
    verdict = classify_terminal_state(
        browser_event_timeline=_timeline(_event("requestfailed")),
        page_terminal_hints=_hints("network_completion"),
    )

    assert verdict.terminal_outcome == "terminal_failed"
    assert verdict.terminal_type == "terminal_failed"
    assert verdict.evidence_strength == "medium"
    assert verdict.stop_decision == "unverified_stop"
    assert verdict.matched_event_ids == ["event-1"]
    assert verdict.matched_evidence == ["browser_error_event"]


def test_response_with_list_hint_detects_list_refresh() -> None:
    verdict = classify_terminal_state(
        browser_event_timeline=_timeline(
            _event("request", "event-1"),
            _event("response", "event-2"),
        ),
        page_terminal_hints=_hints("list_refresh"),
    )

    assert verdict.terminal_outcome == "terminal_detected"
    assert verdict.terminal_type == "list_refresh"
    assert verdict.evidence_strength == "strong"
    assert verdict.stop_decision == "stop"
    assert verdict.matched_event_ids == ["event-1", "event-2"]
    assert verdict.matched_action_ids == ["action-step-1"]
    assert verdict.matched_hint_ids == ["function-1"]


def test_unscoped_response_does_not_stop_or_detect_terminal() -> None:
    verdict = classify_terminal_state(
        browser_event_timeline=_timeline(
            _event("request", "event-1", scoped=False),
            _event("response", "event-2", scoped=False),
        ),
        page_terminal_hints=_hints("list_refresh"),
    )

    assert verdict.terminal_outcome == "terminal_unverified"
    assert verdict.terminal_type == "no_observable_change"
    assert verdict.evidence_strength == "weak"
    assert verdict.stop_decision == "unverified_stop"
    assert verdict.warnings == ["terminal_events_without_action_scope"]
    assert verdict.missing_evidence == ["action_scoped_browser_event"]


def test_missing_evidence_continues_without_success_fields() -> None:
    verdict = classify_terminal_state(
        browser_event_timeline=_timeline(),
        page_terminal_hints={"candidate_terminal_states": []},
    )

    payload = verdict.model_dump(mode="json")
    assert payload["terminal_outcome"] == "terminal_unverified"
    assert payload["terminal_type"] == "no_observable_change"
    assert payload["evidence_strength"] == "none"
    assert payload["stop_decision"] == "continue"
    assert "success" not in payload
    assert "should_save_path" not in payload
    assert "pass_gate" not in payload


def test_recorder_unavailable_returns_unverified_stop() -> None:
    verdict = classify_terminal_state(
        browser_event_timeline=_timeline(status="recording_unavailable"),
        page_terminal_hints=_hints("list_refresh"),
    )

    assert verdict.terminal_outcome == "terminal_unverified"
    assert verdict.terminal_type == "no_observable_change"
    assert verdict.evidence_strength == "none"
    assert verdict.stop_decision == "unverified_stop"
    assert verdict.warnings == ["browser_event_recorder_unavailable"]
    assert verdict.missing_evidence == ["browser_event_timeline"]
    assert verdict.source == "deterministic"


def test_hint_only_returns_unverified_stop_not_false_success() -> None:
    verdict = classify_terminal_state(
        browser_event_timeline=_timeline(),
        page_terminal_hints=_hints("list_refresh", "network_completion"),
    )

    assert verdict.terminal_outcome == "terminal_unverified"
    assert verdict.terminal_type == "no_observable_change"
    assert verdict.evidence_strength == "weak"
    assert verdict.stop_decision == "unverified_stop"
    assert verdict.matched_hint_ids == ["function-1", "function-2"]
    assert verdict.missing_evidence == ["browser_event_or_final_state_change"]
