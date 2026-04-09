from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repos.recording_repo import RecordingRepository
from app.repos.skill_repo import SkillRepository
from app.schemas.common import ApiResponse, CursorPage, decode_cursor, encode_cursor
from app.schemas.skill import SkillCreate, SkillRead, SkillUpdate
from app.services.skill_service import SkillService

router = APIRouter(prefix="/skills", tags=["skills"])
DbSession = Annotated[Session, Depends(get_db)]


def get_service(db: Session) -> SkillService:
    return SkillService(SkillRepository(db), RecordingRepository(db))


@router.get("/list", response_model=ApiResponse[CursorPage[SkillRead]])
def list_skills(
    db: DbSession,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
) -> ApiResponse[CursorPage[SkillRead]]:
    cursor_created_at = cursor_id = None
    if cursor:
        cursor_created_at, cursor_id = decode_cursor(cursor)
    items, has_next = get_service(db).list_skills_page(limit, cursor_created_at, cursor_id)
    next_cursor = encode_cursor(items[-1].created_at, items[-1].id) if has_next and items else None
    return ApiResponse(data=CursorPage(items=items, has_next=has_next, next_cursor=next_cursor))


@router.post("/create", response_model=ApiResponse[SkillRead])
def create_skill(payload: SkillCreate, db: DbSession) -> ApiResponse[SkillRead]:
    return ApiResponse(data=get_service(db).create_skill(payload))


@router.get("/get", response_model=ApiResponse[SkillRead])
def get_skill(skill_id: Annotated[str, Query(...)], db: DbSession) -> ApiResponse[SkillRead]:
    return ApiResponse(data=get_service(db).get_skill(skill_id))


class SkillUpdatePayload(BaseModel):
    skill_id: str
    update_data: SkillUpdate


@router.post("/update", response_model=ApiResponse[SkillRead])
def update_skill(
    payload: SkillUpdatePayload,
    db: DbSession,
) -> ApiResponse[SkillRead]:
    return ApiResponse(data=get_service(db).update_skill(payload.skill_id, payload.update_data))


class SkillDeletePayload(BaseModel):
    skill_id: str


@router.post("/delete", response_model=ApiResponse[dict[str, str]])
def delete_skill(payload: SkillDeletePayload, db: DbSession) -> ApiResponse[dict[str, str]]:
    get_service(db).delete_skill(payload.skill_id)
    return ApiResponse(data={"skill_id": payload.skill_id})
