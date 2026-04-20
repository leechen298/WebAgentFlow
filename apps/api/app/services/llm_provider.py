"""Minimal LLM provider layer.

Provides `generate_text()` and `generate_structured()` as the unified entry
points for all LLM calls in the project.  Business modules (page understanding,
step understanding, etc.) call these functions — never the OpenAI SDK directly.

Transport: OpenAI-compatible API (covers MiniMax, DeepSeek, Moonshot, etc.)
Provider-specific differences are absorbed here via payload patching.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from app.core.config import settings
from app.schemas.llm import LlmError, LlmMessage, LlmRequest, LlmResponse, LlmUsage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client singleton (lazy)
# ---------------------------------------------------------------------------

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=float(settings.llm_timeout),
        )
    return _client


def reset_client() -> None:
    """Reset singleton — mainly for testing."""
    global _client
    _client = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve(request: LlmRequest) -> dict[str, Any]:
    """Build the kwargs dict for chat.completions.create()."""
    model = request.model or settings.llm_default_model
    temperature = request.temperature if request.temperature is not None else settings.llm_temperature
    max_tokens = request.max_tokens if request.max_tokens is not None else settings.llm_max_tokens

    messages: list[dict[str, str]] = []
    if request.system:
        messages.append({"role": "system", "content": request.system})
    for m in request.messages:
        messages.append({"role": m.role, "content": m.content})

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if request.response_schema is not None:
        # Use json_object mode (broad provider compatibility) + schema in prompt.
        # json_schema strict mode is OpenAI-specific; many providers (MiniMax,
        # DeepSeek, etc.) support json_object but not json_schema.
        kwargs["response_format"] = {"type": "json_object"}

        schema_str = json.dumps(request.response_schema, ensure_ascii=False, indent=2)
        schema_instruction = (
            "You MUST respond with a JSON object conforming to this schema. "
            "Output ONLY valid JSON, no extra text.\n\n"
            f"JSON Schema:\n```json\n{schema_str}\n```"
        )
        # Prepend schema instruction to system prompt
        if messages and messages[0]["role"] == "system":
            messages[0]["content"] = schema_instruction + "\n\n" + messages[0]["content"]
        else:
            messages.insert(0, {"role": "system", "content": schema_instruction})

    return kwargs


_THINK_RE = re.compile(r"<think>(.*?)</think>\s*", re.DOTALL)


def _split_thinking(text: str) -> tuple[str, str | None]:
    """Separate <think>...</think> blocks from the final answer.

    Returns (clean_text_without_thinking, concatenated_thinking_content_or_None).
    Used to expose the model's reasoning trace for UI transparency while
    keeping it out of downstream JSON parsing.
    """
    thinking_parts: list[str] = []

    def _capture(match: re.Match[str]) -> str:
        thinking_parts.append(match.group(1))
        return ""

    clean = _THINK_RE.sub(_capture, text).strip()
    thinking = "\n\n".join(p.strip() for p in thinking_parts).strip() if thinking_parts else None
    return clean, thinking


def _strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks — thin wrapper over _split_thinking."""
    clean, _ = _split_thinking(text)
    return clean


_FENCE_RE = re.compile(r"^\s*```(?:[A-Za-z0-9_+-]+)?\s*\n(.*?)\n```\s*$", re.DOTALL)


def _strip_code_fence(text: str) -> str:
    """Peel an optional ```[lang]\\n...\\n``` Markdown wrapper.

    Reasoning-oriented providers (MiniMax-M2.x notably) default to
    Markdown-fenced JSON even when ``response_format={"type":"json_object"}``
    is set, which makes ``json.loads`` choke on the backticks. The
    fence is only stripped when the whole cleaned response is a
    single code block — loose text that merely *contains* a fence is
    left for the caller to handle.
    """
    match = _FENCE_RE.match(text)
    return match.group(1).strip() if match else text


def _extract_usage(raw_usage: Any) -> LlmUsage:
    if raw_usage is None:
        return LlmUsage()
    return LlmUsage(
        prompt_tokens=getattr(raw_usage, "prompt_tokens", 0) or 0,
        completion_tokens=getattr(raw_usage, "completion_tokens", 0) or 0,
        total_tokens=getattr(raw_usage, "total_tokens", 0) or 0,
    )


