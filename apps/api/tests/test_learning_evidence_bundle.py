from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.exploration_run import ExplorationRun, ExplorationRunStatus
from app.models.learned_capability import LearnedCapability
from app.models.learned_path import LearnedPath, TrustStatus
from app.models.learning_batch import LearningBatch, LearningBatchStatus
from app.repos.composition_candidates_repo import CompositionCandidateRepository
from app.schemas.capability_composition_candidates import (
    CompositionCandidateGenerationRequest,
    CompositionCandidateStatus,
)
from app.services.learning.learning_evidence_bundle import LearningEvidenceBundleBuilder


def test_bundle_uses_redacted_candidate_and_capability_refs(db_session: Session) -> None:
    request = CompositionCandidateGenerationRequest(
        target_url="https://validation.example.invalid/users?seed=hidden",
        page_template="/users",
        query_signature={},
        dom_fingerprint="b" * 64,
        user_goal="export users",
        required_families=["filters_then_export"],
    )
    CompositionCandidateRepository(db_session).upsert_generated(
        request,
        candidate_family="filters_then_export",
        source_capability_ids=["cap-region-private-id", "cap-export-private-id"],
        ordered_capability_kinds=["control_input", "export_download"],
        expected_terminal_target={"kind": "download"},
        generation_reason="required family matched",
        status=CompositionCandidateStatus.READY_FOR_EXECUTION,
    )

    bundle = LearningEvidenceBundleBuilder(db_session).build(
        operator_surface="cli",
        operator_command="wagent chat --non-live-summary",
        cwd="/Users/leechen/projects/WebAgentFlow/v0.1",
    )
    payload_text = str(bundle.model_dump(mode="json"))

    assert bundle.composition[0].source_capability_refs[0].startswith("cap_ref_")
    assert "validation.example.invalid" not in payload_text
    assert "seed=hidden" not in payload_text
    assert "cap-region-private-id" not in payload_text
    assert "cap-export-private-id" not in payload_text


def test_bundle_redacts_static_rejection_reason_url_selector_and_secret(
    db_session: Session,
) -> None:
    request = CompositionCandidateGenerationRequest(
        target_url="https://validation.example.invalid/users?seed=hidden",
        page_template="/users",
        query_signature={},
        dom_fingerprint="b" * 64,
        user_goal="export users",
        required_families=["filters_then_export"],
        learning_batch_id="batch-visible",
    )
    CompositionCandidateRepository(db_session).upsert_generated(
        request,
        candidate_family="filters_then_export",
        source_capability_ids=["cap-private-id"],
        ordered_capability_kinds=["control_input", "export_download"],
        expected_terminal_target={"kind": "download"},
        generation_reason="static composition candidate rejected",
        status=CompositionCandidateStatus.REJECTED_STATIC,
        static_rejection_reason=(
            "missing slot on #private-user-filter at "
            "https://validation.example.invalid/users?seed=hidden "
            "target_url=https://validation.example.invalid/users?secret=seed"
        ),
    )

    bundle = LearningEvidenceBundleBuilder(db_session).build(
        operator_surface="cli",
        operator_command="wagent chat --non-live-summary",
        cwd="/Users/leechen/projects/WebAgentFlow/v0.1",
        learning_batch_id="batch-visible",
    )

    reason = bundle.composition[0].static_rejection_reason or ""
    payload_text = str(bundle.model_dump(mode="json"))
    assert "missing slot on" in reason
    assert "#private-user-filter" not in payload_text
    assert "validation.example.invalid" not in payload_text
    assert "seed=hidden" not in payload_text
    assert "secret=seed" not in payload_text
    assert "redacted_control" in reason
    assert "redacted_url" in reason
    assert "redacted_pair" in reason


