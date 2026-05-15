"""Tests for M12.3 deterministic recovery proposal generator."""

from __future__ import annotations

import copy
import inspect

import pytest
from pydantic import ValidationError

from app.schemas.recovery import RecoveryProposalOption
from app.services.recovery import proposal as proposal_module
from app.services.recovery.proposal import (
    RecoveryProposalGenerator,
    generate_recovery_proposal,
)


def _boundary(
    *,
    classification: str = "failure",
    recommendation: str = "stop",
    reason: str = "execution_error",
    evidence: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "classification": classification,
        "recommendation": recommendation,
        "reason": reason,
        "evidence": evidence or [],
    }


def _abort(
    *,
    decision: str = "accepted_stop",
    source: str = "slash_abort",
    session_status: str = "executing",
    has_inflight_action: bool = False,
    no_new_actions_after: bool = True,
    inflight_caveat: bool = False,
) -> dict[str, object]:
    return {
        "decision": decision,
        "message": f"Decision: {decision}",
        "evidence": {
            "signal": {"source": source},
            "state": {
                "session_status": session_status,
                "has_inflight_action": has_inflight_action,
            },
        },
        "no_new_actions_after": no_new_actions_after,
        "inflight_caveat": inflight_caveat,
    }


def generate(source: dict[str, object]):
    return generate_recovery_proposal(source)


# ------------------------------------------------------------------
# 1. Failure boundary -> review / retry / reteach options
# ------------------------------------------------------------------


def test_failure_stop_emits_abandon_task() -> None:
    result = generate(_boundary(
        classification="failure",
        recommendation="stop",
        reason="execution_error",
    ))

    assert result.source == "recovery_boundary"
    assert result.source_classification == "failure"
    assert len(result.options) == 1
    assert result.options[0].kind == "abandon_task"


def test_failure_suggest_reteach_emits_suggest_reteach() -> None:
    result = generate(_boundary(
        classification="failure",
        recommendation="suggest_reteach",
        reason="target_missing",
    ))

    assert len(result.options) == 1
    assert result.options[0].kind == "suggest_reteach"
    assert result.options[0].next_owner == "teaching_flow"


def test_failure_retry_possible_emits_review_and_retry_later() -> None:
    result = generate(_boundary(
        classification="failure",
        recommendation="retry_possible_requires_confirmation",
        reason="replay_failed",
    ))

    assert len(result.options) == 2
    kinds = [opt.kind for opt in result.options]
    assert "review_evidence" in kinds
    assert "consider_retry_later" in kinds


# ------------------------------------------------------------------
# 2. Blocked boundary -> ask_user_for_context
# ------------------------------------------------------------------


def test_blocked_ask_user_emits_ask_user_for_context() -> None:
    result = generate(_boundary(
        classification="blocked",
        recommendation="ask_user",
        reason="missing_context",
    ))

    assert len(result.options) == 1
    assert result.options[0].kind == "ask_user_for_context"
    assert result.options[0].next_owner == "user"
    assert "requires_user_context" in result.options[0].risk_hints


# ------------------------------------------------------------------
# 3. Uncertain boundary -> review_evidence
# ------------------------------------------------------------------


def test_uncertain_emits_review_evidence() -> None:
    result = generate(_boundary(
        classification="uncertain",
        recommendation="needs_review",
        reason="insufficient_postcondition_evidence",
    ))

    assert len(result.options) == 1
    assert result.options[0].kind == "review_evidence"
    assert "evidence_insufficient" in result.options[0].risk_hints


# ------------------------------------------------------------------
# 4. Needs_review boundary -> review_evidence
# ------------------------------------------------------------------


def test_needs_review_emits_review_evidence() -> None:
    result = generate(_boundary(
        classification="needs_review",
        recommendation="needs_review",
        reason="explicit_needs_review",
    ))

    assert len(result.options) == 1
    assert result.options[0].kind == "review_evidence"


# ------------------------------------------------------------------
# 5. Abort accepted_stop -> abandon_task + review_evidence
# ------------------------------------------------------------------


