"""CompositionCandidate data access."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.composition_candidate import CompositionCandidate
from app.schemas.capability_composition_candidates import (
    CompositionCandidateGenerationRequest,
    CompositionCandidateStatus,
)

TERMINAL_CANDIDATE_STATUSES = frozenset(
    {
        CompositionCandidateStatus.PROMOTED_TO_LEARNED_PATH.value,
        CompositionCandidateStatus.NEGATIVE_EVIDENCE_RECORDED.value,
    }
)


def target_scope_ref(
    *,
    target_url: str,
    page_template: str,
    query_signature: dict[str, Any],
    dom_fingerprint: str | None,
) -> str:
    payload = json.dumps(
        {
            "target_url": target_url,
            "page_template": page_template,
            "query_signature": query_signature,
            "dom_fingerprint": dom_fingerprint,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"scope_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def compute_candidate_id(
    request: CompositionCandidateGenerationRequest,
    *,
    candidate_family: str,
    source_capability_ids: list[str],
    ordered_capability_kinds: list[str],
    expected_terminal_target: dict[str, Any],
) -> str:
    payload = json.dumps(
        {
            "target_scope_ref": target_scope_ref(
                target_url=request.target_url,
                page_template=request.page_template,
                query_signature=request.query_signature,
                dom_fingerprint=request.dom_fingerprint,
            ),
            "candidate_family": candidate_family,
            "source_capability_ids": source_capability_ids,
            "ordered_capability_kinds": ordered_capability_kinds,
            "expected_terminal_target": expected_terminal_target,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"candidate_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


class CompositionCandidateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_candidate_id(self, candidate_id: str) -> CompositionCandidate | None:
        stmt = (
            select(CompositionCandidate)
            .where(CompositionCandidate.candidate_id == candidate_id)
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def list_all(self) -> list[CompositionCandidate]:
        stmt = select(CompositionCandidate).order_by(CompositionCandidate.created_at.asc())
        return list(self.session.scalars(stmt).all())

    def list_for_bundle(
        self,
        *,
        learning_batch_id: str | None = None,
        target_scope_ref: str | None = None,
    ) -> list[CompositionCandidate]:
        stmt = select(CompositionCandidate)
        if learning_batch_id is not None:
            stmt = stmt.where(CompositionCandidate.learning_batch_id == learning_batch_id)
        if target_scope_ref is not None:
            stmt = stmt.where(CompositionCandidate.target_scope_ref == target_scope_ref)
        stmt = stmt.order_by(CompositionCandidate.created_at.asc())
        return list(self.session.scalars(stmt).all())

    def upsert_generated(
        self,
        request: CompositionCandidateGenerationRequest,
        *,
        candidate_family: str,
        source_capability_ids: list[str],
        ordered_capability_kinds: list[str],
        expected_terminal_target: dict[str, Any],
        generation_reason: str,
        status: CompositionCandidateStatus,
        static_rejection_reason: str | None = None,
        risk_level: str = "low",
        confidence: str = "high",
    ) -> CompositionCandidate:
        candidate_id = compute_candidate_id(
            request,
            candidate_family=candidate_family,
            source_capability_ids=source_capability_ids,
            ordered_capability_kinds=ordered_capability_kinds,
            expected_terminal_target=expected_terminal_target,
        )
        existing = self.get_by_candidate_id(candidate_id)
        if existing is not None:
            if existing.status in TERMINAL_CANDIDATE_STATUSES:
                return existing
            existing.target_url = request.target_url
            existing.status = status.value
            existing.static_rejection_reason = static_rejection_reason
            existing.generation_reason = generation_reason
            self.session.commit()
            self.session.refresh(existing)
            return existing

        row = CompositionCandidate(
            candidate_id=candidate_id,
            target_url=request.target_url,
            target_scope_ref=target_scope_ref(
                target_url=request.target_url,
                page_template=request.page_template,
                query_signature=request.query_signature,
                dom_fingerprint=request.dom_fingerprint,
            ),
            page_template=request.page_template,
            query_signature=dict(request.query_signature),
            dom_fingerprint=request.dom_fingerprint,
            candidate_family=candidate_family,
            source_capability_ids_json=list(source_capability_ids),
            ordered_capability_kinds_json=list(ordered_capability_kinds),
            expected_terminal_target_json=dict(expected_terminal_target),
            risk_level=risk_level,
            confidence=confidence,
            generation_reason=generation_reason,
            status=status.value,
            static_rejection_reason=static_rejection_reason,
            learning_batch_id=request.learning_batch_id,
            source_run_id=request.source_run_id,
        )
        self.session.add(row)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            existing = self.get_by_candidate_id(candidate_id)
            if existing is None:
                raise
            return existing
        self.session.refresh(row)
        return row

    def update_outcome(
        self,
        row: CompositionCandidate,
        *,
        status: CompositionCandidateStatus,
        execution_outcome: dict[str, Any] | None = None,
        promotion_decision: dict[str, Any] | None = None,
        negative_evidence: dict[str, Any] | None = None,
        promoted_learned_path_id: str | None = None,
    ) -> CompositionCandidate:
        row.status = status.value
        if execution_outcome is not None:
            row.execution_outcome_json = execution_outcome
        if promotion_decision is not None:
            row.promotion_decision_json = promotion_decision
        if negative_evidence is not None:
            row.negative_evidence_json = negative_evidence
        if promoted_learned_path_id is not None:
            row.promoted_learned_path_id = promoted_learned_path_id
        self.session.commit()
        self.session.refresh(row)
        return row
