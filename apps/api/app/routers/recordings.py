from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repos.recording_repo import RecordingRepository
from app.schemas.recording import RecordingCreate, RecordingRead, RecordingUpdate
from app.services.recording_service import RecordingService

router = APIRouter(prefix="/recordings", tags=["recordings"])
DbSession = Annotated[Session, Depends(get_db)]


def get_service(db: Session) -> RecordingService:
    return RecordingService(RecordingRepository(db))


@router.get("/list", response_model=list[RecordingRead])
def list_recordings(db: DbSession) -> list[RecordingRead]:
    return get_service(db).list_recordings()


@router.post("/create", response_model=RecordingRead, status_code=status.HTTP_201_CREATED)
def create_recording(
    payload: RecordingCreate,
    db: DbSession,
) -> RecordingRead:
    return get_service(db).create_recording(payload)


@router.get("/get", response_model=RecordingRead)
def get_recording(recording_id: Annotated[str, Query(...)], db: DbSession) -> RecordingRead:
    return get_service(db).get_recording(recording_id)


class RecordingUpdatePayload(BaseModel):
    recording_id: str
    update_data: RecordingUpdate


@router.post("/update", response_model=RecordingRead)
def update_recording(
    payload: RecordingUpdatePayload,
    db: DbSession,
) -> RecordingRead:
    return get_service(db).update_recording(payload.recording_id, payload.update_data)


class RecordingDeletePayload(BaseModel):
    recording_id: str


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_recording(payload: RecordingDeletePayload, db: DbSession) -> Response:
    get_service(db).delete_recording(payload.recording_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
