"""Page verification — compare an autonomous run against a spec.

Loads ``specs/<page>.assertions.json`` from the validation-site and
scores a completed ``AutonomousExplorationResult`` against it. Produces
a ``PageVerificationScorecard`` with 5 independent scores (no total).

All logic is rule-based. This is project code — not Claude Code analysis,
not an LLM — so results are deterministic and auditable.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.schemas.page_analysis import (
    AutonomousExplorationResult,
    DiscoveredElement,
    PageAnalysis,
)
from app.schemas.page_verification import (
    ActionCheck,
    CriticalElementSpec,
    DistractionCheck,
    DistractionSpec,
    ElementCheck,
    ElementMatcher,
    PageVerificationScorecard,
    PageVerificationSpec,
    PassGate,
    ScoreBlock,
    SupervisorCheck,
    VerdictCheck,
)

logger = logging.getLogger(__name__)


# Root of the validation-site specs. parents[5] == project root.
_SPEC_ROOT = Path(__file__).resolve().parents[5] / "apps" / "validation-site" / "specs"


# ───────────────────────────────────────────────────────────────────
# Spec loader
# ───────────────────────────────────────────────────────────────────


def load_spec(spec_id: str) -> tuple[PageVerificationSpec, Path]:
    """Load a page spec by id. Returns (spec, source_path)."""
    path = _SPEC_ROOT / f"{spec_id}.assertions.json"
    if not path.exists():
        raise FileNotFoundError(f"Page verification spec not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return PageVerificationSpec(**raw), path


# ───────────────────────────────────────────────────────────────────
# Element matcher
# ───────────────────────────────────────────────────────────────────


def _matches(element: DiscoveredElement, matcher: ElementMatcher) -> bool:
    """Check whether an element matches the predicate.

    Semantics:
      - All specified atomic fields must match (AND)
      - OR the element's generated selector appears in selector_any_of
    """
    if matcher.selector_any_of and element.selector in matcher.selector_any_of:
        return True

    # Gather specified atomic criteria
    atomic = [
        (matcher.id, element.id),
        (matcher.name, element.name),
        (matcher.tag, element.tag),
        (matcher.element_type, element.element_type),
        (matcher.element_value, element.element_value),
        (matcher.role, element.role),
    ]
    for expected, observed in atomic:
        if expected is not None and expected != observed:
            return False

    # Substring checks
    if matcher.text_contains is not None:
        if not element.text or matcher.text_contains not in element.text:
            return False
    if matcher.placeholder_contains is not None:
        if not element.placeholder or matcher.placeholder_contains not in element.placeholder:
            return False
    if matcher.aria_label_contains is not None:
        if not element.aria_label or matcher.aria_label_contains not in element.aria_label:
            return False

    # Must have at least one specified atomic or substring field to match;
    # otherwise an empty matcher would match everything.
    specified = any(x is not None for x, _ in atomic) or any([
        matcher.text_contains, matcher.placeholder_contains, matcher.aria_label_contains,
    ])
    return specified


def _all_elements(analysis: PageAnalysis) -> list[DiscoveredElement]:
    """Flatten all discovered elements (visible + hidden) for matching."""
    return [
        *analysis.fillable,
        *analysis.submit,
        *analysis.clickable,
        *analysis.navigation,
        *analysis.select,
        *analysis.toggle,
        *analysis.other,
        *analysis.hidden_interactive,
    ]


def _find_match(
    elements: list[DiscoveredElement], matcher: ElementMatcher,
) -> DiscoveredElement | None:
    """Return the first element matching the predicate, else None."""
    for el in elements:
        if _matches(el, matcher):
            return el
    return None


def _element_actual_category(
    analysis: PageAnalysis, target: DiscoveredElement,
) -> str | None:
    """Return which category bucket an element lives in."""
    buckets = {
        "fillable": analysis.fillable,
        "submit": analysis.submit,
        "clickable": analysis.clickable,
        "navigation": analysis.navigation,
        "select": analysis.select,
        "toggle": analysis.toggle,
        "other": analysis.other,
    }
    for name, bucket in buckets.items():
        if any(el is target for el in bucket):
            return name
    # hidden_interactive — elements aren't in a visible bucket
    if any(el is target for el in analysis.hidden_interactive):
        return "hidden"
    return None


# ───────────────────────────────────────────────────────────────────
# Per-score check helpers
# ───────────────────────────────────────────────────────────────────


def _check_element(
    spec_el: CriticalElementSpec,
    analysis: PageAnalysis,
    scenario_name: str,
) -> ElementCheck:
    """Check a single critical element's recognition quality."""
    # Skip if this element is only expected in other scenarios
    if spec_el.visible_only_on and scenario_name not in spec_el.visible_only_on:
        return ElementCheck(
            role=spec_el.role,
            skipped=True,
            notes=f"Only expected in {spec_el.visible_only_on}; skipped for '{scenario_name}'.",
        )

    elements = _all_elements(analysis)
    match = _find_match(elements, spec_el.match_by)
    if match is None:
        return ElementCheck(
            role=spec_el.role,
            found=False,
            notes="No element matched the spec predicate.",
        )

    observed_category = _element_actual_category(analysis, match)
    category_match = observed_category == spec_el.expected_category

    # semantic_role is only meaningful for certain expected_category values;
    # if the spec doesn't require one, we don't penalize.
    observed_semantic = getattr(match, "semantic_role", None)
    if spec_el.expected_semantic_role is None:
        semantic_match: bool | None = None
    else:
        semantic_match = observed_semantic == spec_el.expected_semantic_role

    notes_parts = []
    if not category_match:
        notes_parts.append(
            f"category: expected={spec_el.expected_category}, observed={observed_category}",
        )
    if semantic_match is False:
        notes_parts.append(
            f"semantic_role: expected={spec_el.expected_semantic_role}, "
            f"observed={observed_semantic}",
        )

    return ElementCheck(
        role=spec_el.role,
        found=True,
        category_match=category_match,
        semantic_role_match=semantic_match,
        observed_category=observed_category,
        observed_semantic_role=observed_semantic,
        observed_selector=match.selector,
        notes="; ".join(notes_parts) if notes_parts else "OK",
    )


