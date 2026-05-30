"""Tests for the autonomous exploration supervisor path.

Covers ``_run_supervisor`` + ``_fallback_supervisor`` in
``apps/api/app/services/learning/autonomous_explorer.py`` — the
Layer-2 LLM verification used by the autonomous workbench + the
``verify-scenario`` skill. The older task-based supervisor is
covered separately in ``test_exploration_supervisor.py``.

Specifically pins:
  * Single retry on retryable errors (rate_limit / timeout / 5xx).
  * No retry on non-retryable errors (auth_error / parse_error).
  * Fallback output carries ``_supervisor_source: "fallback"`` +
    the underlying error kind so the UI and CLI can distinguish a
    real LLM verdict from a rule-mirrored one.
  * LLM-success output carries ``_supervisor_source: "llm"``.
"""

from __future__ import annotations

from unittest.mock import patch

from app.schemas.llm import LlmError, LlmResponse
from app.schemas.page_analysis import PageAnalysis
from app.services.learning import autonomous_explorer as ae


def _empty_analysis() -> PageAnalysis:
    return PageAnalysis(
        url="http://t/",
        title="T",
        total_visible=0,
        total_hidden=0,
        fillable=[],
        submit=[],
        clickable=[],
        navigation=[],
        select=[],
        toggle=[],
        other=[],
    )


def _llm_ok(verdict: str = "success") -> LlmResponse:
    """Emit an observation-atom response shaped so that
    ``derive_verdict`` produces the target mechanical verdict.

    * ``success`` — navigation happened, no error.
    * ``failure`` — error surface rendered.
    * ``uncertain`` — no positive signal and no error.
    """
    atoms: dict[str, object] = {
        "did_navigate": verdict == "success",
        "final_url_path": "/done" if verdict == "success" else "/entry",
        "did_show_error": verdict == "failure",
        "error_texts": ["nope"] if verdict == "failure" else [],
        "form_state_after": "no_form",
        "list_row_count": None,
        "scenario_goal_observed": True,
        "scenario_goal_evidence": "evidence cited",
        "anomalies": [],
        "suggestions": [],
        "summary": "LLM-generated summary.",
    }
    return LlmResponse(ok=True, parsed=atoms, model="test-model")


def _llm_err(kind: str, *, retryable: bool) -> LlmResponse:
    return LlmResponse(
        ok=False,
        error=LlmError(kind=kind, message=f"{kind} blip", retryable=retryable),
    )


# ───────────────────────────────────────────────────────────────────
# LLM success path
# ───────────────────────────────────────────────────────────────────


def test_llm_success_tags_source_llm() -> None:
    with patch("app.services.llm_provider.generate_structured", return_value=_llm_ok()):
        out = ae._run_supervisor(
            _empty_analysis(), [], "success", "all good",
            "http://t/done", "Done", 100,
        )
    assert out is not None
    assert out["_supervisor_source"] == "llm"
    assert out["verdict"] == "success"
    assert "fallback" not in out["summary"].lower()


def test_supervisor_prompt_includes_final_state() -> None:
    # invalid_credentials showed the LLM was hedging to "uncertain"
    # because we didn't pass final_state.alert_texts to it. Pin the
    # fix: when _run_supervisor is called with final_state, the LLM
    # request body carries a compacted form of body_text +
    # alert_texts + test_ids so the model can verify
    # "surface role=alert" directly.
    captured: dict[str, object] = {}

    def fake_gen(req):
        captured["user"] = req.messages[0].content
        return _llm_ok("success")

    with patch("app.services.llm_provider.generate_structured", side_effect=fake_gen):
        ae._run_supervisor(
            _empty_analysis(), [], "failure",
            "Actions executed but login wall persisted.",
            "http://t/login", "Sign in", 100,
            scenario_name="invalid_credentials",
            scenario_description="Wrong creds stay on /login and surface role=alert.",
            final_state={
                "body_text": "Username\nPassword\n用户名或密码错误",
                "body_text_length": 27,
                "alert_texts": ["用户名或密码错误"],
                "test_ids": ["login-error"],
            },
        )
    user_prompt = captured["user"]
    # The compacted final_state must land in the user prompt.
    assert "用户名或密码错误" in user_prompt
    assert "login-error" in user_prompt
    assert "alert_texts" in user_prompt


def test_supervisor_prompt_handles_missing_final_state() -> None:
    # Ad-hoc runs or failures before capture may not have final_state.
    # The supervisor must not crash; the prompt just omits the data.
    def fake_gen(req):
        return _llm_ok("uncertain")

    with patch("app.services.llm_provider.generate_structured", side_effect=fake_gen):
        out = ae._run_supervisor(
            _empty_analysis(), [], "uncertain", "no data", "", "", 0,
            final_state=None,
        )
    assert out is not None
    assert out["verdict"] == "uncertain"


def test_compact_final_state_caps_body_text() -> None:
    # A chatty page mustn't blow the context window. Body text is
    # hard-capped; alert texts individually capped so a long stack
    # trace in a role=alert doesn't dominate the payload.
    long = "x" * 10_000
    compact = ae._compact_final_state({
        "body_text": long,
        "body_text_length": 10_000,
        "alert_texts": ["y" * 1_000],
        "test_ids": ["t1"],
    })
    assert compact is not None
    assert len(compact["body_text"]) < 2_500
    assert compact["body_text_length"] == 10_000
    assert len(compact["alert_texts"][0]) < 500
    assert compact["test_ids"] == ["t1"]


