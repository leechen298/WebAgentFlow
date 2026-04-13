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


# ---------------------------------------------------------------------------
# Understanding endpoint response wrappers
# ---------------------------------------------------------------------------


class LlmUsageSummary(BaseModel):
    """Token usage summary from an LLM call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class UnderstandingResponse(BaseModel, Generic[DataT]):
    """Standard response envelope for understanding endpoints (6C/6D/6E)."""

    ok: bool
    understanding: DataT | None = None
    error: dict | None = None
    usage: LlmUsageSummary | dict | None = None


class CombinedUnderstandingUsage(BaseModel):
    """Usage breakdown for combined understanding (page + step)."""

    page: LlmUsageSummary | dict | None = None
    step: LlmUsageSummary | dict | None = None


class CombinedUnderstandingResponse(BaseModel):
    """Response envelope for the combined understanding endpoint (6E)."""

    ok: bool
    understanding: dict | None = None
    error: dict | None = None
    phase: str | None = None
    usage: CombinedUnderstandingUsage | None = None


def encode_cursor(created_at: datetime, record_id: str) -> str:
    return f"{created_at.isoformat()}|{record_id}"


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    ts_str, record_id = cursor.split("|", 1)
    return datetime.fromisoformat(ts_str), record_id
