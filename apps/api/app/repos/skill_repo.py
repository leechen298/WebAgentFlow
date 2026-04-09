from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.skill import Skill


class SkillRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Skill]:
        stmt = select(Skill).order_by(Skill.created_at.desc())
        return list(self.session.scalars(stmt).all())

    def list_page(
        self,
        limit: int = 20,
        cursor_created_at: datetime | None = None,
        cursor_id: str | None = None,
    ) -> tuple[list[Skill], bool]:
        stmt = select(Skill).order_by(Skill.created_at.desc(), Skill.id.desc())
        if cursor_created_at is not None and cursor_id is not None:
            stmt = stmt.where(
                or_(
                    Skill.created_at < cursor_created_at,
                    and_(Skill.created_at == cursor_created_at, Skill.id < cursor_id),
                )
            )
        items = list(self.session.scalars(stmt.limit(limit + 1)).all())
        has_next = len(items) > limit
        if has_next:
            items = items[:limit]
        return items, has_next

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
