"""Unit tests for the 11.3.7 user-facing WAgent behavior eval runner."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


def _load_runner():
    repo_root = Path(__file__).resolve().parents[3]
    runner_path = repo_root / "scripts" / "evals" / "wagent_user_behavior_eval.py"
    assert runner_path.exists(), "user behavior runner script is missing"
    spec = importlib.util.spec_from_file_location("wagent_user_behavior_eval", runner_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _package_scripts() -> dict[str, str]:
    repo_root = Path(__file__).resolve().parents[3]
    package = json.loads((repo_root / "package.json").read_text(encoding="utf-8"))
    return package["scripts"]


def _operator_actions() -> list[dict[str, Any]]:
    return [
        {
            "surface": "cli",
            "action": "run_wagent_user_behavior_eval",
            "command": ["pnpm", "run", "eval:wagent:user-behavior"],
            "cwd": "/repo",
            "started_at": "2026-05-24T00:00:00+00:00",
        }
    ]


def _base_evidence(response: str) -> dict[str, Any]:
    return {
        "turns": [{"text": "input", "response": {"user_response": response}}],
        "events": [],
        "messages": [{"role": "agent", "content": response}],
        "session": {"id": "session-1", "metadata": {}},
        "history": {},
        "raw_product_client_records": [
            {"method": "POST", "path": "/conversation/sessions"},
            {"method": "POST", "path": "/conversation/sessions/session-1/dispatch"},
        ],
        "operator_actions": _operator_actions(),
    }


def test_package_script_registers_user_behavior_eval() -> None:
    scripts = _package_scripts()

    assert scripts["eval:wagent:user-behavior"] == (
        ".venv/bin/python scripts/evals/wagent_user_behavior_eval.py"
    )


def test_parse_config_defaults_to_first_wave_cases() -> None:
    runner = _load_runner()

    config = runner.parse_config([])

    assert config.cases == [
        "url_only_known_page",
        "url_only_unknown_page",
        "url_only_unknown_choose_learn_starts_learning",
        "execute_known_action",
        "execute_unknown_action",
        "execute_unknown_choose_learn_then_execute_or_learning_flow",
        "vague_input_no_execution",
        "forbidden_test_target_not_in_runtime_code_or_prompts",
    ]
    assert config.api_base == "http://127.0.0.1:8001"
    assert config.spec_path == Path("scripts/evals/specs/wagent_user_behavior_items.json")
    assert config.artifact_dir == Path("artifacts/wagent-user-behavior-eval")


def test_parse_config_accepts_pnpm_argument_separator() -> None:
    runner = _load_runner()

    config = runner.parse_config(
        [
            "--",
            "--case",
            "forbidden_test_target_not_in_runtime_code_or_prompts",
            "--json-only",
        ]
    )

    assert config.cases == ["forbidden_test_target_not_in_runtime_code_or_prompts"]
    assert config.write_markdown is False


def test_scan_only_eval_does_not_require_service_preflight(tmp_path, monkeypatch) -> None:
    runner = _load_runner()
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        json.dumps(
            {
                "target_name": "unit",
                "target_label": "Unit",
                "product_url": "http://127.0.0.1:5176/items",
                "target_manifest": {},
            }
        ),
        encoding="utf-8",
    )
    config = runner.parse_config(
        [
            "--case",
            "forbidden_test_target_not_in_runtime_code_or_prompts",
            "--spec",
            str(spec_path),
            "--json-only",
        ]
    )

    monkeypatch.setattr(
        runner,
        "run_forbidden_target_scan",
        lambda _spec: {"status": "pass", "match_count": 0, "matches": []},
    )
    monkeypatch.setattr(
        runner,
        "run_preflight",
        lambda _config, _spec: (_ for _ in ()).throw(AssertionError("preflight called")),
    )

    result = runner.run_eval(config)

    assert result.status == "pass"
    assert [case.case_id for case in result.case_results] == [
        "forbidden_test_target_not_in_runtime_code_or_prompts"
    ]


def test_blocked_forbidden_scan_stops_before_service_preflight(tmp_path, monkeypatch) -> None:
    runner = _load_runner()
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(
        json.dumps(
            {
                "target_name": "unit",
                "target_label": "Unit",
                "product_url": "http://127.0.0.1:5176/items",
                "target_manifest": {},
            }
        ),
        encoding="utf-8",
    )
    config = runner.parse_config(["--spec", str(spec_path), "--json-only"])

    monkeypatch.setattr(
        runner,
        "run_forbidden_target_scan",
        lambda _spec: {
            "status": "blocked",
            "match_count": 0,
            "matches": [],
            "reason": "scanner unavailable",
        },
    )
    monkeypatch.setattr(
        runner,
        "run_preflight",
        lambda _config, _spec: (_ for _ in ()).throw(AssertionError("preflight called")),
    )

    result = runner.run_eval(config)

    assert result.status == "blocked"
    assert [case.case_id for case in result.case_results] == [
        "forbidden_test_target_not_in_runtime_code_or_prompts"
    ]
    assert result.case_results[0].gates[0].status == "blocked"


def test_forbidden_target_gate_passes_only_when_scan_has_no_matches() -> None:
    runner = _load_runner()

    passed = runner.UserBehaviorGateEvaluator().evaluate_forbidden_target_scan(
        {"status": "pass", "match_count": 0, "matches": []}
    )
    failed = runner.UserBehaviorGateEvaluator().evaluate_forbidden_target_scan(
        {"status": "fail", "match_count": 1, "matches": [{"path": "runtime.py"}]}
    )

    assert passed.status == "pass"
    assert {gate.name: gate.status for gate in passed.gates}["forbidden_target_scan"] == "pass"
    assert failed.status == "fail"
    assert {gate.name: gate.status for gate in failed.gates}["forbidden_target_scan"] == "fail"


def test_url_only_known_page_requires_current_scope_and_no_private_leak() -> None:
    runner = _load_runner()
    evidence = _base_evidence("我已经记住这个页面地址。你想让我学习或执行哪个操作？")
    evidence["isolation"] = {
        "strategy": "current_eval_session",
        "learned_action_count": 1,
        "source": "current_eval_scope",
    }

    result = runner.UserBehaviorGateEvaluator().evaluate_url_only_known_page(evidence)

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "pass"
    assert gates["known_scope_isolated"].status == "pass"
    assert gates["asks_next_step_without_execution"].status == "pass"
    assert gates["public_payload_redacted"].status == "pass"


def test_url_only_unknown_page_requires_no_global_learned_state() -> None:
    runner = _load_runner()
    evidence = _base_evidence("还没学过这个站点或页面，需要先学习。你也可以取消。")
    evidence["isolation"] = {
        "strategy": "fresh_session",
        "learned_action_count": 0,
        "source": "isolated_scope",
    }

    result = runner.UserBehaviorGateEvaluator().evaluate_url_only_unknown_page(evidence)

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "pass"
    assert gates["unknown_scope_isolated"].status == "pass"
    assert gates["unknown_page_guidance"].status == "pass"
    assert gates["no_execution_started"].status == "pass"


def test_execute_known_action_requires_verified_evidence() -> None:
    runner = _load_runner()
    evidence = _base_evidence("执行完成。页面证据已确认目标值“Alpha”。")
    evidence["isolation"] = {
        "strategy": "current_eval_session",
        "learned_action_count": 1,
        "source": "current_eval_scope",
    }
    evidence["events"] = [
        {"id": "evt-start", "type": "chat_execution_started", "payload": {}},
        {
            "id": "evt-complete",
            "type": "chat_execution_completed",
            "payload": {
                "replay": {
                    "replay_status": "succeeded",
                    "execution_evidence": [
                        {
                            "kind": "dom_text_present",
                            "target": "Alpha",
                            "status": "verified",
                            "confidence": 0.95,
                        }
                    ],
                }
            },
        },
        {
            "id": "evt-report",
            "type": "task_result_reported",
            "payload": {"verification_outcome": "verified", "task_verified": True},
        },
    ]

    result = runner.UserBehaviorGateEvaluator().evaluate_execute_known_action(
        evidence,
        expected_value="Alpha",
    )

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "pass"
    assert gates["execution_started"].status == "pass"
    assert gates["execution_evidence_verified"].status == "pass"
    assert gates["reporter_verified"].status == "pass"


def test_execute_unknown_choose_learn_can_pass_staged_learning_without_full_execute() -> None:
    runner = _load_runner()
    evidence = _base_evidence("开始学习页面操作。")
    evidence["isolation"] = {
        "strategy": "fresh_session",
        "learned_action_count": 0,
        "source": "isolated_scope",
    }
    evidence["events"] = [
        {"id": "evt-learn", "type": "chat_learning_started", "payload": {}},
    ]

    result = runner.UserBehaviorGateEvaluator().evaluate_execute_unknown_choose_learn(
        evidence
    )

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "pass"
    assert gates["learning_flow_started"].status == "pass"
    assert gates["full_learn_then_execute"].required is False
    assert gates["full_learn_then_execute"].status == "follow_up"


def test_vague_input_must_not_start_learning_or_execution() -> None:
    runner = _load_runner()
    evidence = _base_evidence("请提供目标页面 URL，或说明要学习/执行的网页操作。")

    result = runner.UserBehaviorGateEvaluator().evaluate_vague_input_no_execution(
        evidence
    )

    gates = {gate.name: gate for gate in result.gates}
    assert result.status == "pass"
    assert gates["no_execution_started"].status == "pass"
    assert gates["no_learning_started"].status == "pass"
    assert gates["clarifies_target_or_goal"].status == "pass"


def test_exit_code_mapping_matches_contract() -> None:
    runner = _load_runner()

    assert runner.exit_code_for_status("pass") == 0
    assert runner.exit_code_for_status("fail") == 1
    assert runner.exit_code_for_status("blocked") == 2
    assert runner.exit_code_for_status("timeout") == 3


def test_artifact_sanitizer_removes_private_terms() -> None:
    runner = _load_runner()
    payload = {
        "learned_path_id": "lp-private",
        "selector": "[data-testid='secret']",
        "nested": {
            "slot_overrides": {"name": "Alpha"},
            "safe": "visible",
        },
    }

    sanitized = runner.sanitize_artifact_payload(payload)
    text = json.dumps(sanitized, ensure_ascii=False)

    assert "learned_path_id" not in text
    assert "selector" not in text
    assert "slot_overrides" not in text
    assert "lp-private" not in text
    assert "visible" in text
