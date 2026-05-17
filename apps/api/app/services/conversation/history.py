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

        session_metadata = redact_sensitive_payload(session.metadata_json)
        learned_actions = session_metadata.get("learned_actions") or []
        learning_runs = self._extract_learning_runs(events)
        replay_summaries = self._extract_replay_summaries(events)
        llm_traces = self._extract_llm_traces(events)
        message_payloads = [self._message_response(m) for m in messages]
        event_payloads = [
            ConversationEventResponse(
                id=e.id,
                session_id=e.session_id,
                type=e.type,
                payload=redact_sensitive_payload(e.payload_json),
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
            raw={
                "session": {
                    "id": session.id,
                    "status": session.status,
                    "current_mode": session.current_mode,
                    "previous_status": session.previous_status,
                    "metadata": session_metadata,
                    "created_at": (
                        session.created_at.isoformat() if session.created_at else None
                    ),
                    "updated_at": (
                        session.updated_at.isoformat() if session.updated_at else None
                    ),
                },
                "messages": [self._raw_message(m) for m in messages],
                "events": [
                    {
                        "id": e.id,
                        "session_id": e.session_id,
                        "type": e.type,
                        "payload": redact_sensitive_payload(e.payload_json),
                        "created_at": (
                            e.created_at.isoformat() if e.created_at else None
                        ),
                    }
                    for e in events
                ],
                "learned_actions": learned_actions,
                "learning_runs": [run.model_dump() for run in learning_runs],
                "replay_summaries": [s.model_dump() for s in replay_summaries],
                "llm_traces": [trace.model_dump(mode="json") for trace in llm_traces],
            },
        )

    def _message_response(self, message: Any) -> ConversationMessageResponse:
        metadata = redact_sensitive_payload(message.metadata_json)
        return ConversationMessageResponse(
            id=message.id,
            session_id=message.session_id,
            role=message.role,
            content=redact_sensitive_payload(message.content),
            metadata=metadata,
            response_provenance=normalize_response_provenance(
                metadata,
                message.role,
            ),
            created_at=message.created_at,
        )

    def _raw_message(self, message: Any) -> dict[str, Any]:
        metadata = redact_sensitive_payload(message.metadata_json)
        provenance = normalize_response_provenance(metadata, message.role)
        payload: dict[str, Any] = {
            "id": message.id,
            "session_id": message.session_id,
            "role": message.role,
            "content": redact_sensitive_payload(message.content),
            "metadata": metadata,
            "created_at": (
                message.created_at.isoformat() if message.created_at else None
            ),
        }
        if provenance is not None:
            payload["response_provenance"] = provenance.model_dump(mode="json")
        return payload

    def _build_summary(
        self, session: ConversationSession
    ) -> ConversationSessionSummaryResponse:
        message_count = self.repo.count_messages(session.id)
        event_count = self.repo.count_events(session.id)
        last_user = self.repo.get_last_message_by_role(session.id, "user")
        last_agent = self.repo.get_last_message_by_role(session.id, "agent")
        learned_actions = redact_sensitive_payload(
            session.metadata_json.get("learned_actions") or []
        )
        return ConversationSessionSummaryResponse(
            id=session.id,
            status=session.status,
            current_mode=session.current_mode,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=message_count,
            event_count=event_count,
            last_user_message=(
                redact_sensitive_payload(last_user.content) if last_user else None
            ),
            last_agent_message=(
                redact_sensitive_payload(last_agent.content) if last_agent else None
            ),
            learned_action_count=len(learned_actions),
            learned_actions=learned_actions,
        )

    def _extract_learning_runs(
        self, events: list[Any]
    ) -> list[ConversationLearningRunSummary]:
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
                    summary=payload.get("summary")
                    or payload.get("message")
                    or "学习完成",
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
                        status=replay.get("replay_status")
                        or replay.get("status"),
                        summary=replay.get("summary")
                        or replay.get("message"),
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
                            summary=payload.get("summary")
                            or payload.get("message"),
                            raw=payload,
                        )
                    )
        return results

    def _extract_llm_traces(
        self, events: list[Any]
    ) -> list[ConversationLlmTraceResponse]:
        results: list[ConversationLlmTraceResponse] = []
        for event in events:
            if event.type != "llm_trace_recorded":
                continue
            payload = redact_sensitive_payload(event.payload_json or {})
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
                    schema_validation=_dict_or_empty(
                        payload.get("schema_validation")
                    ),
                    latency_ms=payload.get("latency_ms"),
                    token_usage=_dict_or_empty(payload.get("token_usage")),
                    raw_request=_dict_or_empty(payload.get("raw_request")),
                    raw_response=_dict_or_empty(payload.get("raw_response")),
                    parsed_output=_dict_or_empty(payload.get("parsed_output")),
                    redaction=_dict_or_empty(payload.get("redaction")),
                    raw=payload,
                    source_event_id=event.id,
                    created_at=event.created_at,
                )
            )
        return results


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
