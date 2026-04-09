from fastapi.testclient import TestClient


def test_get_normalized(client: TestClient) -> None:
    create_response = client.post(
        "/recordings/create",
        json={
            "name": "Normalizer test",
            "source": "extension",
            "events": [
                {"type": "navigate", "timestamp": 1000, "url": "http://example.com/list", "title": "List"},
                {"type": "input", "timestamp": 2000, "url": "http://example.com/list",
                 "target": {"tag": "input", "name": "q"}, "value": "foo",
                 "fieldContext": {"fieldLabel": "Search", "fieldProp": "q"}},
                {"type": "input", "timestamp": 2100, "url": "http://example.com/list",
                 "target": {"tag": "input", "name": "q"}, "value": "foobar",
                 "fieldContext": {"fieldLabel": "Search", "fieldProp": "q"}},
                {"type": "click", "timestamp": 3000, "url": "http://example.com/list",
                 "target": {"tag": "button", "text": "提交", "role": "button"}},
            ],
        },
    )
    recording_id = create_response.json()["data"]["id"]

    resp = client.get(f"/recordings/get_normalized?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["recording_id"] == recording_id
    summary = data["summary"]
    assert summary["event_count_raw"] == 4
    # Two consecutive inputs on same target → merged to 1
    assert summary["event_count_normalized"] == 3
    assert summary["contains_iframe"] is False
    assert summary["contains_richtext"] is False

    assert len(data["segments"]) > 0
    assert len(data["key_actions"]) > 0


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
    assert create_response.status_code == 200
    created = create_response.json()["data"]
    recording_id = created["id"]
    assert create_response.json()["code"] == 0
    assert created["status"] == "draft"

    list_response = client.get("/recordings/list")
    assert list_response.status_code == 200
    list_data = list_response.json()["data"]
    assert len(list_data["items"]) >= 1

    get_response = client.get(f"/recordings/get?recording_id={recording_id}")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["name"] == "Checkout flow"

    update_response = client.post(
        "/recordings/update",
        json={
            "recording_id": recording_id,
            "update_data": {"status": "completed", "name": "Checkout flow v2"},
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["status"] == "completed"
    assert updated["name"] == "Checkout flow v2"

    delete_response = client.post(
        "/recordings/delete",
        json={"recording_id": recording_id},
    )
    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "code": 0,
        "data": {"recording_id": recording_id},
        "msg": "ok",
    }

    missing_response = client.get(f"/recordings/get?recording_id={recording_id}")
    assert missing_response.status_code == 404
    assert missing_response.json() == {
        "code": 404,
        "msg": f"Recording '{recording_id}' was not found.",
        "data": None,
    }
