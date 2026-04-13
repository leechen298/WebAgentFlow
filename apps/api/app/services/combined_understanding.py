"""Combined understanding service (Phase 6E).

Rule-based synthesis of PageUnderstanding (6C) + StepUnderstanding (6D)
into a unified AgentPageUnderstanding.

No LLM call — both inputs are already structured results. This layer
does deterministic merging: enrich regions with step activity, assign
roles to key steps, surface execution notes from no-change observations.

Usage:
    from app.services.combined_understanding import build_agent_page_understanding

    result = build_agent_page_understanding(page_understanding, step_understanding)
"""

from __future__ import annotations

from app.schemas.combined_understanding import (
    AgentPageUnderstanding,
    ExecutionNote,
    KeyStepSummary,
)
from app.schemas.page_understanding import PageUnderstanding
from app.schemas.step_understanding import StepUnderstanding


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
) -> AgentPageUnderstanding:
    """Synthesize PageUnderstanding + StepUnderstanding into a unified result.

    Pure rule-based — no LLM call. Both inputs are already structured
    LLM outputs from 6C and 6D.
    """
    return AgentPageUnderstanding(
        page_kind=page.page_kind,
        page_goal=page.page_goal,
        primary_regions=_enrich_regions(page, steps),
        primary_actions=_enrich_actions(page, steps),
        key_steps=_build_key_steps(steps),
        interaction_patterns=_build_interaction_patterns(page, steps),
        execution_notes=_build_execution_notes(steps, page),
        key_entities=list(page.key_entities),
        confidence_notes=_merge_confidence_notes(page, steps),
    )
