from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    code: int = 0
    data: DataT
    msg: str = "ok"


class ApiErrorResponse(BaseModel):
    code: int
    msg: str
    data: dict | list | None = None
