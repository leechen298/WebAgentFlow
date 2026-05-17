"""Tests for M11.0 conversation HTTP API (11.0.3)."""

from __future__ import annotations

import inspect

from fastapi.testclient import TestClient

from app.models.learned_path import TrustStatus
from app.repos.learned_paths_repo import LearnedPathRepository
from app.schemas.conversation import ConversationReplaySummary

# ── Helpers ───────────────────────────────────────────────────────────────────


def _create_session(client: TestClient, **kwargs) -> str:
    resp = client.post("/conversation/sessions", json=kwargs)
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


# ── POST /conversation/sessions ───────────────────────────────────────────────


def test_create_session_defaults_to_idle(client: TestClient) -> None:
    resp = client.post("/conversation/sessions", json={})

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "idle"
    assert body["data"]["current_mode"] is None
    assert body["data"]["metadata"] == {}
    assert body["data"]["previous_status"] is None
    assert "id" in body["data"]
    assert "created_at" in body["data"]
    assert "updated_at" in body["data"]


def test_create_session_accepts_metadata(client: TestClient) -> None:
    resp = client.post(
        "/conversation/sessions",
        json={"current_mode": "replay", "metadata": {"source": "test"}},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["current_mode"] == "replay"
    assert data["metadata"] == {"source": "test"}


def test_create_session_rejects_initial_status(client: TestClient) -> None:
    resp = client.post(
        "/conversation/sessions",
        json={"initial_status": "replay_running"},
    )

    assert resp.status_code == 422


# ── GET /conversation/sessions/{session_id} ───────────────────────────────────


def test_get_session_reads_session(client: TestClient) -> None:
    session_id = _create_session(client)
    resp = client.get(f"/conversation/sessions/{session_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["id"] == session_id
    assert body["data"]["status"] == "idle"


def test_get_session_unknown_returns_404(client: TestClient) -> None:
    resp = client.get("/conversation/sessions/not-a-real-id")

    assert resp.status_code == 404


# ── POST /conversation/sessions/{session_id}/messages ─────────────────────────


def test_append_user_message(client: TestClient) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/conversation/sessions/{session_id}/messages",
        json={"role": "user", "content": "hello"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["role"] == "user"
    assert data["content"] == "hello"
    assert data["session_id"] == session_id
    assert "id" in data


def test_append_system_message(client: TestClient) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/conversation/sessions/{session_id}/messages",
        json={"role": "system", "content": "ack"},
    )

    assert resp.status_code == 200
    assert resp.json()["data"]["role"] == "system"


def test_append_engine_message(client: TestClient) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/conversation/sessions/{session_id}/messages",
        json={"role": "engine", "content": "done"},
    )

    assert resp.status_code == 200
    assert resp.json()["data"]["role"] == "engine"


def test_append_agent_role_is_rejected(client: TestClient) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/conversation/sessions/{session_id}/messages",
        json={"role": "agent", "content": "secret"},
    )

    assert resp.status_code == 422


def test_append_invalid_message_role_returns_422(client: TestClient) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/conversation/sessions/{session_id}/messages",
        json={"role": "unknown", "content": "x"},
    )

    assert resp.status_code == 422


def test_append_message_unknown_session_returns_404(client: TestClient) -> None:
    resp = client.post(
        "/conversation/sessions/not-a-real-id/messages",
        json={"role": "user", "content": "hello"},
    )

    assert resp.status_code == 404


# ── GET /conversation/sessions/{session_id}/messages ──────────────────────────


def test_list_messages_ordered_by_created_at(client: TestClient) -> None:
    session_id = _create_session(client)
    client.post(
        f"/conversation/sessions/{session_id}/messages",
        json={"role": "user", "content": "first"},
    )
    client.post(
        f"/conversation/sessions/{session_id}/messages",
        json={"role": "user", "content": "second"},
    )

    resp = client.get(f"/conversation/sessions/{session_id}/messages")
    assert resp.status_code == 200
    messages = resp.json()["data"]
    assert len(messages) == 2
    assert messages[0]["content"] == "first"
    assert messages[1]["content"] == "second"


def test_list_messages_unknown_session_returns_404_not_empty(
    client: TestClient,
) -> None:
    resp = client.get("/conversation/sessions/not-a-real-id/messages")

    assert resp.status_code == 404


