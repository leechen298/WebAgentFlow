"""Action planner — generates an action sequence from page analysis.

Takes a PageAnalysis (discovered elements) and an optional goal, then
produces an ordered list of PlannedActions. No site-specific logic.

Planning heuristics (rule-based for MVP):
  1. If fillable elements exist → fill the most prominent one
  2. If submit elements exist → click the most prominent one
  3. If neither → try pressing Enter after fill
  4. Always end with an observe step
"""

from __future__ import annotations

import logging

from app.schemas.page_analysis import (
    DiscoveredElement,
    PageAnalysis,
    PlannedAction,
)

logger = logging.getLogger(__name__)


# Generic action verbs used as weak prominence signals during ranking.
# These are NOT classification criteria — classification uses only structural
# signals (tag/type/role/form context). These verbs appear in submit buttons
# across many locales. Site-specific brand names (baidu/bing/google) are
# intentionally excluded; if per-site dictionaries are ever needed, they
# should live in a separate data/config repo, not in this module.
_GENERIC_SUBMIT_VERBS = (
    "search", "submit", "go", "ok", "confirm", "apply",
    "搜索", "提交", "查询", "确定", "确认",
    "検索", "送信",
)


def _score_fillable(el: DiscoveredElement) -> float:
    """Score a fillable element by prominence using structural signals only.

    Higher score = more likely to be the main user-facing input. Uses tag,
    role, size, position, and presence of labels — not text content.
    """
    score = 0.0
    area = el.rect.get("w", 0) * el.rect.get("h", 0)
    score += min(area / 1000.0, 50.0)  # Size — bigger inputs usually matter more

    # Central vertical position bonus (main content is typically 100-500px from top)
    y = el.rect.get("y", 0)
    if 100 < y < 500:
        score += 20

    # Having ANY accessible label is a signal of purposeful input
    if el.placeholder:
        score += 10
    if el.name:
        score += 5
    if el.aria_label:
        score += 5

    # Role signals — searchbox/combobox are stronger signals than generic textbox
    if el.role in ("searchbox", "combobox"):
        score += 20
    if el.role == "textbox":
        score += 10

    # Textarea gets a slight boost (usually more prominent than small inputs)
    if el.tag == "textarea":
        score += 5

    return score


def _score_submit(el: DiscoveredElement) -> float:
    """Score a submit element by prominence.

    Submit classification already happened structurally in the analyzer.
    This function ranks among submits by prominence signals: size, type,
    and a weak generic-verb match (generic verbs only — no site names).
    """
    score = 0.0
    area = el.rect.get("w", 0) * el.rect.get("h", 0)
    score += min(area / 500.0, 30.0)

    # Explicit type=submit is a stronger signal than "button inside form"
    if el.element_type == "submit":
        score += 20

    # Non-hidden position
    if el.rect.get("y", 0) > 100:
        score += 10

    # Weak signal: button text contains a generic submit verb
    text_lower = (el.text or "").lower()
    if text_lower and any(v in text_lower for v in _GENERIC_SUBMIT_VERBS):
        score += 15

    return score


def _center(r: dict) -> tuple[float, float]:
    """Center point of a bounding rect."""
    return (
        r.get("x", 0) + r.get("w", 0) / 2,
        r.get("y", 0) + r.get("h", 0) / 2,
    )


def _distance(a: DiscoveredElement, b: DiscoveredElement) -> float:
    """Euclidean distance between the centers of two elements."""
    ax, ay = _center(a.rect)
    bx, by = _center(b.rect)
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5


def _score_fallback_submit(el: DiscoveredElement, fillable: DiscoveredElement) -> float:
    """Score a clickable as a potential submit, relative to a fillable element.

    Used when analysis.submit is empty (e.g., SPA without <form> wrapper).
    Signals are purely structural + generic verb (no site names):
      - Close to the fillable element (proximity)
      - Has reasonable size (not hidden-by-opacity)
      - Generic submit verb in text (weak signal)
    """
    score = 0.0

    # Size: reasonable clickable area
    area = el.rect.get("w", 0) * el.rect.get("h", 0)
    if area < 200:  # too small to be a real button
        return -1.0
    score += min(area / 500.0, 30.0)

    # Proximity to the fillable element — closer = higher score.
    # 200px away = 0 bonus, 0px = 40 bonus.
    dist = _distance(el, fillable)
    proximity_bonus = max(0.0, 40.0 - dist / 5.0)
    score += proximity_bonus

    # Generic submit verb as weak signal (same as _score_submit — no site names)
    text_lower = (el.text or "").lower()
    if text_lower and any(v in text_lower for v in _GENERIC_SUBMIT_VERBS):
        score += 15

    # <button> is a slightly stronger submit candidate than role="button" div
    if el.tag == "button":
        score += 5

    return score


