from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.skill import Skill


class SkillRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Skill]:
        stmt = select(Skill).order_by(Skill.created_at.desc())
        return list(self.session.scalars(stmt).all())

    def get(self, skill_id: str) -> Skill | None:
        return self.session.get(Skill, skill_id)

    def create(self, skill: Skill) -> Skill:
        self.session.add(skill)
        self.session.commit()
        self.session.refresh(skill)
        return skill

    def update(self, skill: Skill) -> Skill:
        self.session.add(skill)
        self.session.commit()
        self.session.refresh(skill)
        return skill

    def delete(self, skill: Skill) -> None:
        self.session.delete(skill)
        self.session.commit()
