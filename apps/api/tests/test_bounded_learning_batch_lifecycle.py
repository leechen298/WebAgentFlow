"""Tests for bounded learning policy and batch controller."""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.models.learning_batch import LearningBatchStatus
from app.repos.learning_batches_repo import LearningBatchRepository
from app.schemas.learning_batch import BoundedLearningPolicy
from app.services.learning.bounded_learning import (
    BoundedAttemptState,
    apply_policy_to_scenarios,
    default_bounded_learning_policy,
    derive_batch_terminal_status,
    should_stop_after_attempt,
)
from app.services.learning.learning_batch_controller import LearningBatchController


def test_default_policy_has_finite_budget_values() -> None:
    policy = default_bounded_learning_policy()

    assert policy.version == "bounded_learning_policy.v1"
    assert policy.max_scenario_count > 0
    assert policy.max_wall_clock_seconds > 0
    assert policy.allow_dependency_pairs is False
    assert policy.allow_all_supported_smoke is False


def test_policy_truncates_scenarios_and_skips_expansions_by_default() -> None:
    policy = BoundedLearningPolicy(max_scenario_count=2)
    scenarios = [
        {"scenario_id": "a", "scenario_kind": "single_filter"},
        {"scenario_id": "b", "scenario_kind": "all_supported_filters_smoke"},
        {"scenario_id": "c", "scenario_kind": "pairwise_filter"},
        {"scenario_id": "d", "scenario_kind": "single_filter"},
    ]

    selected = apply_policy_to_scenarios(scenarios, policy)

    assert [item["scenario_id"] for item in selected] == ["a", "d"]


def test_policy_can_enable_dependency_pairs() -> None:
    policy = BoundedLearningPolicy(allow_dependency_pairs=True)
    scenarios = [
        {"scenario_id": "a", "scenario_kind": "single_filter"},
        {"scenario_id": "b", "scenario_kind": "pairwise_filter"},
    ]

    selected = apply_policy_to_scenarios(scenarios, policy)

    assert [item["scenario_id"] for item in selected] == ["a", "b"]


def test_should_stop_after_attempt_uses_failure_and_no_new_thresholds() -> None:
    policy = BoundedLearningPolicy(
        max_failures_per_adapter=1,
        max_consecutive_no_new_capability=2,
    )

    assert should_stop_after_attempt(
        BoundedAttemptState(adapter_failures={"input": 1}),
        policy,
        adapter_type="input",
    )
    assert should_stop_after_attempt(
        BoundedAttemptState(consecutive_no_new_capability=2),
        policy,
    )
    assert not should_stop_after_attempt(BoundedAttemptState(), policy)


def test_terminal_status_derivation_is_consistent() -> None:
    assert (
        derive_batch_terminal_status(BoundedAttemptState(passed_count=2))
        == LearningBatchStatus.COMPLETED
    )
    assert (
        derive_batch_terminal_status(
            BoundedAttemptState(passed_count=1, failed_count=1)
        )
        == LearningBatchStatus.PARTIAL_SUCCESS
    )
    assert (
        derive_batch_terminal_status(BoundedAttemptState(unverified_count=1))
        == LearningBatchStatus.UNVERIFIED
    )
    assert (
        derive_batch_terminal_status(BoundedAttemptState(timeout_occurred=True))
        == LearningBatchStatus.TIMED_OUT
    )
    assert (
        derive_batch_terminal_status(
            BoundedAttemptState(passed_count=1, timeout_occurred=True)
        )
        == LearningBatchStatus.PARTIAL_SUCCESS
    )
    assert (
        derive_batch_terminal_status(BoundedAttemptState(cancellation_requested=True))
        == LearningBatchStatus.CANCELLED
    )
    assert (
        derive_batch_terminal_status(
            BoundedAttemptState(passed_count=1, cancellation_requested=True)
        )
        == LearningBatchStatus.PARTIAL_SUCCESS
    )
    assert derive_batch_terminal_status(BoundedAttemptState()) == LearningBatchStatus.FAILED


