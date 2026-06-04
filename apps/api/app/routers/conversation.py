"""M11.0 runtime conversation API endpoints.

Store-level conversation facade plus the 11.0.6 dispatch endpoint.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.conversation import ConversationSession as ConversationSessionOrm
from app.repos.conversation_repo import ConversationRepository
from app.schemas.common import ApiResponse
from app.schemas.conversation import (
    ConversationDispatchRequest,
    ConversationDispatchResponse,
    ConversationEventCreateRequest,
    ConversationEventResponse,
    ConversationHistoryResponse,
    ConversationMessageCreateRequest,
    ConversationMessageResponse,
    ConversationSessionCreateRequest,
    ConversationSessionListResponse,
    ConversationSessionResponse,
)
from app.services.conversation.history import (
    conversation_event_public_payload,
    conversation_message_public_content,
    session_public_payload,
)
from app.services.conversation.provenance import normalize_response_provenance

router = APIRouter(prefix="/conversation", tags=["conversation"])
DbSession = Annotated[Session, Depends(get_db)]


def _session_response(orm: ConversationSessionOrm) -> ConversationSessionResponse:
    return ConversationSessionResponse(
        id=orm.id,
        status=orm.status,
        current_mode=orm.current_mode,
        previous_status=orm.previous_status,
        metadata=session_public_payload(orm.metadata_json),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _message_response(orm) -> ConversationMessageResponse:
    metadata = session_public_payload(orm.metadata_json)
    return ConversationMessageResponse(
        id=orm.id,
        session_id=orm.session_id,
        role=orm.role,
        content=conversation_message_public_content(orm.content),
        metadata=metadata,
        response_provenance=normalize_response_provenance(
            metadata,
            orm.role,
        ),
        created_at=orm.created_at,
    )


def _event_response(orm) -> ConversationEventResponse:
    return ConversationEventResponse(
        id=orm.id,
        session_id=orm.session_id,
        type=orm.type,
        payload=conversation_event_public_payload(orm.payload_json, event_type=orm.type),
        created_at=orm.created_at,
    )


def _require_session(repo: ConversationRepository, session_id: str) -> ConversationSessionOrm:
    session = repo.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session


# ── Sessions ─────────────────────────────────────────────────────────────────


@router.post("/sessions")
def create_session(
    db: DbSession,
    body: ConversationSessionCreateRequest,
) -> ApiResponse[ConversationSessionResponse]:
    repo = ConversationRepository(db)
    session = repo.create_session(
        current_mode=body.current_mode,
        metadata=body.metadata,
    )
    return ApiResponse(data=_session_response(session))


@router.get("/sessions/{session_id}")
def get_session(
    db: DbSession,
    session_id: str,
) -> ApiResponse[ConversationSessionResponse]:
    repo = ConversationRepository(db)
    session = _require_session(repo, session_id)
    return ApiResponse(data=_session_response(session))


@router.get("/sessions")
def list_sessions(
    db: DbSession,
    current_mode: str | None = None,
    status: str | None = None,
    updated_from: datetime | None = None,
    updated_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=100),
) -> ApiResponse[ConversationSessionListResponse]:
    from app.services.conversation.history import ConversationHistoryService

    svc = ConversationHistoryService(db)
    result = svc.list_session_summaries(
        current_mode=current_mode,
        status=status,
        updated_from=updated_from,
        updated_to=updated_to,
        limit=limit,
    )
    return ApiResponse(data=result)


# ── Messages ─────────────────────────────────────────────────────────────────


@router.post("/sessions/{session_id}/messages")
def append_message(
    db: DbSession,
    session_id: str,
    body: ConversationMessageCreateRequest,
) -> ApiResponse[ConversationMessageResponse]:
    repo = ConversationRepository(db)
    _require_session(repo, session_id)
    message = repo.append_message(
        session_id=session_id,
        role=body.role,
        content=body.content,
        metadata=body.metadata,
    )
    return ApiResponse(data=_message_response(message))


@router.get("/sessions/{session_id}/messages")
def list_messages(
    db: DbSession,
    session_id: str,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> ApiResponse[list[ConversationMessageResponse]]:
    repo = ConversationRepository(db)
    _require_session(repo, session_id)
    messages = repo.list_messages(session_id, limit=limit)
    return ApiResponse(data=[_message_response(m) for m in messages])


@router.get("/sessions/{session_id}/transcript")
def get_transcript(
    db: DbSession,
    session_id: str,
) -> ApiResponse[list[ConversationMessageResponse]]:
    repo = ConversationRepository(db)
    _require_session(repo, session_id)
    messages = repo.get_transcript(session_id)
    return ApiResponse(data=[_message_response(m) for m in messages])


# ── Events ───────────────────────────────────────────────────────────────────


@router.post("/sessions/{session_id}/events")
def append_event(
    db: DbSession,
    session_id: str,
    body: ConversationEventCreateRequest,
) -> ApiResponse[ConversationEventResponse]:
    repo = ConversationRepository(db)
    _require_session(repo, session_id)
    event = repo.append_event(
        session_id=session_id,
        type=body.type,
        payload=body.payload,
    )
    return ApiResponse(data=_event_response(event))


@router.get("/sessions/{session_id}/events")
def list_events(
    db: DbSession,
    session_id: str,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> ApiResponse[list[ConversationEventResponse]]:
    repo = ConversationRepository(db)
    _require_session(repo, session_id)
    events = repo.list_events(session_id, limit=limit)
    return ApiResponse(data=[_event_response(e) for e in events])


@router.get("/sessions/{session_id}/history")
def get_history(
    db: DbSession,
    session_id: str,
) -> ApiResponse[ConversationHistoryResponse]:
    from app.services.conversation.history import ConversationHistoryService

    svc = ConversationHistoryService(db)
    history = svc.get_history(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="session not found")
    return ApiResponse(data=history)


# ── Dispatch (11.0.6) ────────────────────────────────────────────────────────


def _dispatch_action_options(session: ConversationSessionOrm | None) -> list[dict[str, Any]]:
    if session is None:
        return []
    metadata = session_public_payload(session.metadata_json)
    pending_choice = metadata.get("pending_choice") if isinstance(metadata, dict) else None
    if not isinstance(pending_choice, dict):
        return []
    if pending_choice.get("render_as") != "action_options":
        return []
    options: list[dict[str, Any]] = []
    for choice in pending_choice.get("choices") or []:
        if not isinstance(choice, dict):
            continue
        choice_id = str(choice.get("choice_id") or "").strip()
        label = str(choice.get("label") or "").strip()
        if not choice_id or not label:
            continue
        options.append(
            {
                "id": choice_id,
                "label": label,
                "description": choice.get("description"),
                "intent": choice.get("intent"),
            }
        )
    return options


def _dispatch_response(
    result,
    session: ConversationSessionOrm | None = None,
) -> ConversationDispatchResponse:
    return ConversationDispatchResponse(
        session_id=result.session_id,
        previous_status=result.previous_status,
        next_status=result.next_status,
        command_kind=result.command_kind,
        user_response=result.user_response,
        action_options=_dispatch_action_options(session),
        events_appended=result.events_appended,
        message_id=result.message_id,
        allowed=result.allowed,
        error=result.error,
        replay_result=result.replay_result,
    )


@router.post("/sessions/{session_id}/dispatch")
def dispatch_input(
    db: DbSession,
    session_id: str,
    body: ConversationDispatchRequest,
) -> ApiResponse[ConversationDispatchResponse]:
    from app.repos.learned_paths_repo import LearnedPathRepository
    from app.services.conversation.entry_gate import build_runtime_entry_gate_service
    from app.services.conversation.intake import build_runtime_intake_service
    from app.services.conversation.orchestrator import ConversationOrchestrator
    from app.services.conversation.page_context import build_runtime_page_context_provider
    from app.services.conversation.replay_hook import run_explicit_replay
    from app.services.conversation.router_agent import build_runtime_router_service
    from app.services.learning.learning_run_service import (
        LearningRunRequest,
        LearningRunService,
    )
    from app.services.task_planning import (
        LearnedPathRetrievalService,
        PlanningPreviewService,
        TaskPathPlanner,
    )

    repo = ConversationRepository(db)
    _require_session(repo, session_id)

    def replay_handler(
        learned_path_id: str,
        url: str,
        *,
        headless: bool = True,
        slot_overrides: dict[str, str] | None = None,
        evidence_targets: list[Any] | None = None,
    ):
        return run_explicit_replay(
            db,
            learned_path_id,
            url,
            headless=headless,
            slot_overrides=slot_overrides,
            evidence_targets=evidence_targets,
        )

    def learning_handler(
        url: str,
        raw_input: str,
        *,
        headless: bool = True,
        fill_values: dict[str, str] | None = None,
        action_goal: str | None = None,
        canonical_goal: str | None = None,
        action_aliases: list[str] | None = None,
    ):
        return LearningRunService(db).run(
            LearningRunRequest(
                url=url,
                goal=raw_input,
                fill_values=fill_values,
                action_goal=action_goal,
                canonical_goal=canonical_goal,
                action_aliases=action_aliases or [],
                language="zh",
                headless=headless,
                product_level=True,
            )
        )

    learned_path_repo = LearnedPathRepository(db)
    retrieval = LearnedPathRetrievalService(learned_path_repo)
    planner = TaskPathPlanner()
    preview_service = PlanningPreviewService(retrieval, planner)

    orchestrator = ConversationOrchestrator(
        repo,
        replay_handler=replay_handler,
        planning_handler=preview_service.preview,
        execution_handler=replay_handler,
        learning_handler=learning_handler,
        entry_gate_service=build_runtime_entry_gate_service(),
        intake_service=build_runtime_intake_service(),
        router_service=build_runtime_router_service(),
        page_context_provider=build_runtime_page_context_provider(),
    )
    result = orchestrator.dispatch_user_input(
        session_id,
        body.input,
        metadata=body.metadata,
    )
    return ApiResponse(data=_dispatch_response(result, repo.get_session(session_id)))
