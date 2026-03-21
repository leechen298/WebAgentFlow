from fastapi.testclient import TestClient


def test_skill_crud(client: TestClient) -> None:
    recording_response = client.post(
        "/recordings/create",
        json={
            "name": "Search recording",
            "source": "extension",
            "events": [{"type": "input", "selector": "#search"}],
        },
    )
    recording_id = recording_response.json()["data"]["id"]

    create_response = client.post(
        "/skills/create",
        json={
            "name": "Search skill",
            "recording_id": recording_id,
            "definition": {"steps": [{"action": "type"}]},
            "description": "Searches the target site",
        },
    )
    assert create_response.status_code == 200
    skill = create_response.json()["data"]
    skill_id = skill["id"]
    assert skill["recording_id"] == recording_id

    list_response = client.get("/skills/list")
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1

    update_response = client.post(
        "/skills/update",
        json={
            "skill_id": skill_id,
            "update_data": {"status": "published", "version": "1.1.0"},
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["status"] == "published"
    assert updated["version"] == "1.1.0"

    get_response = client.get(f"/skills/get?skill_id={skill_id}")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["name"] == "Search skill"

    delete_response = client.post(
        "/skills/delete",
        json={"skill_id": skill_id},
    )
    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "code": 0,
        "data": {"skill_id": skill_id},
        "msg": "ok",
    }

    missing_response = client.get(f"/skills/get?skill_id={skill_id}")
    assert missing_response.status_code == 404
    assert missing_response.json() == {
        "code": 404,
        "msg": f"Skill '{skill_id}' was not found.",
        "data": None,
    }


def test_skill_requires_existing_recording(client: TestClient) -> None:
    response = client.post(
        "/skills/create",
        json={
            "name": "Broken skill",
            "recording_id": "missing-recording",
            "definition": {"steps": []},
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "code": 404,
        "msg": "Recording 'missing-recording' was not found.",
        "data": None,
    }