# ── GET /conversation/sessions/{session_id}/transcript ────────────────────────


def test_get_transcript_returns_messages_only(client: TestClient) -> None:
    session_id = _create_session(client)
    client.post(
        f"/conversation/sessions/{session_id}/messages",
        json={"role": "user", "content": "hi"},
    )
    client.post(
        f"/conversation/sessions/{session_id}/events",
        json={"type": "state_changed", "payload": {}},
    )

    resp = client.get(f"/conversation/sessions/{session_id}/transcript")
    assert resp.status_code == 200
    transcript = resp.json()["data"]
    assert len(transcript) == 1
    assert transcript[0]["content"] == "hi"


def test_get_transcript_unknown_session_returns_404_not_empty(
    client: TestClient,
) -> None:
    resp = client.get("/conversation/sessions/not-a-real-id/transcript")

    assert resp.status_code == 404


# ── POST /conversation/sessions/{session_id}/events ───────────────────────────


def test_append_event(client: TestClient) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/conversation/sessions/{session_id}/events",
        json={"type": "state_changed", "payload": {"from": "idle", "to": "task_intake"}},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["type"] == "state_changed"
    assert data["payload"] == {"from": "idle", "to": "task_intake"}
    assert data["session_id"] == session_id


def test_append_invalid_event_type_returns_422(client: TestClient) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/conversation/sessions/{session_id}/events",
        json={"type": "not_a_real_event"},
    )

    assert resp.status_code == 422


def test_append_event_unknown_session_returns_404(client: TestClient) -> None:
    resp = client.post(
        "/conversation/sessions/not-a-real-id/events",
        json={"type": "state_changed"},
    )

    assert resp.status_code == 404


# ── GET /conversation/sessions/{session_id}/events ────────────────────────────


def test_list_events_ordered_by_created_at(client: TestClient) -> None:
    session_id = _create_session(client)
    client.post(
        f"/conversation/sessions/{session_id}/events",
        json={"type": "message_received"},
    )
    client.post(
        f"/conversation/sessions/{session_id}/events",
        json={"type": "state_changed"},
    )

    resp = client.get(f"/conversation/sessions/{session_id}/events")
    assert resp.status_code == 200
    events = resp.json()["data"]
    assert len(events) == 2
    assert events[0]["type"] == "message_received"
    assert events[1]["type"] == "state_changed"


def test_list_events_unknown_session_returns_404_not_empty(
    client: TestClient,
) -> None:
    resp = client.get("/conversation/sessions/not-a-real-id/events")

    assert resp.status_code == 404


# ── Response envelope ─────────────────────────────────────────────────────────


def test_api_response_uses_envelope(client: TestClient) -> None:
    session_id = _create_session(client)
    resp = client.get(f"/conversation/sessions/{session_id}")

    body = resp.json()
    assert "code" in body
    assert "data" in body
    assert "msg" in body
    assert body["code"] == 0
    assert body["msg"] == "ok"


# ── No identity / tenant fields in response ───────────────────────────────────


def test_response_does_not_expose_identity_or_tenant_fields(
    client: TestClient,
) -> None:
    session_id = _create_session(client)
    resp = client.get(f"/conversation/sessions/{session_id}")
    data = resp.json()["data"]

    forbidden = {"user", "account", "tenant", "user_id", "account_id", "tenant_id"}
    assert forbidden.isdisjoint(data.keys())


# ── No forbidden imports ──────────────────────────────────────────────────────


# ── POST /conversation/sessions/{session_id}/dispatch ─────────────────────────


def test_dispatch_free_text_empty_catalog_returns_unable_to_plan(
    client: TestClient,
) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "hello world"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["session_id"] == session_id
    assert data["command_kind"] == "free_text"
    assert data["allowed"] is True
    assert data["next_status"] == "task_intake"
    assert data["replay_result"] is None
    # 11.1.4 — planning preview: unable-to-plan when catalog is empty
    assert "Unable to plan" in data["user_response"]


