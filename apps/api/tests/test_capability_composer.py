from __future__ import annotations

import pytest

from app.models.learned_capability import LearnedCapability, TrustStatus
from app.models.learned_path import LearnedPath
from app.schemas.capability_composition import (
    CapabilityCompositionPlan,
    CapabilityCompositionPolicy,
    CapabilityCompositionRequest,
)
from app.services.learning.capability_composer import (
    CapabilityComposer,
    evaluate_composition_promotion,
)


def _request(**overrides) -> CapabilityCompositionRequest:
    payload = {
        "target_url": "http://example.test/customers",
        "page_template": "/customers",
        "user_goal": "search customers by name",
        "required_capability_kinds": ["control_input", "submit_search"],
        "slot_bindings": {"name": "Ada"},
        "dom_fingerprint": "a" * 64,
    }
    payload.update(overrides)
    return CapabilityCompositionRequest(**payload)


def _capability(
    capability_id: str,
    *,
    kind: str,
    trust: TrustStatus | str = TrustStatus.CONFIRMED,
    page_template: str = "/customers",
    query_signature: dict | None = None,
    dom_fingerprint: str = "a" * 64,
    control_ref: str | None = None,
    required_slots: list[str] | None = None,
    operation: str | None = None,
    terminal_kind: str = "list_refresh",
    action_version: str = "capability_action.v1",
    evidence: dict | None = None,
) -> LearnedCapability:
    operation = operation or ("click" if kind == "submit_search" else "fill")
    return LearnedCapability(
        id=capability_id,
        page_template=page_template,
        query_signature=query_signature or {},
        dom_fingerprint=dom_fingerprint,
        capability_key=capability_id,
        capability_kind=kind,
        human_label=kind,
        region_ref="region_filters",
        control_ref=control_ref or f"control_{capability_id}",
        adapter_type=operation,
        action_schema_json={
            "version": action_version,
            "adapter_type": operation,
            "operation": operation,
            "required_slots": required_slots if required_slots is not None else [],
            "control_binding": {"selector": f"#{capability_id}"},
        },
        sample_value_policy_json={"version": "sample_value_policy.v1"},
        terminal_target_json={"kind": terminal_kind},
        evidence_json=evidence if evidence is not None else {
            "version": "capability_evidence.v1",
            "source": "exploration_run",
            "terminal_outcome": "terminal_detected",
            "business_match_observed": True,
            "evidence_strength": "strong",
            "warnings": [],
            "redaction": {},
        },
        provenance="system",
        trust=trust,
        source_run_id=None,
        source_learned_path_id=None,
        dedup_key=capability_id,
    )


def test_composer_prefers_confirmed_learned_path() -> None:
    preferred = LearnedPath(
        id="path-1",
        page_template="/customers",
        query_signature={},
        dom_fingerprint="a" * 64,
        scenario="search customers",
        actions=[],
        trust=TrustStatus.CONFIRMED,
        source_run_id=None,
        dedup_key="path-1",
    )

    result = CapabilityComposer().compose(
        _request(),
        candidates=[],
        preferred_learned_path=preferred,
    )

    assert result.plan.status == "prefer_learned_path"
    assert result.plan.preferred_learned_path_id == "path-1"
    assert result.execution_handoff is None


def test_composer_does_not_prefer_cross_page_learned_path() -> None:
    preferred = LearnedPath(
        id="path-1",
        page_template="/orders",
        query_signature={},
        dom_fingerprint="a" * 64,
        scenario="search orders",
        actions=[],
        trust=TrustStatus.CONFIRMED,
        source_run_id=None,
        dedup_key="path-1",
    )

    result = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"]),
        candidates=[
            _capability("cap-input", kind="control_input", required_slots=["name"])
        ],
        preferred_learned_path=preferred,
    )

    assert result.plan.status == "ready"
    assert result.plan.preferred_learned_path_id is None


