"""Plan confirmation / consent gate for M11.1.5.

Deterministic input classification while a conversation is in
``awaiting_confirmation``. No LLM, no replay, no browser operation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PlanConfirmationDecision:
    kind: str
    raw_input: str


@dataclass
class PlanConfirmationResult:
    decision: str
    user_response: str
    event_type: str
    next_status: str


class PlanConfirmationService:
    """Classify user input during ``awaiting_confirmation``.

    MVP classification uses an exact-match allowlist. Ambiguous input is never
    treated as consent.
    """

    _CONFIRM_KEYWORDS: frozenset[str] = frozenset(
        {"confirm", "yes", "proceed", "continue", "确认", "继续"}
    )
    _CANCEL_KEYWORDS: frozenset[str] = frozenset(
        {"cancel", "abort", "stop", "取消", "停止"}
    )
    _REJECT_KEYWORDS: frozenset[str] = frozenset(
        {"reject", "no", "不要"}
    )

    def classify(self, raw_input: str) -> PlanConfirmationDecision:
        normalized = raw_input.strip().lower()
        if normalized in self._CONFIRM_KEYWORDS:
            return PlanConfirmationDecision("confirm", raw_input)
        if normalized in self._CANCEL_KEYWORDS:
            return PlanConfirmationDecision("cancel", raw_input)
        if normalized in self._REJECT_KEYWORDS:
            return PlanConfirmationDecision("reject", raw_input)
        return PlanConfirmationDecision("ambiguous", raw_input)

    def process(self, raw_input: str) -> PlanConfirmationResult:
        decision = self.classify(raw_input)
        if decision.kind == "confirm":
            return PlanConfirmationResult(
                decision="confirm",
                user_response=(
                    "Plan confirmed. The task is ready for future execution. "
                    "Replay has not run yet."
                ),
                event_type="plan_confirmed",
                next_status="plan_confirmed",
            )
        if decision.kind == "cancel":
            return PlanConfirmationResult(
                decision="cancel",
                user_response="The pending plan has been cancelled. No execution occurred.",
                event_type="plan_cancelled",
                next_status="task_intake",
            )
        if decision.kind == "reject":
            return PlanConfirmationResult(
                decision="reject",
                user_response=(
                    "The plan was not accepted and was not executed. "
                    "Please describe a revised task."
                ),
                event_type="plan_rejected",
                next_status="task_intake",
            )
        return PlanConfirmationResult(
            decision="ambiguous",
            user_response=(
                "Please confirm, cancel, reject, or describe a revised task explicitly."
            ),
            event_type="confirmation_clarification_requested",
            next_status="awaiting_confirmation",
        )
