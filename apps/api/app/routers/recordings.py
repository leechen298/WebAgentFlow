from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repos.recording_repo import RecordingRepository
from app.schemas.common import ApiResponse
from app.schemas.recording import RecordingCreate, RecordingRead, RecordingUpdate
from app.services.recording_service import RecordingService

router = APIRouter(prefix="/recordings", tags=["recordings"])
DbSession = Annotated[Session, Depends(get_db)]


def get_service(db: Session) -> RecordingService:
    return RecordingService(RecordingRepository(db))


@router.get("/list", response_model=ApiResponse[list[RecordingRead]])
def list_recordings(db: DbSession) -> ApiResponse[list[RecordingRead]]:
    return ApiResponse(data=get_service(db).list_recordings())


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
def delete_recording(payload: RecordingDeletePayload, db: DbSession) -> ApiResponse[dict[str, str]]:
    get_service(db).delete_recording(payload.recording_id)
    return ApiResponse(data={"recording_id": payload.recording_id})
