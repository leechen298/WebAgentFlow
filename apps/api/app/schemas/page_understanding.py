"""Page understanding output schema.

Defines the structured result of LLM-based page understanding (Phase 6C).
This is what the Agent produces after analyzing a PageContext.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


PageKind = Literal[
    "list",
    "form",
    "detail",
    "dashboard",
    "config",
    "modal",
    "login",
    "mixed",
    "unknown",
]


class RegionInfo(BaseModel):
    """A major region identified on the page."""

    name: str
    role: str = Field(description="What this region does, one sentence.")


class ActionInfo(BaseModel):
    """A primary action entry point on the page."""

    name: str
    action_type: str = Field(
        description="Category: create, edit, delete, save, submit, navigate, toggle, expand, filter, search, other.",
    )
    description: str = Field(default="", description="Brief clarification if name alone is ambiguous.")


class PageUnderstanding(BaseModel):
    """Structured page understanding result.

    Produced by the page understanding service (6C).
    Consumed by 6E (combined output) and Phase 7 (execution).
    """

    page_kind: PageKind = "unknown"
    page_goal: str = Field(
        default="",
        description="One-sentence description of what this page is for.",
    )
    primary_regions: list[RegionInfo] = Field(default_factory=list)
    primary_actions: list[ActionInfo] = Field(default_factory=list)
    key_entities: list[str] = Field(
        default_factory=list,
        description="Core business objects appearing on the page (e.g. 'order', 'product', 'user').",
    )
    confidence_notes: list[str] = Field(
        default_factory=list,
        description="Optional notes on uncertain judgments, for debug/review.",
    )


# JSON Schema dict for use with generate_structured().
PAGE_UNDERSTANDING_SCHEMA: dict = PageUnderstanding.model_json_schema()
