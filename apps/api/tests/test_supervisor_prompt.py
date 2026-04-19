"""Contract tests for the autonomous supervisor's system prompt.

The supervisor is an LLM call — we can't unit-test its behavior
deterministically. What we CAN pin is the rubric text that tells the
LLM how to map observable signals to a verdict, because when that
text drifts the LLM's verdicts drift too (observed 2026-04-19: the
LLM called a login-wall outcome ``success`` because the step-level
execution succeeded, disagreeing with the rule-based ``no_progress``).

These tests don't check wording exactly — they check that the signals
the rubric is supposed to cover are all mentioned, so future edits
can't silently drop a rule.

(Pre-F note: the 2026-04-19 incident was the LLM returning ``success``
on a login-wall run. Rule-side self-verdict was ``no_progress`` at
the time; after F unified the vocabulary both sides emit the shared
OutcomeVerdict — that specific cross-vocabulary confusion is gone,
but the rubric still needs to guard against the underlying failure
mode, namely "steps ran → success" reasoning.)
"""

from __future__ import annotations

from app.services.learning.autonomous_explorer import (
    _build_supervisor_system_prompt,
)


def _prompt() -> str:
    return _build_supervisor_system_prompt("Respond in English.")


def _normalized(text: str) -> str:
    """Collapse all whitespace so line-wrapping in the prompt doesn't
    break substring assertions. The LLM reads the prompt as one
    wrapped paragraph anyway."""
    return " ".join(text.split())


def test_prompt_contains_strict_verdict_rubric() -> None:
    text = _prompt()
    # Rubric header — without this phrase the LLM treats the four
    # verdict values as interchangeable labels.
    assert "Verdict rubric" in text
    # All four verdict values must be explicitly listed.
    for verdict in ("success", "failure", "partial_success", "uncertain"):
        assert f"``{verdict}``" in text, f"verdict {verdict!r} missing from rubric"


def test_prompt_blocks_login_wall_success() -> None:
    text = _prompt()
    # The 2026-04-19 supervisor disagreement was specifically the LLM
    # calling a login-wall run ``success``. The rubric must explicitly
    # forbid that.
    assert "has_login_wall" in text
    assert "Do not call this success" in text or "this is FAILURE" in text


def test_prompt_covers_captcha_signal() -> None:
    assert "has_captcha" in _prompt()


def test_prompt_covers_alert_error_signal() -> None:
    text = _normalized(_prompt())
    assert "alert_texts" in text
    # Includes at least one Chinese error phrase so non-English error
    # alerts on Chinese pages aren't missed.
    assert "用户名或密码错误" in text


def test_prompt_forbids_step_completion_as_success() -> None:
    text = _prompt()
    # The core failure mode was "steps ran without errors -> success";
    # the rubric must say that step completion alone is insufficient.
    assert "necessary but not sufficient" in text


def test_prompt_keeps_spa_client_side_exception() -> None:
    text = _prompt()
    # SPA filter flows don't change URL but DO change result_row_count;
    # the rubric needs to keep those as a valid success path so we
    # don't over-correct and call legitimate client-side searches
    # ``uncertain``.
    assert "result_row_count" in text
    assert "Client-side SPA exception" in text or "SPA" in text


def test_prompt_defers_to_rule_verdict_by_default() -> None:
    text = _normalized(_prompt())
    # When the LLM and the rule-based self-verdict disagree without
    # a signal-backed reason, the rubric should make the LLM defer.
    assert "agree with it unless" in text


def test_prompt_embeds_language_clause_verbatim() -> None:
    marker = "LANGUAGE-CLAUSE-CANARY-9f3b"
    prompt = _build_supervisor_system_prompt(marker)
    assert marker in prompt


# ───────────────────────────────────────────────────────────────────
# Scenario-intent section (added 2026-04-19 after Run 4 false-partial)
# ───────────────────────────────────────────────────────────────────


def test_prompt_has_operator_intent_section() -> None:
    # The rubric must tell the LLM to read scenario_description
    # before interpreting signals, not just from execution.verdict.
    # Without this section the LLM hedged a deliberate no-match run
    # to partial_success (2026-04-19 Run 4).
    text = _normalized(_prompt())
    assert "scenario_name" in text
    assert "scenario_description" in text


def test_prompt_no_match_example_points_to_success() -> None:
    # Named example ensures the LLM generalises to similar spec
    # scenarios: zero-result runs can be success when the scenario
    # description frames them as intentional.
    text = _normalized(_prompt())
    assert "no_match" in text
    assert "result_row_count == 0" in text


def test_prompt_invalid_credentials_example_points_to_failure() -> None:
    # The converse example: login-wall end state for a bad-credentials
    # test is FAILURE from the verdict perspective (the spec's
    # expected_verdict_not reconciles that later).
    text = _normalized(_prompt())
    assert "invalid_credentials" in text
    assert "has_login_wall" in text
