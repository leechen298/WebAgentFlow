from __future__ import annotations

from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SuccessCriteriaCategory(StrEnum):
    SUBMIT_SUCCESS = "submit_success"
    SEARCH_SUCCESS = "search_success"
    OPEN_SUCCESS = "open_success"
    SAVE_SUCCESS = "save_success"
    FILTER_SUCCESS = "filter_success"
    WEAK_SUCCESS_NO_ERROR = "weak_success_no_error"
    CUSTOM = "custom"


class SuccessCriteriaStrength(StrEnum):
    STRONG = "strong"
    WEAK = "weak"


class SuccessCriteriaCreatedBy(StrEnum):
    SYSTEM = "system"
    USER = "user"


class SuccessCriteria(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "success_criteria"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[SuccessCriteriaCategory] = mapped_column(
        String(32),
        default=SuccessCriteriaCategory.CUSTOM,
        nullable=False,
    )
    strength: Mapped[SuccessCriteriaStrength] = mapped_column(
        String(16),
        default=SuccessCriteriaStrength.STRONG,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    conditions_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    created_by: Mapped[SuccessCriteriaCreatedBy] = mapped_column(
        String(16),
        default=SuccessCriteriaCreatedBy.USER,
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
