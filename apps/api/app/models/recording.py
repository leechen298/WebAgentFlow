from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.skill import Skill


class RecordingStatus(StrEnum):
    DRAFT = "draft"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Recording(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recordings"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[RecordingStatus] = mapped_column(
        String(32),
        default=RecordingStatus.DRAFT,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    events: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    skills: Mapped[list[Skill]] = relationship(back_populates="recording")
