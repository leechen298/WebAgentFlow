"""Conversation intake service for M11.3.4 interactive chat."""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from pydantic import ValidationError

from app.core.config import settings
from app.schemas.conversation_intake import (
    ConversationIntakeAction,
    ConversationIntakeResult,
    ConversationIntakeSlot,
    ConversationIntakeTarget,
    ConversationMissingField,
)
from app.schemas.llm import LlmMessage, LlmRequest
from app.services import llm_provider
from app.services.conversation.prompt_assets import PromptAssetError, load_prompt_asset

IntakeProvider = Callable[[str, dict[str, Any]], ConversationIntakeResult | dict[str, Any] | None]

REDACTED = "[REDACTED]"

_URL_RE = re.compile(r"https?://[^\s，。]+")
_VALUE_PATTERN = r"([^\s，。,.；;!！?？/]+)"
_USERNAME_LABELS = ("操作员账号", "用户名", "用户账号", "账号", "账户")
_PASSWORD_LABELS = ("访问口令", "登录口令", "口令", "密码", "access_secret", "password")
_ITEM_NAME_LABELS = ("项目名称", "项目名", "名称", "name")
_LEARN_KEYWORDS = ("学习", "学一下", "learn", "teach")
_SENSITIVE_KEY_RE = re.compile(r"(password|passwd|pwd|secret|token|access[_-]?secret)", re.I)
_JSON_SENSITIVE_TEXT_RE = re.compile(
    r'((?:"|\')?(?:password|passwd|pwd|secret|token|access[_-]?secret)(?:"|\')?\s*[:=]\s*(?:"|\')?)'
    r"([^\"'\s,}]+)"
    r"((?:\"|\')?)",
    re.I,
)
_PASSWORD_TEXT_RE = re.compile(
    r"((?:访问口令|登录口令|口令|密码)\s*(?:是|为)?\s*[:：]?\s*)" + _VALUE_PATTERN
)
_POSITIONAL_CREDENTIAL_TEXT_RE = re.compile(
    r"((?:https?://[^\s，。,]+)[，,\s]+[A-Za-z0-9_.@-]+\s*/\s*)"
    r"([A-Za-z0-9_.@#$%^&*+=-]+)"
)


