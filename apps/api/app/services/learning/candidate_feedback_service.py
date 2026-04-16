from __future__ import annotations

from datetime import datetime

from app.core.exceptions import NotFoundError
from app.models.candidate_feedback import CandidateFeedback
from app.repos.candidate_feedback_repo import CandidateFeedbackRepository
from app.schemas.candidate_feedback import (
    CandidateFeedbackCreate,
    CandidateFeedbackUpdate,
)


class CandidateFeedbackService:
    def __init__(self, repo: CandidateFeedbackRepository) -> None:
        self.repo = repo

    def list_page(
        self,
        limit: int = 20,
        cursor_created_at: datetime | None = None,
        cursor_id: str | None = None,
    ) -> tuple[list[CandidateFeedback], bool]:
        return self.repo.list_page(limit, cursor_created_at, cursor_id)

    def list_by_recording(
        self,
        recording_id: str,
        run_id: str | None = None,
    ) -> list[CandidateFeedback]:
        return self.repo.list_by_recording(recording_id, run_id)

    def create(self, payload: CandidateFeedbackCreate) -> CandidateFeedback:
        feedback = CandidateFeedback(**payload.model_dump())
        return self.repo.create(feedback)

    def get(self, feedback_id: str) -> CandidateFeedback:
        feedback = self.repo.get(feedback_id)
        if feedback is None:
            raise NotFoundError("CandidateFeedback", feedback_id)
        return feedback

    def update(self, feedback_id: str, payload: CandidateFeedbackUpdate) -> CandidateFeedback:
        feedback = self.get(feedback_id)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(feedback, field, value)
        return self.repo.update(feedback)

    def upsert(self, payload: CandidateFeedbackCreate) -> CandidateFeedback:
        """Create or update feedback by (recording_id, element_key, run_id)."""
        existing = self.repo.get_by_key(
            payload.recording_id, payload.element_key, payload.run_id
        )
        if existing is not None:
            for field, value in payload.model_dump().items():
                if field not in ("recording_id", "element_key", "run_id"):
                    setattr(existing, field, value)
            return self.repo.update(existing)
        feedback = CandidateFeedback(**payload.model_dump())
        return self.repo.create(feedback)

    def delete(self, feedback_id: str) -> None:
        feedback = self.get(feedback_id)
        self.repo.delete(feedback)
