from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.run import Run


class RunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Run]:
        stmt = select(Run).order_by(Run.created_at.desc())
        return list(self.session.scalars(stmt).all())

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