def test_dispatch_metadata_is_persisted_and_preview_event_recorded(
    client: TestClient,
) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={
            "input": "hello world",
            "metadata": {"source": "api-test", "request_id": "req-1"},
        },
    )

    assert resp.status_code == 200

    messages_resp = client.get(f"/conversation/sessions/{session_id}/messages")
    messages = messages_resp.json()["data"]
    assert messages[0]["metadata"] == {"source": "api-test", "request_id": "req-1"}

    events_resp = client.get(f"/conversation/sessions/{session_id}/events")
    events = events_resp.json()["data"]
    command_parsed = [
        event for event in events if event["type"] == "command_parsed"
    ][0]
    assert command_parsed["payload"]["dispatch_metadata"] == {
        "source": "api-test",
        "request_id": "req-1",
    }
    # 11.1.4 — planning preview event is recorded
    assert any(e["type"] == "plan_preview_unable" for e in events)


def test_dispatch_missing_session_returns_404(client: TestClient) -> None:
    resp = client.post(
        "/conversation/sessions/not-a-real-id/dispatch",
        json={"input": "hello"},
    )

    assert resp.status_code == 404


def test_dispatch_malformed_replay_returns_allowed_false_no_replay(
    client: TestClient,
) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "/replay"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["allowed"] is False
    assert data["command_kind"] == "error"
    assert data["replay_result"] is None


def test_dispatch_replay_with_missing_path_returns_candidate_not_found(
    client: TestClient,
) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "/replay non-existent-path http://127.0.0.1:5175/users"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["allowed"] is True
    assert data["command_kind"] == "replay"
    assert data["next_status"] == "failed"
    assert data["replay_result"] is not None
    assert data["replay_result"]["replay_status"] == "candidate_not_found"


def test_dispatch_replay_success_returns_replay_summary(
    client: TestClient,
    monkeypatch,
) -> None:
    session_id = _create_session(client)

    def fake_replay(_db, learned_path_id: str, url: str) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=learned_path_id,
            url=url,
            replay_status="succeeded",
            drift_status="none",
            final_url=url,
            final_title="Users",
            step_count=2,
        )

    monkeypatch.setattr(
        "app.services.conversation.replay_hook.run_explicit_replay",
        fake_replay,
    )

    resp = client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "/replay path-1 http://127.0.0.1:5175/users"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["next_status"] == "completed"
    assert data["replay_result"]["replay_status"] == "succeeded"
    assert data["replay_result"]["step_count"] == 2


def test_dispatch_replay_drift_returns_failed_summary(
    client: TestClient,
    monkeypatch,
) -> None:
    session_id = _create_session(client)

    def fake_replay(_db, learned_path_id: str, url: str) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=learned_path_id,
            url=url,
            replay_status="drifted",
            drift_status="target_missing",
            drift_reasons=["Target missing for step 1"],
        )

    monkeypatch.setattr(
        "app.services.conversation.replay_hook.run_explicit_replay",
        fake_replay,
    )

    resp = client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "/replay path-1 http://127.0.0.1:5175/users"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["next_status"] == "failed"
    assert data["replay_result"]["replay_status"] == "drifted"
    assert data["replay_result"]["drift_status"] == "target_missing"


def test_dispatch_response_does_not_expose_engine_command(
    client: TestClient,
) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "hello"},
    )

    data = resp.json()["data"]
    assert "engine_command" not in data


def test_dispatch_does_not_expose_identity_or_tenant_fields(
    client: TestClient,
) -> None:
    session_id = _create_session(client)
    resp = client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "hello"},
    )

    data = resp.json()["data"]
    forbidden = {"user", "account", "tenant", "user_id", "account_id", "tenant_id"}
    assert forbidden.isdisjoint(data.keys())


# ── No forbidden imports ──────────────────────────────────────────────────────


def test_router_does_not_import_replay_autonomous_or_llm() -> None:
    from app.routers import conversation as router_module

    source = inspect.getsource(router_module)
    forbidden_tokens = [
        "autonomous_explorer",
        "/exploration/autonomous-runs",
        "llm_provider",
        "OpenAI",
    ]
    for token in forbidden_tokens:
        assert token not in source


# ── 11.1.4 Planning preview through dispatch endpoint ──────────────────────────