# ───────────────────────────────────────────────────────────────────
# Retry behaviour
# ───────────────────────────────────────────────────────────────────


def test_retryable_error_retries_once_and_succeeds() -> None:
    # First call returns a retryable error (rate_limit), second call
    # returns a clean LLM verdict. The supervisor must retry once and
    # surface the successful verdict without falling back.
    calls = [_llm_err("rate_limit", retryable=True), _llm_ok("success")]
    with patch("app.services.llm_provider.generate_structured", side_effect=calls):
        out = ae._run_supervisor(
            _empty_analysis(), [], "success", "ok",
            "http://t/", "T", 100,
        )
    assert out["_supervisor_source"] == "llm"
    assert out["verdict"] == "success"


def test_retryable_error_twice_falls_back_with_kind() -> None:
    # Both attempts hit a retryable error — fall back, and tag the
    # output with the error kind so downstream can distinguish "LLM
    # blipped twice" from "spec misconfigured".
    calls = [_llm_err("timeout", retryable=True), _llm_err("timeout", retryable=True)]
    with patch("app.services.llm_provider.generate_structured", side_effect=calls):
        out = ae._run_supervisor(
            _empty_analysis(), [], "success", "ok",
            "http://t/", "T", 100,
        )
    assert out["_supervisor_source"] == "fallback"
    assert out["_supervisor_error_kind"] == "timeout"
    assert "[fallback: timeout]" in out["summary"]


def test_non_retryable_error_falls_back_without_retry() -> None:
    # auth_error is non-retryable — retrying won't change anything,
    # so the supervisor must NOT call generate_structured a second
    # time. We assert exactly one call.
    mock_response = _llm_err("auth_error", retryable=False)
    with patch("app.services.llm_provider.generate_structured", return_value=mock_response) as gen:
        out = ae._run_supervisor(
            _empty_analysis(), [], "success", "ok",
            "http://t/", "T", 100,
        )
    assert gen.call_count == 1
    assert out["_supervisor_source"] == "fallback"
    assert out["_supervisor_error_kind"] == "auth_error"
    assert "[fallback: auth_error]" in out["summary"]


def test_parse_error_falls_back_without_retry() -> None:
    # parse_error isn't retryable in our classification — the provider
    # gave us a syntactically bad response that another attempt won't
    # fix. Fallback immediately.
    mock_response = _llm_err("parse_error", retryable=False)
    with patch("app.services.llm_provider.generate_structured", return_value=mock_response) as gen:
        out = ae._run_supervisor(
            _empty_analysis(), [], "failure", "nope",
            "http://t/", "T", 100,
        )
    assert gen.call_count == 1
    assert out["_supervisor_source"] == "fallback"
    assert out["_supervisor_error_kind"] == "parse_error"


# ───────────────────────────────────────────────────────────────────
# _fallback_supervisor direct shape
# ───────────────────────────────────────────────────────────────────


def test_fallback_includes_error_kind_in_summary() -> None:
    out = ae._fallback_supervisor(
        steps=[{"step_index": 0, "ok": True}],
        self_verdict="success",
        summary="base summary",
        error_kind="rate_limit",
    )
    assert out["_supervisor_source"] == "fallback"
    assert out["_supervisor_error_kind"] == "rate_limit"
    assert out["summary"] == "base summary [fallback: rate_limit]"


def test_fallback_without_error_kind_uses_generic_label() -> None:
    # Backwards-compat: legacy callers that don't pass error_kind
    # still get a usable summary — no crash, generic "LLM unavailable"
    # label preserved so existing history entries remain parseable.
    out = ae._fallback_supervisor(
        steps=[{"step_index": 0, "ok": True}],
        self_verdict="success",
        summary="base summary",
    )
    assert out["_supervisor_source"] == "fallback"
    assert out["_supervisor_error_kind"] is None
    assert "[fallback: LLM unavailable]" in out["summary"]


def test_fallback_does_not_emit_scenario_blind_anomalies() -> None:
    # Earlier versions hardcoded "Login wall detected" / "CAPTCHA
    # detected" anomalies based on result_signals, which was noise:
    # for invalid_credentials the login wall IS the expected outcome,
    # and the rule side already folds these signals into the main
    # verdict via _assess_outcome. Fallback has no scenario context to
    # tell "expected" from "unexpected", so it must stay silent on
    # anomalies entirely — misleading noise is worse than none.
    out = ae._fallback_supervisor(
        steps=[
            {"step_index": 0, "ok": True, "action_type": "click"},
            {
                "step_index": 1,
                "ok": True,
                "action_type": "observe",
                "result_signals": {"has_login_wall": True, "has_captcha": True},
            },
        ],
        self_verdict="failure",
        summary="login wall persisted",
        error_kind="provider_error",
    )
    assert out["verdict"] == "failure"  # passes self_verdict through
    assert out["anomalies"] == []
    # confidence is an LLM self-assessment signal; fallback has no
    # LLM verdict to self-assess, so the field is deliberately None.
    # Downstream keys off _supervisor_source + _supervisor_error_kind
    # to render the "LLM unavailable" state.
    assert out["confidence"] is None
    assert out["_supervisor_source"] == "fallback"
    assert out["_supervisor_error_kind"] == "provider_error"