def _check_action(
    expected: str,
    spec_elements_by_role: dict[str, CriticalElementSpec],
    analysis: PageAnalysis,
    steps: list[dict[str, Any]],
) -> ActionCheck:
    """Check whether an expected action was executed against the right element."""
    if ":" not in expected:
        return ActionCheck(expected=expected, executed=False, notes="Malformed expected action.")
    action_type, role = expected.split(":", 1)

    spec_el = spec_elements_by_role.get(role)
    if spec_el is None:
        return ActionCheck(
            expected=expected, executed=False,
            notes=f"No critical_element with role='{role}' declared.",
        )

    target = _find_match(_all_elements(analysis), spec_el.match_by)
    if target is None:
        return ActionCheck(
            expected=expected, executed=False,
            notes=f"Spec element '{role}' was never discovered on the page.",
        )

    # Find a step that matches both action_type and target selector.
    for step in steps:
        if step.get("action_type") != action_type:
            continue
        if not step.get("ok", False):
            continue
        step_selector = step.get("target_selector") or ""
        # Match in two ways: analyzer-generated selector, or by comparing
        # step's target_description against element identifiers.
        if step_selector and step_selector == target.selector:
            return ActionCheck(
                expected=expected, executed=True,
                step_index=step.get("step_index"),
                notes=f"Matched step by selector {step_selector!r}.",
            )
        # Fall back: check if the element's id/name appears in step description
        desc = step.get("target_description") or ""
        if target.id and f"id={target.id}" in desc:
            return ActionCheck(
                expected=expected, executed=True,
                step_index=step.get("step_index"),
                notes=f"Matched step by id={target.id!r} in description.",
            )
        if target.name and f"name={target.name}" in desc:
            return ActionCheck(
                expected=expected, executed=True,
                step_index=step.get("step_index"),
                notes=f"Matched step by name={target.name!r} in description.",
            )

    return ActionCheck(
        expected=expected, executed=False,
        notes=f"No successful {action_type} step targeted {role}.",
    )


def _check_distraction(
    spec_dist: DistractionSpec,
    analysis: PageAnalysis,
    steps: list[dict[str, Any]],
) -> DistractionCheck:
    """Check that no action landed on a distraction element."""
    target = _find_match(_all_elements(analysis), spec_dist.match_by)
    if target is None:
        return DistractionCheck(
            role=spec_dist.role, hit=False,
            notes="Distraction not present on page (spec mismatch or page changed).",
        )

    for step in steps:
        if step.get("action_type") not in ("click", "fill", "press"):
            continue
        step_selector = step.get("target_selector") or ""
        if step_selector == target.selector:
            return DistractionCheck(
                role=spec_dist.role, hit=True,
                hit_by_step_index=step.get("step_index"),
                notes=f"Action step {step.get('step_index')} targeted this distraction.",
            )

    return DistractionCheck(role=spec_dist.role, hit=False, notes="Not targeted — OK.")


