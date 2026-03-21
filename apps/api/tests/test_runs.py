from fastapi.testclient import TestClient


def test_run_crud(client: TestClient) -> None:
    skill_response = client.post(
        "/skills/create",
        json={
            "name": "Run target skill",
            "definition": {"steps": [{"action": "navigate"}]},
        },
    )
    skill_id = skill_response.json()["id"]

    create_response = client.post(
        "/runs/create",
        json={
            "skill_id": skill_id,
            "input_payload": {"url": "https://example.com"},
            "logs": [{"level": "info", "message": "queued"}],
        },
    )
    assert create_response.status_code == 201
    run = create_response.json()
    run_id = run["id"]
    assert run["status"] == "pending"

    update_response = client.post(
        "/runs/update",
        json={
            "run_id": run_id,
            "update_data": {
                "status": "succeeded",
                "result_payload": {"ok": True},
                "logs": [{"level": "info", "message": "done"}],
            },
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["status"] == "succeeded"
    assert updated["result_payload"] == {"ok": True}

    get_response = client.get(f"/runs/get?run_id={run_id}")
    assert get_response.status_code == 200
    assert get_response.json()["skill_id"] == skill_id

    delete_response = client.post(
        "/runs/delete",
        json={"run_id": run_id},
    )
    assert delete_response.status_code == 204


def test_run_requires_existing_skill(client: TestClient) -> None:
    response = client.post(
        "/runs/create",
        json={
            "skill_id": "missing-skill",
            "input_payload": {"url": "https://example.com"},
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Skill 'missing-skill' was not found."
