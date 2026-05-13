"""Plan execution via replay for M11.1.6.

Deterministic execution of confirmed plans. No LLM, no autonomous run,
no result verification.

Replay invocation is intentionally split out of this service so the
caller (orchestrator) can record ``plan_execution_started`` and transition
to ``executing`` **before** the replay handler runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas.conversation import ConversationEventType, ConversationReplaySummary


@dataclass
class PlanExecutionDecision:
    is_execution_intent: bool
    raw_input: str


@dataclass
class PlanExecutionResult:
    is_execution_intent: bool
    status: str  # "not_execution_intent" | "blocked" | "completed" | "failed"
    user_response: str
    event_type: str
    next_status: str
    payload: dict[str, Any]


_EXECUTION_TOKENS: frozenset[str] = frozenset(
    {"execute", "run", "start", "执行", "开始"}
)


class PlanExecutionService:
    """Classify execution intent and build execution results.

    MVP uses exact-match tokens. No LLM, no fuzzy inference.
    This service does **not** call the replay handler directly; the caller
    is responsible for running replay and then using
    ``build_result_from_replay`` / ``build_result_from_error``.
    """

    def classify(self, raw_input: str) -> PlanExecutionDecision:
        normalized = raw_input.strip()
        lower = normalized.lower()
        if lower in _EXECUTION_TOKENS or normalized in _EXECUTION_TOKENS:
            return PlanExecutionDecision(
                is_execution_intent=True, raw_input=raw_input
            )
        return PlanExecutionDecision(
            is_execution_intent=False, raw_input=raw_input
        )

    def extract_confirmed_plan_context(
        self, events: list[Any]
    ) -> dict[str, Any] | None:
        """Recover confirmed plan context from conversation events.

        Requires **both** a ``plan_preview_proposed`` event and a
        ``plan_confirmed`` event. The ``plan_confirmed`` event is the
        auditable 11.1.5 consent record; without it execution is blocked.
        """
        preview_payload: dict[str, Any] | None = None
        confirmed_payload: dict[str, Any] | None = None

        for event in reversed(events):
            if not hasattr(event, "type") or not hasattr(
                event, "payload_json"
            ):
                continue
            if (
                event.type == ConversationEventType.PLAN_PREVIEW_PROPOSED.value
                and preview_payload is None
            ):
                preview_payload = event.payload_json
            if (
                event.type == ConversationEventType.PLAN_CONFIRMED.value
                and confirmed_payload is None
            ):
                confirmed_payload = event.payload_json

        # 11.1.6 P2: both preview and confirmed evidence are required
        if preview_payload is None or confirmed_payload is None:
            return None

        context: dict[str, Any] = {
            "learned_path_id": preview_payload.get("selected_path_id"),
            "selected_purpose": preview_payload.get("selected_purpose"),
            "target_url": preview_payload.get("target_url"),
            "route_summary": preview_payload.get("route_summary"),
            "route_steps": preview_payload.get("route_steps", []),
            "warnings": preview_payload.get("warnings", []),
            "risk_hints": preview_payload.get("risk_hints", []),
            "confirmation_requirements": preview_payload.get(
                "confirmation_requirements", []
            ),
            "confirmed_at": confirmed_payload.get("confirmed_at"),
            "confirmed_decision": confirmed_payload.get("decision"),
        }
        return context

    def validate(
        self,
        raw_input: str,
        confirmed_plan_context: dict[str, Any] | None,
    ) -> PlanExecutionResult:
        """Classify execution intent and validate context.

        Does **not** call replay. Returns a ``blocked`` result when
        preconditions are missing, otherwise returns the execution context
        inside ``payload`` so the caller can record ``plan_execution_started``
        before invoking replay.
        """
        decision = self.classify(raw_input)
        if not decision.is_execution_intent:
            return PlanExecutionResult(
                is_execution_intent=False,
                status="not_execution_intent",
                user_response="",
                event_type="",
                next_status="plan_confirmed",
                payload={},
            )

        if not confirmed_plan_context:
            return self._blocked(
                reason="missing_confirmed_plan",
                missing_fields=["confirmed_plan_context"],
            )

        learned_path_id = confirmed_plan_context.get("learned_path_id")
        target_url = confirmed_plan_context.get("target_url")

        if not learned_path_id or not target_url:
            missing: list[str] = []
            if not learned_path_id:
                missing.append("learned_path_id")
            if not target_url:
                missing.append("target_url")
            return self._blocked(
                reason="missing_execution_context",
                missing_fields=missing,
            )

        route_steps = confirmed_plan_context.get("route_steps", [])
        if len(route_steps) > 1:
            return self._blocked(
                reason="unsupported_multi_step_route",
                missing_fields=["single_step_route"],
            )

        # Validation passed — return ready payload for the caller to use
        # when recording plan_execution_started.
        return PlanExecutionResult(
            is_execution_intent=True,
            status="ready",
            user_response="",
            event_type="",
            next_status="plan_confirmed",
            payload={
                "learned_path_id": learned_path_id,
                "target_url": target_url,
                "route_summary": confirmed_plan_context.get("route_summary"),
                "no_result_verification": True,
                "no_autonomous": True,
            },
        )

    def build_result_from_replay(
        self,
        raw_input: str,
        confirmed_plan_context: dict[str, Any],
        replay_summary: ConversationReplaySummary,
    ) -> PlanExecutionResult:
        """Build a completed or failed result from a replay summary."""
        learned_path_id = confirmed_plan_context["learned_path_id"]
        target_url = confirmed_plan_context["target_url"]

        completed_payload = {
            "learned_path_id": learned_path_id,
            "target_url": target_url,
            "replay_status": replay_summary.replay_status,
            "drift_status": replay_summary.drift_status,
            "no_result_verification": True,
            "task_verified": False,
            "no_autonomous": True,
        }

        if replay_summary.replay_status in ("succeeded", "observed"):
            return PlanExecutionResult(
                is_execution_intent=True,
                status="completed",
                user_response=(
                    "Replay execution completed. "
                    "Result verification is not implemented in this package."
                ),
                event_type="plan_execution_completed",
                next_status="execution_finished",
                payload=completed_payload,
            )

        failed_payload = {
            "learned_path_id": learned_path_id,
            "target_url": target_url,
            "replay_status": replay_summary.replay_status,
            "drift_status": replay_summary.drift_status,
            "error_summary": replay_summary.error
            or f"replay_status={replay_summary.replay_status}",
            "no_result_verification": True,
            "task_verified": False,
            "no_autonomous": True,
        }
        return PlanExecutionResult(
            is_execution_intent=True,
            status="failed",
            user_response=(
                "Replay execution failed before result verification. "
                "No recovery was attempted."
            ),
            event_type="plan_execution_failed",
            next_status="execution_failed",
            payload=failed_payload,
        )

    def build_result_from_error(
        self,
        raw_input: str,
        confirmed_plan_context: dict[str, Any],
        error: Exception,
    ) -> PlanExecutionResult:
        """Build a failed result from a replay exception."""
        learned_path_id = confirmed_plan_context["learned_path_id"]
        target_url = confirmed_plan_context["target_url"]

        failed_payload = {
            "learned_path_id": learned_path_id,
            "target_url": target_url,
            "error_summary": str(error),
            "no_result_verification": True,
            "task_verified": False,
            "no_autonomous": True,
        }
        return PlanExecutionResult(
            is_execution_intent=True,
            status="failed",
            user_response=(
                "Replay execution failed before result verification. "
                "No recovery was attempted."
            ),
            event_type="plan_execution_failed",
            next_status="execution_failed",
            payload=failed_payload,
        )

    def _blocked(
        self, reason: str, missing_fields: list[str]
    ) -> PlanExecutionResult:
        return PlanExecutionResult(
            is_execution_intent=True,
            status="blocked",
            user_response=(
                "The confirmed plan is not executable because required "
                "replay context is missing."
            ),
            event_type="plan_execution_blocked",
            next_status="plan_confirmed",
            payload={
                "reason": reason,
                "missing_fields": missing_fields,
                "no_result_verification": True,
                "no_autonomous": True,
            },
        )
