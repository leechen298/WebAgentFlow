"""M12.5 recovery conversation flow service.

Deterministic, side-effect-free wrapper that converts M12.1-M12.4 recovery
outputs into user-facing conversation responses, event payload suggestions,
and next-state suggestions.

Core principle:
    Recovery conversation flow is not recovery execution.
    Conversation may present, explain, ask, route, and record choices.
    Conversation must not execute retry, replan, browser continuation, takeover,
    teaching mode, or LearnedPath write-back.
"""

from __future__ import annotations

from typing import Any

from app.schemas.recovery import (
    AbortAcknowledgement,
    EvidenceReference,
    RecoveryBoundary,
    RecoveryChoiceOption,
    RecoveryChoicePrompt,
    RecoveryConversationDecision,
    RecoveryConversationEventPayload,
    RecoveryConversationReason,
    RecoveryConversationResponse,
    RecoveryConversationState,
    RecoveryProposal,
    RecoveryProposalOption,
    RetryPolicyDecision,
)


def build_recovery_conversation_response(
    *,
    session_status: str,
    user_input: str | None = None,
    command_kind: str | None = None,
    boundary: RecoveryBoundary | None = None,
    abort: AbortAcknowledgement | None = None,
    proposal: RecoveryProposal | None = None,
    retry_policy: RetryPolicyDecision | None = None,
    chosen_option_kind: str | None = None,
) -> RecoveryConversationResponse:
    """Build a user-facing recovery conversation response from recovery outputs.

    This function is deterministic and side-effect free. It does not write to
    the database, open a browser, make network calls, or invoke an LLM. It
    does not execute retry, replan, takeover, teaching, or LearnedPath
    write-back.
    """
    # Validate chosen_option_kind against displayed options.
    shown_kinds = {opt.kind for opt in (proposal.options if proposal else [])}
    if chosen_option_kind is not None and chosen_option_kind not in shown_kinds:
        decision = _build_fallback_decision(
            reason="conflicting_recovery_source",
            message=(
                f"Selected option '{chosen_option_kind}' was not among the "
                "displayed recovery options. Please review."
            ),
            session_status=session_status,
        )
        return RecoveryConversationResponse(
            user_response=decision.user_response,
            decision=decision.state,
            reason=decision.reason,
            prompt=None,
            event_payload_suggestion=decision.event_payload,
            next_status_suggestion=decision.next_status_suggestion,
            evidence_refs=(
                decision.event_payload.evidence_refs
                if decision.event_payload is not None
                else []
            ),
            source_boundary=boundary,
            source_abort=abort,
            source_proposal=proposal,
            source_retry_policy=retry_policy,
            chosen_option_kind=None,
        )

    decision = _derive_decision(
        session_status=session_status,
        user_input=user_input,
        command_kind=command_kind,
        boundary=boundary,
        abort=abort,
        proposal=proposal,
        retry_policy=retry_policy,
        chosen_option_kind=chosen_option_kind,
    )

    event_payload = decision.event_payload
    if chosen_option_kind is not None and event_payload is not None:
        event_payload = event_payload.model_copy(update={
            "conversation_choice_marker": {
                "chosen_option_kind": chosen_option_kind,
                "non_executable": True,
                "execution_boundary": "not_executed",
            }
        })

    return RecoveryConversationResponse(
        user_response=decision.user_response,
        decision=decision.state,
        reason=decision.reason,
        prompt=decision.prompt,
        event_payload_suggestion=event_payload,
        next_status_suggestion=decision.next_status_suggestion,
        evidence_refs=(
            event_payload.evidence_refs
            if event_payload is not None
            else []
        ),
        source_boundary=boundary,
        source_abort=abort,
        source_proposal=proposal,
        source_retry_policy=retry_policy,
        chosen_option_kind=chosen_option_kind,
    )


