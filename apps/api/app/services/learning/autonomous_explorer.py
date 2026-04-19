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
    PlannedAction,
)
from app.services.execution.execution_runtime import ExecutionRuntime
from app.services.learning.action_planner import plan_actions
from app.services.learning.page_analyzer import analyze_page

logger = logging.getLogger(__name__)


def _execute_step(
    action: PlannedAction,
    runtime: ExecutionRuntime,
) -> dict[str, Any]:
    """Execute a single planned action and return the step log."""
    page = runtime.page
    ts = int(time.time() * 1000)

    step_log: dict[str, Any] = {
        "step_index": action.step,
        "action_type": action.action_type,
        "target_selector": action.target_selector,
        "target_description": action.target_description,
        "value": action.value,
        "plan_reason": action.reason,
        "timestamp_ms": ts,
    }

    if action.action_type == "observe":
        return _observe_step(step_log, runtime)

    if page is None or page.is_closed():
        step_log["ok"] = False
        step_log["error"] = "No page available"
        return step_log

    # Capture before state
    before_url = page.url
    before_title = page.title()

    try:
        locator = page.locator(action.target_selector)

        # Verify element exists and is visible
        count = locator.count()
        if count == 0:
            step_log["ok"] = False
            step_log["error"] = f"Selector '{action.target_selector}' matched 0 elements"
            step_log["screenshot_ref"] = _safe_screenshot(runtime)
            return step_log

        step_log["matched_count"] = count

        if action.action_type == "fill":
            locator.first.wait_for(state="visible", timeout=5000)
            locator.first.fill(action.value or "")
            time.sleep(0.5)
            step_log["ok"] = True
            step_log["actual_value"] = locator.first.input_value()

        elif action.action_type == "click":
            locator.first.wait_for(state="visible", timeout=5000)
            locator.first.click()
            time.sleep(2.0)  # Wait for navigation / page change
            step_log["ok"] = True

        elif action.action_type == "press":
            locator.first.wait_for(state="visible", timeout=5000)
            locator.first.press(action.value or "Enter")
            time.sleep(2.0)
            step_log["ok"] = True

        else:
            step_log["ok"] = False
            step_log["error"] = f"Unknown action type: {action.action_type}"
            return step_log

    except Exception as exc:
        step_log["ok"] = False
        step_log["error"] = str(exc)[:300]
        step_log["screenshot_ref"] = _safe_screenshot(runtime)
        return step_log

    # Capture after state
    after_url = page.url
    after_title = page.title()
    step_log["url_before"] = before_url
    step_log["url_after"] = after_url
    step_log["title_before"] = before_title
    step_log["title_after"] = after_title
    step_log["url_changed"] = after_url != before_url
    step_log["title_changed"] = after_title != before_title
    step_log["screenshot_ref"] = _safe_screenshot(runtime)

    return step_log


def _observe_step(
    step_log: dict[str, Any],
    runtime: ExecutionRuntime,
) -> dict[str, Any]:
    """Capture final page state without performing any action."""
    page = runtime.page
    time.sleep(2.0)  # Wait for any pending navigation

    step_log["ok"] = True
    if page and not page.is_closed():
        step_log["url"] = page.url
        step_log["title"] = page.title()

        # Discover elements on the result page to check for content
        try:
            result_signals = page.evaluate("""() => {
                const signals = {};

                // Count real data rows.
                //  - <tbody><tr>: standard HTML tables (Ant Table, plain tables)
                //  - [role="row"]: ARIA grids, excluding rows that hold a
                //    column header (i.e. thead analogues)
                // Deliberately narrow — the previous broad matcher
                // ([class*=result], [class*=search], main, article) was
                // counting structural containers like .search-card and
                // ant-select internals, yielding inflated numbers
                // that had no relation to "how many results are shown".
                let rowCount = 0;
                for (const tr of document.querySelectorAll('tbody tr')) {
                    // Skip rows marked as group headers or placeholders.
                    if (tr.getAttribute('aria-hidden') === 'true') continue;
                    rowCount++;
                }
                for (const row of document.querySelectorAll('[role="row"]')) {
                    // Header rows contain a columnheader; skip them.
                    if (row.querySelector('[role="columnheader"]')) continue;
                    // Don't double-count <tr> that also has role="row".
                    if (row.tagName === 'TR' && row.closest('tbody')) continue;
                    rowCount++;
                }
                signals.result_row_count = rowCount;

                signals.has_captcha = !!(
                    document.title.match(/验证|captcha|challenge|security/i)
                    || document.URL.match(/captcha|verify|sorry|challenge/i)
                );
                signals.has_login_wall = !!(
                    document.title.match(/登录|login|sign.?in/i)
                    || document.querySelector('[class*=login-wall], [class*=login-modal]')
                );
                signals.visible_text_length = document.body
                    ? document.body.innerText.length : 0;
                return signals;
            }""")
            step_log["result_signals"] = result_signals
        except Exception:
            pass

    step_log["screenshot_ref"] = _safe_screenshot(runtime)
    return step_log


