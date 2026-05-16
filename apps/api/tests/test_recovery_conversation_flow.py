"""M12.5 recovery conversation flow unit tests.

These tests prove that recovery sources map to user-facing responses and
state suggestions without executing recovery actions.
"""

from __future__ import annotations

import copy

import pytest

from app.schemas.recovery import (
    AbortAcknowledgement,
    AbortEvidence,
    EvidenceReference,
    RecoveryBoundary,
    RecoveryChoiceOption,
    RecoveryConversationEventPayload,
    RecoveryConversationResponse,
    RecoveryProposal,
    RecoveryProposalOption,
    RetryPolicyDecision,
    UserAbortSignal,
    UserAbortState,
)
from app.services.recovery.conversation_flow import (
    build_recovery_conversation_response,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _boundary(
    classification: str,
    recommendation: str,
    reason: str,
    message: str | None = None,
) -> RecoveryBoundary:
    return RecoveryBoundary(
        classification=classification,  # type: ignore[arg-type]
        recommendation=recommendation,  # type: ignore[arg-type]
        reason=reason,  # type: ignore[arg-type]
        message=message,
        evidence=[
            EvidenceReference(
                source="classifier",
                key="classification",
                value=classification,
            )
        ],
    )


def _abort(
    decision: str,
    message: str,
    no_new_actions_after: bool = True,
    inflight_caveat: bool = False,
) -> AbortAcknowledgement:
    return AbortAcknowledgement(
        decision=decision,  # type: ignore[arg-type]
        message=message,
        evidence=AbortEvidence(
            signal=UserAbortSignal(source="slash_abort"),
            state=UserAbortState(session_status="executing"),
        ),
        no_new_actions_after=no_new_actions_after,
        inflight_caveat=inflight_caveat,
    )


def _proposal(
    *options: RecoveryProposalOption,
    recommended: list[str] | None = None,
) -> RecoveryProposal:
    return RecoveryProposal(
        source="recovery_boundary",
        options=list(options),
        recommended_option_kinds=recommended or [],
    )


def _option(
    kind: str,
    title: str,
    description: str,
    rank: int | None = None,
) -> RecoveryProposalOption:
    return RecoveryProposalOption(
        kind=kind,  # type: ignore[arg-type]
        title=title,
        description=description,
        rank=rank,
    )


def _retry(
    outcome: str,
    reason: str,
    message: str | None = None,
) -> RetryPolicyDecision:
    return RetryPolicyDecision(
        outcome=outcome,  # type: ignore[arg-type]
        reason=reason,  # type: ignore[arg-type]
        message=message,
    )


# ---------------------------------------------------------------------------
# Unit: failure boundary
# ---------------------------------------------------------------------------


def test_failure_boundary_shows_proposal_options() -> None:
    boundary = _boundary("failure", "retry_possible_requires_confirmation", "replay_failed")
    proposal = _proposal(
        _option("consider_retry_later", "Retry", "Try again later"),
        _option("abandon_task", "Abandon", "Give up"),
    )

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        boundary=boundary,
        proposal=proposal,
    )

    assert resp.decision == "show_recovery_options"
    # Boundary message merged into proposal response
    assert resp.reason == "boundary_failure"
    assert resp.prompt is not None
    assert len(resp.prompt.options) == 2
    assert resp.next_status_suggestion == "show_recovery_options"
    assert "did not complete successfully" in resp.user_response
    assert "recovery options are available" in resp.user_response
    # Boundary evidence merged into event payload
    assert resp.event_payload_suggestion is not None
    assert any(ev.source == "classifier" for ev in resp.event_payload_suggestion.evidence_refs)
    # No execution command
    assert resp.event_payload_suggestion.non_executable is True


def test_failure_boundary_without_proposal_returns_manual_review() -> None:
    boundary = _boundary("failure", "retry_possible_requires_confirmation", "replay_failed")

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        boundary=boundary,
    )

    assert resp.decision == "needs_manual_review"
    assert resp.reason == "boundary_failure"
    assert resp.prompt is None


