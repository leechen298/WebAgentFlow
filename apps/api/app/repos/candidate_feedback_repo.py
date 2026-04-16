from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.candidate_feedback import CandidateFeedback


class CandidateFeedbackRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_page(
        self,
        limit: int = 20,
        cursor_created_at: datetime | None = None,
        cursor_id: str | None = None,
    ) -> tuple[list[CandidateFeedback], bool]:
        stmt = select(CandidateFeedback).order_by(
            CandidateFeedback.created_at.desc(), CandidateFeedback.id.desc()
        )
        items = list(self.session.scalars(stmt).all())
        if cursor_created_at is not None and cursor_id is not None:
            items = [
                item for item in items
                if (item.created_at, item.id) < (cursor_created_at, cursor_id)
            ]
        items = items[: limit + 1]
        has_next = len(items) > limit
        if has_next:
            items = items[:limit]
        return items, has_next

    def list_by_recording(
        self,
        recording_id: str,
        run_id: str | None = None,
    ) -> list[CandidateFeedback]:
        stmt = select(CandidateFeedback).where(
            CandidateFeedback.recording_id == recording_id
        )
        if run_id is not None:
            stmt = stmt.where(CandidateFeedback.run_id == run_id)
        stmt = stmt.order_by(CandidateFeedback.created_at.desc())
        return list(self.session.scalars(stmt).all())

    def get(self, feedback_id: str) -> CandidateFeedback | None:
        return self.session.get(CandidateFeedback, feedback_id)

    def get_by_key(
        self,
        recording_id: str,
        element_key: str,
        run_id: str | None = None,
    ) -> CandidateFeedback | None:
        stmt = select(CandidateFeedback).where(
            CandidateFeedback.recording_id == recording_id,
            CandidateFeedback.element_key == element_key,
        )
        if run_id is not None:
            stmt = stmt.where(CandidateFeedback.run_id == run_id)
        else:
            stmt = stmt.where(CandidateFeedback.run_id.is_(None))
        return self.session.scalars(stmt).first()

    def create(self, feedback: CandidateFeedback) -> CandidateFeedback:
        self.session.add(feedback)
        self.session.commit()
        self.session.refresh(feedback)
        return feedback

    def update(self, feedback: CandidateFeedback) -> CandidateFeedback:
        self.session.add(feedback)
        self.session.commit()
        self.session.refresh(feedback)
        return feedback

    def delete(self, feedback: CandidateFeedback) -> None:
        self.session.delete(feedback)
        self.session.commit()