def _check_success_signals(
    result: AutonomousExplorationResult,
    scenario: ScenarioSpec,  # noqa: F821
) -> list[str]:
    """Return list of failure notes (empty = all signals pass)."""
    s = scenario.success_signals
    notes: list[str] = []
    final_state = result.final_state or {}
    body_text = final_state.get("body_text", "") or ""
    test_ids = final_state.get("test_ids", []) or []

    if s.url_contains and s.url_contains not in (result.final_url or ""):
        notes.append(f"url_contains: expected '{s.url_contains}' in final_url")
    if s.title_contains and s.title_contains not in (result.final_title or ""):
        notes.append(f"title_contains: expected '{s.title_contains}' in final_title")
    for needle in s.dom_contains_all_of:
        if needle not in body_text:
            notes.append(f"dom_contains_all_of: missing '{needle}' in body text")
    if s.dom_contains_any_of:
        if not any(n in body_text for n in s.dom_contains_any_of):
            notes.append(f"dom_contains_any_of: none of {s.dom_contains_any_of} in body text")
    if s.dom_has_test_id and s.dom_has_test_id not in test_ids:
        notes.append(f"dom_has_test_id: '{s.dom_has_test_id}' not found")
    return notes


def _check_failure_signals(
    result: AutonomousExplorationResult,
    scenario: ScenarioSpec,  # noqa: F821
) -> list[str]:
    """Return list of failure notes (empty = all signals pass)."""
    f = scenario.failure_signals
    notes: list[str] = []
    final_state = result.final_state or {}
    alert_texts = final_state.get("alert_texts", []) or []

    if f.url_contains and f.url_contains not in (result.final_url or ""):
        notes.append(f"url_contains: expected '{f.url_contains}' in final_url")
    if f.alert_visible is True and not alert_texts:
        notes.append("alert_visible: expected at least one visible role=alert, none found")
    if f.alert_text_contains_any_of:
        joined = " | ".join(alert_texts)
        if not any(n in joined for n in f.alert_text_contains_any_of):
            notes.append(
                f"alert_text_contains_any_of: none of {f.alert_text_contains_any_of} "
                f"found in alert texts {alert_texts!r}",
            )
    return notes


def _check_verdict(
    result: AutonomousExplorationResult,
    scenario: ScenarioSpec,  # noqa: F821 — forward ref to avoid cycle
) -> VerdictCheck:
    self_verdict = result.verdict
    expected = scenario.expected_verdict
    expected_not = scenario.expected_verdict_not
    must_not_transition = scenario.must_not_transition_to
    final_url = result.final_url

    matches = True
    notes_parts: list[str] = []

    if expected is not None and self_verdict != expected:
        matches = False
        notes_parts.append(f"expected verdict '{expected}', got '{self_verdict}'")
    if expected_not is not None and self_verdict == expected_not:
        matches = False
        notes_parts.append(f"verdict must not be '{expected_not}', but it is")
    if must_not_transition is not None and must_not_transition in (final_url or ""):
        matches = False
        notes_parts.append(
            f"final_url must not transition to '{must_not_transition}', "
            f"but got '{final_url}'",
        )

    # Signal checks — tied to scenario expectation, not self verdict
    if expected == "success":
        signal_notes = _check_success_signals(result, scenario)
        if signal_notes:
            matches = False
            notes_parts.extend(signal_notes)
    elif expected_not == "success":
        signal_notes = _check_failure_signals(result, scenario)
        if signal_notes:
            matches = False
            notes_parts.extend(signal_notes)

    return VerdictCheck(
        self_verdict=self_verdict,
        expected_verdict=expected,
        expected_verdict_not=expected_not,
        must_not_transition_to=must_not_transition,
        final_url=final_url,
        matches_expectation=matches,
        notes="OK" if matches else "; ".join(notes_parts),
    )


