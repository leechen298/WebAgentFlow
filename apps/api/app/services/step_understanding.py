"""Step understanding service (Phase 6D).

Analyzes a StepsContext and produces a structured StepUnderstanding result
by calling the LLM provider layer.

Usage:
    from app.services.step_understanding import generate_step_understanding

    result = generate_step_understanding(steps_context)
    if result["ok"]:
        understanding = result["understanding"]
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.locale import get_locale
from app.schemas.agent_input import StepsContext
from app.schemas.step_understanding import STEP_UNDERSTANDING_SCHEMA, StepUnderstanding
from app.services.llm_provider import build_request, generate_structured

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_BASE = """\
You are a user-behavior analyst. You receive a sequence of recorded user \
operation steps on a web page. Each step has an event type, target description, \
whether DOM changes were observed, mutation counts, and a human-readable summary.

Your job is to produce a structured understanding of how the page was used.

Rules:
- step_descriptions: provide ONE sentence for EVERY step (not just key steps). \
  Each entry has step_index and description. Be objective and behavior-focused. \
  For no-change steps, describe what the user did and note that no visible page \
  change was observed within the current observation window — never call it a \
  failure or error. Style reference (these examples show the expected tone and \
  detail level — your actual output must follow the language instruction below): \
  "Navigate to the activity creation page." / \
  "Enter the activity name in the name input field." / \
  "Click the save button, but no visible page change was observed."
- common_step_patterns: 1-3 short sentences describing the overall usage flow.
- likely_key_steps: the 1-5 most important steps. Include step_index (0-based).
- likely_expand_steps: steps that look like expand/toggle/open/switch actions. \
  Can be empty if none are apparent.
- likely_submit_steps: steps that look like save/submit/confirm/apply actions. \
  Can be empty if none are apparent.
- likely_no_change_steps: steps where has_changes is false. For each, provide a \
  likely_reason from: async_pending, precondition_unmet, already_active, \
  cross_frame, navigation, genuine_noop, unknown. \
  IMPORTANT: no-change does NOT mean failure. It may simply mean the change \
  happened outside the observation window or in a different frame.
- observed_change_patterns: 1-3 sentences on the most common change patterns \
  (e.g. "input events cause attribute changes", "clicks add child nodes").
- confidence_notes: only add when genuinely uncertain. Usually empty.\
"""

_LOCALE_INSTRUCTIONS: dict[str, str] = {
    "zh": "All text output MUST be in Chinese (简体中文).",
    "en": "All text output MUST be in English.",
    "ja": "All text output MUST be in Japanese (日本語).",
}


def _build_system_prompt(locale: str = "en") -> str:
    lang_line = _LOCALE_INSTRUCTIONS.get(locale, _LOCALE_INSTRUCTIONS["en"])
    return f"{_SYSTEM_PROMPT_BASE}\n- {lang_line}"


def build_step_understanding_prompt(steps_ctx: StepsContext) -> str:
    """Build the user prompt from a StepsContext.

    Exposed for testing — tests can verify prompt structure without
    calling the LLM.
    """
    parts = [
        f"Recording: {steps_ctx.recording_id}",
        f"Total steps: {steps_ctx.step_count}",
        f"Any mutations observed: {steps_ctx.has_mutations}",
    ]

    # Summary stats
    s = steps_ctx.summary
    parts.append(
        f"Steps with changes: {s.steps_with_changes}, "
        f"without changes: {s.steps_without_changes}"
    )
    if s.event_type_counts:
        counts_str = ", ".join(f"{k}: {v}" for k, v in sorted(s.event_type_counts.items()))
        parts.append(f"Event type breakdown: {counts_str}")

    # Steps list
    if steps_ctx.steps:
        parts.append("\nSteps:")
        for i, step in enumerate(steps_ctx.steps):
            line = (
                f"  [{i}] {step.get('event_type', '?')} → {step.get('target', '?')} | "
                f"changes: {step.get('has_changes', False)}"
            )
            if step.get("mutation_total", 0) > 0:
                line += f", mutations: {step['mutation_total']}"
                mt = step.get("mutation_types", {})
                if mt:
                    mt_str = ", ".join(f"{k}:{v}" for k, v in mt.items() if v)
                    if mt_str:
                        line += f" ({mt_str})"
            if step.get("change_area"):
                line += f", area: {step['change_area']}"
            if step.get("no_change_reason"):
                line += f", no_change_reason: {step['no_change_reason']}"
            if step.get("summary"):
                line += f"\n        summary: {step['summary']}"
            parts.append(line)
    else:
        parts.append("\n(no steps recorded)")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_step_understanding(
    steps_ctx: StepsContext,
    *,
    locale: str | None = None,
) -> dict[str, Any]:
    """Generate a structured step understanding from a StepsContext.

    Returns a dict with:
        - "ok": bool
        - "understanding": StepUnderstanding dict (when ok=True)
        - "error": error info (when ok=False)
        - "usage": token usage info
    """
    resolved_locale = locale or get_locale()
    prompt = build_step_understanding_prompt(steps_ctx)

    request = build_request(
        prompt,
        system=_build_system_prompt(resolved_locale),
        response_schema=STEP_UNDERSTANDING_SCHEMA,
    )

    resp = generate_structured(request)

    if not resp.ok:
        logger.warning("Step understanding failed: %s", resp.error)
        return {
            "ok": False,
            "understanding": None,
            "error": resp.error.model_dump() if resp.error else {"kind": "unknown", "message": "Unknown error"},
            "usage": resp.usage.model_dump(),
        }

    # Validate against Pydantic model
    try:
        validated = StepUnderstanding.model_validate(resp.parsed)
    except Exception as exc:
        logger.warning("Step understanding schema validation failed: %s", exc)
        return {
            "ok": False,
            "understanding": resp.parsed,
            "error": {"kind": "validation_error", "message": str(exc)},
            "usage": resp.usage.model_dump(),
        }

    return {
        "ok": True,
        "understanding": validated.model_dump(),
        "error": None,
        "usage": resp.usage.model_dump(),
    }
