"""Deterministic advisory terminal-state classifier."""

from __future__ import annotations

from typing import Any

from app.schemas.terminal_state import TerminalStateVerdict

_LIFECYCLE_EVENTS = ("framenavigated", "load", "domcontentloaded")


def _events(timeline: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(timeline, dict):
        return []
    raw_events = timeline.get("events")
    if not isinstance(raw_events, list):
        return []
    return [event for event in raw_events if isinstance(event, dict)]


def _event_types(events: list[dict[str, Any]]) -> set[str]:
    return {str(event.get("event_type")) for event in events if event.get("event_type")}


def _event_ids(events: list[dict[str, Any]], *event_types: str) -> list[str]:
    wanted = set(event_types)
    return [
        str(event.get("event_id"))
        for event in events
        if event.get("event_type") in wanted and event.get("event_id")
    ]


def _action_scoped_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        event
        for event in events
        if event.get("action_id")
        or event.get("step_index") is not None
        or event.get("action_type")
    ]


def _action_ids(events: list[dict[str, Any]], *event_types: str) -> list[str]:
    wanted = set(event_types)
    return sorted(
        {
            str(event.get("action_id"))
            for event in events
            if event.get("event_type") in wanted and event.get("action_id")
        }
    )


def _step_indices(events: list[dict[str, Any]], *event_types: str) -> list[int]:
    wanted = set(event_types)
    values: set[int] = set()
    for event in events:
        if event.get("event_type") not in wanted:
            continue
        step_index = event.get("step_index")
        if isinstance(step_index, int):
            values.add(step_index)
    return sorted(values)


def _action_types(events: list[dict[str, Any]], *event_types: str) -> list[str]:
    wanted = set(event_types)
    return sorted(
        {
            str(event.get("action_type"))
            for event in events
            if event.get("event_type") in wanted and event.get("action_type")
        }
    )


def _hint_types(page_terminal_hints: dict[str, Any] | None) -> set[str]:
    if not isinstance(page_terminal_hints, dict):
        return set()
    raw_hints = page_terminal_hints.get("candidate_terminal_states")
    if not isinstance(raw_hints, list):
        return set()
    return {
        str(item.get("terminal_type"))
        for item in raw_hints
        if isinstance(item, dict) and item.get("terminal_type")
    }


def _hint_ids(page_terminal_hints: dict[str, Any] | None, *terminal_types: str) -> list[str]:
    if not isinstance(page_terminal_hints, dict):
        return []
    raw_hints = page_terminal_hints.get("candidate_terminal_states")
    if not isinstance(raw_hints, list):
        return []
    wanted = set(terminal_types)
    ids: list[str] = []
    for index, item in enumerate(raw_hints):
        if isinstance(item, dict) and item.get("terminal_type") in wanted:
            ids.append(str(item.get("function_id") or f"hint-{index + 1}"))
    return ids