def _find_fallback_submit(
    fillable: DiscoveredElement,
    clickables: list[DiscoveredElement],
) -> tuple[DiscoveredElement, float] | None:
    """Pick the best clickable to use as a fallback submit.

    Returns (element, score) or None if no clickable is a reasonable candidate.
    """
    if not clickables:
        return None
    ranked = [
        (el, _score_fallback_submit(el, fillable))
        for el in clickables
    ]
    ranked = [(el, s) for el, s in ranked if s > 0]
    if not ranked:
        return None
    ranked.sort(key=lambda pair: pair[1], reverse=True)
    return ranked[0]


def _match_fillable_for_role(
    role: str,
    fillables: list[DiscoveredElement],
    already_used: set[str],
) -> DiscoveredElement | None:
    """Pick the best fillable element for a given semantic role key.

    Exact semantic_role match wins; fallback to the highest-scored fillable
    that doesn't already have a semantic mismatch (e.g. don't put 'username'
    into a password field).
    """
    role_lower = role.lower()

    # Strict match by semantic_role
    exact = [
        e for e in fillables
        if e.semantic_role == role_lower and e.selector not in already_used
    ]
    if exact:
        exact.sort(key=_score_fillable, reverse=True)
        return exact[0]

    # If role is 'text' (generic), any un-used 'text' fillable is fine
    if role_lower == "text":
        candidates = [
            e for e in fillables
            if (e.semantic_role in (None, "text"))
            and e.selector not in already_used
        ]
        if candidates:
            candidates.sort(key=_score_fillable, reverse=True)
            return candidates[0]

    # Last resort: pick the highest-scored fillable that is NOT a type mismatch.
    # A 'username' slot should not fall back to a password input, etc.
    # Password is the only role with broad mismatch rules because
    # password fields are visually / structurally distinct; the new
    # name / role / status slots only need protection against password.
    mismatched = {
        "username": {"password", "email"},
        "email": {"password"},
        "name": {"password"},
        "role": {"password"},
        "status": {"password"},
        "password": {
            "username", "email", "search", "text",
            "name", "role", "status",
        },
    }
    forbidden = mismatched.get(role_lower, set())
    loose = [
        e for e in fillables
        if e.selector not in already_used
        and (e.semantic_role not in forbidden)
    ]
    if loose:
        loose.sort(key=_score_fillable, reverse=True)
        return loose[0]

    return None


