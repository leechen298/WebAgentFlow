"""Tests for M11.0.6 explicit replay command hook integration."""

from __future__ import annotations

import inspect
from typing import Any
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.learned_path import TrustStatus
from app.repos.conversation_repo import ConversationRepository
from app.repos.learned_paths_repo import LearnedPathRepository
from app.schemas.conversation import (
    ConversationEventType,
    ConversationReplaySummary,
)
from app.schemas.learned_path_replay import ExecutionEvidence, ExecutionEvidenceTarget
from app.services.conversation.orchestrator import ConversationOrchestrator
from app.services.conversation.replay_hook import run_explicit_replay


@pytest.fixture
def repo(db_session: Session) -> ConversationRepository:
    return ConversationRepository(db_session)


def _make_summary(
    *,
    status: str = "succeeded",
    drift: str = "none",
    error: str | None = None,
) -> ConversationReplaySummary:
    return ConversationReplaySummary(
        learned_path_id="path-1",
        url="http://127.0.0.1:5175/users",
        replay_status=status,
        drift_status=drift,
        error=error,
    )


def _create_session(repo: ConversationRepository, status: str = "idle") -> str:
    session = repo.create_session(initial_status=status)
    return session.id


def _create_learned_path(db_session: Session, *, trust: TrustStatus) -> str:
    row, _ = LearnedPathRepository(db_session).ingest_run(
        page_template="/users",
        query_signature={},
        dom_fingerprint="a" * 64,
        scenario="filter_by_status",
        actions=[{"step": 1, "action_type": "fill", "target_selector": "#q"}],
        source_run_id=None,
    )
    if trust != TrustStatus.PROVISIONAL:
        row = LearnedPathRepository(db_session).set_trust(
            row.id,
            trust,
            reason=f"test {trust.value}",
        )
    return row.id


# ── Replay command triggers handler ────────────────────────────────────────────


def test_replay_command_calls_handler_and_completes(repo: ConversationRepository) -> None:
    calls: list[tuple[str, str]] = []

    def handler(lid: str, url: str) -> ConversationReplaySummary:
        calls.append((lid, url))
        return _make_summary(status="succeeded")

    orch = ConversationOrchestrator(repo, replay_handler=handler)
    session_id = _create_session(repo, status="idle")

    result = orch.dispatch_user_input(
        session_id, "/replay path-1 http://127.0.0.1:5175/users"
    )

    assert len(calls) == 1
    assert calls[0] == ("path-1", "http://127.0.0.1:5175/users")
    assert result.allowed is True
    assert result.next_status == "completed"
    assert result.command_kind == "replay"
    assert result.replay_result is not None
    assert result.replay_result.replay_status == "succeeded"
    assert "Replay completed" in result.user_response

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "completed"

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert ConversationEventType.REPLAY_COMPLETED.value in event_types
    assert ConversationEventType.STATE_CHANGED.value in event_types


def test_replay_observed_also_completes(repo: ConversationRepository) -> None:
    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        return _make_summary(status="observed")

    orch = ConversationOrchestrator(repo, replay_handler=handler)
    session_id = _create_session(repo, status="idle")

    result = orch.dispatch_user_input(
        session_id, "/replay path-1 http://127.0.0.1:5175/users"
    )

    assert result.next_status == "completed"
    assert result.replay_result is not None
    assert result.replay_result.replay_status == "observed"

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "completed"


def test_replay_drifted_fails_session(repo: ConversationRepository) -> None:
    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        return _make_summary(status="drifted", drift="page_mismatch")

    orch = ConversationOrchestrator(repo, replay_handler=handler)
    session_id = _create_session(repo, status="idle")

    result = orch.dispatch_user_input(
        session_id, "/replay path-1 http://127.0.0.1:5175/users"
    )

    assert result.next_status == "failed"
    assert result.replay_result is not None
    assert result.replay_result.replay_status == "drifted"
    assert "Replay failed" in result.user_response

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "failed"

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert ConversationEventType.REPLAY_FAILED.value in event_types


@pytest.mark.parametrize(
    "bad_status",
    ["unsupported", "failed", "runtime_error", "candidate_not_found"],
)
def test_replay_bad_status_fails_session(
    repo: ConversationRepository,
    bad_status: str,
) -> None:
    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        return _make_summary(status=bad_status)

    orch = ConversationOrchestrator(repo, replay_handler=handler)
    session_id = _create_session(repo, status="idle")

    result = orch.dispatch_user_input(
        session_id, "/replay path-1 http://127.0.0.1:5175/users"
    )

    assert result.next_status == "failed"
    assert result.replay_result is not None
    assert result.replay_result.replay_status == bad_status

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "failed"


