"""Bounded automatic generation of capability composition candidates."""

from __future__ import annotations

import hashlib

from app.models.learned_capability import LearnedCapability
from app.repos.composition_candidates_repo import CompositionCandidateRepository
from app.repos.learned_capabilities_repo import LearnedCapabilityRepository
from app.schemas.capability_composition import CapabilityCompositionRequest
from app.schemas.capability_composition_candidates import (
    CompositionCandidateGenerationRequest,
    CompositionCandidateGenerationResult,
    CompositionCandidatePublic,
    CompositionCandidateStatus,
    CompositionCoverageMetrics,
)
from app.services.learning.capability_composer import CapabilityComposer
from app.services.learning.capability_graph import CapabilityGraphBuilder
from app.services.learning.composition_requirement_deriver import (
    FAMILY_REQUIRED_KINDS,
    CompositionRequirementDeriver,
)


class BoundedCompositionCandidateGenerator:
    def __init__(
        self,
        repo: CompositionCandidateRepository,
        *,
        capability_repo: LearnedCapabilityRepository | None = None,
        composer: CapabilityComposer | None = None,
        graph_builder: CapabilityGraphBuilder | None = None,
        requirement_deriver: CompositionRequirementDeriver | None = None,
        max_candidates_per_family: int = 1,
    ) -> None:
        self._repo = repo
        self._capability_repo = capability_repo
        self._composer = composer or CapabilityComposer()
        self._graph_builder = graph_builder or CapabilityGraphBuilder()
        self._requirement_deriver = requirement_deriver or CompositionRequirementDeriver()
        self._max_candidates_per_family = max_candidates_per_family

    def generate_for_scope(
        self,
        request: CompositionCandidateGenerationRequest,
    ) -> CompositionCandidateGenerationResult:
        if self._capability_repo is None:
            raise ValueError("capability_repo is required for page-scope generation")
        capabilities = self._capability_repo.list_for_page_scope(
            page_template=request.page_template,
            query_signature=request.query_signature,
            dom_fingerprint=request.dom_fingerprint,
            allowed_trust=None,
        )
        graph = self._graph_builder.build(
            page_template=request.page_template,
            query_signature=request.query_signature,
            dom_fingerprint=request.dom_fingerprint,
            capabilities=capabilities,
        )
        requirements = self._requirement_deriver.derive(
            user_goal=request.user_goal,
            graph=graph,
            requested_families=request.required_families or None,
        )
        scoped_request = request.model_copy(
            update={"required_families": requirements.required_families}
        )
        return self.generate(scoped_request, capabilities=capabilities)

    def generate(
        self,
        request: CompositionCandidateGenerationRequest,
        *,
        capabilities: list[LearnedCapability],
    ) -> CompositionCandidateGenerationResult:
        families = list(dict.fromkeys(request.required_families))
        public_candidates: list[CompositionCandidatePublic] = []
        private_capability_ids = [str(capability.id) for capability in capabilities]

        for family in families:
            required_kinds = FAMILY_REQUIRED_KINDS.get(family)
            if not required_kinds:
                public_candidates.append(
                    self._persist_static_rejection(
                        request,
                        family=family,
                        ordered_capability_kinds=[],
                        source_capability_ids=[],
                        expected_terminal_target={},
                        reason=f"unsupported candidate family: {family}",
                    )
                )
                continue

            composition_request = CapabilityCompositionRequest(
                target_url=request.target_url,
                page_template=request.page_template,
                query_signature=request.query_signature,
                user_goal=request.user_goal,
                required_capability_kinds=required_kinds,
                slot_bindings=request.slot_bindings,
                dom_fingerprint=request.dom_fingerprint,
            )
            result = self._composer.compose(
                composition_request,
                candidates=capabilities,
            )
            plan = result.plan
            if plan.status == "ready" and self._max_candidates_per_family > 0:
                row = self._repo.upsert_generated(
                    request,
                    candidate_family=family,
                    source_capability_ids=plan.source_capability_ids,
                    ordered_capability_kinds=[
                        step.capability_kind for step in plan.ordered_steps
                    ],
                    expected_terminal_target=plan.expected_terminal_target,
                    generation_reason="required family matched bounded capability graph",
                    status=CompositionCandidateStatus.READY_FOR_EXECUTION,
                    risk_level=plan.risk_level,
                    confidence=plan.confidence,
                )
                public_candidates.append(_public_from_row(row))
                continue

            rejection_detail = "; ".join(
                plan.rejection_reasons or plan.missing_capabilities
            )
            redacted_reason = _redact_capability_ids_in_reason(
                f"{plan.status}: {rejection_detail}",
                capability_ids=private_capability_ids,
            )
            public_candidates.append(
                self._persist_static_rejection(
                    request,
                    family=family,
                    ordered_capability_kinds=required_kinds,
                    source_capability_ids=plan.source_capability_ids,
                    expected_terminal_target=plan.expected_terminal_target,
                    reason=redacted_reason,
                )
            )

        ready_count = sum(
            1
            for candidate in public_candidates
            if candidate.status == CompositionCandidateStatus.READY_FOR_EXECUTION
        )
        requested_count = len(families)
        coverage = None if requested_count == 0 else ready_count / requested_count
        null_reasons = {}
        if requested_count == 0:
            null_reasons["required_family_coverage"] = "no required families requested"
        return CompositionCandidateGenerationResult(
            candidates=public_candidates,
            coverage=CompositionCoverageMetrics(
                requested_required_families=requested_count,
                generated_required_families=ready_count,
                generated_candidates=len(public_candidates),
                ready_for_execution_candidates=ready_count,
                required_family_coverage=coverage,
                null_metric_reasons=null_reasons,
            ),
        )

    def _persist_static_rejection(
        self,
        request: CompositionCandidateGenerationRequest,
        *,
        family: str,
        ordered_capability_kinds: list[str],
        source_capability_ids: list[str],
        expected_terminal_target: dict,
        reason: str,
    ) -> CompositionCandidatePublic:
        row = self._repo.upsert_generated(
            request,
            candidate_family=family,
            source_capability_ids=source_capability_ids,
            ordered_capability_kinds=ordered_capability_kinds,
            expected_terminal_target=expected_terminal_target,
            generation_reason="static composition candidate rejected",
            status=CompositionCandidateStatus.REJECTED_STATIC,
            static_rejection_reason=reason,
            risk_level="medium",
            confidence="low",
        )
        return _public_from_row(row)


def _public_from_row(row) -> CompositionCandidatePublic:
    return CompositionCandidatePublic(
        candidate_id=row.candidate_id,
        target_scope_ref=row.target_scope_ref,
        page_template=row.page_template,
        candidate_family=row.candidate_family,
        source_capability_refs=[
            _opaque_ref("cap", str(source_id))
            for source_id in row.source_capability_ids_json or []
        ],
        ordered_capability_kinds=list(row.ordered_capability_kinds_json or []),
        expected_terminal_target=dict(row.expected_terminal_target_json or {}),
        risk_level=row.risk_level,
        confidence=row.confidence,
        generation_reason=row.generation_reason,
        status=CompositionCandidateStatus(row.status),
        static_rejection_reason=row.static_rejection_reason,
    )


def _redact_capability_ids_in_reason(reason: str, *, capability_ids: list[str]) -> str:
    redacted = reason
    for capability_id in sorted(set(capability_ids), key=len, reverse=True):
        if capability_id:
            redacted = redacted.replace(capability_id, "redacted_ref")
    return redacted


def _opaque_ref(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_ref_{digest}"
