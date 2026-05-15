"""Deterministic M12.3 recovery proposal generator.

The generator consumes 12.1 RecoveryBoundary or 12.2 AbortAcknowledgement
and produces a RecoveryProposal with display-only, non-executable options.
It performs no browser action, retry, replan, write-back, or LLM call.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.schemas.recovery import (
    AbortAcknowledgement,
    BoundaryRecommendation,
    EvidenceReference,
    ProposalConfirmationRequirement,
    ProposalOwner,
    ProposalRiskHint,
    RecoveryBoundary,
    RecoveryProposal,
    RecoveryProposalKind,
    RecoveryProposalOption,
    StopHandlingDecision,
)


class RecoveryProposalGenerator:
    """Generate recovery proposal from structured boundary or abort output.

    Deterministic, pure logic, no side effects.
    """

    def generate(
        self,
        source: RecoveryBoundary | AbortAcknowledgement | Mapping[str, Any],
    ) -> RecoveryProposal:
        """Return a RecoveryProposal from a 12.1 or 12.2 structured input."""
        if isinstance(source, RecoveryBoundary):
            return self._from_boundary(source)
        if isinstance(source, AbortAcknowledgement):
            return self._from_abort(source)
        return self._from_mapping(source)

    # ------------------------------------------------------------------
    # RecoveryBoundary -> RecoveryProposal
    # ------------------------------------------------------------------

    def _from_boundary(self, boundary: RecoveryBoundary) -> RecoveryProposal:
        options = self._boundary_options(boundary)
        recommended = [opt.kind for opt in options if opt.rank is not None]
        recommended.sort(key=lambda k: next(
            opt.rank for opt in options if opt.kind == k
        ))
        return RecoveryProposal(
            source="recovery_boundary",
            source_classification=boundary.classification,
            source_recommendation=boundary.recommendation,
            options=options,
            evidence_refs=list(boundary.evidence),
            recommended_option_kinds=recommended,
            source_boundary=boundary,
        )

    def _boundary_options(self, boundary: RecoveryBoundary) -> list[RecoveryProposalOption]:
        recommendation: BoundaryRecommendation = boundary.recommendation
        evidence = list(boundary.evidence)

        if recommendation == "ask_user":
            return [self._option(
                kind="ask_user_for_context",
                title="Provide additional context",
                description=(
                    "The task is blocked because required information is missing. "
                    "Please provide the missing context or permissions."
                ),
                evidence_refs=evidence,
                risk_hints=["requires_user_context"],
                confirmation_requirement="user_confirmation_required",
                next_owner="user",
                rank=0,
            )]

        if recommendation == "suggest_reteach":
            return [self._option(
                kind="suggest_reteach",
                title="Re-teach or update the learned path",
                description=(
                    "The learned path may be outdated or incomplete. "
                    "Consider re-teaching the task before any later recovery."
                ),
                evidence_refs=evidence,
                risk_hints=["policy_check_required"],
                confirmation_requirement="user_confirmation_required",
                next_owner="teaching_flow",
                rank=0,
            )]

        if recommendation == "retry_possible_requires_confirmation":
            return [
                self._option(
                    kind="review_evidence",
                    title="Review current evidence",
                    description=(
                        "Review the execution evidence and failure details "
                        "before deciding on any recovery action."
                    ),
                    evidence_refs=evidence,
                    risk_hints=["evidence_insufficient"],
                    confirmation_requirement="none",
                    next_owner="manual_review",
                    rank=0,
                ),
                self._option(
                    kind="consider_retry_later",
                    title="Consider retrying later",
                    description=(
                        "This task may be retryable, but the decision requires "
                        "confirmation through the retry policy (12.4). "
                        "No retry is started by this proposal."
                    ),
                    evidence_refs=evidence,
                    risk_hints=["side_effects_unknown", "policy_check_required"],
                    confirmation_requirement="downstream_policy_check_required",
                    next_owner="retry_policy",
                    rank=1,
                ),
            ]

        if recommendation == "stop":
            return [self._option(
                kind="abandon_task",
                title="Abandon this task",
                description=(
                    "The failure cannot be safely recovered. "
                    "Evidence is preserved for review."
                ),
                evidence_refs=evidence,
                risk_hints=["side_effects_unknown"],
                confirmation_requirement="user_confirmation_required",
                next_owner="user",
                rank=0,
            )]

        if recommendation == "needs_review":
            return [self._option(
                kind="review_evidence",
                title="Review current evidence",
                description=(
                    "The result is uncertain or requires manual review. "
                    "Please inspect the evidence before deciding next steps."
                ),
                evidence_refs=evidence,
                risk_hints=["evidence_insufficient"],
                confirmation_requirement="none",
                next_owner="manual_review",
                rank=0,
            )]

        if recommendation == "no_recovery_needed":
            return []

        # Fallback: conservative review
        return [self._option(
            kind="review_evidence",
            title="Review current evidence",
            description=(
                "The recovery boundary is unclear. "
                "Please review the evidence before proceeding."
            ),
            evidence_refs=evidence,
            risk_hints=["evidence_insufficient"],
            confirmation_requirement="none",
            next_owner="manual_review",
            rank=0,
        )]

    # ------------------------------------------------------------------
    # AbortAcknowledgement -> RecoveryProposal
    # ------------------------------------------------------------------

    def _from_abort(self, abort: AbortAcknowledgement) -> RecoveryProposal:
        options = self._abort_options(abort)
        recommended = [opt.kind for opt in options if opt.rank is not None]
        recommended.sort(key=lambda k: next(
            opt.rank for opt in options if opt.kind == k
        ))
        return RecoveryProposal(
            source="abort_acknowledgement",
            source_decision=abort.decision,
            options=options,
            evidence_refs=self._abort_evidence_refs(abort),
            recommended_option_kinds=recommended,
            source_abort=abort,
        )

    def _abort_options(self, abort: AbortAcknowledgement) -> list[RecoveryProposalOption]:
        decision: StopHandlingDecision = abort.decision
        evidence_refs = self._abort_evidence_refs(abort)

        if decision == "accepted_stop":
            return [
                self._option(
                    kind="abandon_task",
                    title="Keep task stopped",
                    description=(
                        "The task was stopped as requested. "
                        "No new browser actions will be started."
                    ),
                    evidence_refs=evidence_refs,
                    confirmation_requirement="user_confirmation_required",
                    next_owner="user",
                    rank=0,
                ),
                self._option(
                    kind="review_evidence",
                    title="Review execution evidence",
                    description=(
                        "Review what happened before the abort was received."
                    ),
                    evidence_refs=evidence_refs,
                    confirmation_requirement="none",
                    next_owner="manual_review",
                    rank=1,
                ),
            ]

        if decision == "cannot_interrupt_inflight_action":
            return [
                self._option(
                    kind="review_evidence",
                    title="Review execution evidence",
                    description=(
                        "A browser action may already be in flight. "
                        "External side effects may not be reversible. "
                        "Review the evidence before deciding next steps."
                    ),
                    evidence_refs=evidence_refs,
                    risk_hints=["inflight_action_risk", "side_effects_unknown"],
                    confirmation_requirement="none",
                    next_owner="manual_review",
                    rank=0,
                ),
            ]

        if decision == "already_finished":
            return [self._option(
                kind="review_evidence",
                title="Review completed task evidence",
                description=(
                    "The automation had already finished before the abort signal. "
                    "Review the results."
                ),
                evidence_refs=evidence_refs,
                confirmation_requirement="none",
                next_owner="manual_review",
                rank=0,
            )]

        if decision == "already_failed":
            return [self._option(
                kind="review_evidence",
                title="Review failure evidence",
                description=(
                    "The automation had already failed before the abort signal. "
                    "Review the failure details."
                ),
                evidence_refs=evidence_refs,
                risk_hints=["evidence_insufficient"],
                confirmation_requirement="none",
                next_owner="manual_review",
                rank=0,
            )]

        if decision == "not_running":
            return []

        # needs_manual_review or unknown
        risk: list[ProposalRiskHint] = ["evidence_insufficient"]
        if abort.inflight_caveat:
            risk.extend(["inflight_action_risk", "side_effects_unknown"])
        desc = (
            "The runtime state was unclear at abort time. "
            "Manual review is required before deciding next steps."
        )
        if abort.inflight_caveat:
            desc += (
                " A browser action may already be in flight; "
                "external side effects may not be reversible."
            )
        return [self._option(
            kind="review_evidence",
            title="Review current state",
            description=desc,
            evidence_refs=evidence_refs,
            risk_hints=risk,
            confirmation_requirement="none",
            next_owner="manual_review",
            rank=0,
        )]

    # ------------------------------------------------------------------
    # Mapping coercion (dict input)
    # ------------------------------------------------------------------

    def _from_mapping(self, data: Mapping[str, Any]) -> RecoveryProposal:
        if "classification" in data and "recommendation" in data:
            boundary = RecoveryBoundary.model_validate(dict(data))
            return self._from_boundary(boundary)
        if "decision" in data and "evidence" in data:
            abort = AbortAcknowledgement.model_validate(dict(data))
            return self._from_abort(abort)
        # Unknown shape: conservative review
        return RecoveryProposal(
            source="recovery_boundary",
            options=[self._option(
                kind="review_evidence",
                title="Review current evidence",
                description=(
                    "The input source is unrecognized. "
                    "Review the evidence before proceeding."
                ),
                risk_hints=["evidence_insufficient"],
                confirmation_requirement="none",
                next_owner="manual_review",
                rank=0,
            )],
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _option(
        self,
        *,
        kind: RecoveryProposalKind,
        title: str,
        description: str,
        evidence_refs: list[EvidenceReference] | None = None,
        risk_hints: list[ProposalRiskHint] | None = None,
        confirmation_requirement: ProposalConfirmationRequirement = "none",
        next_owner: ProposalOwner | None = None,
        rank: int | None = None,
    ) -> RecoveryProposalOption:
        return RecoveryProposalOption(
            kind=kind,
            title=title,
            description=description,
            evidence_refs=evidence_refs or [],
            risk_hints=risk_hints or [],
            confirmation_requirement=confirmation_requirement,
            next_owner=next_owner,
            rank=rank,
        )

    def _abort_evidence_refs(
        self, abort: AbortAcknowledgement,
    ) -> list[EvidenceReference]:
        refs: list[EvidenceReference] = []
        signal = abort.evidence.signal
        state = abort.evidence.state
        refs.append(EvidenceReference(
            source="abort_signal", key="source", value=signal.source,
        ))
        if signal.raw_text is not None:
            refs.append(EvidenceReference(
                source="abort_signal", key="raw_text",
                value=signal.raw_text,
            ))
        if state.session_status is not None:
            refs.append(EvidenceReference(
                source="abort_state", key="session_status",
                value=state.session_status,
            ))
        if state.has_inflight_action:
            refs.append(EvidenceReference(
                source="abort_state", key="has_inflight_action",
                value=True,
            ))
        if abort.no_new_actions_after:
            refs.append(EvidenceReference(
                source="abort_boundary", key="no_new_actions_after",
                value=True,
            ))
        if abort.inflight_caveat:
            refs.append(EvidenceReference(
                source="abort_boundary", key="inflight_caveat",
                value=True,
            ))
        return refs


def generate_recovery_proposal(
    source: RecoveryBoundary | AbortAcknowledgement | Mapping[str, Any],
) -> RecoveryProposal:
    """Module-level convenience wrapper for the proposal generator."""
    return RecoveryProposalGenerator().generate(source)