class ConversationIntakeService:
    """Turn an ordinary user utterance into schema-constrained intake data."""

    def __init__(
        self,
        provider: IntakeProvider | None = None,
        *,
        confidence_threshold: float = 0.6,
    ) -> None:
        self._provider = provider
        self.confidence_threshold = confidence_threshold
        self._last_trace_payload: dict[str, Any] | None = None
        self.provider_fallback = False

    def analyze(
        self,
        raw_message: str,
        *,
        session_metadata: dict[str, Any] | None = None,
    ) -> ConversationIntakeResult:
        self._last_trace_payload = None
        self.provider_fallback = False
        context = {
            "pending_intake": (session_metadata or {}).get("pending_intake"),
            "pending_target": (session_metadata or {}).get("pending_target"),
            "pending_choice": (session_metadata or {}).get("pending_choice"),
            "last_no_path_reason": (session_metadata or {}).get("last_no_path_reason"),
            "learned_actions": redact_sensitive_payload(
                _strip_private_runtime_payload(
                    (session_metadata or {}).get("learned_actions") or []
                )
            ),
        }
        if self._provider is not None:
            provided = self._call_provider(raw_message, context)
            if provided is not None:
                return provided
        return _deterministic_intake(raw_message, context=context)

    def consume_last_trace_payload(self) -> dict[str, Any] | None:
        payload = self._last_trace_payload
        self._last_trace_payload = None
        return payload

    def _call_provider(
        self,
        raw_message: str,
        context: dict[str, Any],
    ) -> ConversationIntakeResult | None:
        try:
            payload = self._provider(raw_message, context)
            if payload is None:
                self.provider_fallback = True
                return None
            trace_payload = None
            if isinstance(payload, dict) and "llm_trace" in payload:
                trace_payload = payload.get("llm_trace")
                payload = payload.get("intake")
            if payload is None:
                self.provider_fallback = True
                if isinstance(trace_payload, dict):
                    schema_validation = trace_payload.get("schema_validation")
                    if not isinstance(schema_validation, dict):
                        schema_validation = {"ok": False, "fallback": True}
                    self._last_trace_payload = _redacted_trace_payload(
                        trace_payload,
                        parsed_output=None,
                        schema_validation=schema_validation,
                    )
                return None
            if isinstance(payload, ConversationIntakeResult):
                result = payload
            else:
                result = ConversationIntakeResult.model_validate(payload)
            result = _normalize_intake_result(result)
            if result.source == "provider_parse_error":
                self.provider_fallback = True
                if isinstance(trace_payload, dict):
                    schema_validation = trace_payload.get("schema_validation")
                    if not isinstance(schema_validation, dict):
                        schema_validation = {"ok": False, "fallback": True}
                    self._last_trace_payload = _redacted_trace_payload(
                        trace_payload,
                        parsed_output=None,
                        schema_validation=schema_validation,
                    )
                return None
            if isinstance(trace_payload, dict):
                result = result.model_copy(update={"source": "llm"})
                schema_validation = trace_payload.get("schema_validation")
                if not isinstance(schema_validation, dict):
                    schema_validation = {"ok": True}
                self._last_trace_payload = _redacted_trace_payload(
                    trace_payload,
                    parsed_output=result.model_dump(mode="json"),
                    schema_validation=schema_validation,
                )
            return result
        except (TimeoutError, ConnectionError, RuntimeError):
            self.provider_fallback = True
            return None
        except (TypeError, ValidationError) as exc:
            if "trace_payload" in locals() and isinstance(trace_payload, dict):
                self._last_trace_payload = _redacted_trace_payload(
                    trace_payload,
                    parsed_output=None,
                    schema_validation={"ok": False, "error": str(exc)},
                )
            return ConversationIntakeResult(
                intent="unknown",
                confidence=0.0,
                should_ask_user=True,
                ask_user_message_hint="我还需要再确认一下你的意思。",
                source="provider_error",
            )
        except Exception:
            self.provider_fallback = True
            return None


def _normalize_intake_result(result: ConversationIntakeResult) -> ConversationIntakeResult:
    item_context = _is_item_intake_result(result)
    slots = [
        slot.model_copy(
            update={
                "semantic_type": _canonical_slot_semantic_type(
                    slot.semantic_type,
                    item_context=item_context,
                ),
                "name": (
                    "item_name"
                    if _canonical_slot_semantic_type(
                        slot.semantic_type,
                        item_context=item_context,
                    )
                    == "item_name"
                    else slot.name
                ),
            }
        )
        for slot in result.slots
    ]
    present = {slot.semantic_type for slot in slots if slot.value}
    missing = [
        field.model_copy(
            update={
                "semantic_type": _canonical_slot_semantic_type(
                    field.semantic_type,
                    item_context=item_context,
                ),
                "display_name": (
                    "项目名称"
                    if _canonical_slot_semantic_type(
                        field.semantic_type,
                        item_context=item_context,
                    )
                    == "item_name"
                    else field.display_name
                ),
            }
        )
        for field in result.missing_fields
        if _canonical_slot_semantic_type(
            field.semantic_type,
            item_context=item_context,
        )
        not in present
    ]
    updates: dict[str, Any] = {
        "slots": slots,
        "missing_fields": missing,
    }
    if (result.missing_fields and not missing) or _has_actionable_intake_without_missing(
        result,
        slots,
        missing,
    ):
        updates["should_ask_user"] = False
        updates["ask_user_message_hint"] = None
    return result.model_copy(update=updates)


def _has_actionable_intake_without_missing(
    result: ConversationIntakeResult,
    slots: list[ConversationIntakeSlot],
    missing: list[ConversationMissingField],
) -> bool:
    if missing or not result.should_ask_user:
        return False
    if result.intent not in {"learn_operation", "execute_operation"}:
        return False
    if not result.target.url:
        return False
    if not (result.action.goal or result.action.canonical_goal or result.action.aliases):
        return False
    return any(slot.value for slot in slots)


