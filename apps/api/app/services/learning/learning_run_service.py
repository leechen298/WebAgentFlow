"""Synchronous learning run service for M11.3 interactive chat.

Runs the existing autonomous exploration pipeline and returns both the
persisted run id and the LearnedPath id that was actually written.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.models.exploration_run import (
    ExplorationMode,
    ExplorationRun,
    ExplorationRunStatus,
)
from app.repos.exploration_run_repo import ExplorationRunRepository
from app.repos.learned_paths_repo import LearnedPathRepository
from app.schemas.page_analysis import AutonomousExplorationResult, PageAnalysis
from app.services.learning.page_signature import (
    dom_fingerprint,
    path_template,
    query_signature,
)

logger = logging.getLogger(__name__)

_SCREENSHOT_DIR = Path(__file__).resolve().parents[5] / "data" / "screenshots"
_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

LearningStatus = Literal["learned", "failed"]


@dataclass(frozen=True)
class LearningRunRequest:
    url: str
    spec_id: str | None = None
    scenario: str | None = None
    goal: str = ""
    fill_values: dict[str, str] | None = None
    toggle_values: dict[str, str] | None = None
    headless: bool = True
    language: str | None = None
    product_level: bool = False


@dataclass(frozen=True)
class LearningRunResult:
    status: LearningStatus
    run_id: str | None = None
    learned_path_id: str | None = None
    target_url: str = ""
    page_template: str | None = None
    scenario: str | None = None
    action_label: str = ""
    suggested_utterances: list[str] = field(default_factory=list)
    error: str | None = None


class LearningRunService:
    """Run autonomous learning and expose the persisted LearnedPath id."""

    def __init__(
        self,
        db_session: Session,
        *,
        runtime_factory: Callable[..., Any] | None = None,
        explorer: Callable[..., AutonomousExplorationResult] | None = None,
        spec_loader: Callable[[str], tuple[Any, Any]] | None = None,
        verifier: Callable[[AutonomousExplorationResult, Any, str], Any] | None = None,
    ) -> None:
        self._db = db_session
        self._runtime_factory = runtime_factory
        self._explorer = explorer
        self._spec_loader = spec_loader
        self._verifier = verifier

    def run(self, request: LearningRunRequest) -> LearningRunResult:
        """Run a learning request and return run + LearnedPath ids."""
        try:
            result, final_data = self._run_pipeline(request)
            verdict = final_data.get("verdict")
            run_id, learned_path_id = self._persist_finished_run(
                request=request,
                final_data=final_data,
                verdict=verdict,
                status=ExplorationRunStatus.COMPLETED,
            )
            if learned_path_id is None:
                return LearningRunResult(
                    status="failed",
                    run_id=run_id,
                    learned_path_id=None,
                    target_url=request.url,
                    page_template=path_template(result.page_analysis.url or request.url),
                    scenario=request.scenario,
                    action_label=_action_label_for(request),
                    suggested_utterances=_utterances_for(request),
                    error="Learning run did not produce a LearnedPath.",
                )
            return LearningRunResult(
                status="learned",
                run_id=run_id,
                learned_path_id=learned_path_id,
                target_url=request.url,
                page_template=path_template(result.page_analysis.url or request.url),
                scenario=request.scenario,
                action_label=_action_label_for(request),
                suggested_utterances=_utterances_for(request),
            )
        except Exception as exc:
            logger.exception("Learning run failed: %s", exc)
            return LearningRunResult(
                status="failed",
                target_url=request.url,
                scenario=request.scenario,
                action_label=_action_label_for(request),
                suggested_utterances=_utterances_for(request),
                error=str(exc),
            )

    def _run_pipeline(
        self, request: LearningRunRequest
    ) -> tuple[AutonomousExplorationResult, dict[str, Any]]:
        from app.services.execution.execution_runtime import RuntimeConfig

        runtime_factory = self._get_runtime_factory()
        explorer = self._get_explorer()
        runtime_config = RuntimeConfig(
            headless=request.headless,
            screenshot_dir=str(_SCREENSHOT_DIR),
        )

        if request.spec_id and request.scenario:
            # validation-backed learning
            spec, _spec_path = self._load_spec(request.spec_id)
            scenario = spec.scenarios.get(request.scenario)
            if scenario is None:
                raise ValueError(f"scenario not found: {request.scenario}")

            fill_values = request.fill_values or dict(scenario.inputs or {})
            scenario_description = scenario.description or None

            with runtime_factory(config=runtime_config) as runtime:
                result = explorer(
                    url=request.url,
                    runtime=runtime,
                    goal=request.goal,
                    fill_values=fill_values,
                    toggle_values=request.toggle_values,
                    scenario_name=request.scenario,
                    scenario_description=scenario_description,
                    language=request.language,
                )

            scorecard = self._verify(result, spec, request.scenario)
            final_data = result.model_dump()
            final_data["verification"] = {
                "spec_source": str(_spec_path),
                "spec_id": spec.page_id,
                "scenario": request.scenario,
                "scorecard": scorecard.model_dump(),
            }
            _apply_scenario_relative_verdicts(final_data)
            return result, final_data

        # product-level learning (no spec / scenario)
        fill_values = request.fill_values or {}
        with runtime_factory(config=runtime_config) as runtime:
            result = explorer(
                url=request.url,
                runtime=runtime,
                goal=request.goal,
                fill_values=fill_values,
                toggle_values=request.toggle_values,
                language=request.language,
            )

        final_data = result.model_dump()
        final_data["verification"] = None
        return result, final_data

    def _persist_finished_run(
        self,
        *,
        request: LearningRunRequest,
        final_data: dict[str, Any],
        verdict: str | None,
        status: ExplorationRunStatus,
    ) -> tuple[str | None, str | None]:
        scenario_matched = _scenario_matched_from(final_data)
        run = ExplorationRun(
            page_signature=(request.url or "")[:512],
            mode=ExplorationMode.FORM,
            status=status,
            strategy_json={
                "kind": "autonomous",
                "url": request.url,
                "goal": request.goal or "",
                "spec_id": request.spec_id,
                "scenario": request.scenario,
                "language": request.language,
                "headless": request.headless,
                "fill_values": request.fill_values or {},
                "toggle_values": request.toggle_values or {},
                "verdict": verdict,
                "scenario_matched": scenario_matched,
                "product_level": request.product_level,
            },
            summary=final_data.get("summary"),
            result_snapshot_json=final_data,
        )
        ExplorationRunRepository(self._db).create(run)
        learned_path_id = self._maybe_ingest_learned_path(run, request, final_data)
        return str(run.id), learned_path_id

    def _maybe_ingest_learned_path(
        self,
        run: ExplorationRun,
        request: LearningRunRequest,
        final_data: dict[str, Any],
    ) -> str | None:
        if request.product_level:
            # product-level: no spec oracle; accept if explorer reports success
            # or the LLM supervisor explicitly says this path should be saved.
            # Static-page flows can mutate DOM state without a URL/title change,
            # so the rule-side success flag is too narrow.
            if not _product_learning_should_save_path(final_data):
                return None
        else:
            if _pass_gate_from_final_data(final_data) != "pass":
                return None
        page_analysis_dict = final_data.get("page_analysis")
        if not isinstance(page_analysis_dict, dict):
            return None
        analysis = PageAnalysis.model_validate(page_analysis_dict)
        url = analysis.url or request.url
        actions = _trim_actions_for_learned_path(final_data.get("steps") or [])
        fill_values = request.fill_values or {}
        actions, _parameterization_report = parameterize_learned_path_actions(
            actions,
            fill_values,
        )
        repo = LearnedPathRepository(self._db)
        path, created = repo.ingest_run(
            page_template=path_template(url),
            query_signature=query_signature(url),
            dom_fingerprint=dom_fingerprint(analysis),
            scenario=request.scenario or "product_level",
            actions=actions,
            source_run_id=str(run.id),
        )
        if not created:
            merged_actions, changed = _merge_parameterized_action_metadata(
                path.actions or [],
                actions,
            )
            if changed:
                path.actions = merged_actions
                self._db.commit()
                self._db.refresh(path)
        return str(path.id)

    def _load_spec(self, spec_id: str) -> tuple[Any, Any]:
        if self._spec_loader is not None:
            return self._spec_loader(spec_id)
        from app.services.learning.page_verification import load_spec

        return load_spec(spec_id)

    def _verify(
        self,
        result: AutonomousExplorationResult,
        spec: Any,
        scenario: str,
    ) -> Any:
        if self._verifier is not None:
            return self._verifier(result, spec, scenario)
        from app.services.learning.page_verification import verify_against_spec

        return verify_against_spec(result, spec, scenario)

    def _get_runtime_factory(self) -> Callable[..., Any]:
        if self._runtime_factory is not None:
            return self._runtime_factory
        from app.services.execution.execution_runtime import create_execution_runtime

        return create_execution_runtime

    def _get_explorer(self) -> Callable[..., AutonomousExplorationResult]:
        if self._explorer is not None:
            return self._explorer
        from app.services.learning.autonomous_explorer import (
            run_autonomous_exploration,
        )

        return run_autonomous_exploration


def _trim_actions_for_learned_path(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keep_keys = (
        "step",
        "action_type",
        "target_selector",
        "target_description",
        "value",
        "value_slot",
    )
    trimmed: list[dict[str, Any]] = []
    for step in steps:
        kept = {key: step[key] for key in keep_keys if key in step}
        if kept:
            trimmed.append(kept)
    return trimmed


def parameterize_learned_path_actions(
    actions: list[dict[str, Any]],
    fill_values: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    slot_values = {
        str(key): str(value)
        for key, value in fill_values.items()
        if key and value is not None and str(value)
    }
    if not slot_values:
        return actions, {"status": "skipped", "slots": [], "warnings": []}

    bound_count = 0
    warnings: list[str] = []
    parameterized: list[dict[str, Any]] = []
    for action in actions:
        updated = dict(action)
        if str(updated.get("action_type") or "").lower() == "fill":
            matching_slot = next(
                (
                    slot_name
                    for slot_name, value in slot_values.items()
                    if updated.get("value") == value
                ),
                None,
            )
            if matching_slot is not None and updated.get("value_slot") not in (
                None,
                matching_slot,
            ):
                warnings.append(
                    f"fill action at step {updated.get('step')} already has value_slot"
                )
            elif matching_slot is not None:
                if updated.get("value_slot") != matching_slot:
                    updated["value_slot"] = matching_slot
                bound_count += 1
        parameterized.append(updated)

    if bound_count == 0:
        return parameterized, {
            "status": "not_bound",
            "slots": [],
            "warnings": warnings,
            "reason": "No fill action matched learning fill values",
        }
    if bound_count > 1:
        warnings.append("multiple fill actions matched learning fill values")
    return parameterized, {
        "status": "bound",
        "slots": list(slot_values),
        "warnings": warnings,
    }


def _merge_parameterized_action_metadata(
    existing_actions: list[dict[str, Any]],
    incoming_actions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], bool]:
    merged = [dict(action) for action in existing_actions]
    changed = False
    for incoming in incoming_actions:
        value_slot = incoming.get("value_slot")
        if not value_slot:
            continue
        for existing in merged:
            if (
                str(existing.get("action_type") or "").lower()
                == str(incoming.get("action_type") or "").lower()
                and existing.get("target_selector") == incoming.get("target_selector")
                and existing.get("value") == incoming.get("value")
                and not existing.get("value_slot")
            ):
                existing["value_slot"] = value_slot
                changed = True
                break
    return merged, changed


def _pass_gate_from_final_data(final_data: dict[str, Any]) -> str | None:
    scorecard = (final_data.get("verification") or {}).get("scorecard") or {}
    gate = scorecard.get("pass_gate") or {}
    return gate.get("status")


def _product_learning_should_save_path(final_data: dict[str, Any]) -> bool:
    if final_data.get("success"):
        return True

    supervisor = final_data.get("supervisor")
    if not isinstance(supervisor, dict):
        return False
    return (
        supervisor.get("should_save_path") is True
        and supervisor.get("verdict") == "success"
        and supervisor.get("_supervisor_source") == "llm"
        and not supervisor.get("_supervisor_partial_parse", False)
    )


def _scenario_matched_from(final_data: dict[str, Any]) -> bool | None:
    vc = (
        ((final_data.get("verification") or {}).get("scorecard") or {})
        .get("verdict_check") or {}
    )
    if "matches_expectation" in vc:
        return bool(vc["matches_expectation"])
    return None


def _scenario_verdict_from_pass_gate(status: str | None) -> str | None:
    if status == "pass":
        return "success"
    if status == "fail":
        return "failure"
    if status == "unverified":
        return "uncertain"
    return None


def _apply_scenario_relative_verdicts(final_data: dict[str, Any]) -> None:
    scenario_verdict = _scenario_verdict_from_pass_gate(
        _pass_gate_from_final_data(final_data)
    )
    if scenario_verdict is None:
        return
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


def _action_label_for(request: LearningRunRequest) -> str:
    if request.spec_id == "login":
        return "登录"
    if request.product_level:
        return _product_action_label_for(request)
    return request.scenario or "执行操作"


def _utterances_for(request: LearningRunRequest) -> list[str]:
    if request.spec_id == "login":
        return ["帮我登录", "登录一下"]
    label = _action_label_for(request)
    return [f"帮我{label}", f"{label}一下"]


def _product_action_label_for(request: LearningRunRequest) -> str:
    if path_template(request.url).rstrip("/") == "/workspace-login":
        return "进入工作台"

    goal = _strip_product_learning_noise(request.goal or "")
    if "进入工作台" in goal:
        return "进入工作台"
    if "登录" in goal and "工作台" in goal:
        return "进入工作台"
    if "登录" in goal:
        return "登录"

    for prefix in ("帮我", "请帮我", "你帮我", "我要", "我想"):
        if goal.startswith(prefix):
            goal = goal[len(prefix):].strip(" ，,。.!！?？")
            break
    return (goal or "执行操作").strip(" ，,。.!！?？")[:20]


def _strip_product_learning_noise(text: str) -> str:
    cleaned = re.sub(r"https?://[^\s，。]+", "", text)
    cleaned = re.sub(r"操作员账号[是为]?\s*[:：]?[^\s，。,.；;!！?？]+", "", cleaned)
    cleaned = re.sub(r"访问口令[是为]?\s*[:：]?[^\s，。,.；;!！?？]+", "", cleaned)
    for phrase in ("学习一下", "学一下", "学习", "这个", "页面", "地址是"):
        cleaned = cleaned.replace(phrase, "")
    return cleaned.strip()
