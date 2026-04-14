"""Locator resolution schema (Phase 7C).

Defines the structured output of the locator resolver — a description
of *how* to locate a target element on the page that Playwright can
consume.

This module is ONLY the result schema.  The resolution logic lives in
``services/locator_resolver.py``.

Scope — Phase 7C is ONLY the locator resolution layer:
  - NOT an action executor          (7D)
  - NOT a post-action observer      (7E)
  - NOT a wait/retry/recovery system
  - NOT a task planner
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ───────────────────────────────────────────────────────────────────
# Selector descriptor
# ───────────────────────────────────────────────────────────────────

SelectorType = Literal[
    "css",
    "role",
    "text",
    "label",
    "placeholder",
    "test_id",
    "xpath",
]
"""How the selector string should be interpreted by Playwright."""


class SelectorDescriptor(BaseModel):
    """A Playwright-consumable selector description.

    Phase 7D uses this to call the appropriate Playwright locator API::

        if desc.selector_type == "css":
            loc = page.locator(desc.selector)
        elif desc.selector_type == "role":
            loc = page.get_by_role(desc.role, name=desc.name)
        ...
    """

    selector_type: SelectorType
    selector: str = Field(
        default="",
        description="CSS/XPath selector string.  Used when selector_type is 'css' or 'xpath'.",
    )
    role: str = Field(
        default="",
        description="ARIA role for get_by_role().  Used when selector_type is 'role'.",
    )
    name: str = Field(
        default="",
        description="Accessible name / text for role/text/label/placeholder selectors.",
    )
    exact: bool = Field(
        default=False,
        description="Whether name matching should be exact (vs substring).",
    )
    within_frame: str | None = Field(
        default=None,
        description="Frame selector if the target lives inside an iframe.",
    )
    nth: int | None = Field(
        default=None,
        description="0-based index when multiple elements match.  None = first.",
    )


# ───────────────────────────────────────────────────────────────────
# Resolution result
# ───────────────────────────────────────────────────────────────────

class ResolvedLocator(BaseModel):
    """Structured result of locator resolution (Phase 7C output).

    This is what ``resolve_locator()`` returns.  Phase 7D consumes it
    to perform the actual Playwright action — 7D does NOT re-resolve.

    When ``ok`` is False, ``descriptor`` may still carry the best-effort
    attempt, and ``trace`` explains what was tried and why it failed.
    """

    # --- A. Outcome ---
    ok: bool = False
    source: str = Field(
        default="",
        description="LocatorPriority strategy name that produced the match, "
        "e.g. 'SERVER_AST_MATCH', 'STRONG_ATTRIBUTE'.  Empty on failure.",
    )
    confidence: Literal["high", "medium", "low"] = "low"

    # --- B. Playwright-consumable descriptor ---
    descriptor: SelectorDescriptor | None = Field(
        default=None,
        description="How to locate the element.  None when resolution failed entirely.",
    )

    # --- C. Match context ---
    matched_tag: str = Field(default="", description="HTML tag of the matched element.")
    matched_text: str = Field(default="", description="Visible text of the matched element (truncated).")
    matched_count: int = Field(
        default=0,
        description="Number of elements the selector matched on the page.  "
        "1 = unique match, >1 = ambiguous (nth may be set).",
    )

    # --- D. Debug / trace ---
    trace: list[str] = Field(
        default_factory=list,
        description="Ordered log of what the resolver tried, in priority order.",
    )
    fallback_used: bool = Field(
        default=False,
        description="True if the resolver fell below REGION_SCOPED to reach a match.",
    )
