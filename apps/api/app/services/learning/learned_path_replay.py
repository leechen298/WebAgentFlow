"""LearnedPath replay drift checker.

Determines whether a stored LearnedPath can be replayed against the
current page state.  This module does NOT execute actions — that is the
responsibility of the shared action executor (10.2.4).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from playwright.sync_api import Page

from app.models.learned_path import LearnedPath
from app.schemas.learned_path_replay import (
    ReplayAction,
    ReplayDriftStatus,
    ReplayStatus,
)
from app.schemas.page_analysis import PageAnalysis
from app.services.learning.page_signature import (
    build_signature_dict,
    path_template,
)

SUPPORTED_ACTION_TYPES = {"fill", "click", "press", "observe"}


# ---------------------------------------------------------------------------
# Drift precheck result
# ---------------------------------------------------------------------------


@dataclass
class DriftPrecheckResult:
    """Outcome of the replay drift precheck.

    When ``blocked`` is True the caller should abort replay and report
    ``blocked_status`` as the final ``ReplayResult.status``.

    When ``blocked`` is False the caller may proceed to action execution
    (if ``actions`` is non-empty) or report ``observed`` (if ``actions``
    is empty).
    """

    drift_status: ReplayDriftStatus
    drift_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blocked: bool = True
    blocked_status: ReplayStatus | None = None
    actions: list[ReplayAction] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_replay_actions(raw_actions: list[dict[str, Any]]) -> list[ReplayAction]:
    """Convert raw stored actions into validated ``ReplayAction`` objects.

    ``step`` defaults to the list index when missing in storage.
    """
    result: list[ReplayAction] = []
    for idx, raw in enumerate(raw_actions):
        step = raw.get("step", idx)
        action_type = str(raw.get("action_type", "")).lower()
        result.append(
            ReplayAction(
                step=step,
                action_type=action_type,
                target_selector=raw.get("target_selector"),
                target_description=raw.get("target_description"),
                value=raw.get("value"),
            )
        )
    return result


def _count_selector_matches(page: Page, selector: str | None) -> int:
    """Return how many elements match *selector* on the current page."""
    if not selector:
        return 0
    try:
        return page.locator(selector).count()
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Drift precheck
# ---------------------------------------------------------------------------


def run_drift_precheck(
    learned_path: LearnedPath,
    current_url: str,
    current_analysis: PageAnalysis,
    page: Page,
) -> DriftPrecheckResult:
    """Compare a stored LearnedPath against the current page state.

    Evaluation order:

    1. **page_mismatch** — current ``page_template`` differs from stored.
       Blocked; status ``drifted``.
    2. **signature_changed** — ``query_signature`` or ``dom_fingerprint``
       differs while template matches.  Non-fatal warning; replay may
       proceed if selectors are still locatable.
    3. **unsupported_action** — an action type is outside the supported
       set (``fill`` / ``click`` / ``press`` / ``observe``).
       Blocked; status ``unsupported``.
    4. **target_missing** — a supported non-``observe`` action has a
       selector that matches zero elements.
       Blocked; status ``drifted``.
    5. **none** — everything aligns.  Not blocked.

    For observational paths (``actions=[]``) the result is never blocked
    by selector checks; the caller should surface ``observed`` as the
    final status.
    """
    # Current signature
    current_sig = build_signature_dict(url=current_url, analysis=current_analysis)
    current_page_template = current_sig["page_template"]

    stored_page_template = learned_path.page_template
    stored_query_sig = learned_path.query_signature or {}
    stored_dom_fp = learned_path.dom_fingerprint

    # 1. page_mismatch
    if current_page_template != stored_page_template:
        return DriftPrecheckResult(
            drift_status="page_mismatch",
            drift_reasons=[
                f"Page template mismatch: expected {stored_page_template!r}, "
                f"got {current_page_template!r}"
            ],
            blocked=True,
            blocked_status="drifted",
        )

    # 2. signature_changed
    signature_changed = (
        current_sig["query_signature"] != stored_query_sig
        or current_sig["dom_fingerprint"] != stored_dom_fp
    )
    warnings: list[str] = []
    if signature_changed:
        warnings.append(
            "Signature changed: query_signature or dom_fingerprint "
            "differs from stored values"
        )

    # Build actions from storage
    raw_actions = learned_path.actions or []
    replay_actions = _build_replay_actions(raw_actions)

    # 3. unsupported_action
    for action in replay_actions:
        if action.action_type not in SUPPORTED_ACTION_TYPES:
            return DriftPrecheckResult(
                drift_status="unsupported_action",
                drift_reasons=[
                    f"Unsupported action type {action.action_type!r} at step {action.step}"
                ],
                warnings=warnings,
                blocked=True,
                blocked_status="unsupported",
            )

    # 4. target_missing (skip observe actions)
    for action in replay_actions:
        if action.action_type == "observe":
            continue
        count = _count_selector_matches(page, action.target_selector)
        if count == 0:
            return DriftPrecheckResult(
                drift_status="target_missing",
                drift_reasons=[
                    f"Target missing for step {action.step} "
                    f"(selector={action.target_selector!r})"
                ],
                warnings=warnings,
                blocked=True,
                blocked_status="drifted",
            )

    # 5. Final drift status
    drift_status: ReplayDriftStatus = (
        "signature_changed" if signature_changed else "none"
    )

    # Observational path — caller will report observed
    return DriftPrecheckResult(
        drift_status=drift_status,
        warnings=warnings,
        blocked=False,
        actions=replay_actions,
    )