def test_abort_accepted_stop_emits_abandon_and_review() -> None:
    result = generate(_abort(
        decision="accepted_stop",
        session_status="executing",
    ))

    assert result.source == "abort_acknowledgement"
    assert result.source_decision == "accepted_stop"
    kinds = [opt.kind for opt in result.options]
    assert "abandon_task" in kinds
    assert "review_evidence" in kinds


# ------------------------------------------------------------------
# 6. Abort cannot_interrupt_inflight_action -> review_evidence + risk
# ------------------------------------------------------------------


def test_abort_inflight_emits_review_with_risk_hint() -> None:
    result = generate(_abort(
        decision="cannot_interrupt_inflight_action",
        has_inflight_action=True,
        inflight_caveat=True,
    ))

    assert len(result.options) == 1
    opt = result.options[0]
    assert opt.kind == "review_evidence"
    assert "inflight_action_risk" in opt.risk_hints
    assert "side_effects_unknown" in opt.risk_hints


# ------------------------------------------------------------------
# 7. All options non-executable
# ------------------------------------------------------------------


def test_all_options_non_executable_boundary() -> None:
    for recommendation in (
        "stop",
        "ask_user",
        "suggest_reteach",
        "retry_possible_requires_confirmation",
        "needs_review",
    ):
        result = generate(_boundary(recommendation=recommendation))
        for opt in result.options:
            assert opt.non_executable is True, (
                f"Option {opt.kind} from recommendation={recommendation} "
                f"should be non_executable"
            )


def test_all_options_non_executable_abort() -> None:
    for decision in (
        "accepted_stop",
        "cannot_interrupt_inflight_action",
        "already_finished",
        "already_failed",
        "needs_manual_review",
    ):
        result = generate(_abort(decision=decision))
        for opt in result.options:
            assert opt.non_executable is True, (
                f"Option {opt.kind} from decision={decision} "
                f"should be non_executable"
            )


def test_option_schema_rejects_executable_false() -> None:
    with pytest.raises(ValidationError):
        RecoveryProposalOption(
            kind="review_evidence",
            title="Review evidence",
            description="Review preserved evidence before choosing a next step.",
            non_executable=False,
        )


# ------------------------------------------------------------------
# 8. Recommended option is not auto-selected
# ------------------------------------------------------------------


def test_recommended_option_is_not_auto_selected() -> None:
    result = generate(_boundary(
        recommendation="retry_possible_requires_confirmation",
    ))

    # recommended_option_kinds is present but is display emphasis only
    assert hasattr(result, "recommended_option_kinds")
    # No selected_option_id or equivalent on the proposal
    assert not hasattr(result, "selected_option_id")
    assert not hasattr(result, "selected_kind")


# ------------------------------------------------------------------
# 9. No selected_option_id field
# ------------------------------------------------------------------


def test_proposal_schema_has_no_selected_option_id() -> None:
    from app.schemas.recovery import RecoveryProposal

    field_names = set(RecoveryProposal.model_fields.keys())
    assert "selected_option_id" not in field_names
    assert "selected_kind" not in field_names
    assert "selected" not in field_names


def test_option_schema_has_no_selected_option_id() -> None:
    field_names = set(RecoveryProposalOption.model_fields.keys())
    assert "selected_option_id" not in field_names
    assert "selected" not in field_names


# ------------------------------------------------------------------
# 10. Retry option handoff only
# ------------------------------------------------------------------


def test_retry_option_is_handoff_only() -> None:
    result = generate(_boundary(
        recommendation="retry_possible_requires_confirmation",
    ))

    retry_opts = [opt for opt in result.options if opt.kind == "consider_retry_later"]
    assert len(retry_opts) == 1
    opt = retry_opts[0]
    assert opt.next_owner == "retry_policy"
    assert opt.confirmation_requirement == "downstream_policy_check_required"
    assert "policy_check_required" in opt.risk_hints


# ------------------------------------------------------------------
# 11. Re-teach handoff only
# ------------------------------------------------------------------


def test_reteach_is_handoff_only() -> None:
    result = generate(_boundary(
        recommendation="suggest_reteach",
    ))

    assert len(result.options) == 1
    opt = result.options[0]
    assert opt.kind == "suggest_reteach"
    assert opt.next_owner == "teaching_flow"
    assert opt.non_executable is True