def test_controller_fake_clock_timeout_closes_batch(db_session: Session) -> None:
    now = 100.0
    repo = LearningBatchRepository(db_session)
    controller = LearningBatchController(repo, clock=lambda: now)
    policy = BoundedLearningPolicy(max_wall_clock_seconds=5)
    batch = controller.create_pending(
        target_url="https://example.test/search",
        session_id="session-1",
        policy=policy,
        request_json={},
    )
    controller.mark_running(batch.id)
    state = BoundedAttemptState()

    boundary = controller.boundary_state(
        batch.id,
        started_monotonic=90.0,
        policy=policy,
        state=state,
    )
    closed = controller.close(
        batch.id,
        state=state,
        policy=policy,
        planned_count=3,
        attempted_count=0,
        terminal_reason=boundary.reason,
    )

    assert boundary.should_stop is True
    assert boundary.reason == "timed_out"
    assert closed.status == LearningBatchStatus.TIMED_OUT
    assert closed.summary_json["timeout_occurred"] is True


def test_controller_fake_cancel_checker_closes_batch(db_session: Session) -> None:
    repo = LearningBatchRepository(db_session)
    controller = LearningBatchController(repo, cancel_checker=lambda _batch_id: True)
    policy = BoundedLearningPolicy()
    batch = controller.create_pending(
        target_url="https://example.test/search",
        session_id="session-1",
        policy=policy,
        request_json={},
    )
    controller.mark_running(batch.id)
    state = BoundedAttemptState()

    boundary = controller.boundary_state(
        batch.id,
        started_monotonic=0.0,
        policy=policy,
        state=state,
    )
    closed = controller.close(
        batch.id,
        state=state,
        policy=policy,
        planned_count=3,
        attempted_count=0,
        terminal_reason=boundary.reason,
    )

    assert boundary.should_stop is True
    assert boundary.reason == "cancel_requested"
    assert closed.status == LearningBatchStatus.CANCELLED
    assert closed.summary_json["cancellation_requested"] is True


def test_controller_boundary_state_refreshes_cross_session_cancel(
    db_session: Session,
) -> None:
    repo = LearningBatchRepository(db_session)
    controller = LearningBatchController(repo)
    policy = BoundedLearningPolicy()
    batch = controller.create_pending(
        target_url="https://example.test/search",
        session_id="session-1",
        policy=policy,
        request_json={},
    )
    controller.mark_running(batch.id)
    other_session_factory = sessionmaker(bind=db_session.get_bind())
    with other_session_factory() as other_session:
        LearningBatchRepository(other_session).request_cancel(
            batch.id, reason="operator_cancel"
        )
    state = BoundedAttemptState()

    boundary = controller.boundary_state(
        batch.id,
        started_monotonic=0.0,
        policy=policy,
        state=state,
    )

    assert boundary.should_stop is True
    assert boundary.reason == "cancel_requested"
    assert state.cancellation_requested is True


def test_controller_cancel_after_passed_asset_is_partial_success(
    db_session: Session,
) -> None:
    repo = LearningBatchRepository(db_session)
    controller = LearningBatchController(repo, cancel_checker=lambda _batch_id: True)
    policy = BoundedLearningPolicy()
    batch = controller.create_pending(
        target_url="https://example.test/search",
        session_id="session-1",
        policy=policy,
        request_json={},
    )
    controller.mark_running(batch.id)
    state = BoundedAttemptState(passed_count=1)

    boundary = controller.boundary_state(
        batch.id,
        started_monotonic=0.0,
        policy=policy,
        state=state,
    )
    closed = controller.close(
        batch.id,
        state=state,
        policy=policy,
        planned_count=3,
        attempted_count=1,
        terminal_reason=boundary.reason,
        created_capability_ids=["cap-1"],
    )

    assert closed.status == LearningBatchStatus.PARTIAL_SUCCESS
    assert closed.summary_json["cancellation_requested"] is True
    assert closed.created_capability_ids_json == ["cap-1"]
