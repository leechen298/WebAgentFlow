"""Synchronous learning run service for M11.3 interactive chat.

Runs the existing autonomous exploration pipeline and returns both the
persisted run id and the LearnedPath id that was actually written.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.models.exploration_run import (
    ExplorationMode,
    ExplorationRun,
    ExplorationRunStatus,
)
from app.repos.exploration_run_repo import ExplorationRunRepository
from app.repos.learned_capabilities_repo import LearnedCapabilityRepository
from app.repos.learned_paths_repo import LearnedPathRepository
from app.repos.learning_batches_repo import LearningBatchRepository
from app.schemas.learning_batch import BoundedLearningPolicy
from app.schemas.page_analysis import AutonomousExplorationResult, PageAnalysis
from app.services.learning.attempt_evaluation import evaluate_attempt_ingest
from app.services.learning.bounded_learning import (
    BoundedAttemptState,
    apply_policy_to_scenarios,
    default_bounded_learning_policy,
    should_stop_after_attempt,
)
from app.services.learning.capability_discovery import (
    CapabilityScenario,
    build_filter_inventory,
    generate_filter_scenarios,
)
from app.services.learning.learning_batch_controller import (
    CancelChecker,
    Clock,
    LearningBatchController,
)
from app.services.learning.page_signature import (
    dom_fingerprint,
    path_template,
    query_signature,
)

logger = logging.getLogger(__name__)

_SCREENSHOT_DIR = Path(__file__).resolve().parents[5] / "data" / "screenshots"
_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

LearningStatus = Literal["learned", "failed"]
LearningOutcome = Literal["success", "partial_success", "failed", "unverified"]


@dataclass(frozen=True)
class LearningRunRequest:
    url: str
    session_id: str | None = None
    spec_id: str | None = None
    scenario: str | None = None
    goal: str = ""
    fill_values: dict[str, str] | None = None
    toggle_values: dict[str, str] | None = None
    headless: bool = True
    language: str | None = None
    product_level: bool = False
    action_goal: str | None = None
    canonical_goal: str | None = None
    action_aliases: list[str] = field(default_factory=list)
    bounded_policy: BoundedLearningPolicy | None = None


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
    business_goal: str = ""
    canonical_goal: str | None = None
    action_aliases: list[str] = field(default_factory=list)
    business_object: str | None = None
    match_terms: list[str] = field(default_factory=list)
    error: str | None = None
    learning_outcome: LearningOutcome | None = None
    discovery_batch_id: str | None = None
    run_ids: list[str] = field(default_factory=list)
    learned_path_ids: list[str] = field(default_factory=list)
    capability_summaries: list[dict[str, Any]] = field(default_factory=list)
    failed_scenario_summaries: list[dict[str, Any]] = field(default_factory=list)
    unverified_scenario_summaries: list[dict[str, Any]] = field(default_factory=list)
    unsupported_capability_summaries: list[dict[str, Any]] = field(default_factory=list)
    evidence_warnings: list[str] = field(default_factory=list)
    learning_batch_id: str | None = None
    learning_batch_status: str | None = None
    learning_batch_summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class _ScenarioResetResult:
    ok: bool
    mode: str = "navigate_only"
    url: str | None = None
    title: str | None = None
    baseline_summary: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class LearningRunService:
    """Run autonomous learning and expose the persisted LearnedPath id."""

    def __init__(
        self,
        db_session: Session,
        *,
        runtime_factory: Callable[..., Any] | None = None,
        explorer: Callable[..., AutonomousExplorationResult] | None = None,
        page_analyzer: Callable[[Any], PageAnalysis] | None = None,
        spec_loader: Callable[[str], tuple[Any, Any]] | None = None,
        verifier: Callable[[AutonomousExplorationResult, Any, str], Any] | None = None,
        clock: Clock | None = None,
        cancel_checker: CancelChecker | None = None,
    ) -> None:
        self._db = db_session
        self._runtime_factory = runtime_factory
        self._explorer = explorer
        self._page_analyzer = page_analyzer
        self._spec_loader = spec_loader
        self._verifier = verifier
        self._clock = clock
        self._cancel_checker = cancel_checker

    def run(self, request: LearningRunRequest) -> LearningRunResult:
        """Run a learning request and return run + LearnedPath ids."""
        try:
            if _should_run_capability_discovery(request):
                return self._run_capability_discovery(request)
            result, final_data = self._run_pipeline(request)
            verdict = final_data.get("verdict")
            run_id, learned_path_id = self._persist_finished_run(
                request=request,
                final_data=final_data,
                verdict=verdict,
                status=ExplorationRunStatus.COMPLETED,
            )
            if learned_path_id is None:
                identity = _action_identity_for(request)
                return LearningRunResult(
                    status="failed",
                    run_id=run_id,
                    learned_path_id=None,
                    target_url=request.url,
                    page_template=path_template(result.page_analysis.url or request.url),
                    scenario=request.scenario,
                    action_label=_action_label_for(request),
                    suggested_utterances=_utterances_for(request),
                    business_goal=identity["business_goal"],
                    canonical_goal=identity["canonical_goal"],
                    action_aliases=identity["action_aliases"],
                    business_object=identity["business_object"],
                    match_terms=identity["match_terms"],
                    error="Learning run did not produce a LearnedPath.",
                )
            identity = _action_identity_for(request)
            return LearningRunResult(
                status="learned",
                run_id=run_id,
                learned_path_id=learned_path_id,
                target_url=request.url,
                page_template=path_template(result.page_analysis.url or request.url),
                scenario=request.scenario,
                action_label=_action_label_for(request),
                suggested_utterances=_utterances_for(request),
                business_goal=identity["business_goal"],
                canonical_goal=identity["canonical_goal"],
                action_aliases=identity["action_aliases"],
                business_object=identity["business_object"],
                match_terms=identity["match_terms"],
            )
        except Exception as exc:
            logger.exception("Learning run failed: %s", exc)
            identity = _action_identity_for(request)
            return LearningRunResult(
                status="failed",
                target_url=request.url,
                scenario=request.scenario,
                action_label=_action_label_for(request),
                suggested_utterances=_utterances_for(request),
                business_goal=identity["business_goal"],
                canonical_goal=identity["canonical_goal"],
                action_aliases=identity["action_aliases"],
                business_object=identity["business_object"],
                match_terms=identity["match_terms"],
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

    def _run_capability_discovery(self, request: LearningRunRequest) -> LearningRunResult:
        from app.services.execution.execution_runtime import RuntimeConfig

        runtime_factory = self._get_runtime_factory()
        explorer = self._get_explorer()
        page_analyzer = self._get_page_analyzer()
        policy = request.bounded_policy or default_bounded_learning_policy()
        batch_controller = self._get_batch_controller()
        batch = batch_controller.create_pending(
            target_url=request.url,
            session_id=request.session_id,
            policy=policy,
            request_json=_learning_batch_request_payload(request),
        )
        batch_state = BoundedAttemptState()
        batch_started = batch_controller.now()
        runtime_config = RuntimeConfig(
            headless=request.headless,
            screenshot_dir=str(_SCREENSHOT_DIR),
        )
        planned_count = 0
        attempted_count = 0
        run_ids: list[str] = []
        learned_path_ids: list[str] = []
        persisted_learned_path_ids: list[str] = []
        failed_scenarios: list[dict[str, Any]] = []
        unverified_scenarios: list[dict[str, Any]] = []
        passed_capabilities: list[dict[str, Any]] = []
        learned_capability_ids: list[str] = []
        evidence_warnings: list[str] = []
        terminal_reason: str | None = None
        scenario_reset_count = 0
        scenario_reset_warnings: list[str] = []
        reset_unverified_count = 0
        browser_session_started = False

        boundary = batch_controller.boundary_state(
            batch.id,
            started_monotonic=batch_started,
            policy=policy,
            state=batch_state,
        )
        if boundary.should_stop:
            closed = batch_controller.close(
                batch.id,
                state=batch_state,
                policy=policy,
                planned_count=0,
                attempted_count=0,
                terminal_reason=boundary.reason,
            )
            return _batch_result_without_scenarios(request, closed)

        try:
            with runtime_factory(config=runtime_config) as runtime:
                browser_session_started = True
                try:
                    seed_reset = _reset_runtime_for_capability_scenario(
                        runtime,
                        request.url,
                    )
                    if seed_reset.warnings:
                        scenario_reset_warnings.extend(seed_reset.warnings)
                    if not seed_reset.ok:
                        raise RuntimeError("; ".join(seed_reset.warnings) or "seed reset failed")
                    seed_analysis = page_analyzer(runtime)
                    seed_baseline_summary = _runtime_baseline_summary(
                        runtime,
                        seed_analysis,
                    )
                    if not seed_baseline_summary:
                        raise RuntimeError("seed baseline snapshot unavailable")
                except Exception as exc:
                    logger.exception("Capability discovery seed analysis failed: %s", exc)
                    return _failed_capability_discovery_result(
                        db=self._db,
                        request=request,
                        batch_controller=batch_controller,
                        batch=batch,
                        policy=policy,
                        state=batch_state,
                        stage="seed_analysis",
                        exc=exc,
                        planned_count=planned_count,
                        attempted_count=attempted_count,
                    )

                try:
                    inventory = build_filter_inventory(seed_analysis)
                    discovery_batch_id = str(batch.id)
                    candidate_scenarios = generate_filter_scenarios(
                        inventory,
                        discovery_batch_id=discovery_batch_id,
                    )
                    scenarios = apply_policy_to_scenarios(candidate_scenarios, policy)
                    planned_count = len(scenarios)
                    batch_controller.mark_running(
                        batch.id,
                        page_template=path_template(seed_analysis.url or request.url),
                        query_signature=query_signature(seed_analysis.url or request.url),
                        dom_fingerprint=dom_fingerprint(seed_analysis),
                        planned_scenarios=[
                            _scenario_payload(scenario) for scenario in scenarios
                        ],
                    )
                except Exception as exc:
                    logger.exception("Capability discovery scenario planning failed: %s", exc)
                    return _failed_capability_discovery_result(
                        db=self._db,
                        request=request,
                        batch_controller=batch_controller,
                        batch=batch,
                        policy=policy,
                        state=batch_state,
                        stage="scenario_planning",
                        exc=exc,
                        planned_count=planned_count,
                        attempted_count=attempted_count,
                        page_template_value=path_template(seed_analysis.url or request.url),
                    )
                if not scenarios:
                    batch_state.unsupported_count = len(inventory.unsupported_capabilities)
                    closed = batch_controller.close(
                        batch.id,
                        state=batch_state,
                        policy=policy,
                        planned_count=0,
                        attempted_count=0,
                        terminal_reason="no_supported_scenarios",
                        warnings=["No supported filter capabilities were discovered."],
                    )
                    summary = _learning_batch_browser_session_summary(
                        closed.summary_json or {},
                        reset_count=scenario_reset_count,
                        reset_warnings=scenario_reset_warnings,
                    )
                    closed = _replace_learning_batch_summary(self._db, closed, summary)
                    return LearningRunResult(
                        status="failed",
                        target_url=request.url,
                        page_template=path_template(seed_analysis.url or request.url),
                        action_label="页面筛选能力",
                        business_goal="",
                        learning_outcome="failed",
                        discovery_batch_id=discovery_batch_id,
                        learning_batch_id=str(closed.id),
                        learning_batch_status=str(closed.status),
                        learning_batch_summary=closed.summary_json or {},
                        unsupported_capability_summaries=[
                            _capability_summary(capability)
                            for capability in inventory.unsupported_capabilities
                        ],
                        error="No supported filter capabilities were discovered.",
                    )

                for scenario in scenarios:
                    boundary = batch_controller.boundary_state(
                        batch.id,
                        started_monotonic=batch_started,
                        policy=policy,
                        state=batch_state,
                    )
                    if boundary.should_stop:
                        terminal_reason = boundary.reason
                        break
                    scenario_request = _request_for_capability_scenario(request, scenario)
                    reset_result = _reset_runtime_for_capability_scenario(
                        runtime,
                        request.url,
                        baseline=seed_analysis,
                        baseline_summary=seed_baseline_summary,
                        page_analyzer=page_analyzer,
                    )
                    scenario_reset_count += 1
                    if reset_result.warnings:
                        scenario_reset_warnings.extend(reset_result.warnings)
                    if not reset_result.ok:
                        warning = (
                            "; ".join(reset_result.warnings)
                            or "Scenario reset baseline could not be restored."
                        )
                        evidence_warnings.append(warning)
                        reset_run_id = _persist_reset_failure_run(
                            db=self._db,
                            request=scenario_request,
                            scenario=scenario,
                            learning_batch_id=str(batch.id),
                            reset_result=reset_result,
                        )
                        if reset_run_id:
                            run_ids.append(reset_run_id)
                            batch_controller.append_run(batch.id, reset_run_id)
                        unverified_scenarios.append(
                            {
                                "scenario_id": scenario.scenario_id,
                                "scenario_kind": scenario.scenario_kind,
                                "human_label": scenario.human_label,
                                "run_id": reset_run_id,
                                "status": "unverified",
                                "warnings": [warning],
                            }
                        )
                        batch_state.unverified_count += 1
                        batch_state.consecutive_no_new_capability += 1
                        reset_unverified_count += 1
                        terminal_reason = "scenario_reset_failed"
                        break
                    attempted_count += 1
                    try:
                        scenario_result = explorer(
                            url=request.url,
                            runtime=runtime,
                            goal=scenario.human_label,
                            fill_values=scenario.fill_values,
                            toggle_values=scenario.toggle_values,
                            scenario_name=scenario.scenario_id,
                            scenario_description=scenario.human_label,
                            language=request.language,
                        )
                        final_data = scenario_result.model_dump()
                        final_data["verification"] = None
                        final_data["capability_scenario"] = _scenario_payload(scenario)
                        verdict = final_data.get("verdict")
                        run_id, learned_path_id = self._persist_finished_run(
                            request=scenario_request,
                            final_data=final_data,
                            verdict=verdict,
                            status=ExplorationRunStatus.COMPLETED,
                            strategy_metadata=_strategy_metadata_for_scenario(
                                scenario,
                                learning_batch_id=str(batch.id),
                            ),
                        )
                    except Exception as exc:
                        logger.exception("Capability discovery scenario failed: %s", exc)
                        batch_state.failed_count += 1
                        return _failed_capability_discovery_result(
                            db=self._db,
                            request=request,
                            batch_controller=batch_controller,
                            batch=batch,
                            policy=policy,
                            state=batch_state,
                            stage="scenario_execution",
                            exc=exc,
                            planned_count=planned_count,
                            attempted_count=attempted_count,
                            page_template_value=path_template(seed_analysis.url or request.url),
                            failed_scenarios=[
                                *failed_scenarios,
                                {
                                    "scenario_id": scenario.scenario_id,
                                    "scenario_kind": scenario.scenario_kind,
                                    "human_label": scenario.human_label,
                                    "status": "failed",
                                },
                            ],
                            unverified_scenarios=unverified_scenarios,
                            created_run_ids=run_ids,
                            created_capability_ids=learned_capability_ids,
                            created_learned_path_ids=persisted_learned_path_ids,
                            reset_count=scenario_reset_count,
                            reset_warnings=scenario_reset_warnings,
                        )
                    if run_id:
                        run_ids.append(run_id)
                        batch_controller.append_run(batch.id, run_id)
                    summary = _scenario_summary(scenario, run_id, learned_path_id, final_data)
                    if learned_path_id:
                        persisted_learned_path_ids.append(learned_path_id)
                        batch_controller.append_learned_path(batch.id, learned_path_id)
                        capability_ids, capability_warnings = self._ingest_learned_capabilities(
                            request=scenario_request,
                            seed_analysis=seed_analysis,
                            scenario=scenario,
                            run_id=run_id,
                            learned_path_id=learned_path_id,
                            final_data=final_data,
                        )
                        learned_capability_ids.extend(capability_ids)
                        evidence_warnings.extend(capability_warnings)
                        for capability_id in capability_ids:
                            batch_controller.append_capability(batch.id, capability_id)
                        summary["learned_capability_ids"] = capability_ids
                        if capability_warnings:
                            summary["warnings"] = capability_warnings
                        if capability_ids:
                            learned_path_ids.append(learned_path_id)
                            passed_capabilities.extend(summary["capabilities"])
                            batch_state.passed_count += 1
                            batch_state.consecutive_no_new_capability = 0
                        else:
                            failed_scenarios.append(summary)
                            batch_state.failed_count += 1
                            batch_state.consecutive_no_new_capability += 1
                            for adapter_type in _adapter_types_for_scenario(scenario):
                                batch_state.adapter_failures[adapter_type] = (
                                    batch_state.adapter_failures.get(adapter_type, 0) + 1
                                )
                    elif verdict == "uncertain":
                        unverified_scenarios.append(summary)
                        batch_state.unverified_count += 1
                        batch_state.consecutive_no_new_capability += 1
                    else:
                        failed_scenarios.append(summary)
                        batch_state.failed_count += 1
                        batch_state.consecutive_no_new_capability += 1
                        for adapter_type in _adapter_types_for_scenario(scenario):
                            batch_state.adapter_failures[adapter_type] = (
                                batch_state.adapter_failures.get(adapter_type, 0) + 1
                            )

                    boundary = batch_controller.boundary_state(
                        batch.id,
                        started_monotonic=batch_started,
                        policy=policy,
                        state=batch_state,
                    )
                    if boundary.should_stop:
                        terminal_reason = boundary.reason
                        break
                    if should_stop_after_attempt(
                        batch_state,
                        policy,
                        adapter_type=_primary_adapter_type_for_scenario(scenario),
                    ):
                        terminal_reason = "bounded_policy_stop"
                        break

                batch_state.unsupported_count = len(inventory.unsupported_capabilities)
                batch_state.skipped_count = max(
                    0,
                    len(scenarios) - attempted_count - reset_unverified_count,
                )
                closed_batch = batch_controller.close(
                    batch.id,
                    state=batch_state,
                    policy=policy,
                    planned_count=planned_count,
                    attempted_count=attempted_count,
                    terminal_reason=terminal_reason or _batch_terminal_reason(batch_state),
                    warnings=_dedupe_warning_strings(
                        [*evidence_warnings, *scenario_reset_warnings]
                    ),
                    failed_scenarios=failed_scenarios,
                    unverified_scenarios=unverified_scenarios,
                    unsupported_scenarios=[
                        _capability_summary(capability)
                        for capability in inventory.unsupported_capabilities
                    ],
                    created_run_ids=run_ids,
                    created_capability_ids=learned_capability_ids,
                    created_learned_path_ids=persisted_learned_path_ids,
                )
                summary = _learning_batch_browser_session_summary(
                    closed_batch.summary_json or {},
                reset_count=scenario_reset_count,
                reset_warnings=scenario_reset_warnings,
            )
                closed_batch = _replace_learning_batch_summary(self._db, closed_batch, summary)
                outcome = _learning_outcome_for(
                    passed_count=len(learned_path_ids),
                    failed_count=len(failed_scenarios),
                    unverified_count=len(unverified_scenarios),
                    unsupported_count=len(inventory.unsupported_capabilities),
                )
                status: LearningStatus = (
                    "failed"
                    if terminal_reason == "scenario_reset_failed" or not learned_path_ids
                    else "learned"
                )
                primary_path_id = learned_path_ids[0] if learned_path_ids else None
                primary_run_id = run_ids[0] if run_ids else None
                capability_summaries = _dedupe_capability_summaries(passed_capabilities)
                return LearningRunResult(
                    status=status,
                    run_id=primary_run_id,
                    learned_path_id=primary_path_id,
                    target_url=request.url,
                    page_template=path_template(seed_analysis.url or request.url),
                    scenario="filter_capability_discovery",
                    action_label="筛选搜索",
                    suggested_utterances=[],
                    business_goal="筛选搜索",
                    canonical_goal="filter_capability_search",
                    action_aliases=["筛选搜索"],
                    business_object="筛选",
                    match_terms=["筛选搜索", "filter_capability_search", "筛选"],
                    learning_outcome=outcome,
                    discovery_batch_id=discovery_batch_id,
                    run_ids=run_ids,
                    learned_path_ids=learned_path_ids,
                    learning_batch_id=str(closed_batch.id),
                    learning_batch_status=str(closed_batch.status),
                    learning_batch_summary=closed_batch.summary_json or {},
                    capability_summaries=capability_summaries,
                    failed_scenario_summaries=failed_scenarios,
                    unverified_scenario_summaries=unverified_scenarios,
                    unsupported_capability_summaries=[
                        _capability_summary(capability)
                        for capability in inventory.unsupported_capabilities
                    ],
                    evidence_warnings=evidence_warnings,
                    error=(
                        "Scenario reset failed before remaining capabilities could be verified."
                        if terminal_reason == "scenario_reset_failed"
                        else None
                        if learned_path_ids
                        else "No filter capability scenario passed."
                    ),
                )
        except Exception as exc:
            logger.exception("Capability discovery browser session failed: %s", exc)
            return _failed_capability_discovery_result(
                db=self._db,
                request=request,
                batch_controller=batch_controller,
                batch=batch,
                policy=policy,
                state=batch_state,
                stage="browser_session",
                exc=exc,
                planned_count=planned_count,
                attempted_count=attempted_count,
                reset_count=scenario_reset_count,
                reset_warnings=scenario_reset_warnings,
                browser_session_reuse=browser_session_started,
                browser_session_setup_failed=not browser_session_started,
            )

    def _persist_finished_run(
        self,
        *,
        request: LearningRunRequest,
        final_data: dict[str, Any],
        verdict: str | None,
        status: ExplorationRunStatus,
        strategy_metadata: dict[str, Any] | None = None,
    ) -> tuple[str | None, str | None]:
        scenario_matched = _scenario_matched_from(final_data)
        strategy = {
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
        }
        if strategy_metadata:
            strategy.update(strategy_metadata)
        run = ExplorationRun(
            page_signature=(request.url or "")[:512],
            mode=ExplorationMode.FORM,
            status=status,
            strategy_json=strategy,
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
            if not _product_learning_should_save_path(
                final_data,
                request.fill_values or {},
                request.toggle_values or {},
            ):
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
        ingest_evaluation = evaluate_attempt_ingest(
            pass_gate_status="pass",
            terminal_state_verdict=final_data.get("terminal_state_verdict"),
            actions=actions,
        )
        final_data["attempt_ingest_evaluation"] = ingest_evaluation.model_dump(mode="json")
        run.result_snapshot_json = final_data
        self._db.add(run)
        self._db.commit()
        self._db.refresh(run)
        if ingest_evaluation.ingest_status != "eligible":
            return None
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

    def _ingest_learned_capabilities(
        self,
        *,
        request: LearningRunRequest,
        seed_analysis: PageAnalysis,
        scenario: CapabilityScenario,
        run_id: str,
        learned_path_id: str,
        final_data: dict[str, Any],
    ) -> tuple[list[str], list[str]]:
        repo = LearnedCapabilityRepository(self._db)
        capability_ids: list[str] = []
        warnings: list[str] = []
        page_url = seed_analysis.url or request.url
        for binding in scenario.input_bindings:
            capability_kind = _capability_kind_for_binding(binding)
            if capability_kind is None:
                warnings.append(
                    f"unsupported capability binding: {binding.get('capability_id')}"
                )
                continue
            try:
                row, _created = repo.ingest(
                    page_template=path_template(page_url),
                    query_signature=query_signature(page_url),
                    dom_fingerprint=dom_fingerprint(seed_analysis),
                    capability_key=str(binding.get("capability_id") or ""),
                    capability_kind=capability_kind,
                    human_label=str(binding.get("label") or "") or None,
                    region_ref="filter-region",
                    control_ref=str(
                        binding.get("capability_id")
                        or binding.get("binding_key")
                        or ""
                    ),
                    adapter_type=str(binding.get("adapter_type") or "unknown"),
                    action_schema_json=_capability_action_schema(binding),
                    sample_value_policy_json=_sample_value_policy_for(binding),
                    terminal_target_json=_terminal_target_for(scenario),
                    evidence_json=_capability_evidence_for(final_data),
                    source_run_id=run_id,
                    source_learned_path_id=learned_path_id,
                )
            except ValueError as exc:
                warnings.append(
                    f"capability ingest rejected {binding.get('capability_id')}: {exc}"
                )
                continue
            capability_ids.append(str(row.id))
        return capability_ids, warnings

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

    def _get_page_analyzer(self) -> Callable[[Any], PageAnalysis]:
        if self._page_analyzer is not None:
            return self._page_analyzer
        from app.services.learning.page_analyzer import analyze_page

        return analyze_page

    def _get_batch_controller(self) -> LearningBatchController:
        return LearningBatchController(
            LearningBatchRepository(self._db),
            clock=self._clock,
            cancel_checker=self._cancel_checker,
        )


def _should_run_capability_discovery(request: LearningRunRequest) -> bool:
    return (
        request.product_level
        and not request.spec_id
        and not request.scenario
        and not (request.fill_values or {})
        and not (request.toggle_values or {})
        and not request.action_goal
        and not request.canonical_goal
        and not request.action_aliases
        and _is_url_only_learning_goal(request.goal)
    )


def _is_url_only_learning_goal(goal: str) -> bool:
    value = str(goal or "").strip()
    if not value:
        return True
    return value in {
        "开始学习",
        "现在开始",
        "学习",
        "学习这个页面上的操作",
        "开始学习页面操作",
        "是",
        "好的",
    }


def _reset_runtime_for_capability_scenario(
    runtime: Any,
    target_url: str,
    *,
    mode: str = "navigate_only",
    baseline: PageAnalysis | None = None,
    baseline_summary: dict[str, Any] | None = None,
    page_analyzer: Callable[[Any], PageAnalysis] | None = None,
) -> _ScenarioResetResult:
    if mode != "navigate_only":
        return _ScenarioResetResult(
            ok=False,
            mode=mode,
            warnings=[f"unsupported scenario reset mode: {mode}"],
        )
    navigate = getattr(runtime, "navigate", None)
    if not callable(navigate):
        return _ScenarioResetResult(
            ok=False,
            mode=mode,
            warnings=["runtime does not support scenario reset navigation"],
        )
    try:
        navigate(target_url)
    except Exception as exc:
        return _ScenarioResetResult(
            ok=False,
            mode=mode,
            warnings=[f"scenario reset navigation failed: {_safe_exception_message(exc)}"],
        )

    url = target_url
    current_url = getattr(runtime, "current_url", None)
    if callable(current_url):
        try:
            url = current_url()
        except Exception as exc:
            return _ScenarioResetResult(
                ok=False,
                mode=mode,
                warnings=[f"scenario reset URL read failed: {_safe_exception_message(exc)}"],
            )

    title: str | None = None
    current_title = getattr(runtime, "current_title", None)
    if callable(current_title):
        try:
            title = current_title()
        except Exception as exc:
            return _ScenarioResetResult(
                ok=False,
                mode=mode,
                url=url,
                warnings=[f"scenario reset title read failed: {_safe_exception_message(exc)}"],
            )

    reset_summary: dict[str, Any] = {}
    if baseline is not None and page_analyzer is not None:
        try:
            reset_analysis = page_analyzer(runtime)
        except Exception as exc:
            return _ScenarioResetResult(
                ok=False,
                mode=mode,
                url=url,
                title=title,
                warnings=[
                    "scenario reset baseline analysis failed: "
                    f"{_safe_exception_message(exc)}"
                ],
            )
        reset_summary = _runtime_baseline_summary(runtime, reset_analysis)
        if not reset_summary:
            return _ScenarioResetResult(
                ok=False,
                mode=mode,
                url=url,
                title=title,
                warnings=["scenario reset baseline snapshot unavailable"],
            )
        warnings = _baseline_compatibility_warnings(
            baseline,
            reset_analysis,
            baseline_summary=baseline_summary,
            candidate_summary=reset_summary,
        )
        if warnings:
            return _ScenarioResetResult(
                ok=False,
                mode=mode,
                url=url,
                title=title,
                baseline_summary=reset_summary,
                warnings=warnings,
            )

    return _ScenarioResetResult(
        ok=True,
        mode=mode,
        url=url,
        title=title,
        baseline_summary=reset_summary,
    )


def _runtime_baseline_summary(runtime: Any, analysis: PageAnalysis) -> dict[str, Any]:
    page_state = _capture_runtime_page_state(runtime)
    if page_state is None:
        return {}
    analysis_summary = _page_analysis_baseline_summary(analysis)
    result_regions = page_state.get("result_regions")
    return {
        "url": analysis.url,
        "title": analysis.title,
        "counts": analysis_summary["counts"],
        "control_state_fingerprint": _stable_digest(page_state.get("controls")),
        "result_region_summary": _result_region_summary(result_regions),
        "page_state_fingerprint": _stable_digest(page_state),
    }


def _page_analysis_baseline_summary(analysis: PageAnalysis) -> dict[str, Any]:
    return {
        "counts": {
            "fillable": len(analysis.fillable),
            "submit": len(analysis.submit),
            "clickable": len(analysis.clickable),
            "navigation": len(analysis.navigation),
            "select": len(analysis.select),
            "toggle": len(analysis.toggle),
            "other": len(analysis.other),
            "total_visible": analysis.total_visible,
        },
    }


def _capture_runtime_page_state(runtime: Any) -> dict[str, Any] | None:
    page = getattr(runtime, "page", None)
    evaluate = getattr(page, "evaluate", None)
    if not callable(evaluate):
        return None
    try:
        value = evaluate(_RESET_BASELINE_SCRIPT)
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def _result_region_summary(result_regions: Any) -> dict[str, Any]:
    if not isinstance(result_regions, dict):
        return {}
    count_fields = (
        "tableRows",
        "roleRows",
        "listItems",
        "options",
        "alerts",
        "dialogs",
        "modals",
    )
    summary = {
        field_name: result_regions.get(field_name)
        for field_name in count_fields
        if isinstance(result_regions.get(field_name), int)
    }
    summary["content_structure_fingerprint"] = _stable_digest(result_regions)
    return summary


def _baseline_compatibility_warnings(
    baseline: PageAnalysis,
    candidate: PageAnalysis,
    *,
    baseline_summary: dict[str, Any] | None = None,
    candidate_summary: dict[str, Any] | None = None,
) -> list[str]:
    warnings: list[str] = []
    if path_template(candidate.url or "") != path_template(baseline.url or ""):
        warnings.append("scenario reset baseline URL path changed")
    if (candidate.title or "") != (baseline.title or ""):
        warnings.append("scenario reset baseline title changed")

    count_fields = ("fillable", "submit", "select", "toggle")
    baseline_counts = _page_analysis_baseline_summary(baseline)["counts"]
    candidate_counts = _page_analysis_baseline_summary(candidate)["counts"]
    for field_name in count_fields:
        if candidate_counts[field_name] != baseline_counts[field_name]:
            warnings.append(f"scenario reset baseline {field_name} count changed")
    if baseline_summary is not None and candidate_summary is not None:
        if (
            baseline_summary.get("control_state_fingerprint")
            != candidate_summary.get("control_state_fingerprint")
        ):
            warnings.append("scenario reset baseline control state changed")
        if (
            baseline_summary.get("result_region_summary")
            != candidate_summary.get("result_region_summary")
        ):
            warnings.append("scenario reset baseline result region changed")
        if (
            baseline_summary.get("page_state_fingerprint")
            != candidate_summary.get("page_state_fingerprint")
        ):
            warnings.append("scenario reset baseline page state changed")
    return warnings


_RESET_BASELINE_SCRIPT = """() => {
  const normalizeText = (value) => String(value || "").replace(/\\s+/g, " ").trim();
  const textHash = (value) => {
    const text = normalizeText(value).slice(0, 500);
    let hash = 2166136261;
    for (let index = 0; index < text.length; index += 1) {
      hash ^= text.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(16).padStart(8, "0");
  };
  const textSignal = (value) => {
    const text = normalizeText(value);
    return {
      textLength: text.length,
      textHash: textHash(text),
    };
  };
  const elementSignal = (el) => ({
    tag: String(el.tagName || "").toLowerCase(),
    role: String(el.getAttribute("role") || ""),
    childCount: el.children ? el.children.length : 0,
    ...textSignal(el.textContent),
  });
  const childStructureHash = (el, limit = 12) => textHash(
    Array.from(el.querySelectorAll("*")).slice(0, limit).map((child) => (
      String(child.tagName || "").toLowerCase() + ":" +
      String(child.getAttribute("role") || "") + ":" +
      String(child.children ? child.children.length : 0)
    )).join("|")
  );
  const controls = Array.from(document.querySelectorAll(
    "input, textarea, select, [contenteditable='true'], [role='textbox'], " +
    "[role='combobox'], [role='searchbox'], [role='checkbox'], [role='radio'], " +
    "[aria-checked]"
  )).map((el, index) => {
    const html = el;
    const options = html.options ? Array.from(html.options).map((option) => ({
      selected: Boolean(option.selected),
      valueLength: String(option.value || "").length,
    })) : [];
    const value = html.value !== undefined ? html.value : html.textContent;
    return {
      index,
      tag: String(el.tagName || "").toLowerCase(),
      type: String(html.type || ""),
      role: String(el.getAttribute("role") || ""),
      checked: Boolean(html.checked || el.getAttribute("aria-checked") === "true"),
      selectedIndex: Number.isInteger(html.selectedIndex) ? html.selectedIndex : null,
      optionState: options,
      valueLength: String(value || "").length,
      valueHash: textHash(value),
      disabled: Boolean(html.disabled),
      readonly: Boolean(html.readOnly || el.getAttribute("aria-readonly") === "true"),
    };
  });
  const tableFingerprints = Array.from(document.querySelectorAll("table, [role='table']"))
    .slice(0, 5)
    .map((table) => ({
      ...elementSignal(table),
      structureHash: childStructureHash(table, 20),
      rows: Array.from(table.querySelectorAll("tr, [role='row']")).slice(0, 8).map((row) => ({
        ...elementSignal(row),
        cells: Array.from(row.querySelectorAll("th, td, [role='cell'], [role='columnheader']"))
          .slice(0, 8)
          .map((cell) => elementSignal(cell)),
      })),
    }));
  const rowFingerprints = Array.from(document.querySelectorAll("[role='row']"))
    .slice(0, 12)
    .map((row) => ({
      ...elementSignal(row),
      structureHash: childStructureHash(row, 12),
      children: Array.from(row.children || []).slice(0, 8).map((child) => elementSignal(child)),
    }));
  const listFingerprints = Array.from(document.querySelectorAll("li, [role='listitem']"))
    .slice(0, 12)
    .map((item) => ({
      ...elementSignal(item),
      structureHash: childStructureHash(item, 8),
    }));
  const regionFingerprints = Array.from(document.querySelectorAll(
    "main, [role='main'], [role='region'], [aria-live], section, article, " +
    "[role='list'], [role='table'], table, tbody"
  )).slice(0, 12).map((region) => ({
    ...elementSignal(region),
    structureHash: childStructureHash(region, 18),
  }));
  const resultRegions = {
    tableRows: document.querySelectorAll("tbody tr").length,
    roleRows: document.querySelectorAll("[role='row']").length,
    listItems: document.querySelectorAll("li, [role='listitem']").length,
    options: document.querySelectorAll("[role='option'], option").length,
    alerts: document.querySelectorAll("[role='alert']").length,
    dialogs: document.querySelectorAll("[role='dialog'], dialog[open]").length,
    modals: document.querySelectorAll("[aria-modal='true']").length,
    tableFingerprints,
    rowFingerprints,
    listFingerprints,
    regionFingerprints,
  };
  return { controls, result_regions: resultRegions };
}"""


def _learning_batch_browser_session_summary(
    summary: dict[str, Any],
    *,
    reset_count: int,
    reset_warnings: list[str],
    browser_session_reuse: bool = True,
    browser_session_setup_failed: bool = False,
) -> dict[str, Any]:
    result = dict(summary)
    result["browser_session_reuse"] = browser_session_reuse
    if browser_session_setup_failed:
        result["browser_session_setup_failed"] = True
    result["scenario_reset_count"] = reset_count
    if reset_warnings:
        result["scenario_reset_warnings"] = _dedupe_warning_strings(reset_warnings)
    return result


def _dedupe_warning_strings(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _replace_learning_batch_summary(
    db: Session,
    batch: Any,
    summary: dict[str, Any],
) -> Any:
    batch.summary_json = summary
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def _persist_reset_failure_run(
    *,
    db: Session,
    request: LearningRunRequest,
    scenario: CapabilityScenario,
    learning_batch_id: str,
    reset_result: _ScenarioResetResult,
) -> str | None:
    final_data = {
        "verification": None,
        "capability_scenario": _scenario_payload(scenario),
        "verdict": "uncertain",
        "success": False,
        "summary": "Scenario reset failed before execution.",
        "reset_result": {
            "ok": reset_result.ok,
            "mode": reset_result.mode,
            "url": reset_result.url,
            "title": reset_result.title,
            "warnings": reset_result.warnings,
            "baseline_summary": reset_result.baseline_summary,
        },
        "terminal_state_verdict": {
            "terminal_outcome": "terminal_unverified",
            "terminal_type": "no_observable_change",
            "evidence_strength": "none",
            "stop_decision": "unverified_stop",
            "warnings": ["scenario_reset_failed"],
            "missing_evidence": ["scenario_execution"],
            "source": "deterministic",
        },
        "attempt_ingest_evaluation": {
            "ingest_status": "unverified",
            "attempt_outcome": "unverified",
            "failure_category": "scenario_reset_failed",
            "reasons": ["scenario_reset_failed"],
        },
    }
    run = ExplorationRun(
        page_signature=(request.url or "")[:512],
        mode=ExplorationMode.FORM,
        status=ExplorationRunStatus.FAILED,
        strategy_json={
            "kind": "filter_capability_discovery",
            "url": request.url,
            "goal": request.goal or "",
            "scenario": request.scenario,
            "language": request.language,
            "headless": request.headless,
            "product_level": request.product_level,
            "learning_batch_id": learning_batch_id,
            "discovery_batch_id": scenario.discovery_batch_id,
            "scenario_kind": scenario.scenario_kind,
            "scenario_id": scenario.scenario_id,
            "capability_id": scenario.capability_id,
            "reset_failed": True,
            "verdict": "uncertain",
            "scenario_matched": False,
        },
        summary=final_data["summary"],
        result_snapshot_json=final_data,
    )
    ExplorationRunRepository(db).create(run)
    return str(run.id)


def _request_for_capability_scenario(
    request: LearningRunRequest,
    scenario: CapabilityScenario,
) -> LearningRunRequest:
    return replace(
        request,
        scenario=scenario.scenario_id,
        goal=scenario.human_label,
        fill_values=scenario.fill_values,
        toggle_values=scenario.toggle_values,
        action_goal=scenario.human_label,
        canonical_goal=scenario.scenario_id,
        action_aliases=[scenario.human_label],
    )


def _strategy_metadata_for_scenario(
    scenario: CapabilityScenario,
    *,
    learning_batch_id: str | None = None,
) -> dict[str, Any]:
    return {
        "kind": "filter_capability_discovery",
        "discovery_batch_id": scenario.discovery_batch_id,
        "learning_batch_id": learning_batch_id,
        "scenario_kind": scenario.scenario_kind,
        "scenario_id": scenario.scenario_id,
        "capability_id": scenario.capability_id,
        "capability_label": scenario.human_label,
        "bound_controls": scenario.input_bindings,
        "source_capability_ids": scenario.source_capability_ids,
        "expected_observation_target": scenario.expected_observation_target,
    }


def _scenario_payload(scenario: CapabilityScenario) -> dict[str, Any]:
    return {
        "scenario_id": scenario.scenario_id,
        "scenario_kind": scenario.scenario_kind,
        "human_label": scenario.human_label,
        "input_bindings": scenario.input_bindings,
        "expected_observation_target": scenario.expected_observation_target,
        "discovery_batch_id": scenario.discovery_batch_id,
        "source_capability_ids": scenario.source_capability_ids,
        "fill_values": scenario.fill_values,
        "toggle_values": scenario.toggle_values,
    }


def _adapter_types_for_scenario(scenario: CapabilityScenario) -> list[str]:
    adapter_types: list[str] = []
    for binding in scenario.input_bindings:
        adapter_type = str(binding.get("adapter_type") or "").strip()
        if adapter_type and adapter_type not in adapter_types:
            adapter_types.append(adapter_type)
    return adapter_types


def _primary_adapter_type_for_scenario(scenario: CapabilityScenario) -> str | None:
    adapter_types = _adapter_types_for_scenario(scenario)
    return adapter_types[0] if adapter_types else None


def _scenario_summary(
    scenario: CapabilityScenario,
    run_id: str | None,
    learned_path_id: str | None,
    final_data: dict[str, Any],
) -> dict[str, Any]:
    return {
        "scenario_id": scenario.scenario_id,
        "scenario_kind": scenario.scenario_kind,
        "human_label": scenario.human_label,
        "run_id": run_id,
        "learned_path_id": learned_path_id,
        "verdict": final_data.get("verdict"),
        "summary": final_data.get("summary"),
        "capabilities": [
            {
                "capability_id": binding.get("capability_id"),
                "label": binding.get("label"),
                "adapter_type": binding.get("adapter_type"),
                "binding_key": binding.get("binding_key"),
                "control_ref": binding.get("capability_id") or binding.get("binding_key"),
                "scenario_id": scenario.scenario_id,
                "scenario_kind": scenario.scenario_kind,
                "run_id": run_id,
                "learned_path_id": learned_path_id,
            }
            for binding in scenario.input_bindings
        ],
    }


def _capability_summary(capability: Any) -> dict[str, Any]:
    data = asdict(capability)
    return {
        "capability_id": data.get("capability_id"),
        "label": data.get("human_label"),
        "control_type": data.get("control_type"),
        "adapter_type": data.get("adapter_type"),
        "supported": data.get("supported"),
        "support_reason": data.get("support_reason"),
        "control_ref": data.get("capability_id") or data.get("binding_key"),
    }


def _dedupe_capability_summaries(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        key = str(item.get("capability_id") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _learning_outcome_for(
    *,
    passed_count: int,
    failed_count: int,
    unverified_count: int,
    unsupported_count: int,
) -> LearningOutcome:
    if passed_count > 0 and not failed_count and not unverified_count and not unsupported_count:
        return "success"
    if passed_count > 0:
        return "partial_success"
    if unverified_count > 0:
        return "unverified"
    return "failed"


def _learning_batch_request_payload(request: LearningRunRequest) -> dict[str, Any]:
    return {
        "url": request.url,
        "session_id": request.session_id,
        "goal": request.goal,
        "headless": request.headless,
        "language": request.language,
        "product_level": request.product_level,
    }


def _batch_result_without_scenarios(
    request: LearningRunRequest,
    batch: Any,
) -> LearningRunResult:
    return LearningRunResult(
        status="failed",
        target_url=request.url,
        action_label="页面筛选能力",
        business_goal="",
        learning_outcome="failed",
        discovery_batch_id=str(batch.id),
        learning_batch_id=str(batch.id),
        learning_batch_status=str(batch.status),
        learning_batch_summary=batch.summary_json or {},
        error="Learning batch stopped before scenario planning.",
    )


def _failed_capability_discovery_result(
    *,
    db: Session,
    request: LearningRunRequest,
    batch_controller: LearningBatchController,
    batch: Any,
    policy: BoundedLearningPolicy,
    state: BoundedAttemptState,
    stage: str,
    exc: Exception,
    planned_count: int,
    attempted_count: int,
    page_template_value: str | None = None,
    failed_scenarios: list[dict[str, Any]] | None = None,
    unverified_scenarios: list[dict[str, Any]] | None = None,
    created_run_ids: list[str] | None = None,
    created_capability_ids: list[str] | None = None,
    created_learned_path_ids: list[str] | None = None,
    reset_count: int = 0,
    reset_warnings: list[str] | None = None,
    browser_session_reuse: bool = True,
    browser_session_setup_failed: bool = False,
) -> LearningRunResult:
    error = _safe_exception_message(exc)
    if "cancellation requested" in error:
        state.cancellation_requested = True
        terminal_reason = "cancel_requested"
    else:
        state.failed_count = max(state.failed_count, 1)
        terminal_reason = f"exception_{stage}"
    closed = batch_controller.close(
        batch.id,
        state=state,
        policy=policy,
        planned_count=planned_count,
        attempted_count=attempted_count,
        terminal_reason=terminal_reason,
        warnings=[f"{stage} failed: {error}"],
        failed_scenarios=failed_scenarios,
        unverified_scenarios=unverified_scenarios,
        created_run_ids=created_run_ids,
        created_capability_ids=created_capability_ids,
        created_learned_path_ids=created_learned_path_ids,
    )
    summary = _learning_batch_browser_session_summary(
        closed.summary_json or {},
        reset_count=reset_count,
        reset_warnings=reset_warnings or [],
        browser_session_reuse=browser_session_reuse,
        browser_session_setup_failed=browser_session_setup_failed,
    )
    closed = _replace_learning_batch_summary(db, closed, summary)
    return LearningRunResult(
        status="failed",
        target_url=request.url,
        page_template=page_template_value,
        action_label="页面筛选能力",
        business_goal="",
        learning_outcome="failed",
        discovery_batch_id=str(batch.id),
        learning_batch_id=str(closed.id),
        learning_batch_status=str(closed.status),
        learning_batch_summary=closed.summary_json or {},
        error=f"Capability discovery failed during {stage}: {error}",
    )


def _safe_exception_message(exc: Exception) -> str:
    message = f"{type(exc).__name__}: {exc}".strip()
    message = re.sub(r"#[A-Za-z0-9_-]+", "[redacted-selector]", message)
    message = re.sub(r"https?://\S+", "[redacted-url]", message)
    return message[:300]


def _batch_terminal_reason(state: BoundedAttemptState) -> str:
    if state.cancellation_requested and state.passed_count:
        return "cancel_after_assets"
    if state.cancellation_requested:
        return "cancel_before_assets"
    if state.timeout_occurred and state.passed_count:
        return "timeout_after_assets"
    if state.timeout_occurred:
        return "timeout_before_assets"
    if state.passed_count and (
        state.failed_count or state.unverified_count or state.unsupported_count
    ):
        return "some_capabilities_not_learned"
    if state.passed_count:
        return "all_planned_capabilities_learned"
    if state.unverified_count:
        return "only_unverified_capabilities"
    return "no_capability_passed"


def _capability_kind_for_binding(binding: dict[str, Any]) -> str | None:
    adapter_type = str(binding.get("adapter_type") or "").lower()
    if adapter_type in {"fill", "input", "text", "date", "month", "set_value"}:
        return "control_input"
    if adapter_type == "select":
        return "control_select"
    if adapter_type == "toggle":
        return "control_toggle"
    return None


def _capability_action_schema(binding: dict[str, Any]) -> dict[str, Any]:
    adapter_type = str(binding.get("adapter_type") or "unknown")
    binding_key = str(binding.get("binding_key") or "")
    operation = "select" if adapter_type == "select" else "set_value"
    if adapter_type == "toggle":
        operation = "click"
    return {
        "version": "capability_action.v1",
        "adapter_type": adapter_type,
        "operation": operation,
        "required_slots": [binding_key] if binding_key else [],
        "control_binding": {
            "capability_id": str(binding.get("capability_id") or ""),
            "binding_key": binding_key,
            "label": str(binding.get("label") or ""),
        },
    }


def _sample_value_policy_for(binding: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": "sample_value_policy.v1",
        "source": "capability_discovery_binding",
        "strength": "medium",
        "binding_key": str(binding.get("binding_key") or ""),
    }


def _terminal_target_for(scenario: CapabilityScenario) -> dict[str, Any]:
    target = dict(scenario.expected_observation_target or {})
    return {
        "version": "terminal_target.v1",
        "kind": target.get("kind") or "list_refresh",
        "region_ref": target.get("region_ref") or "result-region",
    }


def _capability_evidence_for(final_data: dict[str, Any]) -> dict[str, Any]:
    terminal_state = final_data.get("terminal_state_verdict") or {}
    return {
        "version": "capability_evidence.v1",
        "source": "exploration_run",
        "terminal_outcome": terminal_state.get("terminal_outcome")
        or "terminal_detected",
        "business_match_observed": True,
        "evidence_strength": terminal_state.get("evidence_strength") or "medium",
        "warnings": [],
        "redaction": {"normal_projection_hides_raw_debug": True},
    }


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


def _product_learning_should_save_path(
    final_data: dict[str, Any],
    fill_values: dict[str, str],
    toggle_values: dict[str, str],
) -> bool:
    if not _has_reusable_action_steps(final_data):
        return False

    if (
        isinstance(final_data.get("capability_scenario"), dict)
        and not _expected_bindings_have_action_evidence(
            final_data,
            fill_values=fill_values,
            toggle_values=toggle_values,
        )
    ):
        return False

    if final_data.get("success"):
        return True

    if _final_state_confirms_fill_value(final_data, fill_values):
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


def _has_reusable_action_steps(final_data: dict[str, Any]) -> bool:
    steps = final_data.get("steps")
    if not isinstance(steps, list):
        return False
    reusable_types = {
        "fill",
        "set_value",
        "select",
        "select_first_option",
        "click",
        "press",
    }
    for step in steps:
        if not isinstance(step, dict):
            continue
        action_type = str(step.get("action_type") or "").lower()
        if action_type in reusable_types:
            return True
    return False


def _expected_bindings_have_action_evidence(
    final_data: dict[str, Any],
    *,
    fill_values: dict[str, str],
    toggle_values: dict[str, str],
) -> bool:
    expected_values = [
        str(value).strip()
        for value in [*fill_values.values(), *toggle_values.values()]
        if str(value).strip()
    ]
    if not expected_values:
        return True

    steps = final_data.get("steps")
    if not isinstance(steps, list):
        return False
    observed_values = [
        str(step.get("value")).strip()
        for step in steps
        if isinstance(step, dict) and step.get("value") is not None
    ]
    expected_counts = Counter(expected_values)
    observed_counts = Counter(observed_values)
    return all(observed_counts[value] >= count for value, count in expected_counts.items())


def _final_state_confirms_fill_value(
    final_data: dict[str, Any],
    fill_values: dict[str, str],
) -> bool:
    values = [str(value).strip() for value in fill_values.values() if str(value).strip()]
    if not values:
        return False
    final_state = final_data.get("final_state")
    if not isinstance(final_state, dict):
        return False
    visible_parts: list[str] = []
    for key in ("body_text", "visible_text", "page_text"):
        value = final_state.get(key)
        if isinstance(value, str):
            visible_parts.append(value)
    alerts = final_state.get("alert_texts")
    if isinstance(alerts, list):
        visible_parts.extend(str(item) for item in alerts if item is not None)
    visible_text = "\n".join(visible_parts)
    if not visible_text:
        return False
    return any(value in visible_text for value in values)


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
    if request.product_level:
        return _product_utterances_for(request)
    label = _action_label_for(request)
    return [f"帮我{label}", f"{label}一下"]


def _product_utterances_for(request: LearningRunRequest) -> list[str]:
    identity = _action_identity_for(request)
    fill_values = request.fill_values or {}
    label = _action_label_for(request)
    if label == "登录":
        return ["帮我登录", "登录一下"]
    candidates = [
        identity["business_goal"],
        _readable_canonical_goal(identity["canonical_goal"]),
        *identity["action_aliases"],
    ]
    phrases = [
        phrase
        for phrase in (_clean_utterance_phrase(candidate) for candidate in candidates)
        if phrase
        and not _contains_fill_value(phrase, fill_values)
        and not _is_verb_only_term(phrase)
    ]
    phrases = _dedupe_terms(phrases)
    if not phrases:
        fallback = _clean_utterance_phrase(label)
        if (
            fallback
            and not _contains_fill_value(fallback, fill_values)
            and not _is_verb_only_term(fallback)
        ):
            phrases = [fallback]
    if not phrases:
        return [f"帮我{label}", f"{label}一下"]

    primary = phrases[0]
    if _contains_cjk(primary):
        utterances = [f"帮我{primary}", f"{primary}一下"]
    else:
        utterances = [primary, f"Help me {_lower_initial_ascii(primary)}", *phrases[1:]]
    return _dedupe_terms(
        [
            utterance
            for utterance in utterances
            if not _contains_fill_value(utterance, fill_values)
            and not _is_verb_only_term(utterance)
        ]
    )


def _product_action_label_for(request: LearningRunRequest) -> str:
    identity = _action_identity_for(request)
    identity_goal = identity["business_goal"]
    goal = identity_goal or _readable_canonical_goal(request.canonical_goal)
    if not goal and identity["action_aliases"]:
        goal = identity["action_aliases"][0]
    if not goal:
        goal = _strip_product_learning_noise(request.goal or "")
        goal = _strip_named_value_clauses(goal)
        if _contains_fill_value(goal, request.fill_values or {}):
            goal = ""
    goal = _strip_named_value_clauses(goal)
    if "登录" in goal:
        return "登录"

    for prefix in ("帮我", "请帮我", "你帮我", "我要", "我想"):
        if goal.startswith(prefix):
            goal = goal[len(prefix):].strip(" ，,。.!！?？")
            break
    return (goal or "执行操作").strip(" ，,。.!！?？")[:20]


def _action_identity_for(request: LearningRunRequest) -> dict[str, Any]:
    business_goal = _clean_business_goal(request.action_goal or "")
    if _contains_fill_value(business_goal, request.fill_values or {}):
        business_goal = ""
    if not business_goal and request.product_level:
        fallback_goal = _clean_business_goal(_strip_product_learning_noise(request.goal or ""))
        if not _contains_fill_value(fallback_goal, request.fill_values or {}):
            business_goal = fallback_goal
    canonical_goal = (request.canonical_goal or "").strip() or None
    if canonical_goal and _contains_fill_value(canonical_goal, request.fill_values or {}):
        canonical_goal = None
    action_aliases = _dedupe_terms(
        [
            alias
            for alias in (_clean_business_goal(alias) for alias in request.action_aliases)
            if not _contains_fill_value(alias, request.fill_values or {})
        ]
    )
    if not business_goal:
        business_goal = _readable_canonical_goal(canonical_goal) or (
            action_aliases[0] if action_aliases else ""
        )
    business_object = _business_object_for(
        business_goal=business_goal,
        canonical_goal=canonical_goal,
        aliases=action_aliases,
    )
    match_terms = _dedupe_terms(
        [
            business_goal,
            canonical_goal or "",
            _readable_canonical_goal(canonical_goal),
            *action_aliases,
            business_object or "",
        ]
    )
    match_terms = _exclude_fill_value_terms(match_terms, request.fill_values or {})
    return {
        "business_goal": business_goal,
        "canonical_goal": canonical_goal,
        "action_aliases": action_aliases,
        "business_object": business_object,
        "match_terms": match_terms,
    }


def _clean_business_goal(text: str) -> str:
    return _strip_named_value_clauses(_strip_product_learning_noise(text or ""))


def _clean_utterance_phrase(text: str) -> str:
    return _strip_named_value_clauses(_strip_product_learning_noise(text or "")).strip(
        " ，,。.!！?？"
    )


def _readable_canonical_goal(canonical_goal: str | None) -> str:
    value = (canonical_goal or "").strip()
    if not value:
        return ""
    return re.sub(r"[_-]+", " ", value).strip()


def _business_object_for(
    *,
    business_goal: str,
    canonical_goal: str | None,
    aliases: list[str],
) -> str | None:
    candidates = [
        _readable_canonical_goal(canonical_goal),
        business_goal,
        *aliases,
    ]
    for candidate in candidates:
        value = _strip_leading_action_verb(candidate)
        if value and value != candidate.strip():
            return value
    return None


def _strip_leading_action_verb(text: str) -> str:
    value = (text or "").strip(" ，,。.!！?？")
    lowered = value.lower()
    for verb in (
        "create",
        "add",
        "open",
        "update",
        "edit",
        "delete",
        "remove",
        "search",
        "find",
        "submit",
        "complete",
        "view",
    ):
        prefix = f"{verb} "
        if lowered.startswith(prefix):
            return value[len(prefix) :].strip(" ，,。.!！?？")
    return value


def _dedupe_terms(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for term in terms:
        value = (term or "").strip(" ，,。.!！?？")
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", text or ""))


def _lower_initial_ascii(text: str) -> str:
    if not text:
        return ""
    first = text[0]
    if "A" <= first <= "Z":
        return first.lower() + text[1:]
    return text


def _is_verb_only_term(text: str) -> bool:
    value = re.sub(r"[_-]+", " ", str(text or "").strip().lower())
    value = re.sub(r"[\s，。,.；;!！?？:：\"'“”‘’（）()\[\]{}]+", " ", value).strip()
    return value in {
        "create",
        "add",
        "open",
        "update",
        "edit",
        "delete",
        "remove",
        "search",
        "find",
        "submit",
        "complete",
        "view",
    }


def _contains_fill_value(term: str, fill_values: dict[str, str]) -> bool:
    lowered = str(term or "").strip().lower()
    if not lowered:
        return False
    for value in fill_values.values():
        slot_value = str(value).strip().lower() if value is not None else ""
        if slot_value and slot_value in lowered:
            return True
    return False


def _exclude_fill_value_terms(
    terms: list[str],
    fill_values: dict[str, str],
) -> list[str]:
    slot_values = [
        str(value).strip().lower()
        for value in fill_values.values()
        if value is not None and str(value).strip()
    ]
    if not slot_values:
        return terms
    filtered: list[str] = []
    for term in terms:
        lowered = term.lower()
        if any(slot_value and slot_value in lowered for slot_value in slot_values):
            continue
        filtered.append(term)
    return filtered


def _strip_product_learning_noise(text: str) -> str:
    cleaned = re.sub(r"https?://[^\s，。]+", "", text)
    cleaned = re.sub(r"操作员账号[是为]?\s*[:：]?[^\s，。,.；;!！?？]+", "", cleaned)
    cleaned = re.sub(r"访问口令[是为]?\s*[:：]?[^\s，。,.；;!！?？]+", "", cleaned)
    for phrase in ("学习一下", "学一下", "学习", "这个", "页面", "地址是"):
        cleaned = cleaned.replace(phrase, "")
    cleaned = re.sub(r"^\s*(?:learn how to|learn to|teach me to)\s+", "", cleaned, flags=re.I)
    return cleaned.strip()


def _strip_named_value_clauses(text: str) -> str:
    cleaned = re.sub(
        r"(?:名称|(?<![A-Za-z0-9_])name(?![A-Za-z0-9_]))"
        r"\s*(?:叫|是|为|=|:|：)\s*[^\s，。,.；;!！?？]+",
        "",
        text,
        flags=re.I,
    )
    return cleaned.strip(" ，,。.!！?？")