def test_composer_does_not_prefer_query_mismatch_or_missing_dom_path() -> None:
    query_mismatch = LearnedPath(
        id="path-query",
        page_template="/customers",
        query_signature={"tab": "archived"},
        dom_fingerprint="a" * 64,
        scenario="search customers",
        actions=[],
        trust=TrustStatus.CONFIRMED,
        source_run_id=None,
        dedup_key="path-query",
    )
    missing_dom_request = _request(dom_fingerprint=None)
    missing_dom_path = LearnedPath(
        id="path-no-dom",
        page_template="/customers",
        query_signature={},
        dom_fingerprint="a" * 64,
        scenario="search customers",
        actions=[],
        trust=TrustStatus.CONFIRMED,
        source_run_id=None,
        dedup_key="path-no-dom",
    )

    query_result = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"]),
        candidates=[
            _capability("cap-input", kind="control_input", required_slots=["name"])
        ],
        preferred_learned_path=query_mismatch,
    )
    dom_result = CapabilityComposer().compose(
        missing_dom_request,
        candidates=[
            _capability("cap-input", kind="control_input", required_slots=["name"])
        ],
        preferred_learned_path=missing_dom_path,
    )

    assert query_result.plan.status == "ready"
    assert query_result.plan.preferred_learned_path_id is None
    assert dom_result.plan.status == "unsafe"
    assert dom_result.plan.preferred_learned_path_id is None


def test_composer_reports_missing_capability() -> None:
    result = CapabilityComposer().compose(
        _request(),
        candidates=[_capability("cap-input", kind="control_input", required_slots=["name"])],
    )

    assert result.plan.status == "missing_capability"
    assert result.plan.missing_capabilities == ["submit_search"]
    assert result.execution_handoff is None


def test_composer_rejects_cross_page_candidate_as_unsafe() -> None:
    result = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"]),
        candidates=[
            _capability(
                "cap-other",
                kind="control_input",
                page_template="/orders",
                required_slots=["name"],
            )
        ],
    )

    assert result.plan.status == "unsafe"
    assert any("cross-page" in reason for reason in result.plan.rejection_reasons)


def test_composer_rejects_dom_mismatch_candidate_as_unsafe() -> None:
    result = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"]),
        candidates=[
            _capability(
                "cap-other-dom",
                kind="control_input",
                dom_fingerprint="b" * 64,
                required_slots=["name"],
            )
        ],
    )

    assert result.plan.status == "unsafe"
    assert any("dom-fingerprint" in reason for reason in result.plan.rejection_reasons)


def test_composer_rejects_query_mismatch_candidate_as_unsafe() -> None:
    result = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"], query_signature={"tab": "active"}),
        candidates=[
            _capability(
                "cap-other-query",
                kind="control_input",
                query_signature={"tab": "archived"},
                required_slots=["name"],
            )
        ],
    )

    assert result.plan.status == "unsafe"
    assert any("query-signature" in reason for reason in result.plan.rejection_reasons)


def test_composer_requires_current_dom_fingerprint_by_default() -> None:
    result = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"], dom_fingerprint=None),
        candidates=[
            _capability("cap-input", kind="control_input", required_slots=["name"])
        ],
    )

    assert result.plan.status == "unsafe"
    assert any("dom-fingerprint missing" in reason for reason in result.plan.rejection_reasons)


def test_composer_reports_ambiguous_candidates() -> None:
    result = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"]),
        candidates=[
            _capability("cap-name", kind="control_input", required_slots=["name"]),
            _capability("cap-email", kind="control_input", required_slots=["name"]),
        ],
    )

    assert result.plan.status == "ambiguous"
    assert "ambiguous candidate capabilities for required kind" in (
        result.plan.rejection_reasons
    )


def test_composer_rejects_missing_required_slot() -> None:
    result = CapabilityComposer().compose(
        _request(slot_bindings={}, required_capability_kinds=["control_input"]),
        candidates=[
            _capability("cap-name", kind="control_input", required_slots=["name"])
        ],
    )

    assert result.plan.status == "missing_capability"
    assert any("missing required slot name" in reason for reason in result.plan.rejection_reasons)


def test_composer_reports_unsupported_without_required_kinds() -> None:
    result = CapabilityComposer().compose(
        _request(required_capability_kinds=[]),
        candidates=[],
    )

    assert result.plan.status == "unsupported"
    assert result.execution_handoff is None


