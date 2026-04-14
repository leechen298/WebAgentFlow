from __future__ import annotations

from datetime import datetime

from app.core.exceptions import NotFoundError
from app.models.success_criteria import SuccessCriteria
from app.repos.success_criteria_repo import SuccessCriteriaRepository
from app.schemas.success_criteria import SuccessCriteriaCreate, SuccessCriteriaUpdate


class SuccessCriteriaService:
    def __init__(self, repo: SuccessCriteriaRepository) -> None:
        self.repo = repo

    def list_page(
        self,
        limit: int = 20,
        cursor_created_at: datetime | None = None,
        cursor_id: str | None = None,
    ) -> tuple[list[SuccessCriteria], bool]:
        return self.repo.list_page(limit, cursor_created_at, cursor_id)

    def create(self, payload: SuccessCriteriaCreate) -> SuccessCriteria:
        criteria = SuccessCriteria(**payload.model_dump())
        return self.repo.create(criteria)

    def get(self, criteria_id: str) -> SuccessCriteria:
        criteria = self.repo.get(criteria_id)
        if criteria is None:
            raise NotFoundError("SuccessCriteria", criteria_id)
        return criteria

    def update(self, criteria_id: str, payload: SuccessCriteriaUpdate) -> SuccessCriteria:
        criteria = self.get(criteria_id)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(criteria, field, value)
        return self.repo.update(criteria)

    def delete(self, criteria_id: str) -> None:
        criteria = self.get(criteria_id)
        self.repo.delete(criteria)
