"""Conversation Entry Gate for M11.3.5.1."""

from __future__ import annotations

import hashlib
import json
import queue
import re
import threading
import time
import uuid
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.conversation_entry_gate import (
    ConversationEntryGateCategory,
    ConversationEntryGateResult,
)
from app.schemas.llm import LlmMessage, LlmRequest
from app.services import llm_provider
from app.services.conversation.intake import redact_sensitive_payload
from app.services.conversation.prompt_assets import PromptAssetError, load_prompt_asset
from app.services.conversation.trace_sanitizer import sanitize_provider_thinking

EntryGateProvider = Callable[
    [dict[str, Any]], ConversationEntryGateResult | dict[str, Any] | None
]

_ENTRY_GATE_LLM_TIMEOUT_SEC = 1.5

_URL_RE = re.compile(r"https?://[^\s，。]+")
_WEB_TASK_KEYWORDS = (
    "学习",
    "学一下",
    "执行",
    "操作",
    "网页",
    "页面",
    "网站",
    "打开",
    "点击",
    "填写",
    "搜索",
    "登录",
    "进入",
    "learn",
    "teach",
    "execute",
    "run",
    "browser",
    "web",
    "page",
    "site",
    "open",
    "click",
    "fill",
    "search",
    "login",
    "用户名",
    "用户账号",
    "账号",
    "密码",
    "口令",
    "访问口令",
)
_CAPABILITY_PATTERNS = (
    "你能做什么",
    "你可以做什么",
    "能帮我什么",
    "能干什么",
    "怎么用",
    "帮助",
    "help",
    "what can you do",
    "how do i use",
)
_UNSUPPORTED_PATTERNS = (
    "天气",
    "股票",
    "汇率",
    "新闻",
    "写诗",
    "讲故事",
    "weather",
    "stock",
    "news",
    "poem",
)


