"""Step understanding output schema.

Defines the structured result of LLM-based step understanding (Phase 6D).
This is what the Agent produces after analyzing a StepsContext.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class KeyStepInfo(BaseModel):
    """A step identified as particularly important."""

    step_index: int = Field(description="0-based index in the steps list.")
    event_type: str
    target: str
    reason: str = Field(description="Why this step is considered key, one sentence.")


class CategorizedStep(BaseModel):
    """A step categorized by its likely role."""

    step_index: int
    event_type: str
    target: str
    description: str = Field(default="", description="Brief note on what this step likely does.")


class NoChangeStepInfo(BaseModel):
    """A step with has_changes=false and an observation about why."""

    step_index: int
    event_type: str
    target: str
    likely_reason: str = Field(
        description="Possible explanation: 'async_pending', 'precondition_unmet', "
        "'already_active', 'cross_frame', 'navigation', 'genuine_noop', 'unknown'.",
    )


class StepUnderstanding(BaseModel):
    """Structured step understanding result.

    Produced by the step understanding service (6D).
    Consumed by 6E (combined output) and Phase 7 (execution).
    """

    common_step_patterns: list[str] = Field(
        default_factory=list,
        description="1-3 short sentences describing the typical usage flow observed.",
    )
    likely_key_steps: list[KeyStepInfo] = Field(default_factory=list)
    likely_expand_steps: list[CategorizedStep] = Field(
        default_factory=list,
        description="Steps that look like expand, toggle, open dialog, switch tab, etc.",
    )
    likely_submit_steps: list[CategorizedStep] = Field(
        default_factory=list,
        description="Steps that look like save, submit, confirm, apply, etc.",
    )
    likely_no_change_steps: list[NoChangeStepInfo] = Field(default_factory=list)
    observed_change_patterns: list[str] = Field(
        default_factory=list,
        description="1-3 short sentences summarizing the most common change patterns.",
    )
    confidence_notes: list[str] = Field(
        default_factory=list,
        description="Optional notes on uncertainty, for debug/review.",
    )


# JSON Schema dict for use with generate_structured().
STEP_UNDERSTANDING_SCHEMA: dict = StepUnderstanding.model_json_schema()
