"""LearnedPath replay orchestration.

This module coordinates drift precheck, action execution through the shared
executor, post-action wait results, and replay-level observation aggregation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from playwright.sync_api import Page

from app.models.learned_path import LearnedPath
from app.schemas.learned_path_replay import (
    ReplayAction,
    ReplayDriftStatus,
    ReplayResult,
    ReplayStatus,
    ReplayStepLog,
    WaitResult,
)
from app.schemas.page_analysis import PageAnalysis
from app.services.execution.execution_runtime import RuntimeConfig, create_execution_runtime
from app.services.learning.page_analyzer import analyze_page
from app.services.learning.page_signature import (
    build_signature_dict,
)
from app.services.learning.replay_observation import (
    build_replay_observation_summary,
)
from app.services.learning.wait_for_change import (
    wait_for_change_after_action,
)

SUPPORTED_ACTION_TYPES = {"fill", "click", "press", "observe"}


# ---------------------------------------------------------------------------
# Drift precheck result
# ---------------------------------------------------------------------------


@dataclass
class DriftPrecheckResult:
    """Outcome of the replay drift precheck.

    When ``blocked`` is True the caller should abort replay and report
    ``blocked_status`` as the final ``ReplayResult.status``.

    When ``blocked`` is False the caller may proceed to action execution
    (if ``actions`` is non-empty) or report ``observed`` (if ``actions``
    is empty).
    """

    drift_status: ReplayDriftStatus
    drift_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blocked: bool = True
    blocked_status: ReplayStatus | None = None
    actions: list[ReplayAction] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_replay_actions(raw_actions: list[dict[str, Any]]) -> list[ReplayAction]:
    """Convert raw stored actions into validated ``ReplayAction`` objects.

    ``step`` defaults to the list index when missing in storage.
    """
    result: list[ReplayAction] = []
    for idx, raw in enumerate(raw_actions):
        step = raw.get("step", idx)
        action_type = str(raw.get("action_type", "")).lower()
        result.append(
            ReplayAction(
                step=step,
                action_type=action_type,
                target_selector=raw.get("target_selector"),
                target_description=raw.get("target_description"),
                value=raw.get("value"),
            )
        )
    return result


def _count_selector_matches(page: Page, selector: str | None) -> int:
    """Return how many elements match *selector* on the current page."""
    if not selector:
        return 0
    try:
        return page.locator(selector).count()
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Drift precheck
# ---------------------------------------------------------------------------


def run_drift_precheck(
    learned_path: LearnedPath,
    current_url: str,
    current_analysis: PageAnalysis,
    page: Page,
) -> DriftPrecheckResult:
    """Compare a stored LearnedPath against the current page state.

    Evaluation order:

    1. **page_mismatch** — current ``page_template`` differs from stored.
       Blocked; status ``drifted``.
    2. **signature_changed** — ``query_signature`` or ``dom_fingerprint``
       differs while template matches.  Non-fatal warning; replay may
       proceed if selectors are still locatable.
    3. **unsupported_action** — an action type is outside the supported
       set (``fill`` / ``click`` / ``press`` / ``observe``).
       Blocked; status ``unsupported``.
    4. **target_missing** — a supported non-``observe`` action has a
       selector that matches zero elements.
       Blocked; status ``drifted``.
    5. **none** — everything aligns.  Not blocked.

    For observational paths (``actions=[]``) the result is never blocked
    by selector checks; the caller should surface ``observed`` as the
    final status.
    """
    # Current signature
    current_sig = build_signature_dict(url=current_url, analysis=current_analysis)
    current_page_template = current_sig["page_template"]

    stored_page_template = learned_path.page_template
    stored_query_sig = learned_path.query_signature or {}
    stored_dom_fp = learned_path.dom_fingerprint

    # 1. page_mismatch
    if current_page_template != stored_page_template:
        return DriftPrecheckResult(
            drift_status="page_mismatch",
            drift_reasons=[
                f"Page template mismatch: expected {stored_page_template!r}, "
                f"got {current_page_template!r}"
            ],
            blocked=True,
            blocked_status="drifted",
        )

    # 2. signature_changed
    signature_changed = (
        current_sig["query_signature"] != stored_query_sig
        or current_sig["dom_fingerprint"] != stored_dom_fp
    )
    warnings: list[str] = []
    if signature_changed:
        warnings.append(
            "Signature changed: query_signature or dom_fingerprint "
            "differs from stored values"
        )

    # Build actions from storage
    raw_actions = learned_path.actions or []
    replay_actions = _build_replay_actions(raw_actions)

    # 3. unsupported_action
    for action in replay_actions:
        if action.action_type not in SUPPORTED_ACTION_TYPES:
            return DriftPrecheckResult(
                drift_status="unsupported_action",
                drift_reasons=[
                    f"Unsupported action type {action.action_type!r} at step {action.step}"
                ],
                warnings=warnings,
                blocked=True,
                blocked_status="unsupported",
            )

    # 4. target_missing (skip observe actions)
    for action in replay_actions:
        if action.action_type == "observe":
            continue
        count = _count_selector_matches(page, action.target_selector)
        if count == 0:
            return DriftPrecheckResult(
                drift_status="target_missing",
                drift_reasons=[
                    f"Target missing for step {action.step} "
                    f"(selector={action.target_selector!r})"
                ],
                warnings=warnings,
                blocked=True,
                blocked_status="drifted",
            )

    # 5. Final drift status
    drift_status: ReplayDriftStatus = (
        "signature_changed" if signature_changed else "none"
    )

    # Observational path — caller will report observed
    return DriftPrecheckResult(
        drift_status=drift_status,
        warnings=warnings,
        blocked=False,
        actions=replay_actions,
    )


# ---------------------------------------------------------------------------
# Step-log conversion
# ---------------------------------------------------------------------------


def _step_log_to_replay_step(log: dict[str, Any]) -> ReplayStepLog:
    """Convert an executor step-log dict into a ``ReplayStepLog``."""
    return ReplayStepLog(
        step=log.get("step_index", 0),
        action_type=log.get("action_type", ""),
        selector=log.get("target_selector"),
        ok=log.get("ok", False),
        error=log.get("error"),
        matched_count=log.get("matched_count"),
        url_before=log.get("url_before"),
        title_before=log.get("title_before"),
        url_after=log.get("url_after"),
        title_after=log.get("title_after"),
        screenshot_ref=log.get("screenshot_ref"),
        wait_result=log.get("wait_result"),
    )


# ---------------------------------------------------------------------------
# Full replay
# ---------------------------------------------------------------------------


def run_replay(
    learned_path: LearnedPath,
    url: str,
    *,
    headless: bool = True,
) -> ReplayResult:
    """Run a full LearnedPath replay against *url*.

    Playwright lifecycle or navigation errors surface as
    ``status = runtime_error`` rather than raising.  The runtime is
    always stopped via ``try/finally`` so browser processes are never
    leaked on unexpected exceptions.
    """
    from app.services.execution.action_executor import execute_action

    # ── Start runtime ──
    runtime = None
    try:
        runtime = create_execution_runtime(
            config=RuntimeConfig(headless=headless)
        )
        runtime.start()
    except Exception as exc:
        return ReplayResult(
            learned_path_id=str(learned_path.id),
            source_run_id=learned_path.source_run_id,
            trust=str(learned_path.trust),
            status="runtime_error",
            drift_status="none",
            drift_reasons=[f"Failed to start Playwright runtime: {exc}"],
        )

    # Everything after start() is wrapped in try/finally so
    # runtime.stop() always runs.
    try:
        # ── Navigate ──
        try:
            runtime.navigate(url)
        except Exception as exc:
            return ReplayResult(
                learned_path_id=str(learned_path.id),
                source_run_id=learned_path.source_run_id,
                trust=str(learned_path.trust),
                status="runtime_error",
                drift_status="none",
                drift_reasons=[f"Navigation to {url!r} failed: {exc}"],
            )

        # ── Analyze page ──
        try:
            analysis = analyze_page(runtime)
        except Exception as exc:
            return ReplayResult(
                learned_path_id=str(learned_path.id),
                source_run_id=learned_path.source_run_id,
                trust=str(learned_path.trust),
                status="runtime_error",
                drift_status="none",
                drift_reasons=[f"Page analysis failed: {exc}"],
            )

        current_url = runtime.current_url() if runtime.page else url

        # ── Drift precheck ──
        precheck = run_drift_precheck(
            learned_path, current_url, analysis, runtime.page
        )

        stored_sig = {
            "page_template": learned_path.page_template,
            "query_signature": learned_path.query_signature or {},
            "dom_fingerprint": learned_path.dom_fingerprint,
        }
        current_sig = build_signature_dict(url=current_url, analysis=analysis)

        if precheck.blocked:
            return ReplayResult(
                learned_path_id=str(learned_path.id),
                source_run_id=learned_path.source_run_id,
                trust=str(learned_path.trust),
                status=precheck.blocked_status or "drifted",
                drift_status=precheck.drift_status,
                drift_reasons=precheck.drift_reasons,
                warnings=precheck.warnings,
                stored_signature=stored_sig,
                current_signature=current_sig,
                steps=[],
                final_url=current_url,
                final_title=analysis.title if analysis else None,
            )

        # ── Observational path ──
        if not precheck.actions:
            obs_summary = build_replay_observation_summary(
                learned_path_id=str(learned_path.id),
                steps=[],
            )
            return ReplayResult(
                learned_path_id=str(learned_path.id),
                source_run_id=learned_path.source_run_id,
                trust=str(learned_path.trust),
                status="observed",
                drift_status=precheck.drift_status,
                warnings=precheck.warnings,
                stored_signature=stored_sig,
                current_signature=current_sig,
                steps=[],
                final_url=current_url,
                final_title=analysis.title if analysis else None,
                observation_summary=obs_summary,
            )

        # ── Execute actions ──
        step_logs: list[dict[str, Any]] = []
        failed = False
        try:
            for action in precheck.actions:
                log = execute_action(action, runtime)
                try:
                    wait_result = wait_for_change_after_action(
                        page=runtime.page if runtime else None,
                        action=action,
                        step_log=log,
                    )
                except Exception as wait_exc:
                    # wait service must never change replay status
                    wait_result = WaitResult(
                        status="skipped",
                        notes=f"wait failed: {wait_exc}"[:300],
                    )
                log["wait_result"] = wait_result
                step_logs.append(log)
                if not log.get("ok", False) and action.action_type != "observe":
                    failed = True
                    break
        except Exception as exc:
            # Unexpected failure during action execution — map to failed
            # so the endpoint never returns a raw 500.
            replay_steps = [_step_log_to_replay_step(sl) for sl in step_logs]
            obs_summary = build_replay_observation_summary(
                learned_path_id=str(learned_path.id),
                steps=replay_steps,
            )
            return ReplayResult(
                learned_path_id=str(learned_path.id),
                source_run_id=learned_path.source_run_id,
                trust=str(learned_path.trust),
                status="failed",
                drift_status=precheck.drift_status,
                drift_reasons=[f"Action execution interrupted: {exc}"],
                warnings=precheck.warnings,
                stored_signature=stored_sig,
                current_signature=current_sig,
                steps=replay_steps,
                final_url=current_url,
                final_title=analysis.title if analysis else None,
                observation_summary=obs_summary,
            )

        final_url = runtime.current_url() if runtime.page else current_url
        final_title = runtime.current_title() if runtime.page else ""

        replay_steps = [_step_log_to_replay_step(sl) for sl in step_logs]
        obs_summary = build_replay_observation_summary(
            learned_path_id=str(learned_path.id),
            steps=replay_steps,
        )

        return ReplayResult(
            learned_path_id=str(learned_path.id),
            source_run_id=learned_path.source_run_id,
            trust=str(learned_path.trust),
            status="failed" if failed else "succeeded",
            drift_status=precheck.drift_status,
            warnings=precheck.warnings,
            stored_signature=stored_sig,
            current_signature=current_sig,
            steps=replay_steps,
            final_url=final_url,
            final_title=final_title,
            observation_summary=obs_summary,
        )

    finally:
        if runtime is not None:
            runtime.stop()
