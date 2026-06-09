"""Build redacted learning evidence bundles for external provider evaluation."""

from __future__ import annotations

import hashlib
import re

from sqlalchemy.orm import Session

from app.models.exploration_run import ExplorationRun
from app.models.learned_capability import LearnedCapability
from app.models.learned_path import LearnedPath
from app.models.learning_batch import LearningBatch
from app.repos.composition_candidates_repo import CompositionCandidateRepository
from app.schemas.learning_evidence_bundle import (
    BundleCompositionCandidate,
    BundleOperatorAction,
    LearningEvidenceBundle,
)


class LearningEvidenceBundleBuilder:
    def __init__(self, session: Session) -> None:
        self._session = session

    def build(
        self,
        *,
        operator_surface: str,
        operator_command: str,
        cwd: str,
        learning_batch_id: str | None = None,
        target_scope_ref: str | None = None,
    ) -> LearningEvidenceBundle:
        candidates = CompositionCandidateRepository(self._session).list_for_bundle(
            learning_batch_id=learning_batch_id,
            target_scope_ref=target_scope_ref,
        )
        capability_ids = _candidate_source_ids(candidates)
        path_ids = _candidate_promoted_path_ids(candidates)
        run_ids = _candidate_source_run_ids(candidates)
        learned_capability_summaries = [
            summary
            for capability_id in capability_ids
            if (summary := self._capability_summary(capability_id))
        ]
        learned_path_summaries = [
            summary
            for path_id in path_ids
            if (summary := self._path_summary(path_id))
        ]
        run_summaries = [
            summary for run_id in run_ids if (summary := self._run_summary(run_id))
        ]
        return LearningEvidenceBundle(
            operator_actions=[
                BundleOperatorAction(
                    surface=operator_surface,
                    command=operator_command,
                    cwd=cwd,
                )
            ],
            learning_batches=(
                [self._batch_summary(learning_batch_id)]
                if learning_batch_id is not None
                else []
            ),
            page_analysis_summary=_page_analysis_summary(candidates),
            learned_capabilities=learned_capability_summaries,
            learned_paths=learned_path_summaries,
            runs=run_summaries,
            composition_summary=_composition_summary(candidates),
            composition=[
                BundleCompositionCandidate(
                    candidate_ref=_opaque_ref("candidate", row.candidate_id),
                    target_scope_ref=row.target_scope_ref,
                    page_template=row.page_template,
                    candidate_family=row.candidate_family,
                    source_capability_refs=[
                        _opaque_ref("cap", str(source_id))
                        for source_id in row.source_capability_ids_json or []
                    ],
                    ordered_capability_kinds=list(
                        row.ordered_capability_kinds_json or []
                    ),
                    expected_terminal_target_summary={
                        "kind": (row.expected_terminal_target_json or {}).get("kind")
                    },
                    status=row.status,
                    static_rejection_reason=_redact_reason(
                        row.static_rejection_reason,
                        list(row.source_capability_ids_json or []),
                    ),
                    execution_summary=_execution_summary(
                        row.execution_outcome_json or {}
                    ),
                    promotion_decision_summary=_promotion_summary(
                        row.promotion_decision_json or {}
                    ),
                )
                for row in candidates
            ],
        )

    def _batch_summary(self, batch_id: str) -> dict:
        batch = self._session.get(LearningBatch, batch_id)
        if batch is None:
            return {"batch_ref": _stable_plain_ref("batch", batch_id)}
        summary = dict(batch.summary_json or {})
        return {
            "batch_ref": _stable_plain_ref("batch", batch_id),
            "status": str(batch.status),
            "page_template": batch.page_template,
            "planned_count": _int_or_zero(summary.get("planned")),
            "attempted_count": _int_or_zero(summary.get("attempted")),
            "passed_count": _int_or_zero(summary.get("passed")),
            "failed_count": _int_or_zero(summary.get("failed")),
            "unverified_count": _int_or_zero(summary.get("unverified")),
            "unsupported_count": _int_or_zero(summary.get("unsupported")),
            "warnings": [str(warning) for warning in summary.get("warnings") or []],
            "run_refs": [
                _opaque_ref("run", str(run_id))
                for run_id in batch.created_run_ids_json or []
            ],
            "capability_refs": [
                _opaque_ref("cap", str(capability_id))
                for capability_id in batch.created_capability_ids_json or []
            ],
            "learned_path_refs": [
                _opaque_ref("path", str(path_id))
                for path_id in batch.created_learned_path_ids_json or []
            ],
        }

    def _capability_summary(self, capability_id: str) -> dict:
        capability = self._session.get(LearnedCapability, capability_id)
        if capability is None:
            return {}
        action_schema = dict(capability.action_schema_json or {})
        evidence = dict(capability.evidence_json or {})
        return {
            "capability_ref": _opaque_ref("cap", capability_id),
            "kind": str(capability.capability_kind),
            "adapter_type": str(capability.adapter_type),
            "action_schema_summary": {
                "adapter_type": str(action_schema.get("adapter_type") or ""),
                "operation": str(action_schema.get("operation") or ""),
                "required_slot_count": len(action_schema.get("required_slots") or []),
                "control_binding_redacted": bool(action_schema.get("control_binding")),
            },
            "terminal_target_summary": {
                "kind": (capability.terminal_target_json or {}).get("kind")
            },
            "evidence_summary": {
                "terminal_outcome": evidence.get("terminal_outcome"),
                "evidence_strength": evidence.get("evidence_strength"),
            },
            "trust": str(capability.trust),
            "source_run_ref": (
                _opaque_ref("run", str(capability.source_run_id))
                if capability.source_run_id
                else None
            ),
            "source_learned_path_ref": (
                _opaque_ref("path", str(capability.source_learned_path_id))
                if capability.source_learned_path_id
                else None
            ),
        }

    def _path_summary(self, path_id: str) -> dict:
        path = self._session.get(LearnedPath, path_id)
        if path is None:
            return {}
        action_kinds = [
            str(action.get("action_type") or "")
            for action in path.actions or []
            if isinstance(action, dict)
        ]
        source_capability_ids = _path_source_capability_ids(path)
        return {
            "path_ref": _opaque_ref("path", path_id),
            "path_family_hint": str(path.scenario or ""),
            "action_count": len(path.actions or []),
            "action_kinds": action_kinds,
            "source_run_ref": (
                _opaque_ref("run", str(path.source_run_id)) if path.source_run_id else None
            ),
            "source_capability_refs": [
                _opaque_ref("cap", source_id) for source_id in source_capability_ids
            ],
            "trust": str(path.trust),
        }

    def _run_summary(self, run_id: str) -> dict:
        run = self._session.get(ExplorationRun, run_id)
        if run is None:
            return {}
        snapshot = dict(run.result_snapshot_json or {})
        terminal = dict(snapshot.get("terminal_state_verdict") or {})
        observation = dict(snapshot.get("observation_summary") or {})
        pass_gate = dict(snapshot.get("pass_gate") or {})
        return {
            "run_ref": _opaque_ref("run", run_id),
            "status": str(run.status),
            "pass_gate_status": pass_gate.get("status"),
            "terminal_outcome": terminal.get("terminal_outcome"),
            "terminal_type": terminal.get("terminal_type"),
            "observation_status": observation.get("status"),
        }