# ---------------------------------------------------------------------------
# Unit: blocked boundary
# ---------------------------------------------------------------------------


def test_blocked_boundary_asks_for_context() -> None:
    boundary = _boundary("blocked", "ask_user", "missing_context", "Missing username.")

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        boundary=boundary,
    )

    assert resp.decision == "ask_user_for_context"
    assert resp.reason == "boundary_blocked"
    assert "Missing username" in resp.user_response
    assert resp.next_status_suggestion == "ask_user_for_context"
    assert resp.prompt is None


# ---------------------------------------------------------------------------
# Unit: uncertain result
# ---------------------------------------------------------------------------


def test_uncertain_boundary_asks_review() -> None:
    boundary = _boundary("uncertain", "needs_review", "insufficient_postcondition_evidence")

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        boundary=boundary,
    )

    assert resp.decision == "needs_manual_review"
    assert resp.reason == "boundary_uncertain"
    assert resp.next_status_suggestion == "needs_manual_review"
    assert "unclear" in resp.user_response or "review" in resp.user_response


# ---------------------------------------------------------------------------
# Unit: needs_review
# ---------------------------------------------------------------------------


def test_needs_review_boundary() -> None:
    boundary = _boundary("needs_review", "needs_review", "explicit_needs_review")

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        boundary=boundary,
    )

    assert resp.decision == "needs_manual_review"
    assert resp.reason == "boundary_needs_review"
    assert resp.next_status_suggestion == "needs_manual_review"


# ---------------------------------------------------------------------------
# Unit: abort accepted_stop
# ---------------------------------------------------------------------------


def test_abort_accepted_stop_acknowledges_no_new_actions() -> None:
    abort = _abort("accepted_stop", "Stop accepted.", no_new_actions_after=True)

    resp = build_recovery_conversation_response(
        session_status="abort_requested",
        abort=abort,
    )

    assert resp.decision == "acknowledge_abort"
    assert resp.reason == "abort_present"
    assert "Stop accepted" in resp.user_response
    assert "No new browser actions will be started" in resp.user_response
    # Abort is stop acknowledgement, not abandon intent
    assert resp.next_status_suggestion is None


# ---------------------------------------------------------------------------
# Unit: abort cannot_interrupt_inflight_action
# ---------------------------------------------------------------------------


def test_abort_inflight_caveat_explains_uncertainty() -> None:
    abort = _abort(
        "cannot_interrupt_inflight_action",
        "Cannot interrupt in-flight action.",
        no_new_actions_after=True,
        inflight_caveat=True,
    )

    resp = build_recovery_conversation_response(
        session_status="abort_requested",
        abort=abort,
    )

    assert resp.decision == "acknowledge_abort"
    assert resp.reason == "abort_present"
    assert "Cannot interrupt in-flight action" in resp.user_response
    assert "side effects cannot be guaranteed reversible" in resp.user_response
    # Abort is stop acknowledgement, not abandon intent
    assert resp.next_status_suggestion is None


# ---------------------------------------------------------------------------
# Unit: proposal with consider_retry_later
# ---------------------------------------------------------------------------


def test_proposal_with_consider_retry_later_shows_options() -> None:
    proposal = _proposal(
        _option("consider_retry_later", "Retry Later", "Retry after review"),
    )

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        proposal=proposal,
    )

    assert resp.decision == "show_recovery_options"
    assert resp.reason == "proposal_present"
    assert resp.prompt is not None
    assert any(opt.kind == "consider_retry_later" for opt in resp.prompt.options)
    # Does not start retry
    assert resp.event_payload_suggestion is not None
    assert resp.event_payload_suggestion.execution_boundary == "not_executed"


# ---------------------------------------------------------------------------
# Unit: retry policy retry_allowed_requires_confirmation
# ---------------------------------------------------------------------------


