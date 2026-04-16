"""Simplified single-action entry point for the exploration loop.

Thin synchronous wrapper that:
  1. Assembles an ExecutionRequest from simple parameters
  2. Calls execute_and_observe()
  3. Returns the ExecutionResult

Does NOT manage ExecutionRuntime lifecycle — the caller owns the runtime.
Does NOT contain any site-specific logic.
"""

from __future__ import annotations

import logging
from typing import Any

from app.schemas.execution import (
    ActionTarget,
    ActionType,
    ExecutionRequest,
    ExecutionResult,
    LocatorHint,
    PageSnapshot,
)
from app.schemas.task_definition import TaskStepHint
from app.services.execution.execution_runtime import ExecutionRuntime

logger = logging.getLogger(__name__)


def _build_hints_from_task_hint(hint: TaskStepHint | None) -> list[LocatorHint]:
    """Convert a TaskStepHint into locator hints for the resolver."""
    if hint is None:
        return []

    hints: list[LocatorHint] = []

    # Role-based hint (high priority — STRONG_ATTRIBUTE level)
    if hint.role:
        meta: dict[str, Any] = {"tag": hint.tag}
        if hint.name:
            meta["name"] = hint.name
        hints.append(LocatorHint(
            strategy="STRONG_ATTRIBUTE",
            value=f"role={hint.role}",
            confidence="medium",
            meta=meta,
        ))

    # Name/placeholder (STRONG_ATTRIBUTE)
    if hint.name and not hint.role:
        hints.append(LocatorHint(
            strategy="TAG_TEXT_LABEL",
            value=f"{hint.tag or '*'}::{hint.name}",
            confidence="medium",
            meta={"tag": hint.tag},
        ))

    if hint.placeholder:
        hints.append(LocatorHint(
            strategy="STRONG_ATTRIBUTE",
            value=f"placeholder={hint.placeholder}",
            confidence="medium",
            meta={"tag": hint.tag},
        ))

    # Text content hint
    if hint.text:
        hints.append(LocatorHint(
            strategy="TAG_TEXT_LABEL",
            value=f"{hint.tag or '*'}::{hint.text}",
            confidence="medium",
            meta={"tag": hint.tag},
        ))

    # CSS selector fallback
    if hint.selector:
        hints.append(LocatorHint(
            strategy="FALLBACK_SELECTOR",
            value=hint.selector,
            confidence="low",
            meta={"tag": hint.tag},
        ))

    return hints


def run_single_action(
    *,
    action_type: ActionType,
    runtime: ExecutionRuntime,
    target_description: str = "",
    value: str | None = None,
    target_hint: TaskStepHint | None = None,
    locator_hints: list[LocatorHint] | None = None,
    region_constraint: str | None = None,
) -> ExecutionResult:
    """Execute a single action and return the result with observation.

    This is the atomic operation for the exploration loop. It assembles
    an ExecutionRequest from simple parameters and delegates to the
    existing execute_and_observe() pipeline (7D + 7E).

    Args:
        action_type: What to do (click, fill, press, navigate, etc.)
        runtime: Playwright runtime — caller manages lifecycle.
        target_description: Human-readable target description.
        value: Value for fill/press/select actions.
        target_hint: Soft hints from task definition for locating the target.
        locator_hints: Pre-built locator hints (takes precedence over target_hint).
        region_constraint: Optional region name to narrow search scope.

    Returns:
        ExecutionResult with observation attached.
    """
    from app.services.execution.post_action_observer import execute_and_observe

    # Build locator hints
    hints = locator_hints or _build_hints_from_task_hint(target_hint)

    # Capture current page state for the request
    try:
        page_url = runtime.current_url()
    except Exception:
        page_url = ""
    try:
        page_title = runtime.current_title()
    except Exception:
        page_title = ""

    # Assemble request
    request = ExecutionRequest(
        understanding={},
        page=PageSnapshot(url=page_url, title=page_title),
        action=ActionTarget(
            action_type=action_type,
            target_description=target_description,
            value=value,
            region_constraint=region_constraint,
        ),
        locator_hints=hints,
    )

    # Execute and observe
    result = execute_and_observe(request, runtime)

    return result