def plan_actions(
    analysis: PageAnalysis,
    *,
    goal: str = "",
    fill_value: str = "",
    fill_values: dict[str, str] | None = None,
) -> list[PlannedAction]:
    """Generate an action plan from page analysis results.

    Args:
        analysis: Page analysis with discovered elements.
        goal: Optional goal description (for future LLM planner).
        fill_value: Single-field value mode. Filled into the highest-scored
            fillable. Ignored if ``fill_values`` is provided.
        fill_values: Multi-field mode. Dict keyed by semantic role
            (username/email/name/role/status/search/text/password) → value.
            Each key is matched to the best-fitting fillable.

    Returns:
        Ordered list of PlannedActions.
    """
    actions: list[PlannedAction] = []
    step = 0
    best_input: DiscoveredElement | None = None
    last_filled: DiscoveredElement | None = None  # for Enter-fallback

    # --- Multi-field mode (preferred when fill_values is set) ---
    if fill_values and analysis.fillable:
        used: set[str] = set()
        # Canonical fill order for typical login-like flows and admin
        # filters: identity first (username/email), then admin table
        # filters (name/role/status), then generic search/text, and
        # password last (password fields often trigger additional
        # validation on blur in some SPAs).
        _ROLE_ORDER = [
            "username", "email",
            "name", "role", "status",
            "search", "text",
            "password",
        ]
        order = sorted(
            fill_values.keys(),
            key=lambda k: _ROLE_ORDER.index(k) if k in _ROLE_ORDER else 99,
        )
        for role in order:
            value = fill_values[role]
            target = _match_fillable_for_role(role, analysis.fillable, used)
            if target is None:
                continue
            used.add(target.selector)
            actions.append(PlannedAction(
                step=step,
                action_type="fill",
                target_selector=target.selector,
                target_description=_describe(target),
                value=value,
                reason=f"Multi-field match: role={role!r} → "
                       f"semantic_role={target.semantic_role!r} "
                       f"(score={_score_fillable(target):.0f}). "
                       f"{target.reason}",
            ))
            last_filled = target
            if best_input is None:
                best_input = target
            step += 1

    # --- Single-field fill mode (legacy, only if no fill_values) ---
    elif analysis.fillable:
        ranked_fillable = sorted(
            analysis.fillable, key=_score_fillable, reverse=True,
        )
        best_input = ranked_fillable[0]

        if fill_value:
            actions.append(PlannedAction(
                step=step,
                action_type="fill",
                target_selector=best_input.selector,
                target_description=_describe(best_input),
                value=fill_value,
                reason=f"Highest-scored fillable element "
                       f"(score={_score_fillable(best_input):.0f}). "
                       f"{best_input.reason}",
            ))
            last_filled = best_input
            step += 1

    # --- Find best submit element ---
    #  1. Prefer structurally-classified submit (analysis.submit)
    #  2. Fall back to proximity-based pick from clickables
    #  3. Fall back to pressing Enter on the fillable
    if analysis.submit:
        ranked_submit = sorted(analysis.submit, key=_score_submit, reverse=True)
        best_submit = ranked_submit[0]
        actions.append(PlannedAction(
            step=step,
            action_type="click",
            target_selector=best_submit.selector,
            target_description=_describe(best_submit),
            reason=f"Highest-scored submit element "
                   f"(score={_score_submit(best_submit):.0f}). "
                   f"text='{best_submit.text[:30]}'",
        ))
        step += 1
    elif best_input is not None and analysis.clickable:
        fallback = _find_fallback_submit(best_input, analysis.clickable)
        if fallback is not None:
            candidate, score = fallback
            actions.append(PlannedAction(
                step=step,
                action_type="click",
                target_selector=candidate.selector,
                target_description=_describe(candidate),
                reason=f"No structural submit found. Fallback candidate from "
                       f"clickables (score={score:.0f}): proximity to fillable, "
                       f"size, generic verb signals. text='{candidate.text[:30]}'",
            ))
            step += 1
        elif last_filled is not None:
            actions.append(PlannedAction(
                step=step,
                action_type="press",
                target_selector=last_filled.selector,
                target_description=_describe(last_filled),
                value="Enter",
                reason="No submit and no suitable clickable candidate. "
                       "Pressing Enter on the last filled input.",
            ))
            step += 1
    elif last_filled is not None:
        # Has fillable but nothing submit-like — try Enter on last filled
        actions.append(PlannedAction(
            step=step,
            action_type="press",
            target_selector=last_filled.selector,
            target_description=_describe(last_filled),
            value="Enter",
            reason="No submit button found. Pressing Enter on the last filled input.",
        ))
        step += 1

    # --- Always end with observe ---
    actions.append(PlannedAction(
        step=step,
        action_type="observe",
        target_selector="",
        target_description="Wait and observe the result page",
        reason="Capture final state after all actions.",
    ))

    logger.info(
        "Planned %d actions for %s (fillable=%d, submit=%d)",
        len(actions), analysis.url, len(analysis.fillable), len(analysis.submit),
    )
    return actions


def _describe(el: DiscoveredElement) -> str:
    """Human-readable description of an element."""
    parts = [f"<{el.tag}>"]
    if el.id:
        parts.append(f"id={el.id}")
    if el.name:
        parts.append(f"name={el.name}")
    if el.role:
        parts.append(f"role={el.role}")
    if el.text:
        parts.append(f"text='{el.text[:30]}'")
    if el.placeholder:
        parts.append(f"placeholder='{el.placeholder[:30]}'")
    return " ".join(parts)