def _safe_screenshot(runtime: ExecutionRuntime) -> str | None:
    """Take a screenshot, return path or None on failure."""
    try:
        return runtime.screenshot()
    except Exception:
        return None


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

    Returns (verdict, summary). Verdict is one of:
      - success: ≥1 state-changing action AND observable change (url/title/content)
      - incomplete: some action steps attempted but some failed
      - no_progress: no action steps executed, OR actions ok but no observable change
      - uncertain: signals ambiguous (should rarely fire from rule-based path)

    'success' explicitly cannot be returned when nothing happened.
    """
    # Partition steps: actions (fill/click/press) vs observe/other
    action_steps = [s for s in steps if s.get("action_type") in _ACTION_TYPES]

    # Case 1: no action steps planned or executed → no_progress
    if not action_steps:
        return (
            "no_progress",
            "No interactive action steps were planned or executed. "
            "The page analysis found no actionable target, or planning yielded only observation.",
        )

    failed = [s for s in action_steps if not s.get("ok", False)]
    ok_actions = [s for s in action_steps if s.get("ok", False)]

    # Case 2: all action steps failed → incomplete (all failed is still incomplete, not success)
    if len(failed) == len(action_steps):
        errors = [s.get("error", "") or "(no error message)" for s in failed]
        return (
            "incomplete",
            f"All {len(action_steps)} action step(s) failed. First error: {errors[0][:120]}",
        )

    # Case 3: some actions failed but some succeeded → incomplete
    if failed:
        return (
            "incomplete",
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

    if signals.get("has_captcha"):
        return (
            "no_progress",
            "Actions executed but final page is a CAPTCHA / security verification.",
        )
    if signals.get("has_login_wall"):
        return (
            "no_progress",
            "Actions executed but final page is a login wall.",
        )

    # State-changing actions present but nothing actually changed → no_progress
    if state_changing and not url_changed and not title_changed:
        return (
            "no_progress",
            f"{len(state_changing)} submit/click/press step(s) executed "
            "but no URL or title change was observed.",
        )

    # Had no click/press at all (only fill) and no state change → no_progress
    if not state_changing:
        return (
            "no_progress",
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

    # ── Phase 1: Navigate ──
    emit("navigate_started", {"url": url})
    logger.info("Autonomous exploration: navigating to %s", url)
    runtime.navigate(url)
    time.sleep(1.5)
    emit("navigate_done", {
        "url": runtime.current_url() if runtime.page else url,
        "title": runtime.current_title() if runtime.page else "",
    })

    # ── Phase 2: Analyze ──
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

    # ── Phase 3: Plan ──
    logger.info("Autonomous exploration: planning actions")
    planned = plan_actions(
        analysis, goal=goal, fill_value=fill_value, fill_values=fill_values,
    )
    analysis.recommended_actions = planned
    logger.info("Planned %d actions", len(planned))
    emit("plan_done", {
        "total_actions": len(planned),
        "actions": [a.model_dump() for a in planned],
    })

    # ── Phase 4: Execute ──
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
        step_log = _execute_step(action, runtime)
        step_logs.append(step_log)

        if not step_log.get("ok", False) and action.action_type != "observe":
            logger.warning("  Step %d failed: %s", action.step, step_log.get("error"))
        emit("step_done", step_log)

    # ── Phase 5: Final state ──
    final_url = runtime.current_url() if runtime.page else ""
    final_title = runtime.current_title() if runtime.page else ""
    final_screenshot = _safe_screenshot(runtime)
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

    # ── Phase 6: Supervisor verification (project-internal Agent) ──
    supervisor_output = _run_supervisor(
        analysis, step_logs, verdict, summary, final_url, final_title, elapsed,
        language=language,
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


def _run_supervisor(
    analysis: PageAnalysis,
    steps: list[dict[str, Any]],
    verdict: str,
    summary: str,
    final_url: str,
    final_title: str,
    elapsed_ms: int,
    *,
    language: str | None = None,
) -> dict[str, Any] | None:
    """Run the project's internal supervisor Agent on the exploration results.

    Payload is deliberately trimmed to avoid LLM provider failures:
      - Hidden elements only as counts
      - Element lists capped at top-N
      - Long URLs truncated
      - No screenshot bytes (refs only)

    ``language`` — when provided, instructs the LLM to reply in that language
    regardless of the page's content language. Intended to track the UI locale
    so the user sees the agent's output in their own language.
    """
    import json

    from app.schemas.llm import LlmMessage, LlmRequest
    from app.services.learning.exploration_supervisor import SUPERVISOR_RESPONSE_SCHEMA
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
    }

    language_name = _language_name(language)
    language_clause = (
        f"Write ALL natural-language fields (summary, anomalies, "
        f"suggestions, step_assessments.note) in {language_name}. "
        f"This overrides the page-title language rule."
        if language_name
        else "Respond in the same language as the page title."
    )

    system_prompt = f"""\