def test_dispatch_free_text_with_learned_path_proposes_plan_and_awaits_confirmation(
    client: TestClient,
    db_session,
) -> None:
    # Seed a confirmed learned path
    repo = LearnedPathRepository(db_session)
    lp, _ = repo.ingest_run(
        page_template="/login",
        query_signature={},
        dom_fingerprint="a" * 64,
        scenario="log in",
        actions=[{"action_type": "fill", "target_selector": "#user"}],
        source_run_id=None,
    )
    lp = repo.set_trust(lp.id, TrustStatus.CONFIRMED, reason="test confirmed")
    lp.hit_count = 5
    db_session.commit()

    session_id = _create_session(client)
    resp = client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "log in"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["command_kind"] == "free_text"
    assert data["allowed"] is True
    assert data["next_status"] == "awaiting_confirmation"
    assert "Plan:" in data["user_response"]
    assert "Selected path:" in data["user_response"]

    # Assistant message recorded
    messages_resp = client.get(f"/conversation/sessions/{session_id}/messages")
    messages = messages_resp.json()["data"]
    assert any(m["role"] == "agent" and "Plan:" in m["content"] for m in messages)

    # Preview event recorded with confirmation_required consistent with state
    events_resp = client.get(f"/conversation/sessions/{session_id}/events")
    events = events_resp.json()["data"]
    preview_events = [e for e in events if e["type"] == "plan_preview_proposed"]
    assert len(preview_events) == 1
    assert preview_events[0]["payload"]["confirmation_required"] is True

    # State changed to awaiting_confirmation
    assert any(
        e["type"] == "state_changed" and e["payload"].get("to") == "awaiting_confirmation"
        for e in events
    )


# ── 11.1.5 Confirmation gate through dispatch endpoint ─────────────────────────


def test_dispatch_confirm_from_awaiting_confirmation(client: TestClient, db_session) -> None:
    repo = LearnedPathRepository(db_session)
    lp, _ = repo.ingest_run(
        page_template="/login",
        query_signature={},
        dom_fingerprint="a" * 64,
        scenario="log in",
        actions=[{"action_type": "fill", "target_selector": "#user"}],
        source_run_id=None,
    )
    lp = repo.set_trust(lp.id, TrustStatus.CONFIRMED, reason="test confirmed")
    lp.hit_count = 5
    db_session.commit()

    session_id = _create_session(client)
    client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "log in"},
    )

    resp = client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "confirm"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["next_status"] == "plan_confirmed"
    assert data["allowed"] is True
    assert "ready for future execution" in data["user_response"]

    events_resp = client.get(f"/conversation/sessions/{session_id}/events")
    events = events_resp.json()["data"]
    assert any(e["type"] == "plan_confirmed" for e in events)
    confirmed = [e for e in events if e["type"] == "plan_confirmed"][0]
    assert confirmed["payload"]["replay_executed"] is False


def test_dispatch_cancel_from_awaiting_confirmation(client: TestClient, db_session) -> None:
    repo = LearnedPathRepository(db_session)
    lp, _ = repo.ingest_run(
        page_template="/login",
        query_signature={},
        dom_fingerprint="a" * 64,
        scenario="log in",
        actions=[{"action_type": "fill", "target_selector": "#user"}],
        source_run_id=None,
    )
    lp = repo.set_trust(lp.id, TrustStatus.CONFIRMED, reason="test confirmed")
    lp.hit_count = 5
    db_session.commit()

    session_id = _create_session(client)
    client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "log in"},
    )

    resp = client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "cancel"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["next_status"] == "task_intake"
    assert data["allowed"] is True
    assert "cancelled" in data["user_response"]

    events_resp = client.get(f"/conversation/sessions/{session_id}/events")
    events = events_resp.json()["data"]
    assert any(e["type"] == "plan_cancelled" for e in events)