class ConversationEntryGateService:
    def __init__(
        self,
        provider: EntryGateProvider | None = None,
        *,
        timeout_ms: int = 1500,
        confidence_threshold: float = 0.6,
    ) -> None:
        self._provider = provider
        self.timeout_ms = min(max(int(timeout_ms), 1), 2000)
        self.confidence_threshold = confidence_threshold
        self._last_trace_payload: dict[str, Any] | None = None
        self.provider_fallback = False

    def evaluate(
        self,
        raw_message: str,
        *,
        session_metadata: dict[str, Any] | None = None,
        session_mode: str | None = None,
    ) -> ConversationEntryGateResult:
        self._last_trace_payload = None
        self.provider_fallback = False
        started = time.perf_counter()
        context = _minimal_context(
            session_metadata or {},
            session_mode=session_mode,
        )
        payload = {
            "raw_message": raw_message,
            "context": context,
        }
        deterministic = deterministic_entry_gate(
            raw_message,
            context=context,
            fallback=False,
        )
        if _should_use_deterministic_preflight(deterministic):
            return _with_runtime_timing(
                deterministic,
                started=started,
                timeout_ms=self.timeout_ms,
            )
        if self._provider is not None:
            provided = self._call_provider_with_timeout(payload, started=started)
            if provided is not None:
                fallback = _deterministic_fallback_after_provider(
                    provided,
                    deterministic=deterministic,
                    timeout_ms=self.timeout_ms,
                )
                if fallback is not None:
                    self._replace_last_trace_result(
                        fallback,
                        error_kind=provided.error_kind,
                    )
                    return fallback
                return provided
        result = deterministic.model_copy(update={"fallback": self.provider_fallback})
        return _with_runtime_timing(
            result,
            started=started,
            timeout_ms=self.timeout_ms,
        )

    def consume_last_trace_payload(self) -> dict[str, Any] | None:
        payload = self._last_trace_payload
        self._last_trace_payload = None
        return payload

    def _call_provider_with_timeout(
        self,
        payload: dict[str, Any],
        *,
        started: float,
    ) -> ConversationEntryGateResult | None:
        results: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=1)

        def run_provider() -> None:
            try:
                results.put(("ok", self._provider(payload)))
            except Exception as exc:
                results.put(("error", exc))

        # The LLM-backed runtime provider also sets a short transport timeout.
        # This thread join is the user-facing guardrail; the provider timeout
        # bounds lingering network work if the HTTP client is the slow part.
        thread = threading.Thread(target=run_provider, daemon=True)
        thread.start()
        thread.join(self.timeout_ms / 1000)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if thread.is_alive():
            self.provider_fallback = True
            result = _safe_closed_result(
                category=ConversationEntryGateCategory.NEEDS_CLARIFICATION,
                reason_summary="entry gate provider timed out",
                error_kind="timeout",
                latency_ms=elapsed_ms,
                timeout_ms=self.timeout_ms,
            )
            self._last_trace_payload = _trace_payload_from_result(
                result,
                raw_payload={
                    "input_summary": _provider_input_summary(payload),
                    "error_kind": "timeout",
                },
            )
            return result
        try:
            status, value = results.get_nowait()
        except queue.Empty:
            self.provider_fallback = True
            return None
        if status == "error":
            self.provider_fallback = True
            result = _safe_closed_result(
                category=ConversationEntryGateCategory.NEEDS_CLARIFICATION,
                reason_summary=f"entry gate provider failed: {type(value).__name__}",
                error_kind="provider_error",
                latency_ms=elapsed_ms,
                timeout_ms=self.timeout_ms,
            )
            self._last_trace_payload = _trace_payload_from_result(
                result,
                raw_payload={
                    "input_summary": _provider_input_summary(payload),
                    "error_kind": "provider_error",
                },
            )
            return result
        return self._parse_provider_value(value, payload=payload, elapsed_ms=elapsed_ms)

    def _parse_provider_value(
        self,
        value: Any,
        *,
        payload: dict[str, Any],
        elapsed_ms: int,
    ) -> ConversationEntryGateResult | None:
        trace_payload = None
        try:
            if value is None:
                self.provider_fallback = True
                return None
            if isinstance(value, dict) and "llm_trace" in value:
                trace_payload = value.get("llm_trace")
                value = value.get("entry_gate")
            if value is None:
                self.provider_fallback = True
                return None
            result = (
                value
                if isinstance(value, ConversationEntryGateResult)
                else ConversationEntryGateResult.model_validate(value)
            )
            result = result.model_copy(
                update={
                    "latency_ms": (
                        result.latency_ms
                        if result.latency_ms is not None
                        else elapsed_ms
                    ),
                    "timeout_ms": result.timeout_ms or self.timeout_ms,
                    "source": "llm" if isinstance(trace_payload, dict) else result.source,
                }
            )
            if result.confidence < self.confidence_threshold:
                result = _safe_closed_result(
                    category=ConversationEntryGateCategory.NEEDS_CLARIFICATION,
                    reason_summary="entry gate confidence below threshold",
                    error_kind="low_confidence",
                    latency_ms=result.latency_ms,
                    timeout_ms=self.timeout_ms,
                    provider=result.provider,
                    model=result.model,
                )
            if isinstance(trace_payload, dict):
                self._last_trace_payload = _redacted_trace_payload(
                    trace_payload,
                    result=result,
                    schema_validation={"ok": result.error_kind is None},
                )
            else:
                self._last_trace_payload = _trace_payload_from_result(
                    result,
                    raw_payload={"input_summary": _provider_input_summary(payload)},
                )
            return result
        except (TypeError, ValidationError, ValueError) as exc:
            result = _safe_closed_result(
                category=ConversationEntryGateCategory.NEEDS_CLARIFICATION,
                reason_summary="entry gate provider output failed schema validation",
                error_kind="schema_error",
                latency_ms=elapsed_ms,
                timeout_ms=self.timeout_ms,
            )
            self._last_trace_payload = _trace_payload_from_result(
                result,
                raw_payload={
                    "input_summary": _provider_input_summary(payload),
                    "error": str(exc),
                },
            )
            return result

    def _replace_last_trace_result(
        self,
        result: ConversationEntryGateResult,
        *,
        error_kind: str | None,
    ) -> None:
        if not isinstance(self._last_trace_payload, dict):
            return
        payload = dict(self._last_trace_payload)
        payload["parsed_output"] = result.model_dump(mode="json")
        payload["latency_ms"] = result.latency_ms or payload.get("latency_ms")
        payload["schema_validation"] = {
            **_dict_or_empty(payload.get("schema_validation")),
            "ok": error_kind is None,
            "fallback_override": True,
            "error_kind": error_kind,
        }
        self._last_trace_payload = sanitize_provider_thinking(
            redact_sensitive_payload(payload)
        )


def build_runtime_entry_gate_service() -> ConversationEntryGateService:
    return ConversationEntryGateService(provider=_llm_entry_gate_provider)


def _with_runtime_timing(
    result: ConversationEntryGateResult,
    *,
    started: float,
    timeout_ms: int,
) -> ConversationEntryGateResult:
    return result.model_copy(
        update={
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "timeout_ms": timeout_ms,
        }
    )


def _should_use_deterministic_preflight(
    result: ConversationEntryGateResult,
) -> bool:
    if (
        result.category == ConversationEntryGateCategory.NEEDS_CLARIFICATION
        and result.reason_summary == "empty message"
    ):
        return True
    return result.category in {
        ConversationEntryGateCategory.WEB_TASK_CANDIDATE,
        ConversationEntryGateCategory.CAPABILITY_QUESTION,
        ConversationEntryGateCategory.UNSUPPORTED,
    }


