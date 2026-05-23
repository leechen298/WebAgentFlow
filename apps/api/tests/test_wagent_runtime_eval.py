"""Unit tests for the 11.3.6.1 WAgent runtime eval runner."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def _load_runner():
    repo_root = Path(__file__).resolve().parents[3]
    runner_path = repo_root / "scripts" / "evals" / "wagent_runtime_eval.py"
    assert runner_path.exists(), "runner script is missing"
    spec = importlib.util.spec_from_file_location("wagent_runtime_eval", runner_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _valid_items_evidence(*, include_evidence_targets: bool = True) -> dict[str, Any]:
    execution_payload: dict[str, Any] = {
        "learned_path_id": "lp-current",
        "target_url": "http://127.0.0.1:5176/items",
        "alias": "新增项目",
        "slot_overrides": {"item_name": "测试项目B"},
    }
    if include_evidence_targets:
        execution_payload["evidence_targets"] = [
            {
                "kind": "dom_text_present",
                "text": "测试项目B",
                "source_slot": "item_name",
                "selector": "[data-testid='item-list']",
            }
        ]

    return {
        "session": {
            "id": "session-1",
            "metadata": {
                "pending_target": {"url": "http://127.0.0.1:5176/items"},
                "learned_actions": [
                    {
                        "alias": "新增项目",
                        "learned_path_id": "lp-current",
                        "target_url": "http://127.0.0.1:5176/items",
                    }
                ],
            },
        },
        "events": [
            {
                "id": "evt-learn",
                "type": "chat_learning_completed",
                "payload": {
                    "run_id": "run-1",
                    "new_learned_path_id": "lp-current",
                    "target_url": "http://127.0.0.1:5176/items",
                    "alias": "新增项目",
                },
            },
            {
                "id": "evt-start-b",
                "type": "chat_execution_started",
                "payload": execution_payload,
            },
            {
                "id": "evt-complete-b",
                "type": "chat_execution_completed",
                "payload": {
                    "learned_path_id": "lp-current",
                    "replay": {
                        "learned_path_id": "lp-current",
                        "replay_status": "succeeded",
                        "execution_evidence": [
                            {
                                "kind": "dom_text_present",
                                "target": "测试项目B",
                                "status": "verified",
                                "confidence": 0.95,
                                "summary": "列表中包含测试项目B",
                            }
                        ],
                    },
                },
            },
            {
                "id": "evt-report-b",
                "type": "task_result_reported",
                "payload": {
                    "verification_outcome": "verified",
                    "task_verified": True,
                },
            },
        ],
        "messages": [
            {
                "role": "agent",
                "content": "执行完成。我在列表中看到了“测试项目B”，所以可以确认新增项目成功。",
            }
        ],
        "history": {},
        "learned_path_detail": {
            "id": "lp-current",
            "actions": [{"step": 1, "action_type": "fill", "value_slot": "item_name"}],
        },
    }


def _valid_failure_recovery_evidence() -> dict[str, Any]:
    return {
        "session": {
            "id": "session-1",
            "metadata": {
                "pending_choice": {
                    "type": "pending_choice",
                    "choices": [
                        {
                            "choice_id": "A",
                            "label": "重试执行该操作",
                            "description": "重试会再次执行该操作，可能重复新增 / 提交。",
                        },
                        {"choice_id": "B", "label": "重新学习"},
                        {"choice_id": "C", "label": "取消"},
                    ],
                }
            },
        },
        "events": [
            {
                "id": "evt-happy-report",
                "type": "task_result_reported",
                "payload": {
                    "verification_outcome": "verified",
                    "task_verified": True,
                },
            },
            {
                "id": "evt-hook",
                "type": "chat_progress_recorded",
                "payload": {
                    "progress_kind": "eval_fault_injection_applied",
                    "case_id": "failure_recovery_menu_safety",
                    "fault_class": "needs_review",
                },
            },
            {
                "id": "evt-failed",
                "type": "chat_execution_failed",
                "payload": {
                    "failure_class": "needs_review",
                    "replay": {"replay_status": "succeeded"},
                },
            },
            {
                "id": "evt-reported",
                "type": "task_result_reported",
                "payload": {
                    "verification_outcome": "needs_review",
                    "needs_review": True,
                },
            },
            {
                "id": "evt-recovery",
                "type": "chat_progress_recorded",
                "payload": {
                    "progress_kind": "failure_recovery_offered",
                    "failure_class": "needs_review",
                    "choice_group_id": "choice-group-1",
                    "retry_count": 0,
                    "choices": [
                        {
                            "choice_id": "A",
                            "label": "重试执行该操作",
                            "description": "重试会再次执行该操作，可能重复新增 / 提交。",
                        },
                        {"choice_id": "B", "label": "重新学习"},
                        {"choice_id": "C", "label": "取消"},
                    ],
                    "action_alias": "新增项目",
                },
            },
        ],
        "messages": [
            {
                "role": "agent",
                "content": "执行完成。我在列表中看到了“测试项目B”，所以可以确认新增项目成功。",
            },
            {
                "role": "agent",
                "content": (
                    "执行中。\n操作执行后，我没有在列表中确认看到“测试项目D”。"
                    "可能页面更新较慢，也可能操作没有成功。\n"
                    "你可以选择：\n"
                    "A. 重试执行该操作 - 重试会再次执行该操作，可能重复新增 / 提交。\n"
                    "B. 重新学习\n"
                    "C. 取消"
                ),
            },
        ],
        "history": {},
        "raw_api_responses": {
            "records": [
                {"method": "POST", "path": "/conversation/sessions"},
                {
                    "method": "POST",
                    "path": "/conversation/sessions/session-1/dispatch",
                },
            ]
        },
    }


def test_parse_config_defaults() -> None:
    runner = _load_runner()

    config = runner.parse_config([])

    assert config.api_base == "http://127.0.0.1:8001"
    assert config.product_url == "http://127.0.0.1:5176/items"
    assert config.cases == [
        "items_closed_loop",
        "single_path_direct_replay_regression",
    ]
    assert config.timeout == 300
    assert config.artifact_dir == Path("artifacts/wagent-eval")
    assert config.result_dir == Path("docs/testing/results")
    assert config.browser_visibility == "headless"


def test_parse_config_accepts_failure_recovery_case() -> None:
    runner = _load_runner()

    config = runner.parse_config(["--case", "failure_recovery_menu_safety"])

    assert config.cases == ["failure_recovery_menu_safety"]


def test_preflight_blocks_when_api_unreachable() -> None:
    runner = _load_runner()
    config = runner.parse_config(["--api-base", "http://127.0.0.1:9"])

    def fake_get(url: str, timeout: float) -> dict[str, Any]:
        raise TimeoutError(f"cannot reach {url} within {timeout}")

    result = runner.run_preflight(config, http_get=fake_get)

    assert result.status == "blocked"
    assert result.exit_code == 2
    assert result.services["api"]["ok"] is False
    assert "cannot reach" in result.services["api"]["error"]


def test_preflight_blocks_when_product_site_unreachable() -> None:
    runner = _load_runner()
    config = runner.parse_config([])

    def fake_get(url: str, timeout: float) -> dict[str, Any]:
        if url.endswith("/health"):
            return {"status_code": 200, "ok": True}
        raise OSError("product unavailable")

    result = runner.run_preflight(config, http_get=fake_get)

    assert result.status == "blocked"
    assert result.exit_code == 2
    assert result.services["api"]["ok"] is True
    assert result.services["product"]["ok"] is False
    assert result.services["product"]["error"] == "product unavailable"


def test_items_gate_passes_with_valid_structured_evidence() -> None:
    runner = _load_runner()
    evidence = _valid_items_evidence()

    result = runner.GateEvaluator().evaluate_items_closed_loop(
        evidence,
        expected_item_name="测试项目B",
    )

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "pass"
    assert gates["learned_path_created"].status == "pass"
    assert gates["learned_path_parameterized"].status == "pass"
    assert gates["slot_override_B"].status == "pass"
    assert gates["evidence_target_item_list"].status == "pass"
    assert gates["dom_evidence_verified_B"].status == "pass"
    assert gates["reporter_verified"].status == "pass"
    assert gates["final_response_verified"].status == "pass"


def test_items_gate_fails_when_required_reporter_evidence_missing() -> None:
    runner = _load_runner()
    evidence = _valid_items_evidence()
    evidence["events"] = [
        event for event in evidence["events"] if event["type"] != "task_result_reported"
    ]

    result = runner.GateEvaluator().evaluate_items_closed_loop(
        evidence,
        expected_item_name="测试项目B",
    )

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "fail"
    assert gates["reporter_verified"].status == "fail"


def test_items_gate_marks_effective_value_unobservable_without_guessing() -> None:
    runner = _load_runner()
    evidence = _valid_items_evidence()

    result = runner.GateEvaluator().evaluate_items_closed_loop(
        evidence,
        expected_item_name="测试项目B",
    )

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "pass"
    assert gates["effective_value_B"].required is False
    assert gates["effective_value_B"].status == "not_observable"
    assert "not exposed" in gates["effective_value_B"].evidence


def test_items_gate_does_not_infer_selector_from_execution_evidence() -> None:
    runner = _load_runner()
    evidence = _valid_items_evidence(include_evidence_targets=False)
    evidence["events"][2]["payload"]["replay"]["execution_evidence"][0]["selector"] = (
        "[data-testid='item-list']"
    )

    result = runner.GateEvaluator().evaluate_items_closed_loop(
        evidence,
        expected_item_name="测试项目B",
    )

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "pass"
    assert gates["evidence_target_item_list"].required is False
    assert gates["evidence_target_item_list"].status == "not_observable"
    assert gates["dom_evidence_verified_B"].status == "pass"


def test_items_gate_accepts_history_side_evidence_targets() -> None:
    runner = _load_runner()
    evidence = _valid_items_evidence(include_evidence_targets=False)
    evidence["history"] = {
        "replay_summaries": [
            {
                "raw": {
                    "evidence_targets": [
                        {
                            "kind": "dom_text_present",
                            "text": "测试项目B",
                            "selector": "[data-testid='item-list']",
                        }
                    ]
                }
            }
        ]
    }

    result = runner.GateEvaluator().evaluate_items_closed_loop(
        evidence,
        expected_item_name="测试项目B",
    )

    gates = {gate.name: gate for gate in result.gates}
    assert gates["evidence_target_item_list"].status == "pass"
    assert gates["evidence_target_item_list"].source == "events/history"


def test_single_path_regression_ignores_old_global_items_paths() -> None:
    runner = _load_runner()
    evidence = _valid_items_evidence()
    evidence["events"].extend(
        [
            {
                "id": "evt-start-c",
                "type": "chat_execution_started",
                "payload": {
                    "learned_path_id": "lp-current",
                    "target_url": "http://127.0.0.1:5176/items",
                    "alias": "新增项目",
                    "slot_overrides": {"item_name": "测试项目C"},
                },
            },
            {
                "id": "evt-complete-c",
                "type": "chat_execution_completed",
                "payload": {
                    "learned_path_id": "lp-current",
                    "replay": {
                        "learned_path_id": "lp-current",
                        "replay_status": "succeeded",
                        "execution_evidence": [
                            {
                                "kind": "dom_text_present",
                                "target": "测试项目C",
                                "status": "verified",
                                "confidence": 0.95,
                                "summary": "列表中包含测试项目C",
                            }
                        ],
                    },
                },
            },
            {
                "id": "evt-report-c",
                "type": "task_result_reported",
                "payload": {
                    "verification_outcome": "verified",
                    "task_verified": True,
                },
            },
        ]
    )
    evidence["messages"].append(
        {
            "role": "agent",
            "content": "执行完成。我在列表中看到了“测试项目C”，所以可以确认新增项目成功。",
        }
    )
    evidence["global_learned_paths"] = [
        {"id": "lp-old-1", "page_template": "/items"},
        {"id": "lp-old-2", "page_template": "/items"},
    ]

    result = runner.GateEvaluator().evaluate_single_path_direct_replay_regression(
        evidence,
        expected_item_name="测试项目C",
        learned_path_id="lp-current",
    )

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "pass"
    assert gates["single_candidate_detected"].status == "pass"
    assert gates["no_pending_choice"].status == "pass"
    assert gates["no_planner_choice"].status == "pass"
    assert gates["slot_override_C"].status == "pass"
    assert gates["dom_evidence_verified_C"].status == "pass"


def test_failure_recovery_gate_passes_with_sanitized_recovery_evidence() -> None:
    runner = _load_runner()
    evidence = _valid_failure_recovery_evidence()

    result = runner.GateEvaluator().evaluate_failure_recovery_menu_safety(evidence)

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "pass"
    assert gates["failure_triggered"].status == "pass"
    assert gates["recovery_menu_shown"].status == "pass"
    assert gates["retry_wording_safe"].status == "pass"
    assert gates["retry_side_effect_warning"].status == "pass"
    assert gates["relearn_option_shown"].status == "pass"
    assert gates["cancel_option_shown"].status == "pass"
    assert gates["private_payload_not_visible"].status == "pass"
    assert gates["recovery_events_sanitized"].status == "pass"
    assert gates["verified_happy_path_no_recovery"].status == "pass"
    assert gates["no_autonomous_or_direct_replay"].status == "pass"


def test_failure_recovery_gate_deduplicates_history_message_echo() -> None:
    runner = _load_runner()
    evidence = _valid_failure_recovery_evidence()
    evidence["history"] = {"messages": list(evidence["messages"])}

    result = runner.GateEvaluator().evaluate_failure_recovery_menu_safety(evidence)

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "pass"
    assert gates["verified_happy_path_no_recovery"].status == "pass"


def test_failure_recovery_gate_fails_for_generic_retry_wording() -> None:
    runner = _load_runner()
    evidence = _valid_failure_recovery_evidence()
    evidence["messages"][-1]["content"] = evidence["messages"][-1]["content"].replace(
        "A. 重试执行该操作",
        "A. 重试",
    )

    result = runner.GateEvaluator().evaluate_failure_recovery_menu_safety(evidence)

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "fail"
    assert gates["retry_wording_safe"].status == "fail"


def test_failure_recovery_gate_fails_when_side_effect_warning_missing() -> None:
    runner = _load_runner()
    evidence = _valid_failure_recovery_evidence()
    evidence["messages"][-1]["content"] = evidence["messages"][-1]["content"].replace(
        " - 重试会再次执行该操作，可能重复新增 / 提交。",
        "",
    )

    result = runner.GateEvaluator().evaluate_failure_recovery_menu_safety(evidence)

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "fail"
    assert gates["retry_side_effect_warning"].status == "fail"


def test_failure_recovery_gate_fails_when_relearn_or_cancel_option_missing() -> None:
    runner = _load_runner()
    evidence = _valid_failure_recovery_evidence()
    evidence["messages"][-1]["content"] = evidence["messages"][-1]["content"].replace(
        "B. 重新学习\nC. 取消",
        "B. 重新学习",
    )

    result = runner.GateEvaluator().evaluate_failure_recovery_menu_safety(evidence)

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "fail"
    assert gates["cancel_option_shown"].status == "fail"


def test_failure_recovery_gate_fails_when_private_payload_visible() -> None:
    runner = _load_runner()
    evidence = _valid_failure_recovery_evidence()
    evidence["messages"][-1]["content"] += "\nlearned_path_id=lp-private"

    result = runner.GateEvaluator().evaluate_failure_recovery_menu_safety(evidence)

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "fail"
    assert gates["private_payload_not_visible"].status == "fail"


def test_failure_recovery_gate_fails_when_recovery_event_leaks_payload() -> None:
    runner = _load_runner()
    evidence = _valid_failure_recovery_evidence()
    evidence["events"][-1]["payload"]["slot_overrides"] = {"item_name": "测试项目D"}

    result = runner.GateEvaluator().evaluate_failure_recovery_menu_safety(evidence)

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "fail"
    assert gates["recovery_events_sanitized"].status == "fail"


def test_failure_recovery_gate_fails_when_eval_hook_event_leaks_payload() -> None:
    runner = _load_runner()
    evidence = _valid_failure_recovery_evidence()
    evidence["events"][1]["payload"]["slot_overrides"] = {"item_name": "测试项目D"}

    result = runner.GateEvaluator().evaluate_failure_recovery_menu_safety(evidence)

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "fail"
    assert gates["recovery_events_sanitized"].status == "fail"


def test_failure_recovery_gate_fails_when_happy_path_has_recovery_menu() -> None:
    runner = _load_runner()
    evidence = _valid_failure_recovery_evidence()
    evidence["messages"][0]["content"] += "\nA. 重试执行该操作\nB. 重新学习\nC. 取消"

    result = runner.GateEvaluator().evaluate_failure_recovery_menu_safety(evidence)

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "fail"
    assert gates["verified_happy_path_no_recovery"].status == "fail"


def test_failure_recovery_gate_fails_when_runner_calls_prohibited_endpoint() -> None:
    runner = _load_runner()
    evidence = _valid_failure_recovery_evidence()
    evidence["raw_api_responses"]["records"].append(
        {"method": "POST", "path": "/exploration/" + "autonomous" + "-runs"}
    )

    result = runner.GateEvaluator().evaluate_failure_recovery_menu_safety(evidence)

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "fail"
    assert gates["no_autonomous_or_direct_replay"].status == "fail"


def test_single_path_regression_fails_when_execution_uses_old_path() -> None:
    runner = _load_runner()
    evidence = _valid_items_evidence()
    evidence["events"].extend(
        [
            {
                "id": "evt-start-c",
                "type": "chat_execution_started",
                "payload": {
                    "learned_path_id": "lp-old",
                    "target_url": "http://127.0.0.1:5176/items",
                    "alias": "新增项目",
                    "slot_overrides": {"item_name": "测试项目C"},
                },
            },
            {
                "id": "evt-complete-c",
                "type": "chat_execution_completed",
                "payload": {
                    "learned_path_id": "lp-old",
                    "replay": {
                        "learned_path_id": "lp-old",
                        "replay_status": "succeeded",
                        "execution_evidence": [
                            {
                                "kind": "dom_text_present",
                                "target": "测试项目C",
                                "status": "verified",
                                "confidence": 0.95,
                                "summary": "列表中包含测试项目C",
                            }
                        ],
                    },
                },
            },
            {
                "id": "evt-report-c",
                "type": "task_result_reported",
                "payload": {
                    "verification_outcome": "verified",
                    "task_verified": True,
                },
            },
        ]
    )
    evidence["messages"].append(
        {
            "role": "agent",
            "content": "执行完成。我在列表中看到了“测试项目C”，所以可以确认新增项目成功。",
        }
    )

    result = runner.GateEvaluator().evaluate_single_path_direct_replay_regression(
        evidence,
        expected_item_name="测试项目C",
        learned_path_id="lp-current",
    )

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "fail"
    assert gates["execution_uses_current_learned_path"].status == "fail"
    assert "lp-old" in gates["execution_uses_current_learned_path"].evidence


def test_evidence_collection_timeout_becomes_timeout_result(monkeypatch) -> None:
    runner = _load_runner()
    config = runner.parse_config(["--case", "items_closed_loop"])

    monkeypatch.setattr(
        runner,
        "run_preflight",
        lambda _config: runner.PreflightResult(
            status="pass",
            exit_code=0,
            services={"api": {"ok": True}, "product": {"ok": True}},
        ),
    )

    class TimeoutDriver:
        raw_records: list[dict[str, Any]] = []

        def __init__(self, _config) -> None:
            pass

        def close(self) -> None:
            pass

        def create_session(self) -> dict[str, str]:
            return {"id": "session-timeout"}

        def send_turn(self, _session_id: str, text: str):
            return runner.TurnRecord(
                text=text,
                started_at="2026-05-22T00:00:00+00:00",
                duration_ms=1,
                response={"ok": True},
            )

        def get_session(self, _session_id: str):
            raise runner.httpx.TimeoutException("collector timeout")

    monkeypatch.setattr(runner, "ConversationDriver", TimeoutDriver)

    result = runner.run_eval(config)

    assert result.status == "timeout"
    assert runner.reduce_exit_code([case.status for case in result.case_results]) == 3


def test_redaction_removes_sensitive_keys_but_keeps_item_name() -> None:
    runner = _load_runner()

    redacted = runner.redact_sensitive(
        {
            "token": "secret-token",
            "item_name": "测试项目B",
            "nested": {
                "pending_choice_private_map": {"A": {"learned_path_id": "lp-1"}},
                "cookie": "session=secret",
            },
        }
    )

    assert redacted["token"] == "[REDACTED]"
    assert redacted["item_name"] == "测试项目B"
    assert redacted["nested"]["pending_choice_private_map"] == "[REDACTED]"
    assert redacted["nested"]["cookie"] == "[REDACTED]"


def test_exit_code_reducer_prefers_actionable_status() -> None:
    runner = _load_runner()

    assert runner.reduce_exit_code(["pass"]) == 0
    assert runner.reduce_exit_code(["pass", "fail"]) == 1
    assert runner.reduce_exit_code(["pass", "blocked", "fail"]) == 2
    assert runner.reduce_exit_code(["timeout", "fail"]) == 3
    assert runner.reduce_exit_code(["error", "blocked"]) == 5
    assert runner.reduce_exit_code(["pass"], artifact_write_failed=True) == 4


def test_failure_recovery_case_blocks_on_invalid_api_and_writes_case_result(
    monkeypatch,
) -> None:
    runner = _load_runner()
    config = runner.parse_config(["--case", "failure_recovery_menu_safety"])

    monkeypatch.setattr(
        runner,
        "run_preflight",
        lambda _config: runner.PreflightResult(
            status="blocked",
            exit_code=2,
            services={"api": {"ok": False}, "product": {"ok": False}},
        ),
    )

    result = runner.run_eval(config)

    assert result.status == "blocked"
    assert [case.case_id for case in result.case_results] == ["failure_recovery_menu_safety"]
    assert result.case_results[0].gates[0].status == "blocked"


def test_markdown_report_uses_normalized_gate_results(tmp_path: Path) -> None:
    runner = _load_runner()
    gate = runner.GateResult(
        name="reporter_verified",
        required=True,
        status="pass",
        evidence="verification_outcome=verified",
        source="task_result_reported",
    )
    case = runner.CaseResult(
        case_id="items_closed_loop",
        status="pass",
        turns=[],
        gates=[gate],
        warnings=[],
    )
    result = runner.EvalResult(
        schema_version="11.3.6.1",
        status="pass",
        environment={"commit": "abc123"},
        services={},
        config={},
        session_id="session-1",
        case_results=[case],
        turns=[],
        events=[],
        messages=[],
        history={},
        learned_paths=[],
        raw_api_responses={},
        gate_summary={"required_passed": 1, "required_failed": 0},
    )

    report = runner.render_markdown_report(
        result,
        artifact_path=tmp_path / "artifact.json",
    )

    assert "| items_closed_loop | pass | 1/1 | 0 |" in report
    assert (
        "| items_closed_loop | reporter_verified | pass | "
        "verification_outcome=verified | task_result_reported |"
    ) in report


def test_markdown_report_includes_failure_recovery_not_run_boundary(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    case = runner.CaseResult(
        case_id="failure_recovery_menu_safety",
        status="blocked",
        turns=[],
        gates=[
            runner.GateResult(
                name="preflight",
                required=True,
                status="blocked",
                evidence="API unavailable",
                source="preflight",
            )
        ],
        warnings=[],
    )
    result = runner.EvalResult(
        schema_version=runner.SCHEMA_VERSION,
        status="blocked",
        environment={"commit": "abc123"},
        services={},
        config={},
        session_id=None,
        case_results=[case],
        turns=[],
        events=[],
        messages=[],
        history={},
        learned_paths=[],
        raw_api_responses={},
        gate_summary={"required_passed": 0, "required_failed": 0},
    )

    report = runner.render_markdown_report(
        result,
        artifact_path=tmp_path / "artifact.json",
    )

    assert "Live Conversation eval: not run" in report
    assert "Retry execution: not run" in report
