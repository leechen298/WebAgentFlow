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
    return LlmResponse(
        ok=True,
        parsed={
            "verdict": verdict,
            "confidence": "high",
            "summary": "LLM-generated summary.",
            "step_assessments": [],
            "anomalies": [],
            "suggestions": [],
            "should_save_path": verdict == "success",
        },
        model="test-model",
    )


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
    assert out["confidence"] == "low"  # fallback never pretends to be confident
