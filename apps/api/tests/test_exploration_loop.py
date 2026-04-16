"""Tests for app.services.learning.exploration_loop.

All Playwright / ExecutionRuntime interactions are mocked.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.schemas.execution import ExecutionResult
from app.schemas.exploration_run import ExplorationResult, ExplorationStepLog
from app.schemas.observation import PostActionObservation
from app.schemas.success_criteria import SuccessCondition
from app.schemas.task_definition import (
    TaskDefinition,
    TaskStep,
    TaskStepHint,
    TaskStepSuccessCriteria,
)
from app.services.learning.exploration_loop import (
    _capture_before_state,
    _execute_step,
    _observe_only_step,
    run_exploration,
)


# ───────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────

def _make_runtime(
    *,
    url: str = "https://example.com",
    title: str = "Example",
    html: str = "<html><body>hello</body></html>",
    screenshot_path: str = "/tmp/shot.png",
) -> MagicMock:
    """Create a mock ExecutionRuntime with sensible defaults."""
    runtime = MagicMock()
    runtime.current_url.return_value = url
    runtime.current_title.return_value = title
    runtime.current_html.return_value = html
    runtime.screenshot.return_value = screenshot_path
    return runtime


def _make_task(
    *,
    task_id: str = "test-task",
    name: str = "Test Task",
    target_url: str = "https://example.com",
    steps: list[TaskStep] | None = None,
    variables: dict | None = None,
    global_success_criteria: TaskStepSuccessCriteria | None = None,
) -> TaskDefinition:
    """Build a minimal TaskDefinition for testing."""
    return TaskDefinition(
        id=task_id,
        name=name,
        target_url=target_url,
        steps=steps or [],
        variables=variables or {},
        global_success_criteria=global_success_criteria,
    )


def _make_step(
    *,
    intent: str = "click_button",
    action_type: str = "click",
    value: str | None = None,
    value_from: str | None = None,
    target_hint: TaskStepHint | None = None,
    success_criteria: TaskStepSuccessCriteria | None = None,
) -> TaskStep:
    return TaskStep(
        intent=intent,
        action_type=action_type,
        value=value,
        value_from=value_from,
        target_hint=target_hint,
        success_criteria=success_criteria,
    )


def _make_execution_result(
    *,
    ok: bool = True,
    action_type: str = "click",
    target_summary: str = "button",
    error: str | None = None,
    observation: dict | None = None,
) -> ExecutionResult:
    """Build a mock ExecutionResult."""
    result = ExecutionResult(
        ok=ok,
        action_type=action_type,
        target_summary=target_summary,
        error=error,
    )
    if observation is not None:
        result.observation = observation
    elif ok:
        # Provide a default observation for successful results
        result.observation = {
            "url": "https://example.com/after",
            "title": "After",
            "url_changed": True,
            "title_changed": True,
            "html_changed": True,
            "html_hash": "abc123",
            "timestamp_ms": 1000,
        }
    return result


# ───────────────────────────────────────────────────────────────────
# _capture_before_state
# ───────────────────────────────────────────────────────────────────

class TestCaptureBeforeState:
    """Tests for _capture_before_state."""

    def test_captures_url_title_html_hash(self):
        runtime = _make_runtime(
            url="https://example.com/page",
            title="Page Title",
            html="<html>content</html>",
        )
        state = _capture_before_state(runtime)

        assert state["url"] == "https://example.com/page"
        assert state["title"] == "Page Title"
        assert state["html_hash"] != ""  # non-empty md5 hex digest

    def test_html_hash_is_md5_hex(self):
        import hashlib

        html = "<html>content</html>"
        runtime = _make_runtime(html=html)
        state = _capture_before_state(runtime)

        expected_hash = hashlib.md5(html.encode()).hexdigest()
        assert state["html_hash"] == expected_hash

    def test_returns_empty_values_when_runtime_raises(self):
        runtime = MagicMock()
        runtime.current_url.side_effect = RuntimeError("browser crashed")
        runtime.current_title.side_effect = RuntimeError("browser crashed")
        runtime.current_html.side_effect = RuntimeError("browser crashed")

        state = _capture_before_state(runtime)

        assert state["url"] == ""
        assert state["title"] == ""
        assert state["html_hash"] == ""

    def test_partial_failure_preserves_successful_fields(self):
        runtime = MagicMock()
        runtime.current_url.return_value = "https://example.com"
        runtime.current_title.side_effect = RuntimeError("no title")
        runtime.current_html.return_value = "<html></html>"

        state = _capture_before_state(runtime)

        assert state["url"] == "https://example.com"
        assert state["title"] == ""
        assert state["html_hash"] != ""


# ───────────────────────────────────────────────────────────────────
# _observe_only_step
# ───────────────────────────────────────────────────────────────────

class TestObserveOnlyStep:
    """Tests for _observe_only_step."""

    def test_builds_observation_from_current_state(self):
        runtime = _make_runtime(
            url="https://example.com/results",
            title="Results",
            html="<html>results</html>",
        )
        step = _make_step(intent="check_results", action_type="observe")
        before_state = {"url": "https://example.com", "title": "Home", "html_hash": "old"}

        log = _observe_only_step(
            step=step,
            runtime=runtime,
            variables={},
            before_state=before_state,
            step_index=0,
            ts_start=1000,
        )

        assert log.action_type == "observe"
        assert log.target_summary == "(observation only)"
        assert log.observation is not None
        assert log.observation.url == "https://example.com/results"
        assert log.observation.title == "Results"
        assert log.observation.url_changed is True
        assert log.observation.title_changed is True
        assert log.timestamp_ms == 1000

    def test_no_url_change_detected_when_same(self):
        runtime = _make_runtime(url="https://same.com", title="Same")
        step = _make_step(intent="verify", action_type="observe")
        before_state = {"url": "https://same.com", "title": "Same", "html_hash": ""}

        import hashlib
        html_hash = hashlib.md5(runtime.current_html().encode()).hexdigest()
        before_state["html_hash"] = html_hash

        log = _observe_only_step(
            step=step,
            runtime=runtime,
            variables={},
            before_state=before_state,
            step_index=0,
            ts_start=500,
        )

        assert log.observation is not None
        assert log.observation.url_changed is False
        assert log.observation.title_changed is False
        assert log.observation.html_changed is False

    def test_evaluates_success_criteria(self):
        runtime = _make_runtime(
            url="https://example.com/search?q=test",
            title="Search Results",
        )
        step = _make_step(
            intent="verify_search",
            action_type="observe",
            success_criteria=TaskStepSuccessCriteria(
                conditions=[
                    SuccessCondition(type="url_contains", value="search"),
                ],
            ),
        )
        before_state = {"url": "https://example.com", "title": "Home", "html_hash": ""}

        log = _observe_only_step(
            step=step,
            runtime=runtime,
            variables={},
            before_state=before_state,
            step_index=1,
            ts_start=2000,
        )

        assert log.success_evaluation is not None
        assert log.success_evaluation.satisfied is True

    def test_no_success_criteria_means_no_evaluation(self):
        runtime = _make_runtime()
        step = _make_step(intent="just_look", action_type="observe")
        before_state = {"url": "", "title": "", "html_hash": ""}

        log = _observe_only_step(
            step=step,
            runtime=runtime,
            variables={},
            before_state=before_state,
            step_index=0,
            ts_start=0,
        )

        assert log.success_evaluation is None

    def test_agent_note_includes_satisfied_status(self):
        runtime = _make_runtime(url="https://example.com/done")
        step = _make_step(
            intent="verify_done",
            action_type="observe",
            success_criteria=TaskStepSuccessCriteria(
                conditions=[SuccessCondition(type="url_contains", value="done")],
            ),
        )
        before_state = {"url": "", "title": "", "html_hash": ""}

        log = _observe_only_step(
            step=step,
            runtime=runtime,
            variables={},
            before_state=before_state,
            step_index=0,
            ts_start=0,
        )

        assert "satisfied=True" in log.agent_note

    def test_runtime_failures_produce_empty_strings(self):
        runtime = MagicMock()
        runtime.current_url.side_effect = RuntimeError("crash")
        runtime.current_title.side_effect = RuntimeError("crash")
        runtime.current_html.side_effect = RuntimeError("crash")

        step = _make_step(intent="observe_broken", action_type="observe")
        before_state = {"url": "", "title": "", "html_hash": ""}

        log = _observe_only_step(
            step=step,
            runtime=runtime,
            variables={},
            before_state=before_state,
            step_index=0,
            ts_start=0,
        )

        assert log.observation is not None
        assert log.observation.url == ""
        assert log.observation.title == ""


# ───────────────────────────────────────────────────────────────────
# _execute_step
# ───────────────────────────────────────────────────────────────────

class TestExecuteStep:
    """Tests for _execute_step."""

    @patch("app.services.execution.run_single_action.run_single_action")
    def test_calls_run_single_action_with_correct_args(self, mock_run):
        mock_run.return_value = _make_execution_result()
        runtime = _make_runtime()
        hint = TaskStepHint(role="textbox", placeholder="Search")
        step = _make_step(
            intent="fill_search",
            action_type="fill",
            value="hello",
            target_hint=hint,
        )

        _execute_step(step, runtime, variables={}, step_index=0)

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs["action_type"] == "fill"
        assert call_kwargs.kwargs["runtime"] is runtime
        assert call_kwargs.kwargs["value"] == "hello"
        assert call_kwargs.kwargs["target_hint"] is hint

    @patch("app.services.execution.run_single_action.run_single_action")
    def test_resolves_value_from_variables(self, mock_run):
        mock_run.return_value = _make_execution_result(action_type="fill")
        runtime = _make_runtime()
        step = _make_step(
            intent="fill_query",
            action_type="fill",
            value="static_fallback",
            value_from="query",
        )

        log = _execute_step(
            step, runtime, variables={"query": "dynamic_value"}, step_index=0,
        )

        # value_from should override static value
        assert mock_run.call_args.kwargs["value"] == "dynamic_value"
        assert log.value == "dynamic_value"

    @patch("app.services.execution.run_single_action.run_single_action")
    def test_returns_step_log_with_result(self, mock_run):
        mock_run.return_value = _make_execution_result(
            ok=True,
            action_type="click",
            target_summary="Submit button",
        )
        runtime = _make_runtime()
        step = _make_step(intent="click_submit", action_type="click")

        log = _execute_step(step, runtime, variables={}, step_index=2)

        assert isinstance(log, ExplorationStepLog)
        assert log.step_index == 2
        assert log.intent == "click_submit"
        assert log.action_type == "click"
        assert log.target_summary == "Submit button"
        assert log.execution_result is not None
        assert log.execution_result.ok is True
        assert log.timestamp_ms > 0

    @patch("app.services.execution.run_single_action.run_single_action")
    def test_extracts_observation_from_result(self, mock_run):
        obs_dict = {
            "url": "https://example.com/done",
            "title": "Done",
            "url_changed": True,
            "title_changed": True,
            "html_changed": False,
            "html_hash": "xyz",
            "timestamp_ms": 5000,
        }
        mock_run.return_value = _make_execution_result(observation=obs_dict)
        runtime = _make_runtime()
        step = _make_step(intent="click_it", action_type="click")

        log = _execute_step(step, runtime, variables={}, step_index=0)

        assert log.observation is not None
        assert isinstance(log.observation, PostActionObservation)
        assert log.observation.url == "https://example.com/done"
        assert log.observation.url_changed is True

    @patch("app.services.execution.run_single_action.run_single_action")
    def test_evaluates_step_success_criteria(self, mock_run):
        obs_dict = {
            "url": "https://example.com/results?q=test",
            "title": "Results",
            "url_changed": True,
            "title_changed": True,
            "html_changed": True,
            "html_hash": "new_hash",
            "timestamp_ms": 3000,
        }
        mock_run.return_value = _make_execution_result(observation=obs_dict)
        runtime = _make_runtime()
        step = _make_step(
            intent="search",
            action_type="click",
            success_criteria=TaskStepSuccessCriteria(
                conditions=[
                    SuccessCondition(type="url_contains", value="results"),
                ],
            ),
        )

        log = _execute_step(step, runtime, variables={}, step_index=0)

        assert log.success_evaluation is not None
        assert log.success_evaluation.satisfied is True

    @patch("app.services.execution.run_single_action.run_single_action")
    def test_error_result_with_criteria_produces_failure_eval(self, mock_run):
        mock_run.return_value = _make_execution_result(
            ok=False,
            error="Element not found",
            observation=None,
        )
        runtime = _make_runtime()
        step = _make_step(
            intent="click_missing",
            action_type="click",
            success_criteria=TaskStepSuccessCriteria(
                conditions=[SuccessCondition(type="no_error")],
            ),
        )

        log = _execute_step(step, runtime, variables={}, step_index=0)

        assert log.success_evaluation is not None
        assert log.success_evaluation.satisfied is False
        assert "execution_error" in log.success_evaluation.failed_conditions

    @patch("app.services.execution.run_single_action.run_single_action")
    def test_no_criteria_means_no_evaluation(self, mock_run):
        mock_run.return_value = _make_execution_result()
        runtime = _make_runtime()
        step = _make_step(intent="simple_click", action_type="click")

        log = _execute_step(step, runtime, variables={}, step_index=0)

        assert log.success_evaluation is None

    @patch("app.services.execution.run_single_action.run_single_action")
    def test_agent_note_includes_ok_status(self, mock_run):
        mock_run.return_value = _make_execution_result(ok=True)
        runtime = _make_runtime()
        step = _make_step(intent="do_thing", action_type="click")

        log = _execute_step(step, runtime, variables={}, step_index=0)

        assert "ok=True" in log.agent_note

    @patch("app.services.execution.run_single_action.run_single_action")
    def test_agent_note_includes_error(self, mock_run):
        mock_run.return_value = _make_execution_result(
            ok=False, error="timeout",
        )
        runtime = _make_runtime()
        step = _make_step(intent="fail_thing", action_type="click")

        log = _execute_step(step, runtime, variables={}, step_index=0)

        assert "error=timeout" in log.agent_note

    def test_observe_action_type_delegates_to_observe_only(self):
        """When action_type is 'observe', _execute_step should delegate
        to _observe_only_step instead of calling run_single_action."""
        runtime = _make_runtime(url="https://example.com/page")
        step = _make_step(intent="check_page", action_type="observe")

        log = _execute_step(step, runtime, variables={}, step_index=0)

        assert log.action_type == "observe"
        assert log.target_summary == "(observation only)"
        # run_single_action should NOT have been called
        assert log.execution_result is None


# ───────────────────────────────────────────────────────────────────
# run_exploration
# ───────────────────────────────────────────────────────────────────

class TestRunExploration:
    """Tests for run_exploration."""

    @patch("app.services.execution.run_single_action.run_single_action")
    @patch("time.sleep")
    def test_navigates_to_target_url(self, _mock_sleep, mock_run):
        mock_run.return_value = _make_execution_result()
        runtime = _make_runtime()
        task = _make_task(
            target_url="https://example.com/search",
            steps=[_make_step(intent="click_btn", action_type="click")],
        )

        run_exploration(task, runtime)

        runtime.navigate.assert_called_once_with("https://example.com/search")

    @patch("app.services.execution.run_single_action.run_single_action")
    @patch("time.sleep")
    def test_executes_each_step_in_order(self, _mock_sleep, mock_run):
        mock_run.return_value = _make_execution_result()
        runtime = _make_runtime()

        steps = [
            _make_step(intent="step_0", action_type="click"),
            _make_step(intent="step_1", action_type="fill", value="hello"),
            _make_step(intent="step_2", action_type="press", value="Enter"),
        ]
        task = _make_task(steps=steps)

        result = run_exploration(task, runtime)

        assert result.total_steps == 3
        assert len(result.steps) == 3
        assert result.steps[0].intent == "step_0"
        assert result.steps[1].intent == "step_1"
        assert result.steps[2].intent == "step_2"
        assert mock_run.call_count == 3

    @patch("app.services.execution.run_single_action.run_single_action")
    @patch("time.sleep")
    def test_max_steps_limits_execution(self, _mock_sleep, mock_run):
        mock_run.return_value = _make_execution_result()
        runtime = _make_runtime()

        steps = [
            _make_step(intent=f"step_{i}", action_type="click")
            for i in range(5)
        ]
        task = _make_task(steps=steps)

        result = run_exploration(task, runtime, max_steps=2)

        assert result.total_steps == 2
        assert len(result.steps) == 2
        assert mock_run.call_count == 2
        assert result.steps[0].intent == "step_0"
        assert result.steps[1].intent == "step_1"

    @patch("time.sleep")
    def test_navigation_failure_returns_early(self, _mock_sleep):
        runtime = _make_runtime()
        runtime.navigate.side_effect = RuntimeError("net::ERR_CONNECTION_REFUSED")
        task = _make_task(
            target_url="https://unreachable.example",
            steps=[_make_step(intent="will_not_run", action_type="click")],
        )

        result = run_exploration(task, runtime)

        assert result.success is False
        assert result.total_steps == 0
        assert len(result.steps) == 0
        assert "failed" in result.summary.lower()

    @patch("app.services.execution.run_single_action.run_single_action")
    @patch("time.sleep")
    def test_returns_exploration_result(self, _mock_sleep, mock_run):
        mock_run.return_value = _make_execution_result()
        runtime = _make_runtime(
            url="https://example.com/final",
            title="Final Page",
        )
        task = _make_task(
            steps=[_make_step(intent="do_it", action_type="click")],
        )

        result = run_exploration(task, runtime)

        assert isinstance(result, ExplorationResult)
        assert result.total_steps == 1
        assert result.final_url == "https://example.com/final"
        assert result.final_title == "Final Page"
        assert result.elapsed_ms is not None
        assert result.elapsed_ms >= 0
        assert result.summary != ""

    @patch("app.services.execution.run_single_action.run_single_action")
    @patch("time.sleep")
    def test_no_global_criteria_success_when_all_steps_ok(self, _mock_sleep, mock_run):
        mock_run.return_value = _make_execution_result(ok=True)
        runtime = _make_runtime()
        task = _make_task(
            steps=[
                _make_step(intent="s1", action_type="click"),
                _make_step(intent="s2", action_type="fill", value="x"),
            ],
        )

        result = run_exploration(task, runtime)

        assert result.success is True

    @patch("app.services.execution.run_single_action.run_single_action")
    @patch("time.sleep")
    def test_no_global_criteria_failure_when_step_fails(self, _mock_sleep, mock_run):
        mock_run.return_value = _make_execution_result(ok=False, error="not found")
        runtime = _make_runtime()
        task = _make_task(
            steps=[_make_step(intent="broken", action_type="click")],
        )

        result = run_exploration(task, runtime)

        assert result.success is False

    @patch("app.services.execution.run_single_action.run_single_action")
    @patch("time.sleep")
    def test_evaluates_global_success_criteria(self, _mock_sleep, mock_run):
        mock_run.return_value = _make_execution_result()
        runtime = _make_runtime(
            url="https://example.com/results?q=test",
            title="Search Results",
            html="<html>results page</html>",
        )
        task = _make_task(
            steps=[_make_step(intent="search", action_type="click")],
            global_success_criteria=TaskStepSuccessCriteria(
                conditions=[
                    SuccessCondition(type="url_contains", value="results"),
                ],
            ),
        )

        result = run_exploration(task, runtime)

        assert result.success is True
        assert "SUCCEEDED" in result.summary

    @patch("app.services.execution.run_single_action.run_single_action")
    @patch("time.sleep")
    def test_global_criteria_failure(self, _mock_sleep, mock_run):
        mock_run.return_value = _make_execution_result()
        runtime = _make_runtime(
            url="https://example.com",
            title="Home",
        )
        task = _make_task(
            steps=[_make_step(intent="search", action_type="click")],
            global_success_criteria=TaskStepSuccessCriteria(
                conditions=[
                    SuccessCondition(type="url_contains", value="results"),
                ],
            ),
        )

        result = run_exploration(task, runtime)

        assert result.success is False
        assert "FAILED" in result.summary

    @patch("app.services.execution.run_single_action.run_single_action")
    @patch("time.sleep")
    def test_step_logs_preserved_in_result(self, _mock_sleep, mock_run):
        mock_run.return_value = _make_execution_result(
            ok=True,
            action_type="fill",
            target_summary="textarea",
        )
        runtime = _make_runtime()
        task = _make_task(
            steps=[
                _make_step(intent="fill_input", action_type="fill", value="data"),
            ],
        )

        result = run_exploration(task, runtime)

        assert len(result.steps) == 1
        log = result.steps[0]
        assert log.step_index == 0
        assert log.intent == "fill_input"
        assert log.execution_result is not None
        assert log.execution_result.ok is True
        assert log.execution_result.action_type == "fill"

    @patch("app.services.execution.run_single_action.run_single_action")
    @patch("time.sleep")
    def test_captures_final_screenshot(self, _mock_sleep, mock_run):
        mock_run.return_value = _make_execution_result()
        runtime = _make_runtime(screenshot_path="/tmp/final.png")
        task = _make_task(
            steps=[_make_step(intent="click", action_type="click")],
        )

        result = run_exploration(task, runtime)

        runtime.screenshot.assert_called()
        assert result.final_screenshot_ref == "/tmp/final.png"

    @patch("app.services.execution.run_single_action.run_single_action")
    @patch("time.sleep")
    def test_screenshot_failure_does_not_crash(self, _mock_sleep, mock_run):
        mock_run.return_value = _make_execution_result()
        runtime = _make_runtime()
        runtime.screenshot.side_effect = RuntimeError("screenshot failed")
        task = _make_task(
            steps=[_make_step(intent="click", action_type="click")],
        )

        result = run_exploration(task, runtime)

        assert result.final_screenshot_ref is None

    @patch("time.sleep")
    def test_empty_steps_list(self, _mock_sleep):
        runtime = _make_runtime()
        task = _make_task(steps=[])

        result = run_exploration(task, runtime)

        assert result.total_steps == 0
        assert len(result.steps) == 0
        # No steps failed, so success should be True
        assert result.success is True

    @patch("app.services.execution.run_single_action.run_single_action")
    @patch("time.sleep")
    def test_observe_steps_do_not_affect_no_criteria_success(self, _mock_sleep, mock_run):
        """Observe steps should be excluded from the all-ok check when
        there are no global criteria."""
        mock_run.return_value = _make_execution_result(ok=True)
        runtime = _make_runtime()
        task = _make_task(
            steps=[
                _make_step(intent="do_action", action_type="click"),
                _make_step(intent="verify", action_type="observe"),
            ],
        )

        result = run_exploration(task, runtime)

        assert result.total_steps == 2
        # observe steps are excluded from the ok-check → success True
        assert result.success is True

    @patch("app.services.execution.run_single_action.run_single_action")
    @patch("time.sleep")
    def test_summary_includes_step_details(self, _mock_sleep, mock_run):
        mock_run.return_value = _make_execution_result(ok=True)
        runtime = _make_runtime()
        task = _make_task(
            name="My Test Task",
            steps=[
                _make_step(intent="click_button", action_type="click"),
                _make_step(intent="fill_field", action_type="fill", value="data"),
            ],
        )

        result = run_exploration(task, runtime)

        assert "My Test Task" in result.summary
        assert "click_button" in result.summary
        assert "fill_field" in result.summary

    @patch("app.services.execution.run_single_action.run_single_action")
    @patch("time.sleep")
    def test_variables_passed_to_steps(self, _mock_sleep, mock_run):
        mock_run.return_value = _make_execution_result()
        runtime = _make_runtime()
        task = _make_task(
            variables={"query": "weather"},
            steps=[
                _make_step(
                    intent="fill_search",
                    action_type="fill",
                    value_from="query",
                ),
            ],
        )

        run_exploration(task, runtime)

        # The value should have been resolved from variables
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["value"] == "weather"

    @patch("app.services.execution.run_single_action.run_single_action")
    @patch("time.sleep")
    def test_global_criteria_with_value_from(self, _mock_sleep, mock_run):
        mock_run.return_value = _make_execution_result()
        runtime = _make_runtime(
            url="https://example.com/search?q=weather",
            title="weather - Search",
        )
        task = _make_task(
            variables={"expected_title": "weather"},
            steps=[_make_step(intent="search", action_type="click")],
            global_success_criteria=TaskStepSuccessCriteria(
                conditions=[
                    SuccessCondition(
                        type="title_contains",
                        value_from="expected_title",
                    ),
                ],
            ),
        )

        result = run_exploration(task, runtime)

        assert result.success is True

    @patch("app.services.execution.run_single_action.run_single_action")
    @patch("time.sleep")
    def test_global_criteria_tolerates_final_state_failures(self, _mock_sleep, mock_run):
        mock_run.return_value = _make_execution_result()
        runtime = _make_runtime()
        runtime.current_url.side_effect = [
            "https://before.example.com",
            Exception("url fail"),
            Exception("url fail"),
        ]
        runtime.current_title.side_effect = [
            "Before",
            Exception("title fail"),
            Exception("title fail"),
        ]
        runtime.current_html.side_effect = [
            "<html>before</html>",
            Exception("html fail"),
        ]
        runtime.screenshot.side_effect = Exception("shot fail")
        task = _make_task(
            steps=[_make_step(intent="click", action_type="click")],
            global_success_criteria=TaskStepSuccessCriteria(
                conditions=[SuccessCondition(type="no_error")]
            ),
        )

        result = run_exploration(task, runtime)

        assert result.success is False
        assert result.final_url == ""
        assert result.final_title == ""
        assert result.final_screenshot_ref is None

    @patch("app.services.execution.run_single_action.run_single_action")
    @patch("time.sleep")
    def test_summary_includes_eval_fail_status(self, _mock_sleep, mock_run):
        obs_dict = {
            "url": "https://example.com/after",
            "title": "After",
            "url_changed": False,
            "title_changed": False,
            "html_changed": False,
            "html_hash": "same",
            "timestamp_ms": 3000,
        }
        mock_run.return_value = _make_execution_result(
            ok=True,
            action_type="click",
            observation=obs_dict,
        )
        runtime = _make_runtime(
            url="https://example.com",
            title="Before",
            html="<html>before</html>",
        )
        task = _make_task(
            name="Eval Task",
            steps=[
                _make_step(
                    intent="verify_change",
                    action_type="click",
                    success_criteria=TaskStepSuccessCriteria(
                        conditions=[SuccessCondition(type="title_contains", value="Missing")]
                    ),
                )
            ],
        )

        result = run_exploration(task, runtime)

        assert "verify_change: ok (eval: fail)" in result.summary
