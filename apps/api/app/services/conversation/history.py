"""M11.3.2 Chat History & Debug Console read-model service.

Builds aggregate read-model payloads from existing conversation tables.
No DB schema changes — pure read-only extraction.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.conversation import ConversationSession
from app.repos.conversation_repo import ConversationRepository
from app.schemas.conversation import (
    ConversationEntryGateTrace,
    ConversationEventResponse,
    ConversationHistoryResponse,
    ConversationLearningRunSummary,
    ConversationLlmTraceResponse,
    ConversationMessageResponse,
    ConversationReplayHistorySummary,
    ConversationSessionListResponse,
    ConversationSessionResponse,
    ConversationSessionSummaryResponse,
)
from app.services.conversation.intake import redact_sensitive_payload
from app.services.conversation.provenance import normalize_response_provenance
from app.services.conversation.trace_sanitizer import sanitize_provider_thinking

_PUBLIC_PRIVATE_KEYS = {
    "pending_choice_private_map",
    "learned_path_id",
    "old_learned_path_id",
    "new_learned_path_id",
    "path_id",
    "slot_overrides",
    "evidence_targets",
    "execution_payload",
    "replay_action",
    "replay_actions",
    "selector",
    "target_selector",
    "xpath",
}


class ConversationHistoryService:
    def __init__(self, db_session: Session) -> None:
        self.repo = ConversationRepository(db_session)

    def list_session_summaries(
        self,
        current_mode: str | None = None,
        status: str | None = None,
        updated_from: Any = None,
        updated_to: Any = None,
        limit: int = 50,
    ) -> ConversationSessionListResponse:
        sessions = self.repo.list_sessions(
            current_mode=current_mode,
            status=status,
            updated_from=updated_from,
            updated_to=updated_to,
            limit=limit,
        )
        items = [self._build_summary(s) for s in sessions]
        return ConversationSessionListResponse(items=items)

    def get_history(self, session_id: str) -> ConversationHistoryResponse | None:
        session = self.repo.get_session(session_id)
        if session is None:
            return None

        messages = self.repo.list_messages(session_id, limit=10_000)
        events = self.repo.list_events(session_id, limit=10_000)

        session_metadata = _history_safe_payload(session.metadata_json)
        learned_actions = session_metadata.get("learned_actions") or []
        learning_runs = self._extract_learning_runs(events)
        replay_summaries = self._extract_replay_summaries(events)
        llm_traces = self._extract_llm_traces(events)
        entry_gate_traces = self._extract_entry_gate_traces(events)
        message_payloads = [self._message_response(m) for m in messages]
        event_payloads = [
            ConversationEventResponse(
                id=e.id,
                session_id=e.session_id,
                type=e.type,
                payload=conversation_event_public_payload(e.payload_json, event_type=e.type),
                created_at=e.created_at,
            )
            for e in events
        ]

        return ConversationHistoryResponse(
            session=ConversationSessionResponse(
                id=session.id,
                status=session.status,
                current_mode=session.current_mode,
                previous_status=session.previous_status,
                metadata=session_metadata,
                created_at=session.created_at,
                updated_at=session.updated_at,
            ),
            messages=message_payloads,
            events=event_payloads,
            learned_actions=learned_actions,
            learning_runs=learning_runs,
            replay_summaries=replay_summaries,
            llm_traces=llm_traces,
            entry_gate_traces=entry_gate_traces,
            raw={
                "session": {
                    "id": session.id,
                    "status": session.status,
                    "current_mode": session.current_mode,
                    "previous_status": session.previous_status,
                    "metadata": session_metadata,
                    "created_at": (session.created_at.isoformat() if session.created_at else None),
                    "updated_at": (session.updated_at.isoformat() if session.updated_at else None),
                },
                "messages": [self._raw_message(m) for m in messages],
                "events": [
                    {
                        "id": e.id,
                        "session_id": e.session_id,
                        "type": e.type,
                        "payload": conversation_event_public_payload(
                            e.payload_json,
                            event_type=e.type,
                        ),
                        "created_at": (e.created_at.isoformat() if e.created_at else None),
                    }
                    for e in events
                ],
                "learned_actions": learned_actions,
                "learning_runs": [run.model_dump() for run in learning_runs],
                "replay_summaries": [s.model_dump() for s in replay_summaries],
                "llm_traces": [trace.model_dump(mode="json") for trace in llm_traces],
                "entry_gate_traces": [trace.model_dump(mode="json") for trace in entry_gate_traces],
            },
        )

    def _message_response(self, message: Any) -> ConversationMessageResponse:
        metadata = session_public_payload(message.metadata_json)
        return ConversationMessageResponse(
            id=message.id,
            session_id=message.session_id,
            role=message.role,
            content=conversation_message_public_content(message.content),
            metadata=metadata,
            response_provenance=normalize_response_provenance(
                metadata,
                message.role,
            ),
            created_at=message.created_at,
        )

    def _raw_message(self, message: Any) -> dict[str, Any]:
        metadata = session_public_payload(message.metadata_json)
        provenance = normalize_response_provenance(metadata, message.role)
        payload: dict[str, Any] = {
            "id": message.id,
            "session_id": message.session_id,
            "role": message.role,
            "content": _history_safe_payload(message.content),
            "metadata": metadata,
            "created_at": (message.created_at.isoformat() if message.created_at else None),
        }
        if provenance is not None:
            payload["response_provenance"] = provenance.model_dump(mode="json")
        return payload

    def _build_summary(self, session: ConversationSession) -> ConversationSessionSummaryResponse:
        message_count = self.repo.count_messages(session.id)
        event_count = self.repo.count_events(session.id)
        last_user = self.repo.get_last_message_by_role(session.id, "user")
        last_agent = self.repo.get_last_message_by_role(session.id, "agent")
        learned_actions = session_public_payload(session.metadata_json.get("learned_actions") or [])
        return ConversationSessionSummaryResponse(
            id=session.id,
            status=session.status,
            current_mode=session.current_mode,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=message_count,
            event_count=event_count,
            last_user_message=(_history_safe_payload(last_user.content) if last_user else None),
            last_agent_message=(_history_safe_payload(last_agent.content) if last_agent else None),
            learned_action_count=len(learned_actions),
            learned_actions=learned_actions,
        )

    def _extract_learning_runs(self, events: list[Any]) -> list[ConversationLearningRunSummary]:
        results: list[ConversationLearningRunSummary] = []
        for event in events:
            if event.type != "chat_learning_completed":
                continue
            payload = event.payload_json or {}
            results.append(
                ConversationLearningRunSummary(
                    source_event_id=event.id,
                    source_event_type=event.type,
                    run_id=payload.get("run_id"),
                    learned_path_id=payload.get("new_learned_path_id"),
                    status="learned",
                    summary=payload.get("summary") or payload.get("message") or "学习完成",
                    raw=payload,
                )
            )
        return results

    def _extract_replay_summaries(
        self, events: list[Any]
    ) -> list[ConversationReplayHistorySummary]:
        results: list[ConversationReplayHistorySummary] = []
        for event in events:
            payload = event.payload_json or {}
            replay = payload.get("replay")
            if replay is not None:
                results.append(
                    ConversationReplayHistorySummary(
                        source_event_id=event.id,
                        source_event_type=event.type,
                        learned_path_id=replay.get("learned_path_id"),
                        run_id=replay.get("run_id"),
                        status=replay.get("replay_status") or replay.get("status"),
                        summary=replay.get("summary") or replay.get("message"),
                        raw=replay,
                    )
                )
                continue

            # Fallback: known event types that carry replay summary directly
            if event.type in {
                "chat_execution_completed",
                "chat_execution_failed",
                "plan_execution_completed",
                "plan_execution_failed",
                "replay_completed",
                "replay_failed",
            }:
                # Try to find replay summary fields in the payload itself
                status = payload.get("replay_status") or payload.get("status")
                if status is not None:
                    results.append(
                        ConversationReplayHistorySummary(
                            source_event_id=event.id,
                            source_event_type=event.type,
                            learned_path_id=payload.get("learned_path_id"),
                            run_id=payload.get("run_id"),
                            status=status,
                            summary=payload.get("summary") or payload.get("message"),
                            raw=payload,
                        )
                    )
        return results

    def _extract_llm_traces(self, events: list[Any]) -> list[ConversationLlmTraceResponse]:
        results: list[ConversationLlmTraceResponse] = []
        for event in events:
            if event.type != "llm_trace_recorded":
                continue
            payload = _public_llm_trace_payload(event.payload_json or {})
            trace_id = str(payload.get("trace_id") or event.id)
            results.append(
                ConversationLlmTraceResponse(
                    trace_id=trace_id,
                    purpose=payload.get("purpose"),
                    agent_role=payload.get("agent_role"),
                    provider=payload.get("provider"),
                    model=payload.get("model"),
                    request_id=payload.get("request_id"),
                    prompt_template_id=payload.get("prompt_template_id"),
                    prompt_hash=payload.get("prompt_hash"),
                    schema_name=payload.get("schema_name"),
                    schema_version=payload.get("schema_version"),
                    validation=_dict_or_empty(payload.get("validation")),
                    latency_ms=payload.get("latency_ms"),
                    usage=_dict_or_empty(payload.get("usage")),
                    redaction=_dict_or_empty(payload.get("redaction")),
                    source_event_id=event.id,
                    created_at=event.created_at,
                )
            )
        return results

    def _extract_entry_gate_traces(
        self,
        events: list[Any],
    ) -> list[ConversationEntryGateTrace]:
        results: list[ConversationEntryGateTrace] = []
        for event in events:
            if event.type != "entry_gate_recorded":
                continue
            payload = _history_safe_payload(event.payload_json or {})
            entry_gate = payload.get("entry_gate")
            if not isinstance(entry_gate, dict):
                entry_gate = {}
            raw = _dict_or_empty(payload.get("raw"))
            results.append(
                ConversationEntryGateTrace(
                    source_event_id=event.id,
                    category=entry_gate.get("category") or "needs_clarification",
                    requires_agent_runtime=bool(entry_gate.get("requires_agent_runtime")),
                    skipped_intake_router=bool(payload.get("skipped_intake_router")),
                    confidence=float(entry_gate.get("confidence") or 0.0),
                    latency_ms=payload.get("latency_ms") or entry_gate.get("latency_ms"),
                    timeout_ms=payload.get("timeout_ms") or entry_gate.get("timeout_ms"),
                    provider=payload.get("provider") or entry_gate.get("provider"),
                    model=payload.get("model") or entry_gate.get("model"),
                    fallback=bool(payload.get("fallback") or entry_gate.get("fallback")),
                    error_kind=payload.get("error_kind") or entry_gate.get("error_kind"),
                    prompt_template_id=payload.get("prompt_template_id"),
                    prompt_hash=payload.get("prompt_hash"),
                    raw=payload if not raw else raw,
                )
            )
        return results


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def session_public_payload(value: Any) -> Any:
    return sanitize_provider_thinking(
        redact_sensitive_payload(_strip_session_private_payload(value))
    )


def _history_safe_payload(value: Any) -> Any:
    return sanitize_provider_thinking(
        redact_sensitive_payload(_strip_history_private_payload(value))
    )


def conversation_message_public_content(value: Any) -> Any:
    return _history_safe_payload(value)


def conversation_event_public_payload(value: Any, *, event_type: str | None = None) -> Any:
    if event_type == "llm_trace_recorded":
        return _public_llm_trace_payload(value)
    stripped = _strip_history_private_payload(value)
    progress_kind = stripped.get("progress_kind") if isinstance(stripped, dict) else None
    if progress_kind in {
        "eval_candidate_setup_applied",
        "pending_choice_created",
        "pending_choice_retry",
        "planner_choice_created",
        "planner_choice_selected",
    }:
        stripped = _strip_session_private_payload(stripped)
    return sanitize_provider_thinking(redact_sensitive_payload(stripped))


def _public_llm_trace_payload(value: Any) -> dict[str, Any]:
    payload = _dict_or_empty(value)
    result: dict[str, Any] = {}
    for key in (
        "trace_id",
        "purpose",
        "agent_role",
        "provider",
        "model",
        "request_id",
        "prompt_template_id",
        "prompt_hash",
        "schema_name",
        "schema_version",
        "latency_ms",
    ):
        if payload.get(key) is not None:
            result[key] = sanitize_provider_thinking(redact_sensitive_payload(payload.get(key)))

    validation = _public_trace_validation(payload.get("schema_validation"))
    if validation:
        result["validation"] = validation
    usage = _public_trace_usage(payload.get("token_usage") or payload.get("usage"))
    if usage:
        result["usage"] = usage
    redaction = _public_trace_redaction(payload.get("redaction"))
    if redaction:
        result["redaction"] = redaction
    return result


def _public_trace_validation(value: Any) -> dict[str, Any]:
    validation = _dict_or_empty(value)
    if not validation:
        return {}
    if validation.get("ok") is True or validation.get("valid") is True:
        return {"status": "ok"}
    status = str(validation.get("status") or "").strip().lower()
    if status in {"ok", "valid", "pass", "passed"}:
        return {"status": "ok"}
    if status in {"error", "invalid", "failed", "fail"}:
        result: dict[str, Any] = {"status": "error"}
    else:
        result = {"status": "error" if validation else "unknown"}
    error_count = validation.get("error_count")
    if isinstance(error_count, int):
        result["error_count"] = error_count
    return result


def _public_trace_usage(value: Any) -> dict[str, Any]:
    usage = _dict_or_empty(value)
    result: dict[str, Any] = {}
    for source_key, public_key in (
        ("prompt_tokens", "prompt"),
        ("completion_tokens", "completion"),
        ("total_tokens", "total"),
        ("prompt", "prompt"),
        ("completion", "completion"),
        ("total", "total"),
    ):
        metric = usage.get(source_key)
        if isinstance(metric, int | float):
            result[public_key] = metric
    return result


def _public_trace_redaction(value: Any) -> dict[str, Any]:
    redaction = _dict_or_empty(value)
    result: dict[str, Any] = {}
    for key in ("applied", "status", "strategy"):
        if key in redaction:
            result[key] = sanitize_provider_thinking(redact_sensitive_payload(redaction[key]))
    return result


def _strip_session_private_payload(value: Any) -> Any:
    if isinstance(value, list):
        return [_strip_session_private_payload(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _strip_session_private_payload(item)
            for key, item in value.items()
            if key not in _PUBLIC_PRIVATE_KEYS
        }
    return value


def _strip_history_private_payload(value: Any, *, in_pending_choice: bool = False) -> Any:
    if isinstance(value, list):
        return [
            _strip_history_private_payload(item, in_pending_choice=in_pending_choice)
            for item in value
        ]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key in _PUBLIC_PRIVATE_KEYS:
                if key == "execution_payload" and isinstance(item, dict):
                    result["execution_summary"] = _strip_history_private_payload(
                        {
                            "target_url": item.get("target_url"),
                            "alias": item.get("alias"),
                            "execution_evidence": item.get("execution_evidence"),
                        },
                        in_pending_choice=in_pending_choice,
                    )
                continue
            child_in_pending_choice = in_pending_choice or key == "pending_choice"
            result[key] = _strip_history_private_payload(
                item,
                in_pending_choice=child_in_pending_choice,
            )
        return result
    return value
