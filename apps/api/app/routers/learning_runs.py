from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repos.exploration_run_repo import ExplorationRunRepository
from app.schemas.common import ApiResponse, CursorPage, decode_cursor, encode_cursor
from app.schemas.exploration_run import (
    ExplorationRunCreate,
    ExplorationRunRead,
    ExplorationRunUpdate,
)
from app.services.exploration_run_service import ExplorationRunService

router = APIRouter(prefix="/learning/runs", tags=["learning"])
DbSession = Annotated[Session, Depends(get_db)]


def _service(db: Session) -> ExplorationRunService:
    return ExplorationRunService(ExplorationRunRepository(db))


@router.get("/list", response_model=ApiResponse[CursorPage[ExplorationRunRead]])
def list_exploration_runs(
    db: DbSession,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
) -> ApiResponse[CursorPage[ExplorationRunRead]]:
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


@router.post("/create", response_model=ApiResponse[ExplorationRunRead])
def create_exploration_run(
    payload: ExplorationRunCreate, db: DbSession
) -> ApiResponse[ExplorationRunRead]:
    return ApiResponse(data=_service(db).create(payload))


@router.get("/get", response_model=ApiResponse[ExplorationRunRead])
def get_exploration_run(
    run_id: Annotated[str, Query(...)], db: DbSession
) -> ApiResponse[ExplorationRunRead]:
    return ApiResponse(data=_service(db).get(run_id))


class ExplorationRunUpdatePayload(BaseModel):
    run_id: str
    update_data: ExplorationRunUpdate


@router.post("/update", response_model=ApiResponse[ExplorationRunRead])
def update_exploration_run(
    payload: ExplorationRunUpdatePayload, db: DbSession
) -> ApiResponse[ExplorationRunRead]:
    return ApiResponse(
        data=_service(db).update(payload.run_id, payload.update_data)
    )


class ExplorationRunDeletePayload(BaseModel):
    run_id: str


@router.post("/delete", response_model=ApiResponse[dict[str, str]])
def delete_exploration_run(
    payload: ExplorationRunDeletePayload, db: DbSession
) -> ApiResponse[dict[str, str]]:
    _service(db).delete(payload.run_id)
    return ApiResponse(data={"run_id": payload.run_id})