def _derive_decision(
    *,
    session_status: str,
    user_input: str | None,
    command_kind: str | None,
    boundary: RecoveryBoundary | None,
    abort: AbortAcknowledgement | None,
    proposal: RecoveryProposal | None,
    retry_policy: RetryPolicyDecision | None,
    chosen_option_kind: str | None,
) -> RecoveryConversationDecision:
    """Derive the recovery conversation decision from inputs.

    Derivation order (from technical-design.md):
    1. Abort acknowledgement present -> acknowledge_abort.
    2. Retry policy decision present -> show_retry_policy_result.
    3. Recovery proposal present -> show_recovery_options.
    4. Recovery boundary blocked / ask_user -> ask_user_for_context.
    5. Recovery boundary uncertain / needs_review -> needs_manual_review.
    6. Recovery boundary failure -> explain failure and show options if present.
    7. Unknown or conflicting source -> conservative needs_manual_review.
    """
    # 1. Abort acknowledgement present
    if abort is not None:
        return _build_abort_decision(abort, proposal)

    # 2. Retry policy decision present
    if retry_policy is not None:
        return _build_retry_policy_decision(retry_policy, proposal)

    # 3. Recovery proposal present
    if proposal is not None:
        decision = _build_proposal_decision(proposal)
        if boundary is not None:
            # Merge boundary message and evidence into proposal decision.
            # Boundary provides root-cause context; proposal provides options.
            boundary_note = boundary.message or "The task did not complete successfully."
            decision = decision.model_copy(update={
                "user_response": f"{boundary_note} {decision.user_response}",
                "reason": "boundary_failure",
            })
            if decision.event_payload is not None:
                merged_evidence = list(boundary.evidence) + decision.event_payload.evidence_refs
                decision.event_payload = decision.event_payload.model_copy(update={
                    "evidence_refs": merged_evidence,
                    "reason": "boundary_failure",
                })
        return decision

    # 4-6. Recovery boundary present
    if boundary is not None:
        return _build_boundary_decision(boundary, proposal)

    # 7. Unknown or conflicting source
    return _build_fallback_decision(
        reason="missing_recovery_source",
        message=(
            "No recovery information was provided. "
            "Please review the situation or provide more context."
        ),
        session_status=session_status,
    )


def _build_abort_decision(
    abort: AbortAcknowledgement,
    proposal: RecoveryProposal | None,
) -> RecoveryConversationDecision:
    """Build a decision for abort acknowledgement."""
    inflight_note = (
        " A browser action may already be in flight; side effects cannot be guaranteed reversible."
        if abort.inflight_caveat
        else ""
    )
    stop_note = (
        " No new browser actions will be started."
        if abort.no_new_actions_after
        else ""
    )

    user_response = f"{abort.message}{stop_note}{inflight_note}"

    evidence_refs: list[EvidenceReference] = []
    if abort.evidence is not None:
        evidence_refs.append(
            EvidenceReference(
                source="abort_handler",
                key="stop_decision",
                value=abort.decision,
                description="Stop handling decision from abort handler",
            )
        )

    prompt = None
    if proposal is not None and proposal.options:
        prompt = _build_choice_prompt_from_proposal(proposal)

    event_payload = RecoveryConversationEventPayload(
        source_kind="abort_acknowledgement",
        decision="acknowledge_abort",
        reason="abort_present",
        shown_options=_options_to_dicts(proposal.options if proposal else []),
        evidence_refs=evidence_refs,
        user_facing_explanation=user_response,
        non_executable=True,
        execution_boundary="not_executed",
    )

    # Abort acknowledgement is stop boundary, not abandon intent.
    # Only user explicitly choosing abandon_task should map to abandon.
    next_status = None

    return RecoveryConversationDecision(
        state="acknowledge_abort",
        reason="abort_present",
        user_response=user_response,
        prompt=prompt,
        event_payload=event_payload,
        next_status_suggestion=next_status,
    )