def test_deprecated_learned_path_does_not_call_run_replay(
    db_session: Session,
) -> None:
    path_id = _create_learned_path(db_session, trust=TrustStatus.DEPRECATED)

    with patch(
        "app.services.conversation.replay_hook.run_replay",
        side_effect=AssertionError("run_replay should not be called"),
    ):
        result = run_explicit_replay(
            db_session,
            path_id,
            "http://127.0.0.1:5175/users",
        )

    assert result.learned_path_id == path_id
    assert result.replay_status == "deprecated"
    assert result.drift_status == "none"
    assert result.error == "LearnedPath is deprecated"


def test_replay_handler_exception_maps_to_failed(repo: ConversationRepository) -> None:
    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        raise RuntimeError("browser exploded")

    orch = ConversationOrchestrator(repo, replay_handler=handler)
    session_id = _create_session(repo, status="idle")

    result = orch.dispatch_user_input(
        session_id, "/replay path-1 http://127.0.0.1:5175/users"
    )

    assert result.next_status == "failed"
    assert result.replay_result is not None
    assert result.replay_result.replay_status == "runtime_error"
    assert "browser exploded" in (result.replay_result.error or "")

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "failed"

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]
    assert ConversationEventType.REPLAY_FAILED.value in event_types


# ── Non-replay commands do not call handler ────────────────────────────────────


def test_free_text_does_not_call_handler(repo: ConversationRepository) -> None:
    calls: list[Any] = []

    def handler(lid: str, url: str) -> ConversationReplaySummary:
        calls.append((lid, url))
        return _make_summary()

    orch = ConversationOrchestrator(repo, replay_handler=handler)
    session_id = _create_session(repo, status="idle")

    result = orch.dispatch_user_input(session_id, "do some work")

    assert len(calls) == 0
    assert result.command_kind == "free_text"
    assert result.replay_result is None


# ── Malformed replay does not call handler ─────────────────────────────────────


def test_malformed_replay_does_not_call_handler(repo: ConversationRepository) -> None:
    calls: list[Any] = []

    def handler(lid: str, url: str) -> ConversationReplaySummary:
        calls.append((lid, url))
        return _make_summary()

    orch = ConversationOrchestrator(repo, replay_handler=handler)
    session_id = _create_session(repo, status="idle")

    result = orch.dispatch_user_input(session_id, "/replay")

    assert len(calls) == 0
    assert result.allowed is False
    assert result.replay_result is None
    assert result.next_status == "idle"


def test_dispatch_metadata_is_persisted_on_message_and_command_event(
    repo: ConversationRepository,
) -> None:
    orch = ConversationOrchestrator(repo)
    session_id = _create_session(repo, status="idle")

    orch.dispatch_user_input(
        session_id,
        "do some work",
        metadata={"source": "api", "request_id": "req-1"},
    )

    messages = repo.list_messages(session_id)
    assert messages[0].metadata_json == {"source": "api", "request_id": "req-1"}

    events = repo.list_events(session_id)
    command_parsed = [
        event for event in events
        if event.type == ConversationEventType.COMMAND_PARSED.value
    ][0]
    assert command_parsed.payload_json["dispatch_metadata"] == {
        "source": "api",
        "request_id": "req-1",
    }


# ── No handler configured ──────────────────────────────────────────────────────


def test_replay_without_handler_stops_at_replay_requested(
    repo: ConversationRepository,
) -> None:
    orch = ConversationOrchestrator(repo, replay_handler=None)
    session_id = _create_session(repo, status="idle")

    result = orch.dispatch_user_input(
        session_id, "/replay path-1 http://127.0.0.1:5175/users"
    )

    assert result.allowed is True
    assert result.next_status == "replay_requested"
    assert result.replay_result is None

    session = repo.get_session(session_id)
    assert session is not None
    assert session.status == "replay_requested"


# ── Replay lifecycle events ────────────────────────────────────────────────────


