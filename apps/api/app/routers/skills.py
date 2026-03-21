from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel
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


@router.get("/list", response_model=list[SkillRead])
def list_skills(db: DbSession) -> list[SkillRead]:
    return get_service(db).list_skills()


@router.post("/create", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
def create_skill(payload: SkillCreate, db: DbSession) -> SkillRead:
    return get_service(db).create_skill(payload)


@router.get("/get", response_model=SkillRead)
def get_skill(skill_id: Annotated[str, Query(...)], db: DbSession) -> SkillRead:
    return get_service(db).get_skill(skill_id)


class SkillUpdatePayload(BaseModel):
    skill_id: str
    update_data: SkillUpdate


@router.post("/update", response_model=SkillRead)
def update_skill(
    payload: SkillUpdatePayload,
    db: DbSession,
) -> SkillRead:
    return get_service(db).update_skill(payload.skill_id, payload.update_data)


class SkillDeletePayload(BaseModel):
    skill_id: str


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(payload: SkillDeletePayload, db: DbSession) -> Response:
    get_service(db).delete_skill(payload.skill_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