def test_composer_rejects_provisional_by_default_and_allows_by_policy() -> None:
    candidate = _capability(
        "cap-name",
        kind="control_input",
        trust=TrustStatus.PROVISIONAL,
        required_slots=["name"],
    )

    rejected = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"]),
        candidates=[candidate],
    )
    accepted = CapabilityComposer(
        CapabilityCompositionPolicy(allow_provisional_trust=True)
    ).compose(
        _request(required_capability_kinds=["control_input"]),
        candidates=[candidate],
    )

    assert rejected.plan.status == "missing_capability"
    assert accepted.plan.status == "ready"


@pytest.mark.parametrize("adapter", ["input", "text", "date", "month", "set_value"])
def test_composer_accepts_existing_ingest_adapter_names(adapter: str) -> None:
    result = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"]),
        candidates=[
            _capability(
                f"cap-{adapter}",
                kind="control_input",
                operation=adapter,
                required_slots=["name"],
            )
        ],
    )

    assert result.plan.status == "ready"
    assert result.execution_handoff is not None
    assert result.execution_handoff.ordered_action_schemas[0]["adapter_type"] == adapter
    assert result.execution_handoff.ordered_action_schemas[0]["operation"] == "set_value"
    assert result.plan.ordered_steps[0].action_kind == "set_value"


def test_composer_rejects_supported_adapter_with_unsupported_operation() -> None:
    candidate = _capability("cap-drag", kind="control_input", required_slots=["name"])
    candidate.action_schema_json["operation"] = "drag"

    result = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"]),
        candidates=[candidate],
    )

    assert result.plan.status == "missing_capability"
    assert any("unsupported operation" in reason for reason in result.plan.rejection_reasons)


def test_composer_rejects_unsupported_action_version_and_adapter() -> None:
    bad_version = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"]),
        candidates=[
            _capability(
                "cap-version",
                kind="control_input",
                action_version="capability_action.v0",
                required_slots=["name"],
            )
        ],
    )
    bad_adapter = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"]),
        candidates=[
            _capability(
                "cap-adapter",
                kind="control_input",
                operation="unsupported_widget",
                required_slots=["name"],
            )
        ],
    )

    assert bad_version.plan.status == "missing_capability"
    assert any(
        "unsupported action schema" in reason
        for reason in bad_version.plan.rejection_reasons
    )
    assert bad_adapter.plan.status == "missing_capability"
    assert any(
        "unsupported adapter type" in reason
        for reason in bad_adapter.plan.rejection_reasons
    )


def test_composer_rejects_terminal_failed_and_missing_evidence() -> None:
    terminal_failed = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"]),
        candidates=[
            _capability(
                "cap-failed",
                kind="control_input",
                required_slots=["name"],
                evidence={
                    "terminal_outcome": "terminal_failed",
                    "evidence_strength": "strong",
                },
            )
        ],
    )
    missing_evidence = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"]),
        candidates=[
            _capability(
                "cap-missing-evidence",
                kind="control_input",
                required_slots=["name"],
                evidence={},
            )
        ],
    )

    assert terminal_failed.plan.status == "missing_capability"
    assert any(
        "insufficient terminal evidence" in reason
        for reason in terminal_failed.plan.rejection_reasons
    )
    assert missing_evidence.plan.status == "missing_capability"
    assert any(
        "missing successful terminal evidence" in reason
        for reason in missing_evidence.plan.rejection_reasons
    )


def test_composer_rejects_missing_terminal_target() -> None:
    candidate = _capability("cap-input", kind="control_input", required_slots=["name"])
    candidate.terminal_target_json = {}

    result = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"]),
        candidates=[candidate],
    )

    assert result.plan.status == "missing_capability"
    assert any("missing terminal target" in reason for reason in result.plan.rejection_reasons)


def test_composer_rejects_conflicting_control_capabilities() -> None:
    result = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input", "control_select"]),
        candidates=[
            _capability(
                "cap-input",
                kind="control_input",
                control_ref="control_shared",
                required_slots=["name"],
            ),
            _capability(
                "cap-select",
                kind="control_select",
                operation="select",
                control_ref="control_shared",
            ),
        ],
    )

    assert result.plan.status == "unsafe"
    assert "conflicting capabilities write to the same control" in result.plan.rejection_reasons


