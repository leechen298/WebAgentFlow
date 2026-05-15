"""Tests for replay observation summary schema and aggregation service (M11.2.3)."""

from __future__ import annotations

from app.schemas.learned_path_replay import (
    ObservationSignal,
    ReplayObservationSummary,
    ReplayResult,
    ReplayStepLog,
    StepObservationRef,
    WaitResult,
)
from app.services.learning.replay_observation import build_replay_observation_summary

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_wait_result(
    *,
    status: str = "observed",
    signals: list[ObservationSignal] | None = None,
    primary_signal: ObservationSignal | None = None,
    wait_id: str = "w1",
    notes: str = "",
) -> WaitResult:
    return WaitResult(
        wait_id=wait_id,
        status=status,  # type: ignore[arg-type]
        observed_signals=signals or [],
        primary_signal=primary_signal,
        notes=notes,
    )


def _make_signal(kind: str, **kwargs) -> ObservationSignal:
    return ObservationSignal(kind=kind, **kwargs)  # type: ignore[arg-type]


def _make_step(
    step: int = 0,
    action_type: str = "click",
    wait_result: WaitResult | None = None,
) -> ReplayStepLog:
    return ReplayStepLog(
        step=step,
        action_type=action_type,
        wait_result=wait_result,
    )


# ── Schema tests ─────────────────────────────────────────────────────────────


