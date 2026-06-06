"""LearningBatch data access."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.learning_batch import (
    TERMINAL_LEARNING_BATCH_STATUSES,
    LearningBatch,
    LearningBatchStatus,
)
from app.schemas.common import decode_cursor, encode_cursor


class LearningBatchRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_pending(
        self,
        *,
        target_url: str,
        session_id: str | None,
        policy_json: dict[str, Any],
        request_json: dict[str, Any],
    ) -> LearningBatch:
        row = LearningBatch(
            session_id=session_id,
            target_url=target_url,
            status=LearningBatchStatus.PENDING,
            policy_json=policy_json,
            request_json=request_json,
        )
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row

    def get(self, batch_id: str, *, fresh: bool = False) -> LearningBatch | None:
        return self.session.get(LearningBatch, batch_id, populate_existing=fresh)

    def mark_running(
        self,
        batch_id: str,
        *,
        page_template: str | None = None,
        query_signature: dict[str, Any] | None = None,
        dom_fingerprint: str | None = None,
        planned_scenarios: list[dict[str, Any]] | None = None,
    ) -> LearningBatch:
        row = self._require_batch(batch_id, fresh=True)
        self._ensure_not_terminal(row)
        if LearningBatchStatus(row.status) == LearningBatchStatus.CANCEL_REQUESTED:
            raise ValueError(f"learning batch cancellation requested: {row.id}")
        row.status = LearningBatchStatus.RUNNING
        row.started_at = row.started_at or datetime.now(UTC)
        if page_template is not None:
            row.page_template = page_template
        if query_signature is not None:
            row.query_signature = query_signature
        if dom_fingerprint is not None:
            row.dom_fingerprint = dom_fingerprint
        if planned_scenarios is not None:
            row.planned_scenarios_json = planned_scenarios
        return self._commit(row)

    def request_cancel(self, batch_id: str, *, reason: str | None = None) -> LearningBatch:
        row = self._require_batch(batch_id)
        if self._is_terminal(row):
            return row
        row.status = LearningBatchStatus.CANCEL_REQUESTED
        row.cancel_requested_at = row.cancel_requested_at or datetime.now(UTC)
        summary = dict(row.summary_json or {})
        if reason:
            summary["cancel_reason"] = reason
        row.summary_json = summary
        return self._commit(row)

    def mark_terminal(
        self,
        batch_id: str,
        status: LearningBatchStatus,
        *,
        summary: dict[str, Any] | None = None,
        created_run_ids: list[str] | None = None,
        created_capability_ids: list[str] | None = None,
        created_learned_path_ids: list[str] | None = None,
    ) -> LearningBatch:
        if status not in TERMINAL_LEARNING_BATCH_STATUSES:
            raise ValueError(f"not a terminal learning batch status: {status}")
        row = self._require_batch(batch_id)
        if self._is_terminal(row):
            if row.status != status:
                raise ValueError(
                    f"learning batch already terminal: {row.status} != {status}"
                )
            return row
        row.status = status
        row.completed_at = row.completed_at or datetime.now(UTC)
        if summary is not None:
            row.summary_json = summary
        if created_run_ids is not None:
            row.created_run_ids_json = list(created_run_ids)
        if created_capability_ids is not None:
            row.created_capability_ids_json = list(created_capability_ids)
        if created_learned_path_ids is not None:
            row.created_learned_path_ids_json = list(created_learned_path_ids)
        return self._commit(row)

    def append_run(self, batch_id: str, run_id: str) -> LearningBatch:
        row = self._require_batch(batch_id)
        self._ensure_can_attach_asset(row)
        row.created_run_ids_json = _append_unique(row.created_run_ids_json or [], run_id)
        return self._commit(row)

    def append_capability(self, batch_id: str, capability_id: str) -> LearningBatch:
        row = self._require_batch(batch_id)
        self._ensure_can_attach_asset(row)
        row.created_capability_ids_json = _append_unique(
            row.created_capability_ids_json or [], capability_id
        )
        return self._commit(row)

    def append_learned_path(self, batch_id: str, learned_path_id: str) -> LearningBatch:
        row = self._require_batch(batch_id)
        self._ensure_can_attach_asset(row)
        row.created_learned_path_ids_json = _append_unique(
            row.created_learned_path_ids_json or [], learned_path_id
        )
        return self._commit(row)

    def list_for_session(
        self,
        session_id: str,
        *,
        status: LearningBatchStatus | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[LearningBatch], bool, str | None]:
        stmt = select(LearningBatch).where(LearningBatch.session_id == session_id)
        if status is not None:
            stmt = stmt.where(LearningBatch.status == status)
        if cursor:
            cursor_ts, cursor_id = decode_cursor(cursor)
            stmt = stmt.where(
                or_(
                    LearningBatch.created_at < cursor_ts,
                    and_(
                        LearningBatch.created_at == cursor_ts,
                        LearningBatch.id < cursor_id,
                    ),
                )
            )
        stmt = stmt.order_by(
            LearningBatch.created_at.desc(), LearningBatch.id.desc()
        ).limit(limit + 1)

        windowed = list(self.session.scalars(stmt).all())
        has_next = len(windowed) > limit
        if has_next:
            windowed = windowed[:limit]
        next_cursor: str | None = None
        if has_next and windowed:
            tail = windowed[-1]
            next_cursor = encode_cursor(tail.created_at, tail.id)
        return windowed, has_next, next_cursor

    def _require_batch(self, batch_id: str, *, fresh: bool = False) -> LearningBatch:
        row = self.get(batch_id, fresh=fresh)
        if row is None:
            raise ValueError(f"learning batch not found: {batch_id}")
        return row

    def _is_terminal(self, row: LearningBatch) -> bool:
        return LearningBatchStatus(row.status) in TERMINAL_LEARNING_BATCH_STATUSES

    def _ensure_not_terminal(self, row: LearningBatch) -> None:
        if self._is_terminal(row):
            raise ValueError(f"learning batch already terminal: {row.id}")

    def _ensure_can_attach_asset(self, row: LearningBatch) -> None:
        if LearningBatchStatus(row.status) == LearningBatchStatus.CANCELLED:
            raise ValueError(f"cannot attach assets to cancelled batch: {row.id}")
        self._ensure_not_terminal(row)

    def _commit(self, row: LearningBatch) -> LearningBatch:
        self.session.add(row)
        self.session.commit()
        self.session.refresh(row)
        return row


def _append_unique(items: list[Any], value: str) -> list[str]:
    result = [str(item) for item in items if item is not None]
    if value not in result:
        result.append(value)
    return result