def _canonical_slot_semantic_type(value: str, *, item_context: bool) -> str:
    if value == "project_name" or (item_context and value in {"entity_name", "name"}):
        return "item_name"
    return value


def _is_item_intake_result(result: ConversationIntakeResult) -> bool:
    action_terms = {
        value.lower()
        for value in [
            result.action.goal,
            result.action.canonical_goal,
            *result.action.aliases,
        ]
        if value
    }
    target_path = urlparse(result.target.url or "").path.rstrip("/")
    return (
        target_path == "/items"
        or any("项目" in term for term in action_terms)
        or any("item" in term for term in action_terms)
    )


def build_runtime_intake_service() -> ConversationIntakeService:
    """Build the production intake service.

    When an LLM provider is configured, runtime chat attempts the LLM-backed
    schema-constrained intake first. Provider unavailability falls back to the
    deterministic parser; malformed provider output returns a low-confidence
    safe result instead of executing.
    """

    return ConversationIntakeService(provider=_llm_intake_provider)


def redact_sensitive_payload(value: Any) -> Any:
    """Return a recursively redacted copy suitable for history/debug surfaces."""
    if isinstance(value, list):
        return [redact_sensitive_payload(item) for item in value]
    if isinstance(value, dict):
        is_sensitive_slot = value.get("sensitive") is True
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key == "value" and is_sensitive_slot:
                redacted[key] = REDACTED
            elif str(key) == "token_usage" or str(key).endswith("_tokens"):
                redacted[key] = redact_sensitive_payload(item)
            elif _SENSITIVE_KEY_RE.search(str(key)):
                redacted[key] = REDACTED if item is not None else None
            else:
                redacted[key] = redact_sensitive_payload(item)
        return redacted
    if isinstance(value, str):
        return redact_sensitive_text(value)
    return value


