from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.success_criteria import (
    SuccessCriteriaCategory,
    SuccessCriteriaCreatedBy,
    SuccessCriteriaStrength,
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