def test_dispatch_slash_cancel_from_awaiting_confirmation_uses_confirmation_gate(
    client: TestClient, db_session
) -> None:
    repo = LearnedPathRepository(db_session)
    lp, _ = repo.ingest_run(
        page_template="/login",
        query_signature={},
        dom_fingerprint="a" * 64,
        scenario="log in",
        actions=[{"action_type": "fill", "target_selector": "#user"}],
        source_run_id=None,
    )
    lp = repo.set_trust(lp.id, TrustStatus.CONFIRMED, reason="test confirmed")
    lp.hit_count = 5
    db_session.commit()

    session_id = _create_session(client)
    client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "log in"},
    )

    resp = client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "/cancel"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["next_status"] == "task_intake"
    assert data["allowed"] is True
    assert "cancelled" in data["user_response"]

    events_resp = client.get(f"/conversation/sessions/{session_id}/events")
    events = events_resp.json()["data"]
    assert any(e["type"] == "plan_cancelled" for e in events)
    assert not any(
        e["type"] == "state_changed" and e["payload"].get("to") == "idle"
        for e in events
    )


def test_dispatch_replay_blocked_while_awaiting_confirmation(
    client: TestClient, db_session
) -> None:
    repo = LearnedPathRepository(db_session)
    lp, _ = repo.ingest_run(
        page_template="/login",
        query_signature={},
        dom_fingerprint="a" * 64,
        scenario="log in",
        actions=[{"action_type": "fill", "target_selector": "#user"}],
        source_run_id=None,
    )
    lp = repo.set_trust(lp.id, TrustStatus.CONFIRMED, reason="test confirmed")
    lp.hit_count = 5
    db_session.commit()

    session_id = _create_session(client)
    client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "log in"},
    )

    resp = client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "/replay 11111111-1111-1111-1111-111111111111 http://127.0.0.1:5175/users"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["next_status"] == "awaiting_confirmation"
    assert data["allowed"] is False
    assert "confirm, cancel, or reject" in data["user_response"]

    events_resp = client.get(f"/conversation/sessions/{session_id}/events")
    events = events_resp.json()["data"]
    assert any(
        e["type"] == "explicit_replay_blocked_by_pending_confirmation" for e in events
    )


# ── 11.1.6 Execution gate through dispatch endpoint ───────────────────────────


def test_dispatch_execute_after_confirmed_plan_blocked_no_target_url(
    client: TestClient, db_session
) -> None:
    """Execution is blocked when confirmed plan lacks target_url."""
    repo = LearnedPathRepository(db_session)
    lp, _ = repo.ingest_run(
        page_template="/login",
        query_signature={},
        dom_fingerprint="a" * 64,
        scenario="log in",
        actions=[{"action_type": "fill", "target_selector": "#user"}],
        source_run_id=None,
    )
    lp = repo.set_trust(lp.id, TrustStatus.CONFIRMED, reason="test confirmed")
    lp.hit_count = 5
    db_session.commit()

    session_id = _create_session(client)
    client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "log in"},
    )
    client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "confirm"},
    )

    resp = client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "execute"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["next_status"] == "plan_confirmed"
    assert data["allowed"] is False
    # 11.1.7: blocked user_response now comes from Task Result Reporter
    response = data["user_response"].lower()
    assert "blocked" in response or "could not run" in response

    events_resp = client.get(f"/conversation/sessions/{session_id}/events")
    events = events_resp.json()["data"]
    assert any(e["type"] == "plan_execution_blocked" for e in events)
    assert any(e["type"] == "task_result_reported" for e in events)
    reported = [e for e in events if e["type"] == "task_result_reported"][0]
    assert reported["payload"]["verification_outcome"] == "blocked"
    blocked = [e for e in events if e["type"] == "plan_execution_blocked"][0]
    assert blocked["payload"]["no_result_verification"] is True
    assert blocked["payload"]["no_autonomous"] is True


