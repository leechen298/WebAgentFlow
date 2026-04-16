"""Exploration workbench API endpoints.

Provides the backend for the Exploration Workbench frontend:
  - Task definition listing and retrieval
  - Synchronous exploration run execution
  - Run approval / rejection (MVP placeholder)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.schemas.common import ApiResponse
from app.schemas.task_definition import TaskDefinition

router = APIRouter(prefix="/exploration", tags=["exploration"])
logger = logging.getLogger(__name__)

# Screenshots are stored in a fixed directory so they can be served via HTTP.
_SCREENSHOT_DIR = Path(__file__).resolve().parents[4] / "data" / "screenshots"
_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


# ───────────────────────────────────────────────────────────────────
# Task definition endpoints
# ───────────────────────────────────────────────────────────────────

class TaskListItem(BaseModel):
    id: str
    name: str
    description: str
    target_url: str
    step_count: int
    source: str
    variables: dict[str, Any]


@router.get("/tasks", response_model=ApiResponse[list[TaskListItem]])
def list_tasks() -> ApiResponse[list[TaskListItem]]:
    """List all available task definitions from data/tasks/."""
    from app.services.task_loader import list_tasks as _list

    tasks = _list()
    items = [
        TaskListItem(
            id=t.id,
            name=t.name,
            description=t.description,
            target_url=t.target_url,
            step_count=len(t.steps),
            source=t.source,
            variables=t.variables,
        )
        for t in tasks
    ]
    return ApiResponse(data=items)


@router.get("/tasks/{task_id}", response_model=ApiResponse[TaskDefinition])
def get_task(task_id: str) -> ApiResponse[TaskDefinition]:
    """Get a single task definition by ID."""
    from app.services.task_loader import load_task_by_id

    try:
        task = load_task_by_id(task_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiResponse(data=task)


# ───────────────────────────────────────────────────────────────────
# Exploration run endpoints
# ───────────────────────────────────────────────────────────────────

class RunExplorationPayload(BaseModel):
    task_id: str
    variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Override task variables (e.g. query text).",
    )
    headless: bool = Field(
        default=False,
        description="Run browser in headless mode.",
    )
    max_steps: int | None = Field(
        default=None,
        description="Limit the number of task steps executed after initial navigation.",
    )


class SupervisorAssessmentResponse(BaseModel):
    verdict: str = ""
    confidence: str = ""
    summary: str = ""
    step_assessments: list[dict[str, Any]] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    should_save_path: bool = False


class RunExplorationResponse(BaseModel):
    success: bool
    total_steps: int
    final_url: str
    final_title: str
    elapsed_ms: int | None
    summary: str
    final_screenshot_ref: str | None = None
    steps: list[dict[str, Any]] = Field(default_factory=list)
    supervisor: SupervisorAssessmentResponse | None = None


@router.post("/run", response_model=ApiResponse[RunExplorationResponse])
def run_exploration_endpoint(
    payload: RunExplorationPayload,
) -> ApiResponse[RunExplorationResponse]:
    """Execute an exploration task synchronously and return the full result.

    This is a blocking endpoint — the response is sent when the
    exploration completes. MVP only; streaming will come later.
    """
    from app.services.task_loader import load_task_by_id

    # Load task definition
    task = load_task_by_id(payload.task_id)

    # Override variables if provided
    if payload.variables:
        task = task.model_copy(update={"variables": {**task.variables, **payload.variables}})

    # Lazy import to avoid Playwright at module load
    from app.services.execution.execution_runtime import RuntimeConfig, create_execution_runtime
    from app.services.learning.exploration_loop import run_exploration
    from app.services.learning.exploration_supervisor import summarize_exploration

    runtime_config = RuntimeConfig(
        headless=payload.headless,
        screenshot_dir=str(_SCREENSHOT_DIR),
    )

    with create_execution_runtime(config=runtime_config) as runtime:
        result = run_exploration(task, runtime, max_steps=payload.max_steps)

    # Supervisor assessment
    supervisor_data = None
    try:
        assessment = summarize_exploration(task, result)
        supervisor_data = SupervisorAssessmentResponse(
            verdict=assessment.verdict,
            confidence=assessment.confidence,
            summary=assessment.summary,
            step_assessments=assessment.step_assessments,
            anomalies=assessment.anomalies,
            suggestions=assessment.suggestions,
            should_save_path=assessment.should_save_path,
        )
    except Exception as e:
        logger.warning("Supervisor assessment failed: %s", e)

    # Serialize steps — convert screenshot file paths to API URLs
    steps_data = []
    for step in result.steps:
        step_dict: dict[str, Any] = {
            "step_index": step.step_index,
            "intent": step.intent,
            "action_type": step.action_type,
            "target_summary": step.target_summary,
            "value": step.value,
            "timestamp_ms": step.timestamp_ms,
            "agent_note": step.agent_note,
        }
        if step.execution_result:
            er = step.execution_result.model_dump()
            er["screenshot_ref"] = _to_screenshot_url(er.get("screenshot_ref"))
            step_dict["execution_result"] = er
        if step.observation:
            obs = step.observation.model_dump()
            obs["screenshot_ref"] = _to_screenshot_url(obs.get("screenshot_ref"))
            step_dict["observation"] = obs
        if step.success_evaluation:
            step_dict["success_evaluation"] = step.success_evaluation.model_dump()
        steps_data.append(step_dict)

    return ApiResponse(
        data=RunExplorationResponse(
            success=result.success,
            total_steps=result.total_steps,
            final_url=result.final_url,
            final_title=result.final_title,
            elapsed_ms=result.elapsed_ms,
            summary=result.summary,
            final_screenshot_ref=_to_screenshot_url(result.final_screenshot_ref),
            steps=steps_data,
            supervisor=supervisor_data,
        )
    )


# ───────────────────────────────────────────────────────────────────
# Screenshot serving
# ───────────────────────────────────────────────────────────────────


def _to_screenshot_url(file_path: str | None) -> str | None:
    """Convert a local screenshot file path to an API-servable URL path."""
    if not file_path:
        return None
    name = Path(file_path).name
    return f"/exploration/screenshots/{name}"


@router.get("/screenshots/{filename}")
def get_screenshot(filename: str) -> FileResponse:
    """Serve a screenshot image by filename."""
    path = _SCREENSHOT_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Screenshot not found: {filename}")
    return FileResponse(path, media_type="image/png")


# ───────────────────────────────────────────────────────────────────
# Approval / rejection (MVP placeholder)
# ───────────────────────────────────────────────────────────────────

class ApproveRejectPayload(BaseModel):
    run_id: str
    note: str = ""


@router.post("/runs/{run_id}/approve", response_model=ApiResponse[dict[str, str]])
def approve_run(run_id: str, payload: ApproveRejectPayload | None = None) -> ApiResponse[dict[str, str]]:
    """Approve an exploration run result. MVP placeholder."""
    # TODO: Persist approval to LearnedPath with status=APPROVED
    return ApiResponse(data={"run_id": run_id, "status": "approved", "note": "MVP placeholder — not yet persisted"})


@router.post("/runs/{run_id}/reject", response_model=ApiResponse[dict[str, str]])
def reject_run(run_id: str, payload: ApproveRejectPayload | None = None) -> ApiResponse[dict[str, str]]:
    """Reject an exploration run result. MVP placeholder."""
    # TODO: Persist rejection
    return ApiResponse(data={"run_id": run_id, "status": "rejected", "note": "MVP placeholder — not yet persisted"})
