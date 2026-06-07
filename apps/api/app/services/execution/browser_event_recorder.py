"""Redacted browser event timeline recorder.

The recorder captures browser-level evidence for later terminal-state
classification. It stores metadata only: no request/response bodies, cookies,
authorization headers, or file contents.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, urlsplit

_SECRET_QUERY_KEYS = {
    "access_token",
    "api_key",
    "auth",
    "code",
    "id_token",
    "key",
    "password",
    "secret",
    "session",
    "token",
}
_FORBIDDEN_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "proxy-authorization",
    "x-api-key",
    "x-auth-token",
}
_SAFE_HEADERS = {
    "accept",
    "cache-control",
    "content-type",
    "location",
    "referer",
}
_SECRET_TEXT_RE = re.compile(
    r"(?i)(bearer\s+[a-z0-9._~+/=-]+|"
    r"(password|passwd|pwd|secret|token|api[_-]?key)\s*[:=]\s*[^,\s;]+|"
    r"(密码|口令|访问口令)\s*[:：]?\s*[^,\s;，。]+)"
)
_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?\d[\d\s-]{7,}\d)\b")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]+")


def _now_ms() -> int:
    return int(time.time() * 1000)


def _call(obj: Any, name: str, *args: Any) -> Any:
    attr = getattr(obj, name, None)
    if not callable(attr):
        return None
    with suppress(Exception):
        return attr(*args)
    return None


def _get(obj: Any, name: str, default: Any = None) -> Any:
    with suppress(Exception):
        value = getattr(obj, name)
        if callable(value):
            return value()
        return value
    return default


def _redact_text(value: Any, *, limit: int = 500) -> str:
    text = "" if value is None else str(value)
    text = _CONTROL_CHARS_RE.sub(" ", text)
    text = _SECRET_TEXT_RE.sub("[REDACTED]", text)
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _PHONE_RE.sub("[REDACTED_PHONE]", text)
    if len(text) > limit:
        return text[:limit] + f"...[truncated {len(text) - limit} chars]"
    return text


def _safe_url_metadata(url: Any) -> tuple[dict[str, Any], list[str]]:
    raw = "" if url is None else str(url)
    warnings: list[str] = []
    try:
        parsed = urlsplit(raw)
    except Exception:
        return {"raw": "[UNPARSEABLE_URL]"}, ["url_parse_failed"]

    query_keys: list[str] = []
    secret_query_keys: list[str] = []
    for key, _value in parse_qsl(parsed.query, keep_blank_values=True):
        query_keys.append(key)
        if key.lower() in _SECRET_QUERY_KEYS or any(
            part in key.lower() for part in _SECRET_QUERY_KEYS
        ):
            secret_query_keys.append(key)
    if secret_query_keys:
        warnings.append("secret_query_values_redacted")

    return (
        {
            "scheme": parsed.scheme,
            "host": parsed.netloc,
            "path": parsed.path,
            "query_keys": sorted(set(query_keys)),
            "secret_query_keys": sorted(set(secret_query_keys)),
        },
        warnings,
    )


def _safe_headers(headers: Any) -> tuple[dict[str, str], list[str]]:
    warnings: list[str] = []
    safe: dict[str, str] = {}
    if not isinstance(headers, dict):
        return safe, warnings
    for key, value in headers.items():
        lower = str(key).lower()
        if lower in _FORBIDDEN_HEADERS or any(secret in lower for secret in _SECRET_QUERY_KEYS):
            warnings.append(f"header_redacted:{lower}")
            continue
        if lower in _SAFE_HEADERS:
            safe[lower] = _redact_text(value, limit=180)
    return safe, warnings


def _request_key(*, url: Any, method: Any = None, resource_type: Any = None) -> str:
    url_meta, _warnings = _safe_url_metadata(url)
    payload = {
        "method": str(method or "").upper(),
        "resource_type": str(resource_type or ""),
        "url": url_meta,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def _safe_filename(value: Any) -> str:
    text = _redact_text(value, limit=180)
    text = text.replace("/", "_").replace("\\", "_")
    return text.strip() or "[empty]"


@dataclass
class _ActionScope:
    action_id: str | None = None
    step_index: int | None = None
    action_type: str | None = None


class BrowserEventRecorder:
    """Capture bounded redacted browser event metadata."""

    def __init__(
        self,
        *,
        correlation_id: str | None = None,
        attempt_id: str | None = None,
        max_events: int = 200,
    ) -> None:
        self.correlation_id = correlation_id or f"browser-events-{uuid.uuid4()}"
        self.attempt_id = attempt_id
        self.max_events = max_events
        self._events: list[dict[str, Any]] = []
        self._truncated_count = 0
        self._recorder_warnings: list[str] = []
        self._redaction_warnings: list[str] = []
        self._action_scope = _ActionScope()
        self._attached = False
        self._attach_failed = False
        self._listener_handles: list[tuple[Any, str, Any]] = []

    def attach(self, *, page: Any = None, context: Any = None) -> None:
        """Attach listeners to a Playwright-like page/context.

        Fake objects only need an ``on(event_name, callback)`` method for tests.
        """
        if self._listener_handles:
            self._recorder_warnings.append("already_attached")
            return
        listeners = [
            (page, "request", self.record_request),
            (page, "response", self.record_response),
            (page, "requestfailed", self.record_requestfailed),
            (page, "download", self.record_download),
            (page, "dialog", self.record_dialog),
            (page, "popup", self.record_popup),
            (page, "framenavigated", self.record_framenavigated),
            (page, "load", lambda: self.record_page_event("load")),
            (page, "domcontentloaded", lambda: self.record_page_event("domcontentloaded")),
            (page, "console", self.record_console),
            (page, "pageerror", self.record_pageerror),
            (context, "page", self.record_popup),
            (context, "request", self.record_request),
            (context, "response", self.record_response),
            (context, "requestfailed", self.record_requestfailed),
        ]
        attached = 0
        for target, event_name, handler in listeners:
            if target is None:
                continue
            on = getattr(target, "on", None)
            if not callable(on):
                continue
            try:
                on(event_name, handler)
                attached += 1
                self._listener_handles.append((target, event_name, handler))
            except Exception as exc:
                self._recorder_warnings.append(f"listener_attach_failed:{event_name}:{type(exc).__name__}")
        self._attached = attached > 0
        self._attach_failed = not self._attached
        if self._attach_failed:
            self._recorder_warnings.append("no_supported_event_target")

    def bind_action(
        self,
        *,
        action_id: str | None = None,
        step_index: int | None = None,
        action_type: str | None = None,
    ) -> None:
        self._action_scope = _ActionScope(
            action_id=action_id,
            step_index=step_index,
            action_type=action_type,
        )

    def clear_action(self) -> None:
        self._action_scope = _ActionScope()

    def reset(self) -> None:
        """Start a fresh evidence segment while keeping recorder attachment state."""
        self._events.clear()
        self._truncated_count = 0
        self._redaction_warnings.clear()
        self.clear_action()

    def record_request(self, request: Any) -> None:
        url = _get(request, "url", "")
        method = _get(request, "method")
        resource_type = _get(request, "resource_type")
        url_meta, warnings = _safe_url_metadata(url)
        headers, header_warnings = _safe_headers(
            _call(request, "headers") or _get(request, "headers") or {}
        )
        self._append(
            "request",
            {
                "url": url_meta,
                "method": method,
                "resource_type": resource_type,
                "request_key": _request_key(
                    url=url,
                    method=method,
                    resource_type=resource_type,
                ),
                "headers": headers,
                "body_stored": False,
            },
            warnings + header_warnings,
        )

    def record_response(self, response: Any) -> None:
        request = _call(response, "request") or _get(response, "request")
        url = _get(response, "url") or _get(request, "url", "")
        method = _get(request, "method")
        resource_type = _get(request, "resource_type")
        url_meta, warnings = _safe_url_metadata(url)
        headers, header_warnings = _safe_headers(
            _call(response, "headers") or _get(response, "headers") or {}
        )
        self._append(
            "response",
            {
                "url": url_meta,
                "status": _get(response, "status"),
                "request_key": _request_key(
                    url=url,
                    method=method,
                    resource_type=resource_type,
                ),
                "headers": headers,
                "body_stored": False,
            },
            warnings + header_warnings,
        )

    def record_requestfailed(self, request: Any) -> None:
        url = _get(request, "url", "")
        method = _get(request, "method")
        resource_type = _get(request, "resource_type")
        url_meta, warnings = _safe_url_metadata(url)
        failure = _call(request, "failure") or {}
        self._append(
            "requestfailed",
            {
                "url": url_meta,
                "method": method,
                "resource_type": resource_type,
                "request_key": _request_key(
                    url=url,
                    method=method,
                    resource_type=resource_type,
                ),
                "failure": _redact_text(failure, limit=240),
            },
            warnings,
        )

    def record_download(self, download: Any) -> None:
        self._append(
            "download",
            {
                "suggested_filename": _safe_filename(_get(download, "suggested_filename")),
                "content_stored": False,
            },
            [],
        )

    def record_dialog(self, dialog: Any) -> None:
        self._append(
            "dialog",
            {
                "dialog_type": _call(dialog, "type") or _get(dialog, "type"),
                "message": _redact_text(
                    _call(dialog, "message") or _get(dialog, "message"),
                    limit=300,
                ),
            },
            [],
        )

    def record_popup(self, page: Any) -> None:
        url_meta, warnings = _safe_url_metadata(_get(page, "url", ""))
        self._append("popup", {"url": url_meta}, warnings)

    def record_framenavigated(self, frame: Any) -> None:
        url_meta, warnings = _safe_url_metadata(_get(frame, "url", ""))
        self._append("framenavigated", {"url": url_meta}, warnings)

    def record_page_event(self, event_type: str) -> None:
        self._append(event_type, {}, [])

    def record_console(self, message: Any) -> None:
        text = _call(message, "text") or _get(message, "text")
        self._append(
            "console",
            {
                "message_type": _call(message, "type") or _get(message, "type"),
                "text": _redact_text(text, limit=500),
                "args_stored": False,
            },
            [],
        )

    def record_pageerror(self, error: Any) -> None:
        self._append("pageerror", {"message": _redact_text(error, limit=500)}, [])

    def snapshot(self) -> dict[str, Any]:
        if self._attach_failed:
            status = "recording_unavailable"
        elif self._truncated_count:
            status = "recording_partial"
        else:
            status = "recording_available"
        return {
            "status": status,
            "correlation_id": self.correlation_id,
            "attempt_id": self.attempt_id,
            "events": list(self._events),
            "event_count": len(self._events),
            "truncated": self._truncated_count > 0,
            "truncated_count": self._truncated_count,
            "redaction_warnings": sorted(set(self._redaction_warnings)),
            "recorder_warnings": list(self._recorder_warnings),
        }

    def stop(self) -> dict[str, Any]:
        self.detach()
        return self.snapshot()

    def detach(self) -> None:
        """Best-effort listener cleanup for reused browser pages."""
        for target, event_name, handler in reversed(self._listener_handles):
            remover = getattr(target, "remove_listener", None) or getattr(target, "off", None)
            if not callable(remover):
                self._recorder_warnings.append(f"listener_detach_unavailable:{event_name}")
                continue
            try:
                remover(event_name, handler)
            except Exception as exc:
                self._recorder_warnings.append(
                    f"listener_detach_failed:{event_name}:{type(exc).__name__}"
                )
        self._listener_handles.clear()

    def _append(
        self,
        event_type: str,
        metadata: dict[str, Any],
        warnings: list[str],
    ) -> None:
        if len(self._events) >= self.max_events:
            self._truncated_count += 1
            return
        if warnings:
            self._redaction_warnings.extend(warnings)
        event = {
            "event_id": f"event-{len(self._events) + 1}",
            "event_type": event_type,
            "occurred_at": _now_ms(),
            "correlation_id": self.correlation_id,
            "attempt_id": self.attempt_id,
            "action_id": self._action_scope.action_id,
            "step_index": self._action_scope.step_index,
            "action_type": self._action_scope.action_type,
            "metadata": metadata,
            "redaction_warnings": warnings,
        }
        self._events.append(event)
