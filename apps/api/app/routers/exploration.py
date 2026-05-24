"""Exploration workbench API endpoints.

Provides the backend for the Exploration Workbench frontend:
  - Task definition listing and retrieval
  - Synchronous exploration run execution
  - Run approval / rejection (MVP placeholder)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, get_db
from app.models.exploration_run import (
    ExplorationMode,
    ExplorationRun,
    ExplorationRunStatus,
    OperatorReviewStatus,
)
from app.models.learned_path import TrustStatus
from app.repos.exploration_run_repo import ExplorationRunRepository
from app.repos.learned_paths_repo import LearnedPathRepository
from app.schemas.common import ApiResponse, CursorPage, decode_cursor, encode_cursor
from app.schemas.learned_path import (
    LearnedPathDetail,
    LearnedPathSummary,
    TrustPatchRequest,
)
from app.schemas.learned_path_replay import ReplayRequest, ReplayResult
from app.schemas.page_analysis import PageAnalysis
from app.services.learning.page_verification import (
    SpecNotFound,
    SpecRootNotConfigured,
    UnsafeSpecId,
)
from app.services.learning.page_signature import (
    dom_fingerprint,
    path_template,
    query_signature,
)

router = APIRouter(prefix="/exploration", tags=["exploration"])
logger = logging.getLogger(__name__)

# Screenshots are stored in a fixed directory so they can be served via HTTP.
_SCREENSHOT_DIR = Path(__file__).resolve().parents[4] / "data" / "screenshots"
_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

DbSession = Annotated[Session, Depends(get_db)]


def _spec_http_exception(exc: Exception) -> HTTPException:
    """Map page spec loader exceptions to stable public HTTP errors."""
    if isinstance(exc, SpecRootNotConfigured):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, UnsafeSpecId):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, SpecNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=500, detail="Page verification spec error.")


def _scenario_matched_for(item: ExplorationRun) -> bool | None:
    """Resolve whether a persisted run satisfied the scenario's spec.

    Prefers the cached ``strategy_json.scenario_matched`` value written
    at persist time. Falls back to walking the result snapshot so older
    rows (persisted before this field existed) still surface correctly
    without a data migration.
    """
    strat = item.strategy_json or {}
    if "scenario_matched" in strat:
        cached = strat["scenario_matched"]
        return None if cached is None else bool(cached)
    snapshot = item.result_snapshot_json or {}
    vc = (
        ((snapshot.get("verification") or {}).get("scorecard") or {})
        .get("verdict_check") or {}
    )
    if "matches_expectation" in vc:
        return bool(vc["matches_expectation"])
    return None


def _pass_gate_status_for(item: ExplorationRun) -> str | None:
    """Resolve the strict pass_gate status for the list row.

    Always reads from the persisted result snapshot — cheap, and there's
    no write-time cache to keep in sync (the gate is derivable from
    scorecard anyway). Returns None for rows persisted before the gate
    shipped, and the list falls back to scenario_matched.
    """
    snapshot = item.result_snapshot_json or {}
    scorecard = (snapshot.get("verification") or {}).get("scorecard") or {}
    gate = scorecard.get("pass_gate") or {}
    return gate.get("status")


def _pass_gate_from_final_data(final_data: dict[str, Any]) -> str | None:
    """Pull ``pass_gate.status`` out of a run's final data blob.

    Used by the LearnedPath ingest hook to decide whether to persist a
    run as a reusable path. Mirrors ``_pass_gate_status_for`` but reads
    from the in-flight ``final_data`` dict instead of a persisted row.
    """
    if not isinstance(final_data, dict):
        return None
    scorecard = (final_data.get("verification") or {}).get("scorecard") or {}
    gate = scorecard.get("pass_gate") or {}
    return gate.get("status")


def _scenario_verdict_from_pass_gate(status: str | None) -> str | None:
    """Map the spec-level pass gate to the public verdict vocabulary.

    The rule-side engine still computes a mechanical page outcome first:
    a negative-path scenario like ``invalid_credentials`` mechanically
    ends on a login failure. Once the comparator proves that this is the
    expected outcome, the public run verdict should be scenario-relative:
    matching the spec is ``success``; deviating from it is ``failure``.
    """
    if status == "pass":
        return "success"
    if status == "fail":
        return "failure"
    if status == "unverified":
        return "uncertain"
    return None


def _apply_scenario_relative_verdicts(
    final_data: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Rewrite public verdict fields from mechanical to scenario-relative.

    Internal audit details are preserved under ``mechanical_verdict`` so
    the raw browser outcome is still inspectable. The scorecard keeps
    ``verdict_check.self_verdict`` unchanged because it is the comparator
    evidence used to decide whether the scenario expectation matched.
    """
    if not isinstance(final_data, dict):
        return final_data

    status = _pass_gate_from_final_data(final_data)
    scenario_verdict = _scenario_verdict_from_pass_gate(status)
    if scenario_verdict is None:
        return final_data

    current = final_data.get("verdict")
    if current != scenario_verdict:
        final_data.setdefault("mechanical_verdict", current)
        final_data["verdict"] = scenario_verdict
        final_data["success"] = scenario_verdict == "success"

    supervisor = final_data.get("supervisor")
    if isinstance(supervisor, dict):
        current_supervisor = supervisor.get("verdict")
        if current_supervisor != scenario_verdict:
            supervisor.setdefault("mechanical_verdict", current_supervisor)
            supervisor["verdict"] = scenario_verdict

    return final_data