def test_retry_allowed_requires_confirmation() -> None:
    retry = _retry("retry_allowed_requires_confirmation", "retry_candidate_with_clear_evidence")

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        retry_policy=retry,
    )

    assert resp.decision == "show_retry_policy_result"
    assert resp.reason == "retry_policy_present"
    assert "requires your confirmation" in resp.user_response
    assert resp.next_status_suggestion == "awaiting_confirmation"
    # No retry execution
    assert resp.event_payload_suggestion is not None
    assert resp.event_payload_suggestion.non_executable is True


# ---------------------------------------------------------------------------
# Unit: retry policy retry_denied
# ---------------------------------------------------------------------------


def test_retry_denied_explains_denial() -> None:
    retry = _retry("retry_denied", "non_idempotent_action")

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        retry_policy=retry,
    )

    assert resp.decision == "show_retry_policy_result"
    assert resp.reason == "retry_policy_present"
    assert "not allowed" in resp.user_response
    assert resp.next_status_suggestion == "needs_manual_review"


# ---------------------------------------------------------------------------
# Unit: retry policy retry_needs_more_context
# ---------------------------------------------------------------------------


def test_retry_needs_more_context() -> None:
    retry = _retry("retry_needs_more_context", "missing_execution_evidence")

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        retry_policy=retry,
    )

    assert resp.decision == "ask_user_for_context"
    assert resp.reason == "retry_policy_present"
    assert "More context is needed" in resp.user_response
    assert resp.next_status_suggestion == "ask_user_for_context"


# ---------------------------------------------------------------------------
# Unit: retry policy retry_needs_manual_review
# ---------------------------------------------------------------------------


def test_retry_needs_manual_review() -> None:
    retry = _retry("retry_needs_manual_review", "side_effects_unknown")

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        retry_policy=retry,
    )

    assert resp.decision == "needs_manual_review"
    assert resp.reason == "retry_policy_present"
    assert resp.next_status_suggestion == "needs_manual_review"


# ---------------------------------------------------------------------------
# Unit: abandon_task option
# ---------------------------------------------------------------------------


def test_abandon_task_option_records_conversation_intent_only() -> None:
    proposal = _proposal(
        _option("abandon_task", "Abandon", "Stop and record abandonment"),
    )

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        proposal=proposal,
    )

    assert resp.decision == "show_recovery_options"
    assert resp.prompt is not None
    abandon_opt = next(
        (o for o in resp.prompt.options if o.kind == "abandon_task"),
        None,
    )
    assert abandon_opt is not None
    assert abandon_opt.non_executable is True
    assert abandon_opt.execution_boundary == "not_executed"


# ---------------------------------------------------------------------------
# Unit: recommended option display
# ---------------------------------------------------------------------------


def test_recommended_options_shown_but_not_selected() -> None:
    proposal = _proposal(
        _option("ask_user_for_context", "Ask", "Ask user"),
        _option("abandon_task", "Abandon", "Give up"),
        recommended=["ask_user_for_context"],
    )

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        proposal=proposal,
    )

    assert resp.decision == "show_recovery_options"
    assert resp.prompt is not None
    assert "Recommended options: ask_user_for_context" in resp.user_response
    # No option is auto-selected
    assert resp.chosen_option_kind is None


# ---------------------------------------------------------------------------
# Unit: selected user option uses conversation-only naming
# ---------------------------------------------------------------------------


def test_selected_user_option_uses_conversation_only_marker() -> None:
    """RecoveryConversationResponse supports chosen_option_kind for conversation choice."""
    resp = RecoveryConversationResponse(
        user_response="User chose retry.",
        decision="show_recovery_options",
        reason="proposal_present",
        chosen_option_kind="consider_retry_later",
    )

    assert resp.chosen_option_kind == "consider_retry_later"
    assert resp.chosen_option_kind is not None

