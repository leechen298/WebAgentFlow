"""Tests for ``wagent verify``.

The verify subcommand is a thin HTTP client around
/exploration/autonomous-runs. These tests pin its contract with the
generated skill (and therefore Claude Code):

    - stdout is exactly one JSON object (no log noise)
    - stderr carries the human banner
    - exit codes: 0 success / 1 non-success verdict / 2 CLI-level error
    - --full toggles trimmed vs full result shape
    - arg validation rejects incomplete combos before any HTTP call

Mocks httpx so the tests never touch a real API — they just verify
how the CLI interprets well-formed and malformed responses.
"""

from __future__ import annotations

import json
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from wagent import main as wagent_main
from wagent import verify as vs


def _run(argv: list[str]) -> int:
    """Invoke the top-level wagent dispatcher with 'verify' prefixed."""
    return wagent_main.main(["verify", *argv])


# ───────────────────────────────────────────────────────────────────
# Argument validation
# ───────────────────────────────────────────────────────────────────


def test_spec_id_without_scenario_is_rejected() -> None:
    with pytest.raises(SystemExit) as exc:
        with redirect_stderr(StringIO()):
            _run(["--spec-id", "users"])
    assert exc.value.code == 2


def test_no_spec_no_url_is_rejected() -> None:
    with pytest.raises(SystemExit) as exc:
        with redirect_stderr(StringIO()):
            _run([])
    assert exc.value.code == 2


def test_parse_kv_json_object_literal() -> None:
    assert vs._parse_kv_json('{"name":"alice"}') == {"name": "alice"}


def test_parse_kv_json_none_and_empty() -> None:
    assert vs._parse_kv_json(None) is None
    assert vs._parse_kv_json("") is None


def test_parse_kv_json_rejects_non_object() -> None:
    with pytest.raises(Exception):
        vs._parse_kv_json('["list","not","object"]')


def test_parse_kv_json_coerces_values_to_strings() -> None:
    # Booleans / ints round-trip as strings because the API schema
    # expects dict[str, str].
    result = vs._parse_kv_json('{"status": "active", "n": 7, "on": true}')
    assert result == {"status": "active", "n": "7", "on": "True"}


# ───────────────────────────────────────────────────────────────────
# _trim_result shape
# ───────────────────────────────────────────────────────────────────


def _full_result(
    verdict: str = "success",
    *,
    matches_expectation: bool | None = True,
    pass_gate_status: str | None = "pass",
    pass_gate_reasons: list[str] | None = None,
) -> dict:
    scorecard: dict = {
        "page_id": "login",
        "scenario": "valid",
        "element_recognition": {"score": 1.0, "weight_note": "a"},
        "action_coverage": {"score": 1.0, "weight_note": "b"},
        "verdict_accuracy": {"score": 1.0, "weight_note": "c"},
        "distraction_avoidance": {"score": 1.0, "weight_note": "d"},
        "supervisor_agreement": {"score": 1.0, "weight_note": "e"},
        "element_checks": [{"role": "x"}] * 10,  # heavy
    }
    if matches_expectation is not None:
        scorecard["verdict_check"] = {
            "self_verdict": verdict,
            "expected_verdict": "success" if verdict == "success" else None,
            "expected_verdict_not": None if verdict == "success" else "success",
            "must_not_transition_to": None,
            "final_url": "http://t/",
            "matches_expectation": matches_expectation,
            "notes": "OK",
        }
    if pass_gate_status is not None:
        scorecard["pass_gate"] = {
            "status": pass_gate_status,
            "reasons": pass_gate_reasons or [],
        }
    return {
        "run_id": "abc-123",
        "verdict": verdict,
        "success": verdict == "success",
        "summary": "All 3 action step(s) succeeded.",
        "final_url": "http://t/dashboard",
        "final_title": "Dashboard",
        "total_steps": 4,
        "elapsed_ms": 7000,
        "steps": [{"step_index": 0, "foo": "bar"}] * 5,  # heavy
        "page_analysis": {"huge": True},  # heavy
        "supervisor": {
            "verdict": verdict,
            "confidence": "high",
            "summary": "ok",
            "anomalies": [],
            "suggestions": [],
            "_thinking": "long LLM trace " * 500,  # heavy
            "_supervisor_source": "llm",
            "_supervisor_error_kind": None,
        },
        "verification": {
            "scorecard": scorecard,
        },
    }


