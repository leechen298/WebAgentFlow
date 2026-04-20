"""Execution sub-package — Playwright runtime for autonomous exploration.

Only the runtime lifecycle lives here now; autonomous_explorer drives
clicks / fills directly against the Playwright page it receives.
"""

from app.services.execution.execution_runtime import (
    ExecutionRuntime,
    PageObservationError,
    create_execution_runtime,
)

__all__ = [
    "ExecutionRuntime",
    "PageObservationError",
    "create_execution_runtime",
]
