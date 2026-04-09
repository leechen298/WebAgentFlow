from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.run import Run


class RunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Run]:
        stmt = select(Run).order_by(Run.created_at.desc())
        return list(self.session.scalars(stmt).all())

    def list_page(
        self,
        limit: int = 20,
        cursor_created_at: datetime | None = None,
        cursor_id: str | None = None,
    ) -> tuple[list[Run], bool]:
        stmt = select(Run).order_by(Run.created_at.desc(), Run.id.desc())
        if cursor_created_at is not None and cursor_id is not None:
            stmt = stmt.where(
                or_(
                    Run.created_at < cursor_created_at,
                    and_(Run.created_at == cursor_created_at, Run.id < cursor_id),
                )
            )
        items = list(self.session.scalars(stmt.limit(limit + 1)).all())
        has_next = len(items) > limit
        if has_next:
            items = items[:limit]
        return items, has_next

    def get(self, run_id: str) -> Run | None:
        return self.session.get(Run, run_id)

    def create(self, run: Run) -> Run:
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def update(self, run: Run) -> Run:
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def delete(self, run: Run) -> None:
        self.session.delete(run)
        self.session.commit()
