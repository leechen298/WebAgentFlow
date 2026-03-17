from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.skill import SkillStatus


class SkillBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    version: str = Field(default="1.0.0", min_length=1, max_length=64)
    status: SkillStatus = SkillStatus.DRAFT
    recording_id: str | None = None
    definition: dict[str, Any] = Field(default_factory=dict)
    description: str | None = Field(default=None, max_length=1000)


class SkillCreate(SkillBase):
    pass


class SkillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    version: str | None = Field(default=None, min_length=1, max_length=64)
    status: SkillStatus | None = None
    recording_id: str | None = None
    definition: dict[str, Any] | None = None
    description: str | None = Field(default=None, max_length=1000)


class SkillRead(SkillBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
