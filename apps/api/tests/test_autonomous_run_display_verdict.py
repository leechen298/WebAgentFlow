"""Scenario-relative verdict shaping for autonomous run API payloads."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.exploration_run import (
    ExplorationMode,
    ExplorationRun,
    ExplorationRunStatus,
)
from app.routers.exploration import _apply_scenario_relative_verdicts


def _payload(pass_gate_status: str) -> dict:
    return {
        "verdict": "failure",
        "success": False,
        "summary": "Actions executed but final page is a login wall.",
        "supervisor": {
            "verdict": "failure",
            "summary": "The page stayed on /login with an error alert.",
        },
        "verification": {
            "scorecard": {
                "pass_gate": {"status": pass_gate_status, "reasons": []},
                "verdict_check": {
                    "self_verdict": "failure",
                    "expected_verdict_not": "success",
                    "matches_expectation": True,
                },
            },
        },
    }


def test_pass_gate_pass_rewrites_negative_path_public_verdict_to_success() -> None:
    data = _payload("pass")

    _apply_scenario_relative_verdicts(data)

    assert data["verdict"] == "success"
    assert data["success"] is True
    assert data["mechanical_verdict"] == "failure"
    assert data["supervisor"]["verdict"] == "success"
    assert data["supervisor"]["mechanical_verdict"] == "failure"
    # Comparator evidence stays mechanical and auditable.
    vc = data["verification"]["scorecard"]["verdict_check"]
    assert vc["self_verdict"] == "failure"
    assert vc["matches_expectation"] is True


def test_pass_gate_fail_rewrites_even_raw_success_to_failure() -> None:
    data = _payload("fail")
    data["verdict"] = "success"
    data["success"] = True
    data["supervisor"]["verdict"] = "success"

    _apply_scenario_relative_verdicts(data)

    assert data["verdict"] == "failure"
    assert data["success"] is False
    assert data["mechanical_verdict"] == "success"
    assert data["supervisor"]["verdict"] == "failure"
    assert data["supervisor"]["mechanical_verdict"] == "success"


def test_pass_gate_unverified_maps_to_uncertain_public_verdict() -> None:
    data = _payload("unverified")

    _apply_scenario_relative_verdicts(data)

    assert data["verdict"] == "uncertain"
    assert data["success"] is False
    assert data["mechanical_verdict"] == "failure"


def _insert_autonomous_run(
    db_session: Session,
    *,
    result_verdict: str = "failure",
    strategy_verdict: str = "failure",
) -> str:
    run = ExplorationRun(
        page_signature="https://example.invalid/entry",
        mode=ExplorationMode.FORM,
        status=ExplorationRunStatus.COMPLETED,
        strategy_json={
            "kind": "autonomous",
            "url": "https://example.invalid/entry",
            "spec_id": "login",
            "scenario": "invalid_credentials",
            "verdict": strategy_verdict,
        },
        summary="Actions executed but final page is a login wall.",
        result_snapshot_json={
            **_payload("pass"),
            "verdict": result_verdict,
        },
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return str(run.id)


def test_history_detail_does_not_rewrite_old_snapshot_verdict(
    client: TestClient,
    db_session: Session,
) -> None:
    run_id = _insert_autonomous_run(db_session, result_verdict="failure")

    resp = client.get(f"/exploration/autonomous-runs/{run_id}")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["pass_gate_status"] == "pass"
    assert data["result"]["verdict"] == "failure"
    assert "mechanical_verdict" not in data["result"]


def test_history_list_does_not_rewrite_old_strategy_verdict(
    client: TestClient,
    db_session: Session,
) -> None:
    _insert_autonomous_run(db_session, strategy_verdict="failure")

    resp = client.get("/exploration/autonomous-runs")

    assert resp.status_code == 200
    item = resp.json()["data"]["items"][0]
    assert item["pass_gate_status"] == "pass"
    assert item["verdict"] == "failure"
