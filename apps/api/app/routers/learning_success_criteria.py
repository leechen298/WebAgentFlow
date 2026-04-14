from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repos.success_criteria_repo import SuccessCriteriaRepository
from app.schemas.common import ApiResponse, CursorPage, decode_cursor, encode_cursor
from app.schemas.success_criteria import (
    SuccessCriteriaCreate,
    SuccessCriteriaRead,
    SuccessCriteriaUpdate,
)
from app.services.success_criteria_service import SuccessCriteriaService

router = APIRouter(prefix="/learning/success-criteria", tags=["learning"])
DbSession = Annotated[Session, Depends(get_db)]


def _service(db: Session) -> SuccessCriteriaService:
    return SuccessCriteriaService(SuccessCriteriaRepository(db))


@router.get("/list", response_model=ApiResponse[CursorPage[SuccessCriteriaRead]])
def list_success_criteria(
    db: DbSession,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
) -> ApiResponse[CursorPage[SuccessCriteriaRead]]:
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


@router.post("/create", response_model=ApiResponse[SuccessCriteriaRead])
def create_success_criteria(
    payload: SuccessCriteriaCreate, db: DbSession
) -> ApiResponse[SuccessCriteriaRead]:
    return ApiResponse(data=_service(db).create(payload))


@router.get("/get", response_model=ApiResponse[SuccessCriteriaRead])
def get_success_criteria(
    criteria_id: Annotated[str, Query(...)], db: DbSession
) -> ApiResponse[SuccessCriteriaRead]:
    return ApiResponse(data=_service(db).get(criteria_id))


class SuccessCriteriaUpdatePayload(BaseModel):
    criteria_id: str
    update_data: SuccessCriteriaUpdate


@router.post("/update", response_model=ApiResponse[SuccessCriteriaRead])
def update_success_criteria(
    payload: SuccessCriteriaUpdatePayload, db: DbSession
) -> ApiResponse[SuccessCriteriaRead]:
    return ApiResponse(
        data=_service(db).update(payload.criteria_id, payload.update_data)
    )


class SuccessCriteriaDeletePayload(BaseModel):
    criteria_id: str


@router.post("/delete", response_model=ApiResponse[dict[str, str]])
def delete_success_criteria(
    payload: SuccessCriteriaDeletePayload, db: DbSession
) -> ApiResponse[dict[str, str]]:
    _service(db).delete(payload.criteria_id)
    return ApiResponse(data={"criteria_id": payload.criteria_id})
