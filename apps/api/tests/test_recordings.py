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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_ID = "00000000-0000-0000-0000-000000000000"

_SAMPLE_EVENTS = [
    {"type": "navigate", "timestamp": 1000, "url": "http://example.com/page", "title": "Page"},
    {
        "type": "click",
        "timestamp": 2000,
        "url": "http://example.com/page",
        "target": {"tag": "button", "text": "Save"},
    },
]


def _create_recording(client: TestClient, **overrides) -> str:
    """Create a recording and return its id."""
    payload = {
        "name": overrides.pop("name", "Test recording"),
        "source": overrides.pop("source", "extension"),
        "events": overrides.pop("events", _SAMPLE_EVENTS),
        "meta": overrides.pop("meta", None),
    }
    payload.update(overrides)
    resp = client.post("/recordings/create", json=payload)
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


# ---------------------------------------------------------------------------
# Not-found error cases for every endpoint that takes recording_id
# ---------------------------------------------------------------------------


def test_get_normalized_not_found(client: TestClient) -> None:
    resp = client.get(f"/recordings/get_normalized?recording_id={FAKE_ID}")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 404
    assert "not found" in body["msg"].lower()


def test_get_steps_not_found(client: TestClient) -> None:
    resp = client.get(f"/recordings/get_steps?recording_id={FAKE_ID}")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 404
    assert "not found" in body["msg"].lower()


def test_get_agent_steps_not_found(client: TestClient) -> None:
    resp = client.get(f"/recordings/get_agent_steps?recording_id={FAKE_ID}")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 404
    assert "not found" in body["msg"].lower()


def test_get_page_understanding_not_found(client: TestClient) -> None:
    resp = client.get(f"/recordings/get_page_understanding?recording_id={FAKE_ID}")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 404


def test_get_step_understanding_not_found(client: TestClient) -> None:
    resp = client.get(f"/recordings/get_step_understanding?recording_id={FAKE_ID}")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 404


def test_get_combined_understanding_not_found(client: TestClient) -> None:
    resp = client.get(f"/recordings/get_understanding?recording_id={FAKE_ID}")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 404


