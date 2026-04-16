from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.success_criteria import (
    SuccessCriteriaCategory,
    SuccessCriteriaCreatedBy,
    SuccessCriteriaStrength,
)


# ───────────────────────────────────────────────────────────────────
# Structured condition (replaces opaque dict in conditions_json)
# ───────────────────────────────────────────────────────────────────

ConditionType = Literal[
    "url_changed",
    "url_contains",
    "title_contains",
    "element_present",
    "html_changed",
    "no_error",
]


class SuccessCondition(BaseModel):
    """A single evaluable condition within a SuccessCriteria.

    First-version design: flat list, AND relationship between conditions.
    ``required=True`` conditions must all pass for ``satisfied=True``.
    ``required=False`` conditions contribute to confidence but don't block.
    """

    type: ConditionType
    value: str | None = Field(
        default=None,
        description="Condition payload: substring, CSS selector, regex pattern, etc. "
        "Interpretation depends on ``type``.",
    )
    value_from: str | None = Field(
        default=None,
        description="Variable name to resolve ``value`` from task variables at runtime. "
        "When set, overrides ``value``.",
    )
    required: bool = Field(
        default=True,
        description="If True, this condition must be satisfied for overall success. "
        "If False, it only affects confidence.",
    )


# ───────────────────────────────────────────────────────────────────
# Evaluation result
# ───────────────────────────────────────────────────────────────────

class SuccessEvaluation(BaseModel):
    """Result of evaluating a SuccessCriteria against before/after state.

    Three-state semantics:
      - satisfied=True, confidence=high  → strong success
      - satisfied=False, confidence=high → definite failure
      - satisfied=False, confidence=low, uncertain_reason set → uncertain,
        should NOT be treated as definite failure
    """

    satisfied: bool = False
    strength: SuccessCriteriaStrength = SuccessCriteriaStrength.WEAK
    confidence: Literal["high", "medium", "low"] = "low"
    matched_conditions: list[str] = Field(
        default_factory=list,
        description="Condition types that were satisfied.",
    )
    failed_conditions: list[str] = Field(
        default_factory=list,
        description="Required condition types that were NOT satisfied.",
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw evidence collected during evaluation: "
        "url_before, url_after, title_after, html_changed, etc.",
    )
    uncertain_reason: str | None = Field(
        default=None,
        description="When confidence is low, explains why the result is uncertain. "
        "Presence of this field signals 'do not treat as definite failure'.",
    )


class SuccessCriteriaBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: SuccessCriteriaCategory = SuccessCriteriaCategory.CUSTOM
    strength: SuccessCriteriaStrength = SuccessCriteriaStrength.STRONG
    description: str | None = Field(default=None, max_length=1000)
    conditions_json: list[dict[str, Any]] = Field(default_factory=list)
    created_by: SuccessCriteriaCreatedBy = SuccessCriteriaCreatedBy.USER
    enabled: bool = True


class SuccessCriteriaCreate(SuccessCriteriaBase):
    pass


class SuccessCriteriaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: SuccessCriteriaCategory | None = None
    strength: SuccessCriteriaStrength | None = None
    description: str | None = Field(default=None, max_length=1000)
    conditions_json: list[dict[str, Any]] | None = None
    created_by: SuccessCriteriaCreatedBy | None = None
    enabled: bool | None = None


class SuccessCriteriaRead(SuccessCriteriaBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
