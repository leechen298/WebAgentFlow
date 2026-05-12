"""Task Path Planner — deterministic candidate selection and route-plan generation.

This module implements the Task Path Planner MVP boundary defined in 11.1.3.
It consumes a user task intent and ranked LearnedPath candidates, then produces
a minimal, explainable route-plan proposal.

Boundary rules (enforced by implementation and imports):
- Does NOT read raw HTML.
- Does NOT call page analyzer.
- Does NOT call autonomous run.
- Does NOT perform hidden relearning.
- Does NOT select paths outside the passed candidate list.
- Does NOT execute replay.
- Does NOT fill forms.
- Does NOT perform recovery dialogue.
- Does NOT implement teaching mode.
- Does NOT call LLM providers.
"""

from __future__ import annotations

from app.schemas.task_planning import (
    AgentDPlannerOutput,
    ConfirmationRequirement,
    LearnedPathCandidate,
    RiskHint,
    RoutePlan,
    RouteStep,
    TaskIntent,
)


class TaskPathPlanner:
    """Deterministic-first planner that maps ranked candidates to a route plan."""

    def plan(
        self,
        task_intent: TaskIntent,
        candidates: list[LearnedPathCandidate],
    ) -> AgentDPlannerOutput:
        """Select the best candidate and build a minimal explainable route plan.

        Args:
            task_intent: Normalized user task intent.
            candidates: Ranked LearnedPath candidates from retrieval (11.1.2).

        Returns:
            AgentDPlannerOutput containing route plan, confirmation requirements,
            risk hints, and warnings.
        """
        # Defensive filter: ignore deprecated paths even if retrieval missed them.
        valid = [c for c in candidates if c.trust != "deprecated"]

        if not valid:
            return self._unable_to_plan(
                task_intent, "No valid LearnedPath candidates available for this task."
            )

        top = valid[0]
        ambiguous = self._is_ambiguous(valid)

        route_plan = self._build_route_plan(task_intent, top)
        output = self._assemble_output(task_intent, top, route_plan, ambiguous)
        return output

    # -----------------------------------------------------------------------
    # Candidate selection
    # -----------------------------------------------------------------------

    def _is_ambiguous(self, candidates: list[LearnedPathCandidate]) -> bool:
        """Detect whether the top candidates are too close to call.

        Ambiguity rule (MVP): if the top two candidates are both *confirmed*
        with strong match signals, the selection is ambiguous and should
        surface a confirmation requirement rather than silently executing.
        """
        if len(candidates) < 2:
            return False

        first, second = candidates[0], candidates[1]
        if first.trust != "confirmed" or second.trust != "confirmed":
            return False

        # Both confirmed — check whether the second also has strong signals.
        second_strong = self._has_strong_match(second)
        return second_strong

    def _has_strong_match(self, candidate: LearnedPathCandidate) -> bool:
        """Return True when the candidate has an exact-scenario or exact-page match."""
        for reason in candidate.match_reasons:
            lower = reason.lower()
            if "exact scenario match" in lower or "exact page match" in lower:
                return True
        return False

    # -----------------------------------------------------------------------
    # Route-plan construction
    # -----------------------------------------------------------------------

    def _build_route_plan(
        self, task_intent: TaskIntent, candidate: LearnedPathCandidate
    ) -> RoutePlan:
        """Map a single selected candidate into a minimal RoutePlan."""
        step = RouteStep(
            order=0,
            learned_path_id=candidate.learned_path_id,
            purpose=self._derive_purpose(task_intent, candidate),
            bound_slots={},
            expected_result=None,
            can_execute=True,
            warnings=list(candidate.warnings),
        )
        return RoutePlan(
            task_intent=task_intent,
            steps=[step],
            confirmation_required=False,
            risk_hints=[],
            postconditions=[],
            uncertainty=[],
        )

    def _derive_purpose(
        self, task_intent: TaskIntent, candidate: LearnedPathCandidate
    ) -> str:
        """Derive a human-readable purpose for the route step."""
        return (
            f"Execute learned path '{candidate.scenario}' "
            f"on page '{candidate.page_template}' to fulfill task: "
            f"{task_intent.raw_text}"
        )

    # -----------------------------------------------------------------------
    # Output assembly
    # -----------------------------------------------------------------------

    def _assemble_output(
        self,
        task_intent: TaskIntent,
        candidate: LearnedPathCandidate,
        route_plan: RoutePlan,
        ambiguous: bool,
    ) -> AgentDPlannerOutput:
        """Assemble planner output with warnings, risks, and confirmation reqs."""
        confirmation_requirements: list[ConfirmationRequirement] = []
        risk_hints: list[RiskHint] = []
        uncertainty: list[str] = []
        warnings: list[str] = []

        # Preserve candidate-level warnings.
        warnings.extend(candidate.warnings)

        # Trust-level handling.
        if candidate.trust == "provisional":
            confirmation_requirements.append(
                ConfirmationRequirement(
                    reason="provisional_trust",
                    message=(
                        f"The selected path '{candidate.scenario}' has provisional trust. "
                        "Please confirm before execution."
                    ),
                    severity="warning",
                )
            )
        elif candidate.trust == "flaky":
            risk_hints.append(
                RiskHint(
                    risk_type="flaky_path",
                    reason=(
                        f"Candidate '{candidate.scenario}' has flaky trust status. "
                        "Execution may fail or produce inconsistent results."
                    ),
                    severity="warning",
                )
            )
            confirmation_requirements.append(
                ConfirmationRequirement(
                    reason="flaky_trust",
                    message=(
                        f"The selected path '{candidate.scenario}' is marked flaky. "
                        "Please confirm before execution."
                    ),
                    severity="warning",
                )
            )

        # Ambiguity handling.
        if ambiguous:
            uncertainty.append(
                "Multiple confirmed candidates detected; top candidate was selected "
                "but strong alternatives exist."
            )
            confirmation_requirements.append(
                ConfirmationRequirement(
                    reason="ambiguous_selection",
                    message=(
                        "Multiple confirmed candidates match this task. "
                        "Please review the selected path before execution."
                    ),
                    severity="info",
                )
            )

        # Drift evidence propagation.
        if candidate.drift_evidence_summary:
            warnings.append(f"Drift evidence: {candidate.drift_evidence_summary}")
            risk_hints.append(
                RiskHint(
                    risk_type="drift",
                    reason=candidate.drift_evidence_summary,
                    severity="warning",
                )
            )

        # Negative evidence (preserved from candidate; may be empty in early versions).
        if candidate.negative_evidence_summary:
            warnings.append(f"Negative evidence: {candidate.negative_evidence_summary}")

        route_plan.confirmation_required = (
            len(confirmation_requirements) > 0 or len(route_plan.steps) == 0
        )
        route_plan.risk_hints = risk_hints
        route_plan.uncertainty = uncertainty

        return AgentDPlannerOutput(
            route_plan=route_plan,
            confirmation_requirements=confirmation_requirements,
            risk_hints=risk_hints,
            consent_requirements=[],
            uncertainty=uncertainty,
            warnings=warnings,
        )

    def _unable_to_plan(self, task_intent: TaskIntent, reason: str) -> AgentDPlannerOutput:
        """Return an explicit unable-to-plan result."""
        return AgentDPlannerOutput(
            route_plan=None,
            confirmation_requirements=[
                ConfirmationRequirement(
                    reason="unable_to_plan",
                    message=reason,
                    severity="blocking",
                )
            ],
            risk_hints=[],
            consent_requirements=[],
            uncertainty=[reason],
            warnings=[f"Unable to plan: {reason}"],
        )