def test_service_records_chosen_option_kind_in_event_payload() -> None:
    """Service entrypoint records user choice as conversation marker, not execution."""
    proposal = _proposal(
        _option("consider_retry_later", "Retry", "Retry later"),
    )

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        proposal=proposal,
        chosen_option_kind="consider_retry_later",
    )

    assert resp.chosen_option_kind == "consider_retry_later"
    assert resp.event_payload_suggestion is not None
    marker = resp.event_payload_suggestion.conversation_choice_marker
    assert marker is not None
    assert marker["chosen_option_kind"] == "consider_retry_later"
    assert marker["non_executable"] is True
    assert marker["execution_boundary"] == "not_executed"
    # No execution command surfaced
    assert "retry_command" not in resp.model_dump()

def test_invalid_chosen_option_kind_returns_manual_review() -> None:
    """Chosen option kind must belong to displayed options; otherwise manual review."""
    proposal = _proposal(
        _option("abandon_task", "Abandon", "Give up"),
    )

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        proposal=proposal,
        chosen_option_kind="consider_retry_later",  # not in shown options
    )

    assert resp.decision == "needs_manual_review"
    assert resp.reason == "conflicting_recovery_source"
    assert resp.chosen_option_kind is None
    assert "not among the displayed recovery options" in resp.user_response


# ---------------------------------------------------------------------------
# Unit: choice naming boundary — forbidden field names
# ---------------------------------------------------------------------------


def test_response_does_not_expose_execution_field_names() -> None:
    """RecoveryConversationResponse must not contain field names that imply execution."""
    forbidden = {"selected_action", "execute_choice", "run_choice", "retry_choice"}
    fields = set(RecoveryConversationResponse.model_fields.keys())
    assert not (forbidden & fields), f"Forbidden fields found: {forbidden & fields}"


def test_choice_option_does_not_expose_execution_field_names() -> None:
    """RecoveryChoiceOption must not contain field names that imply execution."""
    forbidden = {"selected_action", "execute_choice", "run_choice", "retry_choice"}
    fields = set(RecoveryChoiceOption.model_fields.keys())
    assert not (forbidden & fields), f"Forbidden fields found: {forbidden & fields}"


# ---------------------------------------------------------------------------
# Unit: choice execution boundary marker
# ---------------------------------------------------------------------------


def test_choice_option_preserves_non_executable_marker() -> None:
    opt = RecoveryChoiceOption(
        kind="abandon_task",
        label="Abandon",
        description="Give up",
    )
    assert opt.non_executable is True
    assert opt.execution_boundary == "not_executed"


def test_event_payload_preserves_non_executable_marker() -> None:
    payload = RecoveryConversationEventPayload(
        source_kind="test",
        decision="show_recovery_options",
        reason="proposal_present",
    )
    assert payload.non_executable is True
    assert payload.execution_boundary == "not_executed"


def test_event_payload_rejects_non_executable_false() -> None:
    """Schema hard constraint: non_executable must be True."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RecoveryConversationEventPayload(
            non_executable=False,  # type: ignore[call-arg]
        )


def test_event_payload_rejects_invalid_execution_boundary() -> None:
    """Schema hard constraint: execution_boundary must be 'not_executed'."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RecoveryConversationEventPayload(
            execution_boundary="retry_started",  # type: ignore[call-arg]
        )

