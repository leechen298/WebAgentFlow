"""Combined understanding output schema (Phase 6E).

Merges PageUnderstanding (6C) and StepUnderstanding (6D) into a single
execution-friendly Agent cognition result.

This is NOT an execution planner, action planner, or path template learner.
It is a unified cognitive view that Phase 7 (execution layer) consumes.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.page_understanding import PageKind


class KeyStepSummary(BaseModel):
    """A key step distilled for execution-layer consumption."""

    step_index: int
    event_type: str
    target: str
    role: str = Field(
        description="Why this step matters: 'key_input', 'expand', 'submit', 'navigate', 'select', 'other'.",
    )
    reason: str = Field(default="", description="One-sentence explanation.")


class ExecutionNote(BaseModel):
    """A note the execution layer should be aware of."""

    note: str
    source: str = Field(
        default="",
        description="Where this note comes from: 'no_change_step', 'page_structure', 'change_pattern', 'confidence'.",
    )


class AgentPageUnderstanding(BaseModel):
    """Unified Agent cognition result — the single output of Phase 6.

    Combines page understanding (6C) and step understanding (6D) into
    one execution-friendly structure. Phase 7 should consume this, not
    the individual 6C/6D results.

    This is a synthesis layer, not an execution planner.
    """

    # --- Page identity (from 6C) ---
    page_kind: PageKind = "unknown"
    page_goal: str = ""

    # --- Regions (from 6C, enriched by step frequency) ---
    primary_regions: list[dict] = Field(
        default_factory=list,
        description="Regions from 6C. Each dict has 'name', 'role', and optionally 'step_activity' if steps touch this region.",
    )

    # --- Actions (from 6C, merged with 6D step roles) ---
    primary_actions: list[dict] = Field(
        default_factory=list,
        description="Actions from 6C. Each dict has 'name', 'action_type', 'description', "
        "and optionally 'observed_in_steps' (bool) if 6D identified matching steps.",
    )

    # --- Key steps (distilled from 6D) ---
    key_steps: list[KeyStepSummary] = Field(default_factory=list)

    # --- Interaction patterns (merged from 6D patterns + 6C structure) ---
    interaction_patterns: list[str] = Field(
        default_factory=list,
        description="1-5 sentences describing common interaction patterns on this page.",
    )

    # --- Execution notes (synthesized warnings/observations) ---
    execution_notes: list[ExecutionNote] = Field(default_factory=list)

    # --- Key entities (from 6C) ---
    key_entities: list[str] = Field(default_factory=list)

    # --- Human-readable descriptions (for review and evaluation) ---
    page_description: str = Field(
        default="",
        description="2-4 sentence description of what this page is, its core regions, "
        "and main operations. More complete than page_goal. Not a mechanical "
        "concatenation of structured fields.",
    )
    operation_description: str = Field(
        default="",
        description="2-5 sentence description of what the user did in this recording. "
        "Covers the overall flow, key actions, and any noteworthy observations "
        "(e.g. no-change steps, async risks). Not an execution plan.",
    )

    # --- Confidence (merged from both) ---
    confidence_notes: list[str] = Field(default_factory=list)
