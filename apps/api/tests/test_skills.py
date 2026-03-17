from fastapi.testclient import TestClient


def test_skill_crud(client: TestClient) -> None:
    recording_response = client.post(
        "/recordings",
        json={
            "name": "Search recording",
            "source": "extension",
            "events": [{"type": "input", "selector": "#search"}],
        },
    )
    recording_id = recording_response.json()["id"]

    create_response = client.post(
        "/skills",
        json={
            "name": "Search skill",
            "recording_id": recording_id,
            "definition": {"steps": [{"action": "type"}]},
            "description": "Searches the target site",
        },
    )
    assert create_response.status_code == 201
    skill = create_response.json()
    skill_id = skill["id"]
    assert skill["recording_id"] == recording_id

    update_response = client.patch(
        f"/skills/{skill_id}",
        json={"status": "published", "version": "1.1.0"},
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["status"] == "published"
    assert updated["version"] == "1.1.0"

    get_response = client.get(f"/skills/{skill_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Search skill"

    delete_response = client.delete(f"/skills/{skill_id}")
    assert delete_response.status_code == 204


def test_skill_requires_existing_recording(client: TestClient) -> None:
    response = client.post(
        "/skills",
        json={
            "name": "Broken skill",
            "recording_id": "missing-recording",
            "definition": {"steps": []},
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Recording 'missing-recording' was not found."