def _build_retry_policy_decision(
    retry_policy: RetryPolicyDecision,
    proposal: RecoveryProposal | None,
) -> RecoveryConversationDecision:
    """Build a decision for retry policy result display."""
    if retry_policy.outcome == "retry_allowed_requires_confirmation":
        user_response = (
            f"Retry is possible, but requires your confirmation. {retry_policy.message or ''} "
            "Please review the evidence and confirm if you want to proceed."
        )
        state: RecoveryConversationState = "show_retry_policy_result"
        reason: RecoveryConversationReason = "retry_policy_present"
        next_status = "awaiting_confirmation"
    elif retry_policy.outcome == "retry_denied":
        user_response = (
            f"Retry is not allowed for this situation. {retry_policy.message or ''} "
            "Please consider alternative options."
        )
        state = "show_retry_policy_result"
        reason = "retry_policy_present"
        next_status = "needs_manual_review"
    elif retry_policy.outcome == "retry_needs_more_context":
        user_response = (
            f"More context is needed to decide on retry. {retry_policy.message or ''} "
            "Please provide additional information."
        )
        state = "ask_user_for_context"
        reason = "retry_policy_present"
        next_status = "ask_user_for_context"
    elif retry_policy.outcome == "retry_needs_manual_review":
        user_response = (
            "This situation needs manual review before retry can be considered. "
            f"{retry_policy.message or ''}"
        )
        state = "needs_manual_review"
        reason = "retry_policy_present"
        next_status = "needs_manual_review"
    else:  # no_retry_needed
        user_response = (
            f"No retry is needed. {retry_policy.message or ''}"
        )
        state = "show_retry_policy_result"
        reason = "retry_policy_present"
        next_status = None

    evidence_refs = [
        EvidenceReference(
            source="retry_policy",
            key="outcome",
            value=retry_policy.outcome,
            description=retry_policy.message,
        )
    ]
    for ev in retry_policy.evidence:
        evidence_refs.append(
            EvidenceReference(
                source=ev.source,
                key=ev.key,
                value=ev.value,
                description=ev.description,
            )
        )

    prompt = None
    if proposal is not None and proposal.options:
        prompt = _build_choice_prompt_from_proposal(proposal)

    event_payload = RecoveryConversationEventPayload(
        source_kind="retry_policy",
        decision=state,
        reason=reason,
        shown_options=_options_to_dicts(proposal.options if proposal else []),
        evidence_refs=evidence_refs,
        retry_policy_outcome=retry_policy.outcome,
        retry_policy_reason=retry_policy.reason,
        user_facing_explanation=user_response,
        non_executable=True,
        execution_boundary="not_executed",
    )

    return RecoveryConversationDecision(
        state=state,
        reason=reason,
        user_response=user_response.strip(),
        prompt=prompt,
        event_payload=event_payload,
        next_status_suggestion=next_status,
    )


def _build_proposal_decision(
    proposal: RecoveryProposal,
) -> RecoveryConversationDecision:
    """Build a decision for recovery proposal display."""
    prompt = _build_choice_prompt_from_proposal(proposal)

    recommended_kinds = proposal.recommended_option_kinds
    recommended_note = (
        f" Recommended options: {', '.join(recommended_kinds)}."
        if recommended_kinds
        else ""
    )

    user_response = (
        f"The following recovery options are available.{recommended_note} "
        "Please review and select one. No action will be taken until you confirm."
    )

    evidence_refs = list(proposal.evidence_refs)
    for opt in proposal.options:
        evidence_refs.extend(opt.evidence_refs)

    event_payload = RecoveryConversationEventPayload(
        source_kind="recovery_proposal",
        decision="show_recovery_options",
        reason="proposal_present",
        shown_options=_options_to_dicts(proposal.options),
        evidence_refs=evidence_refs,
        user_facing_explanation=user_response,
        non_executable=True,
        execution_boundary="not_executed",
    )

    return RecoveryConversationDecision(
        state="show_recovery_options",
        reason="proposal_present",
        user_response=user_response,
        prompt=prompt,
        event_payload=event_payload,
        next_status_suggestion="show_recovery_options",
    )


