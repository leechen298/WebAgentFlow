"""Task definition schema — external task descriptions loaded from JSON files.

A TaskDefinition describes what to do on a specific site/page. It contains
no execution logic — it is pure data consumed by the exploration engine.

Site-specific knowledge lives in these files, NOT in Python code.

Provenance tracking:
  - ``source``: who created it — "builtin" (shipped with the app) or "user"
  - ``provenance``: how it was created — user_authored, autonomous_exploration, etc.
  - ``based_on``: lineage pointer (run ID, recording ID, or another task ID)
  - ``edited_by_user``: whether a user has manually modified it
  - ``revision``: monotonic version counter
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.success_criteria import SuccessCondition


# ───────────────────────────────────────────────────────────────────
# Provenance
# ───────────────────────────────────────────────────────────────────

Source = Literal["builtin", "user"]

Provenance = Literal[
    "user_authored",
    "autonomous_exploration",
    "autonomous_then_user_corrected",
    "derived_from_recording",
    "manual_edit",
]


# ───────────────────────────────────────────────────────────────────
# Task step — one atomic action within a task
# ───────────────────────────────────────────────────────────────────

class TaskStepHint(BaseModel):
    """Hints for locating the target element of a task step.

    These are soft hints, not hard selectors. The locator resolver
    uses them as additional signals alongside its own strategies.
    """

    role: str | None = None
    name: str | None = None
    tag: str | None = None
    selector: str | None = None
    text: str | None = None
    placeholder: str | None = None


class TaskStep(BaseModel):
    """One atomic step in a task definition.

    ``action_type="observe"`` means this step only checks state
    (no interaction). Used for verification steps.
    """

    intent: str = Field(
        description="What this step is trying to achieve, e.g. 'fill_search_box'.",
    )
    action_type: str = Field(
        description="Action to perform: click, fill, press, select, navigate, observe, etc.",
    )
    target_hint: TaskStepHint | None = Field(
        default=None,
        description="Soft hints for locating the target element.",
    )
    value: str | None = Field(
        default=None,
        description="Static value for fill/press/select actions.",
    )
    value_from: str | None = Field(
        default=None,
        description="Variable name to resolve value from task variables. "
        "Overrides ``value`` when set.",
    )
    success_criteria: TaskStepSuccessCriteria | None = Field(
        default=None,
        description="Optional per-step success check. If absent, the step "
        "is considered successful if execution didn't error.",
    )


class TaskStepSuccessCriteria(BaseModel):
    """Inline success criteria for a single task step."""

    conditions: list[SuccessCondition] = Field(default_factory=list)


# ───────────────────────────────────────────────────────────────────
# Task definition — the top-level structure
# ───────────────────────────────────────────────────────────────────

class TaskDefinition(BaseModel):
    """A complete task definition loaded from an external JSON file.

    Contains everything the exploration engine needs to execute
    a task on a specific site. No execution logic — pure data.
    """

    id: str = Field(description="Unique task identifier, e.g. 'google-search-basic'.")
    name: str = Field(description="Human-readable task name.")
    description: str = ""
    target_url: str = Field(description="Starting URL for the task.")

    variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Runtime variables that steps can reference via value_from. "
        "E.g. {\"query\": \"厦门天气\"}.",
    )

    steps: list[TaskStep] = Field(
        default_factory=list,
        description="Ordered list of steps to execute.",
    )

    global_success_criteria: TaskStepSuccessCriteria | None = Field(
        default=None,
        description="Overall success check applied after all steps complete.",
    )

    # --- Provenance ---
    source: Source = "builtin"
    provenance: Provenance = "user_authored"
    based_on: str | None = Field(
        default=None,
        description="Lineage: run ID, recording ID, or task ID this was derived from.",
    )
    edited_by_user: bool = False
    revision: int = Field(
        default=1,
        description="Monotonic version counter. Incremented on each edit.",
    )