def test_dispatch_execute_after_confirmed_plan_with_target_url(
    client: TestClient, db_session, monkeypatch
) -> None:
    """Execution completes when confirmed plan has full replay context."""
    from app.schemas.conversation import ConversationEventType
    from app.services.task_planning.preview import PlanningPreviewResult

    def mock_preview(_self, raw_input: str) -> PlanningPreviewResult:
        return PlanningPreviewResult(
            user_response="Plan: test",
            event_type=ConversationEventType.PLAN_PREVIEW_PROPOSED.value,
            event_payload={
                "task_intent_raw_text": raw_input,
                "candidate_count": 1,
                "selected_path_id": "lp-001",
                "selected_purpose": "Test",
                "target_url": "http://127.0.0.1:5175/users",
                "route_steps": [{"order": 1, "learned_path_id": "lp-001"}],
                "confirmation_required": True,
            },
            confirmation_required=True,
            selected_path_id="lp-001",
        )

    monkeypatch.setattr(
        "app.services.task_planning.preview.PlanningPreviewService.preview",
        mock_preview,
    )

    def fake_replay(_db, learned_path_id: str, url: str) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=learned_path_id,
            url=url,
            replay_status="succeeded",
            drift_status="none",
            step_count=2,
        )

    monkeypatch.setattr(
        "app.services.conversation.replay_hook.run_explicit_replay",
        fake_replay,
    )

    repo = LearnedPathRepository(db_session)
    lp, _ = repo.ingest_run(
        page_template="/login",
        query_signature={},
        dom_fingerprint="a" * 64,
        scenario="log in",
        actions=[{"action_type": "fill", "target_selector": "#user"}],
        source_run_id=None,
    )
    lp = repo.set_trust(lp.id, TrustStatus.CONFIRMED, reason="test confirmed")
    lp.hit_count = 5
    db_session.commit()

    session_id = _create_session(client)
    client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "log in"},
    )
    client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "confirm"},
    )

    resp = client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "run"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["next_status"] == "execution_finished"
    assert data["allowed"] is True
    assert data["replay_result"] is not None
    assert data["replay_result"]["replay_status"] == "succeeded"
    assert data["replay_result"]["step_count"] == 2
    # 11.1.7: user_response now comes from Task Result Reporter
    assert "could not verify" in data["user_response"].lower()

    events_resp = client.get(f"/conversation/sessions/{session_id}/events")
    events = events_resp.json()["data"]
    assert any(e["type"] == "plan_execution_started" for e in events)
    assert any(e["type"] == "plan_execution_completed" for e in events)
    assert any(e["type"] == "task_result_reported" for e in events)
    completed = [e for e in events if e["type"] == "plan_execution_completed"][0]
    assert completed["payload"]["task_verified"] is False
    assert completed["payload"]["no_result_verification"] is True
    assert completed["payload"]["no_autonomous"] is True
    reported = [e for e in events if e["type"] == "task_result_reported"][0]
    assert reported["payload"]["verification_outcome"] == "uncertain"
    assert reported["payload"]["needs_review"] is True
    assert reported["payload"]["no_recovery"] is True
    assert reported["payload"]["no_llm"] is True


def test_dispatch_explicit_replay_compatible_outside_awaiting_confirmation(
    client: TestClient, monkeypatch
) -> None:
    """Explicit /replay still works independently of confirmed-plan execution."""
    def fake_replay(_db, learned_path_id: str, url: str) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=learned_path_id,
            url=url,
            replay_status="succeeded",
            drift_status="none",
        )

    monkeypatch.setattr(
        "app.services.conversation.replay_hook.run_explicit_replay",
        fake_replay,
    )

    session_id = _create_session(client)
    resp = client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "/replay lp-001 http://127.0.0.1:5175/users"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["next_status"] == "completed"
    assert data["replay_result"] is not None
    assert data["replay_result"]["replay_status"] == "succeeded"


