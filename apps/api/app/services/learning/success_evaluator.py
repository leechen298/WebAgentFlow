"""Success criteria evaluator.

Evaluates a set of SuccessConditions against before/after page state.
Pure logic — no I/O, no runtime dependency, fully synchronous.

Supported condition types (Google MVP):
  - url_changed     : URL differs from before-state
  - url_contains    : Post-action URL contains a substring
  - title_contains  : Post-action title contains a substring
  - element_present : A CSS selector matches at least one element in post-action HTML
  - html_changed    : HTML content hash differs from before-state
  - no_error        : The execution result reported no error
"""

from __future__ import annotations

import logging
from typing import Any

from app.schemas.observation import PostActionObservation
from app.schemas.success_criteria import (
    SuccessCondition,
    SuccessEvaluation,
)

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────
# Before-state snapshot (lightweight dict)
# ───────────────────────────────────────────────────────────────────

def make_before_state(
    *,
    url: str = "",
    title: str = "",
    html_hash: str = "",
) -> dict[str, str]:
    """Build a before-state dict for the evaluator."""
    return {"url": url, "title": title, "html_hash": html_hash}


# ───────────────────────────────────────────────────────────────────
# Individual condition checkers
# ───────────────────────────────────────────────────────────────────

def _check_url_changed(
    before: dict[str, str],
    obs: PostActionObservation,
    condition: SuccessCondition,
    _variables: dict[str, Any],
) -> bool:
    return obs.url_changed or (obs.url != "" and obs.url != before.get("url", ""))


def _check_url_contains(
    before: dict[str, str],
    obs: PostActionObservation,
    condition: SuccessCondition,
    variables: dict[str, Any],
) -> bool:
    value = _resolve_value(condition, variables)
    if not value:
        return False
    return value in obs.url


def _check_title_contains(
    before: dict[str, str],
    obs: PostActionObservation,
    condition: SuccessCondition,
    variables: dict[str, Any],
) -> bool:
    value = _resolve_value(condition, variables)
    if not value:
        return False
    return value.lower() in obs.title.lower()


def _check_element_present(
    before: dict[str, str],
    obs: PostActionObservation,
    condition: SuccessCondition,
    variables: dict[str, Any],
) -> bool:
    # element_present checks against the post-action HTML snapshot ref.
    # In the current Phase 7E implementation, we don't have parsed HTML
    # readily available — only html_snapshot_ref (a hash). For the MVP,
    # we check target.still_present as a proxy when no selector is given.
    value = _resolve_value(condition, variables)
    if not value:
        # No specific selector — fall back to target post-state
        if obs.target.still_present is not None:
            return obs.target.still_present
        return False
    # With a selector, we'd need parsed HTML or a runtime query.
    # For now, log a warning and return uncertain.
    logger.warning(
        "element_present with selector '%s' requires runtime query — "
        "not yet supported in offline evaluation, returning False",
        value,
    )
    return False


def _check_html_changed(
    before: dict[str, str],
    obs: PostActionObservation,
    condition: SuccessCondition,
    _variables: dict[str, Any],
) -> bool:
    if obs.html_changed:
        return True
    before_hash = before.get("html_hash", "")
    if before_hash and obs.html_hash:
        return before_hash != obs.html_hash
    return False


def _check_no_error(
    before: dict[str, str],
    obs: PostActionObservation,
    condition: SuccessCondition,
    _variables: dict[str, Any],
) -> bool:
    # no_error is true when there are no warnings indicating failure.
    # The evaluator doesn't directly receive ExecutionResult.error —
    # that check should be done by the caller before invoking evaluation.
    # Here we just check that observation itself is non-degenerate.
    return obs.url != "" or obs.title != ""


_CHECKERS = {
    "url_changed": _check_url_changed,
    "url_contains": _check_url_contains,
    "title_contains": _check_title_contains,
    "element_present": _check_element_present,
    "html_changed": _check_html_changed,
    "no_error": _check_no_error,
}


