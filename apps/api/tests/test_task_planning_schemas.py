"""Tests for M11.1 task planning domain contract schemas.

These tests verify the contract shapes defined in 11.1.1 without exercising
retrieval, slot binding, execution, verification, or LLM behavior.
"""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from app.schemas import task_planning as tp_module
from app.schemas.task_planning import (
    AgentDPlannerInput,
    AgentDPlannerOutput,
    AgentEReporterInput,
    AgentEReporterOutput,
    ArtifactReference,
    ConfirmationRequirement,
    ConsentRequirement,
    LearnedPathCandidate,
    PostconditionSignal,
    RiskHint,
    RoutePlan,
    RouteStep,
    SlotBindingProposal,
    TaskExecutionResult,
    TaskInput,
    TaskIntent,
)

# ---------------------------------------------------------------------------
# Minimal valid data acceptance
# ---------------------------------------------------------------------------


def test_task_input_accepts_minimal_data() -> None:
    obj = TaskInput(raw_text="export users")

    assert obj.raw_text == "export users"
    assert obj.locale is None
    assert obj.metadata == {}


def test_task_intent_accepts_minimal_data() -> None:
    obj = TaskIntent(raw_text="export users")

    assert obj.raw_text == "export users"
    assert obj.normalized_goal is None
    assert obj.normalization_source == "none"
    assert obj.target_page_hint is None
    assert obj.scenario_hint is None
    assert obj.required_outputs == []
    assert obj.constraints == []
    assert obj.uncertainty == []


def test_learned_path_candidate_accepts_minimal_data() -> None:
    obj = LearnedPathCandidate(
        learned_path_id="path-1",
        scenario="users-export",
        page_template="/users",
        trust="confirmed",
    )

    assert obj.learned_path_id == "path-1"
    assert obj.hit_count == 0
    assert obj.match_reasons == []
    assert obj.warnings == []
    assert obj.drift_evidence_summary is None
    assert obj.negative_evidence_summary is None


def test_route_step_accepts_minimal_data() -> None:
    obj = RouteStep(order=0, learned_path_id="path-1", purpose="navigate to users")

    assert obj.order == 0
    assert obj.bound_slots == {}
    assert obj.can_execute is True
    assert obj.warnings == []


def test_route_plan_accepts_minimal_data() -> None:
    intent = TaskIntent(raw_text="export users")
    obj = RoutePlan(task_intent=intent)

    assert obj.id is None
    assert obj.confirmation_required is False
    assert obj.risk_hints == []
    assert obj.postconditions == []
    assert obj.uncertainty == []


def test_slot_binding_proposal_accepts_minimal_data() -> None:
    obj = SlotBindingProposal(slot_name="status", source_text="active")

    assert obj.slot_name == "status"
    assert obj.target_action_index is None
    assert obj.target_field is None
    assert obj.proposed_value is None
    assert obj.confidence == 0.0
    assert obj.requires_confirmation is False


def test_confirmation_requirement_accepts_minimal_data() -> None:
    obj = ConfirmationRequirement(
        reason="destructive action", message="This will delete data.", severity="high"
    )

    assert obj.reason == "destructive action"
    assert obj.fields == []
    assert obj.linked_risk_ids == []


def test_risk_hint_accepts_minimal_data() -> None:
    obj = RiskHint(risk_type="data_loss", reason="delete operation", severity="high")

    assert obj.id is None
    assert obj.policy_source is None


def test_consent_requirement_accepts_minimal_data() -> None:
    obj = ConsentRequirement(
        reason="legal compliance",
        message="Confirm you have authority.",
        severity="critical",
    )

    assert obj.fields == []
    assert obj.linked_risk_ids == []
    assert obj.requires_user_confirmation is True
    assert obj.policy_source is None


def test_postcondition_signal_accepts_minimal_data() -> None:
    obj = PostconditionSignal(signal_type="page_title")

    assert obj.expected is None
    assert obj.source is None
    assert obj.required is True


def test_task_execution_result_accepts_minimal_data() -> None:
    obj = TaskExecutionResult(status="succeeded")

    assert obj.failure_stage is None
    assert obj.failure_reason is None
    assert obj.route_plan_id is None
    assert obj.replay_results == []
    assert obj.postcondition_results == []
    assert obj.artifacts == []
    assert obj.final_state_summary is None
    assert obj.errors == []
    assert obj.warnings == []


def test_artifact_reference_accepts_minimal_placeholder_data() -> None:
    obj = ArtifactReference(kind="screenshot", label="final state")

    assert obj.uri is None
    assert obj.status == "pending"
    assert obj.metadata == {}


