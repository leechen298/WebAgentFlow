"""Execution layer contract schemas (Phase 7A).

This module defines the **input/output contract** for the Phase 7 execution
layer.  It specifies exactly what the execution layer consumes, what it
produces, and the priority order for target locating.

Scope — Phase 7A is ONLY the contract definition:
  - NOT a Playwright runtime             (7B)
  - NOT a locator resolver implementation (7C)
  - NOT an action executor                (7D)
  - NOT a post-action observer            (7E)
  - NOT an API/debug entry point          (7F)
  - NOT a wait/retry/recovery system
  - NOT a task planner or multi-step orchestrator

Design principles:
  1. Cognition input + fact input must coexist — execution cannot rely on
     summaries alone, nor on raw data alone.
  2. Server-side authoritative positioning first — ``server_ast_match`` is
     the primary locator signal.
  3. Single-step action first — the contract describes one atomic action,
     not an action chain.
  4. Output must be observable — every result carries enough context for
     debugging even before real Playwright integration.

Data consumption boundary (see ``LocatorPriority`` docstring):
  - **Primary input**: AgentPageUnderstanding, server_ast_match, server AST
  - **Auxiliary reference**: PageContext, StepUnderstanding, PageUnderstanding
  - **Not a primary source**: client-side astMatch, raw mutations, raw events
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ───────────────────────────────────────────────────────────────────
# Locator priority
# ───────────────────────────────────────────────────────────────────

class LocatorPriority(IntEnum):
    """Target-locating priority for the execution layer.

    Lower numeric value = higher priority.  The execution layer (7C)
    MUST attempt strategies in this order and stop at the first
    successful resolution.

    Data consumption boundary
    ─────────────────────────
    **Execution layer primary input** (must be present or explicitly absent):
      - AgentPageUnderstanding   — high-level page cognition
      - server_ast_match         — authoritative event → AST positioning
      - Server-side AST path     — structural context from html_ast_parser

    **Auxiliary reference** (may be consulted for enrichment / fallback):
      - PageContext              — raw AST stats / interactive-element counts
      - StepUnderstanding        — step-level patterns
      - PageUnderstanding        — page-level patterns

    **Not a primary source** (only for debug / last-resort fallback):
      - Client-side astMatch     — recording-time approximation
      - Raw mutation records     — not consumed by execution layer
      - Raw event list           — only as debug context
    """

    SERVER_AST_MATCH = 1
    STRONG_ATTRIBUTE = 2   # id / name / href / placeholder / role
    TAG_TEXT_LABEL = 3     # tag + visible text / aria-label
    REGION_SCOPED = 4      # search within a region hint
    FALLBACK_SELECTOR = 5  # CSS selector from recording
    CLIENT_AST_MATCH = 6   # client-side astMatch (lowest priority)


LOCATOR_PRIORITY_ORDER: list[str] = [p.name for p in LocatorPriority]
"""Ordered list of locator strategy names, highest priority first."""


# ───────────────────────────────────────────────────────────────────
# Action types
# ───────────────────────────────────────────────────────────────────

ActionType = Literal[
    "click",
    "fill",
    "select",
    "check",
    "uncheck",
    "hover",
    "press",
    "navigate",
    "scroll",
]
"""Atomic action types the execution layer can perform."""


# ───────────────────────────────────────────────────────────────────
# Execution request — input contract
# ───────────────────────────────────────────────────────────────────

class LocatorHint(BaseModel):
    """A single locator hint extracted from upstream data.

    Each hint carries a ``strategy`` tag that maps to ``LocatorPriority``
    so the resolver (7C) knows the precedence.
    """

    strategy: str = Field(
        description="One of LocatorPriority names: SERVER_AST_MATCH, STRONG_ATTRIBUTE, …",
    )
    value: str = Field(
        description="Strategy-specific payload: AST path, attribute selector, text content, …",
    )
    confidence: Literal["high", "medium", "low"] = "medium"
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra context for the resolver (tag, region_hint, match_type, …).",
    )


class ActionTarget(BaseModel):
    """What the execution layer should do in this step.

    Describes a single atomic action.  Multi-step orchestration is
    explicitly out of scope for Phase 7A.
    """

    action_type: ActionType
    target_description: str = Field(
        description="Human-readable summary of the target element, e.g. '提交 button in form region'.",
    )
    value: str | None = Field(
        default=None,
        description="Value for fill / select / press actions.  None for click / hover / etc.",
    )
    region_constraint: str | None = Field(
        default=None,
        description="Optional region name to narrow down target search scope.",
    )


class PageSnapshot(BaseModel):
    """Current page fact context for the execution layer.

    This provides the raw factual grounding that the execution layer
    needs beyond the cognitive summary in AgentPageUnderstanding.
    """

    url: str
    title: str = ""
    simplified_ast_ref: str | None = Field(
        default=None,
        description="Reference key to retrieve the simplified AST (e.g. recording_id).  "
        "The execution layer fetches the actual AST via this ref, not inline.",
    )
    full_ast_node_count: int | None = Field(
        default=None,
        description="Total node count in the full AST, for sanity checks.",
    )
    interactive_element_tags: dict[str, int] = Field(
        default_factory=dict,
        description="Counts of interactive elements by tag (input, button, select, …).",
    )


class ExecutionRequest(BaseModel):
    """Unified input contract for the Phase 7 execution layer.

    Every execution call receives exactly one ``ExecutionRequest``.
    Downstream modules (7B runtime, 7C locator, 7D executor) consume
    fields from this structure — they do NOT independently assemble
    their own input from scattered sources.

    Sections:
      A. Cognition input — AgentPageUnderstanding (Phase 6E output)
      B. Page facts      — current URL, title, AST ref, interactive stats
      C. Action target   — what to do (single atomic action)
      D. Locator hints   — ordered hints for target resolution
    """

    # --- A. Cognition input (Phase 6E) ---
    understanding: dict[str, Any] = Field(
        default_factory=dict,
        description="Serialized AgentPageUnderstanding.  Empty dict when understanding "
        "is unavailable (execution layer must still function in degraded mode).",
    )

    # --- B. Page facts ---
    page: PageSnapshot

    # --- C. Action target ---
    action: ActionTarget

    # --- D. Locator hints (ordered by priority) ---
    locator_hints: list[LocatorHint] = Field(
        default_factory=list,
        description="Locator hints sorted by LocatorPriority (highest first).  "
        "The resolver tries them in order.",
    )

    # --- Metadata ---
    recording_id: str = ""
    step_index: int | None = Field(
        default=None,
        description="0-based index of the step being replayed, for tracing.",
    )


# ───────────────────────────────────────────────────────────────────
# Execution result — output contract
# ───────────────────────────────────────────────────────────────────

class LocatorResult(BaseModel):
    """How the target was resolved."""

    resolved_locator: str = Field(
        default="",
        description="The Playwright locator expression that was used.",
    )
    strategy_used: str = Field(
        default="",
        description="Which LocatorPriority strategy resolved the target.",
    )
    confidence: Literal["high", "medium", "low"] = "low"
    candidates_considered: int = Field(
        default=0,
        description="Number of candidate elements evaluated before resolution.",
    )


class PageStateChange(BaseModel):
    """Observable page state before and after execution."""

    url_before: str = ""
    url_after: str = ""
    title_before: str = ""
    title_after: str = ""


class ExecutionResult(BaseModel):
    """Unified output contract for the Phase 7 execution layer.

    Every execution call produces exactly one ``ExecutionResult``,
    whether the action succeeded, failed, or was skipped.
    """

    # --- A. Basic outcome ---
    ok: bool = False
    action_type: str = ""
    target_summary: str = ""

    # --- B. Locator resolution ---
    locator: LocatorResult = Field(default_factory=LocatorResult)

    # --- C. Page state change ---
    page_change: PageStateChange = Field(default_factory=PageStateChange)

    # --- D. Debug / observability ---
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)
    screenshot_ref: str | None = Field(
        default=None,
        description="Storage key for the post-action screenshot (populated by 7E).",
    )
    html_snapshot_ref: str | None = Field(
        default=None,
        description="Storage key for the post-action HTML snapshot (populated by 7E).",
    )
    trace: list[str] = Field(
        default_factory=list,
        description="Ordered debug notes from the execution pipeline.",
    )
    elapsed_ms: int | None = Field(
        default=None,
        description="Wall-clock time for the action in milliseconds.",
    )

    # --- E. Post-action observation (populated by 7E) ---
    observation: dict[str, Any] | None = Field(
        default=None,
        description="Serialized PostActionObservation from Phase 7E.  "
        "None when observation has not been performed.",
    )