def test_dispatch_execute_failed_replay_includes_task_result_reported(
    client: TestClient, db_session, monkeypatch
) -> None:
    """Failed execution via dispatch must include task_result_reported with failed outcome."""
    from app.schemas.conversation import ConversationEventType
    from app.services.task_planning.preview import PlanningPreviewResult

    def mock_preview(_self, raw_input: str) -> PlanningPreviewResult:
        return PlanningPreviewResult(
            user_response="Plan: test",
            event_type=ConversationEventType.PLAN_PREVIEW_PROPOSED.value,
            event_payload={
                "task_intent_raw_text": raw_input,
                "candidate_count": 1,
                "selected_path_id": "lp-001",
                "selected_purpose": "Test",
                "target_url": "http://127.0.0.1:5175/users",
                "route_steps": [{"order": 1, "learned_path_id": "lp-001"}],
                "confirmation_required": True,
            },
            confirmation_required=True,
            selected_path_id="lp-001",
        )

    monkeypatch.setattr(
        "app.services.task_planning.preview.PlanningPreviewService.preview",
        mock_preview,
    )

    def fake_replay(_db, learned_path_id: str, url: str) -> ConversationReplaySummary:
        return ConversationReplaySummary(
            learned_path_id=learned_path_id,
            url=url,
            replay_status="drifted",
            drift_status="target_missing",
            error="Target missing",
        )

    monkeypatch.setattr(
        "app.services.conversation.replay_hook.run_explicit_replay",
        fake_replay,
    )

    repo = LearnedPathRepository(db_session)
    lp, _ = repo.ingest_run(
        page_template="/login",
        query_signature={},
        dom_fingerprint="a" * 64,
        scenario="log in",
        actions=[{"action_type": "fill", "target_selector": "#user"}],
        source_run_id=None,
    )
    lp = repo.set_trust(lp.id, TrustStatus.CONFIRMED, reason="test confirmed")
    lp.hit_count = 5
    db_session.commit()

    session_id = _create_session(client)
    client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "log in"},
    )
    client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "confirm"},
    )

    resp = client.post(
        f"/conversation/sessions/{session_id}/dispatch",
        json={"input": "run"},
    )

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["next_status"] == "execution_failed"
    assert data["allowed"] is True
    assert "failed" in data["user_response"].lower()
    assert "no recovery" in data["user_response"].lower()

    events_resp = client.get(f"/conversation/sessions/{session_id}/events")
    events = events_resp.json()["data"]
    assert any(e["type"] == "plan_execution_failed" for e in events)
    assert any(e["type"] == "task_result_reported" for e in events)
    reported = [e for e in events if e["type"] == "task_result_reported"][0]
    assert reported["payload"]["verification_outcome"] == "failed"
    assert reported["payload"]["needs_review"] is False
    assert reported["payload"]["no_recovery"] is True


# ── 11.3.2 Chat History & Debug Console ───────────────────────────────────────


def test_list_sessions_returns_items_sorted_by_updated_at_desc(
    client: TestClient,
) -> None:
    # Create two sessions with different modes
    s1 = client.post(
        "/conversation/sessions",
        json={"current_mode": "interactive_chat", "metadata": {"a": 1}},
    ).json()["data"]
    s2 = client.post(
        "/conversation/sessions",
        json={"current_mode": "interactive_chat", "metadata": {"b": 2}},
    ).json()["data"]

    resp = client.get("/conversation/sessions")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "items" in data
    ids = [item["id"] for item in data["items"]]
    assert s2["id"] in ids
    assert s1["id"] in ids
    # Most recently updated first
    assert ids.index(s2["id"]) < ids.index(s1["id"])


def test_list_sessions_filters_by_current_mode(client: TestClient) -> None:
    s_chat = client.post(
        "/conversation/sessions",
        json={"current_mode": "interactive_chat"},
    ).json()["data"]
    s_replay = client.post(
        "/conversation/sessions",
        json={"current_mode": "replay"},
    ).json()["data"]

    resp = client.get("/conversation/sessions?current_mode=interactive_chat")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["data"]["items"]]
    assert s_chat["id"] in ids
    assert s_replay["id"] not in ids


def test_list_sessions_filters_by_status(client: TestClient) -> None:
    s = client.post("/conversation/sessions", json={}).json()["data"]
    # Default status is idle
    resp = client.get("/conversation/sessions?status=idle")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["data"]["items"]]
    assert s["id"] in ids

    resp = client.get("/conversation/sessions?status=task_intake")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["data"]["items"]]
    assert s["id"] not in ids


def test_list_sessions_respects_limit(client: TestClient) -> None:
    for _ in range(3):
        client.post("/conversation/sessions", json={})

    resp = client.get("/conversation/sessions?limit=2")
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) == 2


def test_list_sessions_limit_out_of_range_returns_422(client: TestClient) -> None:
    resp = client.get("/conversation/sessions?limit=0")
    assert resp.status_code == 422

    resp = client.get("/conversation/sessions?limit=101")
    assert resp.status_code == 422


