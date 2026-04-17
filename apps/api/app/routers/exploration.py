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
# Autonomous exploration — URL-only, no task definition
# ───────────────────────────────────────────────────────────────────


class AutonomousExplorePayload(BaseModel):
    url: str = Field(description="Target URL to explore.")
    goal: str = Field(default="", description="Optional goal description.")
    fill_value: str = Field(
        default="",
        description="Value to fill into the primary input (single-field mode).",
    )
    fill_values: dict[str, str] | None = Field(
        default=None,
        description="Multi-field values keyed by generic semantic role "
        "(username/password/email/text). Takes precedence over fill_value.",
    )
    headless: bool = Field(default=True, description="Run browser in headless mode.")
    spec_id: str | None = Field(
        default=None,
        description="If set, load apps/validation-site/specs/<spec_id>.assertions.json "
        "and run the comparator after exploration.",
    )
    scenario: str | None = Field(
        default=None,
        description="Scenario key within the spec (e.g. 'success' / 'failure'). "
        "Required when spec_id is set.",
    )


@router.post("/autonomous-run")
def autonomous_exploration_endpoint(
    payload: AutonomousExplorePayload,
) -> ApiResponse[dict[str, Any]]:
    """Run autonomous exploration on a URL.

    No pre-written selectors. No task definition. The system:
      1. Opens the URL
      2. Analyzes the page to discover interactive elements
      3. Plans actions from the analysis
      4. Executes the plan with Playwright
      5. Runs the project's internal supervisor Agent for verification

    Returns the full structured report plus supervisor verdict.
    """
    from app.services.execution.execution_runtime import (
        RuntimeConfig,
        create_execution_runtime,
    )
    from app.services.learning.autonomous_explorer import (
        run_autonomous_exploration,
    )

    runtime_config = RuntimeConfig(
        headless=payload.headless,
        screenshot_dir=str(_SCREENSHOT_DIR),
    )

    with create_execution_runtime(config=runtime_config) as runtime:
        result = run_autonomous_exploration(
            url=payload.url,
            runtime=runtime,
            goal=payload.goal,
            fill_value=payload.fill_value,
            fill_values=payload.fill_values,
        )

    # Optional: spec-driven verification
    verification_payload: dict[str, Any] | None = None
    if payload.spec_id:
        if not payload.scenario:
            raise HTTPException(
                status_code=400,
                detail="scenario is required when spec_id is set.",
            )
        try:
            from app.services.learning.page_verification import (
                load_spec,
                verify_against_spec,
            )

            spec, spec_path = load_spec(payload.spec_id)
            scorecard = verify_against_spec(result, spec, payload.scenario)
            verification_payload = {
                "spec_source": str(spec_path),
                "spec_id": spec.page_id,
                "scenario": payload.scenario,
                "scorecard": scorecard.model_dump(),
            }
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Verification failed: %s", exc)
            verification_payload = {"error": str(exc)[:300]}

    # Serialize — convert screenshot paths to API URLs
    data = result.model_dump()
    if verification_payload is not None:
        data["verification"] = verification_payload

    # Top-level screenshot
    if data.get("final_screenshot_ref"):
        data["final_screenshot_ref"] = _to_screenshot_url(data["final_screenshot_ref"])

    # Page analysis screenshot
    if data.get("page_analysis", {}).get("screenshot_ref"):
        data["page_analysis"]["screenshot_ref"] = _to_screenshot_url(
            data["page_analysis"]["screenshot_ref"]
        )

    # Each step's screenshot
    for step in data.get("steps", []):
        if step.get("screenshot_ref"):
            step["screenshot_ref"] = _to_screenshot_url(step["screenshot_ref"])

    return ApiResponse(data=data)


# ───────────────────────────────────────────────────────────────────
# Autonomous exploration — streaming (SSE)
# ───────────────────────────────────────────────────────────────────


def _normalize_event_screenshots(data: dict[str, Any]) -> dict[str, Any]:
    """Convert local screenshot paths to API URLs within an event payload.

    Screenshot paths show up in many events:
      - analysis_done.screenshot_ref
      - step_done.screenshot_ref + step_done.execution_result.screenshot_ref
      - self_assessment_done.final_screenshot_ref
    """
    if not isinstance(data, dict):
        return data
    if "screenshot_ref" in data:
        data["screenshot_ref"] = _to_screenshot_url(data["screenshot_ref"])
    if "final_screenshot_ref" in data:
        data["final_screenshot_ref"] = _to_screenshot_url(data["final_screenshot_ref"])
    return data


