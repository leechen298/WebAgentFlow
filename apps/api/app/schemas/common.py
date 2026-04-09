from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    code: int = 0
    data: DataT
    msg: str = "ok"


class CursorPage(BaseModel, Generic[DataT]):
    items: list[DataT]
    has_next: bool
    next_cursor: str | None = None


class ApiErrorResponse(BaseModel):
    code: int
    msg: str
    data: dict | list | None = None


def encode_cursor(created_at: datetime, record_id: str) -> str:
    return f"{created_at.isoformat()}|{record_id}"


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    ts_str, record_id = cursor.split("|", 1)
    return datetime.fromisoformat(ts_str), record_id
