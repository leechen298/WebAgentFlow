"""LearnedPath data access.

This repo is the designated shell-interception point (see
``product-model.md`` §10.7): if a future shell layer ever needs to
encrypt, mirror, or redact LearnedPath data, it wraps this class —
routers never talk to the DB directly.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.learned_path import (
    LearnedPath,
    Provenance,
    TrustStatus,
    is_legal_trust_transition,
)
from app.schemas.common import decode_cursor, encode_cursor


def compute_dedup_key(
    *,
    page_template: str,
    query_signature: dict[str, str],
    dom_fingerprint: str,
    scenario: str,
) -> str:
    """Stable sha256 hex over the LearnedPath identity quadruple.

    The payload is a canonically-ordered JSON blob so two callers
    with the same inputs always land on the same key, regardless of
    dict iteration order.
    """
    payload = json.dumps(
        {
            "page_template": page_template,
            "query_signature": query_signature,
            "dom_fingerprint": dom_fingerprint,
            "scenario": scenario,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class LearnedPathRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def ingest_run(
        self,
        *,
        page_template: str,
        query_signature: dict[str, str],
        dom_fingerprint: str,
        scenario: str,
        actions: list[dict],
        source_run_id: str | None,
        provenance: Provenance = Provenance.SYSTEM,
    ) -> tuple[LearnedPath, bool]:
        """Insert or bump hit_count for a LearnedPath.

        Returns ``(row, created)``. ``created`` is True only on a
        fresh insert; on a dedup hit we increment ``hit_count`` on
        the existing row, do not overwrite ``actions`` (the earliest
        successful path wins), and keep the original
        ``source_run_id``.
        """
        key = compute_dedup_key(
            page_template=page_template,
            query_signature=query_signature,
            dom_fingerprint=dom_fingerprint,
            scenario=scenario,
        )

        existing = self._find_by_dedup_key(key)
        if existing is not None:
            existing.hit_count = (existing.hit_count or 0) + 1
            self.session.commit()
            self.session.refresh(existing)
            return existing, False

        row = LearnedPath(
            page_template=page_template,
            query_signature=query_signature,
            dom_fingerprint=dom_fingerprint,
            scenario=scenario,
            actions=actions,
            provenance=provenance,
            trust=TrustStatus.PROVISIONAL,
            hit_count=1,
            source_run_id=source_run_id,
            dedup_key=key,
        )
        self.session.add(row)
        try:
            self.session.commit()
        except IntegrityError:
            # Two concurrent ingests raced on the unique key. The
            # loser rolls back and treats the winner's row as the
            # existing hit; preserves idempotency under concurrency.
            self.session.rollback()
            existing = self._find_by_dedup_key(key)
            if existing is None:
                # Couldn't recover — re-raise so the caller sees it.
                raise
            existing.hit_count = (existing.hit_count or 0) + 1
            self.session.commit()
            self.session.refresh(existing)
            return existing, False

        self.session.refresh(row)
        return row, True

    def set_trust(
        self,
        path_id: str,
        status: TrustStatus,
        reason: str | None,
    ) -> LearnedPath:
        """Transition a path's trust state.

        Raises ``ValueError`` for unknown id or an illegal transition
        so the router can translate to 404 / 422 respectively.
        """
        row = self.get(path_id)
        if row is None:
            raise ValueError(f"learned_path not found: {path_id}")
        current = TrustStatus(row.trust)
        if not is_legal_trust_transition(current, status):
            raise ValueError(
                f"illegal trust transition: {current.value} -> {status.value}"
            )
        row.trust = status
        row.trust_reason = reason
        row.trust_updated_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(row)
        return row

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    def get(self, path_id: str) -> LearnedPath | None:
        return self.session.get(LearnedPath, path_id)

    def find_by_source_run(self, run_id: str) -> LearnedPath | None:
        stmt = (
            select(LearnedPath)
            .where(LearnedPath.source_run_id == run_id)
            .order_by(LearnedPath.created_at.desc())
            .limit(1)
        )
        return self.session.scalars(stmt).first()

    def list_page(
        self,
        *,
        page_template: str | None = None,
        scenario: str | None = None,
        trust: TrustStatus | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[LearnedPath], bool, str | None]:
        """Return a page of LearnedPaths ordered newest-first.

        Cursor filtering is done Python-side (matching the existing
        ``ExplorationRunRepository.list_page``) so the semantics stay
        consistent across SQLite tests and Postgres runtime without
        dialect-specific timestamp-comparison quirks.
        """
        stmt = select(LearnedPath)
        if page_template is not None:
            stmt = stmt.where(LearnedPath.page_template == page_template)
        if scenario is not None:
            stmt = stmt.where(LearnedPath.scenario == scenario)
        if trust is not None:
            stmt = stmt.where(LearnedPath.trust == trust)
        stmt = stmt.order_by(
            LearnedPath.created_at.desc(), LearnedPath.id.desc()
        )

        rows = list(self.session.scalars(stmt).all())
        if cursor:
            cursor_ts, cursor_id = decode_cursor(cursor)
            rows = [
                row
                for row in rows
                if (row.created_at, row.id) < (cursor_ts, cursor_id)
            ]
        windowed = rows[: limit + 1]
        has_next = len(windowed) > limit
        if has_next:
            windowed = windowed[:limit]
        next_cursor: str | None = None
        if has_next and windowed:
            tail = windowed[-1]
            next_cursor = encode_cursor(tail.created_at, tail.id)
        return windowed, has_next, next_cursor

    def count(self) -> int:
        return int(self.session.scalar(select(func.count(LearnedPath.id))) or 0)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _find_by_dedup_key(self, key: str) -> LearnedPath | None:
        stmt = select(LearnedPath).where(LearnedPath.dedup_key == key).limit(1)
        return self.session.scalars(stmt).first()
