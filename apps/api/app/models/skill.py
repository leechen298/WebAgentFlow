from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.recording import Recording
    from app.models.run import Run


class SkillStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Skill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(64), default="1.0.0", nullable=False)
    status: Mapped[SkillStatus] = mapped_column(
        String(32),
        default=SkillStatus.DRAFT,
        nullable=False,
    )
    recording_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("recordings.id", ondelete="SET NULL"),
        nullable=True,
    )
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    recording: Mapped[Recording | None] = relationship(back_populates="skills")
    runs: Mapped[list[Run]] = relationship(
        back_populates="skill",
        cascade="all, delete-orphan",
    )