def test_bundle_includes_redacted_context_sections_without_private_payload(
    db_session: Session,
) -> None:
    run = ExplorationRun(
        id="run-private-id",
        page_signature="/users",
        status=ExplorationRunStatus.COMPLETED,
        result_snapshot_json={
            "pass_gate": {"status": "pass"},
            "terminal_state_verdict": {
                "terminal_outcome": "terminal_detected",
                "terminal_type": "download",
            },
            "observation_summary": {"status": "observed"},
            "private_selector": "#private-user-filter",
        },
    )
    batch = LearningBatch(
        id="batch-visible",
        session_id="session-private-id",
        target_url="https://validation.example.invalid/users?seed=hidden",
        page_template="/users",
        query_signature={},
        dom_fingerprint="b" * 64,
        status=LearningBatchStatus.COMPLETED,
        policy_json={"max_candidates": 2},
        request_json={"goal": "export users"},
        planned_scenarios_json=["export"],
        summary_json={
            "planned": 1,
            "attempted": 1,
            "passed": 1,
            "failed": 0,
            "unverified": 0,
            "unsupported": 0,
            "warnings": ["redacted warning"],
        },
        created_run_ids_json=["run-private-id"],
        created_capability_ids_json=["cap-private-id"],
        created_learned_path_ids_json=["path-private-id"],
    )
    capability = LearnedCapability(
        id="cap-private-id",
        page_template="/users",
        query_signature={},
        dom_fingerprint="b" * 64,
        capability_key="cap-private-id",
        capability_kind="control_input",
        human_label="Private User Filter",
        region_ref="private-region",
        control_ref="private-control",
        adapter_type="fill",
        action_schema_json={
            "version": "capability_action.v1",
            "adapter_type": "fill",
            "operation": "fill",
            "required_slots": ["name"],
            "control_binding": {"selector": "#private-user-filter"},
        },
        sample_value_policy_json={"version": "sample_value_policy.v1"},
        terminal_target_json={"kind": "download"},
        evidence_json={
            "terminal_outcome": "terminal_detected",
            "evidence_strength": "strong",
        },
        provenance="system",
        trust=TrustStatus.CONFIRMED,
        source_run_id="run-private-id",
        source_learned_path_id=None,
        dedup_key="cap-private-id",
    )
    path = LearnedPath(
        id="path-private-id",
        page_template="/users",
        query_signature={},
        dom_fingerprint="b" * 64,
        scenario="composition:filters_then_export",
        actions=[
            {
                "action_type": "fill",
                "target_selector": "#private-user-filter",
                "metadata": {"source_capability_ids": ["cap-private-id"]},
            },
            {"action_type": "click", "target_selector": "#private-export"},
        ],
        provenance="system",
        trust=TrustStatus.CONFIRMED,
        source_run_id="run-private-id",
        dedup_key="path-private-id",
    )
    db_session.add_all([run, batch, capability, path])
    db_session.commit()

    request = CompositionCandidateGenerationRequest(
        target_url="https://validation.example.invalid/users?seed=hidden",
        page_template="/users",
        query_signature={},
        dom_fingerprint="b" * 64,
        user_goal="export users",
        required_families=["filters_then_export"],
        learning_batch_id="batch-visible",
        source_run_id="run-private-id",
    )
    repo = CompositionCandidateRepository(db_session)
    candidate = repo.upsert_generated(
        request,
        candidate_family="filters_then_export",
        source_capability_ids=["cap-private-id"],
        ordered_capability_kinds=["control_input", "export_download"],
        expected_terminal_target={"kind": "download"},
        generation_reason="required family matched",
        status=CompositionCandidateStatus.READY_FOR_EXECUTION,
    )
    repo.update_outcome(
        candidate,
        status=CompositionCandidateStatus.PROMOTED_TO_LEARNED_PATH,
        execution_outcome={
            "status": "success",
            "pass_gate_status": "pass",
            "terminal_state_verdict": {
                "terminal_outcome": "terminal_detected",
                "terminal_type": "download",
            },
            "attempt_ingest_evaluation": {"ingest_status": "eligible"},
        },
        promotion_decision={"promotable": True, "composition_id": candidate.candidate_id},
        promoted_learned_path_id="path-private-id",
    )

    bundle = LearningEvidenceBundleBuilder(db_session).build(
        operator_surface="cli",
        operator_command="wagent chat --non-live-summary",
        cwd="/Users/leechen/projects/WebAgentFlow/v0.1",
        learning_batch_id="batch-visible",
    )
    payload = bundle.model_dump(mode="json")
    payload_text = str(payload)

    assert payload["page_analysis_summary"]["candidate_count"] == 1
    assert payload["learning_batches"][0]["status"] == "completed"
    assert payload["learned_capabilities"][0]["kind"] == "control_input"
    assert payload["learned_capabilities"][0]["action_schema_summary"] == {
        "adapter_type": "fill",
        "operation": "fill",
        "required_slot_count": 1,
        "control_binding_redacted": True,
    }
    assert payload["learned_paths"][0]["action_count"] == 2
    assert payload["runs"][0]["pass_gate_status"] == "pass"
    assert payload["composition_summary"]["promotion_reliability"] == 1.0
    assert "validation.example.invalid" not in payload_text
    assert "seed=hidden" not in payload_text
    assert "session-private-id" not in payload_text
    assert "run-private-id" not in payload_text
    assert "cap-private-id" not in payload_text
    assert "path-private-id" not in payload_text
    assert "#private-user-filter" not in payload_text
    assert "#private-export" not in payload_text
    assert "Private User Filter" not in payload_text


