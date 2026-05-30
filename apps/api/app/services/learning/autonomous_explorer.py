"""Autonomous explorer — full pipeline from URL to verified report.

Orchestrates the complete autonomous exploration flow:
  1. Navigate to URL
  2. Analyze page (discover interactive elements)
  3. Plan actions (based on analysis, not pre-written selectors)
  4. Execute actions (using Playwright)
  5. Generate structured report
  6. Run project-internal supervisor Agent for verification

No task definitions. No pre-written selectors. No site-specific logic.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from app.schemas.page_analysis import (
    AutonomousExplorationResult,
    DiscoveredElement,
    PageAnalysis,
)
from app.services.execution.action_executor import (
    execute_action,
    safe_screenshot,
)
from app.services.execution.execution_runtime import ExecutionRuntime
from app.services.learning.action_planner import plan_actions
from app.services.learning.page_analyzer import analyze_page

logger = logging.getLogger(__name__)


def _capture_final_state(runtime: ExecutionRuntime) -> dict[str, Any]:
    """Capture richer end-of-run DOM signals used by the spec comparator.

    Intentionally generic: body text, data-testid values, visible role=alert
    texts. Does NOT encode any site-specific logic — these are structural
    signals the spec can refer to.
    """
    page = runtime.page
    if page is None or page.is_closed():
        return {}
    try:
        return page.evaluate("""() => {
            const bodyText = document.body ? (document.body.innerText || '') : '';
            const testIds = Array.from(document.querySelectorAll('[data-testid]'))
                .map(el => el.getAttribute('data-testid'))
                .filter(Boolean);
            const alertTexts = Array.from(document.querySelectorAll('[role="alert"]'))
                .filter(el => {
                    const r = el.getBoundingClientRect();
                    const s = getComputedStyle(el);
                    return r.width > 0 && r.height > 0
                        && s.display !== 'none'
                        && s.visibility !== 'hidden';
                })
                .map(el => (el.innerText || '').trim())
                .filter(t => t.length > 0);
            return {
                body_text: bodyText.slice(0, 8000),
                body_text_length: bodyText.length,
                test_ids: testIds,
                alert_texts: alertTexts,
            };
        }""")
    except Exception as exc:
        logger.warning("Final-state capture failed: %s", exc)
        return {}


_ACTION_TYPES = ("fill", "click", "press")


def _assess_outcome(steps: list[dict[str, Any]]) -> tuple[str, str]:
    """Rule-based outcome verdict from step results.

    Returns (verdict, summary). Verdict is one of the shared
    OutcomeVerdict values (see schemas/page_analysis.py):
      - success: ≥1 state-changing action AND observable change (url/title/content)
      - partial_success: some action steps attempted but some failed
      - failure: no action steps executed, actions ok but no observable
        change, or blocked (CAPTCHA / login wall / error alert)
      - uncertain: signals ambiguous (should rarely fire from rule-based path)

    'success' explicitly cannot be returned when nothing happened.
    """
    # Partition steps: actions (fill/click/press) vs observe/other
    action_steps = [s for s in steps if s.get("action_type") in _ACTION_TYPES]

    # Case 1: no action steps planned or executed → failure
    if not action_steps:
        return (
            "failure",
            "No interactive action steps were planned or executed. "
            "The page analysis found no actionable target, or planning yielded only observation.",
        )

    failed = [s for s in action_steps if not s.get("ok", False)]
    ok_actions = [s for s in action_steps if s.get("ok", False)]

    # Case 2: all action steps failed → partial_success (mechanical
    # failure, not the wider goal-state failure that "failure" means)
    # — actually all failed is worse than partial, emit "failure" with
    # the explicit per-step error so the operator can dig in.
    if len(failed) == len(action_steps):
        errors = [s.get("error", "") or "(no error message)" for s in failed]
        return (
            "failure",
            f"All {len(action_steps)} action step(s) failed. First error: {errors[0][:120]}",
        )

    # Case 3: some actions failed but some succeeded → partial_success
    if failed:
        return (
            "partial_success",
            f"{len(failed)}/{len(action_steps)} action step(s) failed, "
            f"{len(ok_actions)} succeeded.",
        )

    # All actions succeeded. Now check for observable state change.
    state_changing = [s for s in action_steps if s.get("action_type") in ("click", "press")]
    url_changed = any(s.get("url_changed", False) for s in state_changing)
    title_changed = any(s.get("title_changed", False) for s in state_changing)

    # Consult observe signals for blocker detection
    observe = next(
        (s for s in reversed(steps) if s.get("action_type") == "observe"), None,
    )
    signals = (observe.get("result_signals") or {}) if observe else {}

    # SPA fix: clicking Sign in fires router navigation, but the
    # click step's url_after is captured BEFORE the SPA's async
    # router has pushed the new URL. The observe step (which waits)
    # is the first step that sees /dashboard. Fold the observe
    # step's url/title into the change detection so SPA flows don't
    # get mis-verdicted as no_progress just because no single click
    # step's before/after pair saw the update.
    if observe and state_changing:
        first_url = state_changing[0].get("url_before")
        observe_url = observe.get("url")
        if first_url and observe_url and observe_url != first_url:
            url_changed = True
        first_title = state_changing[0].get("title_before")
        observe_title = observe.get("title")
        if first_title and observe_title and observe_title != first_title:
            title_changed = True

    if signals.get("has_captcha"):
        return (
            "failure",
            "Actions executed but final page is a CAPTCHA / security verification.",
        )
    if signals.get("has_login_wall"):
        return (
            "failure",
            "Actions executed but final page is a login wall.",
        )

    # State-changing actions present but nothing actually changed → failure
    if state_changing and not url_changed and not title_changed:
        return (
            "failure",
            f"{len(state_changing)} submit/click/press step(s) executed "
            "but no URL or title change was observed.",
        )

    # Had no click/press at all (only fill) and no state change → failure
    if not state_changing:
        return (
            "failure",
            "Only fill actions were executed; no submit/click/press to trigger state change.",
        )

    # All ok and observable change happened → success
    changed_parts = []
    if url_changed:
        changed_parts.append("URL")
    if title_changed:
        changed_parts.append("title")
    return (
        "success",
        f"All {len(action_steps)} action step(s) succeeded and "
        f"{' and '.join(changed_parts)} changed.",
    )


# ───────────────────────────────────────────────────────────────────
# Public API
# ───────────────────────────────────────────────────────────────────

EventEmitter = Callable[[str, dict[str, Any]], None]


def _noop_emitter(_event: str, _data: dict[str, Any]) -> None:
    """Default emitter: does nothing. Preserves behavior for callers not using SSE."""


def run_autonomous_exploration(
    url: str,
    runtime: ExecutionRuntime,
    *,
    goal: str = "",
    fill_value: str = "",
    fill_values: dict[str, str] | None = None,
    toggle_values: dict[str, str] | None = None,
    scenario_name: str | None = None,
    scenario_description: str | None = None,
    language: str | None = None,
    event_emitter: EventEmitter | None = None,
) -> AutonomousExplorationResult:
    """Run the full autonomous exploration pipeline.

    Args:
        url: Target URL to explore.
        runtime: Playwright runtime (caller manages lifecycle).
        goal: Optional goal description.
        fill_value: Value for the primary input (single-field mode).
        fill_values: Multi-field values keyed by semantic role
            (username/password/email/text). Takes precedence over fill_value.
        toggle_values: Native toggle selections keyed by a group's
            semantic role (e.g. 'status') -> option value (e.g.
            'active'). Drives radio / checkbox groups via the planner's
            toggle_values path.
        scenario_name: Scenario key from the spec (e.g. ``no_match``).
            Passed to the supervisor so the LLM has operator-intent
            context instead of guessing from the raw step log.
        scenario_description: Free-form scenario description from
            the spec (e.g. "Type a value that matches no user; expect
            empty-state"). Pairs with scenario_name — the supervisor
            uses this to tell an intentional no-match scenario from a
            broken search.
        language: Preferred output language for the Supervisor Agent's
            LLM response (e.g. "en", "zh", "ja"). When None, the agent
            defaults to the page title's language.
        event_emitter: Optional callback invoked at each phase boundary
            with ``(event_type, data_dict)``. When None, runs silently —
            backward compatible with callers that want a single return value.

    Returns:
        AutonomousExplorationResult with analysis, execution, and
        supervisor verification.
    """
    emit: EventEmitter = event_emitter or _noop_emitter
    t0 = int(time.time() * 1000)

    # ── Step 1: Navigate ──
    emit("navigate_started", {"url": url})
    logger.info("Autonomous exploration: navigating to %s", url)
    runtime.navigate(url)
    time.sleep(1.5)
    emit("navigate_done", {
        "url": runtime.current_url() if runtime.page else url,
        "title": runtime.current_title() if runtime.page else "",
    })

    # ── Step 2: Analyze ──
    emit("analysis_started", {})
    logger.info("Autonomous exploration: analyzing page")
    analysis = analyze_page(runtime)
    logger.info(
        "Analysis: %d visible elements (fillable=%d, submit=%d, nav=%d)",
        analysis.total_visible, len(analysis.fillable),
        len(analysis.submit), len(analysis.navigation),
    )
    emit("analysis_done", {
        "total_visible": analysis.total_visible,
        "total_hidden": analysis.total_hidden,
        "counts": {
            "fillable": len(analysis.fillable),
            "submit": len(analysis.submit),
            "clickable": len(analysis.clickable),
            "navigation": len(analysis.navigation),
            "select": len(analysis.select),
            "toggle": len(analysis.toggle),
            "other": len(analysis.other),
        },
        "fillable": [e.model_dump() for e in analysis.fillable],
        "submit": [e.model_dump() for e in analysis.submit],
        "clickable": [e.model_dump() for e in analysis.clickable],
        "navigation": [e.model_dump() for e in analysis.navigation[:10]],
        "screenshot_ref": analysis.screenshot_ref,
    })

    # ── Step 3: Plan actions ──
    logger.info("Autonomous exploration: planning actions")
    planned = plan_actions(
        analysis,
        goal=goal,
        fill_value=fill_value,
        fill_values=fill_values,
        toggle_values=toggle_values,
    )
    analysis.recommended_actions = planned
    logger.info("Planned %d actions", len(planned))
    emit("plan_done", {
        "total_actions": len(planned),
        "actions": [a.model_dump() for a in planned],
    })

    # ── Step 4: Execute ──
    logger.info("Autonomous exploration: executing %d actions", len(planned))
    step_logs: list[dict[str, Any]] = []
    for action in planned:
        emit("step_started", {
            "step_index": action.step,
            "action_type": action.action_type,
            "target_selector": action.target_selector,
            "target_description": action.target_description,
            "value": action.value,
        })
        logger.info("  Step %d: %s %s", action.step, action.action_type, action.target_selector)
        step_log = execute_action(action, runtime)
        step_logs.append(step_log)

        if not step_log.get("ok", False) and action.action_type != "observe":
            logger.warning("  Step %d failed: %s", action.step, step_log.get("error"))
        emit("step_done", step_log)

    # ── Step 5: Final state ──
    final_url = runtime.current_url() if runtime.page else ""
    final_title = runtime.current_title() if runtime.page else ""
    final_screenshot = safe_screenshot(runtime)
    final_state = _capture_final_state(runtime)

    elapsed = int(time.time() * 1000) - t0
    verdict, summary = _assess_outcome(step_logs)
    logger.info("Self-assessed verdict: %s — %s", verdict, summary)
    emit("self_assessment_done", {
        "verdict": verdict,
        "summary": summary,
        "final_url": final_url,
        "final_title": final_title,
        "final_screenshot_ref": final_screenshot,
        "final_state": final_state,
    })

    # ── Step 6: Supervisor verification (project-internal Agent) ──
    supervisor_output = _run_supervisor(
        analysis, step_logs, verdict, summary, final_url, final_title, elapsed,
        scenario_name=scenario_name,
        scenario_description=scenario_description,
        language=language,
        final_state=final_state,
    )
    emit("supervisor_done", supervisor_output or {})

    return AutonomousExplorationResult(
        page_analysis=analysis,
        steps=step_logs,
        total_steps=len(step_logs),
        elapsed_ms=elapsed,
        final_url=final_url,
        final_title=final_title,
        final_screenshot_ref=final_screenshot,
        final_state=final_state,
        verdict=verdict,
        success=(verdict == "success"),
        summary=summary,
        supervisor=supervisor_output,
    )


_LLM_URL_MAX = 200          # truncate URLs passed to LLM
_LLM_ELEMENT_TOPN = 10      # cap element lists sent to LLM


def _trim_url(url: str | None) -> str | None:
    """Truncate long URLs for LLM consumption — only keep origin + first query params."""
    if url is None:
        return None
    if len(url) <= _LLM_URL_MAX:
        return url
    return url[:_LLM_URL_MAX] + f"...[truncated {len(url) - _LLM_URL_MAX} chars]"


def _compact_element(e: DiscoveredElement) -> dict[str, Any]:
    """Compact element representation for LLM payload."""
    return {
        "selector": e.selector,
        "tag": e.tag,
        "reason": e.reason,
        "text": (e.text or "")[:40],
        "placeholder": e.placeholder,
    }


_FINAL_STATE_BODY_TEXT_MAX = 2000
_FINAL_STATE_ALERT_TEXT_MAX = 400


def _compact_final_state(fs: dict[str, Any] | None) -> dict[str, Any] | None:
    """Trim final_state for the LLM prompt.

    final_state carries what actually ended up on the page after the
    last action — ``alert_texts`` (DOM nodes with role=alert), visible
    ``body_text``, and any ``test_ids``. The LLM needs these to verify
    scenario requirements like "surface role=alert" without hedging.
    Cap string sizes so a chatty page can't blow the context window.
    """
    if not fs:
        return None
    body_text = (fs.get("body_text") or "")
    if len(body_text) > _FINAL_STATE_BODY_TEXT_MAX:
        body_text = body_text[:_FINAL_STATE_BODY_TEXT_MAX] + "…[truncated]"
    alert_texts_raw = fs.get("alert_texts") or []
    alert_texts = [
        (t if len(t) <= _FINAL_STATE_ALERT_TEXT_MAX else t[:_FINAL_STATE_ALERT_TEXT_MAX] + "…")
        for t in alert_texts_raw
        if isinstance(t, str)
    ]
    return {
        "body_text": body_text,
        "body_text_length": fs.get("body_text_length"),
        "alert_texts": alert_texts,
        "test_ids": fs.get("test_ids") or [],
    }


_LANGUAGE_NAMES: dict[str, str] = {
    "en": "English",
    "zh": "Chinese (Simplified)",
    "zh-cn": "Chinese (Simplified)",
    "zh-tw": "Chinese (Traditional)",
    "zh-hk": "Chinese (Traditional)",
    "ja": "Japanese",
    "ja-jp": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
}


def _language_name(code: str | None) -> str | None:
    """Map a BCP-47-ish locale code to a human-readable language name for the LLM."""
    if not code:
        return None
    return _LANGUAGE_NAMES.get(code.lower().strip())


def _build_supervisor_system_prompt(language_clause: str) -> str:
    """Assemble the supervisor LLM system prompt.

    New contract (2026-04-20): the LLM reports observation atoms, not
    a verdict. The mechanical ``verdict`` is derived in code from the
    atoms by ``supervisor_observations.derive_verdict`` — this prompt
    deliberately contains NO verdict rubric, NO success/failure
    definitions, NO few-shot examples of "this scenario → this
    verdict". The LLM's job ends at "describe the page".

    See project_supervisor_verdict_override_plan.md for the rationale:
    a reasoning model that holds the verdict pen can always talk
    itself out of a stated rule; taking the pen away removes that
    failure mode structurally.
    """
    return f"""\
You are a verification agent inside the WebAgentFlow project. You review
the results of an AUTONOMOUS web exploration run — one where the system
discovered page elements on its own, planned actions, and executed them.

Your job is NOT to judge whether the run passed or failed. That
judgement is computed downstream by project code from the observations
you report. Your job is to describe the final page state accurately.

Return the structured observation atoms defined by the response schema.
Every atom is either a direct reading of the page state, or (for
``scenario_goal_observed``) an "did this scenario's subject event
happen" observation with a short piece of quoted evidence.

Rules for filling the atoms:

* ``did_navigate`` — true iff ``final_url_path`` differs from the URL
  path at the start of the LAST user-intent action (login submit,
  filter apply, …). A hash-only or query-only change still counts.
  Trust the URL fields; don't guess.

* ``final_url_path`` — the path component of ``execution.final_url``,
  stripped of query and fragment. Copy, don't invent.

* ``did_show_error`` — true iff the page rendered an error surface
  carrying non-empty text. ``final_state.alert_texts`` is the primary
  signal; anything listed there that reads like an error (incorrect /
  invalid / denied / failed / 错误 / 失败 / 无效 / etc.) qualifies.
  A neutral status banner ("Results filtered") is NOT an error.

* ``error_texts`` — copy the raw text(s) from each error surface.
  Empty list when ``did_show_error`` is false.

* ``form_state_after`` — if the page has a form, whether its fields
  were cleared (``reset``), still show the submitted values
  (``persisted``), or you cannot tell (``unclear``). If the final
  page has no form, use ``no_form``.

* ``list_row_count`` — if the final page renders a data list or
  table, the number of visible rows. Use null if there is no list.
  Count zero when the list renders with an empty state — zero rows
  is a valid observation, not "no list".

* ``scenario_goal_observed`` — an interpretive observation, not a
  verdict. Read ``execution.scenario_description`` carefully:
    - If the scenario describes a POSITIVE goal ("log in", "filter
      to active users"), set this to true when that positive outcome
      is visible (reached destination, filtered list rendered, etc.).
    - If the scenario describes a NEGATIVE goal ("verify bad
      credentials stay blocked", "verify the form rejects empty
      input"), set this to true when the block + whatever UI the
      scenario names (error alert, warning icon, refusal to submit)
      is visible.
    In both cases "true" means "the thing the scenario is checking
    for actually happened". The downstream code reconciles
    scenario_goal_observed against ``expected_verdict`` /
    ``expected_verdict_not`` — you do NOT.

* ``scenario_goal_evidence`` — one-sentence quote or reference from
  ``final_state`` (alert text, URL path, test_id, body text excerpt)
  that justifies ``scenario_goal_observed``. Empty string when the
  observation is false.

* ``anomalies`` — things outside the atoms that a human should
  notice: a captcha rendered, an analytics banner covered the submit
  button, a third-party iframe loaded late. Keep it short.

* ``suggestions`` — optional. Skip unless you have a concrete fix.

* ``summary`` — 2-4 plain sentences recapping the run. No verdict
  word; just what happened.

Few-shot observation examples (illustrative, not exhaustive):

Example A — form submission reached the expected destination:
```
{{
  "did_navigate": true, "final_url_path": "/target",
  "did_show_error": false, "error_texts": [],
  "form_state_after": "no_form", "list_row_count": 8,
  "scenario_goal_observed": true,
  "scenario_goal_evidence": "Reached /target with 8 rows rendered.",
  "summary": "Form accepted; expected list rendered."
}}
```

Example B — invalid form input stayed on the same page with alert:
```
{{
  "did_navigate": false, "final_url_path": "/form",
  "did_show_error": true, "error_texts": ["Invalid input"],
  "form_state_after": "persisted", "list_row_count": null,
  "scenario_goal_observed": true,
  "scenario_goal_evidence": "role=alert with Invalid input; still on /form.",
  "summary": "Input rejected; form retained values."
}}
```

Example C — filter applied but result list is empty, scenario expects 0 rows:
```
{{
  "did_navigate": false, "final_url_path": "/target",
  "did_show_error": false, "error_texts": [],
  "form_state_after": "no_form", "list_row_count": 0,
  "scenario_goal_observed": true,
  "scenario_goal_evidence": "no-match test_id present; 0 rows.",
  "summary": "Filter produced zero rows; empty-state UI visible."
}}
```

Do NOT output ``verdict`` / ``confidence`` / ``should_save_path`` —
those fields are not in the response schema and will be rejected.

{language_clause}\
"""


def _run_supervisor(
    analysis: PageAnalysis,
    steps: list[dict[str, Any]],
    verdict: str,
    summary: str,
    final_url: str,
    final_title: str,
    elapsed_ms: int,
    *,
    scenario_name: str | None = None,
    scenario_description: str | None = None,
    language: str | None = None,
    final_state: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Run the project's internal supervisor Agent on the exploration results.

    Payload is deliberately trimmed to avoid LLM provider failures:
      - Hidden elements only as counts
      - Element lists capped at top-N
      - Long URLs truncated
      - No screenshot bytes (refs only)

    ``scenario_name`` / ``scenario_description`` — when provided (spec-driven
    runs), included in the LLM prompt so it knows the operator's intent.
    Without this, the LLM has to infer from input values whether e.g. a
    zero-result filter was a deliberate no-match test or a broken search,
    and it hedges to ``partial_success``.

    ``language`` — when provided, instructs the LLM to reply in that language
    regardless of the page's content language. Intended to track the UI locale
    so the user sees the agent's output in their own language.
    """
    import json

    from app.schemas.llm import LlmMessage, LlmRequest
    from app.services.learning.supervisor_observations import (
        SUPERVISOR_OBSERVATIONS_SCHEMA,
        build_supervisor_output,
        parse_observations_lax,
    )
    from app.services.llm_provider import generate_structured

    # Build prompt from autonomous exploration data — trimmed.
    prompt_data: dict[str, Any] = {
        "exploration_type": "autonomous",
        "page_analysis": {
            "url": _trim_url(analysis.url),
            "title": analysis.title,
            "counts": {
                "visible": analysis.total_visible,
                "hidden": analysis.total_hidden,
                "fillable": len(analysis.fillable),
                "submit": len(analysis.submit),
                "clickable": len(analysis.clickable),
                "navigation": len(analysis.navigation),
                "select": len(analysis.select),
                "toggle": len(analysis.toggle),
                "other": len(analysis.other),
            },
            "fillable_top": [_compact_element(e) for e in analysis.fillable[:_LLM_ELEMENT_TOPN]],
            "submit_top": [_compact_element(e) for e in analysis.submit[:_LLM_ELEMENT_TOPN]],
            "clickable_top": [_compact_element(e) for e in analysis.clickable[:_LLM_ELEMENT_TOPN]],
            # hidden_interactive: only count, never details
        },
        "execution": {
            "verdict": verdict,
            "summary": summary,
            "total_steps": len(steps),
            "final_url": _trim_url(final_url),
            "final_title": final_title,
            "elapsed_ms": elapsed_ms,
            # Operator intent. Present only for spec-driven runs — ad-hoc
            # runs without a spec / scenario get ``None`` here, and the
            # supervisor treats that as "intent unspecified, infer from
            # inputs". When present, the LLM should read
            # ``scenario_description`` as the authoritative task intent
            # before interpreting result_signals.
            "scenario_name": scenario_name,
            "scenario_description": scenario_description,
        },
        "steps": [
            {
                "step_index": s.get("step_index"),
                "action_type": s.get("action_type"),
                "target": (s.get("target_description") or s.get("target_selector") or "")[:120],
                "value": s.get("value"),
                "ok": s.get("ok"),
                "error": (s.get("error") or "")[:200] or None,
                "url_before": _trim_url(s.get("url_before")),
                "url_after": _trim_url(s.get("url_after")),
                "url_changed": s.get("url_changed"),
                "title_after": s.get("title_after"),
                "result_signals": s.get("result_signals"),
                # screenshot_ref: intentionally omitted — LLM doesn't consume images here
            }
            for s in steps
        ],
        # Final-page signals the LLM needs to make a high-confidence
        # judgement. Historically we only included per-step
        # result_signals (has_login_wall / result_row_count / etc.),
        # but those are pre-aggregated flags — they can't prove e.g.
        # that the invalid_credentials scenario's role=alert actually
        # surfaced. The full final_state carries alert_texts and
        # test_ids collected from the DOM after the last action, which
        # lets the LLM verify "surface role=alert" directly instead of
        # hedging to "uncertain" for lack of evidence. Kept below a
        # hard byte cap so a chatty page can't blow the context window.
        "final_state": _compact_final_state(final_state),
    }

    language_name = _language_name(language)
    language_clause = (
        f"Write ALL natural-language fields (summary, anomalies, "
        f"suggestions, step_assessments.note) in {language_name}. "
        f"This overrides the page-title language rule."
        if language_name
        else "Respond in the same language as the page title."
    )

    system_prompt = _build_supervisor_system_prompt(language_clause)

    prompt_content = json.dumps(prompt_data, ensure_ascii=False, indent=2)
    request = LlmRequest(
        system=system_prompt,
        messages=[LlmMessage(role="user", content=prompt_content)],
        response_schema=SUPERVISOR_OBSERVATIONS_SCHEMA,
        temperature=0.3,
        metadata={"source": "autonomous_exploration_supervisor"},
    )

    # One retry on transient / retryable errors (rate_limit, timeout,
    # 5xx provider errors). Tight sequential usage — 5 scenarios back-
    # to-back in the exploration runner — routinely triggered a single
    # blip that a one-shot retry covers without re-exercising Playwright.
    # The delay is short because rate-limit windows on our providers
    # tend to be sub-second; long back-off here would balloon run time
    # without meaningfully improving hit rate.
    import time as _time

    last_error_kind: str | None = None
    last_error_message: str | None = None
    attempts = 2
    for attempt in range(attempts):
        try:
            response = generate_structured(request)
            if response.ok and response.parsed:
                # Parse observation atoms laxly — a missing optional
                # atom becomes the conservative default rather than a
                # Pydantic crash that forces the whole supervisor call
                # into fallback. The partial flag rides through to
                # pass_gate so operators can see "LLM answered, but
                # some atoms were missing" as unverified.
                obs, partial = parse_observations_lax(response.parsed)
                result = build_supervisor_output(
                    obs,
                    partial_parse=partial,
                    thinking=response.thinking,
                    model=response.model,
                )
                logger.info(
                    "Supervisor derived verdict=%s partial=%s (attempt %d)",
                    result["verdict"], partial, attempt + 1,
                )
                return result

            # Non-OK response — capture error for potential retry / fallback.
            err = response.error
            last_error_kind = err.kind if err else "unknown"
            last_error_message = err.message if err else "unknown"
            retryable = bool(err and err.retryable)
            logger.warning(
                "Supervisor LLM call failed (attempt %d/%d): kind=%s retryable=%s msg=%s",
                attempt + 1, attempts, last_error_kind, retryable, last_error_message,
            )
            if not retryable or attempt == attempts - 1:
                break
            _time.sleep(0.5)
        except Exception as exc:
            last_error_kind = "exception"
            last_error_message = str(exc)
            logger.warning("Supervisor call raised (attempt %d/%d): %s",
                           attempt + 1, attempts, exc)
            # Exceptions are conservatively treated as retryable once —
            # a transient httpx.ConnectError is the common case.
            if attempt == attempts - 1:
                break
            _time.sleep(0.5)

    # Fallback: rule-based, tagged with the underlying error kind so
    # the UI / CLI can distinguish a real LLM verdict from a fallback.
    return _fallback_supervisor(
        steps, verdict, summary,
        error_kind=last_error_kind,
    )


def _fallback_supervisor(
    steps: list[dict[str, Any]],
    self_verdict: str,
    summary: str,
    *,
    error_kind: str | None = None,
) -> dict[str, Any]:
    """Rule-based fallback when LLM is unavailable.

    Rule-side and supervisor-side now share one OutcomeVerdict
    vocabulary (success / partial_success / failure / uncertain), so
    the fallback just passes self_verdict through — no cross-ontology
    mapping is needed. The only nudge is downgrading an otherwise-
    success verdict to partial_success when anomalies are present,
    which is a stricter check the LLM would usually do on its own.

    ``error_kind`` — optional tag from the failed LLM call
    (``rate_limit`` / ``timeout`` / ``provider_error`` / ``parse_error`` /
    ``auth_error`` / ``exception``). Included in both the summary
    suffix and the returned ``_supervisor_error_kind`` field so the
    operator can tell a transient blip from a persistent misconfig.
    """
    step_assessments = []
    for s in steps:
        if s.get("ok"):
            status = "ok"
            note = "Completed"
        else:
            status = "failed"
            note = (s.get("error") or "Unknown error")[:100]
        step_assessments.append({
            "step_index": s.get("step_index", 0),
            "status": status,
            "note": note,
        })

    # Deliberately NO anomaly detection here. Earlier versions tried
    # to flag ``has_login_wall`` / ``has_captcha`` as anomalies based
    # on the final observe's result_signals, but fallback has no
    # scenario context — for a scenario like ``invalid_credentials``
    # the login wall IS the expected outcome, and "Login wall detected"
    # shows up in the UI as if something went wrong. The rule-side
    # ``_assess_outcome`` already folds these signals into the verdict
    # (failure when login_wall persists on a positive-path scenario);
    # duplicating that as an anomaly string is either redundant or
    # actively misleading.
    #
    # Pass self_verdict straight through — shared vocabulary means no
    # translation. Guard against unexpected values (future-proofing).
    verdict = self_verdict if self_verdict in (
        "success", "partial_success", "failure", "uncertain",
    ) else "uncertain"

    # Deliberately leave confidence unset: ``confidence`` is an LLM
    # self-assessment signal (high/medium/low), and a fallback response
    # has no LLM self-assessment. Reporting "low" here was conflating
    # two different states — "LLM said it isn't confident" vs "LLM
    # never produced a verdict" — which made the UI indistinguishable
    # between those two cases. Downstream code should key off
    # ``_supervisor_source`` + ``_supervisor_error_kind`` to render
    # the fallback state.
    suffix = f" [fallback: {error_kind or 'LLM unavailable'}]"
    return {
        "verdict": verdict,
        "confidence": None,
        "summary": summary + suffix,
        "step_assessments": step_assessments,
        "anomalies": [],
        "suggestions": [],
        "should_save_path": verdict == "success",
        # Fallback has no observations — the LLM never ran. Downstream
        # (pass_gate, UI) treats the absence of observations plus
        # _supervisor_source=="fallback" as "unverified", same as a
        # partial-parse LLM response.
        "observations": None,
        "_supervisor_partial_parse": False,
        "_supervisor_source": "fallback",
        "_supervisor_error_kind": error_kind,
    }
