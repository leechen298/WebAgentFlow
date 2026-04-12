from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repos.recording_repo import RecordingRepository
from app.schemas.common import ApiResponse, CursorPage, decode_cursor, encode_cursor
from app.schemas.recording import (
    NormalizedRecordingRead,
    OperationStepResult,
    RecordingCreate,
    RecordingRead,
    RecordingUpdate,
)
from app.services.recording_normalizer import normalize_recording, normalized_recording_to_dict
from app.services.recording_service import RecordingService
from app.services.step_builder import build_steps

router = APIRouter(prefix="/recordings", tags=["recordings"])
DbSession = Annotated[Session, Depends(get_db)]


def get_service(db: Session) -> RecordingService:
    return RecordingService(RecordingRepository(db))


@router.get("/list", response_model=ApiResponse[CursorPage[RecordingRead]])
def list_recordings(
    db: DbSession,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
) -> ApiResponse[CursorPage[RecordingRead]]:
    cursor_created_at = cursor_id = None
    if cursor:
        cursor_created_at, cursor_id = decode_cursor(cursor)
    items, has_next = get_service(db).list_recordings_page(limit, cursor_created_at, cursor_id)
    next_cursor = encode_cursor(items[-1].created_at, items[-1].id) if has_next and items else None
    return ApiResponse(data=CursorPage(items=items, has_next=has_next, next_cursor=next_cursor))


@router.post("/create", response_model=ApiResponse[RecordingRead])
def create_recording(
    payload: RecordingCreate,
    db: DbSession,
) -> ApiResponse[RecordingRead]:
    return ApiResponse(data=get_service(db).create_recording(payload))


@router.get("/get", response_model=ApiResponse[RecordingRead])
def get_recording(
    recording_id: Annotated[str, Query(...)],
    db: DbSession,
) -> ApiResponse[RecordingRead]:
    return ApiResponse(data=get_service(db).get_recording(recording_id))


class RecordingUpdatePayload(BaseModel):
    recording_id: str
    update_data: RecordingUpdate


@router.post("/update", response_model=ApiResponse[RecordingRead])
def update_recording(
    payload: RecordingUpdatePayload,
    db: DbSession,
) -> ApiResponse[RecordingRead]:
    return ApiResponse(
        data=get_service(db).update_recording(payload.recording_id, payload.update_data)
    )


class RecordingDeletePayload(BaseModel):
    recording_id: str


@router.post("/delete", response_model=ApiResponse[dict[str, str]])
def delete_recording(
    payload: RecordingDeletePayload,
    db: DbSession,
) -> ApiResponse[dict[str, str]]:
    get_service(db).delete_recording(payload.recording_id)
    return ApiResponse(data={"recording_id": payload.recording_id})


@router.get("/get_normalized", response_model=ApiResponse[NormalizedRecordingRead])
def get_normalized_recording(
    recording_id: Annotated[str, Query(...)],
    db: DbSession,
) -> ApiResponse[NormalizedRecordingRead]:
    recording = get_service(db).get_recording(recording_id)
    # Extract initialState from meta (camelCase key, stored by the extension)
    initial_state = (recording.meta or {}).get("initialState") if recording.meta else None
    nr = normalize_recording(
        recording_id,
        recording.events or [],
        initial_state=initial_state,
    )
    return ApiResponse(data=NormalizedRecordingRead(**normalized_recording_to_dict(nr)))


@router.get("/get_steps", response_model=ApiResponse[OperationStepResult])
def get_recording_steps(
    recording_id: Annotated[str, Query(...)],
    db: DbSession,
) -> ApiResponse[OperationStepResult]:
    recording = get_service(db).get_recording(recording_id)
    dom_mutations = (recording.meta or {}).get("domMutations", []) if recording.meta else []
    result = build_steps(
        recording_id,
        recording.events or [],
        dom_mutations,
    )
    return ApiResponse(data=OperationStepResult(**result))
