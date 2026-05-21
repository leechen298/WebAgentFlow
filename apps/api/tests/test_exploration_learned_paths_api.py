"""Contract tests for the LearnedPath HTTP surface + ingest hook."""

from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.exploration_run import (
    ExplorationMode,
    ExplorationRun,
    ExplorationRunStatus,
)
from app.models.learned_path import LearnedPath, TrustStatus
from app.repos.learned_paths_repo import LearnedPathRepository


def _insert_run(
    db_session: Session,
    *,
    kind: str | None = "autonomous",
) -> str:
    strategy = {
        "url": "https://example.com/users",
        "spec_id": "users",
        "scenario": "filter_by_status",
        "verdict": "success",
    }
    if kind is not None:
        strategy["kind"] = kind
    run = ExplorationRun(
        page_signature="https://example.com/users",
        mode=ExplorationMode.FORM,
        status=ExplorationRunStatus.COMPLETED,
        strategy_json=strategy,
        summary="ok",
        result_snapshot_json={"verdict": "success"},
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return str(run.id)


def _ingest_sample(db_session: Session, **overrides) -> str:
    kwargs = dict(
        page_template="/users",
        query_signature={"status": "active"},
        dom_fingerprint="a" * 64,
        scenario="filter_by_status",
        actions=[{"step": 1, "action_type": "fill", "target_selector": "#q"}],
        source_run_id=None,
    )
    kwargs.update(overrides)
    row, _ = LearnedPathRepository(db_session).ingest_run(**kwargs)
    return row.id


def test_list_learned_paths_returns_empty_initially(client: TestClient) -> None:
    resp = client.get("/exploration/learned-paths")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["items"] == []
    assert body["data"]["has_next"] is False


def test_list_learned_paths_returns_inserted_rows(
    client: TestClient, db_session: Session
) -> None:
    _ingest_sample(db_session)
    _ingest_sample(db_session, dom_fingerprint="b" * 64, scenario="filter_by_name")

    resp = client.get("/exploration/learned-paths")
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 2
    assert all(item["trust"] == "provisional" for item in items)


def test_list_learned_paths_filters_by_trust(
    client: TestClient, db_session: Session
) -> None:
    promoted = _ingest_sample(db_session)
    _ingest_sample(db_session, dom_fingerprint="b" * 64)

    client.patch(
        f"/exploration/learned-paths/{promoted}/trust",
        json={"status": "confirmed", "reason": "ok"},
    )

    resp = client.get("/exploration/learned-paths?trust=confirmed")
    items = resp.json()["data"]["items"]
    assert [item["id"] for item in items] == [promoted]


def test_list_learned_paths_rejects_unknown_trust(client: TestClient) -> None:
    resp = client.get("/exploration/learned-paths?trust=bogus")
    assert resp.status_code == 422


def test_get_learned_path_returns_actions(
    client: TestClient, db_session: Session
) -> None:
    row_id = _ingest_sample(db_session)
    resp = client.get(f"/exploration/learned-paths/{row_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == row_id
    assert data["actions"] == [
        {"step": 1, "action_type": "fill", "target_selector": "#q"}
    ]


def test_get_learned_path_unknown_is_404(client: TestClient) -> None:
    resp = client.get("/exploration/learned-paths/missing-id")
    assert resp.status_code == 404


def test_delete_learned_path_removes_path_only(
    client: TestClient,
    db_session: Session,
) -> None:
    run_id = _insert_run(db_session)
    row_id = _ingest_sample(db_session, source_run_id=run_id)

    resp = client.delete(f"/exploration/learned-paths/{row_id}")

    assert resp.status_code == 200
    assert resp.json()["data"] == {"path_id": row_id, "deleted": True}
    assert db_session.get(LearnedPath, row_id) is None
    assert db_session.get(ExplorationRun, run_id) is not None


def test_delete_learned_path_unknown_is_404(client: TestClient) -> None:
    resp = client.delete("/exploration/learned-paths/missing-id")
    assert resp.status_code == 404


def test_patch_trust_promotes_row(
    client: TestClient, db_session: Session
) -> None:
    row_id = _ingest_sample(db_session)
    resp = client.patch(
        f"/exploration/learned-paths/{row_id}/trust",
        json={"status": "confirmed", "reason": "looks good"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["trust"] == "confirmed"
    assert data["trust_reason"] == "looks good"


def test_patch_trust_rejects_illegal_transition(
    client: TestClient, db_session: Session
) -> None:
    row_id = _ingest_sample(db_session)
    # provisional → deprecated is legal; after that flaky is not.
    client.patch(
        f"/exploration/learned-paths/{row_id}/trust",
        json={"status": "deprecated", "reason": "nope"},
    )
    resp = client.patch(
        f"/exploration/learned-paths/{row_id}/trust",
        json={"status": "flaky", "reason": None},
    )
    assert resp.status_code == 422


def test_patch_trust_rejects_provisional_target(
    client: TestClient, db_session: Session
) -> None:
    row_id = _ingest_sample(db_session)
    # provisional isn't in the Literal whitelist — pydantic 422s at
    # the schema layer before reaching the repo.
    resp = client.patch(
        f"/exploration/learned-paths/{row_id}/trust",
        json={"status": "provisional", "reason": None},
    )
    assert resp.status_code == 422


def test_patch_trust_unknown_id_is_404(client: TestClient) -> None:
    resp = client.patch(
        "/exploration/learned-paths/missing-id/trust",
        json={"status": "confirmed"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Autonomous run deletion
# ---------------------------------------------------------------------------


def test_delete_autonomous_run_removes_run_and_preserves_learned_path(
    client: TestClient,
    db_session: Session,
) -> None:
    run_id = _insert_run(db_session)
    learned_path_id = _ingest_sample(db_session, source_run_id=run_id)

    resp = client.delete(f"/exploration/autonomous-runs/{run_id}")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data == {
        "run_id": run_id,
        "deleted": True,
        "deleted_learned_path_ids": [],
    }
    assert db_session.get(ExplorationRun, run_id) is None
    assert db_session.get(LearnedPath, learned_path_id) is not None


def test_delete_autonomous_run_without_learned_path_returns_empty_ids(
    client: TestClient,
    db_session: Session,
) -> None:
    run_id = _insert_run(db_session)

    resp = client.delete(f"/exploration/autonomous-runs/{run_id}")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["deleted"] is True
    assert data["deleted_learned_path_ids"] == []
    assert db_session.get(ExplorationRun, run_id) is None


# ---------------------------------------------------------------------------
# Run review
# ---------------------------------------------------------------------------


def test_patch_run_review_accepts_run(
    client: TestClient,
    db_session: Session,
) -> None:
    run_id = _insert_run(db_session)
    resp = client.patch(
        f"/exploration/autonomous-runs/{run_id}/review",
        json={"status": "accepted", "note": "looks good"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["operator_review_status"] == "accepted"
    assert data["operator_review_note"] == "looks good"
    assert data["operator_reviewed_at"] is not None

    run = db_session.get(ExplorationRun, run_id)
    assert run is not None
    assert str(run.operator_review_status) == "accepted"


def test_patch_run_review_rejects_run(
    client: TestClient,
    db_session: Session,
) -> None:
    run_id = _insert_run(db_session)
    resp = client.patch(
        f"/exploration/autonomous-runs/{run_id}/review",
        json={"status": "rejected", "note": "wrong path"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["operator_review_status"] == "rejected"
    assert data["operator_review_note"] == "wrong path"


def test_patch_run_review_does_not_modify_learned_path(
    client: TestClient,
    db_session: Session,
) -> None:
    run_id = _insert_run(db_session)
    path_id = _ingest_sample(db_session, source_run_id=run_id)

    resp = client.patch(
        f"/exploration/autonomous-runs/{run_id}/review",
        json={"status": "rejected"},
    )
    assert resp.status_code == 200

    path = db_session.get(LearnedPath, path_id)
    assert path is not None
    assert str(path.trust) == "provisional"


def test_patch_run_review_unknown_run_is_404(client: TestClient) -> None:
    resp = client.patch(
        "/exploration/autonomous-runs/missing-id/review",
        json={"status": "accepted"},
    )
    assert resp.status_code == 404


def test_patch_run_review_rejects_non_autonomous_run(
    client: TestClient,
    db_session: Session,
) -> None:
    run_id = _insert_run(db_session, kind="candidate")
    resp = client.patch(
        f"/exploration/autonomous-runs/{run_id}/review",
        json={"status": "accepted"},
    )
    assert resp.status_code == 404


def test_patch_run_review_rejects_invalid_status(
    client: TestClient,
    db_session: Session,
) -> None:
    run_id = _insert_run(db_session)
    resp = client.patch(
        f"/exploration/autonomous-runs/{run_id}/review",
        json={"status": "bogus"},
    )
    assert resp.status_code == 422


def test_patch_run_review_to_unreviewed_clears_reviewed_at(
    client: TestClient,
    db_session: Session,
) -> None:
    run_id = _insert_run(db_session)
    # First accept
    client.patch(
        f"/exploration/autonomous-runs/{run_id}/review",
        json={"status": "accepted", "note": "ok"},
    )
    run = db_session.get(ExplorationRun, run_id)
    assert run is not None
    assert run.operator_reviewed_at is not None

    # Then reset to unreviewed
    resp = client.patch(
        f"/exploration/autonomous-runs/{run_id}/review",
        json={"status": "unreviewed"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["operator_review_status"] == "unreviewed"
    assert data["operator_reviewed_at"] is None

    run = db_session.get(ExplorationRun, run_id)
    assert run is not None
    assert run.operator_reviewed_at is None


# ---------------------------------------------------------------------------
# Detail learned_path relation projection
# ---------------------------------------------------------------------------


def test_get_autonomous_run_shows_learned_path_relation_source(
    client: TestClient,
    db_session: Session,
) -> None:
    run_id = _insert_run(db_session)
    path_id = _ingest_sample(db_session, source_run_id=run_id)

    resp = client.get(f"/exploration/autonomous-runs/{run_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["learned_path"]["id"] == path_id
    assert data["learned_path"]["relation"] == "source"


def test_get_autonomous_run_shows_learned_path_relation_dedup_hit(
    client: TestClient,
    db_session: Session,
) -> None:
    from sqlalchemy.orm import sessionmaker

    from app.models.exploration_run import ExplorationRunStatus
    from app.routers.exploration import (
        AutonomousExplorePayload,
        _persist_autonomous_run,
    )

    TestingSessionLocal = sessionmaker(
        bind=db_session.bind,
        autoflush=False,
        expire_on_commit=False,
    )

    payload = AutonomousExplorePayload(
        url="https://example.com/users?status=active",
        scenario="filter_by_status",
    )
    final_data = {
        "page_analysis": {
            "url": "https://example.com/users?status=active",
            "title": "Users",
            "fillable": [],
            "submit": [],
        },
        "steps": [],
        "verdict": "success",
        "verification": {"scorecard": {"pass_gate": {"status": "pass"}}},
    }

    with patch("app.routers.exploration.SessionLocal", TestingSessionLocal):
        _persist_autonomous_run(
            payload,
            deepcopy(final_data),
            verdict="success",
            status=ExplorationRunStatus.COMPLETED,
        )
        second_run_id = _persist_autonomous_run(
            payload,
            deepcopy(final_data),
            verdict="success",
            status=ExplorationRunStatus.COMPLETED,
        )

    # First run is source, second is dedup_hit
    resp = client.get(f"/exploration/autonomous-runs/{second_run_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["learned_path"]["relation"] == "dedup_hit"
    assert data["learned_path"]["hit_count"] == 2


def test_get_autonomous_run_shows_operator_review_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    run_id = _insert_run(db_session)
    resp = client.get(f"/exploration/autonomous-runs/{run_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["operator_review_status"] == "unreviewed"
    assert data["operator_review_note"] is None
    assert data["operator_reviewed_at"] is None


def test_delete_autonomous_run_unknown_id_is_404(client: TestClient) -> None:
    resp = client.delete("/exploration/autonomous-runs/missing-id")

    assert resp.status_code == 404


def test_delete_autonomous_run_rejects_non_autonomous_run(
    client: TestClient,
    db_session: Session,
) -> None:
    run_id = _insert_run(db_session, kind="candidate")

    resp = client.delete(f"/exploration/autonomous-runs/{run_id}")

    assert resp.status_code == 404
    assert db_session.get(ExplorationRun, run_id) is not None


# ---------------------------------------------------------------------------
# Ingest hook
# ---------------------------------------------------------------------------


def _final_data_with_pass_gate(status: str = "pass") -> dict:
    return {
        "page_analysis": {
            "url": "https://example.com/users",
            "title": "Users",
            "fillable": [
                {
                    "category": "fillable",
                    "tag": "input",
                    "element_type": "text",
                    "name": "q",
                    "label_text": "Search",
                    "semantic_role": "search",
                }
            ],
            "submit": [
                {
                    "category": "submit",
                    "tag": "button",
                    "element_type": "submit",
                    "text": "Search",
                }
            ],
        },
        "steps": [
            {
                "step": 1,
                "action_type": "fill",
                "target_selector": "#q",
                "target_description": "search input",
                "value": "bob",
                "screenshot_ref": "/tmp/not-kept.png",
            }
        ],
        "verdict": "success",
        "verification": {"scorecard": {"pass_gate": {"status": status}}},
    }


def test_ingest_hook_writes_on_pass_gate_pass(
    db_session: Session,
) -> None:
    """Exercise ``_persist_autonomous_run`` directly (no Playwright)
    and assert the LearnedPath side-effect only.

    ``SessionLocal`` is pointed at the test engine so writes land in
    the same in-memory SQLite the fixtures read from.
    """
    from sqlalchemy.orm import sessionmaker

    from app.models.exploration_run import ExplorationRunStatus
    from app.routers.exploration import (
        AutonomousExplorePayload,
        _persist_autonomous_run,
    )

    TestingSessionLocal = sessionmaker(
        bind=db_session.bind,
        autoflush=False,
        expire_on_commit=False,
    )

    payload = AutonomousExplorePayload(
        url="https://example.com/users?status=active",
        scenario="filter_by_status",
    )
    final_data = _final_data_with_pass_gate("pass")
    # Analyzer ended up on the same URL the operator requested — the
    # no-redirect case. Identity is computed from page_analysis.url.
    final_data["page_analysis"]["url"] = "https://example.com/users?status=active"

    with patch("app.routers.exploration.SessionLocal", TestingSessionLocal):
        run_id = _persist_autonomous_run(
            payload,
            final_data,
            verdict="success",
            status=ExplorationRunStatus.COMPLETED,
        )

    assert run_id is not None
    rows, _, _ = LearnedPathRepository(db_session).list_page()
    assert len(rows) == 1
    row = rows[0]
    assert row.source_run_id == run_id
    assert row.scenario == "filter_by_status"
    assert row.page_template == "/users"
    assert row.query_signature == {"status": "active"}
    # screenshot_ref must have been stripped from actions.
    assert "screenshot_ref" not in row.actions[0]


def test_get_autonomous_run_links_repeated_pass_to_deduped_learned_path(
    client: TestClient,
    db_session: Session,
) -> None:
    """Repeated passes dedupe to the first LearnedPath, but every
    matching run detail should still expose that path for trust edits.
    """
    from sqlalchemy.orm import sessionmaker

    from app.routers.exploration import (
        AutonomousExplorePayload,
        _persist_autonomous_run,
    )

    TestingSessionLocal = sessionmaker(
        bind=db_session.bind,
        autoflush=False,
        expire_on_commit=False,
    )

    payload = AutonomousExplorePayload(
        url="https://example.com/users?status=active",
        scenario="filter_by_status",
    )
    final_data = _final_data_with_pass_gate("pass")
    final_data["page_analysis"]["url"] = "https://example.com/users?status=active"

    with patch("app.routers.exploration.SessionLocal", TestingSessionLocal):
        first_run_id = _persist_autonomous_run(
            payload,
            deepcopy(final_data),
            verdict="success",
            status=ExplorationRunStatus.COMPLETED,
        )
        second_run_id = _persist_autonomous_run(
            payload,
            deepcopy(final_data),
            verdict="success",
            status=ExplorationRunStatus.COMPLETED,
        )

    rows, _, _ = LearnedPathRepository(db_session).list_page()
    assert len(rows) == 1
    path = rows[0]
    assert path.source_run_id == first_run_id
    assert path.hit_count == 2

    resp = client.get(f"/exploration/autonomous-runs/{second_run_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["learned_path_id"] == path.id
    assert data["learned_path_trust"] == "provisional"


def test_ingest_hook_identity_tracks_analyzer_url_on_redirect(
    db_session: Session,
) -> None:
    """When Playwright landed on a different URL than requested
    (canonical redirect, slash-fix, etc.), the LearnedPath identity
    must follow the URL the analyzer actually inspected, not the one
    the operator typed in.
    """
    from sqlalchemy.orm import sessionmaker

    from app.models.exploration_run import ExplorationRunStatus
    from app.routers.exploration import (
        AutonomousExplorePayload,
        _persist_autonomous_run,
    )

    TestingSessionLocal = sessionmaker(
        bind=db_session.bind,
        autoflush=False,
        expire_on_commit=False,
    )

    # Operator asked for /users (no query); analyzer ended up on
    # /users/?status=active after a server redirect.
    payload = AutonomousExplorePayload(
        url="https://example.com/users",
        scenario="filter_by_status",
    )
    final_data = _final_data_with_pass_gate("pass")
    final_data["page_analysis"]["url"] = "https://example.com/users/?status=active"

    with patch("app.routers.exploration.SessionLocal", TestingSessionLocal):
        _persist_autonomous_run(
            payload,
            final_data,
            verdict="success",
            status=ExplorationRunStatus.COMPLETED,
        )

    rows, _, _ = LearnedPathRepository(db_session).list_page()
    assert len(rows) == 1
    row = rows[0]
    # page_template should reflect the redirect target (trailing slash
    # normalised by path_template); query_signature should contain the
    # status flag that only exists in the analyzer URL.
    assert row.page_template == "/users"
    assert row.query_signature == {"status": "active"}


def test_ingest_hook_persists_observational_run_with_no_actions(
    db_session: Session,
) -> None:
    """An "observational" pass — ``pass_gate == "pass"`` but the
    scenario didn't require interactive steps (e.g. open page, content
    confirms) — must still sink as a LearnedPath with empty actions.
    Future Phase 3 planners need the signal that this template /
    scenario is reachable on a bare visit.
    """
    from sqlalchemy.orm import sessionmaker

    from app.models.exploration_run import ExplorationRunStatus
    from app.routers.exploration import (
        AutonomousExplorePayload,
        _persist_autonomous_run,
    )

    TestingSessionLocal = sessionmaker(
        bind=db_session.bind,
        autoflush=False,
        expire_on_commit=False,
    )

    payload = AutonomousExplorePayload(
        url="https://example.com/about",
        scenario="page_loads",
    )
    final_data = _final_data_with_pass_gate("pass")
    final_data["page_analysis"]["url"] = "https://example.com/about"
    # No interactive steps — the run only navigated and verified.
    final_data["steps"] = []

    with patch("app.routers.exploration.SessionLocal", TestingSessionLocal):
        run_id = _persist_autonomous_run(
            payload,
            final_data,
            verdict="success",
            status=ExplorationRunStatus.COMPLETED,
        )

    assert run_id is not None
    rows, _, _ = LearnedPathRepository(db_session).list_page()
    assert len(rows) == 1
    row = rows[0]
    assert row.actions == []
    assert row.scenario == "page_loads"
    assert row.page_template == "/about"


def test_ingest_hook_skips_on_pass_gate_unverified(
    db_session: Session,
) -> None:
    from sqlalchemy.orm import sessionmaker

    from app.models.exploration_run import ExplorationRunStatus
    from app.routers.exploration import (
        AutonomousExplorePayload,
        _persist_autonomous_run,
    )

    TestingSessionLocal = sessionmaker(
        bind=db_session.bind,
        autoflush=False,
        expire_on_commit=False,
    )

    payload = AutonomousExplorePayload(
        url="https://example.com/users",
        scenario="filter_by_status",
    )
    final_data = _final_data_with_pass_gate("unverified")

    with patch("app.routers.exploration.SessionLocal", TestingSessionLocal):
        _persist_autonomous_run(
            payload,
            final_data,
            verdict="success",
            status=ExplorationRunStatus.COMPLETED,
        )

    assert LearnedPathRepository(db_session).count() == 0


# ---------------------------------------------------------------------------
# Old-path 404 checks — routes removed by 10.1.4 restful cleanup
# ---------------------------------------------------------------------------


def test_old_autonomous_runs_list_returns_404(client: TestClient) -> None:
    resp = client.get("/exploration/autonomous-runs/list")
    assert resp.status_code == 404


def test_old_autonomous_runs_get_returns_404(client: TestClient) -> None:
    resp = client.get("/exploration/autonomous-runs/get?run_id=anything")
    assert resp.status_code == 404


def test_old_learned_paths_list_returns_404(client: TestClient) -> None:
    resp = client.get("/exploration/learned-paths/list")
    assert resp.status_code == 404


def test_old_autonomous_run_singular_returns_404(client: TestClient) -> None:
    resp = client.post("/exploration/autonomous-run", json={"url": "https://example.com"})
    assert resp.status_code == 404


def test_old_autonomous_run_stream_singular_returns_404(client: TestClient) -> None:
    resp = client.post("/exploration/autonomous-run/stream", json={"url": "https://example.com"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------


def test_replay_unknown_path_is_404(client: TestClient) -> None:
    resp = client.post(
        "/exploration/learned-paths/not-a-real-id/replay",
        json={"url": "http://127.0.0.1:5175/users"},
    )
    assert resp.status_code == 404


def test_replay_deprecated_path_is_422(
    client: TestClient, db_session: Session
) -> None:
    path_id = _ingest_sample(db_session)
    LearnedPathRepository(db_session).set_trust(
        path_id, TrustStatus.DEPRECATED, reason="old"
    )
    resp = client.post(
        f"/exploration/learned-paths/{path_id}/replay",
        json={"url": "http://127.0.0.1:5175/users"},
    )
    assert resp.status_code == 422


def test_replay_missing_url_is_422(
    client: TestClient, db_session: Session
) -> None:
    path_id = _ingest_sample(db_session)
    resp = client.post(
        f"/exploration/learned-paths/{path_id}/replay",
        json={},
    )
    assert resp.status_code == 422


def test_replay_flaky_path_includes_warning(
    client: TestClient, db_session: Session
) -> None:
    from unittest.mock import patch

    from app.schemas.learned_path_replay import ReplayResult

    path_id = _ingest_sample(db_session)
    LearnedPathRepository(db_session).set_trust(
        path_id, TrustStatus.FLAKY, reason="unstable"
    )

    mock_result = ReplayResult(
        learned_path_id=path_id,
        source_run_id=None,
        trust="flaky",
        status="succeeded",
        drift_status="none",
        drift_reasons=[],
        warnings=[],
        stored_signature={},
        current_signature={},
        steps=[],
        final_url="http://127.0.0.1:5175/users",
        final_title="Users",
    )

    with patch(
        "app.services.learning.learned_path_replay.run_replay",
        return_value=mock_result,
    ):
        resp = client.post(
            f"/exploration/learned-paths/{path_id}/replay",
            json={"url": "http://127.0.0.1:5175/users"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "Path trust is flaky" in data["warnings"]


def test_replay_valid_path_returns_result(
    client: TestClient, db_session: Session
) -> None:
    from unittest.mock import patch

    from app.schemas.learned_path_replay import ReplayResult, ReplayStepLog

    path_id = _ingest_sample(db_session)
    mock_result = ReplayResult(
        learned_path_id=path_id,
        source_run_id=None,
        trust="provisional",
        status="succeeded",
        drift_status="none",
        drift_reasons=[],
        warnings=[],
        stored_signature={"page_template": "/users"},
        current_signature={"page_template": "/users"},
        steps=[
            ReplayStepLog(
                step=1,
                action_type="fill",
                selector="#q",
                ok=True,
            )
        ],
        final_url="http://127.0.0.1:5175/users",
        final_title="Users",
    )

    with patch(
        "app.services.learning.learned_path_replay.run_replay",
        return_value=mock_result,
    ):
        resp = client.post(
            f"/exploration/learned-paths/{path_id}/replay",
            json={"url": "http://127.0.0.1:5175/users"},
        )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["learned_path_id"] == path_id
    assert data["status"] == "succeeded"
    assert data["drift_status"] == "none"
    assert len(data["steps"]) == 1
    assert data["steps"][0]["action_type"] == "fill"


def test_replay_request_passes_evidence_targets(
    client: TestClient, db_session: Session
) -> None:
    from unittest.mock import patch

    from app.schemas.learned_path_replay import ReplayResult

    path_id = _ingest_sample(db_session)
    mock_result = ReplayResult(
        learned_path_id=path_id,
        source_run_id=None,
        trust="provisional",
        status="succeeded",
        drift_status="none",
        drift_reasons=[],
        warnings=[],
        stored_signature={"page_template": "/items"},
        current_signature={"page_template": "/items"},
        steps=[],
        final_url="http://127.0.0.1:5176/items",
        final_title="Items",
    )

    with patch(
        "app.services.learning.learned_path_replay.run_replay",
        return_value=mock_result,
    ) as mock_run_replay:
        resp = client.post(
            f"/exploration/learned-paths/{path_id}/replay",
            json={
                "url": "http://127.0.0.1:5176/items",
                "evidence_targets": [
                    {
                        "kind": "dom_text_present",
                        "text": "测试项目B-001",
                        "source_slot": "item_name",
                        "selector": "[data-testid='item-list']",
                    }
                ],
            },
        )

    assert resp.status_code == 200
    target = mock_run_replay.call_args.kwargs["evidence_targets"][0]
    assert target.kind == "dom_text_present"
    assert target.text == "测试项目B-001"
    assert target.source_slot == "item_name"
    assert target.selector == "[data-testid='item-list']"
