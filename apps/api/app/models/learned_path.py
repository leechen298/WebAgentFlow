"""LearnedPath ORM — delivery milestone M10 headline deliverable.

A LearnedPath is a reusable exploration outcome: after a successful
autonomous run (`pass_gate = pass`), the (page_template,
query_signature, dom_fingerprint, scenario) quadruple plus the action
sequence that produced the pass are persisted here. A future L3
planner Agent reads these rows to pick a concrete route for a user
task without ever reading raw HTML.

Schema notes (see docs/iterations/phase-10/01-learned-path-persistence):

- ``dedup_key`` is a sha256 of the key quadruple; the unique
  constraint lets ``ingest_run`` stay idempotent across DB backends
  without relying on JSONB expression indexes.
- ``trust_updated_at`` is nullable — only set when ``trust`` leaves
  its initial ``provisional`` state.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TrustStatus(StrEnum):
    PROVISIONAL = "provisional"
    CONFIRMED = "confirmed"
    FLAKY = "flaky"
    DEPRECATED = "deprecated"


class Provenance(StrEnum):
    SYSTEM = "system"
    USER = "user"


class LearnedPath(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learned_paths"
    __table_args__ = (
        UniqueConstraint("dedup_key", name="uq_learned_paths_dedup_key"),
    )

    page_template: Mapped[str] = mapped_column(String(512), nullable=False)
    query_signature: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    dom_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    actions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    provenance: Mapped[Provenance] = mapped_column(
        String(16),
        nullable=False,
        default=Provenance.SYSTEM,
    )
    trust: Mapped[TrustStatus] = mapped_column(
        String(16),
        nullable=False,
        default=TrustStatus.PROVISIONAL,
    )
    trust_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    trust_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("exploration_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    dedup_key: Mapped[str] = mapped_column(String(64), nullable=False)


_LEGAL_TRUST_TRANSITIONS: dict[TrustStatus, frozenset[TrustStatus]] = {
    TrustStatus.PROVISIONAL: frozenset(
        {TrustStatus.CONFIRMED, TrustStatus.DEPRECATED, TrustStatus.FLAKY}
    ),
    TrustStatus.CONFIRMED: frozenset({TrustStatus.DEPRECATED, TrustStatus.FLAKY}),
    TrustStatus.FLAKY: frozenset({TrustStatus.CONFIRMED, TrustStatus.DEPRECATED}),
    TrustStatus.DEPRECATED: frozenset({TrustStatus.CONFIRMED}),
}


def is_legal_trust_transition(current: TrustStatus, target: TrustStatus) -> bool:
    """Return True if ``current -> target`` is a permitted trust
    lifecycle transition.

    Defined alongside the model so both the repo (server-side
    enforcement) and tests can share the single source of truth.
    """
    if current == target:
        return False
    return target in _LEGAL_TRUST_TRANSITIONS.get(current, frozenset())
