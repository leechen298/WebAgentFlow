from datetime import datetime

from app.core.exceptions import NotFoundError
from app.models.skill import Skill
from app.repos.recording_repo import RecordingRepository
from app.repos.skill_repo import SkillRepository
from app.schemas.skill import SkillCreate, SkillUpdate


class SkillService:
    def __init__(
        self,
        skill_repo: SkillRepository,
        recording_repo: RecordingRepository,
    ) -> None:
        self.skill_repo = skill_repo
        self.recording_repo = recording_repo

    def list_skills(self) -> list[Skill]:
        return self.skill_repo.list()

    def list_skills_page(
        self,
        limit: int = 20,
        cursor_created_at: datetime | None = None,
        cursor_id: str | None = None,
    ) -> tuple[list[Skill], bool]:
        return self.skill_repo.list_page(limit, cursor_created_at, cursor_id)

    def create_skill(self, payload: SkillCreate) -> Skill:
        data = payload.model_dump()
        self._ensure_recording_exists(data.get("recording_id"))
        skill = Skill(**data)
        return self.skill_repo.create(skill)

    def get_skill(self, skill_id: str) -> Skill:
        skill = self.skill_repo.get(skill_id)
        if skill is None:
            raise NotFoundError("Skill", skill_id)
        return skill

    def update_skill(self, skill_id: str, payload: SkillUpdate) -> Skill:
        skill = self.get_skill(skill_id)
        updates = payload.model_dump(exclude_unset=True)
        if "recording_id" in updates:
            self._ensure_recording_exists(updates["recording_id"])
        for field, value in updates.items():
            setattr(skill, field, value)
        return self.skill_repo.update(skill)

    def delete_skill(self, skill_id: str) -> None:
        skill = self.get_skill(skill_id)
        self.skill_repo.delete(skill)

    def _ensure_recording_exists(self, recording_id: str | None) -> None:
        if recording_id is None:
            return
        if self.recording_repo.get(recording_id) is None:
            raise NotFoundError("Recording", recording_id)