def test_update_not_found(client: TestClient) -> None:
    resp = client.post(
        "/recordings/update",
        json={"recording_id": FAKE_ID, "update_data": {"name": "nope"}},
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 404


def test_delete_not_found(client: TestClient) -> None:
    resp = client.post("/recordings/delete", json={"recording_id": FAKE_ID})
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == 404


# ---------------------------------------------------------------------------
# get_steps endpoint
# ---------------------------------------------------------------------------


def test_get_steps_basic(client: TestClient) -> None:
    """get_steps returns OperationStepResult with steps built from events."""
    recording_id = _create_recording(client)
    resp = client.get(f"/recordings/get_steps?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["recording_id"] == recording_id
    assert isinstance(data["steps"], list)
    assert data["event_count"] == len(_SAMPLE_EVENTS)
    assert "mutation_count" in data
    assert "mutations_correlated" in data
    assert "mutations_uncorrelated" in data


def test_get_steps_empty_events(client: TestClient) -> None:
    """get_steps with no events returns zero counts."""
    recording_id = _create_recording(client, events=[])
    resp = client.get(f"/recordings/get_steps?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["steps"] == []
    assert data["event_count"] == 0


def test_get_steps_with_dom_mutations(client: TestClient) -> None:
    """get_steps picks up domMutations from meta."""
    mutations = [
        {
            "id": "m1",
            "timestamp": 2100,
            "type": "childList",
            "target": {"tag": "div", "id": "content"},
        },
    ]
    recording_id = _create_recording(
        client,
        events=_SAMPLE_EVENTS,
        meta={"domMutations": mutations},
    )
    resp = client.get(f"/recordings/get_steps?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["mutation_count"] == 1


# ---------------------------------------------------------------------------
# get_agent_steps endpoint
# ---------------------------------------------------------------------------


def test_get_agent_steps_basic(client: TestClient) -> None:
    """get_agent_steps returns AgentStepListView."""
    recording_id = _create_recording(client)
    resp = client.get(f"/recordings/get_agent_steps?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["recording_id"] == recording_id
    assert isinstance(data["steps"], list)
    assert "step_count" in data
    assert "has_mutations" in data
    assert data["step_count"] == len(data["steps"])


def test_get_agent_steps_empty_events(client: TestClient) -> None:
    recording_id = _create_recording(client, events=[])
    resp = client.get(f"/recordings/get_agent_steps?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["steps"] == []
    assert data["step_count"] == 0
    assert data["has_mutations"] is False


# ---------------------------------------------------------------------------
# get_steps / get_agent_steps with server AST enhancement (capturedHtml)
# ---------------------------------------------------------------------------


def test_get_steps_with_captured_html(client: TestClient) -> None:
    """When meta has capturedHtml, events are enhanced via server AST matching."""
    html = "<html><body><button>Save</button></body></html>"
    recording_id = _create_recording(
        client,
        events=_SAMPLE_EVENTS,
        meta={"capturedHtml": html},
    )
    resp = client.get(f"/recordings/get_steps?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["recording_id"] == recording_id
    # The enhancement runs without error even if no match found
    assert isinstance(data["steps"], list)


def test_get_agent_steps_with_captured_html(client: TestClient) -> None:
    """get_agent_steps also runs server AST enhancement when capturedHtml exists."""
    html = "<html><body><button>Save</button></body></html>"
    recording_id = _create_recording(
        client,
        events=_SAMPLE_EVENTS,
        meta={"capturedHtml": html},
    )
    resp = client.get(f"/recordings/get_agent_steps?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["recording_id"] == recording_id
    assert isinstance(data["steps"], list)


# ---------------------------------------------------------------------------
# Pagination: cursor-based listing
# ---------------------------------------------------------------------------


def test_list_pagination_cursor(client: TestClient) -> None:
    """Create enough recordings to test cursor-based pagination."""
    ids = []
    for i in range(3):
        rid = _create_recording(client, name=f"Rec {i}")
        ids.append(rid)

    # Fetch first page with limit=2
    resp1 = client.get("/recordings/list?limit=2")
    assert resp1.status_code == 200
    page1 = resp1.json()["data"]
    assert len(page1["items"]) == 2
    assert page1["has_next"] is True
    assert page1["next_cursor"] is not None

    # Fetch second page using cursor
    resp2 = client.get(f"/recordings/list?limit=2&cursor={page1['next_cursor']}")
    assert resp2.status_code == 200
    page2 = resp2.json()["data"]
    assert len(page2["items"]) >= 1
    # Items on page2 should differ from page1
    page1_ids = {item["id"] for item in page1["items"]}
    page2_ids = {item["id"] for item in page2["items"]}
    assert page1_ids.isdisjoint(page2_ids)


def test_list_pagination_no_cursor(client: TestClient) -> None:
    """Listing with no cursor and few recordings works."""
    _create_recording(client, name="Single rec")
    resp = client.get("/recordings/list?limit=10")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data["items"]) >= 1
    assert data["has_next"] is False
    assert data["next_cursor"] is None


# ---------------------------------------------------------------------------
# Update and delete operations (dedicated tests beyond the CRUD combo)
# ---------------------------------------------------------------------------


def test_update_partial_fields(client: TestClient) -> None:
    """Update only name, leaving other fields unchanged."""
    recording_id = _create_recording(client, name="Original")
    resp = client.post(
        "/recordings/update",
        json={"recording_id": recording_id, "update_data": {"name": "Renamed"}},
    )
    assert resp.status_code == 200
    updated = resp.json()["data"]
    assert updated["name"] == "Renamed"
    assert updated["status"] == "draft"  # unchanged


def test_update_events_field(client: TestClient) -> None:
    """Update the events list on a recording."""
    recording_id = _create_recording(client, events=[])
    new_events = [{"type": "click", "timestamp": 1000, "url": "http://example.com"}]
    resp = client.post(
        "/recordings/update",
        json={"recording_id": recording_id, "update_data": {"events": new_events}},
    )
    assert resp.status_code == 200
    updated = resp.json()["data"]
    assert len(updated["events"]) == 1


def test_delete_then_list(client: TestClient) -> None:
    """After deleting the only recording, list returns empty."""
    recording_id = _create_recording(client)
    client.post("/recordings/delete", json={"recording_id": recording_id})
    resp = client.get("/recordings/list")
    assert resp.status_code == 200
    assert resp.json()["data"]["items"] == []


# ---------------------------------------------------------------------------
# Understanding endpoints — mock LLM to avoid real API calls
# ---------------------------------------------------------------------------

from unittest.mock import patch


def _fake_page_understanding(*args, **kwargs):
    """Return a successful page understanding result without calling LLM."""
    return {
        "ok": True,
        "understanding": {
            "page_kind": "form",
            "page_goal": "Test page",
            "primary_regions": [],
            "primary_actions": [],
            "key_entities": [],
            "confidence_notes": [],
        },
        "error": None,
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def _fake_step_understanding(*args, **kwargs):
    """Return a successful step understanding result without calling LLM."""
    return {
        "ok": True,
        "understanding": {
            "common_step_patterns": ["User navigated and clicked."],
            "likely_key_steps": [],
            "likely_expand_steps": [],
            "likely_submit_steps": [],
            "likely_no_change_steps": [],
            "observed_change_patterns": [],
            "step_descriptions": [],
            "confidence_notes": [],
        },
        "error": None,
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def _fake_page_understanding_fail(*args, **kwargs):
    return {
        "ok": False,
        "understanding": None,
        "error": {"kind": "api_error", "message": "Mocked LLM failure"},
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def _fake_step_understanding_fail(*args, **kwargs):
    return {
        "ok": False,
        "understanding": None,
        "error": {"kind": "api_error", "message": "Mocked LLM failure"},
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@patch("app.routers.recordings.generate_page_understanding", side_effect=_fake_page_understanding)
def test_get_page_understanding_ok(mock_gen, client: TestClient) -> None:
    """get_page_understanding returns an UnderstandingResponse when LLM succeeds."""
    recording_id = _create_recording(client)
    resp = client.get(f"/recordings/get_page_understanding?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["ok"] is True
    assert data["understanding"]["page_kind"] == "form"
    mock_gen.assert_called_once()


@patch("app.routers.recordings.generate_page_understanding", side_effect=_fake_page_understanding)
def test_get_page_understanding_with_html(mock_gen, client: TestClient) -> None:
    """When capturedHtml exists, a simplified AST is built and passed to the builder."""
    html = "<html><body><form><input name='q'></form></body></html>"
    recording_id = _create_recording(client, meta={"capturedHtml": html})
    resp = client.get(f"/recordings/get_page_understanding?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["ok"] is True
    mock_gen.assert_called_once()


@patch("app.routers.recordings.generate_step_understanding", side_effect=_fake_step_understanding)
def test_get_step_understanding_ok(mock_gen, client: TestClient) -> None:
    """get_step_understanding returns an UnderstandingResponse when LLM succeeds."""
    recording_id = _create_recording(client)
    resp = client.get(f"/recordings/get_step_understanding?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["ok"] is True
    assert isinstance(data["understanding"]["common_step_patterns"], list)
    mock_gen.assert_called_once()


@patch("app.routers.recordings.generate_step_understanding", side_effect=_fake_step_understanding)
def test_get_step_understanding_with_html(mock_gen, client: TestClient) -> None:
    """Server AST enhancement is applied when capturedHtml is present."""
    html = "<html><body><button>Save</button></body></html>"
    recording_id = _create_recording(
        client,
        events=_SAMPLE_EVENTS,
        meta={"capturedHtml": html},
    )
    resp = client.get(f"/recordings/get_step_understanding?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["ok"] is True


@patch("app.routers.recordings.generate_page_understanding", side_effect=_fake_page_understanding)
@patch("app.routers.recordings.generate_step_understanding", side_effect=_fake_step_understanding)
def test_get_combined_understanding_ok(mock_step, mock_page, client: TestClient) -> None:
    """Combined understanding merges page + step results."""
    recording_id = _create_recording(client)
    resp = client.get(f"/recordings/get_understanding?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["ok"] is True
    assert data["understanding"] is not None
    assert data["error"] is None
    mock_page.assert_called_once()
    mock_step.assert_called_once()


@patch("app.routers.recordings.generate_page_understanding", side_effect=_fake_page_understanding)
@patch("app.routers.recordings.generate_step_understanding", side_effect=_fake_step_understanding)
def test_get_combined_understanding_with_html(mock_step, mock_page, client: TestClient) -> None:
    """Combined understanding builds simplified AST when capturedHtml is present."""
    html = "<html><body><h1>Dashboard</h1></body></html>"
    recording_id = _create_recording(
        client,
        events=_SAMPLE_EVENTS,
        meta={"capturedHtml": html},
    )
    resp = client.get(f"/recordings/get_understanding?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["ok"] is True
    assert data["understanding"] is not None


@patch("app.routers.recordings.generate_page_understanding", side_effect=_fake_page_understanding_fail)
def test_get_combined_understanding_page_fail(mock_page, client: TestClient) -> None:
    """Combined understanding returns early when page understanding fails."""
    recording_id = _create_recording(client)
    resp = client.get(f"/recordings/get_understanding?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["ok"] is False
    assert data["phase"] == "page_understanding"
    assert data["error"] is not None


@patch("app.routers.recordings.generate_page_understanding", side_effect=_fake_page_understanding)
@patch("app.routers.recordings.generate_step_understanding", side_effect=_fake_step_understanding_fail)
def test_get_combined_understanding_step_fail(mock_step, mock_page, client: TestClient) -> None:
    """Combined understanding returns early when step understanding fails."""
    recording_id = _create_recording(client)
    resp = client.get(f"/recordings/get_understanding?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["ok"] is False
    assert data["phase"] == "step_understanding"
    assert data["error"] is not None


# ---------------------------------------------------------------------------
# get_steps with alternative meta key names (captured_html / iframe_html)
# ---------------------------------------------------------------------------


def test_get_steps_with_snake_case_captured_html(client: TestClient) -> None:
    """_enhance_events_with_server_ast accepts snake_case meta keys too."""
    html = "<html><body><p>hello</p></body></html>"
    recording_id = _create_recording(
        client,
        events=_SAMPLE_EVENTS,
        meta={"captured_html": html},
    )
    resp = client.get(f"/recordings/get_steps?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data["steps"], list)


def test_get_steps_with_iframe_html(client: TestClient) -> None:
    """_enhance_events_with_server_ast passes iframe HTML to the parser."""
    html = "<html><body><iframe></iframe></body></html>"
    iframe_html = {"frame-0": "<html><body><p>inside</p></body></html>"}
    recording_id = _create_recording(
        client,
        events=_SAMPLE_EVENTS,
        meta={"capturedHtml": html, "iframeHtml": iframe_html},
    )
    resp = client.get(f"/recordings/get_steps?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data["steps"], list)


def test_get_steps_no_captured_html(client: TestClient) -> None:
    """Without capturedHtml, events pass through unenhanced."""
    recording_id = _create_recording(
        client,
        events=_SAMPLE_EVENTS,
        meta={"someOtherField": True},
    )
    resp = client.get(f"/recordings/get_steps?recording_id={recording_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert isinstance(data["steps"], list)
