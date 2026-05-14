"""Deterministic M12.1 recovery boundary classifier.

The classifier only converts structured M11.1 evidence into a classification
and boundary recommendation. It does not perform any recovery action.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.schemas.recovery import (
    BoundaryRecommendation,
    ClassificationReason,
    EvidenceReference,
    RecoveryBoundary,
    RecoveryEvidence,
)


class RecoveryBoundaryClassifier:
    """Classify recovery boundary from structured execution/reporting evidence."""

    def classify(self, evidence: RecoveryEvidence | Mapping[str, Any]) -> RecoveryBoundary:
        """Return the strongest applicable recovery boundary.

        Precedence is fixed by 12.1:
        blocked > failure > uncertain > needs_review marker > success.
        """
        data = self._coerce_evidence(evidence)
        references = self._build_evidence_references(data)

        if self._is_blocked(data):
            reason = self._blocked_reason(data)
            return self._build_boundary(
                data=data,
                classification="blocked",
                recommendation=self._blocked_recommendation(reason),
                reason=reason,
                evidence=references,
            )

        if self._is_failure(data):
            reason = self._failure_reason(data)
            return self._build_boundary(
                data=data,
                classification="failure",
                recommendation=self._failure_recommendation(data, reason),
                reason=reason,
                evidence=references,
            )

        if self._is_uncertain(data):
            reason: ClassificationReason = (
                "result_reporter_uncertain"
                if data.verification_outcome == "uncertain"
                else "insufficient_postcondition_evidence"
            )
            return self._build_boundary(
                data=data,
                classification="uncertain",
                recommendation="needs_review",
                reason=reason,
                evidence=references,
            )

        if data.needs_review or data.verification_outcome == "needs_review":
            return self._build_boundary(
                data=data,
                classification="needs_review",
                recommendation="needs_review",
                reason="explicit_needs_review",
                evidence=references,
            )

        if data.task_verified and data.postcondition_evidence:
            return self._build_boundary(
                data=data,
                classification="success_no_recovery_needed",
                recommendation="no_recovery_needed",
                reason="task_succeeded",
                evidence=references,
            )

        return self._build_boundary(
            data=data,
            classification="needs_review",
            recommendation="needs_review",
            reason="explicit_needs_review",
            evidence=references,
        )

    def _coerce_evidence(self, evidence: RecoveryEvidence | Mapping[str, Any]) -> RecoveryEvidence:
        if isinstance(evidence, RecoveryEvidence):
            return evidence.model_copy(deep=True)
        return RecoveryEvidence.model_validate(dict(evidence))

    def _is_blocked(self, data: RecoveryEvidence) -> bool:
        return (
            data.execution_status == "blocked"
            or data.verification_outcome == "blocked"
            or bool(data.blocked_reason)
            or bool(data.missing_fields)
        )

    def _blocked_reason(self, data: RecoveryEvidence) -> ClassificationReason:
        reason_text = self._normalize(data.blocked_reason)
        missing_text = " ".join(data.missing_fields).lower()
        combined = f"{reason_text} {missing_text}".strip()

        if "unsupported" in combined:
            return "unsupported_action"
        if "permission" in combined or "auth" in combined or "login" in combined:
            return "permission_or_auth_blocked"
        if (
            "unsafe" in combined
            or "unknown_state" in combined
            or "side_effect" in combined
            or "side effect" in combined
        ):
            return "unsafe_or_unknown_state"
        if "target_missing" in combined or "target missing" in combined:
            return "target_missing"
        if data.missing_fields:
            return "missing_context"
        if data.verification_outcome == "blocked":
            return "result_reporter_blocked"
        return "missing_context"

    def _blocked_recommendation(self, reason: ClassificationReason) -> str:
        if reason in ("missing_context", "permission_or_auth_blocked", "result_reporter_blocked"):
            return "ask_user"
        if reason == "target_missing":
            return "suggest_reteach"
        return "stop"

    def _is_failure(self, data: RecoveryEvidence) -> bool:
        return (
            data.verification_outcome == "failed"
            or data.execution_status == "failed"
            or bool(data.error_summary)
            or self._has_failed_replay(data)
            or self._has_drift(data)
        )

    def _failure_reason(self, data: RecoveryEvidence) -> ClassificationReason:
        if data.verification_outcome == "failed":
            return "result_reporter_failed"
        if self._has_failed_replay(data):
            return "replay_failed"
        if self._has_drift(data):
            drift_text = self._normalize(data.drift_status)
            drift_reasons = " ".join(data.drift_reasons).lower()
            combined = f"{drift_text} {drift_reasons}"
            if "target_missing" in combined or "target missing" in combined:
                return "target_missing"
            if "stale" in combined or "missing_path" in combined or "path_coverage" in combined:
                return "stale_or_missing_path_coverage"
            return "replay_drifted"
        return "execution_error"

    def _failure_recommendation(
        self,
        data: RecoveryEvidence,
        reason: ClassificationReason,
    ) -> BoundaryRecommendation:
        if reason in ("target_missing", "stale_or_missing_path_coverage", "replay_drifted"):
            return "suggest_reteach"
        if reason == "replay_failed" and data.retry_candidate:
            return "retry_possible_requires_confirmation"
        return "stop"

    def _is_uncertain(self, data: RecoveryEvidence) -> bool:
        if data.verification_outcome == "uncertain":
            return True
        replay_completed_cleanly = data.replay_status in ("succeeded", "observed") and (
            data.drift_status in (None, "none")
        )
        if replay_completed_cleanly and not self._has_success_evidence(data):
            return True
        return data.execution_status == "completed" and not self._has_success_evidence(data)

    def _has_success_evidence(self, data: RecoveryEvidence) -> bool:
        return data.task_verified and bool(data.postcondition_evidence)

    def _has_failed_replay(self, data: RecoveryEvidence) -> bool:
        return data.replay_status is not None and data.replay_status not in (
            "succeeded",
            "observed",
        )

    def _has_drift(self, data: RecoveryEvidence) -> bool:
        return data.drift_status is not None and data.drift_status != "none"

    def _build_boundary(
        self,
        *,
        data: RecoveryEvidence,
        classification: str,
        recommendation: str,
        reason: ClassificationReason,
        evidence: list[EvidenceReference],
    ) -> RecoveryBoundary:
        return RecoveryBoundary(
            classification=classification,
            recommendation=recommendation,
            reason=reason,
            evidence=evidence,
            message=self._message(classification, recommendation, reason, data),
        )

    def _message(
        self,
        classification: str,
        recommendation: str,
        reason: ClassificationReason,
        data: RecoveryEvidence,
    ) -> str:
        if recommendation == "retry_possible_requires_confirmation":
            return (
                "Future retry consideration requires confirmation through later "
                "recovery policy; this classifier only marks the boundary."
            )
        if recommendation == "suggest_reteach":
            return (
                f"Failure classified as {reason}; consider re-teaching or updating "
                "the learned path before any later recovery decision."
            )
        if classification == "success_no_recovery_needed":
            return "Structured postcondition evidence indicates no recovery is needed."
        if classification == "blocked":
            return f"Boundary is blocked by {reason}; no recovery action is started."
        if classification == "failure":
            return f"Failure classified as {reason}; stop or route to later recovery planning."
        if classification == "uncertain":
            return "Result is uncertain because postcondition evidence is insufficient."
        return "Manual review is required before any recovery decision."

    def _build_evidence_references(self, data: RecoveryEvidence) -> list[EvidenceReference]:
        references: list[EvidenceReference] = []
        self._add_ref(references, "execution", "execution_status", data.execution_status)
        self._add_ref(references, "execution", "blocked_reason", data.blocked_reason)
        self._add_ref(references, "execution", "missing_fields", data.missing_fields)
        self._add_ref(references, "execution", "error_summary", data.error_summary)
        self._add_ref(references, "replay", "replay_status", data.replay_status)
        self._add_ref(references, "replay", "drift_status", data.drift_status)
        self._add_ref(references, "replay", "drift_reasons", data.drift_reasons)
        self._add_ref(
            references,
            "task_result_reporter",
            "verification_outcome",
            data.verification_outcome,
        )
        self._add_ref(references, "task_result_reporter", "needs_review", data.needs_review)
        self._add_ref(references, "task_result_reporter", "task_verified", data.task_verified)
        self._add_ref(
            references,
            "task_result_reporter",
            "postcondition_evidence",
            [ref.model_dump() for ref in data.postcondition_evidence],
        )
        self._add_ref(references, "recovery", "retry_candidate", data.retry_candidate)
        self._add_ref(references, "context", "learned_path_id", data.learned_path_id)
        self._add_ref(references, "context", "target_url", data.target_url)
        self._add_ref(references, "context", "final_url", data.final_url)
        self._add_ref(references, "context", "final_title", data.final_title)
        return references

    def _add_ref(
        self,
        references: list[EvidenceReference],
        source: str,
        key: str,
        value: Any,
    ) -> None:
        if value is None or value == "" or value == []:
            return
        references.append(EvidenceReference(source=source, key=key, value=value))

    def _normalize(self, value: str | None) -> str:
        return (value or "").strip().lower()


def classify_recovery_boundary(evidence: RecoveryEvidence | Mapping[str, Any]) -> RecoveryBoundary:
    """Classify the M12.1 recovery boundary from structured evidence."""
    return RecoveryBoundaryClassifier().classify(evidence)
