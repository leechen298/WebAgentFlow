from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repos.run_repo import RunRepository
from app.repos.skill_repo import SkillRepository
from app.schemas.run import RunCreate, RunRead, RunUpdate
from app.services.run_service import RunService

router = APIRouter(prefix="/runs", tags=["runs"])
DbSession = Annotated[Session, Depends(get_db)]


def get_service(db: Session) -> RunService:
    return RunService(RunRepository(db), SkillRepository(db))


@router.get("/list", response_model=list[RunRead])
def list_runs(db: DbSession) -> list[RunRead]:
    return get_service(db).list_runs()


@router.post("/create", response_model=RunRead, status_code=status.HTTP_201_CREATED)
def create_run(payload: RunCreate, db: DbSession) -> RunRead:
    return get_service(db).create_run(payload)


@router.get("/get", response_model=RunRead)
def get_run(run_id: Annotated[str, Query(...)], db: DbSession) -> RunRead:
    return get_service(db).get_run(run_id)


class RunUpdatePayload(BaseModel):
    run_id: str
    update_data: RunUpdate


@router.post("/update", response_model=RunRead)
def update_run(
    payload: RunUpdatePayload,
    db: DbSession,
) -> RunRead:
    return get_service(db).update_run(payload.run_id, payload.update_data)


class RunDeletePayload(BaseModel):
    run_id: str


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_run(payload: RunDeletePayload, db: DbSession) -> Response:
    get_service(db).delete_run(payload.run_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
