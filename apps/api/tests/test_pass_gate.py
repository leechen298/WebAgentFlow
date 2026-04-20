"""Tests for the strict pass gate computed alongside the scorecard.

The gate codifies "what counts as a real pass" for a spec-driven
scenario: every rule-side check ok AND the LLM cross-checked AND the
LLM was high-confident. Being lax here accumulates "sort-of passed"
runs that silently hide regressions, so the bar is deliberately hard.

See PassGate in app/schemas/page_verification.py for the product
rationale.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.schemas.page_verification import SupervisorCheck, VerdictCheck
from app.services.learning.page_verification import _compute_pass_gate


def _result(supervisor: dict | None) -> SimpleNamespace:
    """Stub the attributes _compute_pass_gate actually reads off the
    AutonomousExplorationResult — just ``supervisor``. SimpleNamespace
    keeps the test decoupled from the full pydantic model."""
    return SimpleNamespace(supervisor=supervisor)


def _vc(matches: bool = True, notes: str = "OK") -> VerdictCheck:
    return VerdictCheck(
        self_verdict="success",
        expected_verdict="success",
        expected_verdict_not=None,
        must_not_transition_to=None,
        final_url="http://t/",
        matches_expectation=matches,
        notes=notes,
    )


def _sup(score: float = 1.0, notes: str = "supervisor success agrees") -> SupervisorCheck:
    return SupervisorCheck(
        supervisor_verdict="success",
        expected_bucket="success",
        score=score,
        notes=notes,
    )


# ───────────────────────────────────────────────────────────────────
# Happy path
# ───────────────────────────────────────────────────────────────────


def test_pass_when_all_gates_clean() -> None:
    gate = _compute_pass_gate(
        result=_result({
            "_supervisor_source": "llm",
            "confidence": "high",
            "verdict": "success",
        }),
        element_score=1.0,
        action_score=1.0,
        verdict_check=_vc(matches=True),
        distraction_score=1.0,
        supervisor_check=_sup(score=1.0),
    )
    assert gate.status == "pass"
    assert gate.reasons == []


# ───────────────────────────────────────────────────────────────────
# Hard fails — spec deviations
# ───────────────────────────────────────────────────────────────────


def test_fail_when_verdict_does_not_match_expectation() -> None:
    gate = _compute_pass_gate(
        result=_result({
            "_supervisor_source": "llm",
            "confidence": "high",
        }),
        element_score=1.0,
        action_score=1.0,
        verdict_check=_vc(matches=False, notes="verdict must not be 'success', but it is"),
        distraction_score=1.0,
        supervisor_check=_sup(score=1.0),
    )
    assert gate.status == "fail"
    assert any("did not match scenario expectation" in r for r in gate.reasons)


def test_fail_when_element_missing() -> None:
    gate = _compute_pass_gate(
        result=_result({"_supervisor_source": "llm", "confidence": "high"}),
        element_score=0.67,
        action_score=1.0,
        verdict_check=_vc(),
        distraction_score=1.0,
        supervisor_check=_sup(),
    )
    assert gate.status == "fail"
    assert any("element recognition score" in r for r in gate.reasons)


def test_fail_when_distraction_hit() -> None:
    gate = _compute_pass_gate(
        result=_result({"_supervisor_source": "llm", "confidence": "high"}),
        element_score=1.0,
        action_score=1.0,
        verdict_check=_vc(),
        distraction_score=0.5,
        supervisor_check=_sup(),
    )
    assert gate.status == "fail"
    assert any("distraction avoidance" in r for r in gate.reasons)


# ───────────────────────────────────────────────────────────────────
# Unverified — LLM didn't cross-check
# ───────────────────────────────────────────────────────────────────


def test_unverified_when_supervisor_is_fallback() -> None:
    # Exactly today's MiniMax 529 case: scenario mechanics clean, but
    # the LLM never independently verified. Must NOT read as success.
    gate = _compute_pass_gate(
        result=_result({
            "_supervisor_source": "fallback",
            "_supervisor_error_kind": "provider_error",
            "verdict": "success",
        }),
        element_score=1.0,
        action_score=1.0,
        verdict_check=_vc(matches=True),
        distraction_score=1.0,
        supervisor_check=_sup(score=1.0),
    )
    assert gate.status == "unverified"
    assert any("fallback mode" in r for r in gate.reasons)
    assert any("provider_error" in r for r in gate.reasons)


def test_unverified_when_llm_confidence_below_high() -> None:
    # The invalid_credentials case from today's session: LLM hedged
    # to uncertain/medium because it couldn't see final_state. Even
    # if the rule rubric passed, medium confidence is not a pass —
    # otherwise every ambiguous run looks green.
    gate = _compute_pass_gate(
        result=_result({
            "_supervisor_source": "llm",
            "confidence": "medium",
            "verdict": "uncertain",
        }),
        element_score=1.0,
        action_score=1.0,
        verdict_check=_vc(matches=True),
        distraction_score=1.0,
        supervisor_check=_sup(score=0.5, notes="uncertain vs non-success"),
    )
    assert gate.status == "unverified"
    assert any("confidence=medium" in r for r in gate.reasons)


def test_unverified_when_supervisor_agreement_partial() -> None:
    # Supervisor disagreed partially with the rule side (0.5 bucket).
    # This is the "uncertain where non-success expected" case — not a
    # pass, not a fail, just unverified.
    gate = _compute_pass_gate(
        result=_result({
            "_supervisor_source": "llm",
            "confidence": "high",
            "verdict": "uncertain",
        }),
        element_score=1.0,
        action_score=1.0,
        verdict_check=_vc(matches=True),
        distraction_score=1.0,
        supervisor_check=_sup(score=0.5, notes="supervisor uncertain where non-success expected"),
    )
    assert gate.status == "unverified"
    assert any("supervisor_agreement score" in r for r in gate.reasons)


# ───────────────────────────────────────────────────────────────────
# Ordering — hard fails surface first, unverified appended below
# ───────────────────────────────────────────────────────────────────


def test_fail_takes_precedence_over_unverified() -> None:
    # Both gate types tripped. Status must be "fail" (the more
    # action-relevant outcome), and the fail reason must appear
    # before any unverified reason so operators read it first.
    gate = _compute_pass_gate(
        result=_result({
            "_supervisor_source": "fallback",
            "_supervisor_error_kind": "timeout",
        }),
        element_score=0.5,
        action_score=1.0,
        verdict_check=_vc(),
        distraction_score=1.0,
        supervisor_check=_sup(score=1.0),
    )
    assert gate.status == "fail"
    # Fail reason comes before unverified reason.
    fail_idx = next(i for i, r in enumerate(gate.reasons) if "element recognition" in r)
    unv_idx = next(i for i, r in enumerate(gate.reasons) if "fallback mode" in r)
    assert fail_idx < unv_idx
