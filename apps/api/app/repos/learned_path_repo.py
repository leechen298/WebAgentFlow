from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.learned_path import LearnedPath


class LearnedPathRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_page(
        self,
        limit: int = 20,
        cursor_created_at: datetime | None = None,
        cursor_id: str | None = None,
    ) -> tuple[list[LearnedPath], bool]:
        stmt = select(LearnedPath).order_by(
            LearnedPath.created_at.desc(), LearnedPath.id.desc()
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

    def get(self, path_id: str) -> LearnedPath | None:
        return self.session.get(LearnedPath, path_id)

    def create(self, path: LearnedPath) -> LearnedPath:
        self.session.add(path)
        self.session.commit()
        self.session.refresh(path)
        return path

    def update(self, path: LearnedPath) -> LearnedPath:
        self.session.add(path)
        self.session.commit()
        self.session.refresh(path)
        return path

    def delete(self, path: LearnedPath) -> None:
        self.session.delete(path)
        self.session.commit()
