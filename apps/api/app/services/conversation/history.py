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
    ConversationMessageResponse,
    ConversationReplayHistorySummary,
    ConversationSessionListResponse,
    ConversationSessionResponse,
    ConversationSessionSummaryResponse,
)


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

        learned_actions = session.metadata_json.get("learned_actions") or []
        learning_runs = self._extract_learning_runs(events)
        replay_summaries = self._extract_replay_summaries(events)

        return ConversationHistoryResponse(
            session=ConversationSessionResponse(
                id=session.id,
                status=session.status,
                current_mode=session.current_mode,
                previous_status=session.previous_status,
                metadata=session.metadata_json,
                created_at=session.created_at,
                updated_at=session.updated_at,
            ),
            messages=[
                ConversationMessageResponse(
                    id=m.id,
                    session_id=m.session_id,
                    role=m.role,
                    content=m.content,
                    metadata=m.metadata_json,
                    created_at=m.created_at,
                )
                for m in messages
            ],
            events=[
                ConversationEventResponse(
                    id=e.id,
                    session_id=e.session_id,
                    type=e.type,
                    payload=e.payload_json,
                    created_at=e.created_at,
                )
                for e in events
            ],
            learned_actions=learned_actions,
            learning_runs=learning_runs,
            replay_summaries=replay_summaries,
            raw={
                "session": {
                    "id": session.id,
                    "status": session.status,
                    "current_mode": session.current_mode,
                    "previous_status": session.previous_status,
                    "metadata": session.metadata_json,
                    "created_at": (
                        session.created_at.isoformat() if session.created_at else None
                    ),
                    "updated_at": (
                        session.updated_at.isoformat() if session.updated_at else None
                    ),
                },
                "messages": [
                    {
                        "id": m.id,
                        "session_id": m.session_id,
                        "role": m.role,
                        "content": m.content,
                        "metadata": m.metadata_json,
                        "created_at": (
                            m.created_at.isoformat() if m.created_at else None
                        ),
                    }
                    for m in messages
                ],
                "events": [
                    {
                        "id": e.id,
                        "session_id": e.session_id,
                        "type": e.type,
                        "payload": e.payload_json,
                        "created_at": (
                            e.created_at.isoformat() if e.created_at else None
                        ),
                    }
                    for e in events
                ],
                "learned_actions": learned_actions,
                "learning_runs": [run.model_dump() for run in learning_runs],
                "replay_summaries": [s.model_dump() for s in replay_summaries],
            },
        )

    def _build_summary(
        self, session: ConversationSession
    ) -> ConversationSessionSummaryResponse:
        message_count = self.repo.count_messages(session.id)
        event_count = self.repo.count_events(session.id)
        last_user = self.repo.get_last_message_by_role(session.id, "user")
        last_agent = self.repo.get_last_message_by_role(session.id, "agent")
        learned_actions = session.metadata_json.get("learned_actions") or []
        return ConversationSessionSummaryResponse(
            id=session.id,
            status=session.status,
            current_mode=session.current_mode,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=message_count,
            event_count=event_count,
            last_user_message=last_user.content if last_user else None,
            last_agent_message=last_agent.content if last_agent else None,
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