# ------------------------------------------------------------------
# 12. Takeover handoff only
# ------------------------------------------------------------------


def test_no_takeover_option_from_boundary() -> None:
    """handoff_to_takeover_later is not emitted by current boundary mapping."""
    for recommendation in (
        "stop",
        "ask_user",
        "suggest_reteach",
        "retry_possible_requires_confirmation",
        "needs_review",
    ):
        result = generate(_boundary(recommendation=recommendation))
        kinds = [opt.kind for opt in result.options]
        assert "handoff_to_takeover_later" not in kinds, (
            f"Unexpected takeover option from recommendation={recommendation}"
        )


# ------------------------------------------------------------------
# 13. Runtime observation handoff only
# ------------------------------------------------------------------


def test_no_runtime_observation_option_from_boundary() -> None:
    """wait_for_runtime_observation_later is not emitted by current mapping."""
    for recommendation in (
        "stop",
        "ask_user",
        "suggest_reteach",
        "retry_possible_requires_confirmation",
        "needs_review",
    ):
        result = generate(_boundary(recommendation=recommendation))
        kinds = [opt.kind for opt in result.options]
        assert "wait_for_runtime_observation_later" not in kinds, (
            f"Unexpected observation option from recommendation={recommendation}"
        )


# ------------------------------------------------------------------
# 14. Input immutability
# ------------------------------------------------------------------


def test_boundary_input_not_mutated() -> None:
    data = _boundary(
        classification="failure",
        recommendation="stop",
        reason="execution_error",
        evidence=[{"source": "test", "key": "k", "value": "v"}],
    )
    original = copy.deepcopy(data)

    generate(data)

    assert data == original


def test_abort_input_not_mutated() -> None:
    data = _abort(decision="accepted_stop")
    original = copy.deepcopy(data)

    generate(data)

    assert data == original


# ------------------------------------------------------------------
# 15. Evidence preservation
# ------------------------------------------------------------------


def test_boundary_evidence_preserved_in_proposal() -> None:
    evidence = [
        {"source": "execution", "key": "execution_status", "value": "failed"},
        {"source": "replay", "key": "replay_status", "value": "failed"},
    ]
    result = generate(_boundary(
        recommendation="stop",
        evidence=evidence,
    ))

    assert len(result.evidence_refs) == 2
    pairs = {(ref.source, ref.key): ref.value for ref in result.evidence_refs}
    assert pairs[("execution", "execution_status")] == "failed"
    assert pairs[("replay", "replay_status")] == "failed"


def test_abort_evidence_preserved_in_proposal() -> None:
    result = generate(_abort(
        decision="accepted_stop",
        source="ui_stop_button",
        session_status="replay_running",
    ))

    assert result.source_abort is not None
    assert result.source_abort.evidence.signal.source == "ui_stop_button"
    assert result.source_abort.evidence.state.session_status == "replay_running"


def test_abort_proposal_top_level_evidence_refs_populated() -> None:
    """P3: abort flow must populate proposal-level evidence_refs."""
    result = generate(_abort(
        decision="accepted_stop",
        source="slash_abort",
        session_status="executing",
    ))

    assert len(result.evidence_refs) > 0
    keys = {ref.key for ref in result.evidence_refs}
    assert "source" in keys
    assert "session_status" in keys


def test_needs_manual_review_with_inflight_preserves_risk_hints() -> None:
    """P2: unknown state + inflight caveat must carry inflight risk hints."""
    result = generate(_abort(
        decision="needs_manual_review",
        session_status="unknown_state",
        has_inflight_action=True,
        inflight_caveat=True,
    ))

    assert len(result.options) == 1
    opt = result.options[0]
    assert opt.kind == "review_evidence"
    assert "inflight_action_risk" in opt.risk_hints
    assert "side_effects_unknown" in opt.risk_hints
    assert "evidence_insufficient" in opt.risk_hints
    assert "in flight" in opt.description.lower()
    assert "side effects" in opt.description.lower()


# ------------------------------------------------------------------
# Abort edge cases
# ------------------------------------------------------------------


def test_abort_already_finished_returns_review() -> None:
    result = generate(_abort(
        decision="already_finished",
        session_status="completed",
        no_new_actions_after=False,
    ))

    assert len(result.options) == 1
    assert result.options[0].kind == "review_evidence"


