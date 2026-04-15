from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repos.candidate_feedback_repo import CandidateFeedbackRepository
from app.schemas.candidate_feedback import (
    CandidateFeedbackCreate,
    CandidateFeedbackRead,
    CandidateFeedbackUpdate,
)
from app.schemas.common import ApiResponse, CursorPage, decode_cursor, encode_cursor
from app.services.candidate_feedback_service import CandidateFeedbackService

router = APIRouter(prefix="/learning/feedback", tags=["learning"])
DbSession = Annotated[Session, Depends(get_db)]


def _service(db: Session) -> CandidateFeedbackService:
    return CandidateFeedbackService(CandidateFeedbackRepository(db))


@router.get("/list", response_model=ApiResponse[CursorPage[CandidateFeedbackRead]])
def list_feedback(
    db: DbSession,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
) -> ApiResponse[CursorPage[CandidateFeedbackRead]]:
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


@router.get(
    "/list-by-recording",
    response_model=ApiResponse[list[CandidateFeedbackRead]],
)
def list_feedback_by_recording(
    recording_id: Annotated[str, Query(...)],
    db: DbSession,
    run_id: str | None = Query(None),
) -> ApiResponse[list[CandidateFeedbackRead]]:
    items = _service(db).list_by_recording(recording_id, run_id)
    return ApiResponse(data=items)


@router.post("/create", response_model=ApiResponse[CandidateFeedbackRead])
def create_feedback(
    payload: CandidateFeedbackCreate, db: DbSession
) -> ApiResponse[CandidateFeedbackRead]:
    return ApiResponse(data=_service(db).create(payload))


@router.post("/upsert", response_model=ApiResponse[CandidateFeedbackRead])
def upsert_feedback(
    payload: CandidateFeedbackCreate, db: DbSession
) -> ApiResponse[CandidateFeedbackRead]:
    """Create or update feedback by (recording_id, element_key, run_id)."""
    return ApiResponse(data=_service(db).upsert(payload))


@router.get("/get", response_model=ApiResponse[CandidateFeedbackRead])
def get_feedback(
    feedback_id: Annotated[str, Query(...)], db: DbSession
) -> ApiResponse[CandidateFeedbackRead]:
    return ApiResponse(data=_service(db).get(feedback_id))


class FeedbackUpdatePayload(BaseModel):
    feedback_id: str
    update_data: CandidateFeedbackUpdate


@router.post("/update", response_model=ApiResponse[CandidateFeedbackRead])
def update_feedback(
    payload: FeedbackUpdatePayload, db: DbSession
) -> ApiResponse[CandidateFeedbackRead]:
    return ApiResponse(
        data=_service(db).update(payload.feedback_id, payload.update_data)
    )


class FeedbackDeletePayload(BaseModel):
    feedback_id: str


@router.post("/delete", response_model=ApiResponse[dict[str, str]])
def delete_feedback(
    payload: FeedbackDeletePayload, db: DbSession
) -> ApiResponse[dict[str, str]]:
    _service(db).delete(payload.feedback_id)
    return ApiResponse(data={"feedback_id": payload.feedback_id})
