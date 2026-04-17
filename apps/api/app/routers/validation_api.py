"""Validation-site mock backend.

Lives under the /validation-api/ prefix and is used exclusively by
``apps/validation-site`` — the self-hosted validation fixture that lets
WebAgentFlow exercise autonomous exploration without depending on
external sites (which introduce CAPTCHA/rate-limit noise).

This router is intentionally dumb: fixed credentials, no database,
no session state. The goal is predictable success/failure paths.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.schemas.common import ApiResponse

router = APIRouter(prefix="/validation-api", tags=["validation"])
logger = logging.getLogger(__name__)


_EXPECTED_USERNAME = "admin"
_EXPECTED_PASSWORD = "123456"


class LoginRequest(BaseModel):
    username: str = Field(default="")
    password: str = Field(default="")


class LoginResponseData(BaseModel):
    token: str
    username: str


@router.post("/login", response_model=ApiResponse[LoginResponseData])
def login(payload: LoginRequest) -> ApiResponse[LoginResponseData]:
    """Stub login. admin/123456 → 200 with token; anything else → 401."""
    if (
        payload.username == _EXPECTED_USERNAME
        and payload.password == _EXPECTED_PASSWORD
    ):
        return ApiResponse(
            data=LoginResponseData(
                token=f"validation-site-token-{payload.username}",
                username=payload.username,
            ),
        )
    # HTTPException is wrapped into the {code, msg, data} envelope by
    # the global exception handler in main.py.
    raise HTTPException(status_code=401, detail="用户名或密码错误")