def test_replay_lifecycle_events_in_correct_order(repo: ConversationRepository) -> None:
    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        return _make_summary(status="succeeded")

    orch = ConversationOrchestrator(repo, replay_handler=handler)
    session_id = _create_session(repo, status="idle")

    result = orch.dispatch_user_input(
        session_id, "/replay path-1 http://127.0.0.1:5175/users"
    )

    events = repo.list_events(session_id)
    event_types = [e.type for e in events]

    assert event_types == [
        ConversationEventType.COMMAND_PARSED.value,
        ConversationEventType.REPLAY_REQUESTED.value,
        ConversationEventType.STATE_CHANGED.value,
        ConversationEventType.STATE_CHANGED.value,
        ConversationEventType.REPLAY_COMPLETED.value,
        ConversationEventType.STATE_CHANGED.value,
    ]
    assert result.events_appended == event_types


def test_replay_event_payload_contains_summary(repo: ConversationRepository) -> None:
    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        return _make_summary(status="succeeded")

    orch = ConversationOrchestrator(repo, replay_handler=handler)
    session_id = _create_session(repo, status="idle")

    orch.dispatch_user_input(
        session_id, "/replay path-1 http://127.0.0.1:5175/users"
    )

    events = repo.list_events(session_id)
    replay_events = [
        e for e in events
        if e.type == ConversationEventType.REPLAY_COMPLETED.value
    ]
    assert len(replay_events) == 1
    payload = replay_events[0].payload_json
    assert payload["learned_path_id"] == "path-1"
    assert payload["url"] == "http://127.0.0.1:5175/users"
    assert payload["replay_status"] == "succeeded"


# ── State transition through replay_running ────────────────────────────────────


def test_replay_status_goes_idle_to_replay_running_to_completed(
    repo: ConversationRepository,
) -> None:
    def handler(_lid: str, _url: str) -> ConversationReplaySummary:
        return _make_summary(status="succeeded")

    orch = ConversationOrchestrator(repo, replay_handler=handler)
    session_id = _create_session(repo, status="idle")

    orch.dispatch_user_input(
        session_id, "/replay path-1 http://127.0.0.1:5175/users"
    )

    state_changes = [
        e for e in repo.list_events(session_id)
        if e.type == ConversationEventType.STATE_CHANGED.value
    ]
    from_values = [sc.payload_json["from"] for sc in state_changes]
    to_values = [sc.payload_json["to"] for sc in state_changes]

    assert "idle" in from_values
    assert "replay_requested" in to_values
    assert "replay_running" in to_values
    assert "completed" in to_values


# ── No path selection ──────────────────────────────────────────────────────────


def test_replay_uses_exact_path_id_no_selection(repo: ConversationRepository) -> None:
    calls: list[str] = []

    def handler(lid: str, _url: str) -> ConversationReplaySummary:
        calls.append(lid)
        return _make_summary()

    orch = ConversationOrchestrator(repo, replay_handler=handler)
    session_id = _create_session(repo, status="idle")

    orch.dispatch_user_input(
        session_id, "/replay exact-id http://127.0.0.1:5175/users"
    )

    assert calls == ["exact-id"]


# ── Forbidden imports ──────────────────────────────────────────────────────────


def test_orchestrator_does_not_import_autonomous_or_llm() -> None:
    from app.services.conversation import orchestrator as orchestrator_module

    source = inspect.getsource(orchestrator_module)
    forbidden_tokens = [
        "autonomous_explorer",
        "/exploration/autonomous-runs",
        "llm_provider",
        "OpenAI",
        "apps.cli",
    ]
    for token in forbidden_tokens:
        assert token not in source


# ── 11.3.1 visible browser operation ─────────────────────────────────────────


def test_run_explicit_replay_default_headless_remains_true(
    db_session: Session,
) -> None:
    """API-5: default headless remains True; override False reaches run_replay."""
    from unittest.mock import MagicMock, patch

    from app.services.conversation.replay_hook import run_explicit_replay

    row, _ = LearnedPathRepository(db_session).ingest_run(
        page_template="/users",
        query_signature={},
        dom_fingerprint="a" * 64,
        scenario="filter_by_status",
        actions=[{"step": 1, "action_type": "fill", "target_selector": "#q"}],
        source_run_id=None,
    )
    LearnedPathRepository(db_session).set_trust(
        row.id, TrustStatus.CONFIRMED, reason="test"
    )

    with patch(
        "app.services.conversation.replay_hook.run_replay"
    ) as mock_run_replay:
        mock_run_replay.return_value = MagicMock(
            learned_path_id=str(row.id),
            status="succeeded",
            drift_status="none",
            drift_reasons=[],
            warnings=[],
            final_url="http://127.0.0.1:5175/users",
            final_title="Users",
            steps=[],
        )
        run_explicit_replay(db_session, str(row.id), "http://127.0.0.1:5175/users")

    assert mock_run_replay.call_args.kwargs.get("headless") is True

    with patch(
        "app.services.conversation.replay_hook.run_replay"
    ) as mock_run_replay:
        mock_run_replay.return_value = MagicMock(
            learned_path_id=str(row.id),
            status="succeeded",
            drift_status="none",
            drift_reasons=[],
            warnings=[],
            final_url="http://127.0.0.1:5175/users",
            final_title="Users",
            steps=[],
        )
        run_explicit_replay(
            db_session, str(row.id), "http://127.0.0.1:5175/users", headless=False
        )

    assert mock_run_replay.call_args.kwargs.get("headless") is False


