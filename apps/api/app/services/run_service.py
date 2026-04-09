from datetime import datetime

from app.core.exceptions import NotFoundError
from app.models.run import Run
from app.repos.run_repo import RunRepository
from app.repos.skill_repo import SkillRepository
from app.schemas.run import RunCreate, RunUpdate


class RunService:
    def __init__(
        self,
        run_repo: RunRepository,
        skill_repo: SkillRepository,
    ) -> None:
        self.run_repo = run_repo
        self.skill_repo = skill_repo

    def list_runs(self) -> list[Run]:
        return self.run_repo.list()

    def list_runs_page(
        self,
        limit: int = 20,
        cursor_created_at: datetime | None = None,
        cursor_id: str | None = None,
    ) -> tuple[list[Run], bool]:
        return self.run_repo.list_page(limit, cursor_created_at, cursor_id)

    def create_run(self, payload: RunCreate) -> Run:
        data = payload.model_dump()
        self._ensure_skill_exists(data["skill_id"])
        run = Run(**data)
        return self.run_repo.create(run)

    def get_run(self, run_id: str) -> Run:
        run = self.run_repo.get(run_id)
        if run is None:
            raise NotFoundError("Run", run_id)
        return run

    def update_run(self, run_id: str, payload: RunUpdate) -> Run:
        run = self.get_run(run_id)
        updates = payload.model_dump(exclude_unset=True)
        if "skill_id" in updates and updates["skill_id"] is not None:
            self._ensure_skill_exists(updates["skill_id"])
        for field, value in updates.items():
            setattr(run, field, value)
        return self.run_repo.update(run)

    def delete_run(self, run_id: str) -> None:
        run = self.get_run(run_id)
        self.run_repo.delete(run)

    def _ensure_skill_exists(self, skill_id: str) -> None:
        if self.skill_repo.get(skill_id) is None:
            raise NotFoundError("Skill", skill_id)