def test_trim_result_drops_heavy_fields() -> None:
    trimmed = vs._trim_result(_full_result())
    assert "steps" not in trimmed
    assert "page_analysis" not in trimmed
    # Supervisor _thinking is not retained in the trimmed view.
    assert "_thinking" not in (trimmed.get("supervisor") or {})
    # Scorecard keeps the 5 score blocks but drops element_checks.
    sc = trimmed["scorecard"]
    assert "element_recognition" in sc
    assert "element_checks" not in sc


def test_trim_result_does_not_emit_frontend_url() -> None:
    # The CLI is a backend client. It must not fabricate a console /
    # workbench URL — the frontend host is not CLI-layer knowledge.
    trimmed = vs._trim_result(_full_result())
    assert "history_url" not in trimmed
    assert trimmed["run_id"] == "abc-123"


# ───────────────────────────────────────────────────────────────────
# Banner
# ───────────────────────────────────────────────────────────────────


def test_banner_success_uses_checkmark() -> None:
    b = vs._banner(vs._trim_result(_full_result("success")))
    assert b.startswith("✓")
    assert "verdict=success" in b
    assert "scorecard=5/5" in b


def test_banner_failure_uses_cross() -> None:
    # Ad-hoc run (no verdict_check + no pass_gate) falls back to raw
    # verdict → ✗ for anything not == "success".
    b = vs._banner(vs._trim_result(_full_result(
        "failure", matches_expectation=None, pass_gate_status=None,
    )))
    assert b.startswith("✗")
    assert "verdict=failure" in b


def test_banner_does_not_leak_frontend_url() -> None:
    b = vs._banner(vs._trim_result(_full_result("success")))
    # Banner must stay a single line with no history/console pointer.
    assert "\n" not in b
    assert "history" not in b.lower()


# ───────────────────────────────────────────────────────────────────
# Exit codes
# ───────────────────────────────────────────────────────────────────


def test_exit_code_success_is_zero() -> None:
    assert vs._exit_code_for("success") == 0


def test_exit_code_non_success_is_one() -> None:
    assert vs._exit_code_for("partial_success") == 1
    assert vs._exit_code_for("failure") == 1
    assert vs._exit_code_for("uncertain") == 1


def test_exit_code_unknown_verdict_is_one_not_two() -> None:
    # CLI-level errors get 2; a run whose verdict we can't parse is a
    # non-success verdict, which is 1. Don't conflate the two.
    assert vs._exit_code_for(None) == 1
    assert vs._exit_code_for("whatever") == 1


def test_exit_code_pass_gate_pass_is_zero() -> None:
    # Authoritative path: pass gate drives the exit code when it's set,
    # overriding both scenario_matched and raw verdict.
    assert vs._exit_code_for("failure", scenario_matched=False,
                             pass_gate_status="pass") == 0


def test_exit_code_pass_gate_unverified_is_one() -> None:
    # "LLM couldn't cross-check" is not a pass — that's the whole
    # reason the gate exists. Exit non-zero so CI catches it.
    assert vs._exit_code_for("success", scenario_matched=True,
                             pass_gate_status="unverified") == 1


def test_exit_code_pass_gate_fail_is_one() -> None:
    assert vs._exit_code_for("success", scenario_matched=True,
                             pass_gate_status="fail") == 1


def test_exit_code_scenario_match_overrides_failure_verdict() -> None:
    # Legacy fallback when pass_gate is absent (ad-hoc / pre-feature).
    # Negative-path scenarios still exit 0.
    assert vs._exit_code_for("failure", scenario_matched=True) == 0
    assert vs._exit_code_for("partial_success", scenario_matched=True) == 0


def test_exit_code_scenario_mismatch_is_one() -> None:
    # Explicit mismatch is always non-zero, even if the rule-side
    # happened to call the run success by accident.
    assert vs._exit_code_for("success", scenario_matched=False) == 1


def test_exit_code_scenario_unspecified_falls_back_to_verdict() -> None:
    # Ad-hoc runs don't have a scenario — exit by verdict.
    assert vs._exit_code_for("success", scenario_matched=None) == 0
    assert vs._exit_code_for("failure", scenario_matched=None) == 1


# ───────────────────────────────────────────────────────────────────
# Scenario-aware trim + banner
# ───────────────────────────────────────────────────────────────────