def test_bundle_composition_summary_reports_contract_metrics(
    db_session: Session,
) -> None:
    repo = CompositionCandidateRepository(db_session)
    base_request = CompositionCandidateGenerationRequest(
        target_url="https://validation.example.invalid/users?seed=hidden",
        page_template="/users",
        query_signature={},
        dom_fingerprint="b" * 64,
        user_goal="export users",
        required_families=["filters_then_export"],
        learning_batch_id="batch-visible",
    )
    ready = repo.upsert_generated(
        base_request,
        candidate_family="filters_then_export",
        source_capability_ids=["cap-ready"],
        ordered_capability_kinds=["control_input", "export_download"],
        expected_terminal_target={"kind": "download"},
        generation_reason="required family matched",
        status=CompositionCandidateStatus.READY_FOR_EXECUTION,
    )
    executed_negative = repo.upsert_generated(
        base_request.model_copy(update={"required_families": ["filters_then_submit"]}),
        candidate_family="filters_then_submit",
        source_capability_ids=["cap-executed"],
        ordered_capability_kinds=["control_input", "submit_search"],
        expected_terminal_target={"kind": "list_refresh"},
        generation_reason="required family matched",
        status=CompositionCandidateStatus.READY_FOR_EXECUTION,
    )
    repo.update_outcome(
        executed_negative,
        status=CompositionCandidateStatus.NEGATIVE_EVIDENCE_RECORDED,
        execution_outcome={
            "status": "failed",
            "pass_gate_status": "fail",
            "attempt_ingest_evaluation": {"ingest_status": "ineligible"},
        },
        negative_evidence={"reason": "execution failed"},
    )
    static_rejected = repo.upsert_generated(
        base_request.model_copy(update={"required_families": ["reset_after_filters"]}),
        candidate_family="reset_after_filters",
        source_capability_ids=["cap-static"],
        ordered_capability_kinds=["control_input", "reset_filters"],
        expected_terminal_target={"kind": "list_refresh"},
        generation_reason="static rejected",
        status=CompositionCandidateStatus.REJECTED_STATIC,
        static_rejection_reason="missing_capability: cap-static",
    )
    promoted_without_eligible = repo.upsert_generated(
        base_request.model_copy(update={"required_families": ["filter_then_open_detail"]}),
        candidate_family="filter_then_open_detail",
        source_capability_ids=["cap-promoted"],
        ordered_capability_kinds=["control_input", "open_detail"],
        expected_terminal_target={"kind": "detail_page"},
        generation_reason="promoted stale fixture",
        status=CompositionCandidateStatus.READY_FOR_EXECUTION,
    )
    repo.update_outcome(
        promoted_without_eligible,
        status=CompositionCandidateStatus.PROMOTED_TO_LEARNED_PATH,
        execution_outcome={
            "status": "success",
            "pass_gate_status": "pass",
            "attempt_ingest_evaluation": {"ingest_status": "unverified"},
        },
        promotion_decision={"promotable": True},
        promoted_learned_path_id="path-promoted",
    )

    bundle = LearningEvidenceBundleBuilder(db_session).build(
        operator_surface="cli",
        operator_command="wagent chat --non-live-summary",
        cwd="/Users/leechen/projects/WebAgentFlow/v0.1",
        learning_batch_id="batch-visible",
    )

    assert ready.status == "ready_for_execution"
    assert static_rejected.status == "rejected_static"
    assert bundle.composition_summary == {
        "total_candidates": 4,
        "ready_for_execution_candidates": 1,
        "executed_candidates": 2,
        "execution_passed_candidates": 0,
        "promoted_candidates": 1,
        "negative_evidence_candidates": 1,
        "static_rejected_candidates": 1,
        "candidate_reasonable_rate": 0.75,
        "execution_attempt_coverage": 2 / 3,
        "promotion_reliability": 0.0,
        "negative_evidence_capture_rate": 1.0,
        "null_metric_reasons": {},
    }
