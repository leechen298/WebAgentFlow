"""
Step Builder — correlates recording events with subsequent DOM mutations.

Produces a list of OperationStep records, each binding one user event to
the DOM mutations that likely resulted from it.

==========================================================================
Phase 5 Boundary Statement
==========================================================================

This module is the **lightweight event → DOM-change organizer**. Its job is
to take raw recording events and raw DOM mutation records and produce a
structured list of steps, each pairing one event with its time-correlated
mutations.

What this module IS:
  - A time-window based event → mutation correlator
  - A stable input layer for downstream Agent consumption (Phase 6+)
  - A provider of structured, predictable summaries

What this module is NOT (and must not become):
  - A causal inference engine (no "did this click *cause* that mutation?")
  - An execution decision layer (no "should the Agent retry?")
  - A path template or replay strategy layer
  - A semantic understanding layer (no NLP, no LLM calls)
  - An AST proximity scorer

Correlation rules (intentionally simple and explainable):

1. **Time window**: After each event, mutations within a configurable window
   (default 2000ms for click/navigate, 500ms for input/change) are candidates.
2. **Frame awareness**: Each event and mutation records its frame_url for
   traceability. Currently all in-window mutations are assigned regardless
   of frame — same-frame preference is not yet implemented.
3. **Non-overlapping**: Each mutation is assigned to at most one step — the
   closest preceding event. If a mutation falls in the window of multiple
   events, the latest event wins.
4. **No-mutation steps**: Events with zero correlated mutations are kept as
   steps (has_changes=False). These are valuable — see no-change semantics
   below.

No-change step semantics:
  A step with has_changes=False does NOT mean the action failed. It means
  no DOM mutations were observed in the correlation window. Possible causes:
    - The change happened outside the observation window (async server call)
    - The change is in a cross-origin frame (not observable)
    - A precondition was not met (e.g. form validation blocked submit)
    - The action is genuinely a no-op (e.g. clicking an already-selected tab)
    - The page uses non-DOM state (canvas, WebGL, etc.)
  Downstream consumers must NOT treat no-change as automatic failure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Time window (ms) after an event during which mutations are candidates.
# click/navigate get a longer window because they often trigger async changes.
_WINDOW_MS: dict[str, int] = {
    "click": 2000,
    "navigate": 2000,
    "input": 500,
    "change": 500,
    "richtext-input": 1000,
}
_DEFAULT_WINDOW_MS = 1000


def _window_for(event_type: str) -> int:
    return _WINDOW_MS.get(event_type, _DEFAULT_WINDOW_MS)


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------

@dataclass
class _EventEntry:
    index: int
    event: dict[str, Any]
    timestamp: int
    event_type: str
    frame_url: str  # "" for top frame


@dataclass
class _MutationEntry:
    mutation: dict[str, Any]
    mut_id: str
    timestamp: int
    frame_url: str
    assigned_event_index: int | None = None


# ---------------------------------------------------------------------------
# Summary helpers — stable, structured, action→result format
#
# Design goals:
#   - Predictable format: verb + target [→ change description]
#   - Short: one line, typically under 100 chars
#   - No NLP, no natural language generation
#   - Stable across runs for the same input
# ---------------------------------------------------------------------------

def _frame_url(obj: dict[str, Any]) -> str:
    fi = obj.get("frameInfo") or {}
    if fi.get("isIframe"):
        return fi.get("frameUrl") or ""
    return ""


def _event_target_summary(ev: dict[str, Any]) -> str:
    """Produce a short human-readable summary of the event target.

    Format: <tag> "text" | <tag> selector | <tag>
    Always starts with the tag in angle brackets for consistency.
    """
    t = ev.get("target") or {}
    tag = t.get("tag") or "?"
    text = t.get("text") or t.get("label") or t.get("nearbyText") or ""
    if text:
        text = text[:60]
        return f'<{tag}> "{text}"'
    sel = t.get("selector") or ""
    if sel:
        return f"<{tag}> {sel[:60]}"
    return f"<{tag}>"


def _mutation_highlight(mut: dict[str, Any]) -> str:
    """Produce a structured one-line description of a mutation.

    Format by type:
      childList:     <tag>: +N nodes (<child_tags>) / -N nodes (<child_tags>)
      attributes:    <tag>.attr: "old" → "new"
      characterData: <tag>: text → "new_text"

    These formats are stable and parseable. Do not add natural language.
    """
    mt = mut.get("mutationType", "")
    detail = mut.get("detail") or {}
    tag = mut.get("targetTag") or "?"

    if mt == "childList":
        added = detail.get("addedNodes") or []
        removed = detail.get("removedNodes") or []
        parts = []
        if added:
            tags = ", ".join(f"<{n.get('tag', '?')}>" for n in added[:3])
            parts.append(f"+{len(added)} nodes ({tags})" if len(added) != 1 else f"+1 node ({tags})")
        if removed:
            tags = ", ".join(f"<{n.get('tag', '?')}>" for n in removed[:3])
            parts.append(f"-{len(removed)} nodes ({tags})" if len(removed) != 1 else f"-1 node ({tags})")
        return f"<{tag}>: {'; '.join(parts)}" if parts else f"<{tag}>: childList (empty)"

    if mt == "attributes":
        attr = detail.get("attributeName") or "?"
        old = detail.get("oldValue")
        new = detail.get("newValue")
        old_s = f'"{old[:20]}"' if old else "null"
        new_s = f'"{new[:20]}"' if new else "(removed)"
        return f"<{tag}>.{attr}: {old_s} → {new_s}"

    if mt == "characterData":
        new_text = (detail.get("newValue") or "")[:40]
        return f'<{tag}>: text → "{new_text}"'

    return f"<{tag}>: {mt}"


# Verb mapping — fixed, no dynamic generation
_EVENT_VERBS: dict[str, str] = {
    "click": "Click",
    "input": "Input",
    "change": "Change",
    "richtext-input": "Edit",
    "navigate": "Navigate",
}


def _step_summary(ev: dict[str, Any], mutation_count: int, highlights: list[str]) -> str:
    """Generate a structured step summary.

    Format:
      Navigate → "Page Title"
      Click <tag> "text" → +N nodes (<tags>)
      Click <tag> "text" → no observable changes
      Input <tag> "text" → N mutations
      Edit <tag> "text" → text → "new content"

    The format is: Verb Target [→ Change]. Stable and predictable.
    """
    ev_type = ev.get("type", "?")
    verb = _EVENT_VERBS.get(ev_type, ev_type.capitalize())

    if ev_type == "navigate":
        title = ev.get("title") or ev.get("url") or ""
        if title:
            return f'Navigate → "{title[:80]}"'
        return "Navigate → (unknown page)"

    target = _event_target_summary(ev)

    if mutation_count == 0:
        return f"{verb} {target} → no observable changes"

    # Use the first highlight as the change description
    if highlights:
        # Extract just the change part (after the tag prefix) for brevity
        return f"{verb} {target} → {highlights[0]}"

    return f"{verb} {target} → {mutation_count} mutation(s)"


def _determine_change_area(
    mutations: list[dict[str, Any]],
    event_ast: dict[str, Any] | None,
) -> str | None:
    """Determine the primary area where changes occurred."""
    # Try area labels from mutations
    areas: dict[str, int] = {}
    for m in mutations:
        area = m.get("areaLabel") or ""
        if not area:
            ast = m.get("astMatch") or {}
            area = ast.get("areaLabel") or ast.get("nodeLabel") or ""
        if area:
            areas[area] = areas.get(area, 0) + 1

    if areas:
        # Return the most frequent area
        return max(areas, key=lambda k: areas[k])

    # Fall back to event's AST area
    if event_ast:
        return event_ast.get("areaLabel") or event_ast.get("nodeLabel") or None

    return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def build_steps(
    recording_id: str,
    events: list[dict[str, Any]],
    mutations: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build operation steps from recording events and DOM mutations.

    Parameters
    ----------
    recording_id : str
    events : list[dict]
        Raw recording events (camelCase keys from browser extension).
    mutations : list[dict]
        DOM mutation records (camelCase keys from browser extension).

    Returns
    -------
    dict matching OperationStepResult schema.
    """
    if not events:
        return {
            "recording_id": recording_id,
            "steps": [],
            "event_count": 0,
            "mutation_count": len(mutations),
            "mutations_correlated": 0,
            "mutations_uncorrelated": len(mutations),
        }

    # --- Parse events ---
    ev_entries: list[_EventEntry] = []
    for i, ev in enumerate(events):
        ev_entries.append(_EventEntry(
            index=i,
            event=ev,
            timestamp=int(ev.get("timestamp") or 0),
            event_type=ev.get("type") or "",
            frame_url=_frame_url(ev),
        ))

    # --- Parse mutations ---
    mut_entries: list[_MutationEntry] = []
    for m in mutations:
        mut_entries.append(_MutationEntry(
            mutation=m,
            mut_id=m.get("id") or "",
            timestamp=int(m.get("timestamp") or 0),
            frame_url=_frame_url(m),
        ))

    # Sort mutations by timestamp for efficient scanning
    mut_entries.sort(key=lambda me: me.timestamp)

    # --- Assign mutations to events ---
    # Strategy: for each event, find mutations within its time window.
    # If a mutation is in the window of multiple events, assign to the
    # latest event (closest preceding cause).
    #
    # We iterate events in reverse chronological order so that later events
    # claim mutations first, preventing earlier events from stealing them.

    for ev_entry in reversed(ev_entries):
        window = _window_for(ev_entry.event_type)
        t_start = ev_entry.timestamp
        t_end = ev_entry.timestamp + window

        for me in mut_entries:
            if me.assigned_event_index is not None:
                continue
            if me.timestamp < t_start:
                continue
            if me.timestamp > t_end:
                # Since mutations are sorted, no more can be in range
                # But events aren't necessarily sorted, so we can't break
                continue
            me.assigned_event_index = ev_entry.index

    # --- Build steps ---
    # Group assigned mutations by event index
    event_mutations: dict[int, list[_MutationEntry]] = {}
    for me in mut_entries:
        if me.assigned_event_index is not None:
            event_mutations.setdefault(me.assigned_event_index, []).append(me)

    steps: list[dict[str, Any]] = []
    for step_idx, ev_entry in enumerate(ev_entries):
        ev = ev_entry.event
        assigned = event_mutations.get(ev_entry.index, [])

        # Build mutation summary
        by_type = {"childList": 0, "attributes": 0, "characterData": 0}
        mutation_ids: list[str] = []
        highlights: list[str] = []

        for me in assigned:
            mt = me.mutation.get("mutationType") or ""
            if mt in by_type:
                by_type[mt] += 1
            mutation_ids.append(me.mut_id)
            if len(highlights) < 5:
                highlights.append(_mutation_highlight(me.mutation))

        event_ast = ev.get("astMatch")
        change_area = _determine_change_area(
            [me.mutation for me in assigned],
            event_ast,
        ) if assigned else None

        end_ts = max(me.timestamp for me in assigned) if assigned else ev_entry.timestamp

        fi = ev.get("frameInfo")

        step = {
            "id": f"s{step_idx}",
            "timestamp": ev_entry.timestamp,
            "end_timestamp": end_ts,
            "url": ev.get("url") or "",
            "frame_info": fi if fi and fi.get("isIframe") else None,
            "event_index": ev_entry.index,
            "event_type": ev_entry.event_type,
            "event_target_summary": _event_target_summary(ev),
            "event_ast_match": event_ast,
            "mutations": {
                "total": len(assigned),
                "by_type": by_type,
                "mutation_ids": mutation_ids,
                "highlights": highlights,
            },
            "has_changes": len(assigned) > 0,
            "change_area": change_area,
            "summary": _step_summary(ev, len(assigned), highlights),
        }
        steps.append(step)

    correlated_ids = {me.mut_id for me in mut_entries if me.assigned_event_index is not None}

    return {
        "recording_id": recording_id,
        "steps": steps,
        "event_count": len(events),
        "mutation_count": len(mutations),
        "mutations_correlated": len(correlated_ids),
        "mutations_uncorrelated": len(mutations) - len(correlated_ids),
    }


