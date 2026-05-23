#!/usr/bin/env python3
"""WAgent runtime eval runner for M11.3.6.x."""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import httpx


SCHEMA_VERSION = "11.3.6.4"
FAILURE_RECOVERY_CASE = "failure_recovery_menu_safety"
PENDING_CHOICE_CASE = "pending_choice_multi_candidate"
PLANNER_CHOICE_CASE = "planner_backed_choice"
PLANNER_SINGLE_PATH_REGRESSION_CASE = "planner_single_path_bypass_regression"
DEFAULT_CASES = [
    "items_closed_loop",
    "single_path_direct_replay_regression",
]
ALL_CASES = [
    *DEFAULT_CASES,
    FAILURE_RECOVERY_CASE,
    PENDING_CHOICE_CASE,
    PLANNER_CHOICE_CASE,
]
ITEM_LIST_SELECTOR = "[data-testid='item-list']"
SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "cookie",
    "credential",
    "credential",
    "credentials",
    "css_selector",
    "evidence_targets",
    "execution_payload",
    "learned_path_id",
    "pending_choice_private_map",
    "planner_summary",
    "password",
    "private_retry_payload",
    "raw_selector",
    "replay_action",
    "replayaction",
    "response_text",
    "secret",
    "selector",
    "slot_overrides",
    "target_selector",
    "token",
    "xpath",
}
RECOVERY_FAILURE_CLASSES = {
    "needs_review",
    "evidence_missing",
    "uncertain",
    "blocked",
    "replay_failed",
}
RECOVERY_SIDE_EFFECT_CLASSES = {"needs_review", "evidence_missing", "uncertain"}
FORBIDDEN_PAYLOAD_TERMS = {
    "learned_path_id",
    "slot_overrides",
    "evidence_targets",
    "ReplayAction",
    "replay_action",
    "execution_payload",
    "pending_choice_private_map",
    "planner_summary",
    "private_retry_payload",
    "credential",
    "password",
    "secret",
    "token",
    "cookie",
    "authorization",
    "api_key",
    "target_selector",
    "raw_selector",
    "css_selector",
    "xpath",
}
PROHIBITED_AUTONOMOUS_PATH_FRAGMENT = "autonomous" + "-runs"
PROHIBITED_DIRECT_REPLAY_SUFFIX = "/" + "replay"


@dataclass
class EvalConfig:
    api_base: str
    product_url: str
    cases: list[str]
    timeout: int
    artifact_dir: Path
    result_dir: Path
    browser_visibility: str
    write_markdown: bool = True


@dataclass
class PreflightResult:
    status: str
    exit_code: int
    services: dict[str, Any]


@dataclass
class GateResult:
    name: str
    required: bool
    status: str
    evidence: str
    source: str


@dataclass
class TurnRecord:
    text: str
    started_at: str
    duration_ms: int
    response: dict[str, Any] | None
    error: str | None = None


@dataclass
class CaseResult:
    case_id: str
    status: str
    turns: list[TurnRecord] = field(default_factory=list)
    gates: list[GateResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    schema_version: str
    status: str
    environment: dict[str, Any]
    services: dict[str, Any]
    config: dict[str, Any]
    session_id: str | None
    case_results: list[CaseResult]
    turns: list[TurnRecord]
    events: list[dict[str, Any]]
    messages: list[dict[str, Any]]
    history: dict[str, Any]
    learned_paths: list[dict[str, Any]]
    raw_api_responses: dict[str, Any]
    gate_summary: dict[str, Any]


class EvalBlockedError(RuntimeError):
    pass


class EvalTimeoutError(RuntimeError):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run WAgent runtime eval cases through the Conversation API.",
    )
    parser.add_argument("--api-base", default="http://127.0.0.1:8001")
    parser.add_argument("--product-url", default="http://127.0.0.1:5176/items")
    parser.add_argument(
        "--case",
        action="append",
        dest="cases",
        help="Case id to run. Repeat or pass comma-separated values.",
    )
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("artifacts/wagent-eval"),
    )
    parser.add_argument(
        "--result-dir",
        type=Path,
        default=Path("docs/testing/results"),
    )
    parser.add_argument(
        "--browser-visibility",
        choices=["headless", "visible"],
        default="headless",
    )
    parser.add_argument("--no-markdown", action="store_true")
    parser.add_argument("--json-only", action="store_true")
    return parser


def parse_config(argv: list[str] | None = None) -> EvalConfig:
    args = build_parser().parse_args(argv)
    cases = _normalize_cases(args.cases)
    return EvalConfig(
        api_base=args.api_base.rstrip("/"),
        product_url=args.product_url,
        cases=cases,
        timeout=args.timeout,
        artifact_dir=args.artifact_dir,
        result_dir=args.result_dir,
        browser_visibility=args.browser_visibility,
        write_markdown=not (args.no_markdown or args.json_only),
    )


def _normalize_cases(raw_cases: list[str] | None) -> list[str]:
    if not raw_cases:
        return list(DEFAULT_CASES)
    cases: list[str] = []
    for raw in raw_cases:
        cases.extend(item.strip() for item in raw.split(",") if item.strip())
    unknown = [case for case in cases if case not in ALL_CASES]
    if unknown:
        raise SystemExit(f"unknown eval case(s): {', '.join(unknown)}")
    return cases


def _default_http_get(url: str, timeout: float) -> dict[str, Any]:
    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    return {"status_code": response.status_code, "ok": response.status_code < 400}


def run_preflight(
    config: EvalConfig,
    *,
    http_get: Callable[[str, float], dict[str, Any]] | None = None,
) -> PreflightResult:
    get = http_get or _default_http_get
    services: dict[str, Any] = {}
    api_url = f"{config.api_base}/health"
    services["api"] = _check_service(api_url, config.timeout, get)
    if not services["api"]["ok"]:
        return PreflightResult(status="blocked", exit_code=2, services=services)
    services["product"] = _check_service(config.product_url, config.timeout, get)
    if not services["product"]["ok"]:
        return PreflightResult(status="blocked", exit_code=2, services=services)
    return PreflightResult(status="pass", exit_code=0, services=services)


def _check_service(
    url: str,
    timeout: float,
    http_get: Callable[[str, float], dict[str, Any]],
) -> dict[str, Any]:
    try:
        result = http_get(url, min(float(timeout), 30.0))
    except Exception as exc:  # noqa: BLE001 - surfaced as blocked preflight
        return {"url": url, "ok": False, "error": str(exc)}
    status_code = result.get("status_code")
    ok = bool(result.get("ok")) and (status_code is None or int(status_code) < 400)
    payload = {"url": url, "ok": ok, "status_code": status_code}
    if not ok:
        payload["error"] = result.get("error") or f"HTTP {status_code}"
    return payload


