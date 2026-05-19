"""Conversation trace sanitization helpers."""

from __future__ import annotations

import re
from typing import Any

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_THINKING_KEYS = {
    "thinking",
    "reasoning",
    "reasoning_content",
    "chain_of_thought",
}


def sanitize_provider_thinking(value: Any) -> Any:
    """Drop provider chain-of-thought fields and inline think blocks.

    This is intentionally separate from sensitive-value redaction: the content
    is not safe to persist or display even when it contains no credentials.
    """

    if isinstance(value, list):
        return [sanitize_provider_thinking(item) for item in value]
    if isinstance(value, dict):
        sanitized: dict[Any, Any] = {}
        for key, item in value.items():
            if str(key).lower() in _THINKING_KEYS:
                continue
            sanitized[key] = sanitize_provider_thinking(item)
        return sanitized
    if isinstance(value, str):
        cleaned = _THINK_BLOCK_RE.sub("", value)
        return cleaned.strip() if cleaned != value else value
    return value
