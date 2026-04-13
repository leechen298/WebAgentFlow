"""Schemas for the LLM provider layer.

Defines unified request, response, and error types so that business logic
(page understanding, step understanding, etc.) never touches provider details.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class LlmMessage(BaseModel):
    role: str = "user"
    content: str


class LlmRequest(BaseModel):
    """Unified input for both text and structured generation."""

    messages: list[LlmMessage]
    system: str | None = None
    model: str | None = None  # None → use config default
    temperature: float | None = None
    max_tokens: int | None = None
    response_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON Schema for structured output. When set, the provider "
        "returns parsed JSON conforming to this schema.",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Opaque bag for tracing / logging context.",
    )


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

class LlmUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LlmResponse(BaseModel):
    """Unified output from both text and structured generation."""

    ok: bool = True
    text: str | None = None
    parsed: dict[str, Any] | None = None
    usage: LlmUsage = Field(default_factory=LlmUsage)
    model: str | None = None
    raw: dict[str, Any] | None = Field(
        default=None,
        description="Raw provider response for debugging.",
    )
    error: LlmError | None = None


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

class LlmError(BaseModel):
    """Structured error — business layer never sees raw provider exceptions."""

    kind: str = Field(
        description="Error category: 'provider_error', 'parse_error', "
        "'timeout', 'auth_error', 'rate_limit', 'unknown'.",
    )
    message: str
    retryable: bool = False
    raw: dict[str, Any] | None = None


# Rebuild LlmResponse now that LlmError is defined (forward ref).
LlmResponse.model_rebuild()
