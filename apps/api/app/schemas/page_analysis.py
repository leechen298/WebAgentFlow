"""Page analysis schema — autonomous discovery of interactive elements.

The page analyzer examines a live page and produces a structured inventory
of interactive elements without any pre-written selectors or task definitions.
This is the foundation for autonomous exploration.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ElementCategory = Literal[
    "fillable",       # input, textarea, contenteditable, role=textbox/combobox/searchbox
    "submit",         # button, input[type=submit], role=button with submit semantics
    "clickable",      # generic buttons, role=button
    "navigation",     # links, menu items, tabs
    "select",         # select, dropdown, role=listbox
    "toggle",         # checkbox, radio, switch
    "other",          # anything else interactive
]


SemanticRole = Literal[
    "username", "password", "email", "search",
    "name", "role", "status",
    "text",
]


class DiscoveredElement(BaseModel):
    """A single interactive element discovered on the page."""

    category: ElementCategory
    tag: str
    element_type: str | None = Field(
        default=None, description="HTML type attribute (text, submit, checkbox, etc.).",
    )
    element_value: str | None = Field(
        default=None,
        description="HTML value attribute. Populated for radio / checkbox / "
        "select <option> elements so the planner can distinguish siblings in "
        "one group (e.g. radios with value='active' vs value='disabled'). "
        "Empty string retained verbatim since it is a meaningful value "
        "(e.g. the 'All' radio in an Ant Design radio group).",
    )
    id: str | None = None
    name: str | None = Field(
        default=None, description="HTML name attribute.",
    )
    role: str | None = Field(
        default=None, description="ARIA role.",
    )
    placeholder: str | None = None
    text: str = Field(
        default="", description="Visible text content (truncated).",
    )
    aria_label: str | None = None
    content_editable: bool = False
    visible: bool = True
    rect: dict[str, int] = Field(
        default_factory=dict, description="Bounding rect: x, y, w, h.",
    )
    selector: str = Field(
        default="", description="Best-effort unique CSS selector for this element.",
    )
    reason: str = Field(
        default="",
        description="Why this element is classified as interactive.",
    )
    semantic_role: SemanticRole | None = Field(
        default=None,
        description="Inferred semantic purpose for fillable elements, from structural signals "
        "(type attribute, name, placeholder, aria-label). None if not applicable.",
    )
    label_text: str | None = Field(
        default=None,
        description="Visible human-readable label associated with this element, "
        "extracted from common UI-library form-item shapes (Ant Design, native "
        "<label>). None if no extractor matched — no fuzzy fallback.",
    )
    label_source: str | None = Field(
        default=None,
        description="Which FormLabelExtractor produced label_text "
        "('ant-design' / 'native'). None when label_text is None.",
    )
    content_hint: str | None = Field(
        default=None,
        description="Short description of what's visually inside an element "
        "when its own text and aria-label are empty. Formats: 'aria:<label>' "
        "from a descendant aria-label, 'icon:<name>' from svg[data-icon], "
        "'img:<alt-or-filename>' from <img>, or bare 'icon' / 'img' when "
        "only the shape is known. None when the element already has "
        "informative text / aria_label, or truly has no content clue.",
    )


class PlannedAction(BaseModel):
    """One step in an action plan derived from page analysis."""

    step: int
    action_type: str  # fill, click, press, observe
    target_selector: str = Field(
        description="CSS selector of the target element (from discovery).",
    )
    target_description: str = Field(
        default="", description="Human-readable description of the target.",
    )
    value: str | None = None
    reason: str = Field(
        default="", description="Why this action was planned.",
    )


class PageAnalysis(BaseModel):
    """Structured result of autonomous page analysis."""

    url: str
    title: str
    timestamp_ms: int = 0
    screenshot_ref: str | None = None

    # Discovered elements by category
    fillable: list[DiscoveredElement] = Field(default_factory=list)
    submit: list[DiscoveredElement] = Field(default_factory=list)
    clickable: list[DiscoveredElement] = Field(default_factory=list)
    navigation: list[DiscoveredElement] = Field(default_factory=list)
    select: list[DiscoveredElement] = Field(default_factory=list)
    toggle: list[DiscoveredElement] = Field(default_factory=list)
    other: list[DiscoveredElement] = Field(default_factory=list)

    # All hidden interactive elements (for reference)
    hidden_interactive: list[DiscoveredElement] = Field(default_factory=list)

    # Stats
    total_discovered: int = 0
    total_visible: int = 0
    total_hidden: int = 0

    # Recommended action plan
    recommended_actions: list[PlannedAction] = Field(default_factory=list)


OutcomeVerdict = Literal[
    "success",          # all action steps ok AND observable state change
    "partial_success",  # some action steps failed
    "failure",          # actions executed but no state change, or blocked (CAPTCHA/auth wall)
    "uncertain",        # cannot determine — insufficient signals
]
# This enum is intentionally shared with the autonomous-supervisor
# response schema (see exploration_supervisor.SUPERVISOR_RESPONSE_SCHEMA).
# Rule-side self-verdict and LLM-side supervisor verdict speak the same
# vocabulary so the scorecard's bucket mapping doesn't have to translate
# between two ontologies.


class AutonomousExplorationResult(BaseModel):
    """Full result of an autonomous exploration run."""

    # Phase 1: Analysis
    page_analysis: PageAnalysis

    # Phase 2: Execution
    steps: list[dict[str, Any]] = Field(default_factory=list)
    total_steps: int = 0
    elapsed_ms: int = 0

    # Phase 3: Final state
    final_url: str = ""
    final_title: str = ""
    final_screenshot_ref: str | None = None
    final_state: dict[str, Any] = Field(
        default_factory=dict,
        description="End-of-run DOM signals (body_text, test_ids, alert_texts) "
        "for spec-driven signal verification. Generic, not site-specific.",
    )

    # Phase 4: Self-assessment (rule-based)
    verdict: OutcomeVerdict = Field(
        default="uncertain",
        description="Rule-based outcome verdict. 'success' requires both action "
        "execution AND observable state change — mere step completion is not enough.",
    )
    success: bool = Field(
        default=False,
        description="Derived: True iff verdict == 'success'. Kept for backward compat.",
    )
    summary: str = ""

    # Phase 5: Supervisor verification (project-internal Agent)
    supervisor: dict[str, Any] | None = Field(
        default=None,
        description="Verification output from the project's internal supervisor Agent. "
        "Contains: verdict, confidence, summary, step_assessments, anomalies, suggestions.",
    )
