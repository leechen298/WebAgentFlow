"""Tests for ``LearningBatchRepository``."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.models.learning_batch import (
    LearningBatch,
    LearningBatchStatus,
)
from app.repos.learning_batches_repo import LearningBatchRepository
from app.schemas.learning_batch import LearningBatchDetail, LearningBatchSummary


@pytest.fixture
def repo(db_session: Session) -> LearningBatchRepository:
    return LearningBatchRepository(db_session)


def _create_batch(repo: LearningBatchRepository) -> LearningBatch:
    return repo.create_pending(
        target_url="https://example.test/search",
        session_id="session-1",
        policy_json={"version": "bounded_learning_policy.v1"},
        request_json={"goal": "learn filters", "seed_value": "private"},
    )


def test_create_pending_batch_with_defaults(repo: LearningBatchRepository) -> None:
    row = _create_batch(repo)

    assert row.status == LearningBatchStatus.PENDING
    assert row.query_signature == {}
    assert row.planned_scenarios_json == []
    assert row.summary_json == {}
    assert row.created_run_ids_json == []
    assert row.created_capability_ids_json == []
    assert row.created_learned_path_ids_json == []
    assert row.started_at is None
    assert row.completed_at is None


def test_mark_running_sets_identity_and_planned_scenarios(
    repo: LearningBatchRepository,
) -> None:
    row = _create_batch(repo)

    updated = repo.mark_running(
        row.id,
        page_template="/search",
        query_signature={"view": "list"},
        dom_fingerprint="a" * 64,
        planned_scenarios=[{"scenario_id": "single-name"}],
    )

    assert updated.status == LearningBatchStatus.RUNNING
    assert updated.started_at is not None
    assert updated.page_template == "/search"
    assert updated.query_signature == {"view": "list"}
    assert updated.dom_fingerprint == "a" * 64
    assert updated.planned_scenarios_json == [{"scenario_id": "single-name"}]


def test_append_ids_dedupes_while_non_terminal(repo: LearningBatchRepository) -> None:
    row = repo.mark_running(_create_batch(repo).id)

    repo.append_run(row.id, "run-1")
    repo.append_run(row.id, "run-1")
    repo.append_capability(row.id, "cap-1")
    updated = repo.append_learned_path(row.id, "path-1")

    assert updated.created_run_ids_json == ["run-1"]
    assert updated.created_capability_ids_json == ["cap-1"]
    assert updated.created_learned_path_ids_json == ["path-1"]


def test_request_cancel_sets_cancel_requested_status(
    repo: LearningBatchRepository,
) -> None:
    row = repo.mark_running(_create_batch(repo).id)

    cancelled = repo.request_cancel(row.id, reason="operator_cancel")

    assert cancelled.status == LearningBatchStatus.CANCEL_REQUESTED
    assert cancelled.cancel_requested_at is not None
    assert cancelled.summary_json["cancel_reason"] == "operator_cancel"


def test_mark_running_does_not_overwrite_cross_session_cancel(
    repo: LearningBatchRepository,
) -> None:
    row = _create_batch(repo)
    other_session_factory = sessionmaker(bind=repo.session.get_bind())
    with other_session_factory() as other_session:
        LearningBatchRepository(other_session).request_cancel(
            row.id, reason="operator_cancel"
        )

    with pytest.raises(ValueError, match="cancellation requested"):
        repo.mark_running(row.id)

    refreshed = repo.get(row.id, fresh=True)
    assert refreshed is not None
    assert refreshed.status == LearningBatchStatus.CANCEL_REQUESTED


def test_mark_terminal_writes_summary_and_rejects_status_change(
    repo: LearningBatchRepository,
) -> None:
    row = repo.mark_running(_create_batch(repo).id)

    terminal = repo.mark_terminal(
        row.id,
        LearningBatchStatus.PARTIAL_SUCCESS,
        summary={"terminal_reason": "timeout_after_assets"},
        created_run_ids=["run-1"],
        created_capability_ids=["cap-1"],
        created_learned_path_ids=["path-1"],
    )

    assert terminal.status == LearningBatchStatus.PARTIAL_SUCCESS
    assert terminal.completed_at is not None
    assert terminal.summary_json["terminal_reason"] == "timeout_after_assets"
    assert terminal.created_run_ids_json == ["run-1"]
    assert terminal.created_capability_ids_json == ["cap-1"]
    assert terminal.created_learned_path_ids_json == ["path-1"]

    same = repo.mark_terminal(row.id, LearningBatchStatus.PARTIAL_SUCCESS)
    assert same.id == row.id

    with pytest.raises(ValueError, match="already terminal"):
        repo.mark_terminal(row.id, LearningBatchStatus.FAILED)


def test_mark_terminal_rejects_non_terminal_status(
    repo: LearningBatchRepository,
) -> None:
    row = repo.mark_running(_create_batch(repo).id)

    with pytest.raises(ValueError, match="not a terminal"):
        repo.mark_terminal(row.id, LearningBatchStatus.RUNNING)


def test_cancelled_batch_rejects_late_asset_attachment(
    repo: LearningBatchRepository,
) -> None:
    row = repo.mark_terminal(_create_batch(repo).id, LearningBatchStatus.CANCELLED)

    with pytest.raises(ValueError, match="cancelled batch"):
        repo.append_run(row.id, "run-late")
    with pytest.raises(ValueError, match="cancelled batch"):
        repo.append_capability(row.id, "cap-late")
    with pytest.raises(ValueError, match="cancelled batch"):
        repo.append_learned_path(row.id, "path-late")


def test_list_for_session_filters_status_and_paginates(
    repo: LearningBatchRepository,
) -> None:
    first = repo.mark_terminal(_create_batch(repo).id, LearningBatchStatus.COMPLETED)
    second = repo.create_pending(
        target_url="https://example.test/other",
        session_id="session-1",
        policy_json={},
        request_json={},
    )
    repo.create_pending(
        target_url="https://example.test/outside",
        session_id="session-2",
        policy_json={},
        request_json={},
    )
    second.created_at = first.created_at + timedelta(seconds=1)
    repo.session.commit()
    repo.session.refresh(second)

    completed, has_next, cursor = repo.list_for_session(
        "session-1",
        status=LearningBatchStatus.COMPLETED,
    )
    assert has_next is False
    assert cursor is None
    assert [row.id for row in completed] == [first.id]

    page, has_next, cursor = repo.list_for_session("session-1", limit=1)
    assert has_next is True
    assert cursor is not None
    assert page[0].id == second.id
    next_page, next_has_next, next_cursor = repo.list_for_session(
        "session-1",
        cursor=cursor,
        limit=1,
    )
    assert next_has_next is False
    assert next_cursor is None
    assert [row.id for row in next_page] == [first.id]


def test_schema_projection_redacts_sensitive_payloads(
    repo: LearningBatchRepository,
) -> None:
    row = repo.create_pending(
        target_url="https://example.test/search",
        session_id="session-1",
        policy_json={"playwright_payload": {"selector": "#private"}},
        request_json={"seed_value": "secret", "goal": "learn"},
    )
    row.summary_json = {
        "terminal_reason": "done",
        "raw_dom": "<div>private</div>",
        "nested": {"target_selector": "#private"},
    }
    row.planned_scenarios_json = [
        {
            "scenario_id": "single-filter",
            "input_bindings": [
                {
                    "binding_key": "keyword",
                    "adapter_type": "input",
                    "value": "secret keyword",
                }
            ],
            "fill_values": {"keyword": "secret keyword"},
            "toggle_values": {"enabled": "secret toggle"},
        }
    ]
    repo.session.commit()
    repo.session.refresh(row)

    summary_payload = LearningBatchSummary.model_validate(row).model_dump()
    detail_payload = LearningBatchDetail.model_validate(row).model_dump()

    assert "raw_dom" not in str(summary_payload)
    assert "target_selector" not in str(summary_payload)
    assert "seed_value" not in str(detail_payload)
    assert "playwright_payload" not in str(detail_payload)
    assert "secret" not in str(detail_payload)
    assert detail_payload["planned_scenarios"][0]["input_bindings"][0]["binding_key"] == "keyword"
    assert "value" not in detail_payload["planned_scenarios"][0]["input_bindings"][0]
    assert "fill_values" not in detail_payload["planned_scenarios"][0]
    assert "toggle_values" not in detail_payload["planned_scenarios"][0]


def test_model_collected_in_metadata() -> None:
    assert "learning_batches" in Base.metadata.tables
    tbl = Base.metadata.tables["learning_batches"]
    expected = {
        "id",
        "session_id",
        "target_url",
        "page_template",
        "query_signature",
        "dom_fingerprint",
        "status",
        "policy_json",
        "request_json",
        "planned_scenarios_json",
        "summary_json",
        "created_run_ids_json",
        "created_capability_ids_json",
        "created_learned_path_ids_json",
        "started_at",
        "completed_at",
        "cancel_requested_at",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(set(tbl.c.keys()))
    assert tbl.c.query_signature.server_default is not None
    assert tbl.c.status.server_default is not None
    assert tbl.c.planned_scenarios_json.server_default is not None