def _strip_private_runtime_payload(value: Any) -> Any:
    if isinstance(value, list):
        return [_strip_private_runtime_payload(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _strip_private_runtime_payload(item)
            for key, item in value.items()
            if key not in {"learned_path_id", "pending_choice_private_map"}
        }
    return value


def redact_sensitive_text(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith(("{", "[")):
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            pass
        else:
            redacted = redact_sensitive_payload(parsed)
            return json.dumps(redacted, ensure_ascii=False)

    value = _JSON_SENSITIVE_TEXT_RE.sub(
        lambda match: match.group(1) + REDACTED + match.group(3),
        text,
    )
    value = _PASSWORD_TEXT_RE.sub(lambda match: match.group(1) + REDACTED, value)
    return _POSITIONAL_CREDENTIAL_TEXT_RE.sub(
        lambda match: match.group(1) + REDACTED,
        value,
    )


def _llm_intake_provider(
    raw_message: str,
    context: dict[str, Any],
) -> dict[str, Any] | ConversationIntakeResult | None:
    if not settings.llm_api_key:
        return None
    try:
        prompt_asset = load_prompt_asset("conversation_intake_agent", version="v1")
    except PromptAssetError:
        return None

    request = LlmRequest(
        system=prompt_asset.assembled_prompt,
        messages=[
            LlmMessage(
                role="user",
                content=(
                    f"Current user message:\n{raw_message}\n\nRedacted session context:\n{context}"
                ),
            )
        ],
        response_schema=ConversationIntakeResult.model_json_schema(),
        temperature=0.0,
        max_tokens=1200,
        metadata={"surface": "conversation_intake"},
    )
    started = time.perf_counter()
    response = llm_provider.generate_structured(request)
    latency_ms = int((time.perf_counter() - started) * 1000)
    trace_payload = _llm_trace_payload(
        request,
        response,
        latency_ms,
        prompt_template_id=f"{prompt_asset.prompt_id}.{prompt_asset.version}",
        prompt_hash=prompt_asset.prompt_sha256,
    )
    if response.ok and response.parsed is not None:
        return {"intake": response.parsed, "llm_trace": trace_payload}
    if response.error and response.error.kind == "parse_error":
        return {
            "intake": ConversationIntakeResult(
                intent="unknown",
                confidence=0.0,
                should_ask_user=True,
                ask_user_message_hint="我还需要再确认一下你的意思。",
                source="provider_parse_error",
            ),
            "llm_trace": _redacted_trace_payload(
                trace_payload,
                parsed_output=None,
                schema_validation={
                    "ok": False,
                    "error_kind": response.error.kind,
                    "error": response.error.message,
                },
            ),
        }
    if response.error is not None:
        return {
            "intake": None,
            "llm_trace": _redacted_trace_payload(
                trace_payload,
                parsed_output=None,
                schema_validation={
                    "ok": False,
                    "error_kind": response.error.kind,
                    "error": response.error.message,
                    "fallback": True,
                },
            ),
        }
    return None


def _llm_trace_payload(
    request: LlmRequest,
    response: Any,
    latency_ms: int,
    *,
    prompt_template_id: str = "conversation_intake_agent.v1",
    prompt_hash: str | None = None,
) -> dict[str, Any]:
    request_payload = request.model_dump(mode="json")
    raw_response = response.model_dump(mode="json") if hasattr(response, "model_dump") else {}
    raw_provider = raw_response.get("raw")
    request_id = raw_provider.get("id") if isinstance(raw_provider, dict) else None
    prompt_material = repr(
        {
            "system": request.system,
            "messages": [message.model_dump() for message in request.messages],
            "schema": request.response_schema,
        }
    )
    return {
        "trace_id": f"trace-{uuid.uuid4()}",
        "purpose": "conversation_intake",
        "agent_role": "conversation_intake_agent",
        "provider": "openai_compatible",
        "model": response.model or request.model or settings.llm_default_model,
        "request_id": request_id,
        "prompt_template_id": prompt_template_id,
        "prompt_hash": prompt_hash or hashlib.sha256(prompt_material.encode()).hexdigest(),
        "schema_name": "ConversationIntakeResult",
        "schema_version": "m11.3.4",
        "schema_validation": {},
        "latency_ms": latency_ms,
        "token_usage": response.usage.model_dump(mode="json"),
        "raw_request": request_payload,
        "raw_response": raw_response,
        "parsed_output": response.parsed or {},
        "redaction": {
            "applied": True,
            "strategy": "conversation_sensitive_payload_redaction",
        },
    }


def _redacted_trace_payload(
    trace_payload: dict[str, Any],
    *,
    parsed_output: dict[str, Any] | None,
    schema_validation: dict[str, Any],
) -> dict[str, Any]:
    payload = dict(trace_payload)
    payload["schema_validation"] = schema_validation
    payload["parsed_output"] = parsed_output or payload.get("parsed_output") or {}
    payload["redaction"] = {
        **_dict_or_empty(payload.get("redaction")),
        "applied": True,
        "strategy": "conversation_sensitive_payload_redaction",
    }
    return redact_sensitive_payload(payload)


def _deterministic_intake(
    raw_message: str,
    *,
    context: dict[str, Any],
) -> ConversationIntakeResult:
    text = raw_message.strip()
    if not text:
        return ConversationIntakeResult(
            intent="unknown",
            confidence=0.0,
            should_ask_user=True,
            ask_user_message_hint="请告诉我你想学习或执行什么网页操作。",
        )

    url = _extract_url(text)
    pending = context.get("pending_intake")
    pending_target = context.get("pending_target")
    slots = _extract_slots(text, url=url)
    has_item_name_slot = any(slot.semantic_type == "item_name" for slot in slots)
    lowered = text.lower()
    has_learn_keyword = any(keyword in lowered or keyword in text for keyword in _LEARN_KEYWORDS)
    action = _infer_action(text, url=url)
    target = _target_from_url(url, text)

    if (
        has_learn_keyword
        and not url
        and isinstance(pending_target, dict)
        and pending_target.get("url")
    ):
        pending_url = str(pending_target["url"])
        target = _target_from_url(pending_url, text)
        action = _infer_action(text, url=pending_url)
        missing = _missing_login_fields(slots, text, pending_url)
        if not action.goal or action.goal == text:
            missing.append(
                ConversationMissingField(
                    semantic_type="operation_goal",
                    display_name="要学习的操作",
                )
            )
        return ConversationIntakeResult(
            intent="learn_operation",
            target=target,
            action=action,
            slots=slots,
            missing_fields=missing,
            confidence=0.82,
            should_ask_user=bool(missing),
            ask_user_message_hint=None,
        )

    if has_learn_keyword and has_item_name_slot and not url:
        return ConversationIntakeResult(
            intent="learn_operation",
            target=target,
            action=action,
            slots=slots,
            confidence=0.84,
            should_ask_user=False,
        )

    if pending and slots and not has_learn_keyword:
        return ConversationIntakeResult(
            intent="provide_missing_info",
            target=target,
            action=action,
            slots=slots,
            confidence=0.82,
        )

    if has_item_name_slot and not has_learn_keyword and action.canonical_goal == "新增项目":
        return ConversationIntakeResult(
            intent="execute_operation",
            target=target,
            action=action,
            slots=slots,
            confidence=0.78,
        )

    if slots and not url and not has_learn_keyword:
        return ConversationIntakeResult(
            intent="provide_missing_info",
            target=target,
            action=action,
            slots=slots,
            confidence=0.72,
        )

    if url and has_learn_keyword:
        missing = _missing_login_fields(slots, text, url)
        return ConversationIntakeResult(
            intent="learn_operation",
            target=target,
            action=action,
            slots=slots,
            missing_fields=missing,
            confidence=0.86 if not missing else 0.78,
            should_ask_user=bool(missing),
            ask_user_message_hint=("我需要登录用的用户名和密码。" if missing else None),
        )

    return ConversationIntakeResult(
        intent="execute_operation",
        target=target,
        action=action,
        slots=slots,
        confidence=0.75,
    )


def _extract_url(text: str) -> str | None:
    match = _URL_RE.search(text)
    return match.group(0) if match else None


def _target_from_url(url: str | None, text: str) -> ConversationIntakeTarget:
    if not url:
        return ConversationIntakeTarget()
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else None
    page_hint = "工作台登录页" if "工作台" in text or "workspace" in url else None
    if not page_hint and parsed.path.rstrip("/") == "/items":
        page_hint = "项目列表页"
    return ConversationIntakeTarget(url=url, site_origin=origin, page_hint=page_hint)


def _extract_slots(text: str, *, url: str | None) -> list[ConversationIntakeSlot]:
    slots: list[ConversationIntakeSlot] = []
    username = _extract_label_value(text, _USERNAME_LABELS)
    password = _extract_label_value(text, _PASSWORD_LABELS)
    item_name = _extract_item_name(text, url=url)

    if (username is None or password is None) and url:
        pair = _extract_positional_credential_pair(text, url)
        if pair is not None:
            username = username or pair[0]
            password = password or pair[1]

    if username is not None:
        slots.append(
            ConversationIntakeSlot(
                name="operator_account",
                semantic_type="username",
                label_seen=_label_seen(text, _USERNAME_LABELS),
                value=username,
                sensitive=False,
            )
        )
    if password is not None:
        slots.append(
            ConversationIntakeSlot(
                name="access_secret",
                semantic_type="password",
                label_seen=_label_seen(text, _PASSWORD_LABELS),
                value=password,
                sensitive=True,
            )
        )
    if item_name is not None:
        slots.append(
            ConversationIntakeSlot(
                name="item_name",
                semantic_type="item_name",
                label_seen=_label_seen(text, _ITEM_NAME_LABELS),
                value=item_name,
                sensitive=False,
            )
        )
    return slots


def _extract_label_value(text: str, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        match = re.search(
            rf"{re.escape(label)}[是为]?\s*[:：]?\s*{_VALUE_PATTERN}",
            text,
            re.I,
        )
        if match:
            return match.group(1)
    return None


def _extract_item_name(text: str, *, url: str | None) -> str | None:
    item_context = _is_item_name_context(text, url=url)
    for label in _ITEM_NAME_LABELS:
        if label == "name":
            label_pattern = r"(?<![A-Za-z0-9_])name(?![A-Za-z0-9_])"
        else:
            label_pattern = re.escape(label)
        match = re.search(
            rf"{label_pattern}\s*(?:叫|是|为|=|:|：)?\s*{_VALUE_PATTERN}",
            text,
            re.I,
        )
        if not match:
            continue
        value = match.group(1)
        if label in ("项目名称", "项目名") or item_context or "项目" in value:
            return value

    if "名称" in text or "项目名" in text or "name" in text.lower():
        return None
    match = re.search(
        rf"(?:新增|创建|添加)\s*(?!项目(?:$|[\s，。,.；;!！?？])){_VALUE_PATTERN}",
        text,
        re.I,
    )
    if match:
        return match.group(1)
    return None


def _is_item_name_context(text: str, *, url: str | None) -> bool:
    if _canonical_goal(text, url=url) == "新增项目":
        return True
    path = urlparse(url or "").path.rstrip("/") if url else ""
    return path == "/items"


def _label_seen(text: str, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        if label in text:
            return label
    return None


def _extract_positional_credential_pair(text: str, url: str) -> tuple[str, str] | None:
    after_url = text.split(url, 1)[-1]
    match = re.search(
        r"([A-Za-z0-9_.@-]+)\s*/\s*([A-Za-z0-9_.@#$%^&*+=-]+)",
        after_url,
    )
    if not match:
        return None
    return match.group(1), match.group(2)


def _missing_login_fields(
    slots: list[ConversationIntakeSlot],
    text: str,
    url: str | None,
) -> list[ConversationMissingField]:
    if not _looks_like_login_goal(text, url):
        return []
    present = {slot.semantic_type for slot in slots if slot.value}
    missing: list[ConversationMissingField] = []
    if "username" not in present:
        missing.append(
            ConversationMissingField(
                semantic_type="username",
                display_name="用户名或账号",
            )
        )
    if "password" not in present:
        missing.append(
            ConversationMissingField(
                semantic_type="password",
                display_name="密码或口令",
            )
        )
    return missing


def _looks_like_login_goal(text: str, url: str | None) -> bool:
    url_value = (url or "").lower()
    return (
        "工作台" in text
        or "workspace" in url_value
        or any(token in text for token in ("账号", "密码", "口令"))
    )


def _infer_action(text: str, *, url: str | None) -> ConversationIntakeAction:
    canonical = _canonical_goal(text, url=url)
    aliases = _aliases_for(canonical)
    return ConversationIntakeAction(
        goal=_goal_text(text, canonical),
        canonical_goal=canonical,
        aliases=aliases,
    )


def _canonical_goal(text: str, *, url: str | None) -> str | None:
    url_value = url or ""
    lowered = text.lower()
    path = urlparse(url_value).path.rstrip("/") if url_value else ""
    if (
        any(token in text for token in ("新增", "添加", "创建"))
        and ("项目" in text or "item" in lowered)
    ) or (path == "/items" and any(token in text for token in ("新增", "添加", "创建"))):
        return "新增项目"
    if "工作台" in text or "workspace" in url_value:
        return "进入工作台"
    if "登录" in text or "login" in url_value:
        return "登录"
    if "打开" in text:
        return text.strip()
    return None


def _goal_text(text: str, canonical: str | None) -> str | None:
    if canonical is not None:
        return canonical
    stripped = text.strip()
    return stripped or None


def _aliases_for(canonical: str | None) -> list[str]:
    if canonical == "新增项目":
        return ["新增项目", "帮我新增项目", "创建项目", "添加项目"]
    if canonical == "进入工作台":
        return ["进入工作台", "登录", "打开工作台", "帮我进入工作台", "进一下工作台"]
    if canonical == "登录":
        return ["登录", "帮我登录", "登录一下", "进入页面"]
    return [canonical] if canonical else []


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
