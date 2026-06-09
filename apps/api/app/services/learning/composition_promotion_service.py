"""Promotion handling for executed composition candidates."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repos.composition_candidates_repo import CompositionCandidateRepository
from app.repos.learned_paths_repo import LearnedPathRepository
from app.schemas.capability_composition import CapabilityCompositionPlan
from app.schemas.capability_composition_candidates import CompositionCandidateStatus
from app.services.learning.attempt_evaluation import evaluate_attempt_ingest
from app.services.learning.capability_composer import evaluate_composition_promotion


class CompositionPromotionService:
    def __init__(
        self,
        session: Session,
        candidate_repo: CompositionCandidateRepository | None = None,
    ) -> None:
        self._session = session
        self._candidate_repo = candidate_repo or CompositionCandidateRepository(session)

    def record_execution_result(
        self,
        *,
        candidate_id: str,
        execution_status: str,
        pass_gate_status: str | None,
        terminal_state_verdict: dict[str, Any] | None,
        terminal_target: dict[str, Any],
        actions: list[dict[str, Any]],
        browser_event_evidence: dict[str, Any] | None = None,
    ):
        candidate = self._candidate_repo.get_by_candidate_id(candidate_id)
        if candidate is None:
            raise ValueError(f"composition candidate not found: {candidate_id}")
        if candidate.status != CompositionCandidateStatus.READY_FOR_EXECUTION.value:
            return candidate

        ingest_evaluation = evaluate_attempt_ingest(
            pass_gate_status=pass_gate_status,
            terminal_state_verdict=terminal_state_verdict,
            actions=actions,
        )
        execution_evidence = {
            "composition_id": candidate.candidate_id,
            "status": execution_status,
            "pass_gate_status": pass_gate_status,
            "terminal_target": terminal_target,
            "source_capability_ids": list(candidate.source_capability_ids_json or []),
            "terminal_state_verdict": terminal_state_verdict or {},
            "attempt_ingest_evaluation": ingest_evaluation.model_dump(mode="json"),
            "browser_event_evidence": browser_event_evidence or {},
            "actions": [dict(action) for action in actions],
        }
        if execution_status != "success" or ingest_evaluation.ingest_status != "eligible":
            return self._candidate_repo.update_outcome(
                candidate,
                status=CompositionCandidateStatus.NEGATIVE_EVIDENCE_RECORDED,
                execution_outcome=execution_evidence,
                negative_evidence={
                    "reason": "execution evidence did not satisfy promotion gate",
                    "status": execution_status,
                    "pass_gate_status": pass_gate_status,
                    "attempt_ingest_evaluation": ingest_evaluation.model_dump(mode="json"),
                    "terminal_target": terminal_target,
                },
            )

        return self._candidate_repo.update_outcome(
            candidate,
            status=CompositionCandidateStatus.EXECUTION_PASSED,
            execution_outcome=execution_evidence,
        )

    def promote_executed_candidate(
        self,
        *,
        candidate_id: str,
        actions: list[dict[str, Any]] | None = None,
    ):
        candidate = self._candidate_repo.get_by_candidate_id(candidate_id)
        if candidate is None:
            raise ValueError(f"composition candidate not found: {candidate_id}")
        if candidate.status != CompositionCandidateStatus.EXECUTION_PASSED.value:
            return candidate
        execution_evidence = dict(candidate.execution_outcome_json or {})
        plan = CapabilityCompositionPlan(
            composition_id=candidate.candidate_id,
            target_url=candidate.target_scope_ref,
            page_template=candidate.page_template,
            user_goal=candidate.generation_reason or candidate.candidate_family,
            status="ready",
            source_capability_ids=list(candidate.source_capability_ids_json or []),
            ordered_steps=[],
            expected_terminal_target=dict(candidate.expected_terminal_target_json or {}),
            risk_level=candidate.risk_level,
            confidence=candidate.confidence,
        )
        decision = evaluate_composition_promotion(plan, execution_evidence)
        if not decision.promotable:
            return self._candidate_repo.update_outcome(
                candidate,
                status=CompositionCandidateStatus.NEGATIVE_EVIDENCE_RECORDED,
                execution_outcome=execution_evidence,
                promotion_decision=decision.model_dump(mode="json"),
                negative_evidence={
                    "reason": "promotion guard rejected execution evidence",
                    "rejection_reasons": decision.rejection_reasons,
                },
            )

        source_ids = list(candidate.source_capability_ids_json or [])
        persisted_actions = list(execution_evidence.get("actions") or [])
        promoted_actions = [
            _attach_source_metadata(action, source_ids) for action in persisted_actions
        ]
        learned_path, _created = LearnedPathRepository(self._session).ingest_run(
            page_template=candidate.page_template,
            query_signature=dict(candidate.query_signature or {}),
            dom_fingerprint=candidate.dom_fingerprint or "",
            scenario=f"composition:{candidate.candidate_family}",
            actions=promoted_actions,
            source_run_id=candidate.source_run_id,
        )
        return self._candidate_repo.update_outcome(
            candidate,
            status=CompositionCandidateStatus.PROMOTED_TO_LEARNED_PATH,
            execution_outcome=execution_evidence,
            promotion_decision=decision.model_dump(mode="json"),
            promoted_learned_path_id=str(learned_path.id),
        )


def _attach_source_metadata(
    action: dict[str, Any],
    source_capability_ids: list[str],
) -> dict[str, Any]:
    copied = dict(action)
    metadata = dict(copied.get("metadata") or {})
    metadata["source_capability_ids"] = list(source_capability_ids)
    copied["metadata"] = metadata
    return copied
