"""Execution contract builder (Phase 7A).

Provides the unified entry point ``build_execution_request`` that assembles
an ``ExecutionRequest`` from existing project data.  All downstream Phase 7
modules (7B runtime, 7C locator, 7D executor, 7E observer) consume the
``ExecutionRequest`` — they do NOT independently gather their own input.

Scope — this module only **assembles** the contract.  It does NOT:
  - Start a Playwright browser          (7B)
  - Resolve a locator to an element     (7C)
  - Execute an action                   (7D)
  - Observe post-action changes         (7E)
  - Expose an API endpoint              (7F)

Data consumption boundary enforced here:
  - Primary: AgentPageUnderstanding, server_ast_match, server AST metadata
  - Auxiliary: PageContext (for page facts), StepUnderstanding (for patterns)
  - Not primary: client astMatch (lowest-priority fallback only)
"""

from __future__ import annotations

import logging
from typing import Any

from app.schemas.execution import (
    ActionTarget,
    ActionType,
    ExecutionRequest,
    LocatorHint,
    LocatorPriority,
    PageSnapshot,
)

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────
# Locator hint extraction
# ───────────────────────────────────────────────────────────────────

def _hints_from_server_ast_match(sam: dict[str, Any]) -> list[LocatorHint]:
    """Extract locator hints from a server_ast_match dict."""
    hints: list[LocatorHint] = []
    if not sam or sam.get("match_type") == "none":
        return hints

    path = sam.get("path")
    if path is not None:
        hints.append(LocatorHint(
            strategy=LocatorPriority.SERVER_AST_MATCH.name,
            value=".".join(str(p) for p in path),
            confidence=sam.get("confidence", "medium"),
            meta={
                "match_type": sam.get("match_type"),
                "tag": sam.get("tag"),
                "label": sam.get("label"),
                "region_hint": sam.get("region_hint"),
            },
        ))

    # region hint → REGION_SCOPED strategy
    rh = sam.get("region_hint")
    if rh:
        hints.append(LocatorHint(
            strategy=LocatorPriority.REGION_SCOPED.name,
            value=rh,
            confidence="low",
            meta={"source": "server_ast_match.region_hint"},
        ))

    return hints


def _hints_from_event_target(target: dict[str, Any]) -> list[LocatorHint]:
    """Extract locator hints from a raw event target dict."""
    hints: list[LocatorHint] = []
    if not target:
        return hints

    # Strong attributes (id, name, href, placeholder, role)
    for attr in ("id", "name", "href", "placeholder", "role"):
        val = target.get(attr)
        if val:
            hints.append(LocatorHint(
                strategy=LocatorPriority.STRONG_ATTRIBUTE.name,
                value=f"{attr}={val}",
                confidence="high" if attr == "id" else "medium",
                meta={"tag": target.get("tag"), "attribute": attr},
            ))

    # Tag + text / label
    tag = target.get("tag")
    text = target.get("text") or target.get("label") or target.get("nearbyText") or ""
    if tag and text:
        hints.append(LocatorHint(
            strategy=LocatorPriority.TAG_TEXT_LABEL.name,
            value=f"{tag}::{text[:120]}",
            confidence="medium",
            meta={"tag": tag},
        ))

    # Fallback selector
    selector = target.get("selector")
    if selector:
        hints.append(LocatorHint(
            strategy=LocatorPriority.FALLBACK_SELECTOR.name,
            value=selector,
            confidence="low",
            meta={"tag": tag},
        ))

    return hints


def _hints_from_client_ast_match(cam: dict[str, Any]) -> list[LocatorHint]:
    """Extract a low-priority hint from client-side astMatch."""
    if not cam:
        return []
    node_id = cam.get("nodeId")
    if not node_id:
        return []
    return [LocatorHint(
        strategy=LocatorPriority.CLIENT_AST_MATCH.name,
        value=str(node_id),
        confidence="low",
        meta={
            "source": "client_ast_match",
            "confidence": cam.get("confidence"),
            "nodeLabel": cam.get("nodeLabel"),
            "areaLabel": cam.get("areaLabel"),
        },
    )]


