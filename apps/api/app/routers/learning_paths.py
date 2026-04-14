from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repos.learned_path_repo import LearnedPathRepository
from app.repos.success_criteria_repo import SuccessCriteriaRepository
from app.schemas.common import ApiResponse, CursorPage, decode_cursor, encode_cursor
from app.schemas.learned_path import LearnedPathCreate, LearnedPathRead, LearnedPathUpdate
from app.services.learned_path_service import LearnedPathService

router = APIRouter(prefix="/learning/paths", tags=["learning"])
DbSession = Annotated[Session, Depends(get_db)]


def _service(db: Session) -> LearnedPathService:
    return LearnedPathService(LearnedPathRepository(db), SuccessCriteriaRepository(db))


@router.get("/list", response_model=ApiResponse[CursorPage[LearnedPathRead]])
def list_learned_paths(
    db: DbSession,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
) -> ApiResponse[CursorPage[LearnedPathRead]]:
    cursor_created_at = cursor_id = None
    if cursor:
        cursor_created_at, cursor_id = decode_cursor(cursor)
    items, has_next = _service(db).list_page(limit, cursor_created_at, cursor_id)
    next_cursor = (
        encode_cursor(items[-1].created_at, items[-1].id) if has_next and items else None
    )
    return ApiResponse(
        data=CursorPage(items=items, has_next=has_next, next_cursor=next_cursor)
    )


@router.post("/create", response_model=ApiResponse[LearnedPathRead])
def create_learned_path(
    payload: LearnedPathCreate, db: DbSession
) -> ApiResponse[LearnedPathRead]:
    return ApiResponse(data=_service(db).create(payload))


@router.get("/get", response_model=ApiResponse[LearnedPathRead])
def get_learned_path(
    path_id: Annotated[str, Query(...)], db: DbSession
) -> ApiResponse[LearnedPathRead]:
    return ApiResponse(data=_service(db).get(path_id))


class LearnedPathUpdatePayload(BaseModel):
    path_id: str
    update_data: LearnedPathUpdate


@router.post("/update", response_model=ApiResponse[LearnedPathRead])
def update_learned_path(
    payload: LearnedPathUpdatePayload, db: DbSession
) -> ApiResponse[LearnedPathRead]:
    return ApiResponse(data=_service(db).update(payload.path_id, payload.update_data))


class LearnedPathDeletePayload(BaseModel):
    path_id: str


@router.post("/delete", response_model=ApiResponse[dict[str, str]])
def delete_learned_path(
    payload: LearnedPathDeletePayload, db: DbSession
) -> ApiResponse[dict[str, str]]:
    _service(db).delete(payload.path_id)
    return ApiResponse(data={"path_id": payload.path_id})
