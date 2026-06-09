"""CompositionCandidate ORM for automatic capability composition attempts."""

from __future__ import annotations

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CompositionCandidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "composition_candidates"

    candidate_id: Mapped[str] = mapped_column(String(96), unique=True, nullable=False)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    target_scope_ref: Mapped[str] = mapped_column(String(96), nullable=False)
    page_template: Mapped[str] = mapped_column(String(512), nullable=False)
    query_signature: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    dom_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    candidate_family: Mapped[str] = mapped_column(String(64), nullable=False)
    source_capability_ids_json: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False
    )
    ordered_capability_kinds_json: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False
    )
    expected_terminal_target_json: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False
    )
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    generation_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    static_rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_outcome_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    promotion_decision_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    negative_evidence_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    learning_batch_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    promoted_learned_path_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