def test_trim_result_surfaces_scenario_matched_from_verdict_check() -> None:
    # The rule-side VerdictCheck is the source of truth for
    # "did this scenario behave as its spec declares". CLI surfaces
    # it so exit code + reporting can be scenario-aware.
    trimmed = vs._trim_result(_full_result("failure", matches_expectation=True))
    assert trimmed["scenario_matched"] is True


def test_trim_result_scenario_matched_none_when_no_verdict_check() -> None:
    # Ad-hoc runs (no spec) → no verdict_check → no scenario_matched
    # signal. Callers fall back to raw verdict-based logic.
    trimmed = vs._trim_result(_full_result("success", matches_expectation=None))
    assert trimmed["scenario_matched"] is None


def test_trim_result_surfaces_supervisor_source() -> None:
    trimmed = vs._trim_result(_full_result("success"))
    sup = trimmed["supervisor"]
    assert sup["source"] == "llm"
    assert sup["error_kind"] is None


def test_banner_uses_pass_gate_when_present() -> None:
    # The gate is authoritative — verdict=failure with pass_gate=pass
    # (invalid_credentials running as designed, LLM confident) should
    # render ✓ pass, not ✗ failure.
    b = vs._banner(vs._trim_result(_full_result(
        "failure", matches_expectation=True, pass_gate_status="pass",
    )))
    assert b.startswith("✓")
    assert "pass" in b


def test_banner_unverified_uses_warning_glyph() -> None:
    # Unverified gets a distinct glyph so the operator doesn't confuse
    # "LLM couldn't cross-check" with a clean pass or a hard fail.
    b = vs._banner(vs._trim_result(_full_result(
        "success", matches_expectation=True,
        pass_gate_status="unverified",
        pass_gate_reasons=["supervisor ran in fallback mode (error_kind=provider_error)"],
    )))
    assert b.startswith("⚠")
    assert "unverified" in b


def test_banner_fail_uses_cross_glyph() -> None:
    b = vs._banner(vs._trim_result(_full_result(
        "failure", matches_expectation=False,
        pass_gate_status="fail",
    )))
    assert b.startswith("✗")
    assert "fail" in b


# ───────────────────────────────────────────────────────────────────
# End-to-end invocation (HTTP mocked)
# ───────────────────────────────────────────────────────────────────


def _mock_client(post_response: dict, get_response: dict | None = None) -> MagicMock:
    """Build a context-manager-friendly mock httpx.Client."""
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    post_resp = MagicMock(status_code=200)
    post_resp.json = MagicMock(return_value=post_response)
    post_resp.text = json.dumps(post_response)
    client.post = MagicMock(return_value=post_resp)
    if get_response is not None:
        get_resp = MagicMock(status_code=200)
        get_resp.json = MagicMock(return_value=get_response)
        get_resp.raise_for_status = MagicMock()
        client.get = MagicMock(return_value=get_resp)
    return client


def test_success_run_writes_json_to_stdout_and_exits_zero() -> None:
    envelope = {"code": 0, "data": _full_result("success"), "msg": "ok"}
    client = _mock_client(envelope)
    with patch.object(vs.httpx, "Client", return_value=client):
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            rc = _run(["--url", "http://t/"])
    assert rc == 0
    parsed = json.loads(stdout.getvalue())
    assert parsed["verdict"] == "success"
    assert parsed["run_id"] == "abc-123"
    assert "steps" not in parsed  # default is trimmed
    assert "✓" in stderr.getvalue()


def test_full_flag_emits_untrimmed_snapshot() -> None:
    envelope = {"code": 0, "data": _full_result("success"), "msg": "ok"}
    client = _mock_client(envelope)
    with patch.object(vs.httpx, "Client", return_value=client):
        stdout = StringIO()
        with redirect_stdout(stdout), redirect_stderr(StringIO()):
            rc = _run(["--url", "http://t/", "--full"])
    assert rc == 0
    parsed = json.loads(stdout.getvalue())
    # Full payload carries the heavy fields.
    assert parsed["steps"]
    assert parsed["page_analysis"]


