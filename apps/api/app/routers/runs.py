from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repos.run_repo import RunRepository
from app.repos.skill_repo import SkillRepository
from app.schemas.common import ApiResponse
from app.schemas.run import RunCreate, RunRead, RunUpdate
from app.services.run_service import RunService

router = APIRouter(prefix="/runs", tags=["runs"])
DbSession = Annotated[Session, Depends(get_db)]


def get_service(db: Session) -> RunService:
    return RunService(RunRepository(db), SkillRepository(db))


@router.get("/list", response_model=ApiResponse[list[RunRead]])
def list_runs(db: DbSession) -> ApiResponse[list[RunRead]]:
    return ApiResponse(data=get_service(db).list_runs())


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