def _check_supervisor(
    result: AutonomousExplorationResult,
    scenario: ScenarioSpec,  # noqa: F821
) -> SupervisorCheck:
    """Agreement between LLM observation and scenario intent.

    New contract: the LLM reports ``scenario_goal_observed`` (did the
    thing the scenario is checking for happen) with a short
    ``scenario_goal_evidence`` quote. Agreement is graded on those
    two atoms, not on a verdict bucket:

      * ``scenario_goal_observed=true`` + evidence non-empty → 1.0
      * ``scenario_goal_observed=true`` + evidence empty     → 0.5
      * ``scenario_goal_observed=false`` OR observations missing → 0.0

    Rationale: under the old contract the LLM returned a verdict
    directly, and the supervisor_agreement check compared it to
    the scenario's expected bucket. That contract proved unsafe —
    reasoning models talked themselves out of mechanical rules. The
    new contract removes the LLM's verdict pen; agreement now
    measures whether the LLM *saw what the scenario was checking
    for*, with evidence. See project_supervisor_verdict_override_plan.md.
    """
    supervisor = result.supervisor or {}
    observations = supervisor.get("observations") or {}
    goal_observed = observations.get("scenario_goal_observed")
    evidence = (observations.get("scenario_goal_evidence") or "").strip()
    # The derived verdict for reporting — what the LLM-observed
    # atoms implied after derivation. Still surfaced so the
    # SupervisorCheck record is useful for audit.
    sup_verdict = supervisor.get("verdict")

    expected = scenario.expected_verdict
    expected_not = scenario.expected_verdict_not
    if expected == "success":
        expected_bucket = "success"
    elif expected_not == "success":
        expected_bucket = "non_success"
    elif expected is not None:
        expected_bucket = expected
    else:
        expected_bucket = "unspecified"

    if not supervisor:
        score, note = 0.0, "supervisor block missing"
    elif not observations:
        # Fallback mode or schema failure — no atoms to grade.
        score, note = 0.0, "no supervisor observations available"
    elif goal_observed is True and evidence:
        score, note = 1.0, (
            f"LLM observed scenario goal ({expected_bucket}) with evidence"
        )
    elif goal_observed is True and not evidence:
        score, note = 0.5, (
            "LLM reported scenario_goal_observed=true but cited no evidence"
        )
    elif goal_observed is False:
        score, note = 0.0, (
            "LLM reported scenario_goal_observed=false — did not see the "
            "thing the scenario is checking for"
        )
    else:
        score, note = 0.0, (
            "scenario_goal_observed atom missing from LLM response"
        )

    return SupervisorCheck(
        supervisor_verdict=sup_verdict,
        expected_bucket=expected_bucket,
        score=score,
        notes=note,
    )


# ───────────────────────────────────────────────────────────────────
# Top-level comparator
# ───────────────────────────────────────────────────────────────────


def verify_against_spec(
    result: AutonomousExplorationResult,
    spec: PageVerificationSpec,
    scenario_name: str,
) -> PageVerificationScorecard:
    """Run all 5 checks and return a scorecard.

    Raises KeyError if scenario_name isn't in spec.scenarios.
    """
    if scenario_name not in spec.scenarios:
        raise KeyError(
            f"Scenario '{scenario_name}' not in spec '{spec.page_id}'. "
            f"Available: {list(spec.scenarios.keys())}",
        )

    scenario = spec.scenarios[scenario_name]
    analysis = result.page_analysis
    steps = result.steps

    # 1. Element recognition
    element_checks = [_check_element(ce, analysis, scenario_name) for ce in spec.critical_elements]
    applicable = [c for c in element_checks if not c.skipped]
    if applicable:
        fully_correct = sum(
            1 for c in applicable
            if c.found and c.category_match and (c.semantic_role_match is not False)
        )
        element_score = fully_correct / len(applicable)
    else:
        element_score = 1.0  # nothing to check → trivially ok

    # 2. Action coverage
    spec_elements_by_role = {ce.role: ce for ce in spec.critical_elements}
    action_checks = [
        _check_action(exp, spec_elements_by_role, analysis, steps)
        for exp in scenario.expected_actions
    ]
    if action_checks:
        action_score = sum(1 for c in action_checks if c.executed) / len(action_checks)
    else:
        action_score = 1.0

    # 3. Verdict accuracy
    verdict_check = _check_verdict(result, scenario)
    verdict_score = 1.0 if verdict_check.matches_expectation else 0.0

    # 4. Distraction avoidance
    distraction_checks = [_check_distraction(d, analysis, steps) for d in spec.distractions]
    if distraction_checks:
        hits = sum(1 for c in distraction_checks if c.hit)
        distraction_score = 1.0 - (hits / len(distraction_checks))
    else:
        distraction_score = 1.0

    # 5. Supervisor agreement
    supervisor_check = _check_supervisor(result, scenario)
    supervisor_score = supervisor_check.score

    # Strict pass gate — see PassGate docstring for rationale.
    pass_gate = _compute_pass_gate(
        result=result,
        element_score=element_score,
        action_score=action_score,
        verdict_check=verdict_check,
        distraction_score=distraction_score,
        supervisor_check=supervisor_check,
    )

    return PageVerificationScorecard(
        page_id=spec.page_id,
        scenario=scenario_name,
        element_recognition=ScoreBlock(
            score=element_score,
            weight_note="Fraction of critical elements found and classified correctly.",
        ),
        element_checks=element_checks,
        action_coverage=ScoreBlock(
            score=action_score,
            weight_note="Fraction of expected actions executed against the right target.",
        ),
        action_checks=action_checks,
        verdict_accuracy=ScoreBlock(
            score=verdict_score,
            weight_note="1 if self-verdict and must_not_transition_to both hold; else 0.",
        ),
        verdict_check=verdict_check,
        distraction_avoidance=ScoreBlock(
            score=distraction_score,
            weight_note="1 minus fraction of distraction elements that actions landed on.",
        ),
        distraction_checks=distraction_checks,
        supervisor_agreement=ScoreBlock(
            score=supervisor_score,
            weight_note="Coarse 3-bucket agreement: "
            "exact=1, uncertain-vs-non-success=0.5, conflict=0.",
        ),
        supervisor_check=supervisor_check,
        pass_gate=pass_gate,
    )