def classify_terminal_state(
    *,
    browser_event_timeline: dict[str, Any] | None,
    page_terminal_hints: dict[str, Any] | None,
    final_state: dict[str, Any] | None = None,
    max_wait_reached: bool = False,
) -> TerminalStateVerdict:
    """Classify whether an attempt reached an evaluable terminal state.

    This is advisory metadata. It does not save LearnedPaths, mutate pass gates,
    or control browser execution.
    """
    raw_events = _events(browser_event_timeline)
    scoped_events = _action_scoped_events(raw_events)
    raw_event_types = _event_types(raw_events)
    event_types = _event_types(scoped_events)
    hint_types = _hint_types(page_terminal_hints)
    final_state = final_state or {}
    timeline_status = (
        browser_event_timeline.get("status")
        if isinstance(browser_event_timeline, dict)
        else None
    )

    if timeline_status == "recording_unavailable":
        return TerminalStateVerdict(
            terminal_outcome="terminal_unverified",
            terminal_type="no_observable_change",
            evidence_strength="none",
            evidence_summary="Browser event recorder was unavailable.",
            stop_decision="unverified_stop",
            warnings=["browser_event_recorder_unavailable"],
            missing_evidence=["browser_event_timeline"],
            max_wait_reached=max_wait_reached,
        )

    if "pageerror" in raw_event_types or "requestfailed" in raw_event_types:
        error_strength = (
            "strong" if {"pageerror", "requestfailed"} <= raw_event_types else "medium"
        )
        return TerminalStateVerdict(
            terminal_outcome="terminal_failed",
            terminal_type="terminal_failed",
            evidence_strength=error_strength,
            evidence_summary="Browser error evidence was recorded.",
            stop_decision="unverified_stop",
            matched_event_ids=_event_ids(raw_events, "pageerror", "requestfailed"),
            matched_evidence=["browser_error_event"],
            max_wait_reached=max_wait_reached,
        )

    if "download" in event_types:
        return TerminalStateVerdict(
            terminal_outcome="terminal_detected",
            terminal_type="download_started",
            evidence_strength="strong",
            evidence_summary="Browser download event was recorded.",
            stop_decision="stop",
            matched_event_ids=_event_ids(scoped_events, "download"),
            matched_action_ids=_action_ids(scoped_events, "download"),
            matched_step_indices=_step_indices(scoped_events, "download"),
            matched_action_types=_action_types(scoped_events, "download"),
            matched_hint_ids=_hint_ids(page_terminal_hints, "download_started"),
            matched_evidence=["download_event"],
            max_wait_reached=max_wait_reached,
        )

    if "dialog" in event_types:
        return TerminalStateVerdict(
            terminal_outcome="terminal_detected",
            terminal_type="browser_dialog",
            evidence_strength="strong",
            evidence_summary="Browser dialog event was recorded.",
            stop_decision="stop",
            matched_event_ids=_event_ids(scoped_events, "dialog"),
            matched_action_ids=_action_ids(scoped_events, "dialog"),
            matched_step_indices=_step_indices(scoped_events, "dialog"),
            matched_action_types=_action_types(scoped_events, "dialog"),
            matched_hint_ids=_hint_ids(page_terminal_hints, "modal_or_popup_opened"),
            matched_evidence=["dialog_event"],
            max_wait_reached=max_wait_reached,
        )

    if "popup" in event_types:
        return TerminalStateVerdict(
            terminal_outcome="terminal_detected",
            terminal_type="modal_or_popup_opened",
            evidence_strength="strong",
            evidence_summary="Popup or child page event was recorded.",
            stop_decision="stop",
            matched_event_ids=_event_ids(scoped_events, "popup"),
            matched_action_ids=_action_ids(scoped_events, "popup"),
            matched_step_indices=_step_indices(scoped_events, "popup"),
            matched_action_types=_action_types(scoped_events, "popup"),
            matched_hint_ids=_hint_ids(page_terminal_hints, "modal_or_popup_opened"),
            matched_evidence=["popup_event"],
            max_wait_reached=max_wait_reached,
        )

    if set(_LIFECYCLE_EVENTS) & event_types:
        strength = "strong" if "navigation" in hint_types else "medium"
        return TerminalStateVerdict(
            terminal_outcome="terminal_detected",
            terminal_type="navigation",
            evidence_strength=strength,
            evidence_summary="Navigation or page lifecycle event was recorded.",
            stop_decision="stop",
            matched_event_ids=_event_ids(scoped_events, *_LIFECYCLE_EVENTS),
            matched_action_ids=_action_ids(scoped_events, *_LIFECYCLE_EVENTS),
            matched_step_indices=_step_indices(scoped_events, *_LIFECYCLE_EVENTS),
            matched_action_types=_action_types(scoped_events, *_LIFECYCLE_EVENTS),
            matched_hint_ids=_hint_ids(page_terminal_hints, "navigation"),
            matched_evidence=["navigation_or_lifecycle_event"],
            max_wait_reached=max_wait_reached,
        )

    if "request" in event_types and "response" not in event_types:
        return TerminalStateVerdict(
            terminal_outcome="terminal_unverified" if max_wait_reached else "not_terminal_yet",
            terminal_type="network_completion",
            evidence_strength="weak",
            evidence_summary="Request was observed but no completion evidence was recorded.",
            stop_decision="unverified_stop" if max_wait_reached else "wait",
            warnings=["network_completion_missing"],
            matched_event_ids=_event_ids(scoped_events, "request"),
            matched_action_ids=_action_ids(scoped_events, "request"),
            matched_step_indices=_step_indices(scoped_events, "request"),
            matched_action_types=_action_types(scoped_events, "request"),
            matched_evidence=["request_event"],
            missing_evidence=["response_or_failure_event"],
            needs_more_wait=not max_wait_reached,
            max_wait_reached=max_wait_reached,
        )

    if "response" in event_types:
        terminal_type = "list_refresh" if "list_refresh" in hint_types else "network_completion"
        strength = "strong" if terminal_type in hint_types else "medium"
        return TerminalStateVerdict(
            terminal_outcome="terminal_detected",
            terminal_type=terminal_type,
            evidence_strength=strength,
            evidence_summary="Network activity matched page terminal hints.",
            stop_decision="stop",
            matched_event_ids=_event_ids(scoped_events, "request", "response"),
            matched_action_ids=_action_ids(scoped_events, "request", "response"),
            matched_step_indices=_step_indices(scoped_events, "request", "response"),
            matched_action_types=_action_types(scoped_events, "request", "response"),
            matched_hint_ids=_hint_ids(page_terminal_hints, terminal_type),
            matched_evidence=["response_event"],
            max_wait_reached=max_wait_reached,
        )

    if raw_events:
        return TerminalStateVerdict(
            terminal_outcome="terminal_unverified",
            terminal_type="no_observable_change",
            evidence_strength="weak",
            evidence_summary=(
                "Browser events were recorded, but none were correlated to an action."
            ),
            stop_decision="unverified_stop",
            warnings=["terminal_events_without_action_scope"],
            matched_event_ids=_event_ids(
                raw_events,
                "request",
                "response",
                "download",
                "dialog",
                "popup",
                "framenavigated",
                "load",
                "domcontentloaded",
            ),
            missing_evidence=["action_scoped_browser_event"],
            max_wait_reached=max_wait_reached,
        )

    alert_texts = final_state.get("alert_texts")
    if isinstance(alert_texts, list) and alert_texts:
        return TerminalStateVerdict(
            terminal_outcome="terminal_detected",
            terminal_type="toast_or_status_message",
            evidence_strength="medium",
            evidence_summary="Visible alert/status text was captured in final state.",
            stop_decision="stop",
            matched_hint_ids=_hint_ids(page_terminal_hints, "toast_or_status_message"),
            matched_evidence=["final_state_alert_text"],
            max_wait_reached=max_wait_reached,
        )

    if hint_types:
        return TerminalStateVerdict(
            terminal_outcome="terminal_unverified",
            terminal_type="no_observable_change",
            evidence_strength="weak",
            evidence_summary=(
                "Page hints exist, but no matching browser or final-state evidence "
                "was recorded."
            ),
            stop_decision="unverified_stop",
            warnings=["terminal_hints_without_matching_evidence"],
            matched_hint_ids=_hint_ids(page_terminal_hints, *hint_types),
            missing_evidence=["browser_event_or_final_state_change"],
            max_wait_reached=max_wait_reached,
        )

    return TerminalStateVerdict(
        terminal_outcome="terminal_unverified",
        terminal_type="no_observable_change",
        evidence_strength="none",
        evidence_summary="No terminal-state evidence was recorded.",
        stop_decision="continue",
        warnings=["no_terminal_evidence"],
        missing_evidence=["browser_event_timeline", "page_terminal_hints", "final_state_signal"],
        max_wait_reached=max_wait_reached,
    )
