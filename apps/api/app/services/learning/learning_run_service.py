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
    action_goal: str | None = None
    canonical_goal: str | None = None
    action_aliases: list[str] = field(default_factory=list)


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
            if not _product_learning_should_save_path(
                final_data,
                request.fill_values or {},
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


def _product_learning_should_save_path(
    final_data: dict[str, Any],
    fill_values: dict[str, str],
) -> bool:
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
    label = _action_label_for(request)
    return [f"帮我{label}", f"{label}一下"]


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
