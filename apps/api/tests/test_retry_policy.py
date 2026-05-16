"""Tests for M12.4 deterministic retry / re-run policy evaluator."""

from __future__ import annotations

import copy
import inspect

from app.services.recovery import retry_policy as retry_policy_module
from app.services.recovery.retry_policy import (
    RetryPolicyEvaluator,
    evaluate_retry_policy,
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


def _proposal(
    *,
    source: str = "recovery_boundary",
    options: list[dict[str, object]] | None = None,
    evidence_refs: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "source": source,
        "options": options or [],
        "evidence_refs": evidence_refs or [],
    }


def _option(
    *,
    kind: str,
    title: str = "Option",
    description: str = "Description",
    risk_hints: list[str] | None = None,
    evidence_refs: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "kind": kind,
        "title": title,
        "description": description,
        "risk_hints": risk_hints or [],
        "evidence_refs": evidence_refs or [],
    }


def evaluate(source: dict[str, object], **kwargs: object):
    return evaluate_retry_policy(source, **kwargs)


# ------------------------------------------------------------------
# 1. consider_retry_later + clear evidence -> retry_allowed
# ------------------------------------------------------------------


def test_consider_retry_later_clear_evidence_allows_with_confirmation() -> None:
    result = evaluate(_proposal(
        options=[_option(
            kind="consider_retry_later",
            risk_hints=["policy_check_required"],
        )],
        evidence_refs=[{"source": "test", "key": "k", "value": "v"}],
    ))

    assert result.outcome == "retry_allowed_requires_confirmation"
    assert result.reason == "missing_user_confirmation"
    assert result.confirmation_requirement == "user_confirmation_required"


def test_consider_retry_later_clear_evidence_with_marker() -> None:
    result = evaluate(
        _proposal(
            options=[_option(
                kind="consider_retry_later",
                risk_hints=["policy_check_required"],
            )],
            evidence_refs=[{"source": "test", "key": "k", "value": "v"}],
        ),
        has_user_confirmation_marker=True,
    )

    assert result.outcome == "retry_allowed_requires_confirmation"
    assert result.reason == "retry_candidate_with_clear_evidence"
    assert result.confirmation_requirement == "user_confirmation_required"


# ------------------------------------------------------------------
# 2. consider_retry_later + side_effects_unknown -> retry_denied
# ------------------------------------------------------------------


def test_consider_retry_later_side_effects_unknown_denies() -> None:
    result = evaluate(_proposal(
        options=[_option(
            kind="consider_retry_later",
            risk_hints=["side_effects_unknown"],
        )],
        evidence_refs=[{"source": "test", "key": "k", "value": "v"}],
    ))

    assert result.outcome == "retry_denied"
    assert result.reason == "side_effects_unknown"
    assert result.risk_level == "high"


# ------------------------------------------------------------------
# 3. consider_retry_later + missing evidence -> needs context
# ------------------------------------------------------------------


def test_consider_retry_later_missing_evidence_needs_context() -> None:
    result = evaluate(_proposal(
        options=[_option(
            kind="consider_retry_later",
            risk_hints=["policy_check_required"],
        )],
        evidence_refs=[],
    ))

    assert result.outcome == "retry_needs_more_context"
    assert result.reason == "missing_execution_evidence"


# ------------------------------------------------------------------
# 4. abandon_task proposal -> no_retry_needed
# ------------------------------------------------------------------


def test_abandon_task_proposal_no_retry_needed() -> None:
    result = evaluate(_proposal(
        options=[_option(kind="abandon_task")],
    ))

    assert result.outcome == "no_retry_needed"
    assert result.reason == "task_abandoned"


# ------------------------------------------------------------------
# 5. review_evidence proposal -> retry_needs_manual_review
# ------------------------------------------------------------------


def test_review_evidence_proposal_needs_manual_review() -> None:
    result = evaluate(_proposal(
        options=[_option(kind="review_evidence")],
    ))

    assert result.outcome == "retry_needs_manual_review"
    assert result.reason == "missing_execution_evidence"


def test_review_evidence_with_inflight_risk_high_risk() -> None:
    result = evaluate(_proposal(
        options=[_option(
            kind="review_evidence",
            risk_hints=["inflight_action_risk", "side_effects_unknown"],
        )],
    ))

    assert result.outcome == "retry_needs_manual_review"
    assert result.reason == "side_effects_unknown"
    assert result.risk_level == "high"


# ------------------------------------------------------------------
# 6. abort accepted_stop -> retry_denied
# ------------------------------------------------------------------


def test_abort_accepted_stop_denies_retry() -> None:
    result = evaluate(_abort(decision="accepted_stop"))

    assert result.outcome == "retry_denied"
    assert result.reason == "abort_boundary_active"
    assert result.risk_level == "high"


# ------------------------------------------------------------------
# 7. abort cannot_interrupt_inflight_action -> retry_denied
# ------------------------------------------------------------------


def test_abort_inflight_denies_retry() -> None:
    result = evaluate(_abort(
        decision="cannot_interrupt_inflight_action",
        has_inflight_action=True,
        inflight_caveat=True,
    ))

    assert result.outcome == "retry_denied"
    assert result.reason == "side_effects_unknown"
    assert result.risk_level == "critical"


# ------------------------------------------------------------------
# 8. success_no_recovery_needed -> no_retry_needed
# ------------------------------------------------------------------


def test_success_no_recovery_needed_no_retry() -> None:
    result = evaluate(_boundary(
        classification="success_no_recovery_needed",
        recommendation="no_recovery_needed",
        reason="task_succeeded",
    ))

    assert result.outcome == "no_retry_needed"
    assert result.reason == "already_succeeded"


# ------------------------------------------------------------------
# 9-11. Boundary scenarios
# ------------------------------------------------------------------


def test_boundary_stop_denies_retry() -> None:
    result = evaluate(_boundary(
        recommendation="stop",
        reason="execution_error",
    ))

    assert result.outcome == "retry_denied"
    assert result.reason == "unsupported_replay_state"


def test_boundary_ask_user_needs_context() -> None:
    result = evaluate(_boundary(
        recommendation="ask_user",
        reason="missing_context",
    ))

    assert result.outcome == "retry_needs_more_context"
    assert result.reason == "missing_user_confirmation"


def test_boundary_retry_possible_with_confirmation_marker() -> None:
    result = evaluate(
        _boundary(
            recommendation="retry_possible_requires_confirmation",
            reason="replay_failed",
        ),
        has_user_confirmation_marker=True,
    )

    assert result.outcome == "retry_allowed_requires_confirmation"
    assert result.reason == "retry_candidate_with_clear_evidence"


def test_boundary_retry_possible_without_confirmation_still_allowed() -> None:
    result = evaluate(_boundary(
        recommendation="retry_possible_requires_confirmation",
        reason="replay_failed",
    ))

    assert result.outcome == "retry_allowed_requires_confirmation"
    assert result.reason == "missing_user_confirmation"
    assert result.confirmation_requirement == "user_confirmation_required"


def test_boundary_suggest_reteach_needs_review() -> None:
    result = evaluate(_boundary(
        recommendation="suggest_reteach",
        reason="target_missing",
    ))

    assert result.outcome == "retry_needs_manual_review"
    assert result.reason == "unsupported_replay_state"


def test_boundary_needs_review_needs_manual_review() -> None:
    result = evaluate(_boundary(
        recommendation="needs_review",
        reason="explicit_needs_review",
    ))

    assert result.outcome == "retry_needs_manual_review"
    assert result.reason == "missing_execution_evidence"


# ------------------------------------------------------------------
# 12. Abort edge cases
# ------------------------------------------------------------------


def test_abort_already_finished_needs_review() -> None:
    result = evaluate(_abort(
        decision="already_finished",
        session_status="completed",
        no_new_actions_after=False,
    ))

    assert result.outcome == "retry_needs_manual_review"
    assert result.reason == "missing_execution_evidence"


def test_abort_already_failed_denies_retry() -> None:
    result = evaluate(_abort(
        decision="already_failed",
        session_status="failed",
        no_new_actions_after=False,
    ))

    assert result.outcome == "retry_denied"
    assert result.reason == "irreversible_action_possible"


def test_abort_not_running_no_retry_needed() -> None:
    result = evaluate(_abort(
        decision="not_running",
        session_status="idle",
        no_new_actions_after=False,
    ))

    assert result.outcome == "no_retry_needed"
    assert result.reason == "not_running"


def test_abort_needs_manual_review_inflight_high_risk() -> None:
    result = evaluate(_abort(
        decision="needs_manual_review",
        session_status="unknown_state",
        has_inflight_action=True,
        inflight_caveat=True,
    ))

    assert result.outcome == "retry_needs_manual_review"
    assert result.reason == "side_effects_unknown"
    assert result.risk_level == "high"


def test_abort_needs_manual_review_no_inflight_medium_risk() -> None:
    result = evaluate(_abort(
        decision="needs_manual_review",
        session_status="unknown_state",
        inflight_caveat=False,
    ))

    assert result.outcome == "retry_needs_manual_review"
    assert result.reason == "missing_execution_evidence"
    assert result.risk_level == "medium"


# ------------------------------------------------------------------
# 13. Missing user confirmation -> allowed but not started
# ------------------------------------------------------------------


def test_missing_confirmation_allows_but_not_started() -> None:
    result = evaluate(
        _proposal(
            options=[_option(
                kind="consider_retry_later",
                risk_hints=["policy_check_required"],
            )],
            evidence_refs=[{"source": "test", "key": "k", "value": "v"}],
        ),
        has_user_confirmation_marker=False,
    )

    assert result.outcome == "retry_allowed_requires_confirmation"
    # Not retry_started
    assert result.outcome != "retry_started"


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

    evaluate(data)

    assert data == original


def test_abort_input_not_mutated() -> None:
    data = _abort(decision="accepted_stop")
    original = copy.deepcopy(data)

    evaluate(data)

    assert data == original


def test_proposal_input_not_mutated() -> None:
    data = _proposal(
        options=[_option(kind="consider_retry_later")],
        evidence_refs=[{"source": "test", "key": "k", "value": "v"}],
    )
    original = copy.deepcopy(data)

    evaluate(data)

    assert data == original


# ------------------------------------------------------------------
# 15. Forbidden dependency scan
# ------------------------------------------------------------------


def test_retry_policy_module_has_no_forbidden_dependencies() -> None:
    """Scan for runtime side-effect imports in the retry policy module."""
    source = inspect.getsource(retry_policy_module)
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
        assert token not in source, f"retry_policy.py must not reference {token}"


# ------------------------------------------------------------------
# 16. Evidence preservation
# ------------------------------------------------------------------


def test_proposal_evidence_preserved_in_decision() -> None:
    evidence = [
        {"source": "execution", "key": "status", "value": "failed"},
        {"source": "replay", "key": "drift", "value": "detected"},
    ]
    result = evaluate(_proposal(
        options=[_option(kind="review_evidence")],
        evidence_refs=evidence,
    ))

    assert len(result.evidence) == 2
    pairs = {(ref.source, ref.key): ref.value for ref in result.evidence}
    assert pairs[("execution", "status")] == "failed"
    assert pairs[("replay", "drift")] == "detected"


def test_boundary_evidence_preserved_in_decision() -> None:
    evidence = [
        {"source": "execution", "key": "execution_status", "value": "failed"},
    ]
    result = evaluate(_boundary(
        recommendation="stop",
        evidence=evidence,
    ))

    assert len(result.evidence) == 1
    assert result.evidence[0].source == "execution"
    assert result.evidence[0].key == "execution_status"


def test_abort_evidence_preserved_in_decision() -> None:
    result = evaluate(_abort(
        decision="accepted_stop",
        source="ui_stop_button",
        session_status="replay_running",
    ))

    assert len(result.evidence) > 0
    sources = {ref.source for ref in result.evidence}
    assert "abort_signal" in sources
    assert "abort_state" in sources


# ------------------------------------------------------------------
# 17. Service class matches function entrypoint
# ------------------------------------------------------------------


def test_service_class_matches_function_entrypoint() -> None:
    data = _boundary(recommendation="stop")
    function_result = evaluate_retry_policy(data)
    service_result = RetryPolicyEvaluator().evaluate(data)

    assert function_result.model_dump() == service_result.model_dump()


# ------------------------------------------------------------------
# 18. Unknown source shape
# ------------------------------------------------------------------


def test_unknown_source_shape_needs_review() -> None:
    result = evaluate({"foo": "bar", "baz": 123})

    assert result.outcome == "retry_needs_manual_review"
    assert result.reason == "policy_source_unknown"
    assert "unrecognized" in result.message.lower()


# ------------------------------------------------------------------
# 19. Dict-shaped proposal input
# ------------------------------------------------------------------


def test_dict_proposal_input_evaluated() -> None:
    result = evaluate(_proposal(
        source="recovery_boundary",
        options=[_option(kind="abandon_task")],
    ))

    assert result.outcome == "no_retry_needed"


# ------------------------------------------------------------------
# 20. Decision has no execution fields
# ------------------------------------------------------------------


def test_decision_has_no_execution_fields() -> None:
    result = evaluate(_boundary(recommendation="stop"))
    dumped = result.model_dump()

    forbidden_fields = [
        "command",
        "browser_action",
        "replay_command",
        "retry_command",
        "selected_option_id",
        "selected_kind",
        "write_back",
    ]
    for field in forbidden_fields:
        assert field not in dumped, f"Decision must not have {field}"


# ------------------------------------------------------------------
# 21. ask_user_for_context proposal -> needs context
# ------------------------------------------------------------------


def test_ask_user_for_context_proposal_needs_context() -> None:
    result = evaluate(_proposal(
        options=[_option(kind="ask_user_for_context")],
    ))

    assert result.outcome == "retry_needs_more_context"
    assert result.reason == "missing_user_confirmation"


# ------------------------------------------------------------------
# 22. suggest_reteach proposal -> needs review
# ------------------------------------------------------------------


def test_suggest_reteach_proposal_needs_review() -> None:
    result = evaluate(_proposal(
        options=[_option(kind="suggest_reteach")],
    ))

    assert result.outcome == "retry_needs_manual_review"
    assert result.reason == "unsupported_replay_state"


# ------------------------------------------------------------------
# 23. selected_option_kind restricts evaluation to selected option
# ------------------------------------------------------------------


def test_selected_option_kind_overrides_priority() -> None:
    """When selected_option_kind=review_evidence, abandon_task is ignored."""
    result = evaluate(
        _proposal(
            options=[
                _option(kind="abandon_task"),
                _option(kind="review_evidence"),
            ],
        ),
        selected_option_kind="review_evidence",
    )

    assert result.outcome == "retry_needs_manual_review"
    assert result.reason == "missing_execution_evidence"


def test_selected_option_kind_abandon_task_selected() -> None:
    """When selected_option_kind=abandon_task, review_evidence is ignored."""
    result = evaluate(
        _proposal(
            options=[
                _option(kind="abandon_task"),
                _option(kind="review_evidence"),
            ],
        ),
        selected_option_kind="abandon_task",
    )

    assert result.outcome == "no_retry_needed"
    assert result.reason == "task_abandoned"


def test_selected_option_kind_consider_retry_selected() -> None:
    """When selected_option_kind=consider_retry_later, abandon_task is ignored."""
    result = evaluate(
        _proposal(
            options=[
                _option(kind="abandon_task"),
                _option(
                    kind="consider_retry_later",
                    risk_hints=["policy_check_required"],
                ),
            ],
            evidence_refs=[{"source": "test", "key": "k", "value": "v"}],
        ),
        selected_option_kind="consider_retry_later",
    )

    assert result.outcome == "retry_allowed_requires_confirmation"
    assert result.reason == "missing_user_confirmation"


def test_selected_option_kind_not_found_fallback() -> None:
    """When selected_option_kind doesn't match any option, conservative fallback."""
    result = evaluate(
        _proposal(
            options=[_option(kind="abandon_task")],
        ),
        selected_option_kind="review_evidence",
    )

    # No matching option -> fallback
    assert result.outcome == "retry_needs_manual_review"
    assert result.reason == "policy_source_unknown"


# ------------------------------------------------------------------
# 24. Option-level evidence refs merged into decision
# ------------------------------------------------------------------


def test_option_level_evidence_merged() -> None:
    """Evidence from target option is included in the decision."""
    result = evaluate(_proposal(
        options=[_option(
            kind="review_evidence",
            evidence_refs=[
                {"source": "option_ev", "key": "detail", "value": "found"},
            ],
        )],
        evidence_refs=[],
    ))

    assert len(result.evidence) == 1
    assert result.evidence[0].source == "option_ev"
    assert result.evidence[0].key == "detail"


def test_proposal_and_option_evidence_merged() -> None:
    """Top-level and option-level evidence are merged without duplicates."""
    result = evaluate(_proposal(
        options=[_option(
            kind="review_evidence",
            evidence_refs=[
                {"source": "opt", "key": "k1", "value": "v1"},
                {"source": "top", "key": "k2", "value": "v2"},
            ],
        )],
        evidence_refs=[
            {"source": "top", "key": "k2", "value": "v2"},
            {"source": "top", "key": "k3", "value": "v3"},
        ],
    ))

    pairs = {(ref.source, ref.key): ref.value for ref in result.evidence}
    assert len(pairs) == 3
    assert pairs[("top", "k2")] == "v2"
    assert pairs[("top", "k3")] == "v3"
    assert pairs[("opt", "k1")] == "v1"


def test_consider_retry_uses_option_evidence_for_safety_check() -> None:
    """consider_retry_later with option-level evidence passes safety check."""
    result = evaluate(_proposal(
        options=[_option(
            kind="consider_retry_later",
            risk_hints=["policy_check_required"],
            evidence_refs=[
                {"source": "exec", "key": "status", "value": "failed"},
            ],
        )],
        evidence_refs=[],
    ))

    # Option-level evidence should satisfy the evidence check
    assert result.outcome == "retry_allowed_requires_confirmation"
    assert result.reason == "missing_user_confirmation"