def _build_boundary_decision(
    boundary: RecoveryBoundary,
    proposal: RecoveryProposal | None,
) -> RecoveryConversationDecision:
    """Build a decision from recovery boundary classification."""
    # Check classification first, then recommendation for reason precision
    if boundary.classification == "blocked":
        user_response = (
            f"{boundary.message or 'The task is blocked.'} "
            "Please provide the missing context or permission needed to continue."
        )
        state = "ask_user_for_context"
        reason: RecoveryConversationReason = "boundary_blocked"
        next_status = "ask_user_for_context"
    elif boundary.classification == "needs_review":
        user_response = (
            f"{boundary.message or 'This situation needs manual review.'} "
            "Please examine the details before deciding."
        )
        state = "needs_manual_review"
        reason = "boundary_needs_review"
        next_status = "needs_manual_review"
    elif boundary.classification == "failure":
        user_response = (
            f"{boundary.message or 'The task did not complete successfully.'} "
            "Please review the failure evidence and available options."
        )
        if proposal is not None and proposal.options:
            state = "show_recovery_options"
            reason = "boundary_failure"
            next_status = "show_recovery_options"
        else:
            state = "needs_manual_review"
            reason = "boundary_failure"
            next_status = "needs_manual_review"
    elif boundary.classification == "uncertain":
        user_response = (
            f"{boundary.message or 'The situation is unclear.'} "
            "Please review the available evidence and confirm how you "
            "would like to proceed."
        )
        state = "needs_manual_review"
        reason = "boundary_uncertain"
        next_status = "needs_manual_review"
    elif boundary.recommendation == "ask_user":
        user_response = (
            f"{boundary.message or 'More context is needed.'} "
            "Please provide the missing information so we can determine "
            "the next step."
        )
        state = "ask_user_for_context"
        reason = "boundary_ask_user"
        next_status = "ask_user_for_context"
    elif boundary.recommendation == "needs_review":
        user_response = (
            f"{boundary.message or 'This situation needs manual review.'} "
            "Please examine the details before deciding."
        )
        state = "needs_manual_review"
        reason = "boundary_needs_review"
        next_status = "needs_manual_review"
    else:
        # success_no_recovery_needed or no_recovery_needed
        user_response = boundary.message or "No recovery action is needed."
        state = "recovery_response_ready"
        reason = "boundary_no_recovery_needed"
        next_status = None

    evidence_refs = list(boundary.evidence)

    prompt = None
    if proposal is not None and proposal.options:
        prompt = _build_choice_prompt_from_proposal(proposal)
        if state == "recovery_response_ready":
            state = "show_recovery_options"
            reason = "proposal_present"
            next_status = "show_recovery_options"

    event_payload = RecoveryConversationEventPayload(
        source_kind="recovery_boundary",
        decision=state,
        reason=reason,
        shown_options=_options_to_dicts(proposal.options if proposal else []),
        evidence_refs=evidence_refs,
        user_facing_explanation=user_response,
        non_executable=True,
        execution_boundary="not_executed",
    )

    return RecoveryConversationDecision(
        state=state,
        reason=reason,
        user_response=user_response,
        prompt=prompt,
        event_payload=event_payload,
        next_status_suggestion=next_status,
    )


def _build_fallback_decision(
    reason: RecoveryConversationReason,
    message: str,
    session_status: str,
) -> RecoveryConversationDecision:
    """Build a conservative fallback decision."""
    event_payload = RecoveryConversationEventPayload(
        source_kind=None,
        decision="needs_manual_review",
        reason=reason,
        shown_options=[],
        evidence_refs=[
            EvidenceReference(
                source="recovery_conversation_flow",
                key="fallback_reason",
                value=reason,
                description="No structured recovery source was available.",
            )
        ],
        user_facing_explanation=message,
        non_executable=True,
        execution_boundary="not_executed",
    )

    return RecoveryConversationDecision(
        state="needs_manual_review",
        reason=reason,
        user_response=message,
        prompt=None,
        event_payload=event_payload,
        next_status_suggestion="needs_manual_review",
    )


def _build_choice_prompt_from_proposal(
    proposal: RecoveryProposal,
) -> RecoveryChoicePrompt:
    """Build a choice prompt from a recovery proposal."""
    options = [_map_proposal_option(opt) for opt in proposal.options]
    return RecoveryChoicePrompt(
        title="Recovery Options",
        explanation=(
            "Please choose one of the following options. "
            "No action will be executed automatically."
        ),
        options=options,
        evidence_refs=list(proposal.evidence_refs),
    )


def _map_proposal_option(opt: RecoveryProposalOption) -> RecoveryChoiceOption:
    """Map a RecoveryProposalOption to a RecoveryChoiceOption."""
    return RecoveryChoiceOption(
        kind=opt.kind,
        label=opt.title,
        description=opt.description,
        non_executable=True,
        execution_boundary="not_executed",
        evidence_refs=list(opt.evidence_refs),
        risk_hints=list(opt.risk_hints),
        confirmation_requirement=opt.confirmation_requirement,
        downstream_owner=opt.next_owner,
        rank=opt.rank,
    )


def _options_to_dicts(options: list[RecoveryProposalOption]) -> list[dict[str, Any]]:
    """Serialize proposal options to plain dicts for event payload."""
    result: list[dict[str, Any]] = []
    for opt in options:
        result.append(
            {
                "kind": opt.kind,
                "title": opt.title,
                "description": opt.description,
                "non_executable": opt.non_executable,
                "execution_boundary": "not_executed",
                "confirmation_requirement": opt.confirmation_requirement,
                "next_owner": opt.next_owner,
                "rank": opt.rank,
            }
        )
    return result