def test_list_sessions_summary_fields(client: TestClient) -> None:
    session_id = _create_session(client, current_mode="interactive_chat")
    client.post(
        f"/conversation/sessions/{session_id}/messages",
        json={"role": "user", "content": "hello"},
    )
    client.post(
        f"/conversation/sessions/{session_id}/messages",
        json={"role": "system", "content": "ack"},
    )
    client.post(
        f"/conversation/sessions/{session_id}/events",
        json={"type": "state_changed", "payload": {}},
    )

    resp = client.get("/conversation/sessions?current_mode=interactive_chat")
    assert resp.status_code == 200
    item = resp.json()["data"]["items"][0]
    assert item["id"] == session_id
    assert item["message_count"] == 2
    assert item["event_count"] == 1
    assert item["last_user_message"] == "hello"
    assert item["last_agent_message"] is None
    assert item["learned_action_count"] == 0


def test_list_sessions_with_learned_actions(client: TestClient) -> None:
    session_id = client.post(
        "/conversation/sessions",
        json={
            "current_mode": "interactive_chat",
            "metadata": {
                "learned_actions": [
                    {
                        "alias": "登录",
                        "learned_path_id": "path-1",
                        "target_url": "http://localhost:5175/login",
                        "page_template": "/login",
                        "scenario": "valid_credentials",
                    }
                ]
            },
        },
    ).json()["data"]["id"]

    resp = client.get("/conversation/sessions")
    assert resp.status_code == 200
    item = [i for i in resp.json()["data"]["items"] if i["id"] == session_id][0]
    assert item["learned_action_count"] == 1
    assert item["learned_actions"][0]["alias"] == "登录"


def test_get_history_returns_aggregate_payload(client: TestClient) -> None:
    session_id = _create_session(client, current_mode="interactive_chat")
    client.post(
        f"/conversation/sessions/{session_id}/messages",
        json={"role": "user", "content": "msg1"},
    )
    client.post(
        f"/conversation/sessions/{session_id}/events",
        json={"type": "state_changed", "payload": {"to": "task_intake"}},
    )

    resp = client.get(f"/conversation/sessions/{session_id}/history")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["session"]["id"] == session_id
    assert len(data["messages"]) == 1
    assert len(data["events"]) == 1
    assert data["learned_actions"] == []
    assert data["learning_runs"] == []
    assert data["replay_summaries"] == []
    assert "raw" in data
    assert "session" in data["raw"]


def test_get_history_extracts_learning_runs(client: TestClient) -> None:
    session_id = _create_session(client)
    client.post(
        f"/conversation/sessions/{session_id}/events",
        json={
            "type": "chat_learning_completed",
            "payload": {
                "run_id": "run-1",
                "new_learned_path_id": "path-1",
                "summary": "学会了登录",
            },
        },
    )

    resp = client.get(f"/conversation/sessions/{session_id}/history")
    assert resp.status_code == 200
    runs = resp.json()["data"]["learning_runs"]
    assert len(runs) == 1
    assert runs[0]["run_id"] == "run-1"
    assert runs[0]["learned_path_id"] == "path-1"
    assert runs[0]["status"] == "learned"
    assert runs[0]["summary"] == "学会了登录"


def test_get_history_extracts_replay_summaries_from_replay_payload(
    client: TestClient,
) -> None:
    session_id = _create_session(client)
    client.post(
        f"/conversation/sessions/{session_id}/events",
        json={
            "type": "chat_execution_completed",
            "payload": {
                "replay": {
                    "learned_path_id": "path-1",
                    "replay_status": "succeeded",
                    "summary": "replay ok",
                }
            },
        },
    )

    resp = client.get(f"/conversation/sessions/{session_id}/history")
    assert resp.status_code == 200
    summaries = resp.json()["data"]["replay_summaries"]
    assert len(summaries) == 1
    assert summaries[0]["learned_path_id"] == "path-1"
    assert summaries[0]["status"] == "succeeded"


def test_get_history_unknown_session_returns_404(client: TestClient) -> None:
    resp = client.get("/conversation/sessions/not-a-real-id/history")
    assert resp.status_code == 404


def test_get_history_empty_session(client: TestClient) -> None:
    session_id = _create_session(client)
    resp = client.get(f"/conversation/sessions/{session_id}/history")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["messages"] == []
    assert data["events"] == []
    assert data["learned_actions"] == []
    assert data["learning_runs"] == []
    assert data["replay_summaries"] == []