def _sort_hints(hints: list[LocatorHint]) -> list[LocatorHint]:
    """Sort hints by LocatorPriority (highest priority first)."""
    priority_map = {p.name: p.value for p in LocatorPriority}
    return sorted(hints, key=lambda h: priority_map.get(h.strategy, 99))


def _infer_action_type(event_type: str) -> ActionType:
    """Map a recording event type to an execution action type."""
    mapping: dict[str, ActionType] = {
        "click": "click",
        "input": "fill",
        "change": "select",
        "richtext-input": "fill",
        "navigate": "navigate",
    }
    return mapping.get(event_type, "click")


# ───────────────────────────────────────────────────────────────────
# Public API
# ───────────────────────────────────────────────────────────────────

def build_execution_request(
    *,
    recording_id: str,
    step: dict[str, Any],
    raw_event: dict[str, Any] | None = None,
    understanding: dict[str, Any] | None = None,
    page_url: str = "",
    page_title: str = "",
    simplified_ast_ref: str | None = None,
    full_ast_node_count: int | None = None,
    interactive_element_tags: dict[str, int] | None = None,
) -> ExecutionRequest:
    """Assemble an ExecutionRequest from existing project data.

    This is the **single entry point** for building execution-layer input.
    All Phase 7 modules consume the resulting ``ExecutionRequest``.

    Parameters
    ----------
    recording_id:
        The recording being replayed.
    step:
        An OperationStep dict (from ``build_steps``).  Must contain at
        minimum ``event_type`` and ``event_target_summary``.
    raw_event:
        The original recording event dict.  Used to extract strong
        attribute hints (id, name, href, …) and client astMatch.
        Optional — if absent, only server_ast_match hints are available.
    understanding:
        Serialized ``AgentPageUnderstanding`` dict (Phase 6E output).
        Empty/None is allowed — execution runs in degraded mode.
    page_url:
        Current page URL.
    page_title:
        Current page title.
    simplified_ast_ref:
        Reference key to fetch the simplified AST (typically recording_id).
    full_ast_node_count:
        Total AST node count for sanity checks.
    interactive_element_tags:
        Interactive element counts from PageContext.
    """
    # --- Locator hints (priority-ordered) ---
    hints: list[LocatorHint] = []

    # 1. Server AST match (highest priority)
    sam = step.get("event_server_ast_match")
    hints.extend(_hints_from_server_ast_match(sam or {}))

    # 2-5. Strong attributes, tag+text, fallback selector from raw event
    if raw_event:
        target = raw_event.get("target") or {}
        hints.extend(_hints_from_event_target(target))

    # 6. Client AST match (lowest priority)
    if raw_event:
        cam = raw_event.get("astMatch")
        hints.extend(_hints_from_client_ast_match(cam or {}))

    hints = _sort_hints(hints)

    # --- Action target ---
    event_type = step.get("event_type") or "click"
    target_summary = step.get("event_target_summary") or ""

    # Determine value for fill/select actions
    value: str | None = None
    if raw_event:
        value = raw_event.get("value") or raw_event.get("inputValue")

    action_type = _infer_action_type(event_type)

    # Region constraint from server AST match
    region_constraint: str | None = None
    if sam and sam.get("region_hint"):
        region_constraint = sam["region_hint"]

    action = ActionTarget(
        action_type=action_type,
        target_description=target_summary,
        value=value,
        region_constraint=region_constraint,
    )

    # --- Page snapshot ---
    url = page_url or step.get("url") or ""
    page = PageSnapshot(
        url=url,
        title=page_title,
        simplified_ast_ref=simplified_ast_ref,
        full_ast_node_count=full_ast_node_count,
        interactive_element_tags=interactive_element_tags or {},
    )

    return ExecutionRequest(
        understanding=understanding or {},
        page=page,
        action=action,
        locator_hints=hints,
        recording_id=recording_id,
        step_index=step.get("event_index"),
    )