_ACTION_KEEP_KEYS = (
    "step",
    "action_type",
    "target_selector",
    "target_description",
    "value",
)


def _trim_actions_for_learned_path(
    steps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep only the fields a planner needs to replay a successful step.

    Screenshots, timing, raw ExecutionResult payloads, and free-form
    diagnostic text are dropped so the LearnedPath row stays small and
    rehydrates cleanly into a planner-ready shape.
    """
    trimmed: list[dict[str, Any]] = []
    for step in steps or []:
        if not isinstance(step, dict):
            continue
        kept = {k: step[k] for k in _ACTION_KEEP_KEYS if k in step}
        if kept:
            trimmed.append(kept)
    return trimmed


def _maybe_ingest_learned_path(
    db: Session,
    run: ExplorationRun,
    payload: AutonomousExplorePayload,
    final_data: dict[str, Any],
) -> str | None:
    """Persist a LearnedPath when the run cleared ``pass_gate=pass``.

    No-op for any other outcome (``fail`` / ``unverified`` / missing
    gate / missing page analysis). Failures here are logged and
    swallowed — LearnedPath ingest must never break the main run's
    response. Returns the learned_path id on success, None otherwise.
    """
    if _pass_gate_from_final_data(final_data) != "pass":
        return None

    page_analysis_dict = final_data.get("page_analysis") if isinstance(final_data, dict) else None
    if not isinstance(page_analysis_dict, dict):
        return None
    try:
        analysis = PageAnalysis.model_validate(page_analysis_dict)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("LearnedPath: failed to rehydrate PageAnalysis: %s", exc)
        return None

    # Prefer the URL the analyzer actually saw (post-navigation /
    # post-redirect) over the URL the operator asked for. Redirects,
    # canonical-slash fixes, login-gate bounces all make payload.url
    # unreliable as a page identity — page_analysis.url is what
    # produced the DOM fingerprint we're about to hash, so they must
    # come from the same source.
    url = analysis.url or payload.url or ""
    actions = _trim_actions_for_learned_path(final_data.get("steps") or [])
    if not actions:
        # Observational pass — the run cleared pass_gate without
        # needing an interactive step (e.g. "open page, content
        # confirms"). We still persist a LearnedPath with an empty
        # action list so future M11.1 path planner has the signal that
        # this (template, scenario) is reachable on a bare visit; we
        # just log so empty-action rows are easy to audit.
        logger.info(
            "Ingesting observational LearnedPath (no actions) for run %s",
            run.id,
        )

    path = LearnedPathRepository(db).ingest_run(
        page_template=path_template(url),
        query_signature=query_signature(url),
        dom_fingerprint=dom_fingerprint(analysis),
        scenario=payload.scenario or "",
        actions=actions,
        source_run_id=str(run.id),
    )[0]
    return str(path.id)


def _learned_path_for_run(db: Session, run: ExplorationRun) -> Any | None:
    """Resolve the LearnedPath a run contributed to.

    Fresh rows are linked by ``source_run_id``. Repeated successful runs
    hit the LearnedPath dedup key instead, so their ``source_run_id``
    remains the first run that created the path. For detail pages those
    repeated pass runs should still expose the existing LearnedPath so
    the operator can confirm or mark it wrong.
    """
    repo = LearnedPathRepository(db)
    linked = repo.find_by_source_run(str(run.id))
    if linked is not None:
        return linked

    final_data = run.result_snapshot_json
    if not isinstance(final_data, dict):
        return None
    if _pass_gate_from_final_data(final_data) != "pass":
        return None

    page_analysis_dict = final_data.get("page_analysis")
    if not isinstance(page_analysis_dict, dict):
        return None
    try:
        analysis = PageAnalysis.model_validate(page_analysis_dict)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("LearnedPath: failed to rehydrate PageAnalysis: %s", exc)
        return None

    strategy = run.strategy_json or {}
    url = analysis.url or strategy.get("url") or ""
    return repo.find_by_identity(
        page_template=path_template(url),
        query_signature=query_signature(url),
        dom_fingerprint=dom_fingerprint(analysis),
        scenario=strategy.get("scenario") or "",
    )


def _persist_autonomous_run(
    payload: AutonomousExplorePayload,
    final_data: dict[str, Any],
    verdict: str | None,
    status: ExplorationRunStatus,
    error: str | None = None,
) -> str | None:
    """Persist a finished autonomous run to the exploration_runs table.

    Opens its own SessionLocal because the streaming endpoint's worker
    runs in a background thread without a request-scoped DB session.
    Returns the new row's id or ``None`` if persistence itself failed
    (we never let persistence errors fail the user-facing run).
    """
    # Cache scenario_matched on the strategy_json so the list endpoint
    # doesn't have to deserialize the full result snapshot just to
    # render the correct status tag. Older rows fall back to reading
    # the nested path at query time (see list_autonomous_runs).
    scenario_matched: bool | None = None
    if isinstance(final_data, dict):
        vc = (
            ((final_data.get("verification") or {}).get("scorecard") or {})
            .get("verdict_check") or {}
        )
        if "matches_expectation" in vc:
            scenario_matched = bool(vc["matches_expectation"])

    try:
        db = SessionLocal()
        try:
            run = ExplorationRun(
                page_signature=(payload.url or "")[:512],
                mode=ExplorationMode.FORM,
                status=status,
                strategy_json={
                    "kind": "autonomous",
                    "url": payload.url,
                    "goal": payload.goal or "",
                    "spec_id": payload.spec_id,
                    "scenario": payload.scenario,
                    "language": payload.language,
                    "headless": payload.headless,
                    "fill_values": payload.fill_values or {},
                    "toggle_values": payload.toggle_values or {},
                    "verdict": verdict,
                    "scenario_matched": scenario_matched,
                    **({"error": error[:500]} if error else {}),
                },
                summary=(final_data.get("summary") if isinstance(final_data, dict) else None),
                result_snapshot_json=final_data if isinstance(final_data, dict) else None,
            )
            ExplorationRunRepository(db).create(run)
            logger.info(
                "Persisted autonomous run %s (spec=%s, scenario=%s, verdict=%s)",
                run.id, payload.spec_id, payload.scenario, verdict,
            )
            try:
                learned_path_id = _maybe_ingest_learned_path(
                    db, run, payload, final_data
                )
                if learned_path_id:
                    logger.info(
                        "Ingested LearnedPath %s from run %s",
                        learned_path_id,
                        run.id,
                    )
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(
                    "LearnedPath ingest failed (run=%s): %s", run.id, exc
                )
            return str(run.id)
        finally:
            db.close()
    except Exception as exc:  # pragma: no cover - defensive; never break the run
        logger.warning("Failed to persist autonomous run: %s", exc)
        return None


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
    toggle_values: dict[str, str] | None = Field(
        default=None,
        description="Native toggle (radio / checkbox) selections keyed by "
        "a group's semantic role (e.g. 'status') -> option value "
        "(e.g. 'active'). Drives the planner's toggle_values path.",
    )
    headless: bool = Field(default=True, description="Run browser in headless mode.")
    spec_id: str | None = Field(
        default=None,
        description="If set, load <spec_id>.assertions.json from the configured "
        "page spec root "
        "and run the comparator after exploration.",
    )
    scenario: str | None = Field(
        default=None,
        description="Scenario key within the spec (e.g. 'success' / 'failure'). "
        "Required when spec_id is set.",
    )
    language: str | None = Field(
        default=None,
        description="Preferred output language for the project-internal Supervisor "
        "Agent (e.g. 'en', 'zh', 'ja'). Defaults to the page title's language when unset.",
    )


@router.post("/autonomous-runs")
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

    # Look up scenario intent up front so the supervisor prompt can
    # include it. Spec lookup failures here degrade gracefully — the
    # run still executes, the supervisor just loses the intent hint.
    scenario_description: str | None = None
    if payload.spec_id and payload.scenario:
        try:
            from app.services.learning.page_verification import load_spec as _load

            _spec, _ = _load(payload.spec_id)
            _sc = _spec.scenarios.get(payload.scenario)
            if _sc is not None:
                scenario_description = _sc.description or None
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Scenario lookup failed (%s/%s): %s",
                           payload.spec_id, payload.scenario, exc)

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
            toggle_values=payload.toggle_values,
            scenario_name=payload.scenario,
            scenario_description=scenario_description,
            language=payload.language,
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
        except (SpecRootNotConfigured, UnsafeSpecId, SpecNotFound) as exc:
            raise _spec_http_exception(exc) from exc
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("Verification failed: %s", exc)
            verification_payload = {"error": str(exc)[:300]}

    # Serialize — convert screenshot paths to API URLs
    data = result.model_dump()
    if verification_payload is not None:
        data["verification"] = verification_payload
        _apply_scenario_relative_verdicts(data)

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

    # Persist the run so baselines can be tracked over time.
    run_id = _persist_autonomous_run(
        payload,
        data,
        verdict=data.get("verdict"),
        status=ExplorationRunStatus.COMPLETED,
    )
    if run_id:
        data["run_id"] = run_id

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


@router.post("/autonomous-runs/stream")
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
      - run_completed (final payload, same shape as POST /autonomous-runs)
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
                "toggle_values": payload.toggle_values,
                "spec_id": payload.spec_id,
                "scenario": payload.scenario,
                "headless": payload.headless,
            })

            # Scenario description for the supervisor prompt. Mirrors
            # the sync endpoint's lookup — degrades gracefully on miss.
            scenario_description: str | None = None
            if payload.spec_id and payload.scenario:
                try:
                    from app.services.learning.page_verification import (
                        load_spec as _load,
                    )

                    _spec, _ = _load(payload.spec_id)
                    _sc = _spec.scenarios.get(payload.scenario)
                    if _sc is not None:
                        scenario_description = _sc.description or None
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning("Scenario lookup failed (%s/%s): %s",
                                   payload.spec_id, payload.scenario, exc)

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
                    toggle_values=payload.toggle_values,
                    scenario_name=payload.scenario,
                    scenario_description=scenario_description,
                    language=payload.language,
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
                except (SpecRootNotConfigured, UnsafeSpecId, SpecNotFound) as exc:
                    http_exc = _spec_http_exception(exc)
                    emit(
                        "verification_done",
                        {
                            "error": str(http_exc.detail),
                            "status_code": http_exc.status_code,
                        },
                    )
                except KeyError as exc:
                    emit("verification_done", {"error": f"scenario not found: {exc}"})
                except Exception as exc:
                    logger.exception("Verification failed: %s", exc)
                    emit("verification_done", {"error": str(exc)[:300]})

            # Final payload — same shape as /autonomous-runs response.data
            final_data = result.model_dump()
            if verification_payload is not None:
                final_data["verification"] = verification_payload
                _apply_scenario_relative_verdicts(final_data)
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

            run_id = _persist_autonomous_run(
                payload,
                final_data,
                verdict=final_data.get("verdict") if isinstance(final_data, dict) else None,
                status=ExplorationRunStatus.COMPLETED,
            )
            if run_id:
                final_data["run_id"] = run_id
            emit("run_completed", final_data)

        except Exception as exc:
            logger.exception("Autonomous streaming run failed: %s", exc)
            err_text = str(exc)[:500]
            _persist_autonomous_run(
                payload,
                {},
                verdict=None,
                status=ExplorationRunStatus.FAILED,
                error=err_text,
            )
            emit("run_failed", {"error": err_text})
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
# Page verification specs — list + get
# ───────────────────────────────────────────────────────────────────


class SpecScenarioSummary(BaseModel):
    key: str
    description: str = ""
    inputs: dict[str, str] = Field(default_factory=dict)
    selections: dict[str, str] = Field(default_factory=dict)
    expected_verdict: str | None = None
    expected_verdict_not: str | None = None


class SpecSummary(BaseModel):
    spec_id: str
    page_id: str = ""
    url_pattern: str = ""
    description: str = ""
    scenarios: list[SpecScenarioSummary] = Field(default_factory=list)


@router.get("/specs", response_model=ApiResponse[list[SpecSummary]])
def list_specs() -> ApiResponse[list[SpecSummary]]:
    """List all authored page-verification specs.

    Scans the configured page spec root and returns each spec's scenarios for
    the workbench dropdowns.
    """
    from app.services.learning.page_verification import iter_spec_paths, load_spec

    items: list[SpecSummary] = []
    try:
        spec_paths = iter_spec_paths()
    except (SpecRootNotConfigured, UnsafeSpecId, SpecNotFound) as exc:
        raise _spec_http_exception(exc) from exc

    for path in spec_paths:
        spec_id = path.stem.removesuffix(".assertions")
        try:
            spec, _ = load_spec(spec_id)
        except (SpecRootNotConfigured, UnsafeSpecId, SpecNotFound) as exc:
            raise _spec_http_exception(exc) from exc
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to load spec %s: %s", spec_id, exc)
            continue
        items.append(
            SpecSummary(
                spec_id=spec_id,
                page_id=spec.page_id,
                url_pattern=spec.url_pattern,
                description=spec.description,
                scenarios=[
                    SpecScenarioSummary(
                        key=key,
                        description=sc.description,
                        inputs=sc.inputs,
                        selections=sc.selections,
                        expected_verdict=sc.expected_verdict,
                        expected_verdict_not=sc.expected_verdict_not,
                    )
                    for key, sc in spec.scenarios.items()
                ],
            )
        )
    return ApiResponse(data=items)


@router.get("/specs/{spec_id}", response_model=ApiResponse[SpecSummary])
def get_spec(spec_id: str) -> ApiResponse[SpecSummary]:
    """Return scenarios (with inputs) for a single spec.

    Used by the workbench to auto-prefill ``fill_values`` from
    ``scenarios[scenario].inputs`` when the user picks a scenario.
    """
    from app.services.learning.page_verification import load_spec

    try:
        spec, _ = load_spec(spec_id)
    except (SpecRootNotConfigured, UnsafeSpecId, SpecNotFound) as exc:
        raise _spec_http_exception(exc) from exc

    summary = SpecSummary(
        spec_id=spec_id,
        page_id=spec.page_id,
        url_pattern=spec.url_pattern,
        description=spec.description,
        scenarios=[
            SpecScenarioSummary(
                key=key,
                description=sc.description,
                inputs=sc.inputs,
                selections=sc.selections,
                expected_verdict=sc.expected_verdict,
                expected_verdict_not=sc.expected_verdict_not,
            )
            for key, sc in spec.scenarios.items()
        ],
    )
    return ApiResponse(data=summary)


# ───────────────────────────────────────────────────────────────────
# Autonomous run history
# ───────────────────────────────────────────────────────────────────


class AutonomousRunSummary(BaseModel):
    """Compact view of a persisted autonomous run for list pages."""

    run_id: str
    created_at: str
    spec_id: str | None = None
    scenario: str | None = None
    verdict: str | None = None
    scenario_matched: bool | None = None
    # Strict pass gate outcome ('pass' / 'fail' / 'unverified') — the
    # UI reads this as the authoritative status. Null for pre-gate
    # rows; the list row then falls back to scenario_matched + verdict.
    pass_gate_status: str | None = None
    operator_review_status: str | None = None
    status: str
    url: str | None = None
    summary: str | None = None


class AutonomousRunDeleteResult(BaseModel):
    run_id: str
    deleted: bool
    deleted_learned_path_ids: list[str] = Field(default_factory=list)


class LearnedPathDeleteResult(BaseModel):
    path_id: str
    deleted: bool


class RunReviewPatchRequest(BaseModel):
    status: Literal["accepted", "rejected", "unreviewed"]
    note: str | None = Field(default=None, max_length=500)


class RunLearnedPathProjection(BaseModel):
    id: str
    trust: str
    source_run_id: str | None = None
    hit_count: int
    relation: Literal["source", "dedup_hit", "none"]


# Rebuild models that use Literal under ``from __future__ import annotations``
# so FastAPI's TypeAdapter can resolve them at import time.
RunReviewPatchRequest.model_rebuild()
RunLearnedPathProjection.model_rebuild()


@router.get(
    "/autonomous-runs",
    response_model=ApiResponse[CursorPage[AutonomousRunSummary]],
)
def list_autonomous_runs(
    db: DbSession,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    spec_id: str | None = Query(None),
    scenario: str | None = Query(None),
) -> ApiResponse[CursorPage[AutonomousRunSummary]]:
    """List persisted autonomous runs, newest first.

    The table is shared with candidate-inference ``ExplorationRun`` rows;
    we distinguish autonomous ones by ``strategy_json.kind == 'autonomous'``
    and allow optional filtering by spec_id / scenario so a spec's
    baseline drift over time can be tracked.
    """
    cursor_created_at = cursor_id = None
    if cursor:
        cursor_created_at, cursor_id = decode_cursor(cursor)

    repo = ExplorationRunRepository(db)
    # We fetch a generous window and filter in Python — the
    # strategy_json columns are JSON and this avoids dialect-specific
    # JSON query paths for the current row volume. Revisit once the
    # table grows past a few thousand rows.
    items, _has_next = repo.list_page(
        limit=limit * 5,
        cursor_created_at=cursor_created_at,
        cursor_id=cursor_id,
    )

    filtered: list[ExplorationRun] = []
    for item in items:
        strategy = item.strategy_json or {}
        if strategy.get("kind") != "autonomous":
            continue
        if spec_id and strategy.get("spec_id") != spec_id:
            continue
        if scenario and strategy.get("scenario") != scenario:
            continue
        filtered.append(item)
        if len(filtered) > limit:
            break

    has_next = len(filtered) > limit
    if has_next:
        filtered = filtered[:limit]

    summaries = [
        AutonomousRunSummary(
            run_id=str(item.id),
            created_at=item.created_at.isoformat(),
            spec_id=(item.strategy_json or {}).get("spec_id"),
            scenario=(item.strategy_json or {}).get("scenario"),
            verdict=(item.strategy_json or {}).get("verdict"),
            scenario_matched=_scenario_matched_for(item),
            pass_gate_status=_pass_gate_status_for(item),
            operator_review_status=str(item.operator_review_status),
            status=str(item.status),
            url=(item.strategy_json or {}).get("url"),
            summary=item.summary,
        )
        for item in filtered
    ]

    next_cursor = (
        encode_cursor(filtered[-1].created_at, filtered[-1].id)
        if has_next and filtered
        else None
    )
    return ApiResponse(
        data=CursorPage(items=summaries, has_next=has_next, next_cursor=next_cursor)
    )


def _learned_path_relation_for_run(
    db: Session,
    run: ExplorationRun,
) -> tuple[Any | None, Literal["source", "dedup_hit", "none"]]:
    """Resolve the LearnedPath associated with a run and the relation type."""
    repo = LearnedPathRepository(db)
    linked = repo.find_by_source_run(str(run.id))
    if linked is not None:
        return linked, "source"

    final_data = run.result_snapshot_json
    if not isinstance(final_data, dict):
        return None, "none"
    if _pass_gate_from_final_data(final_data) != "pass":
        return None, "none"

    page_analysis_dict = final_data.get("page_analysis")
    if not isinstance(page_analysis_dict, dict):
        return None, "none"
    try:
        analysis = PageAnalysis.model_validate(page_analysis_dict)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("LearnedPath: failed to rehydrate PageAnalysis: %s", exc)
        return None, "none"

    strategy = run.strategy_json or {}
    url = analysis.url or strategy.get("url") or ""
    matched = repo.find_by_identity(
        page_template=path_template(url),
        query_signature=query_signature(url),
        dom_fingerprint=dom_fingerprint(analysis),
        scenario=strategy.get("scenario") or "",
    )
    if matched is not None:
        return matched, "dedup_hit"
    return None, "none"


@router.get(
    "/autonomous-runs/{run_id}",
    response_model=ApiResponse[dict[str, Any]],
)
def get_autonomous_run(
    db: DbSession,
    run_id: str,
) -> ApiResponse[dict[str, Any]]:
    """Return one persisted autonomous run with its full result snapshot."""
    repo = ExplorationRunRepository(db)
    run = repo.get(run_id)
    if run is None or (run.strategy_json or {}).get("kind") != "autonomous":
        raise HTTPException(status_code=404, detail=f"Autonomous run not found: {run_id}")
    learned, relation = _learned_path_relation_for_run(db, run)
    learned_path_projection = None
    if learned is not None:
        learned_path_projection = RunLearnedPathProjection(
            id=str(learned.id),
            trust=str(learned.trust),
            source_run_id=learned.source_run_id,
            hit_count=learned.hit_count,
            relation=relation,
        )
    return ApiResponse(
        data={
            "run_id": str(run.id),
            "created_at": run.created_at.isoformat(),
            "updated_at": run.updated_at.isoformat(),
            "status": str(run.status),
            "strategy": run.strategy_json,
            "summary": run.summary,
            "result": run.result_snapshot_json,
            "pass_gate_status": _pass_gate_status_for(run),
            "operator_review_status": str(run.operator_review_status),
            "operator_review_note": run.operator_review_note,
            "operator_reviewed_at": (
                run.operator_reviewed_at.isoformat() if run.operator_reviewed_at else None
            ),
            "learned_path_id": str(learned.id) if learned else None,
            "learned_path_trust": str(learned.trust) if learned else None,
            "learned_path": (
                learned_path_projection.model_dump() if learned_path_projection else None
            ),
        }
    )


@router.patch(
    "/autonomous-runs/{run_id}/review",
    response_model=ApiResponse[dict[str, Any]],
)
def patch_autonomous_run_review(
    db: DbSession,
    run_id: str,
    body: RunReviewPatchRequest,
) -> ApiResponse[dict[str, Any]]:
    """Update the operator review status of a single autonomous run.

    Does not modify any associated LearnedPath.
    """
    repo = ExplorationRunRepository(db)
    run = repo.get(run_id)
    if run is None or (run.strategy_json or {}).get("kind") != "autonomous":
        raise HTTPException(status_code=404, detail=f"Autonomous run not found: {run_id}")

    try:
        run.operator_review_status = OperatorReviewStatus(body.status)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    run.operator_review_note = body.note
    if run.operator_review_status == OperatorReviewStatus.UNREVIEWED:
        run.operator_reviewed_at = None
    else:
        run.operator_reviewed_at = datetime.now(UTC)
    db.commit()
    db.refresh(run)

    learned, relation = _learned_path_relation_for_run(db, run)
    learned_path_projection = None
    if learned is not None:
        learned_path_projection = RunLearnedPathProjection(
            id=str(learned.id),
            trust=str(learned.trust),
            source_run_id=learned.source_run_id,
            hit_count=learned.hit_count,
            relation=relation,
        )

    return ApiResponse(
        data={
            "run_id": str(run.id),
            "operator_review_status": str(run.operator_review_status),
            "operator_review_note": run.operator_review_note,
            "operator_reviewed_at": (
                run.operator_reviewed_at.isoformat() if run.operator_reviewed_at else None
            ),
            "learned_path": (
                learned_path_projection.model_dump() if learned_path_projection else None
            ),
        }
    )


@router.delete(
    "/autonomous-runs/{run_id}",
    response_model=ApiResponse[AutonomousRunDeleteResult],
)
def delete_autonomous_run(
    db: DbSession,
    run_id: str,
) -> ApiResponse[AutonomousRunDeleteResult]:
    """Delete one autonomous run.

    Does NOT delete associated LearnedPaths — those may be shared by
    multiple runs via dedup and must be managed through the LearnedPath
    surface instead.
    """
    repo = ExplorationRunRepository(db)
    run = repo.get(run_id)
    if run is None or (run.strategy_json or {}).get("kind") != "autonomous":
        raise HTTPException(status_code=404, detail=f"Autonomous run not found: {run_id}")

    db.delete(run)
    db.commit()

    return ApiResponse(
        data=AutonomousRunDeleteResult(
            run_id=run_id,
            deleted=True,
            deleted_learned_path_ids=[],
        )
    )


# ───────────────────────────────────────────────────────────────────
# LearnedPath — list / get / trust PATCH
# ───────────────────────────────────────────────────────────────────


def _learned_path_to_summary(row: Any) -> LearnedPathSummary:
    return LearnedPathSummary(
        id=str(row.id),
        page_template=row.page_template,
        query_signature=dict(row.query_signature or {}),
        dom_fingerprint=row.dom_fingerprint,
        scenario=row.scenario or "",
        provenance=str(row.provenance),
        trust=str(row.trust),
        trust_reason=row.trust_reason,
        trust_updated_at=row.trust_updated_at,
        hit_count=row.hit_count,
        source_run_id=row.source_run_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _learned_path_to_detail(row: Any) -> LearnedPathDetail:
    summary = _learned_path_to_summary(row)
    return LearnedPathDetail(
        **summary.model_dump(),
        actions=list(row.actions or []),
    )


@router.get(
    "/learned-paths",
    response_model=ApiResponse[CursorPage[LearnedPathSummary]],
)
def list_learned_paths(
    db: DbSession,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None),
    page_template: str | None = Query(None),
    scenario: str | None = Query(None),
    trust: str | None = Query(None),
) -> ApiResponse[CursorPage[LearnedPathSummary]]:
    """List LearnedPath rows, newest first, with optional filters."""
    trust_filter: TrustStatus | None = None
    if trust is not None:
        try:
            trust_filter = TrustStatus(trust)
        except ValueError as exc:
            raise HTTPException(
                status_code=422, detail=f"invalid trust: {trust}"
            ) from exc

    rows, has_next, next_cursor = LearnedPathRepository(db).list_page(
        page_template=page_template,
        scenario=scenario,
        trust=trust_filter,
        cursor=cursor,
        limit=limit,
    )
    summaries = [_learned_path_to_summary(row) for row in rows]
    return ApiResponse(
        data=CursorPage(items=summaries, has_next=has_next, next_cursor=next_cursor)
    )


@router.get(
    "/learned-paths/{path_id}",
    response_model=ApiResponse[LearnedPathDetail],
)
def get_learned_path(
    db: DbSession,
    path_id: str,
) -> ApiResponse[LearnedPathDetail]:
    row = LearnedPathRepository(db).get(path_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"learned_path not found: {path_id}"
        )
    return ApiResponse(data=_learned_path_to_detail(row))


@router.delete(
    "/learned-paths/{path_id}",
    response_model=ApiResponse[LearnedPathDeleteResult],
)
def delete_learned_path(
    db: DbSession,
    path_id: str,
) -> ApiResponse[LearnedPathDeleteResult]:
    deleted = LearnedPathRepository(db).delete(path_id)
    if not deleted:
        raise HTTPException(
            status_code=404, detail=f"learned_path not found: {path_id}"
        )
    return ApiResponse(data=LearnedPathDeleteResult(path_id=path_id, deleted=True))


@router.patch(
    "/learned-paths/{path_id}/trust",
    response_model=ApiResponse[LearnedPathDetail],
)
def patch_learned_path_trust(
    db: DbSession,
    path_id: str,
    body: TrustPatchRequest,
) -> ApiResponse[LearnedPathDetail]:
    repo = LearnedPathRepository(db)
    if repo.get(path_id) is None:
        raise HTTPException(
            status_code=404, detail=f"learned_path not found: {path_id}"
        )
    try:
        updated = repo.set_trust(path_id, TrustStatus(body.status), body.reason)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ApiResponse(data=_learned_path_to_detail(updated))


@router.post(
    "/learned-paths/{path_id}/replay",
    response_model=ApiResponse[ReplayResult],
)
def replay_learned_path(
    db: DbSession,
    path_id: str,
    body: ReplayRequest,
) -> ApiResponse[ReplayResult]:
    """Replay a stored LearnedPath against a live URL."""
    from app.models.learned_path import TrustStatus
    from app.services.learning.learned_path_replay import run_replay

    row = LearnedPathRepository(db).get(path_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"learned_path not found: {path_id}"
        )

    if row.trust == TrustStatus.DEPRECATED:
        raise HTTPException(
            status_code=422, detail="learned_path is deprecated"
        )

    if not body.url:
        raise HTTPException(status_code=422, detail="url is required")

    result = run_replay(
        row,
        body.url,
        slot_overrides=body.slot_overrides,
        evidence_targets=body.evidence_targets,
    )

    # Flaky paths are allowed but must carry a trust warning
    if row.trust == TrustStatus.FLAKY:
        result.warnings.insert(0, "Path trust is flaky")

    return ApiResponse(data=result)


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
