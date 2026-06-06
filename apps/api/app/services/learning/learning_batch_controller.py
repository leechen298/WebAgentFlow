"""Controller for bounded learning batch lifecycle."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.models.learning_batch import LearningBatch, LearningBatchStatus
from app.repos.learning_batches_repo import LearningBatchRepository
from app.schemas.learning_batch import BoundedLearningPolicy
from app.services.learning.bounded_learning import (
    BoundedAttemptState,
    batch_summary_for_state,
    derive_batch_terminal_status,
)

Clock = Callable[[], float]
CancelChecker = Callable[[str], bool]


@dataclass(frozen=True)
class BatchBoundaryState:
    should_stop: bool
    reason: str | None = None


class LearningBatchController:
    def __init__(
        self,
        repo: LearningBatchRepository,
        *,
        clock: Clock | None = None,
        cancel_checker: CancelChecker | None = None,
    ) -> None:
        self._repo = repo
        self._clock = clock or time.monotonic
        self._cancel_checker = cancel_checker

    def create_pending(
        self,
        *,
        target_url: str,
        session_id: str | None,
        policy: BoundedLearningPolicy,
        request_json: dict[str, Any],
    ) -> LearningBatch:
        return self._repo.create_pending(
            target_url=target_url,
            session_id=session_id,
            policy_json=policy.model_dump(mode="json"),
            request_json=request_json,
        )

    def now(self) -> float:
        return self._clock()

    def mark_running(
        self,
        batch_id: str,
        *,
        page_template: str | None = None,
        query_signature: dict[str, Any] | None = None,
        dom_fingerprint: str | None = None,
        planned_scenarios: list[dict[str, Any]] | None = None,
    ) -> LearningBatch:
        return self._repo.mark_running(
            batch_id,
            page_template=page_template,
            query_signature=query_signature,
            dom_fingerprint=dom_fingerprint,
            planned_scenarios=planned_scenarios,
        )

    def boundary_state(
        self,
        batch_id: str,
        *,
        started_monotonic: float,
        policy: BoundedLearningPolicy,
        state: BoundedAttemptState,
    ) -> BatchBoundaryState:
        batch = self._repo.get(batch_id, fresh=True)
        if batch is None:
            raise ValueError(f"learning batch not found: {batch_id}")
        if batch.status == LearningBatchStatus.CANCEL_REQUESTED or (
            self._cancel_checker is not None and self._cancel_checker(batch_id)
        ):
            state.cancellation_requested = True
            return BatchBoundaryState(True, "cancel_requested")
        elapsed = self._clock() - started_monotonic
        if elapsed >= policy.max_wall_clock_seconds:
            state.timeout_occurred = True
            return BatchBoundaryState(True, "timed_out")
        return BatchBoundaryState(False)

    def append_run(self, batch_id: str, run_id: str) -> LearningBatch:
        return self._repo.append_run(batch_id, run_id)

    def append_capability(self, batch_id: str, capability_id: str) -> LearningBatch:
        return self._repo.append_capability(batch_id, capability_id)

    def append_learned_path(self, batch_id: str, learned_path_id: str) -> LearningBatch:
        return self._repo.append_learned_path(batch_id, learned_path_id)

    def close(
        self,
        batch_id: str,
        *,
        state: BoundedAttemptState,
        policy: BoundedLearningPolicy,
        planned_count: int,
        attempted_count: int,
        terminal_reason: str | None = None,
        warnings: list[str] | None = None,
        failed_scenarios: list[dict[str, Any]] | None = None,
        unverified_scenarios: list[dict[str, Any]] | None = None,
        unsupported_scenarios: list[dict[str, Any]] | None = None,
        created_run_ids: list[str] | None = None,
        created_capability_ids: list[str] | None = None,
        created_learned_path_ids: list[str] | None = None,
    ) -> LearningBatch:
        status = derive_batch_terminal_status(state)
        summary = batch_summary_for_state(
            state=state,
            policy=policy,
            planned_count=planned_count,
            attempted_count=attempted_count,
            terminal_reason=terminal_reason,
            warnings=warnings,
            failed_scenarios=failed_scenarios,
            unverified_scenarios=unverified_scenarios,
            unsupported_scenarios=unsupported_scenarios,
        )
        return self._repo.mark_terminal(
            batch_id,
            status,
            summary=summary,
            created_run_ids=created_run_ids,
            created_capability_ids=created_capability_ids,
            created_learned_path_ids=created_learned_path_ids,
        )
