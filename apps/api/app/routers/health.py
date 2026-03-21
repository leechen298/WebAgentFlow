from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.exceptions import ServiceUnavailableError
from app.schemas.common import ApiResponse

router = APIRouter(tags=["health"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/health")
def health(db: DbSession) -> ApiResponse[dict[str, str]]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise ServiceUnavailableError("Database is unavailable.") from exc

    return ApiResponse(data={"status": "ok", "database": "ok"})
