from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.success_criteria import SuccessCriteria


class SuccessCriteriaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_page(
        self,
        limit: int = 20,
        cursor_created_at: datetime | None = None,
        cursor_id: str | None = None,
    ) -> tuple[list[SuccessCriteria], bool]:
        stmt = select(SuccessCriteria).order_by(
            SuccessCriteria.created_at.desc(), SuccessCriteria.id.desc()
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

    def get(self, criteria_id: str) -> SuccessCriteria | None:
        return self.session.get(SuccessCriteria, criteria_id)

    def create(self, criteria: SuccessCriteria) -> SuccessCriteria:
        self.session.add(criteria)
        self.session.commit()
        self.session.refresh(criteria)
        return criteria

    def update(self, criteria: SuccessCriteria) -> SuccessCriteria:
        self.session.add(criteria)
        self.session.commit()
        self.session.refresh(criteria)
        return criteria

    def delete(self, criteria: SuccessCriteria) -> None:
        self.session.delete(criteria)
        self.session.commit()
