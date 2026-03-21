from fastapi.testclient import TestClient


def test_recording_crud(client: TestClient) -> None:
    create_response = client.post(
        "/recordings/create",
        json={
            "name": "Checkout flow",
            "source": "extension",
            "events": [{"type": "click", "selector": "#submit"}],
            "meta": {"page": "checkout"},
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    recording_id = created["id"]
    assert created["status"] == "draft"

    list_response = client.get("/recordings/list")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get(f"/recordings/get?recording_id={recording_id}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Checkout flow"

    update_response = client.post(
        "/recordings/update",
        json={
            "recording_id": recording_id,
            "update_data": {"status": "completed", "name": "Checkout flow v2"},
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["status"] == "completed"
    assert updated["name"] == "Checkout flow v2"

    delete_response = client.post(
        "/recordings/delete",
        json={"recording_id": recording_id},
    )
    assert delete_response.status_code == 204

    missing_response = client.get(f"/recordings/get?recording_id={recording_id}")
    assert missing_response.status_code == 404
