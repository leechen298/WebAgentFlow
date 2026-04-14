from __future__ import annotations

from datetime import datetime

from app.core.exceptions import NotFoundError
from app.models.learned_path import LearnedPath
from app.repos.learned_path_repo import LearnedPathRepository
from app.repos.success_criteria_repo import SuccessCriteriaRepository
from app.schemas.learned_path import LearnedPathCreate, LearnedPathUpdate


class LearnedPathService:
    def __init__(
        self,
        path_repo: LearnedPathRepository,
        criteria_repo: SuccessCriteriaRepository,
    ) -> None:
        self.path_repo = path_repo
        self.criteria_repo = criteria_repo

    def list_page(
        self,
        limit: int = 20,
        cursor_created_at: datetime | None = None,
        cursor_id: str | None = None,
    ) -> tuple[list[LearnedPath], bool]:
        return self.path_repo.list_page(limit, cursor_created_at, cursor_id)

    def create(self, payload: LearnedPathCreate) -> LearnedPath:
        data = payload.model_dump()
        self._ensure_criteria_exists(data.get("success_criteria_id"))
        path = LearnedPath(**data)
        return self.path_repo.create(path)

    def get(self, path_id: str) -> LearnedPath:
        path = self.path_repo.get(path_id)
        if path is None:
            raise NotFoundError("LearnedPath", path_id)
        return path

    def update(self, path_id: str, payload: LearnedPathUpdate) -> LearnedPath:
        path = self.get(path_id)
        updates = payload.model_dump(exclude_unset=True)
        if "success_criteria_id" in updates:
            self._ensure_criteria_exists(updates["success_criteria_id"])
        for field, value in updates.items():
            setattr(path, field, value)
        return self.path_repo.update(path)

    def delete(self, path_id: str) -> None:
        path = self.get(path_id)
        self.path_repo.delete(path)

    def _ensure_criteria_exists(self, criteria_id: str | None) -> None:
        if criteria_id is None:
            return
        if self.criteria_repo.get(criteria_id) is None:
            raise NotFoundError("SuccessCriteria", criteria_id)
