"""Page verification schemas.

Structured representations for per-page verification specs (authored in
``apps/validation-site/specs/<page>.assertions.json``) and the scorecard
produced after an autonomous run is compared against a spec.

Design notes:
  - Specs are authored BEFORE any autonomous-run output, as an independent
    baseline. The comparator consumes both and produces a scorecard.
  - The scorecard reports 5 independent scores — no aggregate total, so
    a bad sub-score cannot be masked by averaging (per user design).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ───────────────────────────────────────────────────────────────────
# Spec: element matching predicate
# ───────────────────────────────────────────────────────────────────


class ElementMatcher(BaseModel):
    """Predicate for locating an element among the analyzer's discovered set.

    All specified (non-None / non-empty) fields are AND-combined. An element
    matches iff every specified criterion matches its observed attributes.

    ``selector_any_of`` is an alternative OR-path: if the element's own
    generated selector string appears in the list, the element matches
    regardless of the atomic criteria. This lets spec authors fall back to
    raw selectors when needed.
    """

    id: str | None = None
    name: str | None = None
    tag: str | None = None
    element_type: str | None = None
    role: str | None = None
    text_contains: str | None = None
    placeholder_contains: str | None = None
    aria_label_contains: str | None = None
    selector_any_of: list[str] = Field(default_factory=list)


# ───────────────────────────────────────────────────────────────────
# Spec: elements
# ───────────────────────────────────────────────────────────────────


class CriticalElementSpec(BaseModel):
    """A page element that MUST be recognized by the analyzer.

    ``visible_only_on`` lets authors declare that some elements are only
    expected to appear under specific scenarios (e.g. the error alert is
    only mounted in an invalid-credentials run). Values are free-form
    scenario keys that must exist in the spec's ``scenarios`` map.
    """

    role: str = Field(description="Stable role key within this spec, e.g. 'username_input'.")
    expected_category: str = Field(
        description="Element category the analyzer should have assigned "
        "(fillable / submit / clickable / navigation / select / toggle / other).",
    )
    expected_semantic_role: str | None = Field(
        default=None,
        description="Semantic role if applicable: 'username', 'password', 'email', 'text'.",
    )
    visible_only_on: list[str] | None = Field(
        default=None,
        description="If set, this element is only expected in listed scenarios "
        "(scenario keys from this spec's ``scenarios`` map).",
    )
    match_by: ElementMatcher


class DistractionSpec(BaseModel):
    """An element that MUST NOT be chosen as a primary action target."""

    role: str
    match_by: ElementMatcher


# ───────────────────────────────────────────────────────────────────
# Spec: scenarios
# ───────────────────────────────────────────────────────────────────


class SuccessSignals(BaseModel):
    url_contains: str | None = None
    title_contains: str | None = None
    dom_contains_all_of: list[str] = Field(default_factory=list)
    dom_contains_any_of: list[str] = Field(default_factory=list)
    dom_has_test_id: str | None = None


class FailureSignals(BaseModel):
    url_contains: str | None = None
    alert_visible: bool | None = None
    alert_text_contains_any_of: list[str] = Field(default_factory=list)


class ScenarioSpec(BaseModel):
    description: str = ""
    inputs: dict[str, str] = Field(default_factory=dict)
    expected_actions: list[str] = Field(
        default_factory=list,
        description="Encoded as 'action_type:element_role', e.g. 'fill:username_input'.",
    )
    success_signals: SuccessSignals = Field(default_factory=SuccessSignals)
    failure_signals: FailureSignals = Field(default_factory=FailureSignals)
    must_not_transition_to: str | None = None
    expected_verdict: str | None = None
    expected_verdict_not: str | None = None


# ───────────────────────────────────────────────────────────────────
# Top-level spec
# ───────────────────────────────────────────────────────────────────


class PageVerificationSpec(BaseModel):
    """A full page verification spec (matches login.assertions.json)."""

    page_id: str
    url_pattern: str = ""
    description: str = ""
    critical_elements: list[CriticalElementSpec] = Field(default_factory=list)
    distractions: list[DistractionSpec] = Field(default_factory=list)
    scenarios: dict[str, ScenarioSpec] = Field(default_factory=dict)


# ───────────────────────────────────────────────────────────────────
# Scorecard: per-check details
# ───────────────────────────────────────────────────────────────────


class ElementCheck(BaseModel):
    role: str
    skipped: bool = False           # True when visible_only_on excluded this scenario
    found: bool = False
    category_match: bool = False
    semantic_role_match: bool | None = None
    observed_category: str | None = None
    observed_semantic_role: str | None = None
    observed_selector: str | None = None
    notes: str = ""


class ActionCheck(BaseModel):
    expected: str                    # "fill:username_input"
    executed: bool = False
    step_index: int | None = None
    notes: str = ""


class DistractionCheck(BaseModel):
    role: str
    hit: bool = False                # action landed on this distraction
    hit_by_step_index: int | None = None
    notes: str = ""


class VerdictCheck(BaseModel):
    self_verdict: str | None = None
    expected_verdict: str | None = None
    expected_verdict_not: str | None = None
    must_not_transition_to: str | None = None
    final_url: str | None = None
    matches_expectation: bool = False
    notes: str = ""


class SupervisorCheck(BaseModel):
    supervisor_verdict: str | None = None
    expected_bucket: str | None = None
    score: float = 0.0               # 1 / 0.5 / 0
    notes: str = ""


# ───────────────────────────────────────────────────────────────────
# Scorecard: aggregated 5-score card (no total per spec decision)
# ───────────────────────────────────────────────────────────────────


class ScoreBlock(BaseModel):
    score: float = Field(description="Score in [0, 1].")
    weight_note: str = ""


class PageVerificationScorecard(BaseModel):
    """The 5-score output of the comparator. No aggregate total by design."""

    page_id: str
    scenario: str
    spec_schema_version: int = 1

    # 1. Element recognition
    element_recognition: ScoreBlock
    element_checks: list[ElementCheck]

    # 2. Action path coverage
    action_coverage: ScoreBlock
    action_checks: list[ActionCheck]

    # 3. Result verdict accuracy
    verdict_accuracy: ScoreBlock
    verdict_check: VerdictCheck

    # 4. Distraction avoidance
    distraction_avoidance: ScoreBlock
    distraction_checks: list[DistractionCheck]

    # 5. Supervisor agreement with baseline
    supervisor_agreement: ScoreBlock
    supervisor_check: SupervisorCheck

    # Raw metadata
    notes: list[str] = Field(default_factory=list)


class PageVerificationResult(BaseModel):
    """Wrapper returned by the verify endpoint — spec + scorecard."""

    spec_source: str = Field(description="Path the spec was loaded from.")
    spec: dict[str, Any] = Field(description="Raw loaded spec JSON.")
    scorecard: PageVerificationScorecard
