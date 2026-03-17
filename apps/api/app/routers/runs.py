from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
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


@router.get("", response_model=list[RunRead])
def list_runs(db: DbSession) -> list[RunRead]:
    return get_service(db).list_runs()


@router.post("", response_model=RunRead, status_code=status.HTTP_201_CREATED)
def create_run(payload: RunCreate, db: DbSession) -> RunRead:
    return get_service(db).create_run(payload)


@router.get("/{run_id}", response_model=RunRead)
def get_run(run_id: str, db: DbSession) -> RunRead:
    return get_service(db).get_run(run_id)


@router.patch("/{run_id}", response_model=RunRead)
def update_run(run_id: str, payload: RunUpdate, db: DbSession) -> RunRead:
    return get_service(db).update_run(run_id, payload)


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_run(run_id: str, db: DbSession) -> Response:
    get_service(db).delete_run(run_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