def _classify_api_error(exc: APIStatusError) -> LlmError:
    status = exc.status_code
    body = exc.body if isinstance(exc.body, dict) else {}

    if status == 401:
        return LlmError(kind="auth_error", message=str(exc), retryable=False, raw=body)
    if status == 429:
        return LlmError(kind="rate_limit", message=str(exc), retryable=True, raw=body)
    if status >= 500:
        return LlmError(kind="provider_error", message=str(exc), retryable=True, raw=body)

    return LlmError(kind="provider_error", message=str(exc), retryable=False, raw=body)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_text(request: LlmRequest) -> LlmResponse:
    """Call the LLM and return a plain text response."""
    try:
        client = _get_client()
        kwargs = _resolve(request)
        # Strip response_format for plain text calls
        kwargs.pop("response_format", None)

        completion = client.chat.completions.create(**kwargs)
        choice = completion.choices[0] if completion.choices else None
        text = choice.message.content if choice else None
        thinking = None
        if text:
            text, thinking = _split_thinking(text)

        return LlmResponse(
            ok=True,
            text=text,
            thinking=thinking,
            usage=_extract_usage(completion.usage),
            model=completion.model,
            raw=completion.model_dump() if hasattr(completion, "model_dump") else None,
        )

    except APITimeoutError as exc:
        logger.warning("LLM timeout: %s", exc)
        return LlmResponse(
            ok=False,
            error=LlmError(kind="timeout", message=str(exc), retryable=True),
        )
    except APIConnectionError as exc:
        logger.warning("LLM connection error: %s", exc)
        return LlmResponse(
            ok=False,
            error=LlmError(kind="provider_error", message=str(exc), retryable=True),
        )
    except APIStatusError as exc:
        logger.warning("LLM API error %d: %s", exc.status_code, exc)
        return LlmResponse(ok=False, error=_classify_api_error(exc))


def generate_structured(request: LlmRequest) -> LlmResponse:
    """Call the LLM and return a structured (JSON-parsed) response.

    `request.response_schema` must be set.  The response is returned in
    `LlmResponse.parsed`; `LlmResponse.text` also contains the raw JSON string.
    """
    if request.response_schema is None:
        return LlmResponse(
            ok=False,
            error=LlmError(
                kind="parse_error",
                message="response_schema is required for generate_structured()",
            ),
        )

    try:
        client = _get_client()
        kwargs = _resolve(request)

        completion = client.chat.completions.create(**kwargs)
        choice = completion.choices[0] if completion.choices else None
        raw_text = choice.message.content if choice else None
        thinking: str | None = None
        if raw_text:
            raw_text, thinking = _split_thinking(raw_text)

        if not raw_text:
            return LlmResponse(
                ok=False,
                thinking=thinking,
                usage=_extract_usage(completion.usage),
                model=completion.model,
                error=LlmError(kind="parse_error", message="Empty response from provider"),
            )

        # Peel ```json ... ``` wrapper if present — see _strip_code_fence.
        json_text = _strip_code_fence(raw_text)

        # Parse JSON
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as exc:
            return LlmResponse(
                ok=False,
                text=raw_text,
                thinking=thinking,
                usage=_extract_usage(completion.usage),
                model=completion.model,
                error=LlmError(
                    kind="parse_error",
                    message=f"Failed to parse JSON: {exc}",
                    raw={"raw_text": raw_text},
                ),
            )

        return LlmResponse(
            ok=True,
            text=raw_text,
            parsed=parsed,
            thinking=thinking,
            usage=_extract_usage(completion.usage),
            model=completion.model,
            raw=completion.model_dump() if hasattr(completion, "model_dump") else None,
        )

    except APITimeoutError as exc:
        logger.warning("LLM timeout: %s", exc)
        return LlmResponse(
            ok=False,
            error=LlmError(kind="timeout", message=str(exc), retryable=True),
        )
    except APIConnectionError as exc:
        logger.warning("LLM connection error: %s", exc)
        return LlmResponse(
            ok=False,
            error=LlmError(kind="provider_error", message=str(exc), retryable=True),
        )
    except APIStatusError as exc:
        logger.warning("LLM API error %d: %s", exc.status_code, exc)
        return LlmResponse(ok=False, error=_classify_api_error(exc))


# ---------------------------------------------------------------------------
# Convenience builder
# ---------------------------------------------------------------------------

def build_request(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    response_schema: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> LlmRequest:
    """Shorthand to build an LlmRequest from a simple user prompt string."""
    return LlmRequest(
        messages=[LlmMessage(role="user", content=prompt)],
        system=system,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_schema=response_schema,
        metadata=metadata,
    )
