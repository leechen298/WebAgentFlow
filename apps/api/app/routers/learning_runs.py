from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.exceptions import AppError
from app.repos.exploration_run_repo import ExplorationRunRepository
from app.repos.recording_repo import RecordingRepository
from app.schemas.common import ApiResponse, CursorPage, decode_cursor, encode_cursor
from app.schemas.exploration_run import (
    ExplorationRunCreate,
    ExplorationRunRead,
    ExplorationRunUpdate,
)
from app.services.candidate_inference import infer_candidates
from app.services.exploration_run_service import ExplorationRunService
from app.services.html_ast_parser import parse_html

router = APIRouter(prefix="/learning/runs", tags=["learning"])
DbSession = Annotated[Session, Depends(get_db)]


def _service(db: Session) -> ExplorationRunService:
    return ExplorationRunService(ExplorationRunRepository(db))


@router.get("/list", response_model=ApiResponse[CursorPage[ExplorationRunRead]])
def list_exploration_runs(
    db: DbSession,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
) -> ApiResponse[CursorPage[ExplorationRunRead]]:
    cursor_created_at = cursor_id = None
    if cursor:
        cursor_created_at, cursor_id = decode_cursor(cursor)
    items, has_next = _service(db).list_page(limit, cursor_created_at, cursor_id)
    next_cursor = (
        encode_cursor(items[-1].created_at, items[-1].id) if has_next and items else None
    )
    return ApiResponse(
        data=CursorPage(items=items, has_next=has_next, next_cursor=next_cursor)
    )


@router.post("/create", response_model=ApiResponse[ExplorationRunRead])
def create_exploration_run(
    payload: ExplorationRunCreate, db: DbSession
) -> ApiResponse[ExplorationRunRead]:
    return ApiResponse(data=_service(db).create(payload))


@router.get("/get", response_model=ApiResponse[ExplorationRunRead])
def get_exploration_run(
    run_id: Annotated[str, Query(...)], db: DbSession
) -> ApiResponse[ExplorationRunRead]:
    return ApiResponse(data=_service(db).get(run_id))


class ExplorationRunUpdatePayload(BaseModel):
    run_id: str
    update_data: ExplorationRunUpdate


@router.post("/update", response_model=ApiResponse[ExplorationRunRead])
def update_exploration_run(
    payload: ExplorationRunUpdatePayload, db: DbSession
) -> ApiResponse[ExplorationRunRead]:
    return ApiResponse(
        data=_service(db).update(payload.run_id, payload.update_data)
    )


class ExplorationRunDeletePayload(BaseModel):
    run_id: str


@router.post("/delete", response_model=ApiResponse[dict[str, str]])
def delete_exploration_run(
    payload: ExplorationRunDeletePayload, db: DbSession
) -> ApiResponse[dict[str, str]]:
    _service(db).delete(payload.run_id)
    return ApiResponse(data={"run_id": payload.run_id})


# ---------------------------------------------------------------------------
# Candidate inference endpoint
# ---------------------------------------------------------------------------


class InferCandidatesPayload(BaseModel):
    """Infer interactive candidate elements from a recording's AST + mutations."""

    recording_id: str
    """ID of the recording whose captured HTML will be parsed into AST."""

    run_id: str | None = None
    """Optional ExplorationRun ID — if provided, results are written back."""

    score_threshold: float = 0.10
    max_candidates: int = 200


class InferCandidatesResult(BaseModel):
    recording_id: str
    candidate_count: int
    hint_count: int
    candidate_elements: list[dict[str, Any]]
    interaction_hints: list[dict[str, Any]]
    written_to_run: str | None = None


@router.post("/infer-candidates", response_model=ApiResponse[InferCandidatesResult])
def infer_candidates_from_recording(
    payload: InferCandidatesPayload, db: DbSession
) -> ApiResponse[InferCandidatesResult]:
    """Analyze a recording's page AST and mutation history to identify
    candidate interactive elements and generate exploration hints.

    Requires the recording to have captured HTML in meta.capturedHtml.
    Optionally writes results back to an ExplorationRun.
    """
    # 1. Load recording
    rec_repo = RecordingRepository(db)
    recording = rec_repo.get(payload.recording_id)
    if recording is None:
        raise AppError(
            f"Recording '{payload.recording_id}' not found.",
            status_code=404,
            code=404,
        )

    meta = recording.meta or {}

    # 2. Parse HTML → Full AST
    captured_html = meta.get("capturedHtml") or meta.get("captured_html")
    if not captured_html:
        raise AppError(
            "Recording has no captured HTML (meta.capturedHtml). "
            "Cannot infer candidates without page HTML.",
            status_code=400,
        )
    iframe_html = meta.get("iframeHtml") or meta.get("iframe_html")
    full_ast = parse_html(captured_html, iframe_html=iframe_html)

    # 3. Extract mutations
    mutations: list[dict[str, Any]] = meta.get("domMutations") or []

    # 4. Run inference
    candidates, hints = infer_candidates(
        full_ast,
        mutations,
        score_threshold=payload.score_threshold,
        max_candidates=payload.max_candidates,
    )

    # 5. Optionally write back to ExplorationRun
    written_to_run = None
    if payload.run_id:
        svc = _service(db)
        run = svc.get(payload.run_id)
        run.candidate_elements_json = candidates
        run.interaction_hints_json = hints
        from app.repos.exploration_run_repo import ExplorationRunRepository

        ExplorationRunRepository(db).update(run)
        written_to_run = payload.run_id

    return ApiResponse(
        data=InferCandidatesResult(
            recording_id=payload.recording_id,
            candidate_count=len(candidates),
            hint_count=len(hints),
            candidate_elements=candidates,
            interaction_hints=hints,
            written_to_run=written_to_run,
        )
    )
