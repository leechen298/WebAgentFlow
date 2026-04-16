from __future__ import annotations

from datetime import datetime

from app.core.exceptions import NotFoundError
from app.models.exploration_run import ExplorationRun
from app.repos.exploration_run_repo import ExplorationRunRepository
from app.schemas.exploration_run import ExplorationRunCreate, ExplorationRunUpdate


class ExplorationRunService:
    def __init__(self, repo: ExplorationRunRepository) -> None:
        self.repo = repo

    def list_page(
        self,
        limit: int = 20,
        cursor_created_at: datetime | None = None,
        cursor_id: str | None = None,
    ) -> tuple[list[ExplorationRun], bool]:
        return self.repo.list_page(limit, cursor_created_at, cursor_id)

    def create(self, payload: ExplorationRunCreate) -> ExplorationRun:
        run = ExplorationRun(**payload.model_dump())
        return self.repo.create(run)

    def get(self, run_id: str) -> ExplorationRun:
        run = self.repo.get(run_id)
        if run is None:
            raise NotFoundError("ExplorationRun", run_id)
        return run

    def update(self, run_id: str, payload: ExplorationRunUpdate) -> ExplorationRun:
        run = self.get(run_id)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(run, field, value)
        return self.repo.update(run)

    def delete(self, run_id: str) -> None:
        run = self.get(run_id)
        self.repo.delete(run)
