"""Contract tests for the autonomous supervisor's system prompt.

Under the observation-atom contract (2026-04-20), the supervisor LLM
does NOT choose a verdict — it reports a fixed set of observation
atoms and a scenario-goal observation. Verdict is derived in code
by ``supervisor_observations.derive_verdict``.

These tests pin the contract that keeps the prompt scenario-general
and blocks the LLM from re-acquiring the verdict pen:

  * Each required atom is named in the prompt.
  * The prompt tells the LLM it is NOT judging outcomes.
  * Error-text detection covers both English and Chinese surfaces.
  * Few-shot examples illustrate observations, NOT verdict mapping.
  * The old verdict rubric (success/failure/partial_success enum) is
    absent — its presence would leak the old contract back in.
  * The language clause is embedded verbatim.
"""

from __future__ import annotations

from app.services.learning.autonomous_explorer import (
    _build_supervisor_system_prompt,
)


def _prompt() -> str:
    return _build_supervisor_system_prompt("Respond in English.")


def _normalized(text: str) -> str:
    """Collapse all whitespace so line-wrapping in the prompt doesn't
    break substring assertions."""
    return " ".join(text.split())


# ── Required atoms are named in the prompt ───────────────────────────


def test_prompt_names_every_required_atom() -> None:
    text = _prompt()
    for atom in (
        "did_navigate",
        "final_url_path",
        "did_show_error",
        "error_texts",
        "form_state_after",
        "list_row_count",
        "scenario_goal_observed",
        "scenario_goal_evidence",
    ):
        assert atom in text, f"atom {atom!r} missing from prompt"


# ── Prompt strips the LLM of the verdict pen ─────────────────────────


def test_prompt_tells_llm_not_to_judge() -> None:
    # The single most important contract: the LLM must know it is NOT
    # the verdict authority. If this phrase disappears future edits
    # might re-normalize the prompt toward "pick a verdict".
    text = _normalized(_prompt())
    assert "NOT to judge whether the run passed or failed" in text


def test_prompt_does_not_ask_for_verdict_field() -> None:
    text = _prompt()
    # The atoms don't include a verdict/confidence/should_save_path
    # field. The prompt must not mention them as expected output.
    # (They may appear in forbidden-output clauses — assert negation
    # by searching for affirmative phrasings only.)
    assert "Do NOT output" in text
    assert "``verdict``" in text  # named in the forbidden list
    assert "``confidence``" in text


def test_prompt_has_no_old_verdict_rubric() -> None:
    # Phrases that were load-bearing in the old rubric and must be
    # gone now that verdict is derived in code.
    text = _normalized(_prompt())
    forbidden = [
        "Verdict rubric",
        "necessary but not sufficient",
        "Client-side SPA exception",
        "Confidence calibration",
        "Verdict vocabulary is MECHANICAL",
    ]
    for phrase in forbidden:
        assert phrase not in text, (
            f"stale old-rubric phrase {phrase!r} still in prompt — "
            "LLM will revert to verdict-deciding behavior"
        )


# ── Error detection: the prompt is language-aware ────────────────────


def test_prompt_covers_chinese_error_phrases() -> None:
    # Prompt must list at least one common Chinese error cue so the LLM
    # flips did_show_error when it sees one.
    text = _prompt()
    assert "错误" in text or "失败" in text or "无效" in text


def test_prompt_covers_english_error_cues() -> None:
    text = _normalized(_prompt())
    # At least one of the common error tokens must be named so the
    # LLM doesn't hesitate on "Invalid credentials" / "denied" pages.
    tokens = ("invalid", "denied", "failed", "incorrect")
    assert any(tok in text.lower() for tok in tokens)


# ── Scenario-goal observation ────────────────────────────────────────


def test_prompt_instructs_reading_scenario_description() -> None:
    # scenario_goal_observed is an interpretive atom; the prompt must
    # tell the LLM to read scenario_description before picking true /
    # false, otherwise it falls back to guessing from heuristics.
    text = _normalized(_prompt())
    assert "scenario_description" in text


def test_prompt_distinguishes_positive_and_negative_goals() -> None:
    text = _normalized(_prompt())
    # The prompt must cover both "positive goal" (login succeeds) and
    # "negative goal" (login is blocked as expected) without leaking
    # into verdict language.
    assert "POSITIVE" in text
    assert "NEGATIVE" in text


# ── Few-shot observation examples ────────────────────────────────────


def test_prompt_has_observation_examples() -> None:
    # Few-shot section uses observation-atom JSON, not "scenario X →
    # verdict Y" mapping.
    text = _normalized(_prompt())
    assert "Few-shot observation examples" in text
    # Every example JSON carries did_navigate + did_show_error keys.
    assert text.count("did_navigate") >= 3
    assert text.count("did_show_error") >= 3


# ── Language clause passthrough ──────────────────────────────────────


def test_prompt_embeds_language_clause_verbatim() -> None:
    marker = "LANGUAGE-CLAUSE-CANARY-9f3b"
    prompt = _build_supervisor_system_prompt(marker)
    assert marker in prompt