def test_composer_builds_redacted_public_plan_and_private_handoff() -> None:
    result = CapabilityComposer().compose(
        _request(),
        candidates=[
            _capability("cap-input", kind="control_input", required_slots=["name"]),
            _capability("cap-submit", kind="submit_search", operation="click"),
        ],
    )

    assert result.plan.status == "ready"
    assert [step.capability_kind for step in result.plan.ordered_steps] == [
        "control_input",
        "submit_search",
    ]
    public_dump = result.plan.model_dump_json()
    assert "#cap-input" not in public_dump
    assert "#cap-submit" not in public_dump
    assert result.execution_handoff is not None
    assert result.execution_handoff.ordered_action_schemas[0]["control_binding"] == {
        "selector": "#cap-input"
    }
    assert "execution_handoff" not in result.model_dump()
    assert "ordered_action_schemas" not in result.model_dump_json()


def test_public_plan_schema_rejects_raw_selector_detail() -> None:
    try:
        CapabilityCompositionPlan(
            composition_id="composition_0000000000000000",
            target_url="http://example.test/customers",
            page_template="/customers",
            user_goal="search",
            status="ready",
            rejection_reasons=["selector #private leaked"],
        )
    except Exception as exc:
        assert "raw execution detail" in str(exc)
    else:  # pragma: no cover - defensive guard for schema regression.
        raise AssertionError("public plan should reject raw selector detail")


def test_public_plan_schema_rejects_raw_terminal_target_detail() -> None:
    try:
        CapabilityCompositionPlan(
            composition_id="composition_0000000000000000",
            target_url="http://example.test/customers",
            page_template="/customers",
            user_goal="search",
            status="ready",
            expected_terminal_target={"selector": "#private"},
        )
    except Exception as exc:
        assert "raw execution detail" in str(exc)
    else:  # pragma: no cover - defensive guard for schema regression.
        raise AssertionError("public plan should reject raw terminal detail")


def test_promotion_guard_rejects_plan_only_or_failed_evidence() -> None:
    plan = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"]),
        candidates=[
            _capability("cap-input", kind="control_input", required_slots=["name"])
        ],
    ).plan

    plan_only = evaluate_composition_promotion(plan, {})
    failed = evaluate_composition_promotion(
        plan,
        {
            "composition_id": plan.composition_id,
            "status": "failed",
            "terminal_target": {"kind": "list_refresh"},
            "source_capability_ids": ["cap-input"],
        },
    )

    assert plan_only.promotable is False
    assert "execution evidence is not successful" in plan_only.rejection_reasons
    assert failed.promotable is False


def test_promotion_guard_rejects_missing_source_and_incompatible_terminal() -> None:
    plan = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"]),
        candidates=[
            _capability("cap-input", kind="control_input", required_slots=["name"])
        ],
    ).plan

    missing_source = evaluate_composition_promotion(
        plan,
        {
            "composition_id": plan.composition_id,
            "status": "success",
            "terminal_target": {"kind": "list_refresh"},
            "source_capability_ids": [],
        },
    )
    incompatible_terminal = evaluate_composition_promotion(
        plan,
        {
            "composition_id": plan.composition_id,
            "status": "success",
            "terminal_target": {"kind": "toast_shown"},
            "source_capability_ids": ["cap-input"],
        },
    )

    assert missing_source.promotable is False
    assert "missing source capability ids" in missing_source.rejection_reasons
    assert incompatible_terminal.promotable is False
    assert "terminal evidence is incompatible with composition plan" in (
        incompatible_terminal.rejection_reasons
    )


def test_promotion_guard_accepts_successful_execution_evidence() -> None:
    plan = CapabilityComposer().compose(
        _request(required_capability_kinds=["control_input"]),
        candidates=[
            _capability("cap-input", kind="control_input", required_slots=["name"])
        ],
    ).plan

    decision = evaluate_composition_promotion(
        plan,
        {
            "composition_id": plan.composition_id,
            "status": "success",
            "terminal_target": {"kind": "list_refresh"},
            "source_capability_ids": ["cap-input"],
        },
    )

    assert decision.promotable is True
    assert decision.learned_path_metadata["source_capability_ids"] == ["cap-input"]
