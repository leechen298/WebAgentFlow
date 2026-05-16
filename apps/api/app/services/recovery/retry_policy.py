"""Deterministic M12.4 retry / re-run policy evaluator.

Consumes 12.1 RecoveryBoundary, 12.2 AbortAcknowledgement, or
12.3 RecoveryProposal and produces a RetryPolicyDecision.
Deterministic, pure logic, no side effects, no retry execution.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.schemas.recovery import (
    AbortAcknowledgement,
    BoundaryRecommendation,
    RecoveryBoundary,
    RecoveryProposal,
    RecoveryProposalKind,
    RecoveryProposalOption,
    RetryConfirmationRequirement,
    RetryPolicyDecision,
    RetryPolicyEvidence,
    RetryPolicyOutcome,
    RetryPolicyReason,
    RetryRiskLevel,
    StopHandlingDecision,
)


class RetryPolicyEvaluator:
    """Evaluate retry / re-run policy from structured recovery inputs.

    Deterministic, side-effect free, no DB/browser/network/LLM.
    """

    def evaluate(
        self,
        source: (
            RecoveryProposal
            | RecoveryBoundary
            | AbortAcknowledgement
            | Mapping[str, Any]
        ),
        *,
        selected_option_kind: RecoveryProposalKind | None = None,
        has_user_confirmation_marker: bool = False,
    ) -> RetryPolicyDecision:
        """Return a RetryPolicyDecision from structured input."""
        if isinstance(source, RecoveryProposal):
            return self._from_proposal(
                source,
                selected_option_kind=selected_option_kind,
                has_user_confirmation_marker=has_user_confirmation_marker,
            )
        if isinstance(source, RecoveryBoundary):
            return self._from_boundary(
                source,
                has_user_confirmation_marker=has_user_confirmation_marker,
            )
        if isinstance(source, AbortAcknowledgement):
            return self._from_abort(source)
        return self._from_mapping(
            source,
            selected_option_kind=selected_option_kind,
            has_user_confirmation_marker=has_user_confirmation_marker,
        )

    # ------------------------------------------------------------------
    # RecoveryProposal -> RetryPolicyDecision
    # ------------------------------------------------------------------

    def _from_proposal(
        self,
        proposal: RecoveryProposal,
        *,
        selected_option_kind: RecoveryProposalKind | None,
        has_user_confirmation_marker: bool,
    ) -> RetryPolicyDecision:
        options = proposal.options

        # Filter to selected option only, or use all
        if selected_option_kind is not None:
            target = [
                opt for opt in options if opt.kind == selected_option_kind
            ]
        else:
            target = list(options)
        target_kinds = {t.kind for t in target}

        # consider_retry_later
        if "consider_retry_later" in target_kinds:
            retry_opt = next(
                t for t in target if t.kind == "consider_retry_later"
            )
            risk_hints = set(retry_opt.risk_hints)
            evidence = self._proposal_evidence(proposal, target)
            if "side_effects_unknown" in risk_hints:
                return self._deny(
                    "side_effects_unknown",
                    "high",
                    evidence,
                    "Retry denied: side effects are unknown.",
                )
            if "inflight_action_risk" in risk_hints:
                return self._deny(
                    "side_effects_unknown",
                    "high",
                    evidence,
                    "Retry denied: inflight action risk.",
                )
            if not evidence:
                return self._needs_context(
                    "missing_execution_evidence",
                    evidence,
                    "Retry needs more context: insufficient evidence.",
                )
            if has_user_confirmation_marker:
                return self._decision(
                    "retry_allowed_requires_confirmation",
                    "retry_candidate_with_clear_evidence",
                    "low",
                    "user_confirmation_required",
                    evidence,
                    "Retry allowed but requires user confirmation through later flow.",
                )
            return self._decision(
                "retry_allowed_requires_confirmation",
                "retry_candidate_with_clear_evidence",
                "low",
                "user_confirmation_required",
                evidence,
                "Retry allowed but requires user confirmation. No retry is started.",
            )

        # abandon_task
        if "abandon_task" in target_kinds:
            return self._decision(
                "no_retry_needed",
                "task_abandoned",
                "none",
                "none",
                self._proposal_evidence(proposal, target),
                "Task was abandoned. No retry needed.",
            )

        # review_evidence
        if "review_evidence" in target_kinds:
            review_opt = next(
                t for t in target if t.kind == "review_evidence"
            )
            risk = (
                "high"
                if "inflight_action_risk" in review_opt.risk_hints
                else "medium"
            )
            return self._needs_review(
                "side_effects_unknown" if risk == "high"
                else "missing_execution_evidence",
                risk,
                self._proposal_evidence(proposal, target),
                "Manual review required before retry consideration.",
            )

        # ask_user_for_context
        if "ask_user_for_context" in target_kinds:
            return self._needs_context(
                "missing_user_confirmation",
                self._proposal_evidence(proposal, target),
                "More context or user input needed before retry.",
            )

        # suggest_reteach
        if "suggest_reteach" in target_kinds:
            return self._needs_review(
                "unsupported_replay_state",
                "medium",
                self._proposal_evidence(proposal, target),
                "Re-teach suggested. Manual review required.",
            )

        # Fallback
        return self._needs_review(
            "policy_source_unknown",
            "medium",
            self._proposal_evidence(proposal, target),
            "Proposal outcome unclear. Manual review required.",
        )

    # ------------------------------------------------------------------
    # RecoveryBoundary -> RetryPolicyDecision
    # ------------------------------------------------------------------

    def _from_boundary(
        self,
        boundary: RecoveryBoundary,
        *,
        has_user_confirmation_marker: bool,
    ) -> RetryPolicyDecision:
        recommendation: BoundaryRecommendation = boundary.recommendation
        evidence = self._boundary_evidence(boundary)

        if recommendation == "no_recovery_needed":
            return self._decision(
                "no_retry_needed",
                "already_succeeded",
                "none",
                "none",
                evidence,
                "No recovery needed. No retry required.",
            )

        if recommendation == "stop":
            return self._deny(
                "abort_boundary_active",
                "high",
                evidence,
                "Retry denied: recovery boundary recommends stop.",
            )

        if recommendation == "ask_user":
            return self._needs_context(
                "missing_user_confirmation",
                evidence,
                "Retry needs more context: user input required.",
            )

        if recommendation == "retry_possible_requires_confirmation":
            if has_user_confirmation_marker:
                return self._decision(
                    "retry_allowed_requires_confirmation",
                    "retry_candidate_with_clear_evidence",
                    "low",
                    "user_confirmation_required",
                    evidence,
                    "Retry allowed but requires user confirmation through later flow.",
                )
            return self._decision(
                "retry_allowed_requires_confirmation",
                "missing_user_confirmation",
                "low",
                "user_confirmation_required",
                evidence,
                "Retry allowed but requires user confirmation. No retry is started.",
            )

        if recommendation == "suggest_reteach":
            return self._needs_review(
                "unsupported_replay_state",
                "medium",
                evidence,
                "Re-teach suggested. Manual review required.",
            )

        if recommendation == "needs_review":
            return self._needs_review(
                "missing_execution_evidence",
                "medium",
                evidence,
                "Manual review required before retry consideration.",
            )

        # Fallback: conservative
        return self._needs_review(
            "policy_source_unknown",
            "medium",
            evidence,
            "Boundary recommendation unclear. Manual review required.",
        )

    # ------------------------------------------------------------------
    # AbortAcknowledgement -> RetryPolicyDecision
    # ------------------------------------------------------------------

    def _from_abort(
        self,
        abort: AbortAcknowledgement,
    ) -> RetryPolicyDecision:
        decision: StopHandlingDecision = abort.decision
        evidence = self._abort_evidence(abort)

        if decision == "accepted_stop":
            return self._deny(
                "abort_boundary_active",
                "high",
                evidence,
                "Retry denied: abort accepted. Stop boundary is active.",
            )

        if decision == "cannot_interrupt_inflight_action":
            return self._deny(
                "side_effects_unknown",
                "critical",
                evidence,
                "Retry denied: inflight action cannot be interrupted. "
                "Side effects may be unknown.",
            )

        if decision == "already_finished":
            return self._needs_review(
                "missing_execution_evidence",
                "medium",
                evidence,
                "Task already finished. Manual review required.",
            )

        if decision == "already_failed":
            return self._deny(
                "irreversible_action_possible",
                "high",
                evidence,
                "Retry denied: task already failed. "
                "Irreversible actions may have occurred.",
            )

        if decision == "not_running":
            return self._decision(
                "no_retry_needed",
                "not_running",
                "none",
                "none",
                evidence,
                "No automation running. No retry needed.",
            )

        # needs_manual_review or unknown
        risk: RetryRiskLevel = "medium"
        reason: RetryPolicyReason = "missing_execution_evidence"
        if abort.inflight_caveat:
            risk = "high"
            reason = "side_effects_unknown"
        return self._needs_review(
            reason,
            risk,
            evidence,
            "Abort state unclear. Manual review required.",
        )

    # ------------------------------------------------------------------
    # Mapping coercion (dict input)
    # ------------------------------------------------------------------

    def _from_mapping(
        self,
        data: Mapping[str, Any],
        *,
        selected_option_kind: RecoveryProposalKind | None,
        has_user_confirmation_marker: bool,
    ) -> RetryPolicyDecision:
        # Proposal-shaped
        if "source" in data and "options" in data:
            try:
                proposal = RecoveryProposal.model_validate(dict(data))
                return self._from_proposal(
                    proposal,
                    selected_option_kind=selected_option_kind,
                    has_user_confirmation_marker=has_user_confirmation_marker,
                )
            except Exception:
                pass

        # Boundary-shaped
        if "classification" in data and "recommendation" in data:
            try:
                boundary = RecoveryBoundary.model_validate(dict(data))
                return self._from_boundary(
                    boundary,
                    has_user_confirmation_marker=has_user_confirmation_marker,
                )
            except Exception:
                pass

        # Abort-shaped
        if "decision" in data and "evidence" in data:
            try:
                abort = AbortAcknowledgement.model_validate(dict(data))
                return self._from_abort(abort)
            except Exception:
                pass

        # Unknown shape
        return self._needs_review(
            "policy_source_unknown",
            "medium",
            [],
            "Input source unrecognized. Manual review required.",
        )

    # ------------------------------------------------------------------
    # Decision builders
    # ------------------------------------------------------------------

    def _decision(
        self,
        outcome: RetryPolicyOutcome,
        reason: RetryPolicyReason,
        risk_level: RetryRiskLevel,
        confirmation_requirement: RetryConfirmationRequirement,
        evidence: list[RetryPolicyEvidence],
        message: str,
    ) -> RetryPolicyDecision:
        return RetryPolicyDecision(
            outcome=outcome,
            reason=reason,
            risk_level=risk_level,
            confirmation_requirement=confirmation_requirement,
            evidence=evidence,
            message=message,
        )

    def _deny(
        self,
        reason: RetryPolicyReason,
        risk_level: RetryRiskLevel,
        evidence: list[RetryPolicyEvidence],
        message: str,
    ) -> RetryPolicyDecision:
        return RetryPolicyDecision(
            outcome="retry_denied",
            reason=reason,
            risk_level=risk_level,
            confirmation_requirement="none",
            evidence=evidence,
            message=message,
        )

    def _needs_context(
        self,
        reason: RetryPolicyReason,
        evidence: list[RetryPolicyEvidence],
        message: str,
    ) -> RetryPolicyDecision:
        return RetryPolicyDecision(
            outcome="retry_needs_more_context",
            reason=reason,
            risk_level="low",
            confirmation_requirement="user_confirmation_required",
            evidence=evidence,
            message=message,
        )

    def _needs_review(
        self,
        reason: RetryPolicyReason,
        risk_level: RetryRiskLevel,
        evidence: list[RetryPolicyEvidence],
        message: str,
    ) -> RetryPolicyDecision:
        return RetryPolicyDecision(
            outcome="retry_needs_manual_review",
            reason=reason,
            risk_level=risk_level,
            confirmation_requirement="user_confirmation_required",
            evidence=evidence,
            message=message,
        )

    # ------------------------------------------------------------------
    # Evidence helpers
    # ------------------------------------------------------------------

    def _proposal_evidence(
        self,
        proposal: RecoveryProposal,
        target_options: list[RecoveryProposalOption] | None = None,
    ) -> list[RetryPolicyEvidence]:
        seen: set[tuple[str, str]] = set()
        result: list[RetryPolicyEvidence] = []

        # Top-level proposal evidence
        for ref in proposal.evidence_refs:
            pair = (ref.source, ref.key)
            if pair not in seen:
                seen.add(pair)
                result.append(RetryPolicyEvidence(
                    source=ref.source,
                    key=ref.key,
                    value=ref.value,
                    description=ref.description,
                ))

        # Target option evidence (merged, deduplicated)
        for opt in target_options or []:
            for ref in opt.evidence_refs:
                pair = (ref.source, ref.key)
                if pair not in seen:
                    seen.add(pair)
                    result.append(RetryPolicyEvidence(
                        source=ref.source,
                        key=ref.key,
                        value=ref.value,
                        description=ref.description,
                    ))

        return result

    def _boundary_evidence(
        self,
        boundary: RecoveryBoundary,
    ) -> list[RetryPolicyEvidence]:
        return [
            RetryPolicyEvidence(
                source=ref.source,
                key=ref.key,
                value=ref.value,
                description=ref.description,
            )
            for ref in boundary.evidence
        ]

    def _abort_evidence(
        self,
        abort: AbortAcknowledgement,
    ) -> list[RetryPolicyEvidence]:
        evidence: list[RetryPolicyEvidence] = []
        signal = abort.evidence.signal
        state = abort.evidence.state

        evidence.append(RetryPolicyEvidence(
            source="abort_signal", key="source", value=signal.source,
        ))
        if signal.raw_text is not None:
            evidence.append(RetryPolicyEvidence(
                source="abort_signal", key="raw_text",
                value=signal.raw_text,
            ))
        if state.session_status is not None:
            evidence.append(RetryPolicyEvidence(
                source="abort_state", key="session_status",
                value=state.session_status,
            ))
        if state.has_inflight_action:
            evidence.append(RetryPolicyEvidence(
                source="abort_state", key="has_inflight_action",
                value=True,
            ))
        if abort.no_new_actions_after:
            evidence.append(RetryPolicyEvidence(
                source="abort_boundary", key="no_new_actions_after",
                value=True,
            ))
        if abort.inflight_caveat:
            evidence.append(RetryPolicyEvidence(
                source="abort_boundary", key="inflight_caveat",
                value=True,
            ))
        return evidence


def evaluate_retry_policy(
    source: (
        RecoveryProposal
        | RecoveryBoundary
        | AbortAcknowledgement
        | Mapping[str, Any]
    ),
    *,
    selected_option_kind: RecoveryProposalKind | None = None,
    has_user_confirmation_marker: bool = False,
) -> RetryPolicyDecision:
    """Module-level convenience wrapper for the retry policy evaluator."""
    return RetryPolicyEvaluator().evaluate(
        source,
        selected_option_kind=selected_option_kind,
        has_user_confirmation_marker=has_user_confirmation_marker,
    )
