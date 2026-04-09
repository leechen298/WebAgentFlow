from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repos.run_repo import RunRepository
from app.repos.skill_repo import SkillRepository
from app.schemas.common import ApiResponse, CursorPage, decode_cursor, encode_cursor
from app.schemas.run import RunCreate, RunRead, RunUpdate
from app.services.run_service import RunService

router = APIRouter(prefix="/runs", tags=["runs"])
DbSession = Annotated[Session, Depends(get_db)]


def get_service(db: Session) -> RunService:
    return RunService(RunRepository(db), SkillRepository(db))


@router.get("/list", response_model=ApiResponse[CursorPage[RunRead]])
def list_runs(
    db: DbSession,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
) -> ApiResponse[CursorPage[RunRead]]:
    cursor_created_at = cursor_id = None
    if cursor:
        cursor_created_at, cursor_id = decode_cursor(cursor)
    items, has_next = get_service(db).list_runs_page(limit, cursor_created_at, cursor_id)
    next_cursor = encode_cursor(items[-1].created_at, items[-1].id) if has_next and items else None
    return ApiResponse(data=CursorPage(items=items, has_next=has_next, next_cursor=next_cursor))


@router.post("/create", response_model=ApiResponse[RunRead])
def create_run(payload: RunCreate, db: DbSession) -> ApiResponse[RunRead]:
    return ApiResponse(data=get_service(db).create_run(payload))


@router.get("/get", response_model=ApiResponse[RunRead])
def get_run(run_id: Annotated[str, Query(...)], db: DbSession) -> ApiResponse[RunRead]:
    return ApiResponse(data=get_service(db).get_run(run_id))


class RunUpdatePayload(BaseModel):
    run_id: str
    update_data: RunUpdate


@router.post("/update", response_model=ApiResponse[RunRead])
def update_run(
    payload: RunUpdatePayload,
    db: DbSession,
) -> ApiResponse[RunRead]:
    return ApiResponse(data=get_service(db).update_run(payload.run_id, payload.update_data))


class RunDeletePayload(BaseModel):
    run_id: str


@router.post("/delete", response_model=ApiResponse[dict[str, str]])
def delete_run(payload: RunDeletePayload, db: DbSession) -> ApiResponse[dict[str, str]]:
    get_service(db).delete_run(payload.run_id)
    return ApiResponse(data={"run_id": payload.run_id})
