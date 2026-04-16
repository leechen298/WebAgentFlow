"""Generic exploration loop engine.

Executes a TaskDefinition step-by-step, evaluates success at each step,
and produces an ExplorationResult. Contains NO site-specific logic.

Usage:
    from app.services.execution import create_execution_runtime
    from app.services.task_loader import load_task_by_id
    from app.services.learning.exploration_loop import run_exploration

    task = load_task_by_id("search-basic")
    with create_execution_runtime() as runtime:
        result = run_exploration(task, runtime)
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from app.schemas.exploration_run import ExplorationResult, ExplorationStepLog
from app.schemas.observation import PostActionObservation
from app.schemas.success_criteria import SuccessEvaluation
from app.schemas.task_definition import TaskDefinition, TaskStep
from app.services.learning.success_evaluator import (
    evaluate_success,
    make_before_state,
)
from app.services.task_loader import resolve_step_value

if TYPE_CHECKING:
    from app.services.execution.execution_runtime import ExecutionRuntime

logger = logging.getLogger(__name__)


def _capture_before_state(runtime: ExecutionRuntime) -> dict[str, str]:
    """Capture current page state for success evaluation."""
    url = ""
    title = ""
    html_hash = ""
    try:
        url = runtime.current_url()
    except Exception:
        pass
    try:
        title = runtime.current_title()
    except Exception:
        pass
    try:
        import hashlib
        html = runtime.current_html()
        html_hash = hashlib.md5(html.encode()).hexdigest()
    except Exception:
        pass
    return make_before_state(url=url, title=title, html_hash=html_hash)


def _execute_step(
    step: TaskStep,
    runtime: ExecutionRuntime,
    variables: dict[str, Any],
    step_index: int,
) -> ExplorationStepLog:
    """Execute a single task step and return a log entry."""
    ts_start = int(time.time() * 1000)

    # Resolve value
    value = resolve_step_value(step.value, step.value_from, variables)

    # Capture before state
    before_state = _capture_before_state(runtime)

    # "observe" steps don't execute an action — they only evaluate
    if step.action_type == "observe":
        return _observe_only_step(
            step=step,
            runtime=runtime,
            variables=variables,
            before_state=before_state,
            step_index=step_index,
            ts_start=ts_start,
        )

    # Execute action (lazy import to avoid Playwright at module level)
    from app.services.execution.run_single_action import run_single_action

    result = run_single_action(
        action_type=step.action_type,
        runtime=runtime,
        target_description=step.intent,
        value=value,
        target_hint=step.target_hint,
    )

    # Extract observation
    observation = None
    if result.observation:
        observation = PostActionObservation(**result.observation)

    # Evaluate step-level success criteria if defined
    success_eval = None
    if step.success_criteria and step.success_criteria.conditions:
        if observation:
            success_eval = evaluate_success(
                conditions=step.success_criteria.conditions,
                before_state=before_state,
                observation=observation,
                variables=variables,
                execution_error=result.error,
            )
        elif result.error:
            success_eval = SuccessEvaluation(
                satisfied=False,
                confidence="high",
                failed_conditions=["execution_error"],
                evidence={"error": result.error},
            )

    return ExplorationStepLog(
        step_index=step_index,
        intent=step.intent,
        action_type=step.action_type,
        target_summary=result.target_summary,
        value=value,
        execution_result=result,
        observation=observation,
        success_evaluation=success_eval,
        agent_note=f"Step '{step.intent}': ok={result.ok}" + (
            f", error={result.error}" if result.error else ""
        ),
        timestamp_ms=ts_start,
    )


def _observe_only_step(
    *,
    step: TaskStep,
    runtime: ExecutionRuntime,
    variables: dict[str, Any],
    before_state: dict[str, str],
    step_index: int,
    ts_start: int,
) -> ExplorationStepLog:
    """Handle an 'observe' step — evaluate without executing an action."""
    # Build a synthetic observation from current page state
    try:
        url = runtime.current_url()
    except Exception:
        url = ""
    try:
        title = runtime.current_title()
    except Exception:
        title = ""

    import hashlib
    html_hash = ""
    try:
        html = runtime.current_html()
        html_hash = hashlib.md5(html.encode()).hexdigest()
    except Exception:
        pass

    observation = PostActionObservation(
        url=url,
        title=title,
        url_changed=(url != before_state.get("url", "")),
        title_changed=(title != before_state.get("title", "")),
        html_changed=(html_hash != before_state.get("html_hash", "")),
        html_hash=html_hash,
        timestamp_ms=int(time.time() * 1000),
    )

    success_eval = None
    if step.success_criteria and step.success_criteria.conditions:
        success_eval = evaluate_success(
            conditions=step.success_criteria.conditions,
            before_state=before_state,
            observation=observation,
            variables=variables,
        )

    return ExplorationStepLog(
        step_index=step_index,
        intent=step.intent,
        action_type="observe",
        target_summary="(observation only)",
        observation=observation,
        success_evaluation=success_eval,
        agent_note=f"Observe '{step.intent}': satisfied={success_eval.satisfied if success_eval else 'N/A'}",
        timestamp_ms=ts_start,
    )


def run_exploration(
    task: TaskDefinition,
    runtime: ExecutionRuntime,
    *,
    max_steps: int | None = None,
) -> ExplorationResult:
    """Execute a task definition and produce an exploration result.

    This is the main entry point for the exploration engine. It:
    1. Navigates to the target URL
    2. Executes each step in order
    3. Evaluates per-step and global success criteria
    4. Returns a structured ExplorationResult

    The engine is generic — all site-specific knowledge comes from the
    TaskDefinition (loaded from external JSON files).

    Args:
        task: TaskDefinition loaded from JSON.
        runtime: Playwright runtime — caller manages lifecycle.
        max_steps: Override max steps (defaults to len(task.steps)).
    """
    t0 = int(time.time() * 1000)
    step_limit = max_steps or len(task.steps)
    steps_log: list[ExplorationStepLog] = []
    overall_success = False

    logger.info(
        "Starting exploration: task=%s, url=%s, steps=%d",
        task.id, task.target_url, len(task.steps),
    )

    # Capture initial state (before navigation)
    initial_before_state = _capture_before_state(runtime)

    # Step 0: Navigate to target URL
    try:
        runtime.navigate(task.target_url)
        logger.info("Navigated to %s", task.target_url)
    except Exception as e:
        logger.error("Navigation failed: %s", e)
        return ExplorationResult(
            success=False,
            total_steps=0,
            summary=f"Navigation to {task.target_url} failed: {e}",
            elapsed_ms=int(time.time() * 1000) - t0,
        )

    # Wait briefly for page to stabilize
    import time as _time
    _time.sleep(1.0)

    # Execute each step
    for i, task_step in enumerate(task.steps[:step_limit]):
        logger.info("Executing step %d/%d: %s", i + 1, len(task.steps), task_step.intent)

        step_log = _execute_step(
            step=task_step,
            runtime=runtime,
            variables=task.variables,
            step_index=i,
        )
        steps_log.append(step_log)

        # Log step outcome
        if step_log.execution_result and step_log.execution_result.error:
            logger.warning(
                "Step %d error: %s", i, step_log.execution_result.error,
            )

        if step_log.success_evaluation:
            logger.info(
                "Step %d evaluation: satisfied=%s, confidence=%s",
                i,
                step_log.success_evaluation.satisfied,
                step_log.success_evaluation.confidence,
            )

        # Small pause between steps for page stability
        _time.sleep(0.5)

    # Evaluate global success criteria
    global_eval = None
    if task.global_success_criteria and task.global_success_criteria.conditions:
        # Capture final state
        try:
            final_url = runtime.current_url()
        except Exception:
            final_url = ""
        try:
            final_title = runtime.current_title()
        except Exception:
            final_title = ""

        import hashlib
        final_html_hash = ""
        try:
            html = runtime.current_html()
            final_html_hash = hashlib.md5(html.encode()).hexdigest()
        except Exception:
            pass

        final_observation = PostActionObservation(
            url=final_url,
            title=final_title,
            url_changed=(final_url != initial_before_state.get("url", "")),
            title_changed=(final_title != initial_before_state.get("title", "")),
            html_changed=(final_html_hash != initial_before_state.get("html_hash", "")),
            html_hash=final_html_hash,
            timestamp_ms=int(time.time() * 1000),
        )

        global_eval = evaluate_success(
            conditions=task.global_success_criteria.conditions,
            before_state=initial_before_state,
            observation=final_observation,
            variables=task.variables,
        )

        overall_success = global_eval.satisfied
        logger.info(
            "Global evaluation: satisfied=%s, confidence=%s",
            global_eval.satisfied, global_eval.confidence,
        )
    else:
        # No global criteria — success if no step had a hard failure
        overall_success = all(
            s.execution_result is None or s.execution_result.ok
            for s in steps_log
            if s.action_type != "observe"
        )

    # Build result
    try:
        final_url = runtime.current_url()
    except Exception:
        final_url = ""
    try:
        final_title = runtime.current_title()
    except Exception:
        final_title = ""

    final_screenshot_ref = None
    try:
        final_screenshot_ref = runtime.screenshot()
    except Exception:
        pass

    elapsed = int(time.time() * 1000) - t0

    # Build summary
    step_summaries = []
    for s in steps_log:
        status = "ok" if (s.execution_result and s.execution_result.ok) or s.action_type == "observe" else "failed"
        if s.success_evaluation:
            status += f" (eval: {'pass' if s.success_evaluation.satisfied else 'fail'})"
        step_summaries.append(f"  [{s.step_index}] {s.intent}: {status}")

    summary = (
        f"Task '{task.name}' {'SUCCEEDED' if overall_success else 'FAILED'} "
        f"in {len(steps_log)} steps ({elapsed}ms)\n"
        + "\n".join(step_summaries)
    )

    return ExplorationResult(
        success=overall_success,
        steps=steps_log,
        total_steps=len(steps_log),
        final_url=final_url,
        final_title=final_title,
        final_screenshot_ref=final_screenshot_ref,
        summary=summary,
        elapsed_ms=elapsed,
    )
