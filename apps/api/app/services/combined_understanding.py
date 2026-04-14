"""Combined understanding service (Phase 6E).

Rule-based synthesis of PageUnderstanding (6C) + StepUnderstanding (6D)
into a unified AgentPageUnderstanding.

Structural fields are deterministic merges — no LLM call needed.
Description fields (page_description, operation_description) use a
lightweight LLM call to produce locale-aware natural language.

Usage:
    from app.services.combined_understanding import build_agent_page_understanding

    result = build_agent_page_understanding(page_understanding, step_understanding)
"""

from __future__ import annotations

import json
import logging

from app.core.locale import get_locale
from app.schemas.combined_understanding import (
    AgentPageUnderstanding,
    ExecutionNote,
    KeyStepSummary,
)
from app.schemas.page_understanding import PageUnderstanding
from app.schemas.step_understanding import StepUnderstanding
from app.services.llm_provider import build_request, generate_structured

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _text_overlap(a: str, b: str, min_len: int = 2) -> bool:
    """Check if two strings share a meaningful substring overlap."""
    a_lower, b_lower = a.lower(), b.lower()
    if a_lower in b_lower or b_lower in a_lower:
        return True
    # Check if any contiguous substring of length >= min_len overlaps
    shorter, longer = (a_lower, b_lower) if len(a_lower) <= len(b_lower) else (b_lower, a_lower)
    for length in range(len(shorter), min_len - 1, -1):
        for start in range(len(shorter) - length + 1):
            if shorter[start:start + length] in longer:
                return True
    return False


def _enrich_regions(
    page: PageUnderstanding,
    steps: StepUnderstanding,
) -> list[dict]:
    """Copy regions from 6C, annotate with step activity from 6D."""
    # Collect change_area-like mentions from key steps
    step_targets: list[str] = []
    for s in steps.likely_key_steps:
        step_targets.append(s.target)
    for s in steps.likely_expand_steps:
        step_targets.append(s.target)
    for s in steps.likely_submit_steps:
        step_targets.append(s.target)

    regions = []
    for r in page.primary_regions:
        region_dict = {"name": r.name, "role": r.role}
        # Check if any step target has meaningful overlap with region name
        # Use min_len=3 to avoid false positives on short CJK fragments
        has_activity = any(
            _text_overlap(r.name, t, min_len=3)
            for t in step_targets if t
        )
        if has_activity:
            region_dict["step_activity"] = True
        regions.append(region_dict)

    return regions


def _enrich_actions(
    page: PageUnderstanding,
    steps: StepUnderstanding,
) -> list[dict]:
    """Copy actions from 6C, mark which ones were observed in steps."""
    # Collect step targets for matching
    step_target_set = set()
    for s in steps.likely_key_steps:
        step_target_set.add(s.target.lower())
    for s in steps.likely_submit_steps:
        step_target_set.add(s.target.lower())
    for s in steps.likely_expand_steps:
        step_target_set.add(s.target.lower())

    actions = []
    for a in page.primary_actions:
        action_dict = {
            "name": a.name,
            "action_type": a.action_type,
            "description": a.description,
        }
        name_lower = a.name.lower()
        observed = any(name_lower in t or t in name_lower for t in step_target_set if t)
        if observed:
            action_dict["observed_in_steps"] = True
        actions.append(action_dict)

    return actions


def _build_key_steps(steps: StepUnderstanding) -> list[KeyStepSummary]:
    """Distill key steps from 6D into unified KeyStepSummary with role tags."""
    result: list[KeyStepSummary] = []
    seen_indices: set[int] = set()

    # Submit steps get "submit" role
    for s in steps.likely_submit_steps:
        if s.step_index not in seen_indices:
            result.append(KeyStepSummary(
                step_index=s.step_index,
                event_type=s.event_type,
                target=s.target,
                role="submit",
                reason=s.description or "Identified as submit/save action",
            ))
            seen_indices.add(s.step_index)

    # Expand steps get "expand" role
    for s in steps.likely_expand_steps:
        if s.step_index not in seen_indices:
            result.append(KeyStepSummary(
                step_index=s.step_index,
                event_type=s.event_type,
                target=s.target,
                role="expand",
                reason=s.description or "Identified as expand/toggle action",
            ))
            seen_indices.add(s.step_index)

    # Remaining key steps from 6D
    for s in steps.likely_key_steps:
        if s.step_index not in seen_indices:
            # Infer role from event_type
            if s.event_type == "navigate":
                role = "navigate"
            elif s.event_type == "input":
                role = "key_input"
            elif s.event_type in ("click",):
                role = "other"
            else:
                role = "other"
            result.append(KeyStepSummary(
                step_index=s.step_index,
                event_type=s.event_type,
                target=s.target,
                role=role,
                reason=s.reason,
            ))
            seen_indices.add(s.step_index)

    # Sort by step_index for chronological order
    result.sort(key=lambda x: x.step_index)
    return result


def _build_interaction_patterns(
    page: PageUnderstanding,
    steps: StepUnderstanding,
) -> list[str]:
    """Merge step patterns and change patterns into unified interaction patterns."""
    patterns: list[str] = []

    # Step patterns from 6D (how the page is used)
    patterns.extend(steps.common_step_patterns)

    # Change patterns from 6D (what changes look like)
    patterns.extend(steps.observed_change_patterns)

    # Cap at 5
    return patterns[:5]


def _build_execution_notes(
    steps: StepUnderstanding,
    page: PageUnderstanding,
) -> list[ExecutionNote]:
    """Surface observations that the execution layer should know about."""
    notes: list[ExecutionNote] = []

    # No-change steps that aren't navigation
    for s in steps.likely_no_change_steps:
        if s.likely_reason == "navigation":
            continue  # Navigation no-change is expected, not noteworthy
        notes.append(ExecutionNote(
            note=f"Step [{s.step_index}] ({s.event_type} → {s.target}) had no observed changes: {s.likely_reason}",
            source="no_change_step",
        ))

    return notes


