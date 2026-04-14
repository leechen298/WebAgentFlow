"""Request-level locale handling.

Provides a context-variable backed locale that middleware sets
per-request from the ``X-Locale`` / ``Accept-Language`` header.
Services call ``get_locale()`` to obtain the current value.
"""

from __future__ import annotations

from contextvars import ContextVar

_current_locale: ContextVar[str] = ContextVar("current_locale", default="en")

# Supported locale codes — extend this set when adding new languages.
SUPPORTED_LOCALES: frozenset[str] = frozenset({"en", "zh", "ja"})
DEFAULT_LOCALE = "en"


def normalize_locale(raw: str) -> str:
    """Map a raw locale string to a supported short code.

    Examples:
        "zh-CN", "zh-TW", "zh" → "zh"
        "en-US", "en-GB", "en" → "en"
        "ja-JP", "ja"          → "ja"
        "fr"                   → "en" (unsupported → default)
    """
    if not raw:
        return DEFAULT_LOCALE
    short = raw.strip().split("-")[0].split("_")[0].lower()
    return short if short in SUPPORTED_LOCALES else DEFAULT_LOCALE


def get_locale() -> str:
    """Return the locale for the current request context."""
    return _current_locale.get()


def set_locale(locale: str) -> None:
    """Set the locale for the current request context."""
    _current_locale.set(locale)