def _compute_pass_gate(
    *,
    result: AutonomousExplorationResult,
    element_score: float,
    action_score: float,
    verdict_check: VerdictCheck,
    distraction_score: float,
    supervisor_check: SupervisorCheck,
) -> PassGate:
    """Derive the binary pass / fail / unverified status.

    Every gate must be true for ``pass``. A single failure degrades to
    ``fail`` (concrete spec deviation) or ``unverified`` (LLM couldn't
    or didn't validate). See `PassGate` in schemas for the rationale.

    Gate ordering matters for the ``reasons`` list — spec deviations
    surface before LLM-availability issues so the most action-relevant
    reason is first.
    """
    fail_reasons: list[str] = []
    unverified_reasons: list[str] = []

    # Gate 1 — spec deviations (hard fails)
    if not verdict_check.matches_expectation:
        fail_reasons.append(
            f"rule-side verdict did not match scenario expectation: "
            f"{verdict_check.notes or 'see verdict_check'}",
        )
    if element_score < 1.0:
        fail_reasons.append(
            f"element recognition score {element_score:.2f} < 1.0 — "
            f"one or more critical elements missing or mis-classified",
        )
    if action_score < 1.0:
        fail_reasons.append(
            f"action coverage score {action_score:.2f} < 1.0 — "
            f"an expected action was not executed against the right target",
        )
    if distraction_score < 1.0:
        fail_reasons.append(
            f"distraction avoidance score {distraction_score:.2f} < 1.0 — "
            f"planner hit a distractor element",
        )

    # Gate 2 — supervisor availability + observation completeness.
    # Mechanics may be fine but if the LLM didn't (or couldn't)
    # cross-check, the run is unverified — neither a clean pass nor a
    # concrete fail.
    supervisor = result.supervisor or {}
    source = supervisor.get("_supervisor_source") or supervisor.get("source")
    if source == "fallback":
        error_kind = (
            supervisor.get("_supervisor_error_kind")
            or supervisor.get("error_kind")
            or "unknown"
        )
        unverified_reasons.append(
            f"supervisor ran in fallback mode (error_kind={error_kind}) — "
            f"LLM did not independently verify this run",
        )
    else:
        if not supervisor:
            unverified_reasons.append("supervisor block missing entirely")
        else:
            # Under the observation-atom contract the LLM no longer
            # emits a confidence field. The equivalent signal is the
            # partial-parse flag: if any critical atom was missing
            # from the LLM response, the observation side isn't
            # complete and we can't claim a verified pass.
            if supervisor.get("_supervisor_partial_parse") is True:
                unverified_reasons.append(
                    "supervisor response was partially parsed — one or "
                    "more critical observation atoms were missing",
                )
            if supervisor_check.score < 1.0:
                unverified_reasons.append(
                    f"supervisor_agreement score {supervisor_check.score} < 1.0: "
                    f"{supervisor_check.notes}",
                )

    if fail_reasons:
        return PassGate(status="fail", reasons=fail_reasons + unverified_reasons)
    if unverified_reasons:
        return PassGate(status="unverified", reasons=unverified_reasons)
    return PassGate(status="pass", reasons=[])
