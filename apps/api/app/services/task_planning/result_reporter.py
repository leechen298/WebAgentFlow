"""Task Result Reporter for M11.1.7.

Consumes execution evidence, derives a conservative verification outcome,
and builds an evidence-bound user-facing report.

Does NOT:
- execute or re-run replay
- call autonomous run
- read raw HTML
- call LLM provider
- call Page Understanding Agent
- implement recovery
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas.conversation import ConversationReplaySummary


@dataclass
class TaskResultReport:
    """Outcome of the Task Result Reporter."""

    user_response: str
    outcome: str  # verified | failed | uncertain | needs_review | blocked
    evidence_summary: str
    missing_evidence_summary: str
    needs_review: bool
    event_payload: dict[str, Any]
    event_type: str = "task_result_reported"


class TaskResultReporter:
    """Build a verification report from execution evidence.

    First version is conservative:
    - ``plan_execution_completed + no postcondition evidence -> uncertain``
    - ``verified`` requires explicit postcondition evidence (first version
      has minimal postcondition sources, so ``verified`` is rare).
    """

    def build_report(
        self,
        execution_status: str,
        execution_payload: dict[str, Any],
        replay_summary: ConversationReplaySummary | None,
        confirmed_plan_context: dict[str, Any] | None,
    ) -> TaskResultReport:
        """Derive verification outcome and build report."""
        outcome, needs_review = self._derive_outcome(
            execution_status,
            execution_payload,
            replay_summary,
            confirmed_plan_context,
        )
        evidence_summary = self._build_evidence_summary(
            execution_status, execution_payload, replay_summary, confirmed_plan_context
        )
        missing_evidence_summary = self._build_missing_evidence_summary(
            outcome, execution_status, replay_summary
        )
        user_response = self._build_user_response(
            outcome, evidence_summary, missing_evidence_summary
        )

        learned_path_id: str | None = None
        if confirmed_plan_context is not None:
            learned_path_id = confirmed_plan_context.get("learned_path_id")
        if not learned_path_id and execution_payload is not None:
            learned_path_id = execution_payload.get("learned_path_id")

        # Structured replay / execution evidence for UI / downstream parsing.
        replay_status: str | None = None
        drift_status: str | None = None
        final_url: str | None = None
        final_title: str | None = None
        error_summary: str | None = None
        if replay_summary is not None:
            replay_status = replay_summary.replay_status
            drift_status = replay_summary.drift_status
            final_url = replay_summary.final_url
            final_title = replay_summary.final_title
            error_summary = replay_summary.error or None
        if error_summary is None and execution_payload is not None:
            error_summary = execution_payload.get("error_summary") or None
        execution_evidence = self._collect_postcondition_evidence(
            execution_payload,
            confirmed_plan_context,
            replay_summary,
        )

        event_payload: dict[str, Any] = {
            "learned_path_id": learned_path_id,
            "verification_outcome": outcome,
            "evidence_summary": evidence_summary,
            "missing_evidence_summary": missing_evidence_summary,
            "task_verified": outcome == "verified",
            "needs_review": needs_review,
            "no_recovery": True,
            "no_autonomous": True,
            "no_llm": True,
            # Structured evidence fields (added in follow-up fix)
            "execution_status": execution_status,
            "replay_status": replay_status,
            "drift_status": drift_status,
            "error_summary": error_summary,
            "final_url": final_url,
            "final_title": final_title,
            "execution_evidence": execution_evidence,
        }

        return TaskResultReport(
            user_response=user_response,
            outcome=outcome,
            evidence_summary=evidence_summary,
            missing_evidence_summary=missing_evidence_summary,
            needs_review=needs_review,
            event_payload=event_payload,
            event_type="task_result_reported",
        )

    def _derive_outcome(
        self,
        execution_status: str,
        execution_payload: dict[str, Any],
        replay_summary: ConversationReplaySummary | None,
        confirmed_plan_context: dict[str, Any] | None,
    ) -> tuple[str, bool]:
        """Derive verification outcome and needs_review flag.

        Returns ``(outcome, needs_review)``.
        """
        if execution_status == "blocked":
            return "blocked", False

        if execution_status == "failed":
            return "failed", False

        # execution_status == "completed"
        if replay_summary is None:
            return "uncertain", True

        # Replay-level negative signals -> failed
        if replay_summary.replay_status not in ("succeeded", "observed"):
            return "failed", False
        if replay_summary.drift_status != "none":
            return "failed", False
        if replay_summary.error:
            return "failed", False

        # Replay completed cleanly. Check for explicit postcondition evidence.
        postcondition_status = self._check_postconditions(
            replay_summary, execution_payload, confirmed_plan_context
        )
        if postcondition_status == "verified":
            return "verified", False
        if postcondition_status == "missing":
            return "needs_review", True

        # Default: uncertain + needs_review
        return "uncertain", True

    def _check_postconditions(
        self,
        replay_summary: ConversationReplaySummary,
        execution_payload: dict[str, Any],
        confirmed_plan_context: dict[str, Any] | None,
    ) -> str | None:
        """Check whether explicit postcondition evidence supports success.

        First version is conservative. It only checks structured signals
        already present in the execution payload or confirmed plan context.
        It does NOT read raw HTML, call LLM, or open the browser.
        """
        evidence_items = self._collect_postcondition_evidence(
            execution_payload,
            confirmed_plan_context,
            replay_summary,
        )
        expected_target = self._expected_text_target(
            execution_payload,
            confirmed_plan_context,
        )
        saw_matching_missing = False

        for raw in evidence_items:
            evidence = self._normalize_evidence(raw)
            if evidence is None:
                continue
            if evidence.get("kind") != "dom_text_present":
                continue
            if expected_target is not None and evidence.get("target") != expected_target:
                continue
            status = evidence.get("status")
            if status == "verified":
                return "verified"
            if status == "missing":
                saw_matching_missing = True

        if saw_matching_missing:
            return "missing"
        return None

    def _collect_postcondition_evidence(
        self,
        execution_payload: dict[str, Any] | None,
        confirmed_plan_context: dict[str, Any] | None,
        replay_summary: ConversationReplaySummary | None,
    ) -> list[dict[str, Any]]:
        evidence_items: list[Any] = []
        if confirmed_plan_context:
            evidence_items.extend(
                confirmed_plan_context.get("postcondition_evidence") or []
            )
            evidence_items.extend(
                confirmed_plan_context.get("execution_evidence") or []
            )
        if execution_payload:
            evidence_items.extend(execution_payload.get("execution_evidence") or [])
            evidence_items.extend(
                execution_payload.get("postcondition_evidence") or []
            )
        if replay_summary is not None:
            evidence_items.extend(replay_summary.execution_evidence)

        normalized: list[dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        for raw in evidence_items:
            evidence = self._normalize_evidence(raw)
            if evidence is not None:
                key = (
                    evidence.get("kind"),
                    evidence.get("target"),
                    evidence.get("status"),
                    evidence.get("summary"),
                )
                if key in seen:
                    continue
                seen.add(key)
                normalized.append(evidence)
        return normalized

    def _normalize_evidence(self, raw: Any) -> dict[str, Any] | None:
        if raw is None:
            return None
        if hasattr(raw, "model_dump"):
            raw = raw.model_dump(mode="json")
        if not isinstance(raw, dict):
            return None
        kind = raw.get("kind")
        status = raw.get("status")
        confidence = raw.get("confidence", 0.0)
        if kind not in {"dom_text_present", "unknown"}:
            return None
        if status not in {"verified", "missing", "unknown"}:
            return None
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError):
            return None
        if confidence_value < 0.0 or confidence_value > 1.0:
            return None
        return {
            "kind": kind,
            "target": raw.get("target"),
            "status": status,
            "confidence": confidence_value,
            "summary": str(raw.get("summary") or ""),
        }

    def _expected_text_target(
        self,
        execution_payload: dict[str, Any] | None,
        confirmed_plan_context: dict[str, Any] | None,
    ) -> str | None:
        for payload in (confirmed_plan_context, execution_payload):
            if not payload:
                continue
            for raw_target in payload.get("evidence_targets") or []:
                if not isinstance(raw_target, dict):
                    continue
                if raw_target.get("kind") != "dom_text_present":
                    continue
                text = raw_target.get("text")
                if isinstance(text, str) and text:
                    return text
            slot_overrides = payload.get("slot_overrides") or {}
            if isinstance(slot_overrides, dict) and len(slot_overrides) == 1:
                value = next(iter(slot_overrides.values()))
                if isinstance(value, str) and value:
                    return value
        return None

    def _build_evidence_summary(
        self,
        execution_status: str,
        execution_payload: dict[str, Any],
        replay_summary: ConversationReplaySummary | None,
        confirmed_plan_context: dict[str, Any] | None,
    ) -> str:
        """Summarize the evidence that was available."""
        parts: list[str] = []

        if execution_status == "blocked":
            parts.append("Execution was blocked.")
            reason = execution_payload.get("reason")
            if reason:
                parts.append(f"Reason: {reason}.")
            return " ".join(parts)

        if replay_summary is not None:
            parts.append(
                f"Replay status: {replay_summary.replay_status}."
            )
            parts.append(
                f"Drift status: {replay_summary.drift_status}."
            )
            if replay_summary.error:
                parts.append(f"Error: {replay_summary.error}.")
            if replay_summary.final_url:
                parts.append(f"Final URL: {replay_summary.final_url}.")
            if replay_summary.final_title:
                parts.append(f"Final title: {replay_summary.final_title}.")
        else:
            parts.append("Replay summary was not available.")

        if execution_payload.get("error_summary"):
            parts.append(
                f"Execution error: {execution_payload['error_summary']}."
            )

        return " ".join(parts) if parts else "No evidence available."

    def _build_missing_evidence_summary(
        self,
        outcome: str,
        execution_status: str,
        replay_summary: ConversationReplaySummary | None,
    ) -> str:
        """Summarize what evidence was missing."""
        if outcome == "verified":
            return ""

        if outcome == "needs_review":
            return (
                "Postcondition evidence was collected, but the expected "
                "target text was missing."
            )

        if execution_status == "blocked":
            return "Execution did not run; no verification evidence could be collected."

        if replay_summary is None:
            return "Replay result was missing."

        if replay_summary.replay_status not in ("succeeded", "observed"):
            return "Replay did not complete successfully."

        if replay_summary.drift_status != "none":
            return "Page drift detected; postcondition evidence may be unreliable."

        if replay_summary.error:
            return f"Replay error occurred: {replay_summary.error}."

        # Replay completed but no postcondition evidence
        return (
            "Replay completed, but no explicit postcondition evidence "
            "was available to verify business success."
        )

    def _build_user_response(
        self,
        outcome: str,
        evidence_summary: str,
        missing_evidence_summary: str,
    ) -> str:
        """Build user-facing report text."""
        if outcome == "verified":
            return (
                "The replay completed and the expected result was verified "
                "based on available evidence."
            )

        if outcome == "failed":
            return (
                "Replay execution failed before result verification. "
                "No recovery was attempted."
            )

        if outcome == "blocked":
            return (
                "Result verification could not run because execution was "
                "blocked or required evidence is missing."
            )

        if outcome == "uncertain":
            return (
                "Replay completed, but I could not verify the business result "
                "from available evidence. Please review the target page or "
                "provide a verification signal."
            )

        if outcome == "needs_review":
            return (
                "The replay evidence is incomplete. Manual review is needed "
                "before marking the task successful."
            )

        return "Result status is unknown."
