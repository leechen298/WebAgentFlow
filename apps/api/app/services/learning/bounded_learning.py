"""Bounded learning policy and terminal status helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.learning_batch import LearningBatchStatus
from app.schemas.learning_batch import BoundedLearningPolicy


@dataclass
class BoundedAttemptState:
    passed_count: int = 0
    failed_count: int = 0
    unverified_count: int = 0
    unsupported_count: int = 0
    skipped_count: int = 0
    timeout_occurred: bool = False
    cancellation_requested: bool = False
    consecutive_no_new_capability: int = 0
    adapter_failures: dict[str, int] = field(default_factory=dict)

    @property
    def useful_asset_count(self) -> int:
        return self.passed_count


def default_bounded_learning_policy() -> BoundedLearningPolicy:
    return BoundedLearningPolicy()


def apply_policy_to_scenarios(
    scenarios: list[Any],
    policy: BoundedLearningPolicy,
) -> list[Any]:
    selected: list[Any] = []
    for scenario in scenarios:
        if len(selected) >= policy.max_scenario_count:
            break
        kind = _scenario_kind(scenario)
        if kind == "all_supported_filters_smoke" and not policy.allow_all_supported_smoke:
            continue
        if kind == "pairwise_filter" and not policy.allow_dependency_pairs:
            continue
        selected.append(scenario)
    return selected


def should_stop_after_attempt(
    state: BoundedAttemptState,
    policy: BoundedLearningPolicy,
    *,
    adapter_type: str | None = None,
) -> bool:
    if state.consecutive_no_new_capability >= policy.max_consecutive_no_new_capability:
        return True
    if adapter_type:
        failures = state.adapter_failures.get(adapter_type, 0)
        if failures >= policy.max_failures_per_adapter:
            return True
    return False


def derive_batch_terminal_status(state: BoundedAttemptState) -> LearningBatchStatus:
    if state.useful_asset_count > 0 and (
        state.timeout_occurred or state.cancellation_requested
    ):
        return LearningBatchStatus.PARTIAL_SUCCESS
    if state.cancellation_requested:
        return LearningBatchStatus.CANCELLED
    if state.timeout_occurred:
        return LearningBatchStatus.TIMED_OUT
    if (
        state.passed_count > 0
        and state.failed_count == 0
        and state.unverified_count == 0
        and state.unsupported_count == 0
        and state.skipped_count == 0
    ):
        return LearningBatchStatus.COMPLETED
    if state.passed_count > 0:
        return LearningBatchStatus.PARTIAL_SUCCESS
    if state.unverified_count > 0:
        return LearningBatchStatus.UNVERIFIED
    return LearningBatchStatus.FAILED


def batch_summary_for_state(
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
) -> dict[str, Any]:
    return {
        "policy_version": policy.version,
        "planned_count": planned_count,
        "attempted_count": attempted_count,
        "passed_count": state.passed_count,
        "failed_count": state.failed_count,
        "unverified_count": state.unverified_count,
        "unsupported_count": state.unsupported_count,
        "skipped_count": state.skipped_count,
        "terminal_reason": terminal_reason,
        "timeout_occurred": state.timeout_occurred,
        "cancellation_requested": state.cancellation_requested,
        "warnings": warnings or [],
        "failed_scenarios": failed_scenarios or [],
        "unverified_scenarios": unverified_scenarios or [],
        "unsupported_scenarios": unsupported_scenarios or [],
    }


def _scenario_kind(scenario: Any) -> str:
    if isinstance(scenario, dict):
        return str(scenario.get("scenario_kind") or "")
    return str(getattr(scenario, "scenario_kind", "") or "")
