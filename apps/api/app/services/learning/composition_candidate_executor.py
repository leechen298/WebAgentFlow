"""Execution preparation for persisted composition candidates."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.composition_candidate import CompositionCandidate
from app.repos.composition_candidates_repo import CompositionCandidateRepository
from app.repos.learned_capabilities_repo import LearnedCapabilityRepository
from app.schemas.capability_composition import (
    CapabilityCompositionRequest,
    CapabilityExecutionHandoff,
)
from app.schemas.capability_composition_candidates import CompositionCandidateStatus
from app.schemas.learned_path_replay import ReplayAction, WaitResult
from app.services.execution.action_executor import execute_action
from app.services.execution.execution_runtime import RuntimeConfig, create_execution_runtime
from app.services.learning.attempt_evaluation import evaluate_attempt_ingest
from app.services.learning.capability_composer import CapabilityComposer
from app.services.learning.composition_promotion_service import CompositionPromotionService
from app.services.learning.wait_for_change import wait_for_change_after_action


@dataclass(frozen=True)
class CompositionCandidateExecutionPreparation:
    candidate_id: str
    status: CompositionCandidateStatus
    execution_handoff: CapabilityExecutionHandoff | None = None
    rejection_reason: str | None = None


@dataclass(frozen=True)
class CompositionCandidateRuntimeResult:
    execution_status: str
    pass_gate_status: str | None
    terminal_state_verdict: dict[str, Any]
    terminal_target: dict[str, Any]
    actions: list[dict[str, Any]]
    browser_event_evidence: dict[str, Any] | None = None


class CompositionCandidateExecutor:
    """Reconstruct service-internal execution handoff for ready candidates."""

    def __init__(
        self,
        session: Session,
        *,
        candidate_repo: CompositionCandidateRepository | None = None,
        capability_repo: LearnedCapabilityRepository | None = None,
        composer: CapabilityComposer | None = None,
    ) -> None:
        self._candidate_repo = candidate_repo or CompositionCandidateRepository(session)
        self._capability_repo = capability_repo or LearnedCapabilityRepository(session)
        self._composer = composer or CapabilityComposer()
        self._promotion_service = CompositionPromotionService(
            session,
            self._candidate_repo,
        )

    def prepare_execution_handoff(
        self,
        *,
        candidate_id: str,
        slot_bindings: dict[str, str],
    ) -> CompositionCandidateExecutionPreparation:
        candidate = self._candidate_repo.get_by_candidate_id(candidate_id)
        if candidate is None:
            raise ValueError(f"composition candidate not found: {candidate_id}")
        current_status = CompositionCandidateStatus(candidate.status)
        if current_status != CompositionCandidateStatus.READY_FOR_EXECUTION:
            return CompositionCandidateExecutionPreparation(
                candidate_id=candidate_id,
                status=current_status,
                rejection_reason="candidate is not ready for execution",
            )

        source_ids = [str(value) for value in candidate.source_capability_ids_json or []]
        capabilities = [
            capability
            for capability_id in source_ids
            if (capability := self._capability_repo.get(capability_id)) is not None
        ]
        if len(capabilities) != len(source_ids):
            return self._record_preparation_failure(
                candidate,
                reason="source capability unavailable",
                detail={
                    "expected_source_capability_count": len(source_ids),
                    "resolved_source_capability_count": len(capabilities),
                },
            )

        request = CapabilityCompositionRequest(
            target_url=candidate.target_scope_ref,
            page_template=candidate.page_template,
            query_signature=dict(candidate.query_signature or {}),
            user_goal=candidate.candidate_family,
            required_capability_kinds=[
                str(kind) for kind in candidate.ordered_capability_kinds_json or []
            ],
            slot_bindings=dict(slot_bindings),
            dom_fingerprint=candidate.dom_fingerprint,
        )
        result = self._composer.compose(request, candidates=capabilities)
        if result.execution_handoff is None or result.plan.status != "ready":
            return self._record_preparation_failure(
                candidate,
                reason="execution handoff reconstruction failed",
                detail={
                    "composition_status": result.plan.status,
                    "missing_capability_count": len(result.plan.missing_capabilities),
                    "rejection_reason_count": len(result.plan.rejection_reasons),
                },
            )

        handoff = result.execution_handoff.model_copy(
            update={
                "composition_id": candidate.candidate_id,
                "expected_terminal_target": dict(
                    candidate.expected_terminal_target_json or {}
                ),
            }
        )
        return CompositionCandidateExecutionPreparation(
            candidate_id=candidate_id,
            status=CompositionCandidateStatus.READY_FOR_EXECUTION,
            execution_handoff=handoff,
        )

    def execute_candidate(
        self,
        *,
        candidate_id: str,
        slot_bindings: dict[str, str],
        runner: Callable[
            [CapabilityExecutionHandoff],
            CompositionCandidateRuntimeResult,
        ]
        | None = None,
        target_url: str | None = None,
        headless: bool = True,
        promote: bool = False,
    ) -> CompositionCandidate:
        prepared = self.prepare_execution_handoff(
            candidate_id=candidate_id,
            slot_bindings=slot_bindings,
        )
        candidate = self._candidate_repo.get_by_candidate_id(candidate_id)
        if candidate is None:
            raise ValueError(f"composition candidate not found: {candidate_id}")
        if prepared.execution_handoff is None:
            return candidate

        if runner is None:
            runtime_target_url = target_url or candidate.target_url
            if not runtime_target_url:
                return self._record_runtime_target_missing(candidate)

            def runner(
                handoff: CapabilityExecutionHandoff,
            ) -> CompositionCandidateRuntimeResult:
                return run_execution_handoff(
                    handoff,
                    target_url=runtime_target_url,
                    headless=headless,
                )

        try:
            runtime_result = runner(prepared.execution_handoff)
        except Exception:
            return self._record_runner_failure(candidate)

        executed = self._promotion_service.record_execution_result(
            candidate_id=candidate_id,
            execution_status=runtime_result.execution_status,
            pass_gate_status=runtime_result.pass_gate_status,
            terminal_state_verdict=runtime_result.terminal_state_verdict,
            terminal_target=runtime_result.terminal_target,
            actions=runtime_result.actions,
            browser_event_evidence=runtime_result.browser_event_evidence,
        )
        if (
            promote
            and executed.status == CompositionCandidateStatus.EXECUTION_PASSED.value
        ):
            return self._promotion_service.promote_executed_candidate(
                candidate_id=candidate_id,
            )
        return executed

    def _record_preparation_failure(
        self,
        candidate,
        *,
        reason: str,
        detail: dict,
    ) -> CompositionCandidateExecutionPreparation:
        updated = self._candidate_repo.update_outcome(
            candidate,
            status=CompositionCandidateStatus.NEGATIVE_EVIDENCE_RECORDED,
            execution_outcome={
                "status": "preparation_failed",
                "reason": reason,
                **detail,
            },
            negative_evidence={
                "reason": reason,
                **detail,
            },
        )
        return CompositionCandidateExecutionPreparation(
            candidate_id=updated.candidate_id,
            status=CompositionCandidateStatus.NEGATIVE_EVIDENCE_RECORDED,
            rejection_reason=reason,
        )

    def _record_runtime_target_missing(
        self,
        candidate: CompositionCandidate,
    ) -> CompositionCandidate:
        return self._candidate_repo.update_outcome(
            candidate,
            status=CompositionCandidateStatus.NEGATIVE_EVIDENCE_RECORDED,
            execution_outcome={
                "status": "preparation_failed",
                "reason": "target url required for runtime execution",
            },
            negative_evidence={
                "reason": "target url required for runtime execution",
            },
        )

    def _record_runner_failure(
        self,
        candidate: CompositionCandidate,
    ) -> CompositionCandidate:
        terminal_state_verdict = {
            "terminal_outcome": "terminal_failed",
            "terminal_type": "",
            "evidence_strength": "none",
            "stop_decision": "stop",
            "matched_action_types": [],
        }
        ingest_evaluation = evaluate_attempt_ingest(
            pass_gate_status="fail",
            terminal_state_verdict=terminal_state_verdict,
            actions=[],
        )
        return self._candidate_repo.update_outcome(
            candidate,
            status=CompositionCandidateStatus.NEGATIVE_EVIDENCE_RECORDED,
            execution_outcome={
                "status": "failed",
                "reason": "execution runner failed",
                "pass_gate_status": "fail",
                "terminal_target": {},
                "terminal_state_verdict": terminal_state_verdict,
                "attempt_ingest_evaluation": ingest_evaluation.model_dump(mode="json"),
            },
            negative_evidence={
                "reason": "execution runner failed",
                "status": "failed",
                "pass_gate_status": "fail",
                "attempt_ingest_evaluation": ingest_evaluation.model_dump(mode="json"),
            },
        )


def run_execution_handoff(
    handoff: CapabilityExecutionHandoff,
    *,
    target_url: str,
    headless: bool = True,
) -> CompositionCandidateRuntimeResult:
    """Run a prepared handoff through shared execution primitives.

    This runner records browser mechanics only. Clean action execution remains
    ``unverified`` because no Supervisor or provider gate has judged business
    success.
    """

    runtime = create_execution_runtime(RuntimeConfig(headless=headless))
    step_logs: list[dict[str, Any]] = []
    actions = [
        _action_schema_to_replay_action(index, action_schema, handoff.slot_bindings)
        for index, action_schema in enumerate(handoff.ordered_action_schemas, start=1)
    ]
    try:
        runtime.start()
        runtime.navigate(target_url)
        for action in actions:
            log = execute_action(action, runtime)
            try:
                wait_result = wait_for_change_after_action(
                    page=runtime.page,
                    action=action,
                    step_log=log,
                )
            except Exception as wait_exc:
                wait_result = WaitResult(
                    status="skipped",
                    notes=f"wait failed: {wait_exc}"[:300],
                )
            log["wait_result"] = wait_result
            if action.value_slot:
                log["value_slot"] = action.value_slot
                log["override_applied"] = action.value is not None
                log["effective_value"] = action.value
            step_logs.append(log)
            if not log.get("ok", False) and action.action_type != "observe":
                break
    finally:
        runtime.stop()

    failed_count = sum(1 for log in step_logs if not log.get("ok", False))
    execution_status = "failed" if failed_count else "success"
    pass_gate_status = "fail" if failed_count else "unverified"
    terminal_outcome = "terminal_failed" if failed_count else "terminal_unverified"
    return CompositionCandidateRuntimeResult(
        execution_status=execution_status,
        pass_gate_status=pass_gate_status,
        terminal_state_verdict={
            "terminal_outcome": terminal_outcome,
            "terminal_type": str(handoff.expected_terminal_target.get("kind") or ""),
            "evidence_strength": "none" if failed_count else "weak",
            "stop_decision": "stop" if failed_count else "unverified_stop",
            "matched_action_types": [
                action.action_type
                for action, log in zip(actions, step_logs, strict=False)
                if log.get("ok", False)
            ],
        },
        terminal_target=dict(handoff.expected_terminal_target or {}),
        actions=[_replay_action_to_learned_path_action(action) for action in actions],
        browser_event_evidence={
            "runtime_surface": "execution_runtime",
            "action_count": len(step_logs),
            "failed_action_count": failed_count,
            "wait_statuses": [
                str(log["wait_result"].status)
                for log in step_logs
                if isinstance(log.get("wait_result"), WaitResult)
            ],
        },
    )


def _action_schema_to_replay_action(
    step: int,
    action_schema: dict[str, Any],
    slot_bindings: dict[str, str],
) -> ReplayAction:
    control_binding = dict(action_schema.get("control_binding") or {})
    required_slots = [str(slot) for slot in action_schema.get("required_slots") or []]
    value_slot = required_slots[0] if len(required_slots) == 1 else None
    return ReplayAction(
        step=step,
        action_type=str(action_schema.get("operation") or action_schema.get("adapter_type")),
        target_selector=control_binding.get("selector"),
        target_description=control_binding.get("description"),
        value=slot_bindings.get(value_slot) if value_slot else action_schema.get("value"),
        value_slot=value_slot,
    )


def _replay_action_to_learned_path_action(action: ReplayAction) -> dict[str, Any]:
    return {
        "step": action.step,
        "action_type": action.action_type,
        "target_selector": action.target_selector,
        "target_description": action.target_description,
        "value": action.value,
        "value_slot": action.value_slot,
    }
