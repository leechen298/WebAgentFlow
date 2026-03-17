from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repos.recording_repo import RecordingRepository
from app.repos.skill_repo import SkillRepository
from app.schemas.skill import SkillCreate, SkillRead, SkillUpdate
from app.services.skill_service import SkillService

router = APIRouter(prefix="/skills", tags=["skills"])
DbSession = Annotated[Session, Depends(get_db)]


def get_service(db: Session) -> SkillService:
    return SkillService(SkillRepository(db), RecordingRepository(db))


@router.get("", response_model=list[SkillRead])
def list_skills(db: DbSession) -> list[SkillRead]:
    return get_service(db).list_skills()


@router.post("", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
def create_skill(payload: SkillCreate, db: DbSession) -> SkillRead:
    return get_service(db).create_skill(payload)


@router.get("/{skill_id}", response_model=SkillRead)
def get_skill(skill_id: str, db: DbSession) -> SkillRead:
    return get_service(db).get_skill(skill_id)


@router.patch("/{skill_id}", response_model=SkillRead)
def update_skill(
    skill_id: str,
    payload: SkillUpdate,
    db: DbSession,
) -> SkillRead:
    return get_service(db).update_skill(skill_id, payload)


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(skill_id: str, db: DbSession) -> Response:
    get_service(db).delete_skill(skill_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
