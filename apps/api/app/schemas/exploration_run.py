from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.exploration_run import ExplorationMode, ExplorationRunStatus
from app.schemas.execution import ExecutionResult
from app.schemas.observation import PostActionObservation
from app.schemas.success_criteria import SuccessEvaluation


# ───────────────────────────────────────────────────────────────────
# Exploration step log — records a single step within an exploration
# ───────────────────────────────────────────────────────────────────

class ExplorationStepLog(BaseModel):
    """One atomic step in an exploration run.

    Preserves full execution_result and observation objects (not just
    summaries) so that post-run debugging has complete context.
    """

    step_index: int = 0
    candidate_id: str | None = Field(
        default=None,
        description="ID or key of the candidate element that was acted upon.",
    )
    intent: str = Field(
        default="",
        description="What this step was trying to achieve (from task step or strategy).",
    )
    action_type: str = ""
    target_summary: str = ""
    value: str | None = None

    # Full objects — not summaries
    execution_result: ExecutionResult | None = None
    observation: PostActionObservation | None = None
    success_evaluation: SuccessEvaluation | None = None

    agent_note: str | None = Field(
        default=None,
        description="Optional note from the exploration engine about this step "
        "(e.g. why this candidate was chosen, what was unexpected).",
    )
    timestamp_ms: int = 0


class ExplorationResult(BaseModel):
    """Overall result of a completed exploration run."""

    success: bool = False
    steps: list[ExplorationStepLog] = Field(default_factory=list)
    total_steps: int = 0

    # Final page state
    final_url: str = ""
    final_title: str = ""
    final_screenshot_ref: str | None = None

    # If successful, a candidate learned path
    path_candidate: dict[str, Any] | None = Field(
        default=None,
        description="If exploration succeeded, a draft LearnedPath structure "
        "ready to be persisted.",
    )

    summary: str = Field(
        default="",
        description="Human-readable summary of the exploration outcome.",
    )
    elapsed_ms: int | None = None


class ExplorationRunBase(BaseModel):
    page_signature: str | None = Field(default=None, max_length=512)
    mode: ExplorationMode = ExplorationMode.FORM
    status: ExplorationRunStatus = ExplorationRunStatus.PENDING
    success_criteria_ids_json: list[str] = Field(default_factory=list)
    strategy_json: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None
    result_snapshot_json: dict[str, Any] | None = None
    candidate_elements_json: list[dict[str, Any]] | None = None
    interaction_hints_json: list[dict[str, Any]] | None = None


class ExplorationRunCreate(ExplorationRunBase):
    pass


class ExplorationRunUpdate(BaseModel):
    page_signature: str | None = Field(default=None, max_length=512)
    mode: ExplorationMode | None = None
    status: ExplorationRunStatus | None = None
    success_criteria_ids_json: list[str] | None = None
    strategy_json: dict[str, Any] | None = None
    summary: str | None = None
    result_snapshot_json: dict[str, Any] | None = None
    candidate_elements_json: list[dict[str, Any]] | None = None
    interaction_hints_json: list[dict[str, Any]] | None = None


class ExplorationRunRead(ExplorationRunBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