# ---------------------------------------------------------------------------
# Agent-ready view adapter
#
# Converts OperationStepResult into a minimal, stable projection suitable
# for Agent consumption. Strips debug fields, flattens mutation stats.
#
# This is the recommended entry point for Phase 6+ Agent consumers.
# ---------------------------------------------------------------------------

def to_agent_steps(step_result: dict[str, Any]) -> dict[str, Any]:
    """Convert a build_steps() result into an Agent-ready step list.

    The output matches the AgentStepListView schema. Each step is a flat
    dict with only the fields an Agent needs to understand the operation.

    Parameters
    ----------
    step_result : dict
        Output of build_steps().

    Returns
    -------
    dict matching AgentStepListView schema.
    """
    agent_steps: list[dict[str, Any]] = []
    any_mutations = False

    for step in step_result.get("steps", []):
        mutations = step.get("mutations", {})
        has_changes = step.get("has_changes", False)

        if has_changes:
            any_mutations = True

        # Determine no_change_reason
        no_change_reason: str | None = None
        if not has_changes:
            if step.get("event_type") == "navigate":
                no_change_reason = "navigate"
            else:
                no_change_reason = "no_mutations_observed"

        agent_steps.append({
            "event_type": step.get("event_type", ""),
            "target": step.get("event_target_summary", ""),
            "has_changes": has_changes,
            "mutation_total": mutations.get("total", 0),
            "mutation_types": mutations.get("by_type", {"childList": 0, "attributes": 0, "characterData": 0}),
            "change_area": step.get("change_area"),
            "summary": step.get("summary", ""),
            "no_change_reason": no_change_reason,
        })

    return {
        "recording_id": step_result.get("recording_id", ""),
        "steps": agent_steps,
        "step_count": len(agent_steps),
        "has_mutations": any_mutations,
    }
