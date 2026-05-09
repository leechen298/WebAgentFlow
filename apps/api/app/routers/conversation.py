"""M11.0 runtime conversation API endpoints.

Minimal HTTP facade over the 11.0.2 conversation store.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.conversation import ConversationSession as ConversationSessionOrm
from app.repos.conversation_repo import ConversationRepository
from app.schemas.common import ApiResponse
from app.schemas.conversation import (
    ConversationEventCreateRequest,
    ConversationEventResponse,
    ConversationMessageCreateRequest,
    ConversationMessageResponse,
    ConversationSessionCreateRequest,
    ConversationSessionResponse,
)

router = APIRouter(prefix="/conversation", tags=["conversation"])
DbSession = Annotated[Session, Depends(get_db)]


def _session_response(orm: ConversationSessionOrm) -> ConversationSessionResponse:
    return ConversationSessionResponse(
        id=orm.id,
        status=orm.status,
        current_mode=orm.current_mode,
        previous_status=orm.previous_status,
        metadata=orm.metadata_json,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _message_response(orm) -> ConversationMessageResponse:
    return ConversationMessageResponse(
        id=orm.id,
        session_id=orm.session_id,
        role=orm.role,
        content=orm.content,
        metadata=orm.metadata_json,
        created_at=orm.created_at,
    )


def _event_response(orm) -> ConversationEventResponse:
    return ConversationEventResponse(
        id=orm.id,
        session_id=orm.session_id,
        type=orm.type,
        payload=orm.payload_json,
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
