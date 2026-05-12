"""Planning preview service — orchestrates retrieval + planner for conversation dispatch.

This module implements the 11.1.4 conversation-runtime integration:
user free-text input -> TaskIntent -> retrieval -> planner -> planning preview.

Boundary rules (enforced by implementation and imports):
- Does NOT execute replay.
- Does NOT call autonomous run.
- Does NOT read raw HTML.
- Does NOT perform hidden relearning.
- Does NOT connect an LLM provider.
- Does NOT implement real slot binding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas.conversation import ConversationEventType
from app.schemas.task_planning import AgentDPlannerOutput, TaskIntent
from app.services.task_planning.planner import TaskPathPlanner
from app.services.task_planning.retrieval import LearnedPathRetrievalService


@dataclass
class PlanningPreviewResult:
    """Result of a planning preview, consumed by the conversation orchestrator."""

    user_response: str
    event_type: str
    event_payload: dict[str, Any]
    confirmation_required: bool = False
    selected_path_id: str | None = None


class PlanningPreviewService:
    """Coordinates retrieval and planning to produce a preview for the user."""

    def __init__(
        self,
        retrieval_service: LearnedPathRetrievalService,
        planner: TaskPathPlanner,
    ) -> None:
        self._retrieval = retrieval_service
        self._planner = planner

    def preview(self, raw_input: str) -> PlanningPreviewResult:
        """Run retrieval + planning and return a preview result.

        Args:
            raw_input: The raw free-text user input.

        Returns:
            PlanningPreviewResult with user-facing response, event details,
            and confirmation requirements.
        """
        task_intent = TaskIntent(raw_text=raw_input)
        candidates = self._retrieval.retrieve_candidates(task_intent)
        output = self._planner.plan(task_intent, candidates)

        if output.route_plan is None:
            return PlanningPreviewResult(
                user_response=self._format_unable(output),
                event_type=ConversationEventType.PLAN_PREVIEW_UNABLE.value,
                event_payload=self._build_payload(task_intent, output, candidates),
                confirmation_required=False,
            )

        confirmation_required = (
            output.route_plan.confirmation_required
            or len(output.confirmation_requirements) > 0
        )
        return PlanningPreviewResult(
            user_response=self._format_proposed(output),
            event_type=ConversationEventType.PLAN_PREVIEW_PROPOSED.value,
            event_payload=self._build_payload(
                task_intent, output, candidates
            ),
            confirmation_required=confirmation_required,
            selected_path_id=output.route_plan.steps[0].learned_path_id,
        )

    # -----------------------------------------------------------------------
    # Formatting
    # -----------------------------------------------------------------------

    def _format_proposed(self, output: AgentDPlannerOutput) -> str:
        assert output.route_plan is not None
        step = output.route_plan.steps[0]
        parts: list[str] = [
            f"Plan: {step.purpose}",
            f"Selected path: {step.learned_path_id}",
        ]
        if output.warnings:
            parts.append("Warnings: " + "; ".join(output.warnings))
        if output.confirmation_requirements:
            reasons = "; ".join(
                c.message for c in output.confirmation_requirements
            )
            parts.append(f"Confirmation required: {reasons}")
            parts.append("Please confirm to proceed or send /cancel to abort.")
        else:
            parts.append("Please confirm to proceed or send /cancel to abort.")
        return "\n".join(parts)

    def _format_unable(self, output: AgentDPlannerOutput) -> str:
        reasons = output.uncertainty or ["No suitable learned paths found."]
        return f"Unable to plan: {reasons[0]}"

    # -----------------------------------------------------------------------
    # Payload construction
    # -----------------------------------------------------------------------

    def _build_payload(
        self,
        task_intent: TaskIntent,
        output: AgentDPlannerOutput,
        candidates: list[Any],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "task_intent_raw_text": task_intent.raw_text,
            "candidate_count": len(candidates),
            "planning_status": "proposed" if output.route_plan else "unable",
            "confirmation_required": (
                output.route_plan.confirmation_required
                if output.route_plan
                else False
            ),
            "warnings": output.warnings,
        }
        if output.route_plan is not None:
            step = output.route_plan.steps[0]
            payload["selected_path_id"] = step.learned_path_id
            payload["selected_purpose"] = step.purpose
            payload["match_reasons"] = [
                r for r in output.warnings if r.startswith("Retrieval match:")
            ]
        if output.confirmation_requirements:
            payload["confirmation_reasons"] = [
                {"reason": c.reason, "message": c.message}
                for c in output.confirmation_requirements
            ]
        if output.risk_hints:
            payload["risk_hints"] = [
                {"type": r.risk_type, "reason": r.reason}
                for r in output.risk_hints
            ]
        return payload