# ---------------------------------------------------------------------------
# Description generation via lightweight LLM call
# ---------------------------------------------------------------------------

_LOCALE_LABELS: dict[str, str] = {
    "zh": "Chinese (简体中文)",
    "en": "English",
    "ja": "Japanese (日本語)",
}

_DESCRIPTION_SYSTEM_PROMPT = """\
You are a concise technical writer. Given structured analysis results of a web \
page and recorded user operations, produce two short descriptions.

Rules:
- page_description: 2-4 sentences. What this page is, its core regions, and \
  main operations. Not a mechanical list — write naturally.
- operation_description: 2-5 sentences. What the user did in this recording. \
  Cover the overall flow, key actions, and noteworthy observations (e.g. \
  no-change steps, async risks). Do NOT write execution plans or suggestions.
- For no-change steps: describe what the user did and note that no visible \
  change was observed — never call it a failure.
- If there is insufficient information, return an empty string for that field.\
"""

_DESCRIPTION_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "page_description": {"type": "string"},
        "operation_description": {"type": "string"},
    },
    "required": ["page_description", "operation_description"],
}


def _build_description_input(
    page: PageUnderstanding,
    steps: StepUnderstanding,
) -> str:
    """Build a compact JSON summary for the description LLM call."""
    data: dict = {}

    # Page info
    if page.page_kind != "unknown" or page.page_goal:
        data["page_kind"] = page.page_kind
    if page.page_goal:
        data["page_goal"] = page.page_goal
    if page.primary_regions:
        data["regions"] = [{"name": r.name, "role": r.role} for r in page.primary_regions]
    if page.primary_actions:
        data["actions"] = [{"name": a.name, "type": a.action_type} for a in page.primary_actions]
    if page.key_entities:
        data["entities"] = page.key_entities

    # Step info
    if steps.common_step_patterns:
        data["step_patterns"] = steps.common_step_patterns
    if steps.likely_key_steps:
        data["key_steps"] = [
            {"index": s.step_index, "event": s.event_type, "target": s.target, "reason": s.reason}
            for s in steps.likely_key_steps
        ]
    if steps.likely_expand_steps:
        data["expand_steps"] = [
            {"index": s.step_index, "target": s.target, "desc": s.description}
            for s in steps.likely_expand_steps
        ]
    if steps.likely_submit_steps:
        data["submit_steps"] = [
            {"index": s.step_index, "target": s.target, "desc": s.description}
            for s in steps.likely_submit_steps
        ]
    no_change_notable = [
        s for s in steps.likely_no_change_steps if s.likely_reason != "navigation"
    ]
    if no_change_notable:
        data["no_change_steps"] = [
            {"index": s.step_index, "target": s.target, "reason": s.likely_reason}
            for s in no_change_notable
        ]
    if steps.step_descriptions:
        data["step_descriptions"] = [
            {"index": sd.step_index, "desc": sd.description}
            for sd in steps.step_descriptions
        ]

    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _generate_descriptions(
    page: PageUnderstanding,
    steps: StepUnderstanding,
    locale: str = "en",
) -> tuple[str, str]:
    """Generate page_description and operation_description via lightweight LLM call.

    Returns (page_description, operation_description). Falls back to ("", "")
    on any failure — these descriptions are non-critical.
    """
    # Skip if nothing to describe
    if page.page_kind == "unknown" and not page.page_goal and not steps.common_step_patterns:
        return "", ""

    lang_label = _LOCALE_LABELS.get(locale, "English")
    prompt = (
        f"Output language: {lang_label}\n\n"
        f"Structured analysis:\n{_build_description_input(page, steps)}"
    )

    request = build_request(
        prompt,
        system=_DESCRIPTION_SYSTEM_PROMPT,
        response_schema=_DESCRIPTION_SCHEMA,
    )

    try:
        resp = generate_structured(request)
        if resp.ok and resp.parsed:
            return (
                resp.parsed.get("page_description", ""),
                resp.parsed.get("operation_description", ""),
            )
    except Exception as exc:
        logger.warning("Description generation failed (non-critical): %s", exc)

    return "", ""


def _merge_confidence_notes(
    page: PageUnderstanding,
    steps: StepUnderstanding,
) -> list[str]:
    """Merge confidence notes from both sources, dedup."""
    notes: list[str] = []
    seen: set[str] = set()
    for n in page.confidence_notes + steps.confidence_notes:
        if n and n not in seen:
            notes.append(n)
            seen.add(n)
    return notes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_agent_page_understanding(
    page: PageUnderstanding,
    steps: StepUnderstanding,
    *,
    locale: str | None = None,
) -> AgentPageUnderstanding:
    """Synthesize PageUnderstanding + StepUnderstanding into a unified result.

    Structural fields are rule-based merges. Description fields use a
    lightweight LLM call for locale-aware natural language.
    """
    resolved_locale = locale or get_locale()
    page_desc, op_desc = _generate_descriptions(page, steps, resolved_locale)

    return AgentPageUnderstanding(
        page_kind=page.page_kind,
        page_goal=page.page_goal,
        primary_regions=_enrich_regions(page, steps),
        primary_actions=_enrich_actions(page, steps),
        key_steps=_build_key_steps(steps),
        interaction_patterns=_build_interaction_patterns(page, steps),
        execution_notes=_build_execution_notes(steps, page),
        key_entities=list(page.key_entities),
        page_description=page_desc,
        operation_description=op_desc,
        confidence_notes=_merge_confidence_notes(page, steps),
    )
