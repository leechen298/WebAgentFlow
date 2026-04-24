"""Tests for ``LearnedPathRepository``."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.learned_path import LearnedPath, TrustStatus
from app.repos.learned_paths_repo import (
    LearnedPathRepository,
    compute_dedup_key,
)


@pytest.fixture
def repo(db_session: Session) -> LearnedPathRepository:
    return LearnedPathRepository(db_session)


def _sample_ingest_kwargs(**overrides) -> dict:
    base = dict(
        page_template="/users",
        query_signature={"status": "active"},
        dom_fingerprint="a" * 64,
        scenario="filter_by_status",
        actions=[{"selector": "#search-name", "action_type": "fill", "value": "bob"}],
        source_run_id=None,
    )
    base.update(overrides)
    return base


def test_ingest_creates_new_path_with_provisional_trust(
    repo: LearnedPathRepository,
) -> None:
    row, created = repo.ingest_run(**_sample_ingest_kwargs())

    assert created is True
    assert row.trust == TrustStatus.PROVISIONAL
    assert row.provenance == "system"
    assert row.hit_count == 1
    assert row.trust_updated_at is None


def test_ingest_is_idempotent_on_same_quadruple(
    repo: LearnedPathRepository,
) -> None:
    first, created_first = repo.ingest_run(**_sample_ingest_kwargs())
    second, created_second = repo.ingest_run(**_sample_ingest_kwargs())

    assert created_first is True
    assert created_second is False
    assert first.id == second.id
    assert second.hit_count == 2


def test_ingest_does_not_overwrite_earlier_actions(
    repo: LearnedPathRepository,
) -> None:
    first, _ = repo.ingest_run(**_sample_ingest_kwargs())
    first_actions = list(first.actions)

    repo.ingest_run(
        **_sample_ingest_kwargs(
            actions=[{"selector": "#other", "action_type": "click"}],
        )
    )

    assert first.actions == first_actions


def test_ingest_distinguishes_different_fingerprints(
    repo: LearnedPathRepository,
) -> None:
    row_a, _ = repo.ingest_run(
        **_sample_ingest_kwargs(dom_fingerprint="a" * 64)
    )
    row_b, created_b = repo.ingest_run(
        **_sample_ingest_kwargs(dom_fingerprint="b" * 64)
    )

    assert created_b is True
    assert row_a.id != row_b.id


def test_ingest_distinguishes_by_query_signature(
    repo: LearnedPathRepository,
) -> None:
    row_a, _ = repo.ingest_run(
        **_sample_ingest_kwargs(query_signature={"status": "active"})
    )
    row_b, created_b = repo.ingest_run(
        **_sample_ingest_kwargs(query_signature={"status": "draft"})
    )

    assert created_b is True
    assert row_a.id != row_b.id


def test_set_trust_provisional_to_confirmed(
    repo: LearnedPathRepository,
) -> None:
    row, _ = repo.ingest_run(**_sample_ingest_kwargs())

    updated = repo.set_trust(row.id, TrustStatus.CONFIRMED, reason="looks good")

    assert updated.trust == TrustStatus.CONFIRMED
    assert updated.trust_reason == "looks good"
    assert updated.trust_updated_at is not None


def test_set_trust_rejects_noop_transition(
    repo: LearnedPathRepository,
) -> None:
    row, _ = repo.ingest_run(**_sample_ingest_kwargs())

    with pytest.raises(ValueError, match="illegal trust transition"):
        repo.set_trust(row.id, TrustStatus.PROVISIONAL, reason=None)


def test_set_trust_rejects_illegal_transition(
    repo: LearnedPathRepository,
) -> None:
    row, _ = repo.ingest_run(**_sample_ingest_kwargs())
    repo.set_trust(row.id, TrustStatus.DEPRECATED, reason="wrong path")

    with pytest.raises(ValueError, match="illegal trust transition"):
        repo.set_trust(row.id, TrustStatus.FLAKY, reason=None)


def test_set_trust_deprecated_can_be_revived(
    repo: LearnedPathRepository,
) -> None:
    row, _ = repo.ingest_run(**_sample_ingest_kwargs())
    repo.set_trust(row.id, TrustStatus.DEPRECATED, reason="mis-click")

    revived = repo.set_trust(row.id, TrustStatus.CONFIRMED, reason="actually fine")

    assert revived.trust == TrustStatus.CONFIRMED


def test_set_trust_unknown_id_raises(repo: LearnedPathRepository) -> None:
    with pytest.raises(ValueError, match="not found"):
        repo.set_trust("not-a-real-id", TrustStatus.CONFIRMED, reason=None)


def test_find_by_source_run_returns_latest(
    repo: LearnedPathRepository, db_session: Session
) -> None:
    from app.models.exploration_run import (
        ExplorationMode,
        ExplorationRun,
        ExplorationRunStatus,
    )

    run = ExplorationRun(
        page_signature="/users",
        mode=ExplorationMode.FORM,
        status=ExplorationRunStatus.COMPLETED,
        success_criteria_ids_json=[],
        strategy_json={"kind": "autonomous"},
    )
    db_session.add(run)
    db_session.commit()

    repo.ingest_run(**_sample_ingest_kwargs(source_run_id=run.id))
    repo.ingest_run(
        **_sample_ingest_kwargs(dom_fingerprint="c" * 64, source_run_id=run.id)
    )

    hit = repo.find_by_source_run(run.id)
    assert hit is not None
    assert hit.source_run_id == run.id


def test_list_page_filters_by_trust(repo: LearnedPathRepository) -> None:
    a, _ = repo.ingest_run(**_sample_ingest_kwargs(dom_fingerprint="a" * 64))
    b, _ = repo.ingest_run(**_sample_ingest_kwargs(dom_fingerprint="b" * 64))
    repo.set_trust(a.id, TrustStatus.CONFIRMED, reason=None)

    rows, has_next, _ = repo.list_page(trust=TrustStatus.CONFIRMED)

    assert has_next is False
    assert [r.id for r in rows] == [a.id]


def test_list_page_cursor_pagination(repo: LearnedPathRepository) -> None:
    for i in range(3):
        repo.ingest_run(
            **_sample_ingest_kwargs(dom_fingerprint=str(i).rjust(64, "0"))
        )

    page1, has_next, cursor = repo.list_page(limit=2)
    assert has_next is True
    assert len(page1) == 2
    assert cursor is not None

    page2, has_next2, _ = repo.list_page(limit=2, cursor=cursor)
    assert has_next2 is False
    assert len(page2) == 1

    combined_ids = {row.id for row in page1 + page2}
    assert len(combined_ids) == 3


def test_compute_dedup_key_is_order_independent() -> None:
    key_a = compute_dedup_key(
        page_template="/x",
        query_signature={"a": "1", "b": "2"},
        dom_fingerprint="fp",
        scenario="s",
    )
    key_b = compute_dedup_key(
        page_template="/x",
        query_signature={"b": "2", "a": "1"},
        dom_fingerprint="fp",
        scenario="s",
    )
    assert key_a == key_b


def test_model_collected_in_metadata() -> None:
    from app.models.base import Base

    assert "learned_paths" in Base.metadata.tables
    tbl = Base.metadata.tables["learned_paths"]
    # §10.7 guardrail — no multi-tenant columns
    assert "user_id" not in tbl.c
    assert "scope_id" not in tbl.c

    # sanity: expected columns present
    expected = {
        "id",
        "page_template",
        "query_signature",
        "dom_fingerprint",
        "scenario",
        "actions",
        "provenance",
        "trust",
        "trust_reason",
        "trust_updated_at",
        "hit_count",
        "source_run_id",
        "dedup_key",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(set(tbl.c.keys()))


def test_learned_path_returns_orm_row(
    repo: LearnedPathRepository, db_session: Session
) -> None:
    row, _ = repo.ingest_run(**_sample_ingest_kwargs())
    fetched = db_session.get(LearnedPath, row.id)
    assert fetched is not None
    assert fetched.page_template == "/users"
