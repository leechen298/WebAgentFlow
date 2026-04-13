"""Agent input builder — adapts existing project data into Agent input contract.

Converts Simplified AST, recording metadata, and AgentStepListView into
the unified PageContext / StepsContext / AgentUnderstandingInput structures
that Phase 6C/6D/6E consume.

Usage:
    from app.services.agent_input_builder import build_agent_understanding_input

    inp = build_agent_understanding_input(
        recording_id=recording.id,
        events=recording.events,
        simplified_ast=simplified_ast,
        agent_step_view=agent_step_view,
    )
"""

from __future__ import annotations

from typing import Any

from app.schemas.agent_input import (
    AgentUnderstandingInput,
    PageContext,
    StepsContext,
    StepsSummaryStats,
)
from app.schemas.ast import ASTNode, SimplifiedAST


# ---------------------------------------------------------------------------
# Interactive element tags we count for quick orientation
# ---------------------------------------------------------------------------

_INTERACTIVE_TAGS = frozenset({
    "input", "button", "select", "textarea", "a",
    "details", "summary", "dialog",
    "frame-body",  # synthetic iframe wrapper — signals embedded content
})


# ---------------------------------------------------------------------------
# AST tree walking helpers
# ---------------------------------------------------------------------------

def _count_ast_stats(nodes: list[ASTNode]) -> dict[str, Any]:
    """Walk the AST tree once and collect summary stats."""
    element_count = 0
    text_node_count = 0
    visible_element_count = 0
    interactive_tags: dict[str, int] = {}

    def _walk(node: ASTNode) -> None:
        nonlocal element_count, text_node_count, visible_element_count

        if node.node_type == "text":
            text_node_count += 1
            return

        # element node
        element_count += 1
        if node.visible:
            visible_element_count += 1

        tag = node.tag or ""
        if tag in _INTERACTIVE_TAGS:
            interactive_tags[tag] = interactive_tags.get(tag, 0) + 1

        # Also count role-based interactive elements
        role = node.attrs.get("role", "")
        if role in ("button", "link", "textbox", "combobox", "listbox", "checkbox", "radio"):
            role_key = f"[role={role}]"
            interactive_tags[role_key] = interactive_tags.get(role_key, 0) + 1

        for child in node.children:
            _walk(child)

    for n in nodes:
        _walk(n)

    return {
        "element_count": element_count,
        "text_node_count": text_node_count,
        "visible_element_count": visible_element_count,
        "interactive_element_tags": interactive_tags,
        "total_node_count": element_count + text_node_count,
    }


# ---------------------------------------------------------------------------
# Page URL / title extraction from events
# ---------------------------------------------------------------------------

def _extract_page_info(events: list[dict[str, Any]]) -> tuple[str, str]:
    """Extract page URL and title from the first navigate event, or first event with url."""
    for ev in events:
        if ev.get("type") == "navigate":
            return ev.get("url", ""), ev.get("title", "")
    # Fallback: first event with url field
    for ev in events:
        if ev.get("url"):
            return ev.get("url", ""), ev.get("title", "")
    return "", ""


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------

def build_page_context(
    recording_id: str,
    events: list[dict[str, Any]],
    simplified_ast: SimplifiedAST | None,
) -> PageContext:
    """Build PageContext from recording events and Simplified AST."""
    url, title = _extract_page_info(events)

    if simplified_ast is None:
        return PageContext(
            recording_id=recording_id,
            url=url,
            title=title,
        )

    stats = _count_ast_stats(simplified_ast.nodes)

    return PageContext(
        recording_id=recording_id,
        url=url,
        title=title,
        ast_nodes=simplified_ast.nodes,
        ast_stats=simplified_ast.stats,
        total_node_count=stats["total_node_count"],
        element_count=stats["element_count"],
        text_node_count=stats["text_node_count"],
        visible_element_count=stats["visible_element_count"],
        top_level_count=len(simplified_ast.nodes),
        interactive_element_tags=stats["interactive_element_tags"],
    )


def build_steps_context(
    recording_id: str,
    agent_step_view: dict[str, Any],
) -> StepsContext:
    """Build StepsContext from an AgentStepListView dict.

    `agent_step_view` is the dict produced by `to_agent_steps()` in step_builder,
    matching AgentStepListView fields.
    """
    steps = agent_step_view.get("steps", [])
    step_count = agent_step_view.get("step_count", len(steps))
    has_mutations = agent_step_view.get("has_mutations", False)

    # Compute summary stats
    steps_with_changes = 0
    steps_without_changes = 0
    event_type_counts: dict[str, int] = {}
    has_navigate = False

    for step in steps:
        if step.get("has_changes", False):
            steps_with_changes += 1
        else:
            steps_without_changes += 1

        et = step.get("event_type", "unknown")
        event_type_counts[et] = event_type_counts.get(et, 0) + 1

        if et == "navigate":
            has_navigate = True

    summary = StepsSummaryStats(
        steps_with_changes=steps_with_changes,
        steps_without_changes=steps_without_changes,
        event_type_counts=event_type_counts,
        has_navigate=has_navigate,
    )

    return StepsContext(
        recording_id=recording_id,
        steps=steps,
        step_count=step_count,
        has_mutations=has_mutations,
        summary=summary,
    )


def build_agent_understanding_input(
    recording_id: str,
    events: list[dict[str, Any]],
    simplified_ast: SimplifiedAST | None,
    agent_step_view: dict[str, Any],
) -> AgentUnderstandingInput:
    """Build the complete Agent understanding input from existing project data.

    This is the single entry point. Downstream modules (6C, 6D, 6E) consume
    the returned AgentUnderstandingInput and should not assemble inputs themselves.
    """
    page = build_page_context(recording_id, events, simplified_ast)
    steps = build_steps_context(recording_id, agent_step_view)

    return AgentUnderstandingInput(
        recording_id=recording_id,
        page=page,
        steps=steps,
    )
