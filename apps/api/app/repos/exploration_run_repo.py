from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.exploration_run import ExplorationRun


class ExplorationRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_page(
        self,
        limit: int = 20,
        cursor_created_at: datetime | None = None,
        cursor_id: str | None = None,
    ) -> tuple[list[ExplorationRun], bool]:
        stmt = select(ExplorationRun).order_by(
            ExplorationRun.created_at.desc(), ExplorationRun.id.desc()
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

    def get(self, run_id: str) -> ExplorationRun | None:
        return self.session.get(ExplorationRun, run_id)

    def create(self, run: ExplorationRun) -> ExplorationRun:
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def update(self, run: ExplorationRun) -> ExplorationRun:
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def delete(self, run: ExplorationRun) -> None:
        self.session.delete(run)
        self.session.commit()
