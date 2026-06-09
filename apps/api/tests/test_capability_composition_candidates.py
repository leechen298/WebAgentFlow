from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.composition_candidate import CompositionCandidate
from app.models.learned_capability import LearnedCapability, TrustStatus
from app.models.learned_path import LearnedPath
from app.repos.composition_candidates_repo import CompositionCandidateRepository
from app.repos.learned_capabilities_repo import LearnedCapabilityRepository
from app.schemas.capability_composition_candidates import (
    CompositionCandidateGenerationRequest,
    CompositionCandidateStatus,
)
from app.schemas.learned_path_replay import WaitResult
from app.services.learning.capability_graph import CapabilityGraphBuilder
from app.services.learning.composition_candidate_executor import (
    CompositionCandidateExecutor,
    CompositionCandidateRuntimeResult,
)
from app.services.learning.composition_candidate_generator import (
    BoundedCompositionCandidateGenerator,
)
from app.services.learning.composition_promotion_service import (
    CompositionPromotionService,
)
from app.services.learning.composition_requirement_deriver import (
    CompositionRequirementDeriver,
)
from app.services.learning.learning_evidence_bundle import LearningEvidenceBundleBuilder


def _capability(
    capability_id: str,
    *,
    kind: str,
    page_template: str = "/customers",
    trust: TrustStatus = TrustStatus.CONFIRMED,
    required_slots: list[str] | None = None,
    control_ref: str | None = None,
    terminal_kind: str = "list_refresh",
) -> LearnedCapability:
    operation = "click" if kind in {"submit_search", "export_download"} else "fill"
    return LearnedCapability(
        id=capability_id,
        page_template=page_template,
        query_signature={},
        dom_fingerprint="a" * 64,
        capability_key=capability_id,
        capability_kind=kind,
        human_label=kind,
        region_ref="filters",
        control_ref=control_ref or f"control_{capability_id}",
        adapter_type=operation,
        action_schema_json={
            "version": "capability_action.v1",
            "adapter_type": operation,
            "operation": operation,
            "required_slots": required_slots or [],
            "control_binding": {"selector": f"#{capability_id}"},
        },
        sample_value_policy_json={"version": "sample_value_policy.v1"},
        terminal_target_json={"kind": terminal_kind},
        evidence_json={
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


def _request(**overrides) -> CompositionCandidateGenerationRequest:
    payload = {
        "target_url": "https://validation.example.invalid/customers?secret=seed",
        "page_template": "/customers",
        "query_signature": {},
        "dom_fingerprint": "a" * 64,
        "user_goal": "export filtered customers",
        "slot_bindings": {"name": "Ada"},
        "required_families": ["filters_then_submit", "filters_then_export"],
        "learning_batch_id": "batch-1",
    }
    payload.update(overrides)
    return CompositionCandidateGenerationRequest(**payload)


def test_generator_persists_bounded_ready_candidates(db_session: Session) -> None:
    repo = CompositionCandidateRepository(db_session)
    generator = BoundedCompositionCandidateGenerator(repo)

    result = generator.generate(
        _request(),
        capabilities=[
            _capability("cap-name", kind="control_input", required_slots=["name"]),
            _capability("cap-search", kind="submit_search"),
            _capability("cap-export", kind="export_download"),
        ],
    )

    assert result.coverage.required_family_coverage == 1.0
    assert result.coverage.generated_candidates == 2
    assert [candidate.candidate_family for candidate in result.candidates] == [
        "filters_then_submit",
        "filters_then_export",
    ]
    assert all(
        candidate.status == CompositionCandidateStatus.READY_FOR_EXECUTION
        for candidate in result.candidates
    )
    assert all(candidate.target_scope_ref.startswith("scope_") for candidate in result.candidates)
    assert all(
        all(source_ref.startswith("cap_ref_") for source_ref in candidate.source_capability_refs)
        for candidate in result.candidates
    )
    assert all(
        "source_capability_ids" not in candidate.model_dump(mode="json")
        for candidate in result.candidates
    )

    persisted = list(db_session.scalars(select(CompositionCandidate)).all())
    assert len(persisted) == 2
    assert {row.status for row in persisted} == {"ready_for_execution"}


def test_generator_records_static_rejection_for_missing_terminal(db_session: Session) -> None:
    result = BoundedCompositionCandidateGenerator(
        CompositionCandidateRepository(db_session)
    ).generate(
        _request(required_families=["filters_then_export"]),
        capabilities=[
            _capability("cap-name", kind="control_input", required_slots=["name"]),
        ],
    )

    assert result.coverage.required_family_coverage == 0.0
    assert result.candidates[0].status == CompositionCandidateStatus.REJECTED_STATIC
    assert "missing_capability" in (result.candidates[0].static_rejection_reason or "")


def test_generator_redacts_static_rejection_reason_before_public_return_and_persistence(
    db_session: Session,
) -> None:
    raw_id = "cap-private-static-rejection-id"
    mismatched = _capability(
        raw_id,
        kind="export_download",
        terminal_kind="download",
    )
    mismatched.dom_fingerprint = "b" * 64

    result = BoundedCompositionCandidateGenerator(
        CompositionCandidateRepository(db_session)
    ).generate(
        _request(required_families=["filters_then_export"]),
        capabilities=[mismatched],
    )

    public_reason = result.candidates[0].static_rejection_reason or ""
    persisted = db_session.scalar(select(CompositionCandidate))
    assert persisted is not None
    persisted_reason = persisted.static_rejection_reason or ""

    assert result.candidates[0].status == CompositionCandidateStatus.REJECTED_STATIC
    assert "dom-fingerprint mismatch rejected" in public_reason
    assert raw_id not in public_reason
    assert raw_id not in persisted_reason
    assert "redacted_ref" in public_reason
    assert "redacted_ref" in persisted_reason


def test_generator_can_derive_families_and_load_capabilities_from_page_scope(
    db_session: Session,
) -> None:
    capability_repo = LearnedCapabilityRepository(db_session)
    for capability in [
        _capability("cap-name", kind="control_input", required_slots=["name"]),
        _capability("cap-export", kind="export_download"),
    ]:
        db_session.add(capability)
    db_session.commit()

    result = BoundedCompositionCandidateGenerator(
        CompositionCandidateRepository(db_session),
        capability_repo=capability_repo,
    ).generate_for_scope(
        _request(
            required_families=[],
            user_goal="export filtered customers",
        ),
    )

    assert [candidate.candidate_family for candidate in result.candidates] == [
        "filters_then_export"
    ]
    assert result.candidates[0].status == CompositionCandidateStatus.READY_FOR_EXECUTION


def test_capability_graph_groups_scope_and_redacts_public_summary() -> None:
    graph = CapabilityGraphBuilder().build(
        page_template="/customers",
        query_signature={},
        dom_fingerprint="a" * 64,
        capabilities=[
            _capability("cap-name", kind="control_input", required_slots=["name"]),
            _capability("cap-export", kind="export_download", terminal_kind="download"),
            _capability("cap-other-page", kind="submit_search", page_template="/orders"),
        ],
    )

    assert set(graph.capabilities_by_kind) == {"control_input", "export_download"}
    assert [cap.id for cap in graph.capabilities_by_kind["control_input"]] == ["cap-name"]
    assert [cap.id for cap in graph.terminal_action_candidates] == ["cap-export"]
    assert graph.rejected_capability_reasons == {
        "capability_ref_3": "cross-page capability rejected"
    }
    public_summary = graph.public_summary()
    summary_text = str(public_summary)
    assert public_summary["capability_kind_counts"] == {
        "control_input": 1,
        "export_download": 1,
    }
    assert "cap-name" not in summary_text
    assert "#cap-name" not in summary_text
    assert "cap-other-page" not in summary_text


def test_requirement_deriver_uses_goal_and_graph_terminal_availability() -> None:
    graph = CapabilityGraphBuilder().build(
        page_template="/customers",
        query_signature={},
        dom_fingerprint="a" * 64,
        capabilities=[
            _capability("cap-name", kind="control_input", required_slots=["name"]),
        ],
    )

    derived = CompositionRequirementDeriver().derive(
        user_goal="export filtered customers",
        graph=graph,
    )

    assert derived.required_families == []
    assert derived.rejection_reasons == [
        "missing terminal capability for required family: filters_then_export"
    ]

    graph_with_terminal = CapabilityGraphBuilder().build(
        page_template="/customers",
        query_signature={},
        dom_fingerprint="a" * 64,
        capabilities=[
            _capability("cap-name", kind="control_input", required_slots=["name"]),
            _capability("cap-export", kind="export_download", terminal_kind="download"),
        ],
    )

    ready = CompositionRequirementDeriver().derive(
        user_goal="export filtered customers",
        graph=graph_with_terminal,
    )

    assert ready.required_families == ["filters_then_export"]
    assert ready.required_capability_kinds_by_family == {
        "filters_then_export": ["control_input", "export_download"]
    }
    assert ready.slot_requirements_by_family == {"filters_then_export": ["name"]}


def test_requirement_deriver_supports_chinese_goal_terms() -> None:
    graph = CapabilityGraphBuilder().build(
        page_template="/customers",
        query_signature={},
        dom_fingerprint="a" * 64,
        capabilities=[
            _capability("cap-name", kind="control_input", required_slots=["name"]),
            _capability("cap-search", kind="submit_search"),
            _capability("cap-export", kind="export_download", terminal_kind="download"),
            _capability("cap-detail", kind="open_detail", terminal_kind="navigation"),
            _capability("cap-reset", kind="reset_filters"),
        ],
    )

    deriver = CompositionRequirementDeriver()

    assert deriver.derive(user_goal="搜索用户", graph=graph).required_families == [
        "filters_then_submit"
    ]
    assert deriver.derive(user_goal="导出列表", graph=graph).required_families == [
        "filters_then_export"
    ]
    assert deriver.derive(user_goal="打开详情", graph=graph).required_families == [
        "filter_then_open_detail"
    ]
    assert deriver.derive(user_goal="重置筛选", graph=graph).required_families == [
        "reset_after_filters"
    ]


def test_executor_reconstructs_private_handoff_without_public_payload(
    db_session: Session,
) -> None:
    for capability in [
        _capability("cap-name", kind="control_input", required_slots=["name"]),
        _capability("cap-export", kind="export_download"),
    ]:
        db_session.add(capability)
    db_session.commit()

    result = BoundedCompositionCandidateGenerator(
        CompositionCandidateRepository(db_session),
        capability_repo=LearnedCapabilityRepository(db_session),
    ).generate_for_scope(_request(required_families=["filters_then_export"]))

    prepared = CompositionCandidateExecutor(db_session).prepare_execution_handoff(
        candidate_id=result.candidates[0].candidate_id,
        slot_bindings={"name": "Ada"},
    )

    assert prepared.status == CompositionCandidateStatus.READY_FOR_EXECUTION
    assert prepared.execution_handoff is not None
    assert prepared.execution_handoff.ordered_action_schemas[0]["control_binding"] == {
        "selector": "#cap-name"
    }

    bundle = LearningEvidenceBundleBuilder(db_session).build(
        operator_surface="cli",
        operator_command="wagent chat --non-live-summary",
        cwd="/Users/leechen/projects/WebAgentFlow/v0.1",
    )
    payload_text = str(bundle.model_dump(mode="json"))
    assert "ordered_action_schemas" not in payload_text
    assert "#cap-name" not in payload_text


def test_executor_records_negative_evidence_when_source_capability_missing(
    db_session: Session,
) -> None:
    repo = CompositionCandidateRepository(db_session)
    candidate = repo.upsert_generated(
        _request(required_families=["filters_then_export"]),
        candidate_family="filters_then_export",
        source_capability_ids=["missing-capability-id"],
        ordered_capability_kinds=["control_input", "export_download"],
        expected_terminal_target={"kind": "download"},
        generation_reason="required family matched",
        status=CompositionCandidateStatus.READY_FOR_EXECUTION,
    )

    prepared = CompositionCandidateExecutor(db_session).prepare_execution_handoff(
        candidate_id=candidate.candidate_id,
        slot_bindings={"name": "Ada"},
    )

    assert prepared.status == CompositionCandidateStatus.NEGATIVE_EVIDENCE_RECORDED
    assert prepared.execution_handoff is None
    assert prepared.rejection_reason == "source capability unavailable"
    refreshed = repo.get_by_candidate_id(candidate.candidate_id)
    assert refreshed is not None
    assert refreshed.status == CompositionCandidateStatus.NEGATIVE_EVIDENCE_RECORDED
    assert refreshed.negative_evidence_json["reason"] == "source capability unavailable"


def test_executor_records_negative_evidence_when_handoff_cannot_be_reconstructed(
    db_session: Session,
) -> None:
    db_session.add(_capability("cap-name", kind="control_input", required_slots=["name"]))
    db_session.add(_capability("cap-export", kind="export_download"))
    db_session.commit()
    result = BoundedCompositionCandidateGenerator(
        CompositionCandidateRepository(db_session),
        capability_repo=LearnedCapabilityRepository(db_session),
    ).generate_for_scope(_request(required_families=["filters_then_export"]))

    prepared = CompositionCandidateExecutor(db_session).prepare_execution_handoff(
        candidate_id=result.candidates[0].candidate_id,
        slot_bindings={},
    )

    assert prepared.status == CompositionCandidateStatus.NEGATIVE_EVIDENCE_RECORDED
    assert prepared.execution_handoff is None
    assert prepared.rejection_reason == "execution handoff reconstruction failed"
    row = CompositionCandidateRepository(db_session).get_by_candidate_id(
        result.candidates[0].candidate_id
    )
    assert row is not None
    assert row.negative_evidence_json["composition_status"] == "missing_capability"


def test_executor_runner_result_can_record_and_promote_candidate(
    db_session: Session,
) -> None:
    for capability in [
        _capability("cap-name", kind="control_input", required_slots=["name"]),
        _capability("cap-export", kind="export_download", terminal_kind="download"),
    ]:
        db_session.add(capability)
    db_session.commit()
    result = BoundedCompositionCandidateGenerator(
        CompositionCandidateRepository(db_session),
        capability_repo=LearnedCapabilityRepository(db_session),
    ).generate_for_scope(_request(required_families=["filters_then_export"]))

    def fake_runner(handoff) -> CompositionCandidateRuntimeResult:
        assert handoff.ordered_action_schemas[0]["control_binding"]["selector"] == "#cap-name"
        return CompositionCandidateRuntimeResult(
            execution_status="success",
            pass_gate_status="pass",
            terminal_state_verdict={
                "terminal_outcome": "terminal_detected",
                "terminal_type": "download",
                "evidence_strength": "strong",
                "stop_decision": "stop",
                "matched_action_types": ["click"],
            },
            terminal_target={"kind": "download"},
            actions=[
                {"action_type": "fill", "value_slot": "name"},
                {"action_type": "click"},
            ],
        )

    executed = CompositionCandidateExecutor(db_session).execute_candidate(
        candidate_id=result.candidates[0].candidate_id,
        slot_bindings={"name": "Ada"},
        runner=fake_runner,
        promote=True,
    )

    assert executed.status == CompositionCandidateStatus.PROMOTED_TO_LEARNED_PATH
    learned_path = db_session.scalar(select(LearnedPath))
    assert learned_path is not None
    assert learned_path.scenario == "composition:filters_then_export"
    assert learned_path.actions[0]["metadata"]["source_capability_ids"] == [
        "cap-name",
        "cap-export",
    ]


def test_executor_runner_failure_records_negative_evidence(
    db_session: Session,
) -> None:
    for capability in [
        _capability("cap-name", kind="control_input", required_slots=["name"]),
        _capability("cap-export", kind="export_download"),
    ]:
        db_session.add(capability)
    db_session.commit()
    result = BoundedCompositionCandidateGenerator(
        CompositionCandidateRepository(db_session),
        capability_repo=LearnedCapabilityRepository(db_session),
    ).generate_for_scope(_request(required_families=["filters_then_export"]))

    def failing_runner(_handoff) -> CompositionCandidateRuntimeResult:
        raise RuntimeError("browser action failed")

    executed = CompositionCandidateExecutor(db_session).execute_candidate(
        candidate_id=result.candidates[0].candidate_id,
        slot_bindings={"name": "Ada"},
        runner=failing_runner,
        promote=True,
    )

    assert executed.status == CompositionCandidateStatus.NEGATIVE_EVIDENCE_RECORDED
    assert db_session.scalar(select(LearnedPath)) is None
    assert executed.negative_evidence_json["reason"] == "execution runner failed"


def test_executor_default_runner_uses_execution_runtime_without_promotion(
    db_session: Session,
    monkeypatch,
) -> None:
    for capability in [
        _capability("cap-name", kind="control_input", required_slots=["name"]),
        _capability("cap-export", kind="export_download"),
    ]:
        db_session.add(capability)
    db_session.commit()
    result = BoundedCompositionCandidateGenerator(
        CompositionCandidateRepository(db_session),
        capability_repo=LearnedCapabilityRepository(db_session),
    ).generate_for_scope(_request(required_families=["filters_then_export"]))
    runtime_events: list[tuple[str, str | None]] = []
    executed_actions: list[dict] = []

    class FakeRuntime:
        page = object()

        def start(self) -> None:
            runtime_events.append(("start", None))

        def navigate(self, url: str) -> None:
            runtime_events.append(("navigate", url))

        def current_url(self) -> str:
            return "https://target.example.invalid/customers"

        def current_title(self) -> str:
            return "Customers"

        def stop(self) -> None:
            runtime_events.append(("stop", None))

    def fake_create_runtime(config):
        assert config.headless is True
        return FakeRuntime()

    def fake_execute_action(action, runtime):
        assert isinstance(runtime, FakeRuntime)
        executed_actions.append(
            {
                "step": action.step,
                "action_type": action.action_type,
                "target_selector": action.target_selector,
                "value": action.value,
                "value_slot": action.value_slot,
            }
        )
        return {
            "step_index": action.step,
            "action_type": action.action_type,
            "target_selector": action.target_selector,
            "value": action.value,
            "value_slot": action.value_slot,
            "ok": True,
        }

    monkeypatch.setattr(
        "app.services.learning.composition_candidate_executor.create_execution_runtime",
        fake_create_runtime,
    )
    monkeypatch.setattr(
        "app.services.learning.composition_candidate_executor.execute_action",
        fake_execute_action,
    )
    monkeypatch.setattr(
        "app.services.learning.composition_candidate_executor.wait_for_change_after_action",
        lambda **_: WaitResult(status="skipped"),
    )

    executed = CompositionCandidateExecutor(db_session).execute_candidate(
        candidate_id=result.candidates[0].candidate_id,
        slot_bindings={"name": "Ada"},
        target_url="https://target.example.invalid/customers",
        promote=True,
    )

    assert runtime_events == [
        ("start", None),
        ("navigate", "https://target.example.invalid/customers"),
        ("stop", None),
    ]
    assert executed_actions == [
        {
            "step": 1,
            "action_type": "fill",
            "target_selector": "#cap-name",
            "value": "Ada",
            "value_slot": "name",
        },
        {
            "step": 2,
            "action_type": "click",
            "target_selector": "#cap-export",
            "value": None,
            "value_slot": None,
        },
    ]
    assert executed.status == CompositionCandidateStatus.NEGATIVE_EVIDENCE_RECORDED
    assert executed.execution_outcome_json["status"] == "success"
    assert executed.execution_outcome_json["pass_gate_status"] == "unverified"
    assert executed.execution_outcome_json["browser_event_evidence"]["action_count"] == 2
    assert db_session.scalar(select(LearnedPath)) is None

    bundle = LearningEvidenceBundleBuilder(db_session).build(
        operator_surface="cli",
        operator_command="wagent chat --non-live-summary",
        cwd="/Users/leechen/projects/WebAgentFlow/v0.1",
    )
    bundle_text = str(bundle.model_dump(mode="json"))
    assert bundle.composition[0].execution_summary["browser_event_evidence"] == {
        "runtime_surface": "execution_runtime",
        "action_count": 2,
        "failed_action_count": 0,
        "wait_statuses": ["skipped", "skipped"],
    }
    assert "#cap-name" not in bundle_text
    assert "target.example.invalid" not in bundle_text


def test_executor_uses_persisted_target_url_when_runtime_url_not_supplied(
    db_session: Session,
    monkeypatch,
) -> None:
    for capability in [
        _capability("cap-name", kind="control_input", required_slots=["name"]),
        _capability("cap-export", kind="export_download"),
    ]:
        db_session.add(capability)
    db_session.commit()
    result = BoundedCompositionCandidateGenerator(
        CompositionCandidateRepository(db_session),
        capability_repo=LearnedCapabilityRepository(db_session),
    ).generate_for_scope(
        _request(
            required_families=["filters_then_export"],
            target_url="https://runtime.example.invalid/customers",
        )
    )
    navigated_urls: list[str] = []

    class FakeRuntime:
        page = object()

        def start(self) -> None:
            pass

        def navigate(self, url: str) -> None:
            navigated_urls.append(url)

        def stop(self) -> None:
            pass

    monkeypatch.setattr(
        "app.services.learning.composition_candidate_executor.create_execution_runtime",
        lambda _config: FakeRuntime(),
    )
    monkeypatch.setattr(
        "app.services.learning.composition_candidate_executor.execute_action",
        lambda action, _runtime: {
            "step_index": action.step,
            "action_type": action.action_type,
            "target_selector": action.target_selector,
            "ok": True,
        },
    )
    monkeypatch.setattr(
        "app.services.learning.composition_candidate_executor.wait_for_change_after_action",
        lambda **_: WaitResult(status="skipped"),
    )

    executed = CompositionCandidateExecutor(db_session).execute_candidate(
        candidate_id=result.candidates[0].candidate_id,
        slot_bindings={"name": "Ada"},
    )

    assert navigated_urls == ["https://runtime.example.invalid/customers"]
    assert executed.execution_outcome_json["pass_gate_status"] == "unverified"
    bundle = LearningEvidenceBundleBuilder(db_session).build(
        operator_surface="cli",
        operator_command="wagent chat --non-live-summary",
        cwd="/Users/leechen/projects/WebAgentFlow/v0.1",
    )
    assert "runtime.example.invalid" not in str(bundle.model_dump(mode="json"))


def _terminal_verdict() -> dict:
    return {
        "terminal_outcome": "terminal_detected",
        "terminal_type": "list_refresh",
        "evidence_strength": "strong",
        "stop_decision": "stop",
        "matched_action_types": ["click"],
    }


def test_promotion_service_requires_pass_gate_and_ingest_eligible_evidence(
    db_session: Session,
) -> None:
    repo = CompositionCandidateRepository(db_session)
    candidate = repo.upsert_generated(
        _request(),
        candidate_family="filters_then_submit",
        source_capability_ids=["cap-name", "cap-search"],
        ordered_capability_kinds=["control_input", "submit_search"],
        expected_terminal_target={"kind": "list_refresh"},
        generation_reason="required family matched",
        status=CompositionCandidateStatus.READY_FOR_EXECUTION,
    )
    service = CompositionPromotionService(db_session, repo)

    spoofed = service.record_execution_result(
        candidate_id=candidate.candidate_id,
        execution_status="success",
        pass_gate_status="unverified",
        terminal_state_verdict=_terminal_verdict(),
        terminal_target={"kind": "list_refresh"},
        actions=[{"action_type": "click"}],
    )

    assert spoofed.status == CompositionCandidateStatus.NEGATIVE_EVIDENCE_RECORDED
    assert db_session.scalar(select(LearnedPath)) is None

    passed = service.record_execution_result(
        candidate_id=candidate.candidate_id,
        execution_status="success",
        pass_gate_status="pass",
        terminal_state_verdict=_terminal_verdict(),
        terminal_target={"kind": "list_refresh"},
        actions=[
            {"action_type": "fill", "value_slot": "name"},
            {"action_type": "click", "metadata": {"composition_source": True}},
        ],
    )

    assert passed.status == CompositionCandidateStatus.NEGATIVE_EVIDENCE_RECORDED
    assert db_session.scalar(select(LearnedPath)) is None
    assert service.promote_executed_candidate(
        candidate_id=candidate.candidate_id,
        actions=[{"action_type": "click"}],
    ).status == CompositionCandidateStatus.NEGATIVE_EVIDENCE_RECORDED
    assert db_session.scalar(select(LearnedPath)) is None


def test_promotion_service_promotes_only_clean_ready_candidate(
    db_session: Session,
) -> None:
    repo = CompositionCandidateRepository(db_session)
    candidate = repo.upsert_generated(
        _request(),
        candidate_family="filters_then_submit",
        source_capability_ids=["cap-name", "cap-search"],
        ordered_capability_kinds=["control_input", "submit_search"],
        expected_terminal_target={"kind": "list_refresh"},
        generation_reason="required family matched",
        status=CompositionCandidateStatus.READY_FOR_EXECUTION,
    )

    service = CompositionPromotionService(db_session, repo)
    executed = service.record_execution_result(
        candidate_id=candidate.candidate_id,
        execution_status="success",
        pass_gate_status="pass",
        terminal_state_verdict=_terminal_verdict(),
        terminal_target={"kind": "list_refresh"},
        actions=[
            {"action_type": "fill", "value_slot": "name"},
            {"action_type": "click", "metadata": {"composition_source": True}},
        ],
    )
    assert executed.status == CompositionCandidateStatus.EXECUTION_PASSED

    promoted = service.promote_executed_candidate(
        candidate_id=candidate.candidate_id,
        actions=[
            {"action_type": "fill", "value_slot": "name"},
            {"action_type": "click", "metadata": {"composition_source": True}},
        ],
    )

    assert promoted.status == CompositionCandidateStatus.PROMOTED_TO_LEARNED_PATH
    learned_path = db_session.scalar(select(LearnedPath))
    assert learned_path is not None
    assert learned_path.scenario == "composition:filters_then_submit"
    assert learned_path.actions[0]["metadata"]["source_capability_ids"] == [
        "cap-name",
        "cap-search",
    ]


def test_promotion_uses_persisted_execution_actions_not_caller_supplied_actions(
    db_session: Session,
) -> None:
    repo = CompositionCandidateRepository(db_session)
    candidate = repo.upsert_generated(
        _request(),
        candidate_family="filters_then_submit",
        source_capability_ids=["cap-name", "cap-search"],
        ordered_capability_kinds=["control_input", "submit_search"],
        expected_terminal_target={"kind": "list_refresh"},
        generation_reason="required family matched",
        status=CompositionCandidateStatus.READY_FOR_EXECUTION,
    )
    service = CompositionPromotionService(db_session, repo)
    service.record_execution_result(
        candidate_id=candidate.candidate_id,
        execution_status="success",
        pass_gate_status="pass",
        terminal_state_verdict=_terminal_verdict(),
        terminal_target={"kind": "list_refresh"},
        actions=[
            {"action_type": "fill", "value_slot": "name"},
            {"action_type": "click", "metadata": {"composition_source": True}},
        ],
    )

    promoted = service.promote_executed_candidate(
        candidate_id=candidate.candidate_id,
        actions=[
            {
                "action_type": "click",
                "target_selector": "#never-executed",
                "value": "forged",
            }
        ],
    )

    assert promoted.status == CompositionCandidateStatus.PROMOTED_TO_LEARNED_PATH
    learned_path = db_session.scalar(select(LearnedPath))
    assert learned_path is not None
    assert learned_path.actions == [
        {
            "action_type": "fill",
            "value_slot": "name",
            "metadata": {"source_capability_ids": ["cap-name", "cap-search"]},
        },
        {
            "action_type": "click",
            "metadata": {
                "composition_source": True,
                "source_capability_ids": ["cap-name", "cap-search"],
            },
        },
    ]


def test_repo_does_not_regress_terminal_candidate_status(db_session: Session) -> None:
    repo = CompositionCandidateRepository(db_session)
    candidate = repo.upsert_generated(
        _request(),
        candidate_family="filters_then_submit",
        source_capability_ids=["cap-name", "cap-search"],
        ordered_capability_kinds=["control_input", "submit_search"],
        expected_terminal_target={"kind": "list_refresh"},
        generation_reason="required family matched",
        status=CompositionCandidateStatus.READY_FOR_EXECUTION,
    )
    repo.update_outcome(
        candidate,
        status=CompositionCandidateStatus.PROMOTED_TO_LEARNED_PATH,
        promotion_decision={"promotable": True},
    )

    preserved = repo.upsert_generated(
        _request(),
        candidate_family="filters_then_submit",
        source_capability_ids=["cap-name", "cap-search"],
        ordered_capability_kinds=["control_input", "submit_search"],
        expected_terminal_target={"kind": "list_refresh"},
        generation_reason="regenerated family",
        status=CompositionCandidateStatus.READY_FOR_EXECUTION,
    )

    assert preserved.status == CompositionCandidateStatus.PROMOTED_TO_LEARNED_PATH
    assert preserved.generation_reason == "required family matched"


def test_learning_evidence_bundle_redacts_private_target_details(
    db_session: Session,
) -> None:
    repo = CompositionCandidateRepository(db_session)
    repo.upsert_generated(
        _request(),
        candidate_family="filters_then_submit",
        source_capability_ids=["cap-name", "cap-search"],
        ordered_capability_kinds=["control_input", "submit_search"],
        expected_terminal_target={"kind": "list_refresh"},
        generation_reason="required family matched",
        status=CompositionCandidateStatus.READY_FOR_EXECUTION,
    )

    bundle = LearningEvidenceBundleBuilder(db_session).build(
        operator_surface="cli",
        operator_command="wagent chat --non-live-summary",
        cwd="/Users/leechen/projects/WebAgentFlow/v0.1",
    )
    payload = bundle.model_dump(mode="json")
    payload_text = str(payload)

    assert bundle.schema_version == "waf.learning_evidence_bundle.v1"
    assert payload["composition"][0]["target_scope_ref"].startswith("scope_")
    assert "validation.example.invalid" not in payload_text
    assert "secret=seed" not in payload_text
    assert "selector" not in payload_text
    assert "cap-name" not in payload_text


def test_learning_evidence_bundle_is_batch_scoped_and_redacts_rejection_reason(
    db_session: Session,
) -> None:
    repo = CompositionCandidateRepository(db_session)
    repo.upsert_generated(
        _request(learning_batch_id="batch-visible"),
        candidate_family="filters_then_export",
        source_capability_ids=["cap-name"],
        ordered_capability_kinds=["control_input", "export_download"],
        expected_terminal_target={"kind": "download"},
        generation_reason="static composition candidate rejected",
        status=CompositionCandidateStatus.REJECTED_STATIC,
        static_rejection_reason="missing_capability: raw-capability-id-123",
    )
    repo.upsert_generated(
        _request(learning_batch_id="batch-hidden", required_families=["reset_after_filters"]),
        candidate_family="reset_after_filters",
        source_capability_ids=["hidden-capability-id"],
        ordered_capability_kinds=["control_input", "reset_filters"],
        expected_terminal_target={"kind": "list_refresh"},
        generation_reason="required family matched",
        status=CompositionCandidateStatus.READY_FOR_EXECUTION,
    )

    bundle = LearningEvidenceBundleBuilder(db_session).build(
        operator_surface="cli",
        operator_command="wagent chat --non-live-summary",
        cwd="/Users/leechen/projects/WebAgentFlow/v0.1",
        learning_batch_id="batch-visible",
    )
    payload = bundle.model_dump(mode="json")
    payload_text = str(payload)

    assert len(payload["composition"]) == 1
    assert bundle.learning_batches == [{"batch_ref": "batch_ref_batch-visible"}]
    assert "raw-capability-id-123" not in payload_text
    assert "hidden-capability-id" not in payload_text
    assert payload["composition"][0]["static_rejection_reason"] == (
        "missing_capability: redacted_ref"
    )


def test_learning_evidence_bundle_includes_execution_gate_summary(
    db_session: Session,
) -> None:
    repo = CompositionCandidateRepository(db_session)
    candidate = repo.upsert_generated(
        _request(learning_batch_id="batch-visible"),
        candidate_family="filters_then_submit",
        source_capability_ids=["cap-name", "cap-search"],
        ordered_capability_kinds=["control_input", "submit_search"],
        expected_terminal_target={"kind": "list_refresh"},
        generation_reason="required family matched",
        status=CompositionCandidateStatus.READY_FOR_EXECUTION,
    )
    service = CompositionPromotionService(db_session, repo)
    service.record_execution_result(
        candidate_id=candidate.candidate_id,
        execution_status="success",
        pass_gate_status="pass",
        terminal_state_verdict=_terminal_verdict(),
        terminal_target={"kind": "list_refresh"},
        actions=[{"action_type": "click"}],
    )

    bundle = LearningEvidenceBundleBuilder(db_session).build(
        operator_surface="cli",
        operator_command="wagent chat --non-live-summary",
        cwd="/Users/leechen/projects/WebAgentFlow/v0.1",
        learning_batch_id="batch-visible",
    )

    assert bundle.composition[0].execution_summary == {
        "pass_gate_status": "pass",
        "terminal_outcome": "terminal_detected",
        "terminal_type": "list_refresh",
        "ingest_status": "eligible",
        "browser_event_evidence": {},
    }
    assert bundle.composition_summary == {
        "total_candidates": 1,
        "ready_for_execution_candidates": 0,
        "executed_candidates": 1,
        "execution_passed_candidates": 1,
        "promoted_candidates": 0,
        "negative_evidence_candidates": 0,
        "static_rejected_candidates": 0,
        "candidate_reasonable_rate": 1.0,
        "execution_attempt_coverage": 1.0,
        "promotion_reliability": None,
        "negative_evidence_capture_rate": None,
        "null_metric_reasons": {
            "negative_evidence_capture_rate": "no failed or rejected candidates",
            "promotion_reliability": "no promoted candidates"
        },
    }