def test_agent_d_planner_input_accepts_minimal_data() -> None:
    intent = TaskIntent(raw_text="export users")
    obj = AgentDPlannerInput(task_intent=intent)

    assert obj.candidates == []
    assert obj.slot_proposals == []
    assert obj.negative_evidence_summaries == []
    assert obj.replay_evidence_summaries == []


def test_agent_d_planner_output_accepts_minimal_data() -> None:
    obj = AgentDPlannerOutput()

    assert obj.route_plan is None
    assert obj.confirmation_requirements == []
    assert obj.risk_hints == []
    assert obj.consent_requirements == []
    assert obj.uncertainty == []
    assert obj.warnings == []


def test_agent_e_reporter_input_accepts_minimal_data() -> None:
    result = TaskExecutionResult(status="succeeded")
    obj = AgentEReporterInput(task_execution_result=result)

    assert obj.postcondition_results == []
    assert obj.artifact_references == []
    assert obj.warnings == []
    assert obj.final_state_evidence == {}


def test_agent_e_reporter_output_accepts_minimal_data() -> None:
    obj = AgentEReporterOutput(status="succeeded", user_facing_summary="Done.")

    assert obj.evidence_summary is None
    assert obj.uncertainty == []
    assert obj.warnings == []
    assert obj.next_suggested_action is None


# ---------------------------------------------------------------------------
# Enum / literal validation
# ---------------------------------------------------------------------------


def test_normalization_source_rejects_invalid_value() -> None:
    with pytest.raises(ValidationError):
        TaskIntent(raw_text="x", normalization_source="invalid")  # type: ignore[call-arg]


def test_task_execution_status_rejects_invalid_value() -> None:
    with pytest.raises(ValidationError):
        TaskExecutionResult(status="invalid")  # type: ignore[call-arg]


def test_failure_stage_rejects_invalid_value() -> None:
    with pytest.raises(ValidationError):
        TaskExecutionResult(status="failed", failure_stage="invalid")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Structural assertions
# ---------------------------------------------------------------------------


def test_route_step_order_preserved_in_plan() -> None:
    intent = TaskIntent(raw_text="multi-step task")
    plan = RoutePlan(
        task_intent=intent,
        steps=[
            RouteStep(order=0, learned_path_id="a", purpose="first"),
            RouteStep(order=1, learned_path_id="b", purpose="second"),
            RouteStep(order=2, learned_path_id="c", purpose="third"),
        ],
    )

    orders = [step.order for step in plan.steps]
    assert orders == [0, 1, 2]


def test_slot_binding_confidence_enforced_range() -> None:
    with pytest.raises(ValidationError):
        SlotBindingProposal(slot_name="x", source_text="y", confidence=1.5)

    with pytest.raises(ValidationError):
        SlotBindingProposal(slot_name="x", source_text="y", confidence=-0.1)

    valid = SlotBindingProposal(slot_name="x", source_text="y", confidence=0.75)
    assert valid.confidence == 0.75


# ---------------------------------------------------------------------------
# Contract rules from 11.1.1
# ---------------------------------------------------------------------------


def test_schemas_do_not_define_identity_or_tenant_fields() -> None:
    """No user / account / tenant fields in any task planning schema."""
    forbidden = {"user", "account", "tenant", "user_id", "account_id", "tenant_id"}
    models = [
        TaskInput,
        TaskIntent,
        LearnedPathCandidate,
        RoutePlan,
        RouteStep,
        SlotBindingProposal,
        ConfirmationRequirement,
        RiskHint,
        ConsentRequirement,
        PostconditionSignal,
        TaskExecutionResult,
        ArtifactReference,
        AgentDPlannerInput,
        AgentDPlannerOutput,
        AgentEReporterInput,
        AgentEReporterOutput,
    ]

    for model in models:
        assert forbidden.isdisjoint(model.model_fields), f"{model.__name__} has forbidden field"


def test_task_planning_module_does_not_import_replay_autonomous_or_llm() -> None:
    source = inspect.getsource(tp_module)

    forbidden_tokens = [
        "learned_path_replay",
        "run_replay",
        "autonomous_explorer",
        "/exploration/autonomous-runs",
        "llm_provider",
        "OpenAI",
    ]
    for token in forbidden_tokens:
        assert token not in source, f"task_planning.py imports {token}"


def test_task_intent_raw_text_is_required() -> None:
    with pytest.raises(ValidationError):
        TaskIntent()  # type: ignore[call-arg]


def test_learned_path_candidate_rejects_invalid_trust() -> None:
    with pytest.raises(ValidationError):
        LearnedPathCandidate(
            learned_path_id="path-1",
            scenario="x",
            page_template="/x",
            trust="bogus",  # type: ignore[call-arg]
        )
