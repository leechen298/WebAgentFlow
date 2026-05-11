"""M11.1 task-to-path planning domain contract.

These contracts define the data structures for retrieval, slot binding,
Agent D planning, confirmation, execution, verification, and Agent E reporting.

This module intentionally does NOT import or reference replay, autonomous
exploration, or LLM provider modules. It is a pure schema layer.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Shared literals
# ---------------------------------------------------------------------------

NormalizationSource = Literal["none", "deterministic", "agent_d"]

TaskExecutionStatus = Literal["succeeded", "failed", "uncertain", "needs_review"]

FailureStage = Literal[
    "planning",
    "confirmation",
    "replay",
    "verification",
    "artifact",
    "unknown",
]

# ---------------------------------------------------------------------------
# Task intake
# ---------------------------------------------------------------------------


class TaskInput(BaseModel):
    """Raw user input that initiates a task planning flow."""

    raw_text: str
    locale: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskIntent(BaseModel):
    """Normalized understanding of what the user wants to accomplish.

    `raw_text` is the immutable original input.
    `normalized_goal` may be populated later by a deterministic normalizer
    or Agent D (11.1.4). `normalization_source` tracks which component
    produced the normalized goal.
    """

    raw_text: str
    normalized_goal: str | None = None
    normalization_source: NormalizationSource = "none"
    target_page_hint: str | None = None
    scenario_hint: str | None = None
    required_outputs: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Retrieval candidates
# ---------------------------------------------------------------------------


class LearnedPathCandidate(BaseModel):
    """A candidate learned path that may satisfy a task intent."""

    learned_path_id: str
    scenario: str
    page_template: str
    trust: str
    hit_count: int = 0
    match_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    drift_evidence_summary: str | None = None
    negative_evidence_summary: str | None = None


# ---------------------------------------------------------------------------
# Route plan
# ---------------------------------------------------------------------------


class RouteStep(BaseModel):
    """A single step within a route plan."""

    order: int
    learned_path_id: str
    purpose: str
    bound_slots: dict[str, Any] = Field(default_factory=dict)
    expected_result: str | None = None
    can_execute: bool = True
    warnings: list[str] = Field(default_factory=list)


class RoutePlan(BaseModel):
    """A planned sequence of learned path replays to fulfill a task."""

    id: str | None = None
    task_intent: TaskIntent
    steps: list[RouteStep] = Field(default_factory=list)
    confirmation_required: bool = False
    risk_hints: list[RiskHint] = Field(default_factory=list)
    postconditions: list[PostconditionSignal] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Slot binding
# ---------------------------------------------------------------------------


class SlotBindingProposal(BaseModel):
    """A proposed slot value binding derived from user input or context."""

    slot_name: str
    source_text: str
    target_action_index: int | None = None
    target_field: str | None = None
    proposed_value: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    requires_confirmation: bool = False


# ---------------------------------------------------------------------------
# Confirmation & risk
# ---------------------------------------------------------------------------


class RiskHint(BaseModel):
    """A risk signal identified by the system before execution.

    Risk hints do not block execution on their own; they feed into
    `ConsentRequirement` or policy decisions (11.1.5).
    """

    id: str | None = None
    risk_type: str
    reason: str
    severity: str
    policy_source: str | None = None


class ConfirmationRequirement(BaseModel):
    """A requirement to obtain user confirmation before proceeding."""

    reason: str
    message: str
    fields: list[str] = Field(default_factory=list)
    severity: str
    linked_risk_ids: list[str] = Field(default_factory=list)


class ConsentRequirement(BaseModel):
    """A consent gate that must be cleared before execution.

    Unlike `RiskHint`, a `ConsentRequirement` represents an actionable
    barrier: the user must explicitly agree before the plan can proceed.
    """

    reason: str
    message: str
    fields: list[str] = Field(default_factory=list)
    severity: str
    linked_risk_ids: list[str] = Field(default_factory=list)
    requires_user_confirmation: bool = True
    policy_source: str | None = None


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


class PostconditionSignal(BaseModel):
    """An expected post-execution signal used to verify success."""

    signal_type: str
    expected: str | None = None
    source: str | None = None
    required: bool = True


# ---------------------------------------------------------------------------
# Execution result
# ---------------------------------------------------------------------------


class TaskExecutionResult(BaseModel):
    """Outcome of executing a route plan.

    Failure source is expressed via `failure_stage` and `failure_reason`,
    not by expanding the status enum.
    """

    status: TaskExecutionStatus
    failure_stage: FailureStage | None = None
    failure_reason: str | None = None
    route_plan_id: str | None = None
    replay_results: list[dict[str, Any]] = Field(default_factory=list)
    postcondition_results: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[ArtifactReference] = Field(default_factory=list)
    final_state_summary: str | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Artifact placeholder
# ---------------------------------------------------------------------------


class ArtifactReference(BaseModel):
    """Placeholder reference to an artifact produced during execution.

    This is intentionally minimal; artifact lifecycle (capture, storage,
    retention, download) is out of scope for 11.1.1.
    """

    kind: str
    label: str
    uri: str | None = None
    status: str = "pending"
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent D / Agent E contracts
# ---------------------------------------------------------------------------


class AgentDPlannerInput(BaseModel):
    """Input contract for Agent D (planner).

    This schema only defines the contract shape; prompt construction,
    LLM invocation, and runtime logic are out of scope for 11.1.1.
    """

    task_intent: TaskIntent
    candidates: list[LearnedPathCandidate] = Field(default_factory=list)
    slot_proposals: list[SlotBindingProposal] = Field(default_factory=list)
    negative_evidence_summaries: list[str] = Field(default_factory=list)
    replay_evidence_summaries: list[str] = Field(default_factory=list)


class AgentDPlannerOutput(BaseModel):
    """Output contract for Agent D (planner)."""

    route_plan: RoutePlan | None = None
    confirmation_requirements: list[ConfirmationRequirement] = Field(
        default_factory=list
    )
    risk_hints: list[RiskHint] = Field(default_factory=list)
    consent_requirements: list[ConsentRequirement] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AgentEReporterInput(BaseModel):
    """Input contract for Agent E (reporter).

    This schema only defines the contract shape; prompt construction,
    LLM invocation, and runtime logic are out of scope for 11.1.1.
    """

    task_execution_result: TaskExecutionResult
    postcondition_results: list[PostconditionSignal] = Field(default_factory=list)
    artifact_references: list[ArtifactReference] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    final_state_evidence: dict[str, Any] = Field(default_factory=dict)


class AgentEReporterOutput(BaseModel):
    """Output contract for Agent E (reporter)."""

    status: TaskExecutionStatus
    user_facing_summary: str
    evidence_summary: str | None = None
    uncertainty: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_suggested_action: str | None = None