def _opaque_ref(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_ref_{digest}"


def _stable_plain_ref(prefix: str, value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return f"{prefix}_ref_{safe}"


def _candidate_source_ids(candidates) -> list[str]:
    seen: dict[str, None] = {}
    for row in candidates:
        for source_id in row.source_capability_ids_json or []:
            seen[str(source_id)] = None
    return list(seen)


def _candidate_promoted_path_ids(candidates) -> list[str]:
    seen: dict[str, None] = {}
    for row in candidates:
        if row.promoted_learned_path_id:
            seen[str(row.promoted_learned_path_id)] = None
    return list(seen)


def _candidate_source_run_ids(candidates) -> list[str]:
    seen: dict[str, None] = {}
    for row in candidates:
        if row.source_run_id:
            seen[str(row.source_run_id)] = None
    return list(seen)


def _path_source_capability_ids(path: LearnedPath) -> list[str]:
    seen: dict[str, None] = {}
    for action in path.actions or []:
        if not isinstance(action, dict):
            continue
        metadata = dict(action.get("metadata") or {})
        for source_id in metadata.get("source_capability_ids") or []:
            seen[str(source_id)] = None
    return list(seen)


def _page_analysis_summary(candidates) -> dict:
    page_templates = list(dict.fromkeys(str(row.page_template) for row in candidates))
    families = list(dict.fromkeys(str(row.candidate_family) for row in candidates))
    terminal_kinds = list(
        dict.fromkeys(
            str((row.expected_terminal_target_json or {}).get("kind") or "")
            for row in candidates
            if (row.expected_terminal_target_json or {}).get("kind")
        )
    )
    return {
        "candidate_count": len(candidates),
        "page_templates": page_templates,
        "candidate_families": families,
        "terminal_target_kinds": terminal_kinds,
        "visible_total": None,
        "capability_hint_kinds": [],
        "summary_status": "composition_candidate_projection",
    }


def _int_or_zero(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _redact_reason(reason: str | None, source_capability_ids: list[str]) -> str | None:
    if reason is None:
        return None
    redacted = reason
    for source_id in source_capability_ids:
        if source_id:
            redacted = redacted.replace(source_id, "redacted_ref")
    redacted = re.sub(r"https?://[^\s,;'\"<>)}]+", "redacted_url", redacted)
    redacted = re.sub(r"#[A-Za-z][A-Za-z0-9_-]*", "redacted_control", redacted)
    redacted = re.sub(
        r"\b(?:target_url|url|seed|secret|token|api_key|password|credential|cookie)"
        r"=[^\s,;'\"<>)}]+",
        "redacted_pair",
        redacted,
        flags=re.IGNORECASE,
    )
    redacted = re.sub(r"(?<=: )[A-Za-z0-9_.-]*capability[A-Za-z0-9_.-]*", "redacted_ref", redacted)
    redacted = re.sub(r"(rejected: )[A-Za-z0-9_.-]+", r"\1redacted_ref", redacted)
    return redacted


def _execution_summary(value: dict) -> dict:
    if not value:
        return {}
    ingest = dict(value.get("attempt_ingest_evaluation") or {})
    terminal = dict(value.get("terminal_state_verdict") or {})
    return {
        "pass_gate_status": value.get("pass_gate_status"),
        "terminal_outcome": terminal.get("terminal_outcome"),
        "terminal_type": terminal.get("terminal_type"),
        "ingest_status": ingest.get("ingest_status"),
        "browser_event_evidence": _browser_event_summary(
            dict(value.get("browser_event_evidence") or {})
        ),
    }


def _promotion_summary(value: dict) -> dict:
    if not value:
        return {}
    summary = {
        "promotable": bool(value.get("promotable")),
        "rejection_reasons": list(value.get("rejection_reasons") or []),
    }
    if value.get("composition_id"):
        summary["candidate_ref"] = _opaque_ref("candidate", str(value["composition_id"]))
    return summary


def _browser_event_summary(value: dict) -> dict:
    if not value:
        return {}
    return {
        "runtime_surface": value.get("runtime_surface"),
        "action_count": int(value.get("action_count") or 0),
        "failed_action_count": int(value.get("failed_action_count") or 0),
        "wait_statuses": [str(status) for status in value.get("wait_statuses") or []],
    }


def _composition_summary(candidates) -> dict:
    total = len(candidates)
    ready = [row for row in candidates if row.status == "ready_for_execution"]
    executed = [
        row
        for row in candidates
        if row.execution_outcome_json
        and row.execution_outcome_json.get("status") != "preparation_failed"
    ]
    promoted = [
        row
        for row in candidates
        if row.status == "promoted_to_learned_path"
    ]
    promoted_with_pass = [
        row
        for row in promoted
        if _has_pass_and_eligible_ingest(row)
    ]
    static_rejected = [row for row in candidates if row.status == "rejected_static"]
    negative_evidence = [
        row for row in candidates if row.status == "negative_evidence_recorded"
    ]
    reasonable_or_executed_ids = {
        row.candidate_id for row in [*ready, *executed, *promoted]
    }
    reasonable_or_executed_count = len(reasonable_or_executed_ids)
    executable_denominator = reasonable_or_executed_count
    failed_or_rejected_total = len(static_rejected) + len(negative_evidence)
    failed_or_rejected_recorded = sum(
        1 for row in [*static_rejected, *negative_evidence]
        if row.static_rejection_reason or row.negative_evidence_json
    )
    null_metric_reasons = {}
    if promoted:
        promotion_reliability = len(promoted_with_pass) / len(promoted)
    else:
        promotion_reliability = None
        null_metric_reasons["promotion_reliability"] = "no promoted candidates"
    if total:
        candidate_reasonable_rate = reasonable_or_executed_count / total
    else:
        candidate_reasonable_rate = None
        null_metric_reasons["candidate_reasonable_rate"] = "no candidates"
    if executable_denominator:
        execution_attempt_coverage = len(executed) / executable_denominator
    else:
        execution_attempt_coverage = None
        null_metric_reasons["execution_attempt_coverage"] = "no executable candidates"
    if failed_or_rejected_total:
        negative_evidence_capture_rate = (
            failed_or_rejected_recorded / failed_or_rejected_total
        )
    else:
        negative_evidence_capture_rate = None
        null_metric_reasons["negative_evidence_capture_rate"] = (
            "no failed or rejected candidates"
        )
    return {
        "total_candidates": total,
        "ready_for_execution_candidates": len(ready),
        "executed_candidates": len(executed),
        "execution_passed_candidates": sum(
            1 for row in candidates if row.status == "execution_passed"
        ),
        "promoted_candidates": len(promoted),
        "negative_evidence_candidates": len(negative_evidence),
        "static_rejected_candidates": len(static_rejected),
        "candidate_reasonable_rate": candidate_reasonable_rate,
        "execution_attempt_coverage": execution_attempt_coverage,
        "promotion_reliability": promotion_reliability,
        "negative_evidence_capture_rate": negative_evidence_capture_rate,
        "null_metric_reasons": null_metric_reasons,
    }


def _has_pass_and_eligible_ingest(row) -> bool:
    execution = dict(row.execution_outcome_json or {})
    ingest = dict(execution.get("attempt_ingest_evaluation") or {})
    return (
        execution.get("pass_gate_status") == "pass"
        and ingest.get("ingest_status") == "eligible"
    )
