from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.recording import Recording


class RecordingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Recording]:
        stmt = select(Recording).order_by(Recording.created_at.desc())
        return list(self.session.scalars(stmt).all())

    def list_page(
        self,
        limit: int = 20,
        cursor_created_at: datetime | None = None,
        cursor_id: str | None = None,
    ) -> tuple[list[Recording], bool]:
        stmt = select(Recording).order_by(Recording.created_at.desc(), Recording.id.desc())
        if cursor_created_at is not None and cursor_id is not None:
            stmt = stmt.where(
                or_(
                    Recording.created_at < cursor_created_at,
                    and_(Recording.created_at == cursor_created_at, Recording.id < cursor_id),
                )
            )
        items = list(self.session.scalars(stmt.limit(limit + 1)).all())
        has_next = len(items) > limit
        if has_next:
            items = items[:limit]
        return items, has_next

    def get(self, recording_id: str) -> Recording | None:
        return self.session.get(Recording, recording_id)

    def create(self, recording: Recording) -> Recording:
        self.session.add(recording)
        self.session.commit()
        self.session.refresh(recording)
        return recording

    def update(self, recording: Recording) -> Recording:
        self.session.add(recording)
        self.session.commit()
        self.session.refresh(recording)
        return recording

    def delete(self, recording: Recording) -> None:
        self.session.delete(recording)
        self.session.commit()
