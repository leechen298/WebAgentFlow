"""Execution sub-package — Phase 7 execution pipeline.

Public API:
  - build_execution_request()   — 7A contract builder
  - create_execution_runtime()  — 7B runtime factory
  - ExecutionRuntime            — 7B runtime class
  - resolve_locator()           — 7C locator resolution
  - execute_action()            — 7D action execution
  - execute_and_observe()       — 7D+7E combined pipeline
  - observe_post_action()       — 7E observation
  - run_single_action()         — simplified entry point for exploration loop
"""

from app.services.execution.execution_contract import build_execution_request
from app.services.execution.execution_runtime import (
    ExecutionRuntime,
    PageObservationError,
    create_execution_runtime,
)
from app.services.execution.locator_resolver import resolve_locator, to_playwright_locator
from app.services.execution.action_executor import execute_action
from app.services.execution.post_action_observer import (
    execute_and_observe,
    observe_post_action,
)
from app.services.execution.run_single_action import run_single_action

__all__ = [
    "build_execution_request",
    "create_execution_runtime",
    "ExecutionRuntime",
    "PageObservationError",
    "resolve_locator",
    "to_playwright_locator",
    "execute_action",
    "execute_and_observe",
    "observe_post_action",
    "run_single_action",
]
