"""Tests for ``LearnedCapabilityRepository``."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.exploration_run import (
    ExplorationMode,
    ExplorationRun,
    ExplorationRunStatus,
)
from app.models.learned_capability import (
    LearnedCapability,
    TrustStatus,
)
from app.repos.learned_capabilities_repo import (
    LearnedCapabilityRepository,
    compute_capability_dedup_key,
)
from app.repos.learned_paths_repo import LearnedPathRepository
from app.schemas.learned_capability import (
    LearnedCapabilityDetail,
    LearnedCapabilitySummary,
)


@pytest.fixture
def repo(db_session: Session) -> LearnedCapabilityRepository:
    return LearnedCapabilityRepository(db_session)


def _sample_evidence(**overrides) -> dict:
    base = {
        "version": "capability_evidence.v1",
        "source": "exploration_run",
        "terminal_outcome": "terminal_detected",
        "business_match_observed": True,
        "evidence_strength": "strong",
        "warnings": [],
        "redaction": {"normal_projection_hides_raw_debug": True},
        "debug": {
            "raw_selector": "#private-selector",
            "raw_dom": "<button data-testid='hidden'>Search</button>",
        },
    }
    base.update(overrides)
    return base


def _sample_ingest_kwargs(**overrides) -> dict:
    base = {
        "page_template": "/generic-search",
        "query_signature": {"view": "list"},
        "dom_fingerprint": "a" * 64,
        "capability_key": "filter-name-input",
        "capability_kind": "control_input",
        "human_label": "Name filter",
        "region_ref": "filter-panel",
        "control_ref": "filter-panel/name-input",
        "adapter_type": "input",
        "action_schema_json": {
            "version": "capability_action.v1",
            "adapter_type": "input",
            "operation": "fill",
            "required_slots": ["name"],
            "control_binding": {"role": "textbox"},
        },
        "sample_value_policy_json": {
            "version": "sample_value_policy.v1",
            "source": "visible_rows",
            "strength": "medium",
        },
        "terminal_target_json": {
            "version": "terminal_target.v1",
            "kind": "list_refresh",
            "result_region_ref": "results-table",
        },
        "evidence_json": _sample_evidence(),
        "source_run_id": None,
        "source_learned_path_id": None,
    }
    base.update(overrides)
    return base


def test_ingest_rejects_unknown_capability_kind(
    repo: LearnedCapabilityRepository,
) -> None:
    with pytest.raises(ValueError, match="unsupported capability_kind"):
        repo.ingest(**_sample_ingest_kwargs(capability_kind="target_specific_magic"))


def test_ingest_rejects_missing_action_schema_keys(
    repo: LearnedCapabilityRepository,
) -> None:
    with pytest.raises(ValueError, match="action_schema_json missing keys"):
        repo.ingest(**_sample_ingest_kwargs(action_schema_json={"version": "x"}))


def test_ingest_rejects_missing_evidence_keys(
    repo: LearnedCapabilityRepository,
) -> None:
    with pytest.raises(ValueError, match="evidence_json missing keys"):
        repo.ingest(**_sample_ingest_kwargs(evidence_json={"version": "x"}))


def test_ingest_rejects_direct_playwright_or_replay_payload(
    repo: LearnedCapabilityRepository,
) -> None:
    with pytest.raises(ValueError, match="action_schema_json contains forbidden key"):
        repo.ingest(
            **_sample_ingest_kwargs(
                action_schema_json={
                    "version": "capability_action.v1",
                    "adapter_type": "input",
                    "operation": "fill",
                    "required_slots": ["name"],
                    "control_binding": {"role": "textbox"},
                    "playwright_command": "page.click('#danger')",
                }
            )
        )

    with pytest.raises(ValueError, match="action_schema_json contains forbidden key"):
        repo.ingest(
            **_sample_ingest_kwargs(
                action_schema_json={
                    "version": "capability_action.v1",
                    "adapter_type": "input",
                    "operation": "fill",
                    "required_slots": ["name"],
                    "control_binding": {
                        "role": "textbox",
                        "binding_source": {"llm_payload": {"step": "click first"}},
                    },
                }
            )
        )

    with pytest.raises(ValueError, match="action_schema_json contains forbidden key"):
        repo.ingest(
            **_sample_ingest_kwargs(
                action_schema_json={
                    "version": "capability_action.v1",
                    "adapter_type": "input",
                    "operation": "fill",
                    "required_slots": ["name"],
                    "control_binding": {
                        "role": "textbox",
                        "binding_source": {"replay": [{"selector": "#danger"}]},
                    },
                }
            )
        )

    with pytest.raises(ValueError, match="action_schema_json contains forbidden key"):
        repo.ingest(
            **_sample_ingest_kwargs(
                action_schema_json={
                    "version": "capability_action.v1",
                    "adapter_type": "input",
                    "operation": "fill",
                    "required_slots": ["name"],
                    "control_binding": {
                        "role": "textbox",
                        "binding_source": {
                            "llm_steps": ["click the first visible match"]
                        },
                    },
                }
            )
        )


def test_ingest_creates_capability_with_required_fields(
    repo: LearnedCapabilityRepository,
) -> None:
    row, created = repo.ingest(**_sample_ingest_kwargs())

    assert created is True
    assert row.trust == TrustStatus.PROVISIONAL
    assert row.provenance == "system"
    assert row.capability_kind == "control_input"
    assert row.evidence_json["version"] == "capability_evidence.v1"
    assert row.trust_updated_at is None


def test_ingest_duplicate_returns_existing_without_overwriting_evidence(
    repo: LearnedCapabilityRepository,
) -> None:
    first, created_first = repo.ingest(**_sample_ingest_kwargs())
    first_evidence = dict(first.evidence_json)

    second, created_second = repo.ingest(
        **_sample_ingest_kwargs(
            evidence_json=_sample_evidence(
                terminal_outcome="terminal_unverified",
                warnings=["later evidence should not replace the first"],
            )
        )
    )

    assert created_first is True
    assert created_second is False
    assert second.id == first.id
    assert second.evidence_json == first_evidence


def test_compute_dedup_key_is_stable_for_sorted_json() -> None:
    key_a = compute_capability_dedup_key(
        page_template="/x",
        query_signature={"b": "2", "a": "1"},
        dom_fingerprint="fp",
        capability_kind="control_input",
        region_ref="filters",
        control_ref="filters/name",
        terminal_target_json={"kind": "list_refresh", "region": "results"},
    )
    key_b = compute_capability_dedup_key(
        page_template="/x",
        query_signature={"a": "1", "b": "2"},
        dom_fingerprint="fp",
        capability_kind="control_input",
        region_ref="filters",
        control_ref="filters/name",
        terminal_target_json={"region": "results", "kind": "list_refresh"},
    )

    assert key_a == key_b


def test_compute_dedup_key_excludes_sample_value_policy() -> None:
    base = {
        "page_template": "/x",
        "query_signature": {},
        "dom_fingerprint": "fp",
        "capability_kind": "control_input",
        "region_ref": "filters",
        "control_ref": "filters/name",
        "terminal_target_json": {"kind": "list_refresh"},
    }

    assert compute_capability_dedup_key(**base) == compute_capability_dedup_key(**base)


def test_set_trust_allows_legal_transition(repo: LearnedCapabilityRepository) -> None:
    row, _ = repo.ingest(**_sample_ingest_kwargs())

    updated = repo.set_trust(row.id, TrustStatus.CONFIRMED, reason="operator approved")

    assert updated.trust == TrustStatus.CONFIRMED
    assert updated.trust_reason == "operator approved"
    assert updated.trust_updated_at is not None


def test_set_trust_rejects_illegal_transition(repo: LearnedCapabilityRepository) -> None:
    row, _ = repo.ingest(**_sample_ingest_kwargs())

    with pytest.raises(ValueError, match="illegal trust transition"):
        repo.set_trust(row.id, TrustStatus.PROVISIONAL, reason=None)


def test_deleted_source_run_or_path_can_be_null(
    repo: LearnedCapabilityRepository,
    db_session: Session,
) -> None:
    run = ExplorationRun(
        page_signature="/generic-search",
        mode=ExplorationMode.FORM,
        status=ExplorationRunStatus.COMPLETED,
        success_criteria_ids_json=[],
        strategy_json={"kind": "autonomous"},
    )
    db_session.add(run)
    db_session.commit()

    row, _ = repo.ingest(**_sample_ingest_kwargs(source_run_id=run.id))
    db_session.delete(run)
    db_session.commit()
    db_session.refresh(row)

    assert row.source_run_id is None

    path_repo = LearnedPathRepository(db_session)
    learned_path, _ = path_repo.ingest_run(
        page_template="/generic-search",
        query_signature={},
        dom_fingerprint="b" * 64,
        scenario="search",
        actions=[{"action_type": "click", "selector": "#submit"}],
        source_run_id=None,
    )
    sourced_capability, _ = repo.ingest(
        **_sample_ingest_kwargs(
            dom_fingerprint="b" * 64,
            source_learned_path_id=learned_path.id,
        )
    )

    db_session.delete(learned_path)
    db_session.commit()
    db_session.refresh(sourced_capability)

    assert sourced_capability.source_learned_path_id is None


def test_list_page_filters_by_kind_and_trust(
    repo: LearnedCapabilityRepository,
) -> None:
    input_capability, _ = repo.ingest(**_sample_ingest_kwargs())
    repo.ingest(
        **_sample_ingest_kwargs(
            dom_fingerprint="c" * 64,
            capability_key="submit-search",
            capability_kind="submit_search",
            control_ref="filter-panel/search-button",
            adapter_type="button",
        )
    )
    repo.set_trust(input_capability.id, TrustStatus.CONFIRMED, reason=None)

    rows, has_next, cursor = repo.list_page(
        capability_kind="control_input",
        trust=TrustStatus.CONFIRMED,
    )

    assert has_next is False
    assert cursor is None
    assert [row.id for row in rows] == [input_capability.id]


def test_summary_projection_hides_raw_debug_payload(
    repo: LearnedCapabilityRepository,
) -> None:
    row, _ = repo.ingest(
        **_sample_ingest_kwargs(
            evidence_json=_sample_evidence(
                raw_selector="#leaky-selector",
                nested={"raw_dom": "<div>secret</div>"},
                raw_evidence={"target_selector": "#private-target"},
                terminal_detail={"learned_path_id": "lp-secret"},
            )
        )
    )

    summary = LearnedCapabilitySummary.model_validate(row)
    payload = summary.model_dump()

    assert payload["evidence"]["version"] == "capability_evidence.v1"
    assert "debug" not in payload["evidence"]
    assert "raw_selector" not in str(payload)
    assert "raw_dom" not in str(payload)


def test_projection_hides_source_learned_path_id(
    repo: LearnedCapabilityRepository,
    db_session: Session,
) -> None:
    path_repo = LearnedPathRepository(db_session)
    learned_path, _ = path_repo.ingest_run(
        page_template="/generic-search",
        query_signature={},
        dom_fingerprint="d" * 64,
        scenario="search",
        actions=[{"action_type": "click", "selector": "#submit"}],
        source_run_id=None,
    )
    row, _ = repo.ingest(
        **_sample_ingest_kwargs(
            dom_fingerprint="d" * 64,
            source_learned_path_id=learned_path.id,
        )
    )

    assert row.source_learned_path_id == learned_path.id

    summary_payload = LearnedCapabilitySummary.model_validate(row).model_dump()
    detail_payload = LearnedCapabilityDetail.model_validate(row).model_dump()

    assert "source_run_id" in summary_payload
    assert "source_learned_path_id" not in summary_payload
    assert "source_learned_path_id" not in detail_payload
    assert learned_path.id not in str(summary_payload)
    assert learned_path.id not in str(detail_payload)


def test_detail_projection_includes_action_terminal_and_sample_policy(
    repo: LearnedCapabilityRepository,
) -> None:
    row, _ = repo.ingest(
        **_sample_ingest_kwargs(
            action_schema_json={
                "version": "capability_action.v1",
                "adapter_type": "input",
                "operation": "fill",
                "required_slots": ["name"],
                "control_binding": {
                    "role": "textbox",
                    "raw_selector": "#private-input",
                    "target_selector": "#private-target",
                    "learned_path_id": "lp-secret",
                    "private_hint": "operator-only hint",
                },
            },
            terminal_target_json={
                "version": "terminal_target.v1",
                "kind": "list_refresh",
                "raw_dom": "<table>private</table>",
                "terminal_detail": {"raw_action": "private replay detail"},
                "evidence_targets": [{"selector": "#private-result"}],
                "path_id": "lp-secret",
            },
        )
    )

    detail = LearnedCapabilityDetail.model_validate(row)
    payload = detail.model_dump()

    assert detail.action_schema["version"] == "capability_action.v1"
    assert detail.sample_value_policy["version"] == "sample_value_policy.v1"
    assert detail.terminal_target["version"] == "terminal_target.v1"
    assert "raw_selector" not in str(payload["action_schema"])
    assert "target_selector" not in str(payload["action_schema"])
    assert "private_hint" not in str(payload["action_schema"])
    assert "raw_dom" not in str(payload["terminal_target"])
    assert "terminal_detail" not in str(payload["terminal_target"])
    assert "evidence_targets" not in str(payload["terminal_target"])
    assert "path_id" not in str(payload["terminal_target"])
    assert "lp-secret" not in str(payload)


def test_model_defines_server_defaults_for_sql_inserts() -> None:
    from app.models.base import Base

    tbl = Base.metadata.tables["learned_capabilities"]

    assert tbl.c.query_signature.server_default is not None
    assert tbl.c.provenance.server_default is not None
    assert tbl.c.trust.server_default is not None


def test_model_collected_in_metadata() -> None:
    from app.models.base import Base

    assert "learned_capabilities" in Base.metadata.tables
    tbl = Base.metadata.tables["learned_capabilities"]
    expected = {
        "id",
        "page_template",
        "query_signature",
        "dom_fingerprint",
        "capability_key",
        "capability_kind",
        "human_label",
        "region_ref",
        "control_ref",
        "adapter_type",
        "action_schema_json",
        "sample_value_policy_json",
        "terminal_target_json",
        "evidence_json",
        "provenance",
        "trust",
        "trust_reason",
        "trust_updated_at",
        "source_run_id",
        "source_learned_path_id",
        "dedup_key",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(set(tbl.c.keys()))


def test_learned_capability_returns_orm_row(
    repo: LearnedCapabilityRepository,
    db_session: Session,
) -> None:
    row, _ = repo.ingest(**_sample_ingest_kwargs())
    fetched = db_session.get(LearnedCapability, row.id)
    assert fetched is not None
    assert fetched.capability_key == "filter-name-input"
