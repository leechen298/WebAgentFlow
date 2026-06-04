"""Human-readable conversation debug timeline read model."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from app.schemas.conversation import (
    ConversationDebugTimelineItem,
    ConversationDebugTimelineRawRef,
    ConversationEntryGateTrace,
    ConversationEventResponse,
    ConversationLlmTraceResponse,
    ConversationMessageResponse,
)

TimelineStatus = Literal["info", "waiting", "running", "success", "warning", "error", "cancelled"]
TimelineSource = Literal["message", "event", "trace", "derived"]

_URL_RE = re.compile(r"https?://", re.IGNORECASE)
_PRIVATE_TOKEN_RE = re.compile(
    r"(pending_choice_private_map|learned_path_id|old_learned_path_id|new_learned_path_id|"
    r"path_id|slot_overrides|execution_payload|replay_action|replay_actions|selector|xpath|"
    r"api[_-]?key|secret|credential|password|token)",
    re.IGNORECASE,
)


def build_debug_timeline(
    *,
    messages: list[ConversationMessageResponse],
    events: list[ConversationEventResponse],
    llm_traces: list[ConversationLlmTraceResponse],
    entry_gate_traces: list[ConversationEntryGateTrace],
) -> list[ConversationDebugTimelineItem]:
    rows: list[tuple[datetime | None, int, ConversationDebugTimelineItem]] = []
    order = 0
    event_created_at_by_id = {
        event.id: event.created_at
        for event in events
        if event.id
    }
    structured_trace_event_ids = {
        trace.source_event_id
        for trace in llm_traces
        if trace.source_event_id
    } | {
        trace.source_event_id
        for trace in entry_gate_traces
        if trace.source_event_id
    }

    for message in messages:
        item = _message_item(message, order)
        rows.append((item.created_at, order, item))
        order += 1

    for event in events:
        if event.id in structured_trace_event_ids:
            continue
        item = _event_item(event, order)
        rows.append((item.created_at, order, item))
        order += 1

    for trace in llm_traces:
        item = _trace_item(trace, order)
        rows.append((item.created_at, order, item))
        order += 1

    for trace in entry_gate_traces:
        item = _entry_gate_item(
            trace,
            order,
            event_created_at_by_id.get(trace.source_event_id or ""),
        )
        rows.append((item.created_at, order, item))
        order += 1

    rows.sort(key=lambda row: (row[0] is None, row[0] or datetime.max, row[1]))
    return [row[2] for row in rows]


def _message_item(
    message: ConversationMessageResponse,
    order: int,
) -> ConversationDebugTimelineItem:
    role = str(message.role)
    content = str(message.content or "")
    if role == "user":
        title = "用户输入页面地址" if _URL_RE.search(content) else "用户输入需求"
        summary = _truncate(content) or "收到用户输入。"
        kind = "user_message"
        status: TimelineStatus = "info"
    elif role == "agent":
        title = "我回复用户"
        summary = _truncate(content) or "已生成用户回复。"
        kind = "agent_response"
        status = (
            "warning"
            if message.response_provenance and message.response_provenance.fallback
            else "info"
        )
    else:
        title = f"记录 {role} 消息"
        summary = _truncate(content) or "记录了一条会话消息。"
        kind = "message"
        status = "info"

    trace_ids = (
        message.response_provenance.llm_trace_ids
        if message.response_provenance is not None
        else []
    )
    details = _safe_details(
        {
            "role": role,
            "content": content,
            "metadata": message.metadata,
            "response_provenance": (
                message.response_provenance.model_dump(mode="json")
                if message.response_provenance is not None
                else None
            ),
        }
    )
    return ConversationDebugTimelineItem(
        id=f"message-{message.id or order}",
        kind=kind,
        title=title,
        summary=summary,
        status=status,
        created_at=message.created_at,
        source="message",
        message_id=message.id,
        related_trace_ids=list(trace_ids),
        details=details,
        raw_ref=ConversationDebugTimelineRawRef(tab="transcript", id=message.id),
    )


def _event_item(event: ConversationEventResponse, order: int) -> ConversationDebugTimelineItem:
    payload = event.payload if isinstance(event.payload, dict) else {}
    event_type = str(event.type)
    progress_kind = str(payload.get("progress_kind") or "")
    kind = _event_kind(event_type, progress_kind)
    title = _event_title(event_type, progress_kind)
    status = _event_status(event_type, payload, progress_kind)
    summary = _event_summary(event_type, payload, progress_kind)
    trace_id = str(payload.get("trace_id") or "") or None

    return ConversationDebugTimelineItem(
        id=f"event-{event.id or order}",
        kind=kind,
        title=title,
        summary=summary,
        status=status,
        created_at=event.created_at,
        source="event",
        event_id=event.id,
        trace_id=trace_id,
        related_trace_ids=[trace_id] if trace_id else [],
        details=_safe_details(payload),
        raw_ref=ConversationDebugTimelineRawRef(tab="events", id=event.id),
    )


def _trace_item(trace: ConversationLlmTraceResponse, order: int) -> ConversationDebugTimelineItem:
    status: TimelineStatus = "error" if trace.validation.get("status") == "error" else "info"
    if trace.redaction.get("applied") is False:
        status = "warning"
    details = _safe_details(
        {
            "purpose": trace.purpose,
            "agent_role": trace.agent_role,
            "provider": trace.provider,
            "model": trace.model,
            "request_id": trace.request_id,
            "schema_name": trace.schema_name,
            "schema_version": trace.schema_version,
            "validation": trace.validation,
            "latency_ms": trace.latency_ms,
            "usage": trace.usage,
            "redaction": trace.redaction,
        }
    )
    return ConversationDebugTimelineItem(
        id=f"trace-{trace.trace_id or order}",
        kind="llm_trace",
        title="LLM 调用完成",
        summary=_provider_summary(trace.provider, trace.model, trace.request_id),
        status=status,
        created_at=trace.created_at,
        source="trace",
        event_id=trace.source_event_id,
        trace_id=trace.trace_id,
        details=details,
        raw_ref=ConversationDebugTimelineRawRef(tab="raw", id=trace.trace_id),
    )


def _entry_gate_item(
    trace: ConversationEntryGateTrace,
    order: int,
    created_at: datetime | None,
) -> ConversationDebugTimelineItem:
    status: TimelineStatus = "warning" if trace.fallback or trace.error_kind else "info"
    details = _safe_details(trace.model_dump(mode="json"))
    runtime_need = "需要" if trace.requires_agent_runtime else "不需要"
    return ConversationDebugTimelineItem(
        id=f"entry-gate-{trace.source_event_id or order}",
        kind="entry_gate",
        title="入口门禁判断",
        summary=f"识别为 {trace.category}，{runtime_need} Agent runtime。",
        status=status,
        created_at=created_at,
        source="trace",
        event_id=trace.source_event_id,
        details=details,
        raw_ref=ConversationDebugTimelineRawRef(tab="raw", id=trace.source_event_id),
    )


def _event_kind(event_type: str, progress_kind: str) -> str:
    if event_type == "entry_gate_recorded":
        return "entry_gate"
    if event_type == "llm_trace_recorded":
        return "llm_trace"
    if event_type == "chat_progress_recorded":
        if progress_kind == "unknown_target_choice_created":
            return "action_options"
        if "choice_selected" in progress_kind:
            return "pending_choice"
        if "recovery" in progress_kind or "failure" in progress_kind:
            return "recovery"
        if "cancel" in progress_kind:
            return "cancel"
    if "learning" in event_type:
        return "learning"
    if "execution" in event_type or "replay" in event_type:
        return "replay"
    if "abort" in event_type or "cancel" in event_type:
        return "cancel"
    if "failed" in event_type or "error" in event_type:
        return "error"
    return "event"


def _event_title(event_type: str, progress_kind: str) -> str:
    mapping = {
        "entry_gate_recorded": "入口门禁判断",
        "llm_trace_recorded": "LLM 调用完成",
        "chat_learning_started": "开始学习页面操作",
        "chat_learning_completed": "学习完成",
        "chat_learning_failed": "学习失败",
        "chat_execution_started": "开始执行已学操作",
        "chat_execution_completed": "执行完成",
        "chat_execution_failed": "执行失败",
        "chat_no_path": "没有可用路径",
    }
    if event_type == "chat_progress_recorded":
        if progress_kind == "unknown_target_choice_created":
            return "生成下一步选项"
        if "choice_selected" in progress_kind:
            return "用户选择下一步"
        if "cancel" in progress_kind:
            return "用户取消当前任务"
        if "recovery" in progress_kind or "failure" in progress_kind:
            return "进入失败恢复"
    return mapping.get(event_type, f"记录事件：{event_type}")


def _event_status(event_type: str, payload: dict[str, Any], progress_kind: str) -> TimelineStatus:
    text = " ".join(str(payload.get(key) or "") for key in ("status", "result", "error_kind"))
    haystack = f"{event_type} {progress_kind} {text}".lower()
    if "cancel" in haystack or "abort" in haystack:
        return "cancelled"
    if "failed" in haystack or "error" in haystack or "provider_error" in haystack:
        return "error"
    if "fallback" in haystack or "unverified" in haystack or payload.get("fallback") is True:
        return "warning"
    if "started" in haystack or "running" in haystack:
        return "running"
    if progress_kind == "unknown_target_choice_created" or "waiting" in haystack:
        return "waiting"
    if "completed" in haystack or "success" in haystack or "succeeded" in haystack:
        return "success"
    return "info"


def _event_summary(event_type: str, payload: dict[str, Any], progress_kind: str) -> str:
    if event_type == "llm_trace_recorded":
        return _provider_summary(
            _string_or_none(payload.get("provider")),
            _string_or_none(payload.get("model")),
            _string_or_none(payload.get("request_id")),
        )
    summary = payload.get("summary") or payload.get("message") or payload.get("reason_summary")
    if isinstance(summary, str) and summary.strip():
        return _truncate(summary)
    if progress_kind == "unknown_target_choice_created":
        choices = payload.get("choices") if isinstance(payload.get("choices"), list) else []
        labels = [
            str(choice.get("label"))
            for choice in choices
            if isinstance(choice, dict) and choice.get("label")
        ]
        return "等待用户选择下一步：" + " / ".join(labels) if labels else "等待用户选择下一步。"
    if progress_kind:
        return f"记录 chat progress：{progress_kind}。"
    return f"记录 conversation event：{event_type}。"


def _provider_summary(provider: str | None, model: str | None, request_id: str | None) -> str:
    parts = [part for part in (provider, model, request_id) if part]
    return " / ".join(parts) if parts else "记录了一次 LLM 调用。"


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _truncate(value: str, limit: int = 180) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "..."


def _safe_details(value: Any) -> dict[str, Any]:
    safe = _drop_none(value)
    if not isinstance(safe, dict):
        return {}
    return _strip_private_tokens(safe)


def _drop_none(value: Any) -> Any:
    if isinstance(value, list):
        return [_drop_none(item) for item in value if item is not None]
    if isinstance(value, dict):
        return {
            str(key): _drop_none(item)
            for key, item in value.items()
            if item is not None
        }
    return value


def _strip_private_tokens(value: Any) -> Any:
    if isinstance(value, list):
        return [_strip_private_tokens(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _strip_private_tokens(item)
            for key, item in value.items()
            if not _PRIVATE_TOKEN_RE.search(str(key))
        }
    if isinstance(value, str) and _PRIVATE_TOKEN_RE.search(value):
        return "[redacted]"
    return value
