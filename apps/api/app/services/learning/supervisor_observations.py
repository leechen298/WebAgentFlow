"""Supervisor observation atoms + mechanical verdict derivation.

New supervisor contract (2026-04-20): the LLM no longer picks the
``verdict`` directly. It reports a fixed set of page-state atoms
(booleans + short strings) and a scenario-goal observation. The
mechanical ``verdict`` is derived in code from those atoms — the LLM
can no longer reason itself out of the rule "mechanical verdict is
mechanical", because it never produces the verdict string.

See ``memory/project_supervisor_verdict_override_plan.md`` for the
architectural rationale. The short version: the root cause of the
verdict-override bug wasn't "the supervisor is too simple" — it was
"the LLM shouldn't be holding the verdict pen at all". Making the
Agent more complex (tool-using, multi-LLM ensemble, aggregator)
would have given the model *more* rope, not less.

This module owns:
  * the LLM-facing JSON schema (``SUPERVISOR_OBSERVATIONS_SCHEMA``),
  * the pydantic observation record (``SupervisorObservations``),
  * the lax parser (returns defaults + a partial flag when fields
    are missing, rather than failing Pydantic and forcing a fallback
    round-trip),
  * the derivation function (``derive_verdict``).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

FormStateAfter = Literal["reset", "persisted", "no_form", "unclear"]


class SupervisorObservations(BaseModel):
    """Page-state observations emitted by the supervisor LLM.

    Every field has a conservative default so a partial LLM response
    still parses — missing atoms simply land in the "didn't observe"
    bucket, which is strictly safer than erroring out.
    """

    # ── Objective page-state atoms ─────────────────────────────────
    did_navigate: bool = False
    final_url_path: str = ""
    did_show_error: bool = False
    error_texts: list[str] = Field(default_factory=list)
    form_state_after: FormStateAfter = "unclear"
    list_row_count: int | None = None

    # ── Subjective scenario-goal atom (NOT a verdict) ──────────────
    # "Did the thing this scenario is checking for actually happen?"
    # LLM is asked to cite a short page quote as evidence.
    scenario_goal_observed: bool = False
    scenario_goal_evidence: str = ""

    # ── Free-form (carried over from old contract) ─────────────────
    anomalies: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    summary: str = ""


# LLM-facing JSON schema. Passed to ``generate_structured`` so the
# provider constrains output shape at generation time — much more
# reliable than prompt-ask-JSON. Required fields are the ones whose
# absence would degrade verdict derivation; optional fields default
# to conservative values at parse time.
SUPERVISOR_OBSERVATIONS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "did_navigate": {
            "type": "boolean",
            "description": (
                "True iff the final URL path differs from the URL path "
                "before the last user-intent action (login submit, filter "
                "apply, etc.). Hash / query-only changes still count."
            ),
        },
        "final_url_path": {
            "type": "string",
            "description": "Final URL's path component (no query / fragment).",
        },
        "did_show_error": {
            "type": "boolean",
            "description": (
                "True iff the page rendered a visible error surface "
                "(role=alert, .error, .ant-message-error, toast marked as "
                "error, …) carrying non-empty text. A validation hint next "
                "to a field also qualifies. Not true for neutral messages."
            ),
        },
        "error_texts": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Raw text(s) extracted from each error surface. Empty when "
                "did_show_error is false."
            ),
        },
        "form_state_after": {
            "type": "string",
            "enum": ["reset", "persisted", "no_form", "unclear"],
            "description": (
                "State of the submitted form after the action. "
                "'reset' = fields cleared; 'persisted' = fields still show "
                "submitted values; 'no_form' = page has no form; "
                "'unclear' = cannot tell from the data provided."
            ),
        },
        "list_row_count": {
            "type": ["integer", "null"],
            "description": (
                "If the page is (or ended on) a data list / table, the "
                "number of visible rows after the action. null when no "
                "list is on the page."
            ),
        },
        "scenario_goal_observed": {
            "type": "boolean",
            "description": (
                "Did the thing this scenario is checking for happen on the "
                "page? For a positive-path scenario ('log in with valid "
                "credentials'), this is true when the post-auth destination "
                "is reached. For a negative-path scenario ('bad credentials "
                "stay on login'), this is true when the block + error UI "
                "surfaced. This is NOT a verdict — it is an observation of "
                "scenario intent. Cite evidence in scenario_goal_evidence."
            ),
        },
        "scenario_goal_evidence": {
            "type": "string",
            "description": (
                "A short quote or concrete reference from the page state "
                "(alert text, URL fragment, test_id, body text) that "
                "justifies scenario_goal_observed. Keep it to one sentence. "
                "Empty string when scenario_goal_observed is false."
            ),
        },
        "anomalies": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Anything unexpected that the above atoms don't capture "
                "(CAPTCHA appeared, third-party iframe, analytics banner "
                "obscuring action button, etc.). Optional."
            ),
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Actionable suggestions for improving spec / planner / "
                "analyzer. Optional."
            ),
        },
        "summary": {
            "type": "string",
            "description": "2-4 sentence human-readable recap of what happened on the page.",
        },
    },
    "required": [
        "did_navigate",
        "did_show_error",
        "form_state_after",
        "scenario_goal_observed",
        "summary",
    ],
}


# Fields whose presence (and shape) matters for verdict derivation or
# agreement scoring. When one of these is missing, the response is
# tagged ``partial_parse=true`` and pass_gate downgrades to unverified
# so an operator knows the LLM side was incomplete.
_CRITICAL_ATOMS = (
    "did_navigate",
    "did_show_error",
    "form_state_after",
    "scenario_goal_observed",
)


def parse_observations_lax(
    raw: dict[str, Any] | None,
) -> tuple[SupervisorObservations, bool]:
    """Parse an LLM response into observations, with lax defaults.

    Returns ``(observations, partial_parse)``. ``partial_parse`` is
    true iff any critical atom was absent or ill-typed in the raw
    response — caller uses that to downgrade pass_gate.

    Rationale for being lax: a full Pydantic failure forces the whole
    supervisor call into fallback mode, which is a worse operator
    experience than "LLM gave us 4/5 atoms, pass_gate=unverified, here
    is what it did see". The schema constraint at generation time
    already handles the common drift paths; this is defence in depth.
    """
    if not raw:
        return SupervisorObservations(), True

    partial = any(atom not in raw for atom in _CRITICAL_ATOMS)

    cleaned: dict[str, Any] = {}
    for field_name in SupervisorObservations.model_fields:
        if field_name in raw:
            cleaned[field_name] = raw[field_name]

    try:
        obs = SupervisorObservations(**cleaned)
    except Exception:  # noqa: BLE001 — fall through with all defaults
        return SupervisorObservations(), True

    return obs, partial


def derive_verdict(
    obs: SupervisorObservations,
) -> tuple[str, list[str]]:
    """Derive the mechanical verdict from observation atoms.

    Returns ``(verdict, derivation_trail)``.

    Derivation rules (ordered — first matching rule wins):

      1. ``did_show_error`` is true → ``failure``. An error surface is
         a decisive negative signal regardless of other activity.
      2. ``did_navigate`` is true → ``success``. Navigation to a new
         path means the action flow progressed past the current page.
      3. ``list_row_count`` is not null → ``success``. A data list
         rendered means the page responded; the row count (0 for a
         deliberate no-match, N for a filtered result) is reconciled
         by the scenario-level ``success_signals`` rules downstream.
      4. ``form_state_after`` is ``"reset"`` → ``success``. A cleared
         form is a common "submitted ok, server cleared it" pattern.
      5. otherwise → ``uncertain``.

    The mechanical verdict here mirrors the original rule-side
    verdict vocabulary (success / failure / uncertain) so the
    existing ``_check_verdict`` comparator against ScenarioSpec's
    ``expected_verdict`` / ``expected_verdict_not`` continues to
    work unchanged.
    """
    trail: list[str] = []

    if obs.did_show_error:
        trail.append(
            f"did_show_error=true (error_texts={obs.error_texts!r}) → failure",
        )
        return "failure", trail

    if obs.did_navigate:
        trail.append(
            f"did_navigate=true (final_url_path={obs.final_url_path!r}) → success",
        )
        return "success", trail

    if obs.list_row_count is not None:
        trail.append(
            f"list_row_count={obs.list_row_count} (list rendered) → success",
        )
        return "success", trail

    if obs.form_state_after == "reset":
        trail.append("form_state_after=reset → success")
        return "success", trail

    trail.append("no positive signal and no error → uncertain")
    return "uncertain", trail


def build_supervisor_output(
    obs: SupervisorObservations,
    *,
    partial_parse: bool,
    thinking: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Assemble the ``result.supervisor`` dict from observations.

    Keeps top-level ``verdict`` / ``summary`` / ``anomalies`` /
    ``suggestions`` fields for backward-compat with code that reads
    these directly (pass_gate, UI, CLI). The raw atoms are nested
    under ``observations`` for consumers that want them, and the
    derivation trail is stored under
    ``_supervisor_verdict_derivation`` so the UI can display "this
    verdict came from these atoms".
    """
    verdict, trail = derive_verdict(obs)

    result: dict[str, Any] = {
        # Derived mechanical verdict — same vocabulary as before.
        "verdict": verdict,
        # confidence no longer exists on the LLM side (verdict is
        # derived, not asserted). Set to None so pass_gate's existing
        # "confidence < high → unverified" branch is a no-op for the
        # LLM path. For fallback we also emit None, so the two paths
        # look uniform and pass_gate gains a partial-parse check
        # instead.
        "confidence": None,
        "summary": obs.summary,
        "anomalies": list(obs.anomalies),
        "suggestions": list(obs.suggestions),
        "should_save_path": verdict == "success",
        # Nested atom detail for the UI.
        "observations": obs.model_dump(),
        # Derivation trail — one-line human-readable reasons per rule
        # that fired, so the UI can answer "why is this failure?".
        "_supervisor_verdict_derivation": trail,
        "_supervisor_partial_parse": partial_parse,
        "_supervisor_source": "llm",
    }
    if thinking:
        result["_thinking"] = thinking
    if model:
        result["_model"] = model
    return result
