"""Tests for ``ConversationRepository``.

M11.0 conversation session / message / event persistence.
"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy.orm import Session

from app.models.conversation import ConversationEvent, ConversationMessage, ConversationSession
from app.repos.conversation_repo import ConversationRepository
from app.schemas.conversation import ConversationEventType, ConversationRole, ConversationStatus


@pytest.fixture
def repo(db_session: Session) -> ConversationRepository:
    return ConversationRepository(db_session)


# ── Session lifecycle ─────────────────────────────────────────────────────────


def test_create_session_defaults_to_idle(repo: ConversationRepository) -> None:
    session = repo.create_session()

    assert session.status == "idle"
    assert session.current_mode is None
    assert session.metadata_json == {}
    assert session.previous_status is None


def test_create_session_stores_metadata(repo: ConversationRepository) -> None:
    session = repo.create_session(
        initial_status="task_intake",
        current_mode="replay",
        metadata={"source": "cli"},
    )

    assert session.status == "task_intake"
    assert session.current_mode == "replay"
    assert session.metadata_json == {"source": "cli"}


def test_create_session_rejects_invalid_status(repo: ConversationRepository) -> None:
    with pytest.raises(ValueError, match="initial_status.*not_a_status"):
        repo.create_session(initial_status="not_a_status")


def test_get_session_by_id(repo: ConversationRepository) -> None:
    created = repo.create_session()
    fetched = repo.get_session(created.id)

    assert fetched is not None
    assert fetched.id == created.id


def test_get_session_unknown_returns_none(repo: ConversationRepository) -> None:
    assert repo.get_session("not-a-real-id") is None


def test_update_session_status(repo: ConversationRepository) -> None:
    session = repo.create_session(initial_status="idle")
    updated = repo.update_session_status(session.id, status="task_intake")

    assert updated.status == "task_intake"
    assert updated.id == session.id


def test_update_session_previous_status_for_pause_resume(
    repo: ConversationRepository,
) -> None:
    session = repo.create_session(initial_status="replay_running")
    paused = repo.update_session_status(
        session.id,
        status="paused",
        previous_status="replay_running",
    )

    assert paused.status == "paused"
    assert paused.previous_status == "replay_running"

    resumed = repo.update_session_status(
        session.id,
        status="task_intake",
        previous_status=None,
    )

    assert resumed.status == "task_intake"
    assert resumed.previous_status is None


def test_update_session_metadata_patch_merges(repo: ConversationRepository) -> None:
    session = repo.create_session(metadata={"a": 1})
    updated = repo.update_session_status(
        session.id,
        status="idle",
        metadata_patch={"b": 2},
    )

    assert updated.metadata_json == {"a": 1, "b": 2}


def test_update_session_unknown_id_raises(repo: ConversationRepository) -> None:
    with pytest.raises(ValueError, match="session not found"):
        repo.update_session_status("not-a-real-id", status="idle")


def test_update_session_rejects_invalid_status(repo: ConversationRepository) -> None:
    session = repo.create_session()

    with pytest.raises(ValueError, match="status.*not_a_status"):
        repo.update_session_status(session.id, status="not_a_status")


# ── Messages ──────────────────────────────────────────────────────────────────


def test_append_user_message(repo: ConversationRepository) -> None:
    session = repo.create_session()
    msg = repo.append_message(session.id, role="user", content="hello")

    assert msg.session_id == session.id
    assert msg.role == "user"
    assert msg.content == "hello"
    assert msg.metadata_json == {}
    assert msg.created_at is not None


def test_append_system_message(repo: ConversationRepository) -> None:
    session = repo.create_session()
    msg = repo.append_message(
        session.id,
        role="system",
        content="ack",
        metadata={"intent": "confirm"},
    )

    assert msg.role == "system"
    assert msg.metadata_json == {"intent": "confirm"}


def test_append_engine_message(repo: ConversationRepository) -> None:
    session = repo.create_session()
    msg = repo.append_message(session.id, role="engine", content="done")

    assert msg.role == "engine"


def test_append_message_accepts_conversation_role_enum(repo: ConversationRepository) -> None:
    session = repo.create_session()
    msg = repo.append_message(session.id, role=ConversationRole.USER, content="hello")

    assert msg.role == "user"


def test_append_message_rejects_invalid_role(repo: ConversationRepository) -> None:
    session = repo.create_session()

    with pytest.raises(ValueError, match="role.*operator"):
        repo.append_message(session.id, role="operator", content="hello")


def test_append_message_unknown_session_raises(repo: ConversationRepository) -> None:
    with pytest.raises(ValueError, match="session not found: missing-session"):
        repo.append_message("missing-session", role="user", content="hello")


def test_list_messages_ordered_by_created_at(repo: ConversationRepository) -> None:
    session = repo.create_session()
    m1 = repo.append_message(session.id, role="user", content="first")
    m2 = repo.append_message(session.id, role="user", content="second")

    messages = repo.list_messages(session.id)
    assert [m.id for m in messages] == [m1.id, m2.id]


def test_list_messages_respects_limit(repo: ConversationRepository) -> None:
    session = repo.create_session()
    for i in range(5):
        repo.append_message(session.id, role="user", content=str(i))

    messages = repo.list_messages(session.id, limit=2)
    assert len(messages) == 2


def test_list_messages_with_cursor_raises(repo: ConversationRepository) -> None:
    session = repo.create_session()

    with pytest.raises(ValueError, match="cursor pagination is not implemented yet"):
        repo.list_messages(session.id, cursor="cursor-1")


def test_get_transcript_returns_messages_only(repo: ConversationRepository) -> None:
    session = repo.create_session()
    msg = repo.append_message(session.id, role="user", content="hi")
    repo.append_event(session.id, type="state_changed", payload={"to": "task_intake"})

    transcript = repo.get_transcript(session.id)
    assert len(transcript) == 1
    assert transcript[0].id == msg.id


# ── Events ────────────────────────────────────────────────────────────────────


def test_append_event(repo: ConversationRepository) -> None:
    session = repo.create_session()
    event = repo.append_event(
        session.id,
        type="state_changed",
        payload={"from": "idle", "to": "task_intake"},
    )

    assert event.session_id == session.id
    assert event.type == "state_changed"
    assert event.payload_json == {"from": "idle", "to": "task_intake"}
    assert event.created_at is not None


def test_create_and_update_session_accept_conversation_status_enum(
    repo: ConversationRepository,
) -> None:
    session = repo.create_session(initial_status=ConversationStatus.TASK_INTAKE)
    updated = repo.update_session_status(
        session.id,
        status=ConversationStatus.PAUSED,
        previous_status=ConversationStatus.TASK_INTAKE,
    )

    assert updated.status == "paused"
    assert updated.previous_status == "task_intake"


def test_append_event_accepts_conversation_event_type_enum(
    repo: ConversationRepository,
) -> None:
    session = repo.create_session()
    event = repo.append_event(session.id, type=ConversationEventType.STATE_CHANGED)

    assert event.type == "state_changed"


def test_append_event_rejects_invalid_type(repo: ConversationRepository) -> None:
    session = repo.create_session()

    with pytest.raises(ValueError, match="type.*made_up_event"):
        repo.append_event(session.id, type="made_up_event")


def test_append_event_unknown_session_raises(repo: ConversationRepository) -> None:
    with pytest.raises(ValueError, match="session not found: missing-session"):
        repo.append_event("missing-session", type="state_changed")


def test_list_events_ordered_by_created_at(repo: ConversationRepository) -> None:
    session = repo.create_session()
    e1 = repo.append_event(session.id, type="message_received")
    e2 = repo.append_event(session.id, type="state_changed")

    events = repo.list_events(session.id)
    assert [e.id for e in events] == [e1.id, e2.id]


def test_list_events_respects_limit(repo: ConversationRepository) -> None:
    session = repo.create_session()
    for i in range(5):
        repo.append_event(session.id, type="message_received", payload={"n": i})

    events = repo.list_events(session.id, limit=2)
    assert len(events) == 2


def test_list_events_with_cursor_raises(repo: ConversationRepository) -> None:
    session = repo.create_session()

    with pytest.raises(ValueError, match="cursor pagination is not implemented yet"):
        repo.list_events(session.id, cursor="cursor-1")


# ── Cascade delete ────────────────────────────────────────────────────────────


def test_session_delete_cascades_messages_and_events(
    repo: ConversationRepository,
    db_session: Session,
) -> None:
    session = repo.create_session()
    msg = repo.append_message(session.id, role="user", content="hi")
    event = repo.append_event(session.id, type="session_created")

    db_session.delete(session)
    db_session.commit()

    assert db_session.get(ConversationSession, session.id) is None
    assert db_session.get(ConversationMessage, msg.id) is None
    assert db_session.get(ConversationEvent, event.id) is None


# ── No identity / tenant fields ───────────────────────────────────────────────


def test_models_do_not_define_identity_or_tenant_fields() -> None:
    forbidden = {"user", "account", "tenant", "user_id", "account_id", "tenant_id"}
    models = [ConversationSession, ConversationMessage, ConversationEvent]

    for model in models:
        columns = {c.name for c in model.__table__.columns}
        assert forbidden.isdisjoint(columns), f"{model.__name__} contains forbidden fields"


# ── No forbidden imports ──────────────────────────────────────────────────────


def test_repo_does_not_import_replay_autonomous_or_llm() -> None:
    source = inspect.getsource(ConversationRepository)
    forbidden_tokens = [
        "learned_path_replay",
        "run_replay",
        "autonomous_explorer",
        "/exploration/autonomous-runs",
        "llm_provider",
        "OpenAI",
    ]
    for token in forbidden_tokens:
        assert token not in source


# ── Model metadata sanity ─────────────────────────────────────────────────────


def test_model_collected_in_metadata() -> None:
    from app.models.base import Base

    assert "conversation_sessions" in Base.metadata.tables
    assert "conversation_messages" in Base.metadata.tables
    assert "conversation_events" in Base.metadata.tables

    session_tbl = Base.metadata.tables["conversation_sessions"]
    expected_session = {
        "id",
        "status",
        "current_mode",
        "previous_status",
        "metadata_json",
        "created_at",
        "updated_at",
    }
    assert expected_session.issubset(set(session_tbl.c.keys()))
    assert "ix_conversation_sessions_updated_at" in {idx.name for idx in session_tbl.indexes}

    msg_tbl = Base.metadata.tables["conversation_messages"]
    expected_msg = {"id", "session_id", "role", "content", "metadata_json", "created_at"}
    assert expected_msg.issubset(set(msg_tbl.c.keys()))

    event_tbl = Base.metadata.tables["conversation_events"]
    expected_event = {"id", "session_id", "type", "payload_json", "created_at"}
    assert expected_event.issubset(set(event_tbl.c.keys()))
