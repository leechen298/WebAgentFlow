"""Tests for learning, exploration, and AST routers.

Covers:
  - /learning/feedback/* (CandidateFeedback CRUD + upsert + list-by-recording)
  - /learning/paths/*    (LearnedPath CRUD, FK validation to SuccessCriteria)
  - /learning/runs/*     (ExplorationRun CRUD + infer-candidates with mocked services)
  - /learning/success-criteria/* (SuccessCriteria CRUD)
  - /exploration/*       (task list, task get, approve/reject placeholders)
  - /ast/*               (parse + simplify)
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


# ═══════════════════════════════════════════════════════════════════════
# Learning Feedback (/learning/feedback/*)
# ═══════════════════════════════════════════════════════════════════════


def _create_feedback(client: TestClient, **overrides) -> dict:
    payload = {
        "recording_id": overrides.get("recording_id", "rec-001"),
        "element_key": overrides.get("element_key", "input#username"),
        "judgment": overrides.get("judgment", "reasonable"),
        "comment": overrides.get("comment", "Looks correct"),
        "candidate_score": overrides.get("candidate_score", 0.85),
    }
    payload.update(overrides)
    resp = client.post("/learning/feedback/create", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def test_feedback_crud(client: TestClient) -> None:
    # Create
    fb = _create_feedback(client)
    fb_id = fb["id"]
    assert fb["judgment"] == "reasonable"
    assert fb["element_key"] == "input#username"
    assert fb["candidate_score"] == 0.85

    # List
    resp = client.get("/learning/feedback/list")
    assert resp.status_code == 200
    page = resp.json()["data"]
    assert len(page["items"]) >= 1
    assert page["has_next"] is False

    # Get
    resp = client.get(f"/learning/feedback/get?feedback_id={fb_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == fb_id

    # Update
    resp = client.post(
        "/learning/feedback/update",
        json={
            "feedback_id": fb_id,
            "update_data": {
                "judgment": "unreasonable",
                "comment": "Wrong element",
            },
        },
    )
    assert resp.status_code == 200
    updated = resp.json()["data"]
    assert updated["judgment"] == "unreasonable"
    assert updated["comment"] == "Wrong element"

    # Delete
    resp = client.post("/learning/feedback/delete", json={"feedback_id": fb_id})
    assert resp.status_code == 200
    assert resp.json()["data"]["feedback_id"] == fb_id

    # Get after delete -> 404
    resp = client.get(f"/learning/feedback/get?feedback_id={fb_id}")
    assert resp.status_code == 404


def test_feedback_get_not_found(client: TestClient) -> None:
    resp = client.get("/learning/feedback/get?feedback_id=nonexistent")
    assert resp.status_code == 404


def test_feedback_update_not_found(client: TestClient) -> None:
    resp = client.post(
        "/learning/feedback/update",
        json={
            "feedback_id": "nonexistent",
            "update_data": {"judgment": "unreasonable"},
        },
    )
    assert resp.status_code == 404


def test_feedback_delete_not_found(client: TestClient) -> None:
    resp = client.post(
        "/learning/feedback/delete", json={"feedback_id": "nonexistent"}
    )
    assert resp.status_code == 404


def test_feedback_list_by_recording(client: TestClient) -> None:
    _create_feedback(client, recording_id="rec-A", element_key="btn1")
    _create_feedback(client, recording_id="rec-A", element_key="btn2")
    _create_feedback(client, recording_id="rec-B", element_key="btn3")

    resp = client.get("/learning/feedback/list-by-recording?recording_id=rec-A")
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) == 2
    assert all(i["recording_id"] == "rec-A" for i in items)


def test_feedback_list_by_recording_with_run_id(client: TestClient) -> None:
    _create_feedback(client, recording_id="rec-C", element_key="x", run_id="run-1")
    _create_feedback(client, recording_id="rec-C", element_key="y", run_id="run-2")

    resp = client.get(
        "/learning/feedback/list-by-recording?recording_id=rec-C&run_id=run-1"
    )
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) == 1
    assert items[0]["run_id"] == "run-1"


def test_feedback_upsert_creates_then_updates(client: TestClient) -> None:
    payload = {
        "recording_id": "rec-U",
        "element_key": "input#email",
        "judgment": "reasonable",
        "comment": "first",
    }

    # First upsert: creates
    resp = client.post("/learning/feedback/upsert", json=payload)
    assert resp.status_code == 200
    fb1 = resp.json()["data"]
    assert fb1["comment"] == "first"

    # Second upsert with same key: updates
    payload["comment"] = "second"
    payload["judgment"] = "unreasonable"
    resp = client.post("/learning/feedback/upsert", json=payload)
    assert resp.status_code == 200
    fb2 = resp.json()["data"]
    assert fb2["id"] == fb1["id"]  # same record
    assert fb2["comment"] == "second"
    assert fb2["judgment"] == "unreasonable"


def test_feedback_list_pagination(client: TestClient) -> None:
    # Create 3 items, request limit=2 to trigger has_next
    for i in range(3):
        _create_feedback(client, element_key=f"el-{i}")

    resp = client.get("/learning/feedback/list?limit=2")
    assert resp.status_code == 200
    page = resp.json()["data"]
    assert len(page["items"]) == 2
    assert page["has_next"] is True
    assert page["next_cursor"] is not None

    # Second page using cursor
    resp2 = client.get(f"/learning/feedback/list?limit=2&cursor={page['next_cursor']}")
    assert resp2.status_code == 200
    page2 = resp2.json()["data"]
    assert len(page2["items"]) == 1
    assert page2["has_next"] is False


# ═══════════════════════════════════════════════════════════════════════
# Success Criteria (/learning/success-criteria/*)
# ═══════════════════════════════════════════════════════════════════════


def _create_criteria(client: TestClient, **overrides) -> dict:
    payload = {
        "name": overrides.get("name", "Form submit OK"),
        "category": overrides.get("category", "submit_success"),
        "strength": overrides.get("strength", "strong"),
        "description": overrides.get("description", "URL changes after submit"),
        "conditions_json": overrides.get(
            "conditions_json",
            [{"type": "url_changed", "required": True}],
        ),
    }
    payload.update(overrides)
    resp = client.post("/learning/success-criteria/create", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def test_success_criteria_crud(client: TestClient) -> None:
    # Create
    sc = _create_criteria(client)
    sc_id = sc["id"]
    assert sc["name"] == "Form submit OK"
    assert sc["category"] == "submit_success"
    assert sc["strength"] == "strong"
    assert sc["enabled"] is True

    # List
    resp = client.get("/learning/success-criteria/list")
    assert resp.status_code == 200
    page = resp.json()["data"]
    assert len(page["items"]) >= 1

    # Get
    resp = client.get(f"/learning/success-criteria/get?criteria_id={sc_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "Form submit OK"

    # Update
    resp = client.post(
        "/learning/success-criteria/update",
        json={
            "criteria_id": sc_id,
            "update_data": {
                "name": "Updated criteria",
                "enabled": False,
            },
        },
    )
    assert resp.status_code == 200
    updated = resp.json()["data"]
    assert updated["name"] == "Updated criteria"
    assert updated["enabled"] is False

    # Delete
    resp = client.post(
        "/learning/success-criteria/delete", json={"criteria_id": sc_id}
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["criteria_id"] == sc_id

    # Get after delete -> 404
    resp = client.get(f"/learning/success-criteria/get?criteria_id={sc_id}")
    assert resp.status_code == 404


def test_success_criteria_get_not_found(client: TestClient) -> None:
    resp = client.get("/learning/success-criteria/get?criteria_id=nonexistent")
    assert resp.status_code == 404


def test_success_criteria_update_not_found(client: TestClient) -> None:
    resp = client.post(
        "/learning/success-criteria/update",
        json={
            "criteria_id": "nonexistent",
            "update_data": {"name": "x"},
        },
    )
    assert resp.status_code == 404


def test_success_criteria_delete_not_found(client: TestClient) -> None:
    resp = client.post(
        "/learning/success-criteria/delete", json={"criteria_id": "nonexistent"}
    )
    assert resp.status_code == 404


def test_success_criteria_list_pagination(client: TestClient) -> None:
    for i in range(3):
        _create_criteria(client, name=f"Criteria {i}")

    resp = client.get("/learning/success-criteria/list?limit=2")
    assert resp.status_code == 200
    page = resp.json()["data"]
    assert len(page["items"]) == 2
    assert page["has_next"] is True
    assert page["next_cursor"] is not None

    resp2 = client.get(
        f"/learning/success-criteria/list?limit=2&cursor={page['next_cursor']}"
    )
    assert resp2.status_code == 200
    page2 = resp2.json()["data"]
    assert len(page2["items"]) == 1
    assert page2["has_next"] is False


# ═══════════════════════════════════════════════════════════════════════
# Learned Paths (/learning/paths/*)
# ═══════════════════════════════════════════════════════════════════════


def _create_path(client: TestClient, **overrides) -> dict:
    payload = {
        "page_signature": overrides.get("page_signature", "https://example.com/form"),
        "goal_type": overrides.get("goal_type", "submit"),
        "steps_json": overrides.get(
            "steps_json",
            [{"action": "fill", "target": "#name", "value": "Test"}],
        ),
        "confidence": overrides.get("confidence", 0.9),
    }
    payload.update(overrides)
    resp = client.post("/learning/paths/create", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def test_learned_path_crud(client: TestClient) -> None:
    # Create
    path = _create_path(client)
    path_id = path["id"]
    assert path["page_signature"] == "https://example.com/form"
    assert path["goal_type"] == "submit"
    assert path["status"] == "candidate"
    assert path["confidence"] == 0.9

    # List
    resp = client.get("/learning/paths/list")
    assert resp.status_code == 200
    page = resp.json()["data"]
    assert len(page["items"]) >= 1

    # Get
    resp = client.get(f"/learning/paths/get?path_id={path_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["goal_type"] == "submit"

    # Update
    resp = client.post(
        "/learning/paths/update",
        json={
            "path_id": path_id,
            "update_data": {
                "status": "approved",
                "confidence": 0.95,
                "recommended": True,
            },
        },
    )
    assert resp.status_code == 200
    updated = resp.json()["data"]
    assert updated["status"] == "approved"
    assert updated["confidence"] == 0.95
    assert updated["recommended"] is True

    # Delete
    resp = client.post("/learning/paths/delete", json={"path_id": path_id})
    assert resp.status_code == 200
    assert resp.json()["data"]["path_id"] == path_id

    # Get after delete -> 404
    resp = client.get(f"/learning/paths/get?path_id={path_id}")
    assert resp.status_code == 404


def test_learned_path_get_not_found(client: TestClient) -> None:
    resp = client.get("/learning/paths/get?path_id=nonexistent")
    assert resp.status_code == 404


def test_learned_path_update_not_found(client: TestClient) -> None:
    resp = client.post(
        "/learning/paths/update",
        json={
            "path_id": "nonexistent",
            "update_data": {"status": "approved"},
        },
    )
    assert resp.status_code == 404


def test_learned_path_delete_not_found(client: TestClient) -> None:
    resp = client.post(
        "/learning/paths/delete", json={"path_id": "nonexistent"}
    )
    assert resp.status_code == 404


def test_learned_path_with_success_criteria_fk(client: TestClient) -> None:
    """Create a path referencing a real SuccessCriteria."""
    sc = _create_criteria(client)
    path = _create_path(client, success_criteria_id=sc["id"])
    assert path["success_criteria_id"] == sc["id"]


def test_learned_path_with_invalid_criteria_fk(client: TestClient) -> None:
    """Creating a path with a non-existent success_criteria_id should 404."""
    resp = client.post(
        "/learning/paths/create",
        json={
            "page_signature": "https://example.com",
            "goal_type": "submit",
            "success_criteria_id": "nonexistent-criteria",
            "steps_json": [],
            "confidence": 0.5,
        },
    )
    assert resp.status_code == 404


def test_learned_path_list_pagination(client: TestClient) -> None:
    for i in range(3):
        _create_path(client, page_signature=f"https://example.com/{i}")

    resp = client.get("/learning/paths/list?limit=2")
    assert resp.status_code == 200
    page = resp.json()["data"]
    assert len(page["items"]) == 2
    assert page["has_next"] is True

    resp2 = client.get(
        f"/learning/paths/list?limit=2&cursor={page['next_cursor']}"
    )
    assert resp2.status_code == 200
    page2 = resp2.json()["data"]
    assert len(page2["items"]) == 1
    assert page2["has_next"] is False


# ═══════════════════════════════════════════════════════════════════════
# Exploration Runs (/learning/runs/*)
# ═══════════════════════════════════════════════════════════════════════


def _create_run(client: TestClient, **overrides) -> dict:
    payload = {
        "page_signature": overrides.get(
            "page_signature", "https://example.com/search"
        ),
        "mode": overrides.get("mode", "form"),
        "status": overrides.get("status", "pending"),
        "strategy_json": overrides.get("strategy_json", {"approach": "fill-all"}),
    }
    payload.update(overrides)
    resp = client.post("/learning/runs/create", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def test_exploration_run_crud(client: TestClient) -> None:
    # Create
    run = _create_run(client)
    run_id = run["id"]
    assert run["mode"] == "form"
    assert run["status"] == "pending"
    assert run["page_signature"] == "https://example.com/search"

    # List
    resp = client.get("/learning/runs/list")
    assert resp.status_code == 200
    page = resp.json()["data"]
    assert len(page["items"]) >= 1

    # Get
    resp = client.get(f"/learning/runs/get?run_id={run_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == run_id

    # Update
    resp = client.post(
        "/learning/runs/update",
        json={
            "run_id": run_id,
            "update_data": {
                "status": "completed",
                "summary": "All steps passed",
            },
        },
    )
    assert resp.status_code == 200
    updated = resp.json()["data"]
    assert updated["status"] == "completed"
    assert updated["summary"] == "All steps passed"

    # Delete
    resp = client.post("/learning/runs/delete", json={"run_id": run_id})
    assert resp.status_code == 200
    assert resp.json()["data"]["run_id"] == run_id

    # Get after delete -> 404
    resp = client.get(f"/learning/runs/get?run_id={run_id}")
    assert resp.status_code == 404


def test_exploration_run_get_not_found(client: TestClient) -> None:
    resp = client.get("/learning/runs/get?run_id=nonexistent")
    assert resp.status_code == 404


def test_exploration_run_update_not_found(client: TestClient) -> None:
    resp = client.post(
        "/learning/runs/update",
        json={
            "run_id": "nonexistent",
            "update_data": {"status": "completed"},
        },
    )
    assert resp.status_code == 404


def test_exploration_run_delete_not_found(client: TestClient) -> None:
    resp = client.post(
        "/learning/runs/delete", json={"run_id": "nonexistent"}
    )
    assert resp.status_code == 404


def test_exploration_run_list_pagination(client: TestClient) -> None:
    for i in range(3):
        _create_run(client, page_signature=f"https://example.com/{i}")

    resp = client.get("/learning/runs/list?limit=2")
    assert resp.status_code == 200
    page = resp.json()["data"]
    assert len(page["items"]) == 2
    assert page["has_next"] is True

    resp2 = client.get(
        f"/learning/runs/list?limit=2&cursor={page['next_cursor']}"
    )
    assert resp2.status_code == 200
    page2 = resp2.json()["data"]
    assert len(page2["items"]) == 1
    assert page2["has_next"] is False


# ── Infer-candidates endpoint ──


def test_infer_candidates_recording_not_found(client: TestClient) -> None:
    resp = client.post(
        "/learning/runs/infer-candidates",
        json={"recording_id": "nonexistent"},
    )
    assert resp.status_code == 404


def test_infer_candidates_no_captured_html(client: TestClient) -> None:
    """Recording exists but meta has no capturedHtml."""
    rec = client.post(
        "/recordings/create",
        json={
            "name": "No HTML recording",
            "source": "extension",
            "events": [{"type": "click", "selector": "#btn"}],
            "meta": {"page": "test"},
        },
    )
    rec_id = rec.json()["data"]["id"]

    resp = client.post(
        "/learning/runs/infer-candidates",
        json={"recording_id": rec_id},
    )
    assert resp.status_code == 400
    assert "capturedHtml" in resp.json()["msg"]


def test_infer_candidates_success(client: TestClient) -> None:
    """Mock parse_html and infer_candidates to test the endpoint wiring."""
    rec = client.post(
        "/recordings/create",
        json={
            "name": "HTML recording",
            "source": "extension",
            "events": [],
            "meta": {"capturedHtml": "<html><body><input/></body></html>"},
        },
    )
    rec_id = rec.json()["data"]["id"]

    fake_candidates = [
        {"element_key": "input#search", "score": 0.9, "actions": ["fill"]}
    ]
    fake_hints = [
        {"element_key": "input#search", "action": "fill", "priority": 1}
    ]
    fake_ast = object()  # parse_html return value; passed through to infer_candidates

    with (
        patch(
            "app.routers.learning_runs.parse_html", return_value=fake_ast
        ) as mock_parse,
        patch(
            "app.routers.learning_runs.infer_candidates",
            return_value=(fake_candidates, fake_hints),
        ) as mock_infer,
    ):
        resp = client.post(
            "/learning/runs/infer-candidates",
            json={"recording_id": rec_id},
        )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["recording_id"] == rec_id
    assert data["candidate_count"] == 1
    assert data["hint_count"] == 1
    assert data["candidate_elements"] == fake_candidates
    assert data["interaction_hints"] == fake_hints
    assert data["written_to_run"] is None
    mock_parse.assert_called_once()
    mock_infer.assert_called_once()


def test_infer_candidates_writes_to_run(client: TestClient) -> None:
    """When run_id is provided, results are written back to the ExplorationRun."""
    rec = client.post(
        "/recordings/create",
        json={
            "name": "HTML recording 2",
            "source": "extension",
            "events": [],
            "meta": {"capturedHtml": "<html><body><button>Go</button></body></html>"},
        },
    )
    rec_id = rec.json()["data"]["id"]
    run = _create_run(client)
    run_id = run["id"]

    fake_candidates = [{"element_key": "button", "score": 0.8}]
    fake_hints = []
    fake_ast = object()

    with (
        patch(
            "app.routers.learning_runs.parse_html", return_value=fake_ast
        ),
        patch(
            "app.routers.learning_runs.infer_candidates",
            return_value=(fake_candidates, fake_hints),
        ),
    ):
        resp = client.post(
            "/learning/runs/infer-candidates",
            json={"recording_id": rec_id, "run_id": run_id},
        )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["written_to_run"] == run_id

    # Verify the run was updated
    get_resp = client.get(f"/learning/runs/get?run_id={run_id}")
    assert get_resp.status_code == 200
    run_data = get_resp.json()["data"]
    assert run_data["candidate_elements_json"] == fake_candidates
    assert run_data["interaction_hints_json"] == fake_hints


def test_infer_candidates_custom_thresholds(client: TestClient) -> None:
    """Verify score_threshold and max_candidates are forwarded."""
    rec = client.post(
        "/recordings/create",
        json={
            "name": "Threshold test",
            "source": "extension",
            "events": [],
            "meta": {"capturedHtml": "<html><body>Hi</body></html>"},
        },
    )
    rec_id = rec.json()["data"]["id"]
    fake_ast = object()

    with (
        patch(
            "app.routers.learning_runs.parse_html", return_value=fake_ast
        ),
        patch(
            "app.routers.learning_runs.infer_candidates",
            return_value=([], []),
        ) as mock_infer,
    ):
        resp = client.post(
            "/learning/runs/infer-candidates",
            json={
                "recording_id": rec_id,
                "score_threshold": 0.5,
                "max_candidates": 50,
            },
        )

    assert resp.status_code == 200
    _, kwargs = mock_infer.call_args
    assert kwargs["score_threshold"] == 0.5
    assert kwargs["max_candidates"] == 50


# ═══════════════════════════════════════════════════════════════════════
# Exploration Workbench (/exploration/*)
# ═══════════════════════════════════════════════════════════════════════


def test_exploration_list_tasks(client: TestClient) -> None:
    """List task definitions (mocked to avoid filesystem dependency)."""
    from app.schemas.task_definition import TaskDefinition, TaskStep

    fake_tasks = [
        TaskDefinition(
            id="test-task-1",
            name="Test Task",
            description="A test",
            target_url="https://example.com",
            steps=[
                TaskStep(intent="fill_form", action_type="fill"),
                TaskStep(intent="submit", action_type="click"),
            ],
            source="builtin",
        ),
    ]
    with patch("app.routers.exploration.list_tasks", return_value=[]) as _:
        # Re-patch at the lazy import location inside the endpoint
        pass

    # The endpoint does a lazy import: from app.services.task_loader import list_tasks as _list
    with patch(
        "app.services.task_loader.list_tasks", return_value=fake_tasks
    ):
        resp = client.get("/exploration/tasks")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == "test-task-1"
    assert data[0]["name"] == "Test Task"
    assert data[0]["step_count"] == 2
    assert data[0]["source"] == "builtin"


def test_exploration_list_tasks_empty(client: TestClient) -> None:
    with patch("app.services.task_loader.list_tasks", return_value=[]):
        resp = client.get("/exploration/tasks")

    assert resp.status_code == 200
    assert resp.json()["data"] == []


def test_exploration_get_task(client: TestClient) -> None:
    from app.schemas.task_definition import TaskDefinition

    fake_task = TaskDefinition(
        id="search-basic",
        name="Search",
        description="Do a search",
        target_url="https://google.com",
        steps=[],
        source="builtin",
    )
    with patch(
        "app.services.task_loader.load_task_by_id", return_value=fake_task
    ):
        resp = client.get("/exploration/tasks/search-basic")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == "search-basic"
    assert data["name"] == "Search"
    assert data["target_url"] == "https://google.com"


def test_exploration_get_task_not_found(client: TestClient) -> None:
    with patch(
        "app.services.task_loader.load_task_by_id",
        side_effect=FileNotFoundError("Task not found"),
    ):
        resp = client.get("/exploration/tasks/nonexistent")
    assert resp.status_code == 404


def test_exploration_approve_run(client: TestClient) -> None:
    resp = client.post(
        "/exploration/runs/run-123/approve",
        json={"run_id": "run-123", "note": "LGTM"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["run_id"] == "run-123"
    assert data["status"] == "approved"


def test_exploration_approve_run_no_body(client: TestClient) -> None:
    """Approve endpoint works without a body (payload is optional)."""
    resp = client.post("/exploration/runs/run-456/approve")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["run_id"] == "run-456"
    assert data["status"] == "approved"


def test_exploration_reject_run(client: TestClient) -> None:
    resp = client.post(
        "/exploration/runs/run-789/reject",
        json={"run_id": "run-789", "note": "Not accurate"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["run_id"] == "run-789"
    assert data["status"] == "rejected"


def test_exploration_reject_run_no_body(client: TestClient) -> None:
    resp = client.post("/exploration/runs/run-000/reject")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["run_id"] == "run-000"
    assert data["status"] == "rejected"


def test_exploration_run_endpoint_success(client: TestClient) -> None:
    from app.schemas.execution import ExecutionResult, PageStateChange
    from app.schemas.exploration_run import ExplorationResult, ExplorationStepLog
    from app.schemas.observation import PostActionObservation
    from app.schemas.success_criteria import SuccessEvaluation
    from app.schemas.task_definition import TaskDefinition, TaskStep

    task = TaskDefinition(
        id="search-task",
        name="Search Task",
        description="Run a search",
        target_url="https://example.com",
        variables={"query": "default"},
        steps=[TaskStep(intent="search", action_type="fill", value_from="query")],
        source="builtin",
    )
    step = ExplorationStepLog(
        step_index=0,
        intent="search",
        action_type="fill",
        target_summary="search box",
        value="override",
        timestamp_ms=1234,
        agent_note="picked top candidate",
        execution_result=ExecutionResult(
            ok=True,
            action_type="fill",
            target_summary="search box",
            page_change=PageStateChange(title_before="Before", title_after="After"),
        ),
        observation=PostActionObservation(title="After", html_hash="abc"),
        success_evaluation=SuccessEvaluation(satisfied=True, confidence="high"),
    )
    result = ExplorationResult(
        success=True,
        steps=[step],
        total_steps=1,
        final_url="https://example.com/results",
        final_title="Results",
        final_screenshot_ref="shot.png",
        summary="exploration ok",
        elapsed_ms=321,
    )
    assessment = SimpleNamespace(
        verdict="success",
        confidence="high",
        summary="looks good",
        step_assessments=[{"step_index": 0, "verdict": "ok"}],
        anomalies=["minor"],
        suggestions=["save path"],
        should_save_path=True,
    )
    fake_runtime = SimpleNamespace()
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = fake_runtime
    fake_cm.__exit__.return_value = False

    with (
        patch("app.services.task_loader.load_task_by_id", return_value=task),
        patch(
            "app.services.execution.execution_runtime.create_execution_runtime",
            return_value=fake_cm,
        ) as mock_runtime_factory,
        patch(
            "app.services.learning.exploration_loop.run_exploration",
            return_value=result,
        ) as mock_run,
        patch(
            "app.services.learning.exploration_supervisor.summarize_exploration",
            return_value=assessment,
        ) as mock_supervisor,
    ):
        resp = client.post(
            "/exploration/run",
            json={
                "task_id": "search-task",
                "variables": {"query": "override"},
                "headless": True,
                "max_steps": 2,
            },
        )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["success"] is True
    assert data["final_url"] == "https://example.com/results"
    assert data["steps"][0]["execution_result"]["ok"] is True
    assert data["steps"][0]["observation"]["title"] == "After"
    assert data["steps"][0]["success_evaluation"]["satisfied"] is True
    assert data["supervisor"]["verdict"] == "success"
    mock_runtime_factory.assert_called_once_with(headless=True)
    passed_task, passed_runtime = mock_run.call_args.args[:2]
    assert passed_task.variables["query"] == "override"
    assert passed_runtime is fake_runtime
    assert mock_run.call_args.kwargs["max_steps"] == 2
    mock_supervisor.assert_called_once()


def test_exploration_run_endpoint_supervisor_failure(client: TestClient) -> None:
    from app.schemas.exploration_run import ExplorationResult
    from app.schemas.task_definition import TaskDefinition

    task = TaskDefinition(
        id="simple-task",
        name="Simple",
        description="simple",
        target_url="https://example.com",
        steps=[],
        source="builtin",
    )
    result = ExplorationResult(
        success=False,
        steps=[],
        total_steps=0,
        final_url="https://example.com",
        final_title="Home",
        summary="no-op",
        elapsed_ms=12,
    )
    fake_runtime = SimpleNamespace()
    fake_cm = MagicMock()
    fake_cm.__enter__.return_value = fake_runtime
    fake_cm.__exit__.return_value = False

    with (
        patch("app.services.task_loader.load_task_by_id", return_value=task),
        patch(
            "app.services.execution.execution_runtime.create_execution_runtime",
            return_value=fake_cm,
        ),
        patch(
            "app.services.learning.exploration_loop.run_exploration",
            return_value=result,
        ),
        patch(
            "app.services.learning.exploration_supervisor.summarize_exploration",
            side_effect=Exception("supervisor boom"),
        ),
    ):
        resp = client.post("/exploration/run", json={"task_id": "simple-task"})

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["success"] is False
    assert data["supervisor"] is None


# ═══════════════════════════════════════════════════════════════════════
# AST Router (/ast/*)
# ═══════════════════════════════════════════════════════════════════════


def test_ast_parse_basic(client: TestClient) -> None:
    resp = client.post(
        "/ast/parse",
        json={"html": "<html><body><div>Hello</div></body></html>"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["node_count"] >= 1
    assert data["nodes"][0]["tag"] == "div"


def test_ast_parse_fragment(client: TestClient) -> None:
    resp = client.post(
        "/ast/parse",
        json={"html": "<div><span>text</span></div>"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["nodes"][0]["tag"] == "div"
    assert data["nodes"][0]["children"][0]["tag"] == "span"


def test_ast_parse_with_iframe_html(client: TestClient) -> None:
    resp = client.post(
        "/ast/parse",
        json={
            "html": '<html><body><iframe src="about:blank"></iframe></body></html>',
            "iframe_html": {"about:blank": "<html><body><p>iframe content</p></body></html>"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["nodes"][0]["tag"] == "iframe"
    assert data["nodes"][0]["children"][0]["tag"] == "frame-body"


def test_ast_simplify_basic(client: TestClient) -> None:
    resp = client.post(
        "/ast/simplify",
        json={"html": "<html><body><input type='text' name='q'/></body></html>"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["nodes"][0]["tag"] == "input"
    assert data["stats"]["node_count"] == 1


def test_ast_simplify_with_iframe_html(client: TestClient) -> None:
    resp = client.post(
        "/ast/simplify",
        json={
            "html": '<html><body><iframe src="x"></iframe></body></html>',
            "iframe_html": {"x": "<html><body>hi</body></html>"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["nodes"][0]["tag"] == "iframe"
    assert data["nodes"][0]["children"][0]["tag"] == "frame-body"


# ═══════════════════════════════════════════════════════════════════════
# Envelope format validation
# ═══════════════════════════════════════════════════════════════════════


def test_all_responses_use_envelope(client: TestClient) -> None:
    """Verify code/msg/data envelope structure on a few endpoints."""
    endpoints = [
        ("GET", "/learning/feedback/list"),
        ("GET", "/learning/success-criteria/list"),
        ("GET", "/learning/paths/list"),
        ("GET", "/learning/runs/list"),
    ]
    for method, url in endpoints:
        resp = client.request(method, url)
        body = resp.json()
        assert body["code"] == 0, f"{url}: code != 0"
        assert body["msg"] == "ok", f"{url}: msg != ok"
        assert "data" in body, f"{url}: missing data"