def test_abort_already_failed_returns_review() -> None:
    result = generate(_abort(
        decision="already_failed",
        session_status="failed",
        no_new_actions_after=False,
    ))

    assert len(result.options) == 1
    assert result.options[0].kind == "review_evidence"
    assert "evidence_insufficient" in result.options[0].risk_hints


def test_abort_not_running_returns_empty_options() -> None:
    result = generate(_abort(
        decision="not_running",
        session_status="idle",
        no_new_actions_after=False,
    ))

    assert len(result.options) == 0


def test_abort_needs_manual_review_returns_review() -> None:
    result = generate(_abort(
        decision="needs_manual_review",
        session_status="unknown_state",
    ))

    assert len(result.options) == 1
    assert result.options[0].kind == "review_evidence"
    assert result.options[0].next_owner == "manual_review"


# ------------------------------------------------------------------
# No-recovery-needed returns empty
# ------------------------------------------------------------------


def test_no_recovery_needed_returns_empty_options() -> None:
    result = generate(_boundary(
        classification="success_no_recovery_needed",
        recommendation="no_recovery_needed",
        reason="task_succeeded",
    ))

    assert len(result.options) == 0


# ------------------------------------------------------------------
# Service class matches function entrypoint
# ------------------------------------------------------------------


def test_service_class_matches_function_entrypoint() -> None:
    data = _boundary(recommendation="stop")
    function_result = generate_recovery_proposal(data)
    service_result = RecoveryProposalGenerator().generate(data)

    assert function_result.model_dump() == service_result.model_dump()


# ------------------------------------------------------------------
# Recommended ordering
# ------------------------------------------------------------------


def test_recommended_kinds_ordered_by_rank() -> None:
    result = generate(_boundary(
        recommendation="retry_possible_requires_confirmation",
    ))

    # review_evidence has rank=0, consider_retry_later has rank=1
    assert result.recommended_option_kinds == ["review_evidence", "consider_retry_later"]


# ------------------------------------------------------------------
# Source boundary / abort preserved
# ------------------------------------------------------------------


def test_source_boundary_preserved_on_proposal() -> None:
    boundary_data = _boundary(recommendation="stop")
    result = generate(boundary_data)

    assert result.source_boundary is not None
    assert result.source_boundary.classification == "failure"
    assert result.source_boundary.recommendation == "stop"


def test_source_abort_preserved_on_proposal() -> None:
    abort_data = _abort(decision="accepted_stop")
    result = generate(abort_data)

    assert result.source_abort is not None
    assert result.source_abort.decision == "accepted_stop"


# ------------------------------------------------------------------
# Forbidden dependency scan
# ------------------------------------------------------------------


def test_proposal_module_has_no_forbidden_dependencies() -> None:
    """Scan for runtime side-effect imports in the proposal module."""
    source = inspect.getsource(proposal_module)
    forbidden_tokens = [
        "learned_path_replay",
        "run_replay",
        "autonomous_explorer",
        "/exploration/autonomous-runs",
        "llm_provider",
        "OpenAI",
        "sqlalchemy",
        "Session",
        "playwright",
        "requests",
        "httpx",
        "ConversationOrchestrator",
        "RecoveryBoundaryClassifier",
        "classify_recovery_boundary",
    ]
    for token in forbidden_tokens:
        assert token not in source, f"proposal.py must not reference {token}"


def test_proposal_does_not_import_classifier() -> None:
    """The proposal generator must not import or invoke the 12.1 classifier."""
    source = inspect.getsource(proposal_module)
    forbidden = [
        "RecoveryBoundaryClassifier",
        "classify_recovery_boundary",
    ]
    for token in forbidden:
        assert token not in source, f"proposal.py must not reference {token}"


# ------------------------------------------------------------------
# Unknown source shape -> conservative review
# ------------------------------------------------------------------


def test_unknown_source_shape_returns_conservative_review() -> None:
    result = generate({"foo": "bar", "baz": 123})

    assert len(result.options) == 1
    assert result.options[0].kind == "review_evidence"
    assert "unrecognized" in result.options[0].description.lower()