def test_run_explicit_replay_passes_slot_overrides(
    db_session: Session,
) -> None:
    from unittest.mock import MagicMock, patch

    row, _ = LearnedPathRepository(db_session).ingest_run(
        page_template="/records",
        query_signature={},
        dom_fingerprint="b" * 64,
        scenario="product_level",
        actions=[
            {
                "step": 1,
                "action_type": "fill",
                "target_selector": "#name",
                "value": "Alpha Record",
                "value_slot": "record_name",
            }
        ],
        source_run_id=None,
    )
    LearnedPathRepository(db_session).set_trust(
        row.id, TrustStatus.CONFIRMED, reason="test"
    )

    with patch(
        "app.services.conversation.replay_hook.run_replay"
    ) as mock_run_replay:
        mock_run_replay.return_value = MagicMock(
            learned_path_id=str(row.id),
            status="succeeded",
            drift_status="none",
            drift_reasons=[],
            warnings=[],
            final_url="http://example.test/records",
            final_title="Records",
            steps=[],
        )
        run_explicit_replay(
            db_session,
            str(row.id),
            "http://example.test/records",
            slot_overrides={"record_name": "Beta Record"},
        )

    assert mock_run_replay.call_args.kwargs["slot_overrides"] == {
        "record_name": "Beta Record"
    }


def test_run_explicit_replay_passes_evidence_targets(
    db_session: Session,
) -> None:
    from unittest.mock import MagicMock, patch

    row, _ = LearnedPathRepository(db_session).ingest_run(
        page_template="/records",
        query_signature={},
        dom_fingerprint="c" * 64,
        scenario="product_level",
        actions=[],
        source_run_id=None,
    )
    LearnedPathRepository(db_session).set_trust(
        row.id, TrustStatus.CONFIRMED, reason="test"
    )
    target = ExecutionEvidenceTarget(
        kind="dom_text_present",
        text="Beta Record 001",
        source_slot="record_name",
        selector="[data-testid='record-list']",
    )

    with patch(
        "app.services.conversation.replay_hook.run_replay"
    ) as mock_run_replay:
        mock_run_replay.return_value = MagicMock(
            learned_path_id=str(row.id),
            status="succeeded",
            drift_status="none",
            drift_reasons=[],
            warnings=[],
            final_url="http://example.test/records",
            final_title="Records",
            steps=[],
            execution_evidence=[],
        )
        run_explicit_replay(
            db_session,
            str(row.id),
            "http://example.test/records",
            evidence_targets=[target],
        )

    assert mock_run_replay.call_args.kwargs["evidence_targets"] == [target]


def test_run_explicit_replay_summary_contains_execution_evidence(
    db_session: Session,
) -> None:
    from unittest.mock import MagicMock, patch

    row, _ = LearnedPathRepository(db_session).ingest_run(
        page_template="/records",
        query_signature={},
        dom_fingerprint="d" * 64,
        scenario="product_level",
        actions=[],
        source_run_id=None,
    )
    LearnedPathRepository(db_session).set_trust(
        row.id, TrustStatus.CONFIRMED, reason="test"
    )
    evidence = [
        ExecutionEvidence(
            kind="dom_text_present",
            target="Beta Record 001",
            status="verified",
            confidence=0.95,
            summary="record list contains Beta Record 001.",
        )
    ]

    with patch(
        "app.services.conversation.replay_hook.run_replay"
    ) as mock_run_replay:
        mock_run_replay.return_value = MagicMock(
            learned_path_id=str(row.id),
            status="succeeded",
            drift_status="none",
            drift_reasons=[],
            warnings=[],
            final_url="http://example.test/records",
            final_title="Records",
            steps=[],
            execution_evidence=evidence,
        )
        summary = run_explicit_replay(
            db_session,
            str(row.id),
            "http://example.test/records",
        )

    assert summary.execution_evidence == evidence