You are a verification agent inside the WebAgentFlow project. You review
the results of an AUTONOMOUS web exploration run — one where the system
discovered page elements on its own (no pre-written selectors), planned
actions, and executed them.

Your job:
1. Assess whether the page analysis was accurate (did it find the right elements?)
2. Assess whether the action plan was reasonable
3. Assess whether each execution step succeeded or failed
4. Determine if the overall goal was achieved
5. Identify anomalies (CAPTCHA, login wall, false positives, etc.)
6. Provide suggestions for improving the system

Be concise, specific, and fact-based. Look at URLs, titles, and result_signals
to determine the real outcome — don't just trust the self-reported success flag.

{language_clause}\
"""

    prompt_content = json.dumps(prompt_data, ensure_ascii=False, indent=2)
    request = LlmRequest(
        system=system_prompt,
        messages=[LlmMessage(role="user", content=prompt_content)],
        response_schema=SUPERVISOR_RESPONSE_SCHEMA,
        temperature=0.3,
        metadata={"source": "autonomous_exploration_supervisor"},
    )

    try:
        response = generate_structured(request)
        if response.ok and response.parsed:
            logger.info("Supervisor verdict: %s", response.parsed.get("verdict"))
            # Expose the model's <think> reasoning trace for UI transparency.
            # Key is `_thinking` (underscore-prefixed) so schema-strict consumers
            # can ignore it; Pydantic SupervisorAssessment uses
            # **dict-to-kwargs construction, so this would normally be rejected
            # — but the frontend receives the raw dict via SSE and renders it.
            result = dict(response.parsed)
            if response.thinking:
                result["_thinking"] = response.thinking
            if response.model:
                result["_model"] = response.model
            return result

        logger.warning("Supervisor LLM call failed: %s",
                       response.error.message if response.error else "unknown")
    except Exception as exc:
        logger.warning("Supervisor call raised: %s", exc)

    # Fallback: rule-based
    return _fallback_supervisor(steps, verdict, summary)


def _fallback_supervisor(
    steps: list[dict[str, Any]],
    self_verdict: str,
    summary: str,
) -> dict[str, Any]:
    """Rule-based fallback when LLM is unavailable.

    Maps the self-assessed verdict (success/incomplete/no_progress/uncertain)
    to the supervisor verdict space (success/partial_success/failure/uncertain).
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

    # Detect anomalies
    anomalies = []
    observe = next(
        (s for s in reversed(steps) if s.get("action_type") == "observe"), None,
    )
    if observe:
        signals = observe.get("result_signals") or {}
        if signals.get("has_captcha"):
            anomalies.append("CAPTCHA / security verification detected")
        if signals.get("has_login_wall"):
            anomalies.append("Login wall detected")

    # Map self-verdict → supervisor verdict
    verdict_map = {
        "success": "success",
        "incomplete": "partial_success",
        "no_progress": "failure",
        "uncertain": "uncertain",
    }
    verdict = verdict_map.get(self_verdict, "uncertain")
    if anomalies and verdict == "success":
        verdict = "partial_success"

    return {
        "verdict": verdict,
        "confidence": "medium" if not anomalies else "high",
        "summary": summary + (" [fallback: LLM unavailable]"),
        "step_assessments": step_assessments,
        "anomalies": anomalies,
        "suggestions": [],
        "should_save_path": (verdict == "success") and not anomalies,
    }