def test_failure_verdict_exits_one() -> None:
    # Ad-hoc run (no scenario) with verdict=failure exits 1.
    envelope = {
        "code": 0,
        "data": _full_result(
            "failure", matches_expectation=None, pass_gate_status=None,
        ),
        "msg": "ok",
    }
    client = _mock_client(envelope)
    with patch.object(vs.httpx, "Client", return_value=client):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            rc = _run(["--url", "http://t/"])
    assert rc == 1


def test_business_error_code_exits_two() -> None:
    envelope = {"code": 400, "msg": "bad spec", "data": None}
    client = _mock_client(envelope)
    with patch.object(vs.httpx, "Client", return_value=client):
        stderr = StringIO()
        with redirect_stdout(StringIO()), redirect_stderr(stderr):
            rc = _run(["--url", "http://t/"])
    assert rc == 2
    assert "400" in stderr.getvalue()


def test_http_4xx_exits_two() -> None:
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    resp = MagicMock(status_code=422)
    resp.text = "validation error"
    client.post = MagicMock(return_value=resp)
    with patch.object(vs.httpx, "Client", return_value=client):
        stderr = StringIO()
        with redirect_stdout(StringIO()), redirect_stderr(stderr):
            rc = _run(["--url", "http://t/"])
    assert rc == 2
    assert "422" in stderr.getvalue()


# ───────────────────────────────────────────────────────────────────
# Spec-driven hydration
# ───────────────────────────────────────────────────────────────────


def test_spec_scenario_hydrates_url_and_fill_values() -> None:
    # When --spec-id/--scenario are given but --url/--fill-values are
    # not, the CLI should pull them from /exploration/specs/<id>.
    spec_get = {
        "code": 0,
        "data": {
            "spec_id": "login",
            "url_pattern": "http://resolved/login",
            "scenarios": [
                {
                    "key": "valid_credentials",
                    "inputs": {"username": "admin", "password": "123456"},
                    "selections": {},
                },
            ],
        },
        "msg": "ok",
    }
    run_envelope = {"code": 0, "data": _full_result("success"), "msg": "ok"}
    client = _mock_client(run_envelope, get_response=spec_get)
    with patch.object(vs.httpx, "Client", return_value=client):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            rc = _run([
                "--spec-id", "login",
                "--scenario", "valid_credentials",
            ])
    assert rc == 0
    # The POST should have carried the resolved URL and fill_values.
    post_kwargs = client.post.call_args.kwargs
    payload = post_kwargs["json"]
    assert payload["url"] == "http://resolved/login"
    assert payload["fill_values"] == {"username": "admin", "password": "123456"}
    assert payload["spec_id"] == "login"
    assert payload["scenario"] == "valid_credentials"


def test_path_style_url_pattern_refuses_and_hints() -> None:
    # spec's url_pattern is a match pattern (e.g. "/login"), not a
    # navigable URL. The CLI must refuse, print a hint, and exit 2 —
    # anything else ends up as a 500 inside Playwright.
    spec_get = {
        "code": 0,
        "data": {
            "spec_id": "login",
            "url_pattern": "/login",
            "scenarios": [{"key": "valid", "inputs": {}, "selections": {}}],
        },
        "msg": "ok",
    }
    client = _mock_client(post_response={"code": 0, "data": {}}, get_response=spec_get)
    with patch.object(vs.httpx, "Client", return_value=client):
        stderr = StringIO()
        with redirect_stdout(StringIO()), redirect_stderr(stderr):
            rc = _run(["--spec-id", "login", "--scenario", "valid"])
    assert rc == 2
    err = stderr.getvalue()
    assert "path-style" in err or "--url" in err
    # Must not have sent the POST — no run should have happened.
    assert not client.post.called


def test_explicit_url_overrides_spec_url() -> None:
    # Operator-supplied --url must win over the spec's url_pattern.
    spec_get = {
        "code": 0,
        "data": {
            "url_pattern": "http://spec-wants-this/",
            "scenarios": [{"key": "s", "inputs": {}, "selections": {}}],
        },
        "msg": "ok",
    }
    run_envelope = {"code": 0, "data": _full_result("success"), "msg": "ok"}
    client = _mock_client(run_envelope, get_response=spec_get)
    with patch.object(vs.httpx, "Client", return_value=client):
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            _run([
                "--spec-id", "x", "--scenario", "s",
                "--url", "http://operator-override/",
            ])
    payload = client.post.call_args.kwargs["json"]
    assert payload["url"] == "http://operator-override/"
