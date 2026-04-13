"""Agent input contract — unified input structures for Agent understanding.

Defines the stable input schemas that Phase 6C (page understanding),
6D (step understanding), and 6E (combined output) consume.
Business modules should use these types, not raw API data.

Design principles:
- Separates page material from step material
- Includes summary stats so LLM prompts can reference counts without re-computing
- Serializable and prompt-friendly — no debug fields, no internal IDs beyond recording_id
- Preserves enough information for understanding without raw implementation detail
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.ast import ASTNode, SimplifyStats


# ---------------------------------------------------------------------------
# Page context — input for page understanding (6C)
# ---------------------------------------------------------------------------

class PageContext(BaseModel):
    """Everything the Agent needs to understand what a page is.

    Built from the Simplified AST + recording metadata.
    """

    recording_id: str
    url: str = ""
    title: str = ""

    # Simplified AST — the primary page structure
    ast_nodes: list[ASTNode] = Field(default_factory=list)
    ast_stats: SimplifyStats = Field(default_factory=SimplifyStats)

    # Summary stats for quick orientation (computed by builder)
    total_node_count: int = 0
    element_count: int = 0
    text_node_count: int = 0
    visible_element_count: int = 0
    top_level_count: int = 0
    """Number of direct children at the AST root — rough proxy for major page regions."""

    interactive_element_tags: dict[str, int] = Field(default_factory=dict)
    """Counts of interactive element tags found in the AST (input, button, select, a, textarea, etc.)."""


# ---------------------------------------------------------------------------
# Steps context — input for step understanding (6D)
# ---------------------------------------------------------------------------

class StepsSummaryStats(BaseModel):
    """Pre-computed summary of step patterns — saves the LLM from counting."""

    steps_with_changes: int = 0
    steps_without_changes: int = 0
    event_type_counts: dict[str, int] = Field(default_factory=dict)
    """Breakdown by event_type: {"click": 5, "input": 3, "navigate": 1, ...}"""
    has_navigate: bool = False
    """Whether any step is a navigation event."""


class StepsContext(BaseModel):
    """Everything the Agent needs to understand how a page was used.

    Built from the AgentStepListView.
    """

    recording_id: str

    # The steps themselves — the primary material
    steps: list[dict] = Field(default_factory=list)
    """Each step as a plain dict matching AgentStepView fields.
    Using dict (not AgentStepView) to keep this layer serialization-friendly
    and decoupled — the contract is the field names, not the Pydantic class."""

    step_count: int = 0
    has_mutations: bool = False

    # Pre-computed summary
    summary: StepsSummaryStats = Field(default_factory=StepsSummaryStats)


# ---------------------------------------------------------------------------
# Combined input — the single entry point for Agent understanding
# ---------------------------------------------------------------------------

class AgentUnderstandingInput(BaseModel):
    """Unified input container for all Agent understanding modules.

    This is what 6C, 6D, and 6E consume. It bundles page material and step
    material together so that understanding modules don't assemble inputs
    themselves.
    """

    recording_id: str
    page: PageContext
    steps: StepsContext
    schema_version: str = "1"
    """Version of this input contract. Bump when fields change in a breaking way."""