class ConversationDriver:
    def __init__(self, config: EvalConfig) -> None:
        self.config = config
        timeout = httpx.Timeout(float(config.timeout))
        self.client = httpx.Client(
            base_url=config.api_base,
            timeout=timeout,
            follow_redirects=True,
        )
        self.raw_records: list[dict[str, Any]] = []

    def close(self) -> None:
        self.client.close()

    def create_session(
        self,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session_metadata = {
            "client": "wagent_eval",
            "browser_visibility": self.config.browser_visibility,
            "eval_runner": {
                "name": "wagent_runtime_eval",
                "schema_version": SCHEMA_VERSION,
            },
        }
        if metadata:
            session_metadata.update(metadata)
        payload = {
            "current_mode": "interactive_chat",
            "metadata": session_metadata,
        }
        return self._request("POST", "/conversation/sessions", json_body=payload)

    def send_turn(
        self,
        session_id: str,
        text: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> TurnRecord:
        started = utc_now()
        start = time.perf_counter()
        try:
            response = self._request(
                "POST",
                f"/conversation/sessions/{session_id}/dispatch",
                json_body={
                    "input": text,
                    "metadata": {
                        "client": "wagent_eval",
                        "browser_visibility": self.config.browser_visibility,
                        **(metadata or {}),
                    },
                },
            )
        except httpx.TimeoutException as exc:
            raise EvalTimeoutError(str(exc)) from exc
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return TurnRecord(
                text=text,
                started_at=started,
                duration_ms=duration_ms,
                response=None,
                error=str(exc),
            )
        duration_ms = int((time.perf_counter() - start) * 1000)
        return TurnRecord(
            text=text,
            started_at=started,
            duration_ms=duration_ms,
            response=response,
        )

    def get_session(self, session_id: str) -> dict[str, Any]:
        return self._request("GET", f"/conversation/sessions/{session_id}")

    def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        return self._request(
            "GET",
            f"/conversation/sessions/{session_id}/messages",
            params={"limit": 1000},
        )

    def get_events(self, session_id: str) -> list[dict[str, Any]]:
        return self._request(
            "GET",
            f"/conversation/sessions/{session_id}/events",
            params={"limit": 1000},
        )

    def get_history(self, session_id: str) -> dict[str, Any]:
        return self._request("GET", f"/conversation/sessions/{session_id}/history")

    def get_learned_path_detail(self, learned_path_id: str) -> dict[str, Any] | None:
        try:
            return self._request("GET", f"/exploration/learned-paths/{learned_path_id}")
        except EvalBlockedError:
            return None

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        start = time.perf_counter()
        record: dict[str, Any] = {
            "method": method,
            "path": path,
            "json": json_body,
            "params": params,
        }
        try:
            response = self.client.request(method, path, json=json_body, params=params)
            record["status_code"] = response.status_code
            record["duration_ms"] = int((time.perf_counter() - start) * 1000)
            record["response_text"] = response.text[:2000]
            response.raise_for_status()
            payload = response.json()
            record["response_json"] = payload
        except httpx.TimeoutException as exc:
            record["duration_ms"] = int((time.perf_counter() - start) * 1000)
            record["error"] = "timeout"
            self.raw_records.append(record)
            raise EvalTimeoutError(str(exc)) from exc
        except Exception as exc:
            record["duration_ms"] = int((time.perf_counter() - start) * 1000)
            record["error"] = str(exc)
            self.raw_records.append(record)
            raise EvalBlockedError(str(exc)) from exc
        self.raw_records.append(record)
        if isinstance(payload, dict) and "data" in payload:
            if payload.get("code") not in (0, None):
                raise EvalBlockedError(f"API envelope error: {payload.get('msg')}")
            return payload.get("data")
        return payload


class EvidenceCollector:
    def __init__(self, driver: ConversationDriver) -> None:
        self.driver = driver

    def collect(
        self,
        session_id: str,
        learned_path_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        session = self.driver.get_session(session_id)
        messages = self.driver.get_messages(session_id)
        events = self.driver.get_events(session_id)
        history = self.driver.get_history(session_id)
        ids = list(dict.fromkeys((learned_path_ids or []) + _learned_path_ids(events)))
        learned_paths = [
            detail
            for learned_path_id in ids
            if (detail := self.driver.get_learned_path_detail(learned_path_id))
        ]
        learned_path_detail = learned_paths[-1] if learned_paths else None
        return {
            "session": session,
            "messages": messages,
            "events": events,
            "history": history,
            "learned_paths": learned_paths,
            "learned_path_detail": learned_path_detail,
        }


class GateEvaluator:
    def evaluate_items_closed_loop(
        self,
        evidence: dict[str, Any],
        *,
        expected_item_name: str,
    ) -> CaseResult:
        learned_path_id = _latest_learned_path_id(evidence)
        execution_event = _latest_execution_started_for_item(
            evidence,
            expected_item_name,
        )
        completed_event = _latest_event_after(
            evidence,
            "chat_execution_completed",
            execution_event,
        )
        reporter_event = _latest_event_after(
            evidence,
            "task_result_reported",
            execution_event,
        )
        gates = [
            _gate_session_created(evidence),
            _gate_pending_target_or_equivalent(evidence, learned_path_id),
            _gate_learned_path_created(learned_path_id),
            _gate_learned_path_parameterized(evidence),
            _gate_execution_started(execution_event),
            _gate_slot_override("slot_override_B", execution_event, expected_item_name),
            _gate_effective_value("effective_value_B", evidence, expected_item_name),
            _gate_evidence_target_item_list(evidence, execution_event),
            _gate_dom_evidence(
                "dom_evidence_verified_B",
                completed_event,
                expected_item_name,
            ),
            _gate_reporter_verified(reporter_event),
            _gate_final_response_verified(evidence, expected_item_name),
        ]
        return CaseResult(
            case_id="items_closed_loop",
            status=_case_status(gates),
            gates=gates,
            warnings=_warnings(gates),
        )

    def evaluate_single_path_direct_replay_regression(
        self,
        evidence: dict[str, Any],
        *,
        expected_item_name: str,
        learned_path_id: str,
    ) -> CaseResult:
        execution_event = _latest_execution_started_for_item(
            evidence,
            expected_item_name,
        )
        completed_event = _latest_event_after(
            evidence,
            "chat_execution_completed",
            execution_event,
        )
        reporter_event = _latest_event_after(
            evidence,
            "task_result_reported",
            execution_event,
        )
        gates = [
            _gate_single_candidate(evidence, learned_path_id),
            _gate_execution_uses_current_learned_path(
                execution_event,
                learned_path_id,
            ),
            _gate_no_pending_choice(evidence, execution_event),
            _gate_no_planner_choice(evidence, execution_event),
            _gate_slot_override("slot_override_C", execution_event, expected_item_name),
            _gate_dom_evidence(
                "dom_evidence_verified_C",
                completed_event,
                expected_item_name,
            ),
            _gate_reporter_verified(reporter_event),
            _gate_final_response_verified(evidence, expected_item_name),
        ]
        return CaseResult(
            case_id="single_path_direct_replay_regression",
            status=_case_status(gates),
            gates=gates,
            warnings=_warnings(gates),
        )

    def evaluate_failure_recovery_menu_safety(
        self,
        evidence: dict[str, Any],
    ) -> CaseResult:
        failure_class = _latest_recovery_failure_class(evidence)
        latest_message = _latest_agent_message(evidence)
        gates = [
            _gate_failure_triggered(failure_class),
            _gate_recovery_menu_shown(latest_message),
            _gate_retry_wording_safe(latest_message),
            _gate_retry_side_effect_warning(latest_message, failure_class),
            _gate_relearn_option_shown(latest_message),
            _gate_cancel_option_shown(latest_message),
            _gate_private_payload_not_visible(evidence),
            _gate_recovery_events_sanitized(evidence),
            _gate_verified_happy_path_no_recovery(evidence),
            _gate_no_autonomous_or_direct_replay(evidence),
        ]
        return CaseResult(
            case_id=FAILURE_RECOVERY_CASE,
            status=_case_status(gates),
            gates=gates,
            warnings=_warnings(gates),
        )

    def evaluate_pending_choice_multi_candidate(
        self,
        evidence: dict[str, Any],
        *,
        expected_item_name: str | None = None,
    ) -> CaseResult:
        execution_event = _latest_pending_choice_execution_started(evidence)
        completed_event = _latest_event_after(
            evidence,
            "chat_execution_completed",
            execution_event,
        )
        reporter_event = _latest_event_after(
            evidence,
            "task_result_reported",
            execution_event,
        )
        item_name = expected_item_name or _get(
            execution_event or {}, "payload", "slot_overrides", "item_name"
        )
        gates = [
            _gate_setup_multi_candidate_current_eval(evidence),
            _gate_pending_choice_created(evidence),
            _gate_public_choices_abc_visible(evidence),
            _gate_public_choice_payload_sanitized(evidence),
            _gate_pending_choice_planner_not_invoked(evidence),
            _gate_select_a_dispatched(evidence),
            _gate_choice_a_execution_started(execution_event),
            _gate_execution_uses_choice_a_path(evidence, execution_event),
            _gate_slot_override_after_choice(execution_event, item_name),
            _gate_pending_choice_cleared(evidence),
            _gate_private_map_not_public_after_selection(evidence),
            _gate_pending_choice_execution_verified(
                completed_event,
                reporter_event,
                item_name,
            ),
            _gate_final_response_verified(evidence, item_name or ""),
            _gate_no_autonomous_or_direct_replay(evidence),
        ]
        return CaseResult(
            case_id=PENDING_CHOICE_CASE,
            status=_case_status(gates),
            gates=gates,
            warnings=_warnings(gates),
        )

    def evaluate_planner_backed_choice(
        self,
        evidence: dict[str, Any],
        *,
        expected_item_name: str | None = None,
    ) -> CaseResult:
        selected_event = _latest_planner_choice_selected_event(evidence)
        execution_event = _latest_event_after(
            evidence,
            "chat_execution_started",
            selected_event,
        )
        completed_event = _latest_event_after(
            evidence,
            "chat_execution_completed",
            execution_event,
        )
        reporter_event = _latest_event_after(
            evidence,
            "task_result_reported",
            execution_event,
        )
        item_name = expected_item_name or _get(
            execution_event or {}, "payload", "slot_overrides", "item_name"
        )
        gates = [
            _gate_setup_planner_candidates_current_eval(evidence),
            _gate_planner_candidates_generated(evidence),
            _gate_planner_choice_created(evidence),
            _gate_non_planner_choice_not_used(evidence),
            _gate_public_choices_abc_visible(evidence),
            _gate_planner_public_payload_sanitized(evidence),
            _gate_planner_event_sanitized(evidence),
            _gate_planner_warning_wording_safe(evidence),
            _gate_planner_top_choice_observable(evidence),
            _gate_select_planner_choice_dispatched(evidence),
            _gate_planner_choice_selected(selected_event),
            _gate_planner_choice_execution_started(execution_event),
            _gate_execution_uses_selected_choice_path(evidence, execution_event),
            _gate_pending_choice_cleared(evidence),
            _gate_pending_choice_execution_verified(
                completed_event,
                reporter_event,
                item_name,
            ),
            _gate_final_response_verified(evidence, item_name or ""),
            _gate_no_autonomous_or_direct_replay(evidence),
        ]
        return CaseResult(
            case_id=PLANNER_CHOICE_CASE,
            status=_case_status(gates),
            gates=gates,
            warnings=_warnings(gates),
        )

    def evaluate_planner_single_path_bypass_regression(
        self,
        evidence: dict[str, Any],
        *,
        expected_item_name: str,
        learned_path_id: str,
    ) -> CaseResult:
        execution_event = _latest_execution_started_for_item(
            evidence,
            expected_item_name,
        )
        completed_event = _latest_event_after(
            evidence,
            "chat_execution_completed",
            execution_event,
        )
        reporter_event = _latest_event_after(
            evidence,
            "task_result_reported",
            execution_event,
        )
        gates = [
            _gate_single_candidate(evidence, learned_path_id),
            _gate_no_planner_candidates_generated(evidence),
            _gate_no_planner_choice_created(evidence),
            _gate_direct_execution_started(execution_event),
            _gate_execution_uses_current_learned_path(
                execution_event,
                learned_path_id,
            ),
            _gate_pending_choice_execution_verified(
                completed_event,
                reporter_event,
                expected_item_name,
            ),
            _gate_final_response_verified(evidence, expected_item_name),
        ]
        return CaseResult(
            case_id=PLANNER_SINGLE_PATH_REGRESSION_CASE,
            status=_case_status(gates),
            gates=gates,
            warnings=_warnings(gates),
        )


def _gate_session_created(evidence: dict[str, Any]) -> GateResult:
    session_id = _get(evidence, "session", "id")
    if session_id:
        return GateResult(
            "session_created", True, "pass", f"session_id={session_id}", "session"
        )
    return GateResult("session_created", True, "fail", "session id missing", "session")


def _gate_pending_target_or_equivalent(
    evidence: dict[str, Any],
    learned_path_id: str | None,
) -> GateResult:
    metadata = _get(evidence, "session", "metadata") or {}
    target = metadata.get("pending_target") or metadata.get("target_url")
    if target:
        return GateResult(
            "pending_target_or_equivalent",
            True,
            "pass",
            "target context exists in session metadata",
            "session",
        )
    if learned_path_id:
        return GateResult(
            "pending_target_or_equivalent",
            True,
            "pass",
            "downstream learning completed with target context",
            "events",
        )
    return GateResult(
        "pending_target_or_equivalent",
        True,
        "fail",
        "no pending target or equivalent learned-path evidence",
        "session/events",
    )


def _gate_learned_path_created(learned_path_id: str | None) -> GateResult:
    if learned_path_id:
        return GateResult(
            "learned_path_created",
            True,
            "pass",
            f"new_learned_path_id={learned_path_id}",
            "events",
        )
    return GateResult(
        "learned_path_created",
        True,
        "fail",
        "new learned path id missing",
        "events/history",
    )


def _gate_learned_path_parameterized(evidence: dict[str, Any]) -> GateResult:
    path = evidence.get("learned_path_detail") or _latest_learned_path_detail(evidence)
    actions = path.get("actions") if isinstance(path, dict) else None
    if any(
        isinstance(action, dict) and action.get("value_slot") == "item_name"
        for action in actions or []
    ):
        path_id = path.get("id") if isinstance(path, dict) else None
        return GateResult(
            "learned_path_parameterized",
            True,
            "pass",
            f"LearnedPath {path_id} has value_slot=item_name",
            "learned_path_detail",
        )
    return GateResult(
        "learned_path_parameterized",
        True,
        "fail",
        "fill action with value_slot=item_name missing",
        "learned_path_detail",
    )


def _gate_execution_started(event: dict[str, Any] | None) -> GateResult:
    if event:
        return GateResult(
            "execution_started",
            True,
            "pass",
            f"event_id={event.get('id')}",
            "events",
        )
    return GateResult(
        "execution_started",
        True,
        "fail",
        "chat_execution_started missing",
        "events",
    )


def _gate_slot_override(
    name: str,
    event: dict[str, Any] | None,
    expected_item_name: str,
) -> GateResult:
    actual = _get(event or {}, "payload", "slot_overrides", "item_name")
    if actual == expected_item_name:
        return GateResult(
            name,
            True,
            "pass",
            f"slot_overrides.item_name={actual}",
            "events",
        )
    return GateResult(
        name,
        True,
        "fail",
        f"expected slot_overrides.item_name={expected_item_name}, got {actual}",
        "events",
    )


def _gate_effective_value(
    name: str,
    evidence: dict[str, Any],
    expected_item_name: str,
) -> GateResult:
    values = _find_key_values(evidence, "effective_value")
    if not values:
        return GateResult(
            name,
            False,
            "not_observable",
            "effective_value not exposed in public history/events",
            "history/events",
        )
    if expected_item_name in values:
        return GateResult(
            name,
            True,
            "pass",
            f"effective_value={expected_item_name}",
            "history/events",
        )
    return GateResult(
        name,
        True,
        "fail",
        f"effective_value did not include {expected_item_name}",
        "history/events",
    )


def _gate_evidence_target_item_list(
    evidence: dict[str, Any],
    execution_event: dict[str, Any] | None,
) -> GateResult:
    targets = []
    if execution_event:
        _extend_evidence_targets(
            targets,
            _get(execution_event, "payload", "evidence_targets"),
        )
    for value in _find_key_values(evidence.get("history"), "evidence_targets"):
        _extend_evidence_targets(targets, value)
    for target in targets:
        if not isinstance(target, dict):
            continue
        if target.get("selector") == ITEM_LIST_SELECTOR:
            return GateResult(
                "evidence_target_item_list",
                True,
                "pass",
                f"selector={ITEM_LIST_SELECTOR}",
                "events/history",
            )
    return GateResult(
        "evidence_target_item_list",
        False,
        "not_observable",
        "evidence_targets selector not exposed; not inferred from execution_evidence",
        "events/history",
    )


def _extend_evidence_targets(targets: list[Any], value: Any) -> None:
    if isinstance(value, list):
        targets.extend(value)
    elif isinstance(value, dict):
        targets.append(value)


def _gate_dom_evidence(
    name: str,
    event: dict[str, Any] | None,
    expected_item_name: str,
) -> GateResult:
    evidence_items = _execution_evidence_items(event)
    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        if (
            item.get("kind") == "dom_text_present"
            and item.get("target") == expected_item_name
            and item.get("status") == "verified"
        ):
            return GateResult(
                name,
                True,
                "pass",
                f"dom_text_present verified target={expected_item_name}",
                "events/history",
            )
    return GateResult(
        name,
        True,
        "fail",
        f"verified dom_text_present evidence for {expected_item_name} missing",
        "events/history",
    )


def _gate_reporter_verified(event: dict[str, Any] | None) -> GateResult:
    outcome = _get(event or {}, "payload", "verification_outcome")
    if outcome == "verified":
        return GateResult(
            "reporter_verified",
            True,
            "pass",
            "verification_outcome=verified",
            "task_result_reported",
        )
    return GateResult(
        "reporter_verified",
        True,
        "fail",
        f"expected verification_outcome=verified, got {outcome}",
        "task_result_reported",
    )


def _gate_final_response_verified(
    evidence: dict[str, Any],
    expected_item_name: str,
) -> GateResult:
    message = _latest_agent_message(evidence)
    if expected_item_name in message and any(
        marker in message for marker in ("看到了", "确认", "成功", "verified")
    ):
        return GateResult(
            "final_response_verified",
            True,
            "pass",
            f"final response references {expected_item_name}",
            "message",
        )
    return GateResult(
        "final_response_verified",
        True,
        "fail",
        f"final response does not evidence success for {expected_item_name}",
        "message",
    )


def _gate_single_candidate(
    evidence: dict[str, Any],
    learned_path_id: str,
) -> GateResult:
    actions = _session_learned_actions(evidence)
    matches = [
        action
        for action in actions
        if isinstance(action, dict) and action.get("learned_path_id") == learned_path_id
    ]
    if len(matches) == 1:
        return GateResult(
            "single_candidate_detected",
            True,
            "pass",
            f"one current-session learned action matched {learned_path_id}",
            "history",
        )
    return GateResult(
        "single_candidate_detected",
        True,
        "fail",
        f"expected one current-session action for {learned_path_id}, got {len(matches)}",
        "history",
    )


def _gate_execution_uses_current_learned_path(
    event: dict[str, Any] | None,
    learned_path_id: str,
) -> GateResult:
    actual = _get(event or {}, "payload", "learned_path_id")
    if actual == learned_path_id:
        return GateResult(
            "execution_uses_current_learned_path",
            True,
            "pass",
            f"chat_execution_started.learned_path_id={actual}",
            "events",
        )
    return GateResult(
        "execution_uses_current_learned_path",
        True,
        "fail",
        f"expected chat_execution_started.learned_path_id={learned_path_id}, got {actual}",
        "events",
    )


def _gate_no_pending_choice(
    evidence: dict[str, Any],
    execution_event: dict[str, Any] | None,
) -> GateResult:
    events = _events_after(evidence, execution_event)
    for event in events:
        text = json.dumps(event, ensure_ascii=False)
        progress_kind = _get(event, "payload", "progress_kind")
        if "pending_choice" in str(progress_kind) or "pending_choice" in text:
            return GateResult(
                "no_pending_choice",
                True,
                "fail",
                f"pending choice signal observed at event {event.get('id')}",
                "events",
            )
    return GateResult(
        "no_pending_choice",
        True,
        "pass",
        "no pending choice signal after C execution",
        "events",
    )


def _gate_no_planner_choice(
    evidence: dict[str, Any],
    execution_event: dict[str, Any] | None,
) -> GateResult:
    events = _events_after(evidence, execution_event)
    for event in events:
        progress_kind = str(_get(event, "payload", "progress_kind") or "")
        if progress_kind.startswith("planner_") or "planner_choice" in progress_kind:
            return GateResult(
                "no_planner_choice",
                True,
                "fail",
                f"planner signal observed: {progress_kind}",
                "events",
            )
    return GateResult(
        "no_planner_choice",
        True,
        "pass",
        "no planner choice signal after C execution",
        "events",
    )


def _latest_recovery_failure_class(evidence: dict[str, Any]) -> str | None:
    for event in reversed(_events(evidence)):
        failure_class = _get(event, "payload", "failure_class")
        if failure_class in RECOVERY_FAILURE_CLASSES:
            return str(failure_class)
        outcome = _get(event, "payload", "verification_outcome")
        if outcome in RECOVERY_FAILURE_CLASSES:
            return str(outcome)
    return None


def _gate_failure_triggered(failure_class: str | None) -> GateResult:
    if failure_class in RECOVERY_FAILURE_CLASSES:
        return GateResult(
            "failure_triggered",
            True,
            "pass",
            f"failure_class={failure_class}",
            "events/history",
        )
    return GateResult(
        "failure_triggered",
        True,
        "fail",
        "no recovery failure class observed",
        "events/history",
    )


def _gate_recovery_menu_shown(message: str) -> GateResult:
    if _has_recovery_menu(message):
        return GateResult(
            "recovery_menu_shown",
            True,
            "pass",
            "visible reply contains A/B/C recovery menu",
            "message",
        )
    return GateResult(
        "recovery_menu_shown",
        True,
        "fail",
        "visible reply does not contain A/B/C recovery menu",
        "message",
    )


def _gate_retry_wording_safe(message: str) -> GateResult:
    if "A. 重试执行该操作" in message or "A、重试执行该操作" in message:
        return GateResult(
            "retry_wording_safe",
            True,
            "pass",
            "A option uses 重试执行该操作",
            "message",
        )
    return GateResult(
        "retry_wording_safe",
        True,
        "fail",
        "A option must say 重试执行该操作",
        "message",
    )


def _gate_retry_side_effect_warning(
    message: str,
    failure_class: str | None,
) -> GateResult:
    if failure_class not in RECOVERY_SIDE_EFFECT_CLASSES:
        return GateResult(
            "retry_side_effect_warning",
            False,
            "not_observable",
            f"not required for failure_class={failure_class}",
            "message",
        )
    if "重试会再次执行该操作" in message and (
        "可能重复" in message or "重复" in message
    ):
        return GateResult(
            "retry_side_effect_warning",
            True,
            "pass",
            "retry warning mentions repeated execution risk",
            "message",
        )
    return GateResult(
        "retry_side_effect_warning",
        True,
        "fail",
        "retry side-effect warning missing for conservative failure class",
        "message",
    )


def _gate_relearn_option_shown(message: str) -> GateResult:
    if "B. 重新学习" in message or "B、重新学习" in message:
        return GateResult(
            "relearn_option_shown",
            True,
            "pass",
            "B option offers 重新学习",
            "message",
        )
    return GateResult(
        "relearn_option_shown",
        True,
        "fail",
        "B option must offer 重新学习",
        "message",
    )


def _gate_cancel_option_shown(message: str) -> GateResult:
    if "C. 取消" in message or "C、取消" in message:
        return GateResult(
            "cancel_option_shown",
            True,
            "pass",
            "C option offers 取消",
            "message",
        )
    return GateResult(
        "cancel_option_shown",
        True,
        "fail",
        "C option must offer 取消",
        "message",
    )


def _gate_private_payload_not_visible(evidence: dict[str, Any]) -> GateResult:
    public_surface = {
        "messages": evidence.get("messages") or [],
        "session_metadata": _get(evidence, "session", "metadata") or {},
    }
    leak = _first_forbidden_term(public_surface)
    if leak is None:
        return GateResult(
            "private_payload_not_visible",
            True,
            "pass",
            "visible messages and session public payload are sanitized",
            "messages/session",
        )
    return GateResult(
        "private_payload_not_visible",
        True,
        "fail",
        f"private payload token observed: {leak}",
        "messages/session",
    )


def _gate_recovery_events_sanitized(evidence: dict[str, Any]) -> GateResult:
    recovery_events = [
        event for event in _events(evidence) if _is_recovery_safety_event(event)
    ]
    leak = _first_forbidden_term(recovery_events)
    if leak is None:
        return GateResult(
            "recovery_events_sanitized",
            True,
            "pass",
            f"{len(recovery_events)} recovery event(s) sanitized",
            "events/history",
        )
    return GateResult(
        "recovery_events_sanitized",
        True,
        "fail",
        f"private recovery token observed: {leak}",
        "events/history",
    )


def _is_recovery_safety_event(event: dict[str, Any]) -> bool:
    progress_kind = str(_get(event, "payload", "progress_kind") or "")
    return (
        progress_kind.startswith("failure_recovery")
        or progress_kind == "eval_fault_injection_applied"
    )


def _gate_verified_happy_path_no_recovery(evidence: dict[str, Any]) -> GateResult:
    messages = _agent_messages(evidence)
    prior_messages = messages[:-1]
    if not prior_messages:
        return GateResult(
            "verified_happy_path_no_recovery",
            True,
            "fail",
            "no prior happy-path message available",
            "messages",
        )
    for index, message in enumerate(prior_messages):
        if _has_recovery_menu(message):
            return GateResult(
                "verified_happy_path_no_recovery",
                True,
                "fail",
                f"prior agent message {index} contains recovery menu",
                "messages",
            )
    return GateResult(
        "verified_happy_path_no_recovery",
        True,
        "pass",
        "prior happy-path messages do not contain recovery menu",
        "messages",
    )


def _gate_no_autonomous_or_direct_replay(evidence: dict[str, Any]) -> GateResult:
    records = _get(evidence, "raw_api_responses", "records") or []
    for record in records if isinstance(records, list) else []:
        path = str(record.get("path") or "") if isinstance(record, dict) else ""
        if PROHIBITED_AUTONOMOUS_PATH_FRAGMENT in path or (
            "learned-paths/" in path
            and path.rstrip("/").endswith(PROHIBITED_DIRECT_REPLAY_SUFFIX)
        ):
            return GateResult(
                "no_autonomous_or_direct_replay",
                True,
                "fail",
                f"prohibited runner request path observed: {path}",
                "runner raw request log",
            )
    return GateResult(
        "no_autonomous_or_direct_replay",
        True,
        "pass",
        "runner request log contains no autonomous-run or direct replay endpoint",
        "runner raw request log",
    )


def _gate_setup_multi_candidate_current_eval(
    evidence: dict[str, Any],
) -> GateResult:
    manifest = evidence.get("setup_manifest")
    if not isinstance(manifest, dict):
        return GateResult(
            "setup_multi_candidate_current_eval",
            True,
            "fail",
            "setup manifest missing",
            "setup_manifest",
        )
    setup_type = str(manifest.get("setup_type") or "")
    candidates = [
        candidate
        for candidate in manifest.get("candidates") or []
        if isinstance(candidate, dict)
    ]
    aliases = [
        str(candidate.get("alias") or "")
        for candidate in candidates
        if candidate.get("alias")
    ]
    distinct_aliases = sorted(set(aliases))
    current_real_path_count = sum(
        1
        for candidate in candidates
        if candidate.get("is_current_eval_real_path")
        or candidate.get("current_eval_run")
        or candidate.get("source") == "current_eval_run"
    )
    live_capability = bool(manifest.get("live_multi_action_capability"))
    if (
        setup_type in _pending_choice_setup_types()
        and len(candidates) >= 3
        and len(distinct_aliases) >= 3
        and (setup_type == "fixture_only" or current_real_path_count >= 1)
    ):
        return GateResult(
            "setup_multi_candidate_current_eval",
            True,
            "pass",
            (
                f"setup_type={setup_type}; "
                f"live_multi_action_capability={str(live_capability).lower()}; "
                f"candidate_count={len(candidates)}; "
                f"current_eval_real_path_count={current_real_path_count}; "
                f"aliases={','.join(distinct_aliases)}"
            ),
            "setup_manifest",
        )
    return GateResult(
        "setup_multi_candidate_current_eval",
        True,
        "fail",
        (
            f"setup_type={setup_type or 'missing'}; candidate_count={len(candidates)}; "
            f"distinct_alias_count={len(distinct_aliases)}; "
            f"current_eval_real_path_count={current_real_path_count}"
        ),
        "setup_manifest",
    )


def _pending_choice_setup_types() -> set[str]:
    return {
        "live_same_session_distinct_paths",
        "live_setup_session_distinct_paths",
        "eval_only_candidate_binding",
        "fixture_only",
    }


def _gate_pending_choice_created(evidence: dict[str, Any]) -> GateResult:
    event = _latest_pending_choice_created_event(evidence)
    if event:
        return GateResult(
            "pending_choice_created",
            True,
            "pass",
            f"event_id={event.get('id')}",
            "events/history",
        )
    return GateResult(
        "pending_choice_created",
        True,
        "fail",
        "non-planner pending_choice_created event missing",
        "events/history",
    )


def _gate_public_choices_abc_visible(evidence: dict[str, Any]) -> GateResult:
    choice_ids = set(_pending_choice_public_choice_ids(evidence))
    messages_text = "\n".join(_agent_messages(evidence))
    has_visible_markers = all(marker in messages_text for marker in ("A.", "B.", "C."))
    if {"A", "B", "C"}.issubset(choice_ids) or has_visible_markers:
        return GateResult(
            "public_choices_abc_visible",
            True,
            "pass",
            f"public choice ids={','.join(sorted(choice_ids)) or 'message_markers'}",
            "message/events",
        )
    return GateResult(
        "public_choices_abc_visible",
        True,
        "fail",
        f"expected public choices A/B/C, got {','.join(sorted(choice_ids)) or 'none'}",
        "message/events",
    )


def _gate_public_choice_payload_sanitized(
    evidence: dict[str, Any],
) -> GateResult:
    surface = _pending_choice_public_surface(evidence)
    leak = _first_forbidden_term(surface)
    if leak is None:
        return GateResult(
            "public_choice_payload_sanitized",
            True,
            "pass",
            "public pending choice payload contains no private tokens",
            "messages/session/events",
        )
    return GateResult(
        "public_choice_payload_sanitized",
        True,
        "fail",
        f"private pending choice token observed: {leak}",
        "messages/session/events",
    )


def _gate_pending_choice_planner_not_invoked(evidence: dict[str, Any]) -> GateResult:
    for event in _events(evidence):
        text = json.dumps(event, ensure_ascii=False, default=str)
        progress_kind = str(_get(event, "payload", "progress_kind") or "")
        if progress_kind.startswith("planner_") or "planner_choice" in text:
            return GateResult(
                "planner_not_invoked",
                True,
                "fail",
                f"planner signal observed: {progress_kind or event.get('id')}",
                "events/history",
            )
    return GateResult(
        "planner_not_invoked",
        True,
        "pass",
        "no planner choice signal observed",
        "events/history",
    )


def _gate_select_a_dispatched(evidence: dict[str, Any]) -> GateResult:
    for turn in evidence.get("turns") or []:
        text = ""
        error = None
        response = None
        if isinstance(turn, TurnRecord):
            text = turn.text
            error = turn.error
            response = turn.response
        elif isinstance(turn, dict):
            text = str(turn.get("text") or "")
            error = turn.get("error")
            response = turn.get("response")
        if text.strip().upper() == "A" and error is None and response is not None:
            return GateResult(
                "select_A_dispatched",
                True,
                "pass",
                "choice A dispatch succeeded",
                "turns",
            )
    return GateResult(
        "select_A_dispatched",
        True,
        "fail",
        "successful A selection dispatch missing",
        "turns",
    )


def _gate_choice_a_execution_started(
    event: dict[str, Any] | None,
) -> GateResult:
    if event:
        return GateResult(
            "choice_A_execution_started",
            True,
            "pass",
            f"event_id={event.get('id')}",
            "events",
        )
    return GateResult(
        "choice_A_execution_started",
        True,
        "fail",
        "chat_execution_started missing after A selection",
        "events",
    )


def _gate_execution_uses_choice_a_path(
    evidence: dict[str, Any],
    event: dict[str, Any] | None,
) -> GateResult:
    expected = _setup_choice_path_id(evidence, "A")
    actual = _get(event or {}, "payload", "learned_path_id")
    setup_type = str(_get(evidence, "setup_manifest", "setup_type") or "unknown")
    expected_hash = _stable_hash(expected)
    actual_hash = _stable_hash(actual)
    alias = _setup_choice_alias(evidence, "A") or "A"
    match = bool(expected and actual and expected == actual)
    evidence_text = (
        f"expected_choice=A; expected_alias={alias}; "
        f"expected_path_hash={expected_hash}; actual_path_hash={actual_hash}; "
        f"match={str(match).lower()}; setup_type={setup_type}"
    )
    if match:
        return GateResult(
            "execution_uses_choice_A_path",
            True,
            "pass",
            evidence_text,
            "setup_manifest/events",
        )
    return GateResult(
        "execution_uses_choice_A_path",
        True,
        "fail",
        evidence_text,
        "setup_manifest/events",
    )


def _gate_slot_override_after_choice(
    event: dict[str, Any] | None,
    expected_item_name: str | None,
) -> GateResult:
    if not expected_item_name:
        return GateResult(
            "slot_override_after_choice",
            False,
            "not_observable",
            "no expected business slot for A selection",
            "events",
        )
    actual = _get(event or {}, "payload", "slot_overrides", "item_name")
    if actual == expected_item_name:
        return GateResult(
            "slot_override_after_choice",
            True,
            "pass",
            f"slot_overrides.item_name={actual}",
            "events",
        )
    return GateResult(
        "slot_override_after_choice",
        True,
        "fail",
        f"expected slot_overrides.item_name={expected_item_name}, got {actual}",
        "events",
    )


def _gate_pending_choice_cleared(evidence: dict[str, Any]) -> GateResult:
    metadata = _get(evidence, "session", "metadata") or {}
    if (
        isinstance(metadata, dict)
        and "pending_choice" not in metadata
        and "pending_choice_private_map" not in metadata
    ):
        return GateResult(
            "pending_choice_cleared",
            True,
            "pass",
            "public session has no pending_choice after selection",
            "session",
        )
    return GateResult(
        "pending_choice_cleared",
        True,
        "fail",
        "pending choice state remains visible after selection",
        "session",
    )


def _gate_private_map_not_public_after_selection(
    evidence: dict[str, Any],
) -> GateResult:
    surface = {
        "messages": evidence.get("messages") or [],
        "session_metadata": _get(evidence, "session", "metadata") or {},
        "history_session_metadata": _get(evidence, "history", "session", "metadata")
        or {},
    }
    text = json.dumps(surface, ensure_ascii=False, default=str).lower()
    if "pending_choice_private_map" not in text:
        return GateResult(
            "private_map_not_public_after_selection",
            True,
            "pass",
            "messages and public session payload contain no private map",
            "messages/session/history",
        )
    return GateResult(
        "private_map_not_public_after_selection",
        True,
        "fail",
        "pending_choice_private_map observed after selection",
        "messages/session/history",
    )


def _gate_pending_choice_execution_verified(
    completed_event: dict[str, Any] | None,
    reporter_event: dict[str, Any] | None,
    expected_item_name: str | None,
) -> GateResult:
    outcome = _get(reporter_event or {}, "payload", "verification_outcome")
    if outcome == "verified":
        return GateResult(
            "execution_verified",
            True,
            "pass",
            "verification_outcome=verified",
            "task_result_reported",
        )
    if expected_item_name:
        dom_gate = _gate_dom_evidence(
            "execution_verified",
            completed_event,
            expected_item_name,
        )
        if dom_gate.status == "pass":
            return dom_gate
    return GateResult(
        "execution_verified",
        True,
        "fail",
        f"expected verified execution, reporter outcome={outcome}",
        "events/history",
    )


def _gate_setup_planner_candidates_current_eval(
    evidence: dict[str, Any],
) -> GateResult:
    manifest = evidence.get("setup_manifest")
    if not isinstance(manifest, dict):
        return GateResult(
            "setup_planner_candidates_current_eval",
            True,
            "fail",
            "setup manifest missing",
            "setup_manifest",
        )
    setup_type = str(manifest.get("setup_type") or "")
    candidates = _setup_candidates(evidence)
    aliases = [
        str(candidate.get("alias") or "")
        for candidate in candidates
        if candidate.get("alias")
    ]
    distinct_aliases = sorted(set(aliases))
    current_real_path_count = sum(
        1
        for candidate in candidates
        if candidate.get("is_current_eval_real_path")
        or candidate.get("current_eval_run")
        or candidate.get("source") == "current_eval_run"
    )
    live_capability = bool(manifest.get("live_multi_action_capability"))
    distinct_path_capability = bool(manifest.get("planner_distinct_path_capability"))
    if (
        setup_type in _planner_choice_setup_types()
        and len(candidates) >= 3
        and len(distinct_aliases) >= 3
        and (setup_type == "fixture_only" or current_real_path_count >= 1)
    ):
        return GateResult(
            "setup_planner_candidates_current_eval",
            True,
            "pass",
            (
                f"setup_type={setup_type}; "
                f"live_multi_action_capability={str(live_capability).lower()}; "
                f"planner_distinct_path_capability={str(distinct_path_capability).lower()}; "
                f"candidate_count={len(candidates)}; "
                f"current_eval_real_path_count={current_real_path_count}; "
                f"aliases={','.join(distinct_aliases)}"
            ),
            "setup_manifest",
        )
    return GateResult(
        "setup_planner_candidates_current_eval",
        True,
        "fail",
        (
            f"setup_type={setup_type or 'missing'}; candidate_count={len(candidates)}; "
            f"distinct_alias_count={len(distinct_aliases)}; "
            f"current_eval_real_path_count={current_real_path_count}"
        ),
        "setup_manifest",
    )


def _planner_choice_setup_types() -> set[str]:
    return {
        "live_same_session_distinct_paths",
        "live_setup_session_distinct_paths",
        "eval_only_planner_candidate_binding",
        "fixture_only",
    }


def _gate_planner_candidates_generated(evidence: dict[str, Any]) -> GateResult:
    event = _latest_planner_candidates_generated_event(evidence)
    if not event:
        return GateResult(
            "planner_candidates_generated",
            True,
            "fail",
            "planner_candidates_generated event missing",
            "events/history",
        )
    candidate_count = _get(event, "payload", "candidate_count")
    setup_count = len(_setup_candidates(evidence))
    if (
        isinstance(candidate_count, int)
        and setup_count
        and candidate_count < setup_count
    ):
        return GateResult(
            "planner_candidates_generated",
            True,
            "fail",
            f"candidate_count={candidate_count} < setup_candidate_count={setup_count}",
            "events/history",
        )
    return GateResult(
        "planner_candidates_generated",
        True,
        "pass",
        f"event_id={event.get('id')}; candidate_count={candidate_count}",
        "events/history",
    )


def _gate_planner_choice_created(evidence: dict[str, Any]) -> GateResult:
    event = _latest_planner_choice_created_event(evidence)
    if event:
        return GateResult(
            "planner_choice_created",
            True,
            "pass",
            f"event_id={event.get('id')}",
            "events/history",
        )
    return GateResult(
        "planner_choice_created",
        True,
        "fail",
        "planner_choice_created event missing",
        "events/history",
    )


def _gate_non_planner_choice_not_used(evidence: dict[str, Any]) -> GateResult:
    for event in _events(evidence):
        if _get(event, "payload", "progress_kind") == "pending_choice_created":
            return GateResult(
                "non_planner_choice_not_used",
                True,
                "fail",
                f"non-planner pending_choice_created observed at event {event.get('id')}",
                "events/history",
            )
    return GateResult(
        "non_planner_choice_not_used",
        True,
        "pass",
        "no non-planner pending_choice_created event observed",
        "events/history",
    )


def _gate_planner_public_payload_sanitized(evidence: dict[str, Any]) -> GateResult:
    surface = _planner_public_surface(evidence)
    leak = _first_forbidden_term(surface)
    if leak is None:
        return GateResult(
            "planner_public_payload_sanitized",
            True,
            "pass",
            "visible planner choice payload contains no private tokens",
            "messages/session/events",
        )
    return GateResult(
        "planner_public_payload_sanitized",
        True,
        "fail",
        f"private planner payload token observed: {leak}",
        "messages/session/events",
    )


def _gate_planner_event_sanitized(evidence: dict[str, Any]) -> GateResult:
    events = _planner_safety_events(evidence)
    leak = _first_forbidden_term(events)
    if leak is None:
        return GateResult(
            "planner_event_sanitized",
            True,
            "pass",
            f"{len(events)} planner event(s) sanitized",
            "events/history",
        )
    return GateResult(
        "planner_event_sanitized",
        True,
        "fail",
        f"private planner event token observed: {leak}",
        "events/history",
    )


def _gate_planner_warning_wording_safe(evidence: dict[str, Any]) -> GateResult:
    warning_count = _planner_signal_count(evidence, "planner_warning_count")
    risk_count = _planner_signal_count(evidence, "planner_risk_count")
    uncertainty_count = _planner_signal_count(evidence, "uncertainty_count")
    if warning_count + risk_count + uncertainty_count == 0:
        return GateResult(
            "planner_warning_wording_safe",
            False,
            "not_observable",
            "no planner warning/risk/uncertainty count observed",
            "messages/events",
        )
    visible = "\n".join(_agent_messages(evidence))
    raw_markers = (
        "top candidate",
        "historical warning",
        "ambiguous_selection",
        "provisional_trust",
        "flaky_path",
        "risk_type",
        "confirmation_required",
    )
    leaked = next((marker for marker in raw_markers if marker in visible), None)
    if leaked:
        return GateResult(
            "planner_warning_wording_safe",
            True,
            "fail",
            f"raw planner wording leaked: {leaked}",
            "messages/events",
        )
    generic_markers = (
        "存在 Planner 警告",
        "存在风险提示",
        "存在不确定性",
        "需要你确认后执行",
    )
    if any(marker in visible for marker in generic_markers):
        return GateResult(
            "planner_warning_wording_safe",
            True,
            "pass",
            "visible planner warnings use generic wording",
            "messages/events",
        )
    return GateResult(
        "planner_warning_wording_safe",
        True,
        "fail",
        "planner warning/risk/uncertainty exists but generic visible wording is missing",
        "messages/events",
    )


def _gate_planner_top_choice_observable(evidence: dict[str, Any]) -> GateResult:
    event = _latest_planner_choice_created_event(evidence)
    top_choice_id = _get(event or {}, "payload", "top_choice_id")
    top_path_hash = _get(event or {}, "payload", "top_path_hash")
    if top_choice_id or top_path_hash:
        return GateResult(
            "planner_top_choice_observable",
            False,
            "pass",
            f"top_choice_id={top_choice_id or 'N/A'}; top_path_hash={top_path_hash or 'N/A'}",
            "events/history",
        )
    return GateResult(
        "planner_top_choice_observable",
        False,
        "not_observable",
        "current public read surface does not expose top choice id/hash",
        "events/history",
    )


def _gate_select_planner_choice_dispatched(evidence: dict[str, Any]) -> GateResult:
    expected_choice = str(
        _get(evidence, "setup_manifest", "expected_selected_choice") or "A"
    )
    for turn in evidence.get("turns") or []:
        text = ""
        error = None
        response = None
        if isinstance(turn, TurnRecord):
            text = turn.text
            error = turn.error
            response = turn.response
        elif isinstance(turn, dict):
            text = str(turn.get("text") or "")
            error = turn.get("error")
            response = turn.get("response")
        if (
            text.strip().upper() == expected_choice
            and error is None
            and response is not None
        ):
            return GateResult(
                "select_planner_choice_dispatched",
                True,
                "pass",
                f"choice {expected_choice} dispatch succeeded",
                "turns",
            )
    return GateResult(
        "select_planner_choice_dispatched",
        True,
        "fail",
        f"successful {expected_choice} selection dispatch missing",
        "turns",
    )


def _gate_planner_choice_selected(event: dict[str, Any] | None) -> GateResult:
    if event:
        return GateResult(
            "planner_choice_selected",
            True,
            "pass",
            f"event_id={event.get('id')}",
            "events/history",
        )
    return GateResult(
        "planner_choice_selected",
        True,
        "fail",
        "planner_choice_selected event missing",
        "events/history",
    )


def _gate_planner_choice_execution_started(
    event: dict[str, Any] | None,
) -> GateResult:
    if event:
        return GateResult(
            "planner_choice_execution_started",
            True,
            "pass",
            f"event_id={event.get('id')}",
            "events",
        )
    return GateResult(
        "planner_choice_execution_started",
        True,
        "fail",
        "chat_execution_started missing after planner choice selection",
        "events",
    )


def _gate_execution_uses_selected_choice_path(
    evidence: dict[str, Any],
    event: dict[str, Any] | None,
) -> GateResult:
    selected_choice = str(
        _get(evidence, "setup_manifest", "expected_selected_choice") or "A"
    )
    expected = _setup_choice_path_id(evidence, selected_choice)
    actual = _get(event or {}, "payload", "learned_path_id")
    setup_type = str(_get(evidence, "setup_manifest", "setup_type") or "unknown")
    distinct_path_capability = bool(
        _get(evidence, "setup_manifest", "planner_distinct_path_capability")
    )
    expected_hash = _stable_hash(expected)
    actual_hash = _stable_hash(actual)
    alias = _setup_choice_alias(evidence, selected_choice) or selected_choice
    match = bool(expected and actual and expected == actual)
    evidence_text = (
        f"expected_choice={selected_choice}; expected_alias={alias}; "
        f"expected_path_hash={expected_hash}; actual_path_hash={actual_hash}; "
        f"match={str(match).lower()}; setup_type={setup_type}; "
        f"planner_distinct_path_capability={str(distinct_path_capability).lower()}"
    )
    if match:
        return GateResult(
            "execution_uses_selected_choice_path",
            True,
            "pass",
            evidence_text,
            "setup_manifest/events",
        )
    return GateResult(
        "execution_uses_selected_choice_path",
        True,
        "fail",
        evidence_text,
        "setup_manifest/events",
    )


def _gate_no_planner_candidates_generated(evidence: dict[str, Any]) -> GateResult:
    event = _latest_planner_candidates_generated_event(evidence)
    if event:
        return GateResult(
            "no_planner_candidates_generated",
            True,
            "fail",
            f"planner_candidates_generated observed at event {event.get('id')}",
            "events/history",
        )
    return GateResult(
        "no_planner_candidates_generated",
        True,
        "pass",
        "no planner_candidates_generated event observed",
        "events/history",
    )


def _gate_no_planner_choice_created(evidence: dict[str, Any]) -> GateResult:
    event = _latest_planner_choice_created_event(evidence)
    if event:
        return GateResult(
            "no_planner_choice_created",
            True,
            "fail",
            f"planner_choice_created observed at event {event.get('id')}",
            "events/history",
        )
    return GateResult(
        "no_planner_choice_created",
        True,
        "pass",
        "no planner_choice_created event observed",
        "events/history",
    )


def _gate_direct_execution_started(event: dict[str, Any] | None) -> GateResult:
    if event:
        return GateResult(
            "direct_execution_started",
            True,
            "pass",
            f"event_id={event.get('id')}",
            "events",
        )
    return GateResult(
        "direct_execution_started",
        True,
        "fail",
        "chat_execution_started missing",
        "events",
    )


def _has_recovery_menu(message: str) -> bool:
    return all(marker in message for marker in ("A.", "B.", "C.")) and all(
        label in message for label in ("重试执行该操作", "重新学习", "取消")
    )


def _agent_messages(evidence: dict[str, Any]) -> list[str]:
    raw_messages = [
        raw
        for raw in evidence.get("messages") or []
        if isinstance(raw, dict) and raw.get("role") in {"agent", "engine"}
    ]
    if not raw_messages:
        raw_messages = [
            raw
            for raw in _get(evidence, "history", "messages") or []
            if isinstance(raw, dict) and raw.get("role") in {"agent", "engine"}
        ]
    messages: list[str] = []
    for raw in raw_messages:
        if isinstance(raw, dict) and raw.get("role") in {"agent", "engine"}:
            messages.append(str(raw.get("content") or ""))
    return messages


def _first_forbidden_term(value: Any) -> str | None:
    text = json.dumps(value, ensure_ascii=False, default=str)
    lowered = text.lower()
    for term in sorted(FORBIDDEN_PAYLOAD_TERMS, key=str.lower):
        if term.lower() in lowered:
            return term
    return None


def _case_status(gates: list[GateResult]) -> str:
    required = [gate for gate in gates if gate.required]
    if any(gate.status == "blocked" for gate in required):
        return "blocked"
    if any(gate.status == "fail" for gate in required):
        return "fail"
    if all(gate.status == "pass" for gate in required):
        return "pass"
    return "error"


def _warnings(gates: list[GateResult]) -> list[str]:
    return [
        f"{gate.name}: {gate.status} - {gate.evidence}"
        for gate in gates
        if gate.status in {"warning", "not_observable"}
    ]


def reduce_exit_code(
    statuses: list[str],
    *,
    artifact_write_failed: bool = False,
) -> int:
    if artifact_write_failed:
        return 4
    if "error" in statuses:
        return 5
    if "blocked" in statuses:
        return 2
    if "timeout" in statuses:
        return 3
    if "fail" in statuses:
        return 1
    return 0


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            key_text = str(key).lower()
            if key_text in SENSITIVE_KEYS:
                result[key] = "[REDACTED]"
            else:
                result[key] = redact_sensitive(item)
        return result
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


def render_markdown_report(
    result: EvalResult,
    *,
    artifact_path: Path,
) -> str:
    warnings = [warning for case in result.case_results for warning in case.warnings]
    has_failure_recovery = any(
        case.case_id == FAILURE_RECOVERY_CASE for case in result.case_results
    )
    pending_choice_case = next(
        (case for case in result.case_results if case.case_id == PENDING_CHOICE_CASE),
        None,
    )
    planner_choice_case = next(
        (case for case in result.case_results if case.case_id == PLANNER_CHOICE_CASE),
        None,
    )
    lines = [
        "# M11.3.6 WAgent Runtime Eval Result",
        "",
        f"Date: {datetime.now(UTC).isoformat()}",
        f"Status: {result.status}",
        f"Commit: {result.environment.get('commit') or 'unknown'}",
        f"API Base: {result.config.get('api_base') or 'unknown'}",
        f"Product URL: {result.config.get('product_url') or 'unknown'}",
        f"Session ID: {result.session_id or 'N/A'}",
        f"JSON Artifact: {artifact_path}",
        "",
        "## Cases",
        "",
        "| Case | Status | Required Gates | Warnings |",
        "|---|---|---:|---:|",
    ]
    for case in result.case_results:
        required = [gate for gate in case.gates if gate.required]
        passed = sum(1 for gate in required if gate.status == "pass")
        lines.append(
            f"| {case.case_id} | {case.status} | {passed}/{len(required)} | "
            f"{len(case.warnings)} |"
        )
    lines.extend(
        [
            "",
            "## Required Gates",
            "",
            "| Case | Gate | Status | Evidence | Source |",
            "|---|---|---|---|---|",
        ]
    )
    for case in result.case_results:
        for gate in case.gates:
            lines.append(
                f"| {case.case_id} | {gate.name} | {gate.status} | "
                f"{_md_escape(gate.evidence)} | {_md_escape(gate.source)} |"
            )
    lines.extend(["", "## Warnings / Not Observable", ""])
    if warnings:
        lines.extend(f"- {_md_escape(warning)}" for warning in warnings)
    else:
        lines.append("- None")
    if has_failure_recovery:
        live_status = "run through Conversation API" if result.session_id else "not run"
        trigger_type = (
            "eval-only hook"
            if result.session_id and result.status != "blocked"
            else "not run"
        )
        lines.extend(
            [
                "",
                "## Failure Recovery Eval",
                "",
                f"- Live Conversation eval: {live_status}.",
                f"- Failure trigger type: {trigger_type}.",
                "- Retry execution: not run.",
            ]
        )
    if pending_choice_case is not None:
        setup_gate = next(
            (
                gate
                for gate in pending_choice_case.gates
                if gate.name == "setup_multi_candidate_current_eval"
            ),
            None,
        )
        setup_type = _evidence_field(
            setup_gate.evidence if setup_gate else "", "setup_type"
        )
        live_multi = _evidence_field(
            setup_gate.evidence if setup_gate else "",
            "live_multi_action_capability",
        )
        lines.extend(
            [
                "",
                "## Pending Choice Eval",
                "",
                f"- Live Conversation eval: {'run through Conversation API' if result.session_id else 'not run'}.",
                f"- Candidate setup type: {setup_type or 'unknown'}.",
                f"- Live multi-action capability: {live_multi or 'unknown'}.",
                "- Planner-backed choice: out of scope for 11.3.6.3.",
            ]
        )
    if planner_choice_case is not None:
        setup_gate = next(
            (
                gate
                for gate in planner_choice_case.gates
                if gate.name == "setup_planner_candidates_current_eval"
            ),
            None,
        )
        selected_gate = next(
            (
                gate
                for gate in planner_choice_case.gates
                if gate.name == "execution_uses_selected_choice_path"
            ),
            None,
        )
        planner_events = [
            gate.name
            for gate in planner_choice_case.gates
            if gate.name in {"planner_candidates_generated", "planner_choice_created"}
            and gate.status == "pass"
        ]
        setup_type = _evidence_field(
            setup_gate.evidence if setup_gate else "", "setup_type"
        )
        live_multi = _evidence_field(
            setup_gate.evidence if setup_gate else "",
            "live_multi_action_capability",
        )
        distinct_path = _evidence_field(
            setup_gate.evidence if setup_gate else "",
            "planner_distinct_path_capability",
        )
        lines.extend(
            [
                "",
                "## Planner-backed Choice Eval",
                "",
                f"- Live Conversation eval: {'run through Conversation API' if result.session_id else 'not run'}.",
                f"- Candidate setup type: {setup_type or 'unknown'}.",
                f"- Live multi-action capability: {live_multi or 'unknown'}.",
                f"- Planner distinct-path capability: {distinct_path or 'unknown'}.",
                f"- Planner events observed: {', '.join(planner_events) or 'none'}.",
                f"- Selected choice evidence: {selected_gate.evidence if selected_gate else 'N/A'}.",
                (
                    "- Eval-only alias binding does not prove full live distinct-action "
                    "Planner capability."
                ),
            ]
        )
    lines.extend(
        [
            "",
            "## Not Run / Boundary",
            "",
            "- `verify-scenario`: not run.",
            "- autonomous run endpoints: not called.",
            "- Console UI smoke: not run.",
            "- Direct replay API substitution: not used.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_artifacts(
    result: EvalResult,
    config: EvalConfig,
) -> tuple[Path, Path | None]:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = config.artifact_dir / f"wagent-runtime-eval-{timestamp}.json"
    markdown_path: Path | None = None
    config.artifact_dir.mkdir(parents=True, exist_ok=True)
    result_dict = redact_sensitive(_to_jsonable(result))
    json_path.write_text(
        json.dumps(result_dict, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if config.write_markdown:
        config.result_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = config.result_dir / _markdown_result_filename(
            config.cases,
            timestamp,
        )
        markdown_path.write_text(
            render_markdown_report(result, artifact_path=json_path),
            encoding="utf-8",
        )
    return json_path, markdown_path


def _markdown_result_filename(cases: list[str], timestamp: str) -> str:
    if FAILURE_RECOVERY_CASE in cases:
        return f"m11-11.3.6.2-failure-recovery-eval-{timestamp}.md"
    if PLANNER_CHOICE_CASE in cases:
        return f"m11-11.3.6.4-planner-backed-choice-eval-{timestamp}.md"
    if PENDING_CHOICE_CASE in cases:
        return f"m11-11.3.6.3-pending-choice-multi-candidate-eval-{timestamp}.md"
    return f"m11-11.3.6.1-wagent-runtime-eval-core-{timestamp}.md"


def _evidence_field(evidence: str, key: str) -> str | None:
    prefix = f"{key}="
    for part in evidence.split(";"):
        value = part.strip()
        if value.startswith(prefix):
            return value[len(prefix) :].strip()
    return None


def run_eval(config: EvalConfig) -> EvalResult:
    preflight = run_preflight(config)
    environment = {"commit": _git_commit(), "cwd": str(Path.cwd())}
    config_dict = _config_dict(config)
    if preflight.status == "blocked":
        cases = [
            CaseResult(
                case_id=case,
                status="blocked",
                gates=[
                    GateResult(
                        "preflight",
                        True,
                        "blocked",
                        "API or product site unavailable",
                        "preflight",
                    )
                ],
                warnings=[],
            )
            for case in config.cases
        ]
        return EvalResult(
            schema_version=SCHEMA_VERSION,
            status="blocked",
            environment=environment,
            services=preflight.services,
            config=config_dict,
            session_id=None,
            case_results=cases,
            turns=[],
            events=[],
            messages=[],
            history={},
            learned_paths=[],
            raw_api_responses={},
            gate_summary=_gate_summary(cases),
        )

    driver = ConversationDriver(config)
    turns: list[TurnRecord] = []
    case_results: list[CaseResult] = []
    latest_evidence: dict[str, Any] = {}
    learned_path_id: str | None = None
    try:
        session = driver.create_session()
        session_id = session["id"]
        collector = EvidenceCollector(driver)
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        if "items_closed_loop" in config.cases:
            learn_name = f"测试项目A-{stamp}"
            exec_name = f"测试项目B-{stamp}"
            for text in [
                config.product_url,
                f"学习新增项目，名称叫 {learn_name}",
                f"帮我新增项目，名称叫 {exec_name}",
            ]:
                turn = driver.send_turn(session_id, text)
                turns.append(turn)
                if turn.error:
                    raise EvalBlockedError(turn.error)
            latest_evidence = collector.collect(session_id)
            learned_path_id = _latest_learned_path_id(latest_evidence)
            if learned_path_id and not latest_evidence.get("learned_path_detail"):
                latest_evidence = collector.collect(session_id, [learned_path_id])
            case_results.append(
                GateEvaluator().evaluate_items_closed_loop(
                    latest_evidence,
                    expected_item_name=exec_name,
                )
            )
        if "single_path_direct_replay_regression" in config.cases:
            if learned_path_id is None:
                case_results.append(
                    CaseResult(
                        case_id="single_path_direct_replay_regression",
                        status="blocked",
                        gates=[
                            GateResult(
                                "items_closed_loop_dependency",
                                True,
                                "blocked",
                                "single-path regression requires a learned path from this eval session",
                                "runner",
                            )
                        ],
                    )
                )
            else:
                exec_name = f"测试项目C-{stamp}"
                turn = driver.send_turn(
                    session_id,
                    f"帮我新增项目，名称叫 {exec_name}",
                )
                turns.append(turn)
                if turn.error:
                    raise EvalBlockedError(turn.error)
                latest_evidence = collector.collect(session_id, [learned_path_id])
                case_results.append(
                    GateEvaluator().evaluate_single_path_direct_replay_regression(
                        latest_evidence,
                        expected_item_name=exec_name,
                        learned_path_id=learned_path_id,
                    )
                )
        if FAILURE_RECOVERY_CASE in config.cases:
            if learned_path_id is None:
                learn_name = f"测试项目A-{stamp}"
                exec_name = f"测试项目B-{stamp}"
                for text in [
                    config.product_url,
                    f"学习新增项目，名称叫 {learn_name}",
                    f"帮我新增项目，名称叫 {exec_name}",
                ]:
                    turn = driver.send_turn(session_id, text)
                    turns.append(turn)
                    if turn.error:
                        raise EvalBlockedError(turn.error)
                latest_evidence = collector.collect(session_id)
                learned_path_id = _latest_learned_path_id(latest_evidence)
                if learned_path_id and not latest_evidence.get("learned_path_detail"):
                    latest_evidence = collector.collect(session_id, [learned_path_id])
            if learned_path_id is None:
                case_results.append(
                    CaseResult(
                        case_id=FAILURE_RECOVERY_CASE,
                        status="blocked",
                        gates=[
                            GateResult(
                                "items_closed_loop_dependency",
                                True,
                                "blocked",
                                "failure recovery eval requires a learned path from this eval session",
                                "runner",
                            )
                        ],
                    )
                )
            else:
                exec_name = f"测试项目D-{stamp}"
                turn = driver.send_turn(
                    session_id,
                    f"帮我新增项目，名称叫 {exec_name}",
                    metadata={
                        "eval_fault_injection": {
                            "case_id": FAILURE_RECOVERY_CASE,
                            "reporter_outcome": "needs_review",
                        }
                    },
                )
                turns.append(turn)
                if turn.error:
                    raise EvalBlockedError(turn.error)
                latest_evidence = collector.collect(session_id, [learned_path_id])
                latest_evidence["raw_api_responses"] = {"records": driver.raw_records}
                case_results.append(
                    GateEvaluator().evaluate_failure_recovery_menu_safety(
                        latest_evidence,
                    )
                )
        if PENDING_CHOICE_CASE in config.cases:
            if learned_path_id is None:
                learn_name = f"测试项目A-{stamp}"
                exec_name = f"测试项目B-{stamp}"
                for text in [
                    config.product_url,
                    f"学习新增项目，名称叫 {learn_name}",
                    f"帮我新增项目，名称叫 {exec_name}",
                ]:
                    turn = driver.send_turn(session_id, text)
                    turns.append(turn)
                    if turn.error:
                        raise EvalBlockedError(turn.error)
                latest_evidence = collector.collect(session_id)
                learned_path_id = _latest_learned_path_id(latest_evidence)
                if learned_path_id and not latest_evidence.get("learned_path_detail"):
                    latest_evidence = collector.collect(session_id, [learned_path_id])
            if learned_path_id is None:
                case_results.append(
                    CaseResult(
                        case_id=PENDING_CHOICE_CASE,
                        status="blocked",
                        gates=[
                            GateResult(
                                "items_closed_loop_dependency",
                                True,
                                "blocked",
                                "pending choice eval requires a learned path from this eval run",
                                "runner",
                            )
                        ],
                    )
                )
            else:
                setup_manifest = _build_pending_choice_setup_manifest(
                    learned_path_id=learned_path_id,
                    target_url=config.product_url,
                )
                eval_session = driver.create_session(
                    metadata=_pending_choice_eval_session_metadata(setup_manifest),
                )
                session_id = eval_session["id"]
                collector = EvidenceCollector(driver)
                exec_name = f"测试项目ChoiceA-{stamp}"
                turn = driver.send_turn(session_id, config.product_url)
                turns.append(turn)
                if turn.error:
                    raise EvalBlockedError(turn.error)
                turn = driver.send_turn(
                    session_id,
                    f"帮我处理一下这个页面，名称叫 {exec_name}",
                    metadata={
                        "eval_candidate_setup": _pending_choice_dispatch_setup(
                            setup_manifest,
                        )
                    },
                )
                turns.append(turn)
                if turn.error:
                    raise EvalBlockedError(turn.error)
                turn = driver.send_turn(session_id, "A")
                turns.append(turn)
                if turn.error:
                    raise EvalBlockedError(turn.error)
                latest_evidence = collector.collect(session_id, [learned_path_id])
                latest_evidence["setup_manifest"] = setup_manifest
                latest_evidence["turns"] = _to_jsonable(turns)
                latest_evidence["raw_api_responses"] = {"records": driver.raw_records}
                case_results.append(
                    GateEvaluator().evaluate_pending_choice_multi_candidate(
                        latest_evidence,
                        expected_item_name=exec_name,
                    )
                )
        if PLANNER_CHOICE_CASE in config.cases:
            if learned_path_id is None:
                learn_name = f"测试项目A-{stamp}"
                exec_name = f"测试项目B-{stamp}"
                for text in [
                    config.product_url,
                    f"学习新增项目，名称叫 {learn_name}",
                    f"帮我新增项目，名称叫 {exec_name}",
                ]:
                    turn = driver.send_turn(session_id, text)
                    turns.append(turn)
                    if turn.error:
                        raise EvalBlockedError(turn.error)
                latest_evidence = collector.collect(session_id)
                learned_path_id = _latest_learned_path_id(latest_evidence)
                if learned_path_id and not latest_evidence.get("learned_path_detail"):
                    latest_evidence = collector.collect(session_id, [learned_path_id])
            if learned_path_id is None:
                blocked_gate = GateResult(
                    "items_closed_loop_dependency",
                    True,
                    "blocked",
                    "planner-backed choice eval requires a learned path from this eval run",
                    "runner",
                )
                case_results.append(
                    CaseResult(
                        case_id=PLANNER_CHOICE_CASE,
                        status="blocked",
                        gates=[blocked_gate],
                    )
                )
                case_results.append(
                    CaseResult(
                        case_id=PLANNER_SINGLE_PATH_REGRESSION_CASE,
                        status="blocked",
                        gates=[blocked_gate],
                    )
                )
            else:
                setup_manifest = _build_planner_choice_setup_manifest(
                    learned_path_id=learned_path_id,
                    target_url=config.product_url,
                )
                eval_session = driver.create_session(
                    metadata=_planner_choice_eval_session_metadata(setup_manifest),
                )
                session_id = eval_session["id"]
                collector = EvidenceCollector(driver)
                exec_name = f"测试项目PlannerA-{stamp}"
                turn = driver.send_turn(session_id, config.product_url)
                turns.append(turn)
                if turn.error:
                    raise EvalBlockedError(turn.error)
                turn = driver.send_turn(
                    session_id,
                    f"帮我处理一下这个页面，名称叫 {exec_name}",
                )
                turns.append(turn)
                if turn.error:
                    raise EvalBlockedError(turn.error)
                turn = driver.send_turn(session_id, "A")
                turns.append(turn)
                if turn.error:
                    raise EvalBlockedError(turn.error)
                latest_evidence = collector.collect(session_id, [learned_path_id])
                latest_evidence["setup_manifest"] = setup_manifest
                latest_evidence["turns"] = _to_jsonable(turns)
                latest_evidence["raw_api_responses"] = {"records": driver.raw_records}
                case_results.append(
                    GateEvaluator().evaluate_planner_backed_choice(
                        latest_evidence,
                        expected_item_name=exec_name,
                    )
                )

                single_session = driver.create_session(
                    metadata={
                        "pending_target": {"url": config.product_url},
                        "learned_actions": [
                            {
                                "alias": "新增项目",
                                "utterances": ["新增项目", "帮我新增项目"],
                                "learned_path_id": learned_path_id,
                                "target_url": config.product_url,
                                "source": "wagent_eval_single_path_regression",
                            }
                        ],
                    },
                )
                session_id = single_session["id"]
                collector = EvidenceCollector(driver)
                single_name = f"测试项目PlannerSingle-{stamp}"
                turn = driver.send_turn(session_id, config.product_url)
                turns.append(turn)
                if turn.error:
                    raise EvalBlockedError(turn.error)
                turn = driver.send_turn(
                    session_id, f"帮我新增项目，名称叫 {single_name}"
                )
                turns.append(turn)
                if turn.error:
                    raise EvalBlockedError(turn.error)
                latest_evidence = collector.collect(session_id, [learned_path_id])
                latest_evidence["turns"] = _to_jsonable(turns)
                latest_evidence["raw_api_responses"] = {"records": driver.raw_records}
                case_results.append(
                    GateEvaluator().evaluate_planner_single_path_bypass_regression(
                        latest_evidence,
                        expected_item_name=single_name,
                        learned_path_id=learned_path_id,
                    )
                )
        status = _overall_status(case_results)
        return EvalResult(
            schema_version=SCHEMA_VERSION,
            status=status,
            environment=environment,
            services=preflight.services,
            config=config_dict,
            session_id=session_id,
            case_results=case_results,
            turns=turns,
            events=latest_evidence.get("events") or [],
            messages=latest_evidence.get("messages") or [],
            history=latest_evidence.get("history") or {},
            learned_paths=latest_evidence.get("learned_paths") or [],
            raw_api_responses={"records": driver.raw_records},
            gate_summary=_gate_summary(case_results),
        )
    except (EvalTimeoutError, httpx.TimeoutException) as exc:
        case_results.append(_terminal_case("timeout", str(exc), "dispatch"))
    except Exception as exc:  # noqa: BLE001 - runner records internal failure
        case_results.append(_terminal_case("error", str(exc), "runner"))
    finally:
        driver.close()

    return EvalResult(
        schema_version=SCHEMA_VERSION,
        status=_overall_status(case_results),
        environment=environment,
        services=preflight.services,
        config=config_dict,
        session_id=latest_evidence.get("session", {}).get("id"),
        case_results=case_results,
        turns=turns,
        events=latest_evidence.get("events") or [],
        messages=latest_evidence.get("messages") or [],
        history=latest_evidence.get("history") or {},
        learned_paths=latest_evidence.get("learned_paths") or [],
        raw_api_responses={"records": driver.raw_records},
        gate_summary=_gate_summary(case_results),
    )


def _terminal_case(status: str, evidence: str, source: str) -> CaseResult:
    return CaseResult(
        case_id="runner",
        status=status,
        gates=[
            GateResult(
                name=status,
                required=True,
                status=status,
                evidence=evidence,
                source=source,
            )
        ],
    )


def _overall_status(case_results: list[CaseResult]) -> str:
    statuses = [case.status for case in case_results]
    if not statuses:
        return "error"
    if "error" in statuses:
        return "error"
    if "blocked" in statuses:
        return "blocked"
    if "timeout" in statuses:
        return "timeout"
    if "fail" in statuses:
        return "fail"
    return "pass"


def _gate_summary(case_results: list[CaseResult]) -> dict[str, Any]:
    required = [gate for case in case_results for gate in case.gates if gate.required]
    return {
        "required_total": len(required),
        "required_passed": sum(1 for gate in required if gate.status == "pass"),
        "required_failed": sum(1 for gate in required if gate.status == "fail"),
        "required_blocked": sum(1 for gate in required if gate.status == "blocked"),
        "warnings": sum(
            1
            for case in case_results
            for gate in case.gates
            if gate.status in {"warning", "not_observable"}
        ),
    }


def _config_dict(config: EvalConfig) -> dict[str, Any]:
    return {
        "api_base": config.api_base,
        "product_url": config.product_url,
        "cases": list(config.cases),
        "timeout": config.timeout,
        "artifact_dir": str(config.artifact_dir),
        "result_dir": str(config.result_dir),
        "browser_visibility": config.browser_visibility,
        "write_markdown": config.write_markdown,
    }


def _build_pending_choice_setup_manifest(
    *,
    learned_path_id: str,
    target_url: str,
) -> dict[str, Any]:
    aliases = [("A", "新增项目"), ("B", "添加项目"), ("C", "录入项目")]
    candidates = []
    for index, (choice_id, alias) in enumerate(aliases):
        candidates.append(
            {
                "choice_id": choice_id,
                "alias": alias,
                "learned_path_id": learned_path_id,
                "target_url": target_url,
                "source": "current_eval_run" if index == 0 else "eval_alias_binding",
                "is_current_eval_real_path": index == 0,
                "path_hash": _stable_hash(learned_path_id),
            }
        )
    return {
        "case_id": PENDING_CHOICE_CASE,
        "setup_type": "eval_only_candidate_binding",
        "live_multi_action_capability": False,
        "candidates": candidates,
    }


def _build_planner_choice_setup_manifest(
    *,
    learned_path_id: str,
    target_url: str,
) -> dict[str, Any]:
    aliases = [("A", "新增项目"), ("B", "添加项目"), ("C", "录入项目")]
    candidates = []
    for index, (choice_id, alias) in enumerate(aliases):
        candidates.append(
            {
                "choice_id": choice_id,
                "alias": alias,
                "learned_path_id": learned_path_id,
                "target_url": target_url,
                "source": "current_eval_run" if index == 0 else "eval_alias_binding",
                "is_current_eval_real_path": index == 0,
                "path_hash": _stable_hash(learned_path_id),
            }
        )
    return {
        "case_id": PLANNER_CHOICE_CASE,
        "setup_type": "eval_only_planner_candidate_binding",
        "live_multi_action_capability": False,
        "planner_distinct_path_capability": False,
        "expected_selected_choice": "A",
        "candidates": candidates,
    }


def _pending_choice_eval_session_metadata(
    setup_manifest: dict[str, Any],
) -> dict[str, Any]:
    actions = []
    for candidate in setup_manifest.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        alias = str(candidate.get("alias") or "")
        actions.append(
            {
                "alias": alias,
                "utterances": [alias] if alias else [],
                "learned_path_id": candidate.get("learned_path_id"),
                "target_url": candidate.get("target_url"),
                "source": "wagent_eval_candidate_binding",
            }
        )
    return {
        "pending_target": {"url": actions[0].get("target_url")} if actions else {},
        "learned_actions": actions,
        "eval_candidate_setup": {
            "case_id": PENDING_CHOICE_CASE,
            "setup_type": setup_manifest.get("setup_type"),
            "live_multi_action_capability": setup_manifest.get(
                "live_multi_action_capability",
            ),
            "candidate_count": len(actions),
            "aliases": [action.get("alias") for action in actions],
            "path_hashes": [
                candidate.get("path_hash")
                for candidate in setup_manifest.get("candidates") or []
                if isinstance(candidate, dict)
            ],
        },
    }


def _planner_choice_eval_session_metadata(
    setup_manifest: dict[str, Any],
) -> dict[str, Any]:
    actions = []
    for candidate in setup_manifest.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        alias = str(candidate.get("alias") or "")
        actions.append(
            {
                "alias": alias,
                "utterances": [alias, f"帮我{alias}"] if alias else [],
                "learned_path_id": candidate.get("learned_path_id"),
                "target_url": candidate.get("target_url"),
                "source": "wagent_eval_planner_candidate_binding",
            }
        )
    return {
        "pending_target": {"url": actions[0].get("target_url")} if actions else {},
        "learned_actions": actions,
        "eval_candidate_setup": {
            "case_id": PLANNER_CHOICE_CASE,
            "setup_type": setup_manifest.get("setup_type"),
            "live_multi_action_capability": setup_manifest.get(
                "live_multi_action_capability",
            ),
            "planner_distinct_path_capability": setup_manifest.get(
                "planner_distinct_path_capability",
            ),
            "candidate_count": len(actions),
            "aliases": [action.get("alias") for action in actions],
            "path_hashes": [
                candidate.get("path_hash")
                for candidate in setup_manifest.get("candidates") or []
                if isinstance(candidate, dict)
            ],
        },
    }


def _pending_choice_dispatch_setup(setup_manifest: dict[str, Any]) -> dict[str, Any]:
    actions = []
    for candidate in setup_manifest.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        actions.append(
            {
                "choice_id": candidate.get("choice_id"),
                "alias": candidate.get("alias"),
                "learned_path_id": candidate.get("learned_path_id"),
            }
        )
    return {
        "case_id": PENDING_CHOICE_CASE,
        "setup_type": setup_manifest.get("setup_type"),
        "live_multi_action_capability": setup_manifest.get(
            "live_multi_action_capability",
        ),
        "actions": actions,
    }


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return result.stdout.strip() or None


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _get(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _events(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    events = evidence.get("events") or []
    return [event for event in events if isinstance(event, dict)]


def _event_index(evidence: dict[str, Any], event: dict[str, Any] | None) -> int:
    if event is None:
        return -1
    events = _events(evidence)
    for index, candidate in enumerate(events):
        if candidate is event or candidate.get("id") == event.get("id"):
            return index
    return -1


def _events_after(
    evidence: dict[str, Any],
    event: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    index = _event_index(evidence, event)
    if index < 0:
        return _events(evidence)
    return _events(evidence)[index + 1 :]


def _latest_event_after(
    evidence: dict[str, Any],
    event_type: str,
    after_event: dict[str, Any] | None,
) -> dict[str, Any] | None:
    matches = [
        event
        for event in _events_after(evidence, after_event)
        if event.get("type") == event_type
    ]
    if matches:
        return matches[-1]
    matches = [event for event in _events(evidence) if event.get("type") == event_type]
    return matches[-1] if matches else None


def _latest_pending_choice_created_event(
    evidence: dict[str, Any],
) -> dict[str, Any] | None:
    matches = []
    for event in _events(evidence):
        progress_kind = str(_get(event, "payload", "progress_kind") or "")
        if progress_kind == "pending_choice_created":
            matches.append(event)
    return matches[-1] if matches else None


def _latest_pending_choice_execution_started(
    evidence: dict[str, Any],
) -> dict[str, Any] | None:
    choice_event = _latest_pending_choice_created_event(evidence)
    matches = [
        event
        for event in _events_after(evidence, choice_event)
        if event.get("type") == "chat_execution_started"
    ]
    if matches:
        return matches[-1]
    matches = [
        event
        for event in _events(evidence)
        if event.get("type") == "chat_execution_started"
    ]
    return matches[-1] if matches else None


def _latest_planner_candidates_generated_event(
    evidence: dict[str, Any],
) -> dict[str, Any] | None:
    matches = []
    for event in _events(evidence):
        if _get(event, "payload", "progress_kind") == "planner_candidates_generated":
            matches.append(event)
    return matches[-1] if matches else None


def _latest_planner_choice_created_event(
    evidence: dict[str, Any],
) -> dict[str, Any] | None:
    matches = []
    for event in _events(evidence):
        if _get(event, "payload", "progress_kind") == "planner_choice_created":
            matches.append(event)
    return matches[-1] if matches else None


def _latest_planner_choice_selected_event(
    evidence: dict[str, Any],
) -> dict[str, Any] | None:
    matches = []
    for event in _events(evidence):
        if _get(event, "payload", "progress_kind") == "planner_choice_selected":
            matches.append(event)
    return matches[-1] if matches else None


def _latest_execution_started_for_item(
    evidence: dict[str, Any],
    item_name: str,
) -> dict[str, Any] | None:
    matches = [
        event
        for event in _events(evidence)
        if event.get("type") == "chat_execution_started"
        and _get(event, "payload", "slot_overrides", "item_name") == item_name
    ]
    if matches:
        return matches[-1]
    matches = [
        event
        for event in _events(evidence)
        if event.get("type") == "chat_execution_started"
    ]
    return matches[-1] if matches else None


def _latest_learned_path_id(evidence: dict[str, Any]) -> str | None:
    events = [
        event
        for event in _events(evidence)
        if event.get("type") == "chat_learning_completed"
    ]
    for event in reversed(events):
        learned_path_id = _get(event, "payload", "new_learned_path_id")
        if learned_path_id:
            return str(learned_path_id)
    history_runs = _get(evidence, "history", "learning_runs") or []
    for run in reversed(history_runs):
        if isinstance(run, dict) and run.get("learned_path_id"):
            return str(run["learned_path_id"])
    return None


def _learned_path_ids(events: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for event in events:
        for key in ("new_learned_path_id", "learned_path_id"):
            value = _get(event, "payload", key)
            if value:
                ids.append(str(value))
        replay_id = _get(event, "payload", "replay", "learned_path_id")
        if replay_id:
            ids.append(str(replay_id))
    return list(dict.fromkeys(ids))


def _latest_learned_path_detail(evidence: dict[str, Any]) -> dict[str, Any] | None:
    paths = evidence.get("learned_paths") or []
    if paths:
        return paths[-1]
    return None


def _pending_choice_public_choice_ids(evidence: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for payload in _pending_choice_public_payloads(evidence):
        choices = payload.get("choices") if isinstance(payload, dict) else None
        for choice in choices or []:
            if isinstance(choice, dict) and choice.get("choice_id"):
                ids.append(str(choice["choice_id"]))
    return list(dict.fromkeys(ids))


def _pending_choice_public_payloads(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    metadata_pending = _get(evidence, "session", "metadata", "pending_choice")
    if isinstance(metadata_pending, dict):
        payloads.append(metadata_pending)
    history_pending = _get(evidence, "history", "session", "metadata", "pending_choice")
    if isinstance(history_pending, dict):
        payloads.append(history_pending)
    for event in _events(evidence):
        progress_kind = str(_get(event, "payload", "progress_kind") or "")
        if progress_kind == "eval_candidate_setup_applied":
            payload = event.get("payload")
            if isinstance(payload, dict):
                payloads.append(payload)
            continue
        if progress_kind not in {"pending_choice_created", "pending_choice_retry"}:
            continue
        pending = _get(event, "payload", "pending_choice")
        if isinstance(pending, dict):
            payloads.append(pending)
        choices = _get(event, "payload", "choices")
        if isinstance(choices, list):
            payloads.append({"choices": choices})
    history_events = _get(evidence, "history", "events") or []
    for event in history_events if isinstance(history_events, list) else []:
        progress_kind = str(_get(event, "payload", "progress_kind") or "")
        if progress_kind == "eval_candidate_setup_applied":
            payload = event.get("payload")
            if isinstance(payload, dict):
                payloads.append(payload)
            continue
        if progress_kind not in {"pending_choice_created", "pending_choice_retry"}:
            continue
        pending = _get(event, "payload", "pending_choice")
        if isinstance(pending, dict):
            payloads.append(pending)
    return payloads


def _pending_choice_public_surface(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "messages": evidence.get("messages") or [],
        "pending_choice_payloads": _pending_choice_public_payloads(evidence),
    }


def _planner_public_surface(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "messages": evidence.get("messages") or [],
        "session_pending_choice": _get(
            evidence, "session", "metadata", "pending_choice"
        ),
        "history_pending_choice": _get(
            evidence,
            "history",
            "session",
            "metadata",
            "pending_choice",
        ),
        "planner_events": _planner_safety_events(evidence),
    }


def _planner_safety_events(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for event in _events(evidence):
        progress_kind = str(_get(event, "payload", "progress_kind") or "")
        if (
            progress_kind.startswith("planner_")
            or progress_kind == "eval_candidate_setup_applied"
        ):
            events.append(event)
    history_events = _get(evidence, "history", "events") or []
    for event in history_events if isinstance(history_events, list) else []:
        progress_kind = str(_get(event, "payload", "progress_kind") or "")
        if (
            progress_kind.startswith("planner_")
            or progress_kind == "eval_candidate_setup_applied"
        ):
            events.append(event)
    return events


def _planner_signal_count(evidence: dict[str, Any], key: str) -> int:
    values: list[int] = []
    for event in _planner_safety_events(evidence):
        value = _get(event, "payload", key)
        if isinstance(value, int):
            values.append(value)
    return max(values) if values else 0


def _setup_choice_path_id(evidence: dict[str, Any], choice_id: str) -> str | None:
    for candidate in _setup_candidates(evidence):
        if candidate.get("choice_id") == choice_id and candidate.get("learned_path_id"):
            return str(candidate["learned_path_id"])
    return None


def _setup_choice_alias(evidence: dict[str, Any], choice_id: str) -> str | None:
    for candidate in _setup_candidates(evidence):
        if candidate.get("choice_id") == choice_id and candidate.get("alias"):
            return str(candidate["alias"])
    return None


def _setup_candidates(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    manifest = evidence.get("setup_manifest")
    if not isinstance(manifest, dict):
        return []
    return [
        candidate
        for candidate in manifest.get("candidates") or []
        if isinstance(candidate, dict)
    ]


def _stable_hash(value: Any) -> str:
    if value is None:
        return "sha256:none"
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]
    return f"sha256:{digest}"


def _session_learned_actions(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    history_actions = _get(evidence, "history", "learned_actions")
    if isinstance(history_actions, list):
        return history_actions
    metadata_actions = _get(evidence, "session", "metadata", "learned_actions")
    if isinstance(metadata_actions, list):
        return metadata_actions
    raw_actions = _get(evidence, "history", "raw", "learned_actions")
    return raw_actions if isinstance(raw_actions, list) else []


def _execution_evidence_items(event: dict[str, Any] | None) -> list[dict[str, Any]]:
    if event is None:
        return []
    items = _get(event, "payload", "replay", "execution_evidence")
    if isinstance(items, list):
        return items
    items = _get(event, "payload", "execution_evidence")
    return items if isinstance(items, list) else []


def _latest_agent_message(evidence: dict[str, Any]) -> str:
    messages = evidence.get("messages") or []
    for message in reversed(messages):
        if isinstance(message, dict) and message.get("role") in {"agent", "engine"}:
            return str(message.get("content") or "")
    history_messages = _get(evidence, "history", "messages") or []
    for message in reversed(history_messages):
        if isinstance(message, dict) and message.get("role") in {"agent", "engine"}:
            return str(message.get("content") or "")
    return ""


def _find_key_values(value: Any, key: str) -> list[Any]:
    matches: list[Any] = []
    if isinstance(value, dict):
        for current_key, current_value in value.items():
            if current_key == key:
                matches.append(current_value)
            matches.extend(_find_key_values(current_value, key))
    elif isinstance(value, list):
        for item in value:
            matches.extend(_find_key_values(item, key))
    return matches


def main(argv: list[str] | None = None) -> int:
    config = parse_config(argv)
    result = run_eval(config)
    try:
        artifact_path, markdown_path = write_artifacts(result, config)
    except Exception as exc:  # noqa: BLE001 - maps to artifact failure exit
        print(f"status=error artifact_write_failed={exc}", file=sys.stderr)
        return 4
    exit_code = reduce_exit_code([case.status for case in result.case_results])
    print(f"status={result.status}")
    print(f"exit_code={exit_code}")
    print(f"json_artifact={artifact_path}")
    if markdown_path:
        print(f"markdown_result={markdown_path}")
    if result.session_id:
        print(f"session_id={result.session_id}")
    for case in result.case_results:
        print(f"case={case.case_id} status={case.status}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
