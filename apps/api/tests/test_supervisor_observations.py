"""Tests for the observation-atom supervisor contract.

Pins:
  * Lax parsing — missing fields default to conservative values and
    flag ``partial_parse=true`` instead of raising.
  * Verdict derivation — the five rules, their order, and their
    interaction with null / unclear atoms.
  * Output assembly — ``build_supervisor_output`` carries the atoms,
    the derivation trail, and the legacy top-level fields used by
    pass_gate / UI / CLI.
"""

from __future__ import annotations

from app.services.learning.supervisor_observations import (
    SupervisorObservations,
    build_supervisor_output,
    derive_verdict,
    parse_observations_lax,
)


# ── Lax parsing ──────────────────────────────────────────────────────


def test_parse_full_response_is_complete() -> None:
    raw = {
        "did_navigate": True,
        "final_url_path": "/users",
        "did_show_error": False,
        "error_texts": [],
        "form_state_after": "no_form",
        "list_row_count": 7,
        "scenario_goal_observed": True,
        "scenario_goal_evidence": "Reached /users.",
        "anomalies": [],
        "suggestions": [],
        "summary": "Login succeeded.",
    }
    obs, partial = parse_observations_lax(raw)
    assert partial is False
    assert obs.did_navigate is True
    assert obs.list_row_count == 7


def test_parse_missing_critical_atom_flags_partial() -> None:
    # did_show_error omitted — critical atom missing, must flag partial.
    raw = {
        "did_navigate": True,
        "final_url_path": "/users",
        "form_state_after": "no_form",
        "scenario_goal_observed": True,
        "summary": "…",
    }
    obs, partial = parse_observations_lax(raw)
    assert partial is True
    assert obs.did_show_error is False  # default


def test_parse_missing_optional_atom_does_not_flag_partial() -> None:
    # error_texts / list_row_count / anomalies / suggestions are
    # optional — their absence doesn't degrade the response.
    raw = {
        "did_navigate": True,
        "did_show_error": False,
        "form_state_after": "reset",
        "scenario_goal_observed": True,
        "summary": "Form cleared.",
    }
    obs, partial = parse_observations_lax(raw)
    assert partial is False
    assert obs.error_texts == []
    assert obs.list_row_count is None


def test_parse_none_input_returns_defaults_and_partial() -> None:
    obs, partial = parse_observations_lax(None)
    assert partial is True
    assert obs == SupervisorObservations()


def test_parse_ill_typed_response_falls_back_gracefully() -> None:
    # did_navigate as a string instead of bool — Pydantic sometimes
    # coerces, sometimes errors depending on value. If it errors we
    # must still return a usable default observation + partial flag.
    raw = {
        "did_navigate": {"not": "a bool"},
        "did_show_error": False,
        "form_state_after": "unclear",
        "scenario_goal_observed": False,
        "summary": "",
    }
    obs, partial = parse_observations_lax(raw)
    assert partial is True
    # Defaulted because the construction failed.
    assert obs.did_navigate is False


# ── Verdict derivation ───────────────────────────────────────────────


def test_derive_error_trumps_navigation() -> None:
    # A run that both showed an error and navigated — error wins. This
    # is the invalid_credentials-on-a-redirect-login-page pattern: the
    # form might bounce you to a new URL with an error banner. The
    # presence of an error surface is the decisive negative signal.
    obs = SupervisorObservations(
        did_show_error=True,
        error_texts=["Invalid credentials"],
        did_navigate=True,
        final_url_path="/login?error=1",
        scenario_goal_observed=True,
    )
    verdict, trail = derive_verdict(obs)
    assert verdict == "failure"
    assert "did_show_error=true" in trail[0]


def test_derive_navigation_without_error_is_success() -> None:
    obs = SupervisorObservations(
        did_navigate=True,
        final_url_path="/users",
    )
    verdict, _ = derive_verdict(obs)
    assert verdict == "success"


def test_derive_list_rendered_with_zero_rows_is_success() -> None:
    # no_match scenarios deliberately produce zero rows. The list
    # rendering at all means the filter applied — scenario-level
    # success_signals downstream decide whether 0 was expected.
    obs = SupervisorObservations(list_row_count=0)
    verdict, trail = derive_verdict(obs)
    assert verdict == "success"
    assert "list_row_count=0" in trail[0]


def test_derive_form_reset_is_success() -> None:
    obs = SupervisorObservations(form_state_after="reset")
    verdict, _ = derive_verdict(obs)
    assert verdict == "success"


def test_derive_no_signal_is_uncertain() -> None:
    obs = SupervisorObservations()  # all defaults
    verdict, trail = derive_verdict(obs)
    assert verdict == "uncertain"
    assert "no positive signal" in trail[0]


def test_derive_persisted_form_without_error_is_uncertain() -> None:
    # Form still shows submitted values, no error, no navigation —
    # ambiguous. Could be "submit was a no-op", could be "server
    # accepted but didn't redirect". Honest answer: uncertain.
    obs = SupervisorObservations(form_state_after="persisted")
    verdict, _ = derive_verdict(obs)
    assert verdict == "uncertain"


# ── Output assembly ──────────────────────────────────────────────────


def test_build_output_exposes_legacy_top_level_fields() -> None:
    # pass_gate / UI / CLI read verdict + summary + anomalies at the
    # top level. They must stay there even though they now come from
    # derivation + observation fields.
    obs = SupervisorObservations(
        did_navigate=True,
        final_url_path="/users",
        summary="Logged in.",
        anomalies=["captcha rendered but not interacted"],
        suggestions=["add captcha handling"],
    )
    out = build_supervisor_output(obs, partial_parse=False)
    assert out["verdict"] == "success"
    assert out["summary"] == "Logged in."
    assert out["anomalies"] == ["captcha rendered but not interacted"]
    assert out["suggestions"] == ["add captcha handling"]
    assert out["confidence"] is None


def test_build_output_includes_observations_and_trail() -> None:
    obs = SupervisorObservations(did_show_error=True, error_texts=["nope"])
    out = build_supervisor_output(obs, partial_parse=True)
    assert out["observations"]["did_show_error"] is True
    assert out["observations"]["error_texts"] == ["nope"]
    assert out["_supervisor_verdict_derivation"]
    assert out["_supervisor_partial_parse"] is True
    assert out["_supervisor_source"] == "llm"


def test_build_output_carries_model_and_thinking_when_present() -> None:
    obs = SupervisorObservations(did_navigate=True, final_url_path="/x")
    out = build_supervisor_output(
        obs, partial_parse=False,
        thinking="let me think…",
        model="minimax-m2",
    )
    assert out["_thinking"] == "let me think…"
    assert out["_model"] == "minimax-m2"


def test_build_output_omits_thinking_when_absent() -> None:
    obs = SupervisorObservations()
    out = build_supervisor_output(obs, partial_parse=False)
    assert "_thinking" not in out
    assert "_model" not in out
