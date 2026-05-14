"""Deterministic M12.2 user abort / stop handler.

The handler consumes a user abort signal and the current runtime state snapshot,
outputs a stop decision and acknowledgement. It performs no browser action,
generates no recovery proposal, and triggers no retry.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.schemas.recovery import (
    AbortAcknowledgement,
    AbortEvidence,
    StopHandlingDecision,
    UserAbortSignal,
    UserAbortState,
)


class UserAbortHandler:
    """Handle user abort signal deterministically — pure logic, no side effects."""

    # Statuses that mean the automation is already done.
    _FINISHED_STATUSES: frozenset[str] = frozenset(
        {
            "completed",
            "execution_finished",
            "success",
        }
    )
    _FAILED_STATUSES: frozenset[str] = frozenset(
        {
            "failed",
            "execution_failed",
            "error",
        }
    )
    # Statuses that mean there is active automation in progress.
    # Pre-execution states (awaiting_confirmation, task_intake) are excluded —
    # user abort during plan confirmation is a cancel, not an execution stop.
    _ACTIVE_STATUSES: frozenset[str] = frozenset(
        {
            "executing",
            "replay_running",
            "replay_requested",
            "abort_requested",
            "plan_confirmed",
            "paused",
        }
    )

    def handle(
        self,
        signal: UserAbortSignal | Mapping[str, Any],
        state: UserAbortState | Mapping[str, Any],
    ) -> AbortAcknowledgement:
        """Return a stable stop decision and acknowledgement for the given abort signal."""
        sig = self._coerce_signal(signal)
        st = self._coerce_state(state)
        decision = self._decide(st)
        evidence = self._build_evidence(sig, st)
        return AbortAcknowledgement(
            decision=decision,
            message=self._message(decision, st),
            evidence=evidence,
            no_new_actions_after=decision
            not in ("already_finished", "already_failed", "not_running"),
            inflight_caveat=st.has_inflight_action
            and decision not in ("already_finished", "already_failed", "not_running"),
        )

    # ------------------------------------------------------------------
    # Coercion
    # ------------------------------------------------------------------

    def _coerce_signal(self, signal: UserAbortSignal | Mapping[str, Any]) -> UserAbortSignal:
        if isinstance(signal, UserAbortSignal):
            return signal.model_copy(deep=True)
        return UserAbortSignal.model_validate(dict(signal))

    def _coerce_state(self, state: UserAbortState | Mapping[str, Any]) -> UserAbortState:
        if isinstance(state, UserAbortState):
            return state.model_copy(deep=True)
        return UserAbortState.model_validate(dict(state))

    # ------------------------------------------------------------------
    # Decision rules (deterministic, precedence-based)
    # ------------------------------------------------------------------

    def _decide(self, state: UserAbortState) -> StopHandlingDecision:
        status = (state.session_status or "").strip().lower()

        # Precedence 1: already finished or failed
        if status in self._FINISHED_STATUSES:
            return "already_finished"
        if status in self._FAILED_STATUSES:
            return "already_failed"

        # Precedence 2: no active automation
        if not status or status in ("idle", "not_running"):
            return "not_running"

        # Precedence 3: active but inflight action caveat
        if state.has_inflight_action and status in self._ACTIVE_STATUSES:
            return "cannot_interrupt_inflight_action"

        # Precedence 4: active automation, no inflight caveat
        if status in self._ACTIVE_STATUSES:
            return "accepted_stop"

        # Fallback: unknown / unrecognised state
        return "needs_manual_review"

    # ------------------------------------------------------------------
    # Evidence builder
    # ------------------------------------------------------------------

    def _build_evidence(self, signal: UserAbortSignal, state: UserAbortState) -> AbortEvidence:
        return AbortEvidence(
            signal=signal,
            state=state,
            captured_at=signal.timestamp,
        )

    # ------------------------------------------------------------------
    # Message dispatch
    # ------------------------------------------------------------------

    def _message(self, decision: StopHandlingDecision, state: UserAbortState) -> str:
        if decision == "accepted_stop":
            return "Abort accepted. No new browser actions will be started."
        if decision == "cannot_interrupt_inflight_action":
            return (
                "Abort accepted. A browser action may already be in flight; "
                "best-effort stop boundary recorded. No new actions will start."
            )
        if decision == "already_finished":
            return "Automation already finished before the abort was handled."
        if decision == "already_failed":
            return "Automation already failed before the abort was handled."
        if decision == "not_running":
            return "No active automation is currently running."
        return (
            "Abort received but the current runtime state is unclear; "
            "manual review is required before deciding next steps."
        )


def handle_user_abort(
    signal: UserAbortSignal | Mapping[str, Any],
    state: UserAbortState | Mapping[str, Any],
) -> AbortAcknowledgement:
    """Module-level convenience wrapper for the abort handler."""
    return UserAbortHandler().handle(signal, state)
