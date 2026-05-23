#!/usr/bin/env python3
"""11.3.7 user-facing WAgent behavior eval runner.

This runner is a project eval surface. It drives the Conversation API and
records sanitized operator evidence. It must not call direct replay,
autonomous-run endpoints, or verify-scenario.
"""

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

SCHEMA_VERSION = "11.3.7.1"
URL_ONLY_KNOWN_PAGE = "url_only_known_page"
URL_ONLY_UNKNOWN_PAGE = "url_only_unknown_page"
URL_ONLY_UNKNOWN_CHOOSE_LEARN = "url_only_unknown_choose_learn_starts_learning"
EXECUTE_KNOWN_ACTION = "execute_known_action"
EXECUTE_UNKNOWN_ACTION = "execute_unknown_action"
EXECUTE_UNKNOWN_CHOOSE_LEARN = "execute_unknown_choose_learn_then_execute_or_learning_flow"
VAGUE_INPUT_NO_EXECUTION = "vague_input_no_execution"
FORBIDDEN_TARGET_SCAN_CASE = "forbidden_test_target_not_in_runtime_code_or_prompts"
DEFAULT_CASES = [
    URL_ONLY_KNOWN_PAGE,
    URL_ONLY_UNKNOWN_PAGE,
    URL_ONLY_UNKNOWN_CHOOSE_LEARN,
    EXECUTE_KNOWN_ACTION,
    EXECUTE_UNKNOWN_ACTION,
    EXECUTE_UNKNOWN_CHOOSE_LEARN,
    VAGUE_INPUT_NO_EXECUTION,
    FORBIDDEN_TARGET_SCAN_CASE,
]
ALL_CASES = set(DEFAULT_CASES)

PROHIBITED_AUTONOMOUS_PATH_FRAGMENT = "autonomous" + "-runs"
PROHIBITED_DIRECT_REPLAY_SUFFIX = "/" + "replay"
ALLOWED_OPERATOR_SURFACES = {"cli", "ui"}
CURRENT_SCOPE_STRATEGIES = {"current_eval_session", "current_eval_scope", "explicit_eval_scope"}
UNKNOWN_SCOPE_STRATEGIES = {"fresh_session", "isolated_scope", "explicit_filtered_catalog"}
SENSITIVE_TERMS = {
    "pending_choice_private_map",
    "private_choice_map",
    "private_retry_payload",
    "slot_overrides",
    "evidence_targets",
    "replayaction",
    "replay_action",
    "execution_payload",
    "selector",
    "xpath",
    "learned_path_id",
    "new_learned_path_id",
    "old_learned_path_id",
    "path_id",
    "authorization",
    "cookie",
    "set-cookie",
    "password",
    "credential",
    "access_token",
    "refresh_token",
    "api_key",
    "secret",
    "token",
}
SENSITIVE_KEY_TERMS = tuple(sorted(SENSITIVE_TERMS, key=len, reverse=True))


@dataclass
class EvalConfig:
    api_base: str
    spec_path: Path
    cases: list[str]
    timeout: int
    artifact_dir: Path
    result_dir: Path
    browser_visibility: str
    write_markdown: bool = True


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
class OperatorActionRecord:
    surface: str
    action: str
    command: list[str]
    cwd: str
    started_at: str
    finished_at: str | None = None
    duration_ms: int | None = None
    exit_code: int | None = None