@router.post("/autonomous-run/stream")
def autonomous_exploration_stream(
    payload: AutonomousExplorePayload,
):
    """Streaming variant of autonomous-run via Server-Sent Events.

    Emits events at each phase boundary so the frontend workbench can
    render live progress (no black-box waiting).

    Event types (in order):
      - run_started
      - navigate_started / navigate_done
      - analysis_started / analysis_done
      - plan_done
      - step_started / step_done (per step)
      - self_assessment_done
      - supervisor_done
      - verification_done (only if spec_id provided)
      - run_completed (final payload, same shape as POST /autonomous-run)
      - run_failed (on exception)
    """
    import asyncio
    import json
    import queue
    import threading

    from fastapi.responses import StreamingResponse

    if payload.spec_id and not payload.scenario:
        raise HTTPException(
            status_code=400,
            detail="scenario is required when spec_id is set.",
        )

    event_queue: queue.Queue[tuple[str, dict[str, Any]] | None] = queue.Queue()

    def emit(event_type: str, data: dict[str, Any]) -> None:
        # Normalize screenshot paths so the browser can load them directly.
        try:
            data = _normalize_event_screenshots(dict(data))
        except Exception:
            pass
        event_queue.put((event_type, data))

    def worker() -> None:
        """Run the exploration in a background thread, pushing events as they occur."""
        from app.services.execution.execution_runtime import (
            RuntimeConfig,
            create_execution_runtime,
        )
        from app.services.learning.autonomous_explorer import (
            run_autonomous_exploration,
        )

        try:
            emit("run_started", {
                "url": payload.url,
                "goal": payload.goal,
                "fill_values": payload.fill_values,
                "spec_id": payload.spec_id,
                "scenario": payload.scenario,
                "headless": payload.headless,
            })

            runtime_config = RuntimeConfig(
                headless=payload.headless,
                screenshot_dir=str(_SCREENSHOT_DIR),
            )
            with create_execution_runtime(config=runtime_config) as runtime:
                result = run_autonomous_exploration(
                    url=payload.url,
                    runtime=runtime,
                    goal=payload.goal,
                    fill_value=payload.fill_value,
                    fill_values=payload.fill_values,
                    event_emitter=emit,
                )

            # Spec verification (mirrors the non-streaming endpoint)
            verification_payload: dict[str, Any] | None = None
            if payload.spec_id and payload.scenario:
                try:
                    from app.services.learning.page_verification import (
                        load_spec,
                        verify_against_spec,
                    )
                    spec, spec_path = load_spec(payload.spec_id)
                    scorecard = verify_against_spec(result, spec, payload.scenario)
                    verification_payload = {
                        "spec_source": str(spec_path),
                        "spec_id": spec.page_id,
                        "scenario": payload.scenario,
                        "scorecard": scorecard.model_dump(),
                    }
                    emit("verification_done", verification_payload)
                except FileNotFoundError as exc:
                    emit("verification_done", {"error": f"spec not found: {exc}"})
                except KeyError as exc:
                    emit("verification_done", {"error": f"scenario not found: {exc}"})
                except Exception as exc:
                    logger.exception("Verification failed: %s", exc)
                    emit("verification_done", {"error": str(exc)[:300]})

            # Final payload — same shape as /autonomous-run response.data
            final_data = result.model_dump()
            if verification_payload is not None:
                final_data["verification"] = verification_payload
            if final_data.get("final_screenshot_ref"):
                final_data["final_screenshot_ref"] = _to_screenshot_url(
                    final_data["final_screenshot_ref"],
                )
            if final_data.get("page_analysis", {}).get("screenshot_ref"):
                final_data["page_analysis"]["screenshot_ref"] = _to_screenshot_url(
                    final_data["page_analysis"]["screenshot_ref"],
                )
            for step in final_data.get("steps", []):
                if step.get("screenshot_ref"):
                    step["screenshot_ref"] = _to_screenshot_url(step["screenshot_ref"])
                inner = step.get("execution_result") or {}
                if inner.get("screenshot_ref"):
                    inner["screenshot_ref"] = _to_screenshot_url(inner["screenshot_ref"])

            emit("run_completed", final_data)

        except Exception as exc:
            logger.exception("Autonomous streaming run failed: %s", exc)
            emit("run_failed", {"error": str(exc)[:500]})
        finally:
            event_queue.put(None)  # sentinel

    threading.Thread(target=worker, daemon=True).start()

    async def event_generator():
        while True:
            item = await asyncio.to_thread(event_queue.get)
            if item is None:
                break
            event_type, data = item
            payload_json = json.dumps(data, ensure_ascii=False)
            yield f"event: {event_type}\ndata: {payload_json}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disable proxy buffering if behind nginx
            "Connection": "keep-alive",
        },
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