def test_choice_option_rejects_invalid_execution_boundary() -> None:
    """Schema hard constraint: RecoveryChoiceOption.execution_boundary must be 'not_executed'."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RecoveryChoiceOption(
            kind="abandon_task",
            label="Abandon",
            description="Give up",
            execution_boundary="retry_started",  # type: ignore[call-arg]
        )

# ---------------------------------------------------------------------------
# Unit: input immutability
# ---------------------------------------------------------------------------


def test_inputs_are_not_mutated() -> None:
    boundary = _boundary("failure", "retry_possible_requires_confirmation", "replay_failed")
    proposal = _proposal(
        _option("abandon_task", "Abandon", "Give up"),
    )
    retry = _retry("retry_denied", "non_idempotent_action")
    abort = _abort("accepted_stop", "Stopped.")

    boundary_before = copy.deepcopy(boundary.model_dump())
    proposal_before = copy.deepcopy(proposal.model_dump())
    retry_before = copy.deepcopy(retry.model_dump())
    abort_before = copy.deepcopy(abort.model_dump())

    build_recovery_conversation_response(
        session_status="execution_failed",
        boundary=boundary,
        proposal=proposal,
        retry_policy=retry,
        abort=abort,
    )

    assert boundary.model_dump() == boundary_before
    assert proposal.model_dump() == proposal_before
    assert retry.model_dump() == retry_before
    assert abort.model_dump() == abort_before


# ---------------------------------------------------------------------------
# Unit: forbidden dependency scan
# ---------------------------------------------------------------------------


def test_service_module_has_no_forbidden_imports() -> None:
    """The conversation flow service must not import browser, network, LLM,
    retry execution, replan execution, or LearnedPath write-back modules.
    """
    import app.services.recovery.conversation_flow as cf_module

    source = cf_module.__loader__.get_source(cf_module.__name__) or ""
    forbidden_patterns = [
        "playwright",
        "httpx",
        "requests",
        "openai",
        "llm",
        "autonomous_explorer",
        "execution_runtime",
        "learned_path",
        "LearnedPath",
        "run_autonomous",
    ]
    lines = source.splitlines()
    violations = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped.startswith(("import ", "from ")):
            continue
        if stripped.startswith("#"):
            continue
        lower = stripped.lower()
        for pat in forbidden_patterns:
            if pat in lower:
                violations.append((i, stripped))
                break

    assert not violations, f"Forbidden imports found: {violations[:10]}"


# ---------------------------------------------------------------------------
# Unit: fallback / missing recovery source
# ---------------------------------------------------------------------------


def test_missing_recovery_source_falls_back_to_manual_review() -> None:
    resp = build_recovery_conversation_response(
        session_status="execution_failed",
    )

    assert resp.decision == "needs_manual_review"
    assert resp.reason == "missing_recovery_source"
    assert resp.prompt is None
    assert resp.next_status_suggestion == "needs_manual_review"


# ---------------------------------------------------------------------------
# Unit: abort + proposal combination
# ---------------------------------------------------------------------------


def test_abort_with_proposal_shows_options_without_execution() -> None:
    abort = _abort("accepted_stop", "Stopped.")
    proposal = _proposal(
        _option("abandon_task", "Abandon", "Give up"),
        _option("handoff_to_takeover_later", "Takeover", "Hand off"),
    )

    resp = build_recovery_conversation_response(
        session_status="abort_requested",
        abort=abort,
        proposal=proposal,
    )

    assert resp.decision == "acknowledge_abort"
    assert resp.prompt is not None
    assert len(resp.prompt.options) == 2
    # Abort is stop acknowledgement, not abandon intent
    assert resp.next_status_suggestion is None


# ---------------------------------------------------------------------------
# Unit: retry policy + proposal combination
# ---------------------------------------------------------------------------


def test_retry_policy_with_proposal_shows_options() -> None:
    retry = _retry("retry_allowed_requires_confirmation", "retry_candidate_with_clear_evidence")
    proposal = _proposal(
        _option("consider_retry_later", "Retry", "Retry option"),
    )

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        retry_policy=retry,
        proposal=proposal,
    )

    assert resp.decision == "show_retry_policy_result"
    assert resp.prompt is not None
    assert any(opt.kind == "consider_retry_later" for opt in resp.prompt.options)
    assert resp.event_payload_suggestion is not None
    assert (
        resp.event_payload_suggestion.retry_policy_outcome
        == "retry_allowed_requires_confirmation"
    )


# ---------------------------------------------------------------------------
# Unit: derivation priority
# ---------------------------------------------------------------------------


def test_abort_takes_priority_over_retry_and_boundary() -> None:
    abort = _abort("accepted_stop", "Stopped.")
    retry = _retry("retry_allowed_requires_confirmation", "retry_candidate_with_clear_evidence")
    boundary = _boundary("failure", "retry_possible_requires_confirmation", "replay_failed")

    resp = build_recovery_conversation_response(
        session_status="abort_requested",
        abort=abort,
        retry_policy=retry,
        boundary=boundary,
    )

    assert resp.decision == "acknowledge_abort"


def test_retry_policy_takes_priority_over_boundary_and_proposal() -> None:
    retry = _retry("retry_denied", "non_idempotent_action")
    boundary = _boundary("failure", "retry_possible_requires_confirmation", "replay_failed")
    proposal = _proposal(_option("abandon_task", "Abandon", "Give up"))

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        retry_policy=retry,
        boundary=boundary,
        proposal=proposal,
    )

    assert resp.decision == "show_retry_policy_result"


def test_proposal_takes_priority_over_boundary() -> None:
    boundary = _boundary("failure", "retry_possible_requires_confirmation", "replay_failed")
    proposal = _proposal(_option("abandon_task", "Abandon", "Give up"))

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        boundary=boundary,
        proposal=proposal,
    )

    assert resp.decision == "show_recovery_options"


# ---------------------------------------------------------------------------
# Unit: success_no_recovery_needed boundary
# ---------------------------------------------------------------------------


def test_success_boundary_returns_ready() -> None:
    boundary = _boundary("success_no_recovery_needed", "no_recovery_needed", "task_succeeded")

    resp = build_recovery_conversation_response(
        session_status="completed",
        boundary=boundary,
    )

    assert resp.decision == "recovery_response_ready"
    assert resp.reason == "boundary_no_recovery_needed"
    assert resp.next_status_suggestion is None


# ---------------------------------------------------------------------------
# Unit: event payload structure
# ---------------------------------------------------------------------------


def test_event_payload_contains_source_kind_and_decision() -> None:
    retry = _retry("retry_denied", "non_idempotent_action")

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        retry_policy=retry,
    )

    payload = resp.event_payload_suggestion
    assert payload is not None
    assert payload.source_kind == "retry_policy"
    assert payload.decision == "show_retry_policy_result"
    assert payload.reason == "retry_policy_present"
    assert payload.retry_policy_outcome == "retry_denied"
    assert payload.retry_policy_reason == "non_idempotent_action"


def test_event_payload_shown_options_are_dicts() -> None:
    proposal = _proposal(
        _option("abandon_task", "Abandon", "Give up"),
    )

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        proposal=proposal,
    )

    payload = resp.event_payload_suggestion
    assert payload is not None
    assert len(payload.shown_options) == 1
    assert payload.shown_options[0]["kind"] == "abandon_task"
    assert payload.shown_options[0]["non_executable"] is True
    assert payload.shown_options[0]["execution_boundary"] == "not_executed"


# ---------------------------------------------------------------------------
# Unit: no execution fields in response
# ---------------------------------------------------------------------------


def test_response_contains_no_execution_commands() -> None:
    proposal = _proposal(
        _option("consider_retry_later", "Retry", "Retry later"),
    )

    resp = build_recovery_conversation_response(
        session_status="execution_failed",
        proposal=proposal,
    )

    resp_dict = resp.model_dump()
    # No retry command, replan command, browser action, takeover command, teaching command
    assert "retry_command" not in resp_dict
    assert "replan_command" not in resp_dict
    assert "browser_action" not in resp_dict
    assert "takeover_command" not in resp_dict
    assert "teaching_command" not in resp_dict
    assert "learned_path_writeback" not in resp_dict