def _deterministic_fallback_after_provider(
    provided: ConversationEntryGateResult,
    *,
    deterministic: ConversationEntryGateResult,
    timeout_ms: int,
) -> ConversationEntryGateResult | None:
    if deterministic.category == ConversationEntryGateCategory.NEEDS_CLARIFICATION:
        return None
    should_override = bool(provided.error_kind or provided.fallback)
    if (
        deterministic.category == ConversationEntryGateCategory.NON_WEB_CHAT
        and provided.category == ConversationEntryGateCategory.NEEDS_CLARIFICATION
    ):
        should_override = True
    if not should_override:
        return None
    return deterministic.model_copy(
        update={
            "latency_ms": provided.latency_ms,
            "timeout_ms": provided.timeout_ms or timeout_ms,
            "provider": provided.provider,
            "model": provided.model,
            "fallback": True,
            "error_kind": provided.error_kind,
            "source": "deterministic_fallback",
        }
    )


def deterministic_entry_gate(
    raw_message: str,
    *,
    context: dict[str, Any] | None = None,
    fallback: bool = False,
) -> ConversationEntryGateResult:
    context = context or {}
    text = raw_message.strip()
    lowered = text.lower()
    if not text:
        return ConversationEntryGateResult(
            category=ConversationEntryGateCategory.NEEDS_CLARIFICATION,
            requires_agent_runtime=False,
            confidence=0.92,
            reply_hint="请告诉我目标网页和你想学习或执行的操作。",
            reason_summary="empty message",
            fallback=fallback,
        )
    if context.get("pending_intake_exists") or context.get("pending_target_exists"):
        return ConversationEntryGateResult(
            category=ConversationEntryGateCategory.WEB_TASK_CANDIDATE,
            requires_agent_runtime=True,
            confidence=0.84,
            reason_summary="session has pending web task context",
            fallback=fallback,
        )
    if _has_web_task_signal(text):
        return ConversationEntryGateResult(
            category=ConversationEntryGateCategory.WEB_TASK_CANDIDATE,
            requires_agent_runtime=True,
            confidence=0.88,
            reason_summary="message contains web task candidate signals",
            fallback=fallback,
        )
    if any(pattern in lowered or pattern in text for pattern in _CAPABILITY_PATTERNS):
        return ConversationEntryGateResult(
            category=ConversationEntryGateCategory.CAPABILITY_QUESTION,
            requires_agent_runtime=False,
            confidence=0.9,
            reply_hint="说明 WebAgentFlow 的网页操作学习和执行能力。",
            reason_summary="user asks about product capability",
            fallback=fallback,
        )
    if any(pattern in lowered or pattern in text for pattern in _UNSUPPORTED_PATTERNS):
        return ConversationEntryGateResult(
            category=ConversationEntryGateCategory.UNSUPPORTED,
            requires_agent_runtime=False,
            confidence=0.84,
            reply_hint="说明该请求不属于当前网页操作范围。",
            reason_summary="message is outside current product scope",
            fallback=fallback,
        )
    return ConversationEntryGateResult(
        category=ConversationEntryGateCategory.NON_WEB_CHAT,
        requires_agent_runtime=False,
        confidence=0.82,
        reply_hint="友好回应，并引导用户提供目标 URL 和网页操作目标。",
        reason_summary="message has no web task signal",
        fallback=fallback,
    )


def _llm_entry_gate_provider(
    payload: dict[str, Any],
) -> ConversationEntryGateResult | dict[str, Any] | None:
    if not settings.llm_api_key:
        return None
    try:
        asset = load_prompt_asset("conversation_entry_gate", version="v1")
    except PromptAssetError:
        return None

    request = LlmRequest(
        system=asset.assembled_prompt,
        messages=[
            LlmMessage(
                role="user",
                content=json.dumps(redact_sensitive_payload(payload), ensure_ascii=False),
            )
        ],
        response_schema=ConversationEntryGateResult.model_json_schema(),
        temperature=0.0,
        max_tokens=500,
        timeout=_ENTRY_GATE_LLM_TIMEOUT_SEC,
        metadata={"surface": "conversation_entry_gate"},
    )
    started = time.perf_counter()
    response = llm_provider.generate_structured(request)
    latency_ms = int((time.perf_counter() - started) * 1000)
    trace = _llm_trace_payload(asset, request, response, latency_ms)
    if response.ok and response.parsed is not None:
        return {"entry_gate": response.parsed, "llm_trace": trace}
    error_kind = response.error.kind if response.error is not None else "parse_error"
    result = _safe_closed_result(
        category=ConversationEntryGateCategory.NEEDS_CLARIFICATION,
        reason_summary=f"entry gate provider returned {error_kind}",
        error_kind=error_kind,
        latency_ms=latency_ms,
    )
    return {"entry_gate": result, "llm_trace": trace}