@dataclass
class CaseResult:
    case_id: str
    status: str
    gates: list[GateResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    schema_version: str
    status: str
    environment: dict[str, Any]
    spec: dict[str, Any]
    config: dict[str, Any]
    services: dict[str, Any]
    case_results: list[CaseResult]
    sessions: dict[str, str]
    operator_actions: list[OperatorActionRecord | dict[str, Any]]
    raw_product_client_records: list[dict[str, Any]]
    gate_summary: dict[str, Any]


class EvalBlockedError(RuntimeError):
    pass


class EvalTimeoutError(RuntimeError):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run 11.3.7 user-facing WAgent behavior eval through Conversation API.",
    )
    parser.add_argument("--api-base", default="http://127.0.0.1:8001")
    parser.add_argument(
        "--spec",
        dest="spec_path",
        type=Path,
        default=Path("scripts/evals/specs/wagent_user_behavior_items.json"),
    )
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
        default=Path("artifacts/wagent-user-behavior-eval"),
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
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if raw_argv and raw_argv[0] == "--":
        raw_argv = raw_argv[1:]
    args = build_parser().parse_args(raw_argv)
    cases = _normalize_cases(args.cases)
    return EvalConfig(
        api_base=args.api_base.rstrip("/"),
        spec_path=args.spec_path,
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


def load_spec(path: Path) -> dict[str, Any]:
    spec_path = path if path.is_absolute() else Path.cwd() / path
    return json.loads(spec_path.read_text(encoding="utf-8"))


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _default_http_get(url: str, timeout: float) -> dict[str, Any]:
    response = httpx.get(url, timeout=timeout, follow_redirects=True)
    return {"status_code": response.status_code, "ok": response.status_code < 400}


def run_preflight(
    config: EvalConfig,
    spec: dict[str, Any],
    *,
    http_get: Callable[[str, float], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    get = http_get or _default_http_get
    services: dict[str, Any] = {}
    services["api"] = _check_service(f"{config.api_base}/health", config.timeout, get)
    if not services["api"]["ok"]:
        return {"status": "blocked", "services": services}
    product_url = str(spec.get("product_url") or "")
    services["product"] = _check_service(product_url, config.timeout, get)
    if not services["product"]["ok"]:
        return {"status": "blocked", "services": services}
    return {"status": "pass", "services": services}


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


def run_forbidden_target_scan(spec: dict[str, Any]) -> dict[str, Any]:
    manifest = spec.get("target_manifest")
    if not isinstance(manifest, dict):
        return {
            "status": "blocked",
            "matches": [],
            "match_count": 0,
            "reason": "target_manifest missing from eval spec",
        }
    scan_path = (
        repo_root()
        / ".agents"
        / "skills"
        / "webagentflow-eval-integrity"
        / "scripts"
        / "forbidden_target_scan.py"
    )
    module_spec = importlib.util.spec_from_file_location("forbidden_target_scan", scan_path)
    if module_spec is None or module_spec.loader is None:
        return {
            "status": "blocked",
            "matches": [],
            "match_count": 0,
            "reason": "forbidden target scanner unavailable",
        }
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    try:
        return module.scan(repo_root(), manifest)
    except Exception as exc:  # noqa: BLE001 - invalid scanner setup blocks eval
        return {"status": "blocked", "matches": [], "match_count": 0, "reason": str(exc)}


class ConversationDriver:
    def __init__(self, config: EvalConfig) -> None:
        self.config = config
        self.client = httpx.Client(
            base_url=config.api_base,
            timeout=httpx.Timeout(float(config.timeout)),
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
        payload = {
            "current_mode": "interactive_chat",
            "metadata": {
                "client": "wagent_user_behavior_eval",
                "browser_visibility": self.config.browser_visibility,
                "eval_runner": {
                    "name": "wagent_user_behavior_eval",
                    "schema_version": SCHEMA_VERSION,
                },
                **(metadata or {}),
            },
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
                        "client": "wagent_user_behavior_eval",
                        "browser_visibility": self.config.browser_visibility,
                        **(metadata or {}),
                    },
                },
            )
        except httpx.TimeoutException as exc:
            raise EvalTimeoutError(str(exc)) from exc
        except Exception as exc:
            return TurnRecord(
                text=text,
                started_at=started,
                duration_ms=int((time.perf_counter() - start) * 1000),
                response=None,
                error=str(exc),
            )
        return TurnRecord(
            text=text,
            started_at=started,
            duration_ms=int((time.perf_counter() - start) * 1000),
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

    def collect(
        self,
        session_id: str,
        *,
        turns: list[TurnRecord],
        isolation: dict[str, Any],
        operator_actions: list[OperatorActionRecord],
    ) -> dict[str, Any]:
        return {
            "session": self.get_session(session_id),
            "messages": self.get_messages(session_id),
            "events": self.get_events(session_id),
            "history": self.get_history(session_id),
            "turns": _to_jsonable(turns),
            "isolation": isolation,
            "raw_product_client_records": self.raw_records,
            "operator_actions": _to_jsonable(operator_actions),
        }

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


class UserBehaviorGateEvaluator:
    def evaluate_forbidden_target_scan(self, scan_result: dict[str, Any]) -> CaseResult:
        status = str(scan_result.get("status") or "blocked")
        match_count = int(scan_result.get("match_count") or 0)
        gate_status = "pass" if status == "pass" and match_count == 0 else status
        if gate_status not in {"pass", "blocked"}:
            gate_status = "fail"
        gate = GateResult(
            "forbidden_target_scan",
            True,
            gate_status,
            f"status={status}; match_count={match_count}",
            "webagentflow-eval-integrity forbidden_target_scan",
        )
        return CaseResult(
            FORBIDDEN_TARGET_SCAN_CASE,
            _case_status([gate]),
            [gate],
        )

    def evaluate_url_only_known_page(self, evidence: dict[str, Any]) -> CaseResult:
        gates = [
            _gate_known_scope_isolated(evidence),
            _gate_no_execution_started(evidence),
            _gate_asks_next_step_without_execution(evidence),
            _gate_public_payload_redacted(evidence),
            _gate_no_autonomous_or_direct_replay(evidence),
            _gate_operator_surface_audited(evidence),
        ]
        return CaseResult(URL_ONLY_KNOWN_PAGE, _case_status(gates), gates, _warnings(gates))

    def evaluate_url_only_unknown_page(self, evidence: dict[str, Any]) -> CaseResult:
        gates = [
            _gate_unknown_scope_isolated(evidence),
            _gate_no_execution_started(evidence),
            _gate_unknown_page_guidance(evidence),
            _gate_public_payload_redacted(evidence),
            _gate_no_autonomous_or_direct_replay(evidence),
            _gate_operator_surface_audited(evidence),
        ]
        return CaseResult(URL_ONLY_UNKNOWN_PAGE, _case_status(gates), gates, _warnings(gates))

    def evaluate_url_only_unknown_choose_learn(self, evidence: dict[str, Any]) -> CaseResult:
        gates = [
            _gate_unknown_scope_isolated(evidence),
            _gate_learning_flow_started_or_blocked(evidence),
            _gate_no_autonomous_or_direct_replay(evidence),
            _gate_operator_surface_audited(evidence),
        ]
        return CaseResult(
            URL_ONLY_UNKNOWN_CHOOSE_LEARN,
            _case_status(gates),
            gates,
            _warnings(gates),
        )

    def evaluate_execute_known_action(
        self,
        evidence: dict[str, Any],
        *,
        expected_value: str,
    ) -> CaseResult:
        gates = [
            _gate_known_scope_isolated(evidence),
            _gate_execution_started(evidence),
            _gate_execution_evidence_verified(evidence, expected_value),
            _gate_reporter_verified(evidence),
            _gate_final_response_verified(evidence, expected_value),
            _gate_public_payload_redacted(evidence),
            _gate_no_autonomous_or_direct_replay(evidence),
            _gate_operator_surface_audited(evidence),
        ]
        return CaseResult(EXECUTE_KNOWN_ACTION, _case_status(gates), gates, _warnings(gates))

    def evaluate_execute_unknown_action(self, evidence: dict[str, Any]) -> CaseResult:
        gates = [
            _gate_unknown_scope_isolated(evidence),
            _gate_no_execution_started(evidence),
            _gate_unknown_execute_guidance(evidence),
            _gate_public_payload_redacted(evidence),
            _gate_no_autonomous_or_direct_replay(evidence),
            _gate_operator_surface_audited(evidence),
        ]
        return CaseResult(EXECUTE_UNKNOWN_ACTION, _case_status(gates), gates, _warnings(gates))

    def evaluate_execute_unknown_choose_learn(self, evidence: dict[str, Any]) -> CaseResult:
        gates = [
            _gate_unknown_scope_isolated(evidence),
            _gate_learning_flow_started_or_blocked(evidence),
            _gate_full_learn_then_execute_or_follow_up(evidence),
            _gate_no_autonomous_or_direct_replay(evidence),
            _gate_operator_surface_audited(evidence),
        ]
        return CaseResult(
            EXECUTE_UNKNOWN_CHOOSE_LEARN,
            _case_status(gates),
            gates,
            _warnings(gates),
        )

    def evaluate_vague_input_no_execution(self, evidence: dict[str, Any]) -> CaseResult:
        gates = [
            _gate_no_execution_started(evidence),
            _gate_no_learning_started(evidence),
            _gate_clarifies_target_or_goal(evidence),
            _gate_public_payload_redacted(evidence),
            _gate_no_autonomous_or_direct_replay(evidence),
            _gate_operator_surface_audited(evidence),
        ]
        return CaseResult(
            VAGUE_INPUT_NO_EXECUTION,
            _case_status(gates),
            gates,
            _warnings(gates),
        )


def _gate_known_scope_isolated(evidence: dict[str, Any]) -> GateResult:
    isolation = evidence.get("isolation") or {}
    strategy = str(isolation.get("strategy") or "")
    count = int(isolation.get("learned_action_count") or 0)
    source = str(isolation.get("source") or "")
    if strategy in CURRENT_SCOPE_STRATEGIES and count > 0 and source == "current_eval_scope":
        return GateResult(
            "known_scope_isolated",
            True,
            "pass",
            f"strategy={strategy}; learned_action_count={count}; source={source}",
            "isolation",
        )
    return GateResult(
        "known_scope_isolated",
        True,
        "blocked",
        (
            f"strategy={strategy or 'missing'}; learned_action_count={count}; "
            f"source={source or 'missing'}"
        ),
        "isolation",
    )


def _gate_unknown_scope_isolated(evidence: dict[str, Any]) -> GateResult:
    isolation = evidence.get("isolation") or {}
    strategy = str(isolation.get("strategy") or "")
    count = int(isolation.get("learned_action_count") or 0)
    source = str(isolation.get("source") or "")
    if strategy in UNKNOWN_SCOPE_STRATEGIES and count == 0 and source == "isolated_scope":
        return GateResult(
            "unknown_scope_isolated",
            True,
            "pass",
            f"strategy={strategy}; learned_action_count=0; source={source}",
            "isolation",
        )
    return GateResult(
        "unknown_scope_isolated",
        True,
        "blocked",
        (
            f"strategy={strategy or 'missing'}; learned_action_count={count}; "
            f"source={source or 'missing'}"
        ),
        "isolation",
    )


def _gate_no_execution_started(evidence: dict[str, Any]) -> GateResult:
    if _has_event(evidence, "chat_execution_started"):
        return GateResult(
            "no_execution_started",
            True,
            "fail",
            "chat_execution_started observed",
            "events",
        )
    return GateResult(
        "no_execution_started",
        True,
        "pass",
        "no chat_execution_started event observed",
        "events",
    )


def _gate_no_learning_started(evidence: dict[str, Any]) -> GateResult:
    if _has_event(evidence, "chat_learning_started"):
        return GateResult(
            "no_learning_started",
            True,
            "fail",
            "chat_learning_started observed",
            "events",
        )
    return GateResult(
        "no_learning_started",
        True,
        "pass",
        "no chat_learning_started event observed",
        "events",
    )


def _gate_asks_next_step_without_execution(evidence: dict[str, Any]) -> GateResult:
    response = _latest_user_response(evidence)
    has_prompt = ("你想" in response or "要" in response) and (
        "学习" in response or "执行" in response or "操作" in response
    )
    if has_prompt and not _has_event(evidence, "chat_execution_started"):
        return GateResult(
            "asks_next_step_without_execution",
            True,
            "pass",
            "response asks for next learn/execute operation without execution",
            "message/events",
        )
    return GateResult(
        "asks_next_step_without_execution",
        True,
        "fail",
        "URL-only known response did not ask for next operation safely",
        "message/events",
    )


def _gate_unknown_page_guidance(evidence: dict[str, Any]) -> GateResult:
    response = _latest_user_response(evidence)
    says_unknown = any(marker in response for marker in ("没学过", "未学过", "还没学过"))
    offers_next = "学习" in response and any(
        marker in response for marker in ("取消", "查看", "inspect", "检查", "学习")
    )
    if says_unknown and offers_next:
        return GateResult(
            "unknown_page_guidance",
            True,
            "pass",
            "response says page/action is not learned and offers a learning path",
            "message",
        )
    return GateResult(
        "unknown_page_guidance",
        True,
        "fail",
        "unknown page response must say not learned and ask whether to learn/inspect/cancel",
        "message",
    )


def _gate_unknown_execute_guidance(evidence: dict[str, Any]) -> GateResult:
    response = _latest_user_response(evidence)
    says_unknown = any(marker in response for marker in ("没学过", "未学过", "还没学过"))
    asks_learning = "学习" in response
    if says_unknown and asks_learning and not _has_event(evidence, "chat_execution_started"):
        return GateResult(
            "unknown_execute_guidance",
            True,
            "pass",
            "response blocks execution and prompts learning first",
            "message/events",
        )
    return GateResult(
        "unknown_execute_guidance",
        True,
        "fail",
        "execute-unknown response must block replay and prompt learning",
        "message/events",
    )


def _gate_learning_flow_started_or_blocked(evidence: dict[str, Any]) -> GateResult:
    if _has_event(evidence, "chat_learning_started"):
        return GateResult(
            "learning_flow_started",
            True,
            "pass",
            "chat_learning_started event observed",
            "events",
        )
    if _has_event(evidence, "chat_learning_failed") or (
        "学习失败" in _latest_user_response(evidence)
    ):
        return GateResult(
            "learning_flow_started",
            True,
            "blocked",
            "product returned a reviewable learning failure state",
            "events/message",
        )
    return GateResult(
        "learning_flow_started",
        True,
        "fail",
        "learn choice did not start a learning flow or return product-level blocked state",
        "events/message",
    )


def _gate_execution_started(evidence: dict[str, Any]) -> GateResult:
    if _has_event(evidence, "chat_execution_started"):
        return GateResult(
            "execution_started",
            True,
            "pass",
            "chat_execution_started event observed",
            "events",
        )
    return GateResult(
        "execution_started",
        True,
        "fail",
        "chat_execution_started missing",
        "events",
    )


def _gate_execution_evidence_verified(evidence: dict[str, Any], expected_value: str) -> GateResult:
    for item in _execution_evidence_items(evidence):
        if (
            item.get("kind") == "dom_text_present"
            and item.get("target") == expected_value
            and item.get("status") == "verified"
        ):
            return GateResult(
                "execution_evidence_verified",
                True,
                "pass",
                f"dom_text_present verified target={expected_value}",
                "events",
            )
    return GateResult(
        "execution_evidence_verified",
        True,
        "fail",
        f"verified dom_text_present evidence for {expected_value} missing",
        "events",
    )


def _gate_reporter_verified(evidence: dict[str, Any]) -> GateResult:
    for event in reversed(_events(evidence)):
        if event.get("type") != "task_result_reported":
            continue
        outcome = _get(event, "payload", "verification_outcome")
        if outcome == "verified" or _get(event, "payload", "task_verified") is True:
            return GateResult(
                "reporter_verified",
                True,
                "pass",
                "task_result_reported verification_outcome=verified",
                "events",
            )
        return GateResult(
            "reporter_verified",
            True,
            "fail",
            f"expected reporter verified outcome, got {outcome}",
            "events",
        )
    return GateResult(
        "reporter_verified",
        True,
        "fail",
        "task_result_reported event missing",
        "events",
    )


def _gate_final_response_verified(evidence: dict[str, Any], expected_value: str) -> GateResult:
    response = _latest_user_response(evidence)
    if expected_value in response and any(
        marker in response for marker in ("确认", "完成", "verified")
    ):
        return GateResult(
            "final_response_verified",
            True,
            "pass",
            f"final response references expected value {expected_value}",
            "message",
        )
    return GateResult(
        "final_response_verified",
        True,
        "fail",
        f"final response does not verify expected value {expected_value}",
        "message",
    )


def _gate_full_learn_then_execute_or_follow_up(evidence: dict[str, Any]) -> GateResult:
    if _has_event(evidence, "chat_execution_started") and _reporter_verified(evidence):
        return GateResult(
            "full_learn_then_execute",
            False,
            "pass",
            "learning was followed by verified execution",
            "events",
        )
    return GateResult(
        "full_learn_then_execute",
        False,
        "follow_up",
        "full learn-then-execute not observed; staged learning-flow result only",
        "events",
    )


def _gate_clarifies_target_or_goal(evidence: dict[str, Any]) -> GateResult:
    response = _latest_user_response(evidence)
    if any(marker in response for marker in ("URL", "页面", "操作", "说明", "提供")):
        return GateResult(
            "clarifies_target_or_goal",
            True,
            "pass",
            "response asks user to provide page or operation target",
            "message",
        )
    return GateResult(
        "clarifies_target_or_goal",
        True,
        "fail",
        "vague input response did not clarify page or operation target",
        "message",
    )


def _gate_public_payload_redacted(evidence: dict[str, Any]) -> GateResult:
    public_surface = {
        "messages": evidence.get("messages") or [],
        "session_metadata": _get(evidence, "session", "metadata") or {},
        "events": evidence.get("events") or [],
    }
    leak = _first_sensitive_term(public_surface)
    if leak is None:
        return GateResult(
            "public_payload_redacted",
            True,
            "pass",
            "public messages/session/events contain no private payload terms",
            "messages/session/events",
        )
    return GateResult(
        "public_payload_redacted",
        True,
        "fail",
        f"sensitive term observed: {_stable_hash(leak)}",
        "messages/session/events",
    )


def _gate_no_autonomous_or_direct_replay(evidence: dict[str, Any]) -> GateResult:
    records = evidence.get("raw_product_client_records") or []
    for record in records if isinstance(records, list) else []:
        path = str(record.get("path") or "") if isinstance(record, dict) else ""
        if PROHIBITED_AUTONOMOUS_PATH_FRAGMENT in path or (
            "learned-paths/" in path and path.rstrip("/").endswith(PROHIBITED_DIRECT_REPLAY_SUFFIX)
        ):
            return GateResult(
                "no_autonomous_or_direct_replay",
                True,
                "fail",
                f"prohibited request path observed: {path}",
                "raw_product_client_records",
            )
    return GateResult(
        "no_autonomous_or_direct_replay",
        True,
        "pass",
        "request log contains no autonomous-run or direct replay endpoint",
        "raw_product_client_records",
    )


def _gate_operator_surface_audited(evidence: dict[str, Any]) -> GateResult:
    actions = evidence.get("operator_actions") or []
    if not isinstance(actions, list) or not actions:
        return GateResult(
            "operator_surface_audited",
            True,
            "fail",
            "operator action log missing",
            "operator_actions",
        )
    disallowed: list[str] = []
    surfaces: list[str] = []
    for raw in actions:
        action = _to_jsonable(raw)
        if not isinstance(action, dict):
            disallowed.append(type(raw).__name__)
            continue
        surface = str(action.get("surface") or "")
        action_name = str(action.get("action") or "")
        surfaces.append(surface or "missing")
        if surface not in ALLOWED_OPERATOR_SURFACES:
            disallowed.append(surface or "missing")
        if action_name in {"direct_api", "direct_replay", "post_autonomous_run"}:
            disallowed.append(action_name)
    if disallowed:
        return GateResult(
            "operator_surface_audited",
            True,
            "fail",
            f"disallowed operator surface/action observed: {', '.join(disallowed)}",
            "operator_actions",
        )
    return GateResult(
        "operator_surface_audited",
        True,
        "pass",
        f"allowed operator surfaces: {', '.join(sorted(set(surfaces)))}",
        "operator_actions",
    )


def _has_event(evidence: dict[str, Any], event_type: str) -> bool:
    return any(event.get("type") == event_type for event in _events(evidence))


def _events(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    events = evidence.get("events") or []
    return [event for event in events if isinstance(event, dict)]


def _execution_evidence_items(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for event in _events(evidence):
        if event.get("type") != "chat_execution_completed":
            continue
        for raw in (
            _get(event, "payload", "replay", "execution_evidence")
            or _get(event, "payload", "execution_evidence")
            or []
        ):
            if isinstance(raw, dict):
                items.append(raw)
    return items


def _reporter_verified(evidence: dict[str, Any]) -> bool:
    for event in _events(evidence):
        if event.get("type") == "task_result_reported" and (
            _get(event, "payload", "verification_outcome") == "verified"
            or _get(event, "payload", "task_verified") is True
        ):
            return True
    return False


def _latest_user_response(evidence: dict[str, Any]) -> str:
    turns = evidence.get("turns") or []
    for turn in reversed(turns if isinstance(turns, list) else []):
        response = _get(turn, "response", "user_response")
        if response:
            return str(response)
    messages = evidence.get("messages") or []
    for message in reversed(messages if isinstance(messages, list) else []):
        if isinstance(message, dict) and message.get("role") in {"agent", "engine"}:
            return str(message.get("content") or "")
    return ""


def _first_sensitive_term(value: Any) -> str | None:
    text = json.dumps(value, ensure_ascii=False, default=str).lower()
    for term in SENSITIVE_TERMS:
        if term.lower() in text:
            return term
    return None


def _get(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _case_status(gates: list[GateResult]) -> str:
    required = [gate for gate in gates if gate.required]
    if any(gate.status == "timeout" for gate in required):
        return "timeout"
    if any(gate.status == "fail" for gate in required):
        return "fail"
    if any(gate.status == "blocked" for gate in required):
        return "blocked"
    return "pass"


def _warnings(gates: list[GateResult]) -> list[str]:
    return [
        f"{gate.name}: {gate.status} - {gate.evidence}"
        for gate in gates
        if not gate.required and gate.status != "pass"
    ]


def overall_status(case_results: list[CaseResult]) -> str:
    statuses = [case.status for case in case_results]
    if not statuses:
        return "fail"
    if "timeout" in statuses:
        return "timeout"
    if "fail" in statuses:
        return "fail"
    if "blocked" in statuses:
        return "blocked"
    return "pass"


def exit_code_for_status(status: str) -> int:
    return {"pass": 0, "fail": 1, "blocked": 2, "timeout": 3}.get(status, 1)


def _gate_summary(case_results: list[CaseResult]) -> dict[str, Any]:
    required = [gate for case in case_results for gate in case.gates if gate.required]
    return {
        "required_total": len(required),
        "required_passed": sum(1 for gate in required if gate.status == "pass"),
        "required_failed": sum(1 for gate in required if gate.status == "fail"),
        "required_blocked": sum(1 for gate in required if gate.status == "blocked"),
        "warnings": sum(1 for case in case_results for warning in case.warnings if warning),
    }


def run_eval(config: EvalConfig) -> EvalResult:
    started_at = utc_now()
    operator_actions = [_build_cli_operator_action(config, started_at)]
    spec = load_spec(config.spec_path)
    evaluator = UserBehaviorGateEvaluator()
    scan_result = run_forbidden_target_scan(spec)
    case_results = [evaluator.evaluate_forbidden_target_scan(scan_result)]
    environment = {"commit": _git_commit(), "cwd": str(Path.cwd())}
    sessions: dict[str, str] = {}
    raw_records: list[dict[str, Any]] = []
    services: dict[str, Any] = {}
    behavior_cases = [case for case in config.cases if case != FORBIDDEN_TARGET_SCAN_CASE]

    if case_results[0].status != "pass":
        return _build_eval_result(
            config=config,
            spec=spec,
            environment=environment,
            services=services,
            case_results=case_results,
            sessions=sessions,
            raw_records=raw_records,
            operator_actions=operator_actions,
        )

    if not behavior_cases:
        return _build_eval_result(
            config=config,
            spec=spec,
            environment=environment,
            services=services,
            case_results=case_results,
            sessions=sessions,
            raw_records=raw_records,
            operator_actions=operator_actions,
        )

    preflight = run_preflight(config, spec)
    services = preflight["services"]
    if preflight["status"] == "blocked":
        for case_id in behavior_cases:
            case_results.append(_blocked_case(case_id, "API or product test surface unavailable"))
        return _build_eval_result(
            config=config,
            spec=spec,
            environment=environment,
            services=services,
            case_results=case_results,
            sessions=sessions,
            raw_records=raw_records,
            operator_actions=operator_actions,
        )

    driver = ConversationDriver(config)
    try:
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        product_url = str(spec["product_url"])
        values = spec.get("values") or {}
        utterances = spec.get("utterances") or {}

        known_session_id: str | None = None
        known_turns: list[TurnRecord] = []
        known_ready = any(
            case in behavior_cases
            for case in (URL_ONLY_KNOWN_PAGE, EXECUTE_KNOWN_ACTION)
        )
        if known_ready:
            known_session = driver.create_session(
                metadata={"eval_scope_id": f"m11.3.7-known-{stamp}"}
            )
            known_session_id = str(known_session["id"])
            sessions["known"] = known_session_id
            known_turns.extend(
                _send_required_turns(
                    driver,
                    known_session_id,
                    [
                        product_url,
                        _format_utterance(
                            utterances["learn_action"],
                            value=f"{values.get('learn_known', 'KnownA')}-{stamp}",
                            url=product_url,
                        ),
                    ],
                )
            )

        if URL_ONLY_KNOWN_PAGE in behavior_cases:
            if known_session_id is None:
                case_results.append(_blocked_case(URL_ONLY_KNOWN_PAGE, "known setup missing"))
            else:
                turns = list(known_turns)
                turns.extend(_send_required_turns(driver, known_session_id, [product_url]))
                evidence = driver.collect(
                    known_session_id,
                    turns=turns,
                    isolation=_known_isolation(driver, known_session_id),
                    operator_actions=operator_actions,
                )
                case_results.append(evaluator.evaluate_url_only_known_page(evidence))

        if EXECUTE_KNOWN_ACTION in behavior_cases:
            if known_session_id is None:
                case_results.append(_blocked_case(EXECUTE_KNOWN_ACTION, "known setup missing"))
            else:
                expected_value = f"{values.get('execute_known', 'KnownB')}-{stamp}"
                turns = list(known_turns)
                turns.extend(
                    _send_required_turns(
                        driver,
                        known_session_id,
                        [
                            _format_utterance(
                                utterances["execute_known"],
                                value=expected_value,
                                url=product_url,
                            )
                        ],
                    )
                )
                evidence = driver.collect(
                    known_session_id,
                    turns=turns,
                    isolation=_known_isolation(driver, known_session_id),
                    operator_actions=operator_actions,
                )
                case_results.append(
                    evaluator.evaluate_execute_known_action(
                        evidence,
                        expected_value=expected_value,
                    )
                )

        if (
            URL_ONLY_UNKNOWN_PAGE in behavior_cases
            or URL_ONLY_UNKNOWN_CHOOSE_LEARN in behavior_cases
        ):
            unknown_session = driver.create_session(
                metadata={"eval_scope_id": f"m11.3.7-url-unknown-{stamp}"}
            )
            unknown_session_id = str(unknown_session["id"])
            sessions["url_unknown"] = unknown_session_id
            unknown_turns = _send_required_turns(driver, unknown_session_id, [product_url])
            if URL_ONLY_UNKNOWN_PAGE in behavior_cases:
                evidence = driver.collect(
                    unknown_session_id,
                    turns=unknown_turns,
                    isolation=_unknown_isolation(),
                    operator_actions=operator_actions,
                )
                case_results.append(evaluator.evaluate_url_only_unknown_page(evidence))
            if URL_ONLY_UNKNOWN_CHOOSE_LEARN in behavior_cases:
                learn_value = f"{values.get('learn_unknown_url', 'UnknownC')}-{stamp}"
                choose_turns = list(unknown_turns)
                choose_turns.extend(
                    _send_required_turns(
                        driver,
                        unknown_session_id,
                        [
                            _format_utterance(
                                utterances["learn_action"],
                                value=learn_value,
                                url=product_url,
                            )
                        ],
                    )
                )
                evidence = driver.collect(
                    unknown_session_id,
                    turns=choose_turns,
                    isolation=_unknown_isolation(),
                    operator_actions=operator_actions,
                )
                case_results.append(evaluator.evaluate_url_only_unknown_choose_learn(evidence))

        if (
            EXECUTE_UNKNOWN_ACTION in behavior_cases
            or EXECUTE_UNKNOWN_CHOOSE_LEARN in behavior_cases
        ):
            execute_unknown_session = driver.create_session(
                metadata={"eval_scope_id": f"m11.3.7-execute-unknown-{stamp}"}
            )
            execute_unknown_session_id = str(execute_unknown_session["id"])
            sessions["execute_unknown"] = execute_unknown_session_id
            execute_unknown_value = f"{values.get('execute_unknown', 'UnknownD')}-{stamp}"
            unknown_exec_turns = _send_required_turns(
                driver,
                execute_unknown_session_id,
                [
                    _format_utterance(
                        utterances["execute_unknown"],
                        value=execute_unknown_value,
                        url=product_url,
                    )
                ],
            )
            if EXECUTE_UNKNOWN_ACTION in behavior_cases:
                evidence = driver.collect(
                    execute_unknown_session_id,
                    turns=unknown_exec_turns,
                    isolation=_unknown_isolation(),
                    operator_actions=operator_actions,
                )
                case_results.append(evaluator.evaluate_execute_unknown_action(evidence))
            if EXECUTE_UNKNOWN_CHOOSE_LEARN in behavior_cases:
                choose_turns = list(unknown_exec_turns)
                choose_turns.extend(
                    _send_required_turns(
                        driver,
                        execute_unknown_session_id,
                        [
                            _format_utterance(
                                utterances["learn_action"],
                                value=execute_unknown_value,
                                url=product_url,
                            )
                        ],
                    )
                )
                evidence = driver.collect(
                    execute_unknown_session_id,
                    turns=choose_turns,
                    isolation=_unknown_isolation(),
                    operator_actions=operator_actions,
                )
                case_results.append(evaluator.evaluate_execute_unknown_choose_learn(evidence))

        if VAGUE_INPUT_NO_EXECUTION in behavior_cases:
            vague_session = driver.create_session(
                metadata={"eval_scope_id": f"m11.3.7-vague-{stamp}"}
            )
            vague_session_id = str(vague_session["id"])
            sessions["vague"] = vague_session_id
            vague_turns = _send_required_turns(
                driver,
                vague_session_id,
                [str(utterances.get("vague") or "随便搞一下")],
            )
            evidence = driver.collect(
                vague_session_id,
                turns=vague_turns,
                isolation=_unknown_isolation(),
                operator_actions=operator_actions,
            )
            case_results.append(evaluator.evaluate_vague_input_no_execution(evidence))
    except EvalTimeoutError as exc:
        case_results.append(_terminal_case("timeout", str(exc), "runner"))
    except Exception as exc:  # noqa: BLE001 - runner records internal failure
        case_results.append(_terminal_case("blocked", str(exc), "runner"))
    finally:
        raw_records = list(driver.raw_records)
        driver.close()

    return _build_eval_result(
        config=config,
        spec=spec,
        environment=environment,
        services=services,
        case_results=case_results,
        sessions=sessions,
        raw_records=raw_records,
        operator_actions=operator_actions,
    )


def _send_required_turns(
    driver: ConversationDriver,
    session_id: str,
    texts: list[str],
) -> list[TurnRecord]:
    turns: list[TurnRecord] = []
    for text in texts:
        turn = driver.send_turn(session_id, text)
        turns.append(turn)
        if turn.error:
            raise EvalBlockedError(turn.error)
    return turns


def _format_utterance(template: str, *, value: str, url: str) -> str:
    return template.format(value=value, url=url)


def _known_isolation(driver: ConversationDriver, session_id: str) -> dict[str, Any]:
    try:
        session = driver.get_session(session_id)
    except Exception:
        session = {}
    actions = _get(session, "metadata", "learned_actions") or []
    count = len(actions) if isinstance(actions, list) else 0
    return {
        "strategy": "current_eval_session",
        "learned_action_count": count,
        "source": "current_eval_scope",
    }


def _unknown_isolation() -> dict[str, Any]:
    return {
        "strategy": "fresh_session",
        "learned_action_count": 0,
        "source": "isolated_scope",
    }


def _blocked_case(case_id: str, reason: str) -> CaseResult:
    return CaseResult(
        case_id=case_id,
        status="blocked",
        gates=[GateResult("preflight", True, "blocked", reason, "runner")],
    )


def _terminal_case(status: str, evidence: str, source: str) -> CaseResult:
    return CaseResult(
        case_id="runner",
        status=status,
        gates=[GateResult(status, True, status, evidence, source)],
    )


def _build_eval_result(
    *,
    config: EvalConfig,
    spec: dict[str, Any],
    environment: dict[str, Any],
    services: dict[str, Any],
    case_results: list[CaseResult],
    sessions: dict[str, str],
    raw_records: list[dict[str, Any]],
    operator_actions: list[OperatorActionRecord],
) -> EvalResult:
    status = overall_status(case_results)
    return EvalResult(
        schema_version=SCHEMA_VERSION,
        status=status,
        environment=environment,
        spec={
            "target_name": spec.get("target_name"),
            "target_label": spec.get("target_label"),
            "product_url": spec.get("product_url"),
        },
        config=_config_dict(config),
        services=services,
        case_results=case_results,
        sessions=sessions,
        operator_actions=operator_actions,
        raw_product_client_records=raw_records,
        gate_summary=_gate_summary(case_results),
    )


def _config_dict(config: EvalConfig) -> dict[str, Any]:
    return {
        "api_base": config.api_base,
        "spec_path": str(config.spec_path),
        "cases": list(config.cases),
        "timeout": config.timeout,
        "artifact_dir": str(config.artifact_dir),
        "result_dir": str(config.result_dir),
        "browser_visibility": config.browser_visibility,
        "write_markdown": config.write_markdown,
    }


def sanitize_artifact_payload(value: Any) -> Any:
    return _sanitize_value(value)


def _sanitize_value(value: Any) -> Any:
    if is_dataclass(value):
        return _sanitize_value(asdict(value))
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        redacted: list[str] = []
        for key, item in value.items():
            key_str = str(key)
            if _is_sensitive_key(key_str):
                redacted.append(_stable_hash(key_str))
                continue
            clean[key_str] = _sanitize_value(item)
        if redacted:
            clean["_redacted_key_hashes"] = redacted
        return clean
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, str):
        sanitized = value
        for term in SENSITIVE_TERMS:
            if term.lower() in sanitized.lower():
                sanitized = _replace_case_insensitive(sanitized, term, _stable_hash(term))
        return sanitized
    if isinstance(value, Path):
        return str(value)
    return value


def _is_sensitive_key(key: str) -> bool:
    lower = key.lower()
    return any(term in lower for term in SENSITIVE_KEY_TERMS)


def _replace_case_insensitive(text: str, needle: str, replacement: str) -> str:
    lower = text.lower()
    needle_lower = needle.lower()
    result = text
    start = lower.find(needle_lower)
    while start >= 0:
        end = start + len(needle)
        result = result[:start] + replacement + result[end:]
        lower = result.lower()
        start = lower.find(needle_lower, start + len(replacement))
    return result


def write_artifacts(result: EvalResult, config: EvalConfig) -> tuple[Path, Path | None]:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    config.artifact_dir.mkdir(parents=True, exist_ok=True)
    json_path = config.artifact_dir / f"wagent-user-behavior-eval-{timestamp}.json"
    payload = sanitize_artifact_payload(_to_jsonable(result))
    json_text = json.dumps(payload, ensure_ascii=False, indent=2)
    json_path.write_text(json_text + "\n", encoding="utf-8")
    (config.artifact_dir / "wagent-user-behavior-eval-latest.json").write_text(
        json_text + "\n",
        encoding="utf-8",
    )
    markdown_path: Path | None = None
    if config.write_markdown:
        config.result_dir.mkdir(parents=True, exist_ok=True)
        markdown_path = (
            config.result_dir
            / f"m11-11.3.7-user-facing-wagent-behavior-eval-{timestamp}.md"
        )
        markdown = render_markdown_report(result, json_path)
        markdown_path.write_text(markdown, encoding="utf-8")
        (
            config.result_dir
            / "m11-11.3.7-user-facing-wagent-behavior-eval-latest.md"
        ).write_text(markdown, encoding="utf-8")
    return json_path, markdown_path


def render_markdown_report(result: EvalResult, json_path: Path) -> str:
    lines = [
        "# 11.3.7 User-facing WAgent Behavior Eval",
        "",
        f"- Status: `{result.status}`",
        f"- Schema version: `{result.schema_version}`",
        f"- JSON artifact: `{json_path}`",
        f"- Commit: `{result.environment.get('commit')}`",
        "",
        "## Cases",
        "",
        "| Case | Status | Required passed | Required failed | Required blocked |",
        "|---|---:|---:|---:|---:|",
    ]
    for case in result.case_results:
        required = [gate for gate in case.gates if gate.required]
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_escape(case.case_id),
                    f"`{case.status}`",
                    str(sum(1 for gate in required if gate.status == "pass")),
                    str(sum(1 for gate in required if gate.status == "fail")),
                    str(sum(1 for gate in required if gate.status == "blocked")),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Gates", ""])
    for case in result.case_results:
        lines.extend(
            [
                f"### `{case.case_id}`",
                "",
                "| Gate | Required | Status | Evidence | Source |",
                "|---|---:|---:|---|---|",
            ]
        )
        for gate in case.gates:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _md_escape(gate.name),
                        "yes" if gate.required else "no",
                        f"`{gate.status}`",
                        _md_escape(gate.evidence),
                        _md_escape(gate.source),
                    ]
                )
                + " |"
            )
        if case.warnings:
            lines.extend(["", "Warnings:"])
            lines.extend(f"- {_md_escape(warning)}" for warning in case.warnings)
        lines.append("")
    lines.extend(
        [
            "## Boundary",
            "",
            "- Surface: project eval CLI via Conversation API.",
            "- Not run: verify-scenario, autonomous-run endpoints, Console UI smoke.",
            "- Direct replay API is prohibited and checked from the product-client request log.",
            "",
        ]
    )
    return "\n".join(lines)


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


def _build_cli_operator_action(config: EvalConfig, started_at: str) -> OperatorActionRecord:
    return OperatorActionRecord(
        surface="cli",
        action="run_wagent_user_behavior_eval",
        command=list(sys.argv),
        cwd=str(Path.cwd()),
        started_at=started_at,
    )


def _finalize_cli_operator_action(
    result: EvalResult,
    *,
    started_at: str,
    duration_ms: int,
    exit_code: int,
) -> None:
    if not result.operator_actions:
        result.operator_actions.append(
            OperatorActionRecord(
                surface="cli",
                action="run_wagent_user_behavior_eval",
                command=list(sys.argv),
                cwd=str(Path.cwd()),
                started_at=started_at,
            )
        )
    first = result.operator_actions[0]
    if isinstance(first, OperatorActionRecord):
        first.finished_at = utc_now()
        first.duration_ms = duration_ms
        first.exit_code = exit_code
    elif isinstance(first, dict):
        first["finished_at"] = utc_now()
        first["duration_ms"] = duration_ms
        first["exit_code"] = exit_code


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


def _stable_hash(value: Any) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]
    return f"sha256:{digest}"


def _md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def main(argv: list[str] | None = None) -> int:
    started_at = utc_now()
    start = time.perf_counter()
    try:
        config = parse_config(argv)
        result = run_eval(config)
    except EvalTimeoutError as exc:
        config = parse_config(argv)
        result = _build_eval_result(
            config=config,
            spec={},
            environment={"commit": _git_commit(), "cwd": str(Path.cwd())},
            services={},
            case_results=[_terminal_case("timeout", str(exc), "runner")],
            sessions={},
            raw_records=[],
            operator_actions=[_build_cli_operator_action(config, started_at)],
        )
    status = result.status
    exit_code = exit_code_for_status(status)
    _finalize_cli_operator_action(
        result,
        started_at=started_at,
        duration_ms=int((time.perf_counter() - start) * 1000),
        exit_code=exit_code,
    )
    artifact_path, markdown_path = write_artifacts(result, config)
    print(f"status={result.status}")
    print(f"exit_code={exit_code}")
    print(f"json_artifact={artifact_path}")
    if markdown_path is not None:
        print(f"markdown_result={markdown_path}")
    for case in result.case_results:
        print(f"case={case.case_id} status={case.status}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
