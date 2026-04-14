"""Post-action observation schema (Phase 7E).

Captures the page state immediately after a single-step action has been
executed.  Provides lightweight change detection (URL, title, HTML hash)
and optional target-element post-action status.

Scope — Phase 7E is ONLY immediate post-action fact sampling:
  - NOT wait-until-expected-change   (Phase 8)
  - NOT retry / recovery
  - NOT DOM diff
  - NOT next-action planning
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TargetPostState(BaseModel):
    """Lightweight post-action status of the target element."""

    still_present: bool | None = Field(
        default=None,
        description="Whether the target element is still in the DOM after the action.  "
        "None if the check could not be performed.",
    )
    still_visible: bool | None = Field(
        default=None,
        description="Whether the target element is still visible after the action.  "
        "None if the check could not be performed.",
    )


class PostActionObservation(BaseModel):
    """Structured observation captured immediately after action execution.

    This is the output of ``observe_post_action()``.  It records page
    facts — not judgments about whether the action "succeeded" in a
    business sense.
    """

    # --- A. Page state snapshot ---
    url: str = ""
    title: str = ""
    screenshot_ref: str | None = None
    html_snapshot_ref: str | None = None

    # --- B. Change signals ---
    url_changed: bool = False
    title_changed: bool = False
    html_changed: bool = False

    # --- C. Lightweight stats ---
    html_length: int = 0
    html_hash: str = Field(default="", description="Hex digest of HTML content for change detection.")
    timestamp_ms: int = 0
    elapsed_since_action_ms: int | None = None

    # --- D. Target element post-state ---
    target: TargetPostState = Field(default_factory=TargetPostState)

    # --- E. Debug ---
    warnings: list[str] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)