def _has_web_task_signal(text: str) -> bool:
    lowered = text.lower()
    if _URL_RE.search(text):
        return True
    return any(keyword in lowered or keyword in text for keyword in _WEB_TASK_KEYWORDS)


def _minimal_context(
    metadata: dict[str, Any],
    *,
    session_mode: str | None,
) -> dict[str, Any]:
    return {
        "session_mode": session_mode,
        "pending_target_exists": bool(metadata.get("pending_target")),
        "pending_intake_exists": bool(metadata.get("pending_intake")),
        "last_no_path_reason_exists": bool(metadata.get("last_no_path_reason")),
    }


def _safe_closed_result(
    *,
    category: ConversationEntryGateCategory,
    reason_summary: str,
    error_kind: str,
    latency_ms: int | None = None,
    timeout_ms: int | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> ConversationEntryGateResult:
    return ConversationEntryGateResult(
        category=category,
        requires_agent_runtime=False,
        confidence=0.0,
        reply_hint="请提供目标页面 URL，或说明要学习/执行的网页操作。",
        reason_summary=reason_summary,
        latency_ms=latency_ms,
        timeout_ms=timeout_ms,
        provider=provider,
        model=model,
        fallback=True,
        error_kind=error_kind,
        source="provider_error",
    )


def _llm_trace_payload(
    asset: Any,
    request: LlmRequest,
    response: Any,
    latency_ms: int,
) -> dict[str, Any]:
    request_payload = request.model_dump(mode="json")
    raw_response = (
        response.model_dump(mode="json") if hasattr(response, "model_dump") else {}
    )
    raw_provider = raw_response.get("raw")
    request_id = raw_provider.get("id") if isinstance(raw_provider, dict) else None
    prompt_material = repr(
        {
            "prompt": asset.assembled_prompt,
            "messages": [message.model_dump() for message in request.messages],
            "schema": request.response_schema,
        }
    )
    return {
        "trace_id": f"trace-{uuid.uuid4()}",
        "purpose": "conversation_entry_gate",
        "agent_role": "conversation_entry_gate",
        "provider": "openai_compatible",
        "model": response.model or request.model or settings.llm_default_model,
        "request_id": request_id,
        "prompt_template_id": f"{asset.prompt_id}.{asset.version}",
        "prompt_hash": asset.prompt_sha256
        or hashlib.sha256(prompt_material.encode()).hexdigest(),
        "schema_name": "ConversationEntryGateResult",
        "schema_version": "m11.3.5.1",
        "schema_validation": {"ok": bool(response.ok)},
        "latency_ms": latency_ms,
        "token_usage": response.usage.model_dump(mode="json"),
        "raw_request": request_payload,
        "raw_response": raw_response,
        "parsed_output": response.parsed or {},
        "redaction": {
            "applied": True,
            "strategy": "conversation_sensitive_and_thinking_redaction",
        },
    }


def _redacted_trace_payload(
    trace_payload: dict[str, Any],
    *,
    result: ConversationEntryGateResult,
    schema_validation: dict[str, Any],
) -> dict[str, Any]:
    payload = dict(trace_payload)
    payload["schema_validation"] = schema_validation
    payload["parsed_output"] = result.model_dump(mode="json")
    payload["latency_ms"] = result.latency_ms or payload.get("latency_ms")
    payload["provider"] = result.provider or payload.get("provider")
    payload["model"] = result.model or payload.get("model")
    payload["redaction"] = {
        **_dict_or_empty(payload.get("redaction")),
        "applied": True,
        "strategy": "conversation_sensitive_and_thinking_redaction",
    }
    return sanitize_provider_thinking(redact_sensitive_payload(payload))


def _trace_payload_from_result(
    result: ConversationEntryGateResult,
    *,
    raw_payload: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "trace_id": f"trace-{uuid.uuid4()}",
        "purpose": "conversation_entry_gate",
        "agent_role": "conversation_entry_gate",
        "provider": result.provider,
        "model": result.model,
        "prompt_template_id": None,
        "prompt_hash": None,
        "schema_name": "ConversationEntryGateResult",
        "schema_version": "m11.3.5.1",
        "schema_validation": {"ok": result.error_kind is None},
        "latency_ms": result.latency_ms,
        "raw_request": raw_payload,
        "raw_response": {},
        "parsed_output": result.model_dump(mode="json"),
        "redaction": {
            "applied": True,
            "strategy": "conversation_sensitive_and_thinking_redaction",
        },
    }
    return sanitize_provider_thinking(redact_sensitive_payload(payload))


def _provider_input_summary(payload: dict[str, Any]) -> dict[str, Any]:
    raw = str(payload.get("raw_message") or "")
    return {
        "message_length": len(raw),
        "has_url": bool(_URL_RE.search(raw)),
        "context": payload.get("context") or {},
    }


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