# ───────────────────────────────────────────────────────────────────
# Value resolution
# ───────────────────────────────────────────────────────────────────

def _resolve_value(
    condition: SuccessCondition,
    variables: dict[str, Any],
) -> str | None:
    """Resolve condition value, with value_from taking precedence."""
    if condition.value_from:
        resolved = variables.get(condition.value_from)
        if resolved is not None:
            return str(resolved)
        logger.warning(
            "value_from='%s' not found in variables, falling back to static value",
            condition.value_from,
        )
    return condition.value


# ───────────────────────────────────────────────────────────────────
# Main evaluator
# ───────────────────────────────────────────────────────────────────

def evaluate_success(
    conditions: list[SuccessCondition],
    before_state: dict[str, str],
    observation: PostActionObservation,
    *,
    variables: dict[str, Any] | None = None,
    execution_error: str | None = None,
) -> SuccessEvaluation:
    """Evaluate success conditions against before/after page state.

    Args:
        conditions: Flat list of conditions, AND relationship.
        before_state: Dict from ``make_before_state()``.
        observation: PostActionObservation from Phase 7E.
        variables: Task variables for value_from resolution.
        execution_error: If the execution itself reported an error,
            short-circuit to failure.

    Returns:
        SuccessEvaluation with three-state semantics.
    """
    variables = variables or {}
    evidence: dict[str, Any] = {
        "url_before": before_state.get("url", ""),
        "url_after": observation.url,
        "title_after": observation.title,
        "html_changed": observation.html_changed,
    }

    # Short-circuit: execution error means no_error condition fails
    if execution_error:
        evidence["execution_error"] = execution_error
        return SuccessEvaluation(
            satisfied=False,
            confidence="high",
            failed_conditions=["execution_error"],
            evidence=evidence,
        )

    if not conditions:
        # No conditions defined — weak success (nothing to fail)
        return SuccessEvaluation(
            satisfied=True,
            confidence="low",
            evidence=evidence,
            uncertain_reason="No conditions defined — vacuous success.",
        )

    matched: list[str] = []
    failed_required: list[str] = []
    failed_optional: list[str] = []

    for condition in conditions:
        checker = _CHECKERS.get(condition.type)
        if checker is None:
            logger.warning("Unknown condition type: %s, skipping", condition.type)
            continue

        result = checker(before_state, observation, condition, variables)
        label = condition.type
        if condition.value or condition.value_from:
            label = f"{condition.type}({condition.value or condition.value_from})"

        if result:
            matched.append(label)
        elif condition.required:
            failed_required.append(label)
        else:
            failed_optional.append(label)

    # Determine outcome
    satisfied = len(failed_required) == 0
    total = len(matched) + len(failed_required) + len(failed_optional)
    match_ratio = len(matched) / total if total > 0 else 0.0

    if satisfied and match_ratio >= 0.8:
        confidence = "high"
    elif satisfied and match_ratio >= 0.5:
        confidence = "medium"
    else:
        confidence = "low" if not satisfied and len(failed_required) <= 1 else "high"

    # Determine uncertain_reason
    uncertain_reason = None
    if not satisfied and confidence == "low":
        uncertain_reason = (
            f"Only 1 required condition failed ({failed_required[0]}), "
            f"but {len(matched)} conditions passed — may be transient."
        )

    # Determine strength
    from app.models.success_criteria import SuccessCriteriaStrength
    strength = (
        SuccessCriteriaStrength.STRONG
        if satisfied and confidence == "high"
        else SuccessCriteriaStrength.WEAK
    )

    return SuccessEvaluation(
        satisfied=satisfied,
        strength=strength,
        confidence=confidence,
        matched_conditions=matched,
        failed_conditions=failed_required,
        evidence=evidence,
        uncertain_reason=uncertain_reason,
    )