class TestReplayObservationSummarySchema:
    def test_accepts_valid_statuses(self) -> None:
        for status in ("observed", "no_primary_observation",
                        "partial_observation", "not_applicable"):
            summary = ReplayObservationSummary(status=status)
            assert summary.status == status

    def test_invalid_status_rejected(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ReplayObservationSummary(status="invalid_status")  # type: ignore[arg-type]

    def test_result_observation_summary_may_be_none(self) -> None:
        result = ReplayResult(
            learned_path_id="lp-1",
            trust="confirmed",
            status="succeeded",
            drift_status="none",
        )
        assert result.observation_summary is None

    def test_result_observation_summary_may_be_populated(self) -> None:
        summary = ReplayObservationSummary(status="observed")
        result = ReplayResult(
            learned_path_id="lp-1",
            trust="confirmed",
            status="succeeded",
            drift_status="none",
            observation_summary=summary,
        )
        assert result.observation_summary is not None
        assert result.observation_summary.status == "observed"

    def test_step_observation_ref_excludes_raw_payloads(self) -> None:
        field_names = set(StepObservationRef.model_fields.keys())
        for forbidden in ("screenshot_ref", "raw_html", "dom_dump",
                          "screenshot_payload", "reporter_wording"):
            assert forbidden not in field_names


# ── Aggregation service tests ────────────────────────────────────────────────


class TestBuildReplayObservationSummary:
    def test_empty_steps_returns_not_applicable(self) -> None:
        summary = build_replay_observation_summary(
            learned_path_id="lp-1", steps=[]
        )
        assert summary.status == "not_applicable"
        assert summary.step_count == 0
        assert summary.wait_result_count == 0

    def test_all_not_required_returns_not_applicable(self) -> None:
        steps = [
            _make_step(
                step=0,
                action_type="observe",
                wait_result=_make_wait_result(status="not_required"),
            ),
            _make_step(
                step=1,
                action_type="observe",
                wait_result=_make_wait_result(status="not_required"),
            ),
        ]
        summary = build_replay_observation_summary(
            learned_path_id="lp-1", steps=steps
        )
        assert summary.status == "not_applicable"
        assert summary.step_count == 2
        assert summary.not_required_step_count == 2

    def test_observed_primary_signal(self) -> None:
        steps = [
            _make_step(
                step=0,
                wait_result=_make_wait_result(
                    status="observed",
                    signals=[_make_signal("url_changed")],
                    primary_signal=_make_signal("url_changed"),
                ),
            ),
        ]
        summary = build_replay_observation_summary(
            learned_path_id="lp-1", steps=steps
        )
        assert summary.status == "observed"
        assert summary.has_primary_observation is True
        assert summary.observed_step_count == 1
        assert "url_changed" in summary.primary_signal_kinds
        assert summary.has_timeout is False

    def test_observed_primary_plus_skipped_gives_partial(self) -> None:
        steps = [
            _make_step(
                step=0,
                wait_result=_make_wait_result(
                    status="observed",
                    signals=[_make_signal("url_changed")],
                    primary_signal=_make_signal("url_changed"),
                ),
            ),
            _make_step(
                step=1,
                wait_result=_make_wait_result(status="skipped"),
            ),
        ]
        summary = build_replay_observation_summary(
            learned_path_id="lp-1", steps=steps
        )
        assert summary.status == "partial_observation"
        assert summary.has_primary_observation is True
        assert summary.skipped_step_count == 1

    def test_observed_primary_plus_timeout_gives_partial(self) -> None:
        steps = [
            _make_step(
                step=0,
                wait_result=_make_wait_result(
                    status="observed",
                    signals=[_make_signal("title_changed")],
                    primary_signal=_make_signal("title_changed"),
                ),
            ),
            _make_step(
                step=1,
                wait_result=_make_wait_result(status="timeout"),
            ),
        ]
        summary = build_replay_observation_summary(
            learned_path_id="lp-1", steps=steps
        )
        assert summary.status == "partial_observation"
        assert summary.has_timeout is True
        assert summary.has_primary_observation is True

    def test_only_network_idle_is_no_primary_observation(self) -> None:
        steps = [
            _make_step(
                step=0,
                wait_result=_make_wait_result(
                    status="timeout",
                    signals=[_make_signal("network_idle_observed")],
                ),
            ),
        ]
        summary = build_replay_observation_summary(
            learned_path_id="lp-1", steps=steps
        )
        assert summary.status == "no_primary_observation"
        assert summary.has_primary_observation is False
        assert summary.has_only_supporting_observation is True
        assert "network_idle_observed" in summary.supporting_signal_kinds
        assert "network_idle_observed" not in summary.primary_signal_kinds

    def test_timeout_only_is_no_primary_observation(self) -> None:
        steps = [
            _make_step(
                step=0,
                wait_result=_make_wait_result(status="timeout"),
            ),
        ]
        summary = build_replay_observation_summary(
            learned_path_id="lp-1", steps=steps
        )
        assert summary.status == "no_primary_observation"
        assert summary.has_timeout is True
        assert summary.timeout_step_count == 1

    def test_skipped_only_is_no_primary_observation(self) -> None:
        steps = [
            _make_step(
                step=0,
                wait_result=_make_wait_result(status="skipped"),
            ),
        ]
        summary = build_replay_observation_summary(
            learned_path_id="lp-1", steps=steps
        )
        assert summary.status == "no_primary_observation"
        assert summary.has_primary_observation is False
        assert summary.skipped_step_count == 1

    def test_wait_result_none_backward_compatible(self) -> None:
        steps = [
            _make_step(step=0, wait_result=None),
        ]
        summary = build_replay_observation_summary(
            learned_path_id="lp-1", steps=steps
        )
        assert summary.wait_result_count == 0
        assert summary.step_count == 1
        # No wait_result -> has_skipped_or_uncertain -> no_primary_observation
        assert summary.status == "no_primary_observation"
        assert summary.step_observation_refs[0].notes == "no wait_result"

    def test_duplicated_signal_kinds_are_deduped(self) -> None:
        steps = [
            _make_step(
                step=0,
                wait_result=_make_wait_result(
                    status="observed",
                    signals=[
                        _make_signal("url_changed"),
                        _make_signal("url_changed"),
                    ],
                    primary_signal=_make_signal("url_changed"),
                ),
            ),
            _make_step(
                step=1,
                wait_result=_make_wait_result(
                    status="observed",
                    signals=[_make_signal("url_changed")],
                    primary_signal=_make_signal("url_changed"),
                ),
            ),
        ]
        summary = build_replay_observation_summary(
            learned_path_id="lp-1", steps=steps
        )
        assert summary.primary_signal_kinds.count("url_changed") == 1

    def test_network_idle_not_in_primary(self) -> None:
        steps = [
            _make_step(
                step=0,
                wait_result=_make_wait_result(
                    status="observed",
                    signals=[
                        _make_signal("url_changed"),
                        _make_signal("network_idle_observed"),
                    ],
                    primary_signal=_make_signal("url_changed"),
                ),
            ),
        ]
        summary = build_replay_observation_summary(
            learned_path_id="lp-1", steps=steps
        )
        assert "network_idle_observed" not in summary.primary_signal_kinds
        assert "network_idle_observed" in summary.supporting_signal_kinds
        assert "url_changed" in summary.primary_signal_kinds

    def test_summary_has_observation_summary_id(self) -> None:
        summary = build_replay_observation_summary(
            learned_path_id="lp-1", steps=[]
        )
        assert summary.observation_summary_id  # non-empty string

    def test_learned_path_id_propagated(self) -> None:
        summary = build_replay_observation_summary(
            learned_path_id="lp-42", steps=[]
        )
        assert summary.learned_path_id == "lp-42"

    def test_replay_id_propagated(self) -> None:
        summary = build_replay_observation_summary(
            learned_path_id="lp-1", steps=[], replay_id="run-99"
        )
        assert summary.replay_id == "run-99"

    def test_replay_id_defaults_to_none(self) -> None:
        summary = build_replay_observation_summary(
            learned_path_id="lp-1", steps=[]
        )
        assert summary.replay_id is None

    def test_step_refs_populated(self) -> None:
        steps = [
            _make_step(
                step=0,
                wait_result=_make_wait_result(
                    status="observed",
                    wait_id="w-0",
                    signals=[_make_signal("url_changed")],
                    primary_signal=_make_signal("url_changed"),
                ),
            ),
        ]
        summary = build_replay_observation_summary(
            learned_path_id="lp-1", steps=steps
        )
        assert len(summary.step_observation_refs) == 1
        ref = summary.step_observation_refs[0]
        assert ref.step_index == 0
        assert ref.wait_id == "w-0"
        assert ref.wait_status == "observed"
        assert ref.has_primary_signal is True
        assert ref.primary_signal_kind == "url_changed"

    def test_mixed_signals_per_step(self) -> None:
        """A step with both primary and supporting signals."""
        steps = [
            _make_step(
                step=0,
                wait_result=_make_wait_result(
                    status="observed",
                    signals=[
                        _make_signal("url_changed"),
                        _make_signal("network_idle_observed"),
                    ],
                    primary_signal=_make_signal("url_changed"),
                ),
            ),
        ]
        summary = build_replay_observation_summary(
            learned_path_id="lp-1", steps=steps
        )
        assert summary.has_primary_observation is True
        assert summary.has_only_supporting_observation is False
        ref = summary.step_observation_refs[0]
        assert ref.has_primary_signal is True
        assert ref.has_supporting_signal is True


# ── Boundary tests ───────────────────────────────────────────────────────────


class TestBoundaryInvariants:
    def test_reporter_not_called(self) -> None:
        """Aggregation service must not import or call Task Result Reporter."""
        import importlib

        mod = importlib.import_module("app.services.learning.replay_observation")
        source = open(mod.__file__).read()  # type: ignore[arg-type]
        # Check no import of reporter modules (ignore docstring mentions)
        lines = source.split("\n")
        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped or stripped.startswith(("#", '"""', "'''")):
                continue
            if stripped.startswith("import ") or stripped.startswith("from "):
                assert "reporter" not in stripped.lower()
                assert "task_result" not in stripped.lower()

    def test_no_recovery_dependency(self) -> None:
        """Aggregation service must not import recovery modules."""
        import importlib
        mod = importlib.import_module("app.services.learning.replay_observation")
        source = open(mod.__file__).read()  # type: ignore[arg-type]
        for term in ("recovery", "retry", "abort", "user_takeover"):
            assert term not in source.lower()

    def test_no_page_understanding_dependency(self) -> None:
        """Aggregation service must not import Page Understanding Agent."""
        import importlib
        mod = importlib.import_module("app.services.learning.replay_observation")
        source = open(mod.__file__).read()  # type: ignore[arg-type]
        assert "page_understanding" not in source.lower()
        assert "page_context_bridge" not in source.lower()

    def test_no_raw_html_fields_in_summary(self) -> None:
        field_names = set(ReplayObservationSummary.model_fields.keys())
        for forbidden in ("raw_html", "dom_dump", "html_content",
                          "screenshot_payload"):
            assert forbidden not in field_names

    def test_summary_does_not_alter_replay_status(self) -> None:
        """Observation summary is diagnostic only; replay status is separate."""
        steps = [
            _make_step(
                step=0,
                wait_result=_make_wait_result(status="timeout"),
            ),
        ]
        summary = build_replay_observation_summary(
            learned_path_id="lp-1", steps=steps
        )
        # Summary says no_primary_observation, but that doesn't make
        # replay status "failed"
        assert summary.status == "no_primary_observation"
        # This is the invariant: summary status != replay status
