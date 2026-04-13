from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.repos.recording_repo import RecordingRepository
from app.schemas.common import ApiResponse, CursorPage, decode_cursor, encode_cursor
from app.schemas.recording import (
    AgentStepListView,
    NormalizedRecordingRead,
    OperationStepResult,
    RecordingCreate,
    RecordingRead,
    RecordingUpdate,
)
from app.services.ast_simplifier import simplify_ast
from app.services.html_ast_parser import parse_html
from app.services.agent_input_builder import build_page_context, build_steps_context
from app.services.page_understanding import generate_page_understanding
from app.services.step_understanding import generate_step_understanding
from app.services.recording_normalizer import normalize_recording, normalized_recording_to_dict
from app.services.recording_service import RecordingService
from app.services.step_builder import build_steps, to_agent_steps

router = APIRouter(prefix="/recordings", tags=["recordings"])
DbSession = Annotated[Session, Depends(get_db)]


def get_service(db: Session) -> RecordingService:
    return RecordingService(RecordingRepository(db))


@router.get("/list", response_model=ApiResponse[CursorPage[RecordingRead]])
def list_recordings(
    db: DbSession,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
) -> ApiResponse[CursorPage[RecordingRead]]:
    cursor_created_at = cursor_id = None
    if cursor:
        cursor_created_at, cursor_id = decode_cursor(cursor)
    items, has_next = get_service(db).list_recordings_page(limit, cursor_created_at, cursor_id)
    next_cursor = encode_cursor(items[-1].created_at, items[-1].id) if has_next and items else None
    return ApiResponse(data=CursorPage(items=items, has_next=has_next, next_cursor=next_cursor))


@router.post("/create", response_model=ApiResponse[RecordingRead])
def create_recording(
    payload: RecordingCreate,
    db: DbSession,
) -> ApiResponse[RecordingRead]:
    return ApiResponse(data=get_service(db).create_recording(payload))


@router.get("/get", response_model=ApiResponse[RecordingRead])
def get_recording(
    recording_id: Annotated[str, Query(...)],
    db: DbSession,
) -> ApiResponse[RecordingRead]:
    return ApiResponse(data=get_service(db).get_recording(recording_id))


class RecordingUpdatePayload(BaseModel):
    recording_id: str
    update_data: RecordingUpdate


@router.post("/update", response_model=ApiResponse[RecordingRead])
def update_recording(
    payload: RecordingUpdatePayload,
    db: DbSession,
) -> ApiResponse[RecordingRead]:
    return ApiResponse(
        data=get_service(db).update_recording(payload.recording_id, payload.update_data)
    )


class RecordingDeletePayload(BaseModel):
    recording_id: str


@router.post("/delete", response_model=ApiResponse[dict[str, str]])
def delete_recording(
    payload: RecordingDeletePayload,
    db: DbSession,
) -> ApiResponse[dict[str, str]]:
    get_service(db).delete_recording(payload.recording_id)
    return ApiResponse(data={"recording_id": payload.recording_id})


@router.get("/get_normalized", response_model=ApiResponse[NormalizedRecordingRead])
def get_normalized_recording(
    recording_id: Annotated[str, Query(...)],
    db: DbSession,
) -> ApiResponse[NormalizedRecordingRead]:
    recording = get_service(db).get_recording(recording_id)
    # Extract initialState from meta (camelCase key, stored by the extension)
    initial_state = (recording.meta or {}).get("initialState") if recording.meta else None
    nr = normalize_recording(
        recording_id,
        recording.events or [],
        initial_state=initial_state,
    )
    return ApiResponse(data=NormalizedRecordingRead(**normalized_recording_to_dict(nr)))


@router.get("/get_steps", response_model=ApiResponse[OperationStepResult])
def get_recording_steps(
    recording_id: Annotated[str, Query(...)],
    db: DbSession,
) -> ApiResponse[OperationStepResult]:
    recording = get_service(db).get_recording(recording_id)
    dom_mutations = (recording.meta or {}).get("domMutations", []) if recording.meta else []
    result = build_steps(
        recording_id,
        recording.events or [],
        dom_mutations,
    )
    return ApiResponse(data=OperationStepResult(**result))


@router.get("/get_agent_steps", response_model=ApiResponse[AgentStepListView])
def get_agent_steps(
    recording_id: Annotated[str, Query(...)],
    db: DbSession,
) -> ApiResponse[AgentStepListView]:
    """Agent-ready step view — minimal, stable projection for Agent consumption."""
    recording = get_service(db).get_recording(recording_id)
    dom_mutations = (recording.meta or {}).get("domMutations", []) if recording.meta else []
    result = build_steps(
        recording_id,
        recording.events or [],
        dom_mutations,
    )
    agent_view = to_agent_steps(result)
    return ApiResponse(data=AgentStepListView(**agent_view))


@router.get("/get_page_understanding", response_model=ApiResponse[dict])
def get_page_understanding(
    recording_id: Annotated[str, Query(...)],
    db: DbSession,
) -> ApiResponse[dict]:
    """LLM-based page understanding — what the page is, its regions and actions.

    Parses the recording's captured HTML into a Simplified AST, builds a
    PageContext, and calls the LLM to produce a structured PageUnderstanding.
    """
    recording = get_service(db).get_recording(recording_id)

    # Build Simplified AST from captured HTML in meta
    simplified_ast = None
    meta = recording.meta or {}
    captured_html = meta.get("capturedHtml") or meta.get("captured_html")
    if captured_html:
        iframe_html = meta.get("iframeHtml") or meta.get("iframe_html")
        full_ast = parse_html(captured_html, iframe_html=iframe_html)
        simplified_ast = simplify_ast(full_ast)

    # Build PageContext
    page_ctx = build_page_context(
        recording_id,
        recording.events or [],
        simplified_ast,
    )

    # Generate understanding
    result = generate_page_understanding(page_ctx)
    return ApiResponse(data=result)


@router.get("/get_step_understanding", response_model=ApiResponse[dict])
def get_step_understanding(
    recording_id: Annotated[str, Query(...)],
    db: DbSession,
) -> ApiResponse[dict]:
    """LLM-based step understanding — how the page was used, key steps, change patterns.

    Builds operation steps from the recording, converts to AgentStepListView,
    then calls the LLM to produce a structured StepUnderstanding.
    """
    recording = get_service(db).get_recording(recording_id)
    dom_mutations = (recording.meta or {}).get("domMutations", []) if recording.meta else []

    raw_result = build_steps(
        recording_id,
        recording.events or [],
        dom_mutations,
    )
    agent_view = to_agent_steps(raw_result)
    steps_ctx = build_steps_context(recording_id, agent_view)

    result = generate_step_understanding(steps_ctx)
    return ApiResponse(data=result)
