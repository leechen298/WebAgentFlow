"""Tests for page_verification — spec-baseline comparator and scorecard.

Covers: element matcher, element/action/distraction/signal/verdict/supervisor
checks, verify_against_spec integration, and load_spec.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.schemas.page_analysis import (
    AutonomousExplorationResult,
    DiscoveredElement,
    PageAnalysis,
)
from app.schemas.page_verification import (
    ActionCheck,
    CriticalElementSpec,
    DistractionCheck,
    DistractionSpec,
    ElementCheck,
    ElementMatcher,
    PageVerificationScorecard,
    PageVerificationSpec,
    ScenarioSpec,
    ScoreBlock,
    SuccessSignals,
    FailureSignals,
    SupervisorCheck,
    VerdictCheck,
)
from app.services.learning.page_verification import (
    SpecNotFound,
    SpecRootNotConfigured,
    UnsafeSpecId,
    _all_elements,
    _check_action,
    _check_distraction,
    _check_element,
    _check_failure_signals,
    _check_success_signals,
    _check_supervisor,
    _check_verdict,
    _element_actual_category,
    _find_match,
    _matches,
    get_spec_root,
    iter_spec_paths,
    load_spec,
    verify_against_spec,
)


# ───────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────


def _el(
    *,
    selector: str = "#inp",
    category: str = "fillable",
    tag: str = "input",
    element_type: str | None = "text",
    id: str | None = None,
    name: str | None = None,
    role: str | None = None,
    text: str = "",
    placeholder: str | None = None,
    aria_label: str | None = None,
    element_value: str | None = None,
    semantic_role: str | None = None,
    visible: bool = True,
) -> DiscoveredElement:
    return DiscoveredElement(
        category=category,
        tag=tag,
        element_type=element_type,
        id=id,
        name=name,
        role=role,
        text=text,
        placeholder=placeholder,
        aria_label=aria_label,
        element_value=element_value,
        semantic_role=semantic_role,
        selector=selector,
        visible=visible,
    )


def _analysis(
    fillable=None, submit=None, clickable=None, navigation=None,
    select=None, toggle=None, other=None, hidden_interactive=None,
) -> PageAnalysis:
    return PageAnalysis(
        url="http://test/",
        title="Test",
        fillable=fillable or [],
        submit=submit or [],
        clickable=clickable or [],
        navigation=navigation or [],
        select=select or [],
        toggle=toggle or [],
        other=other or [],
        hidden_interactive=hidden_interactive or [],
    )


def _result(
    analysis: PageAnalysis | None = None,
    steps: list[dict] | None = None,
    verdict: str = "success",
    final_url: str = "http://test/ok",
    final_title: str = "OK",
    final_state: dict | None = None,
    supervisor: dict | None = None,
) -> AutonomousExplorationResult:
    return AutonomousExplorationResult(
        page_analysis=analysis or _analysis(),
        steps=steps or [],
        verdict=verdict,
        final_url=final_url,
        final_title=final_title,
        final_state=final_state or {},
        supervisor=supervisor,
    )


def _spec(
    *,
    page_id: str = "test_page",
    critical_elements=None,
    distractions=None,
    scenarios=None,
) -> PageVerificationSpec:
    return PageVerificationSpec(
        page_id=page_id,
        critical_elements=critical_elements or [],
        distractions=distractions or [],
        scenarios=scenarios or {},
    )


def _ok_supervisor() -> dict:
    return {
        "_supervisor_source": "llm",
        "_supervisor_partial_parse": False,
        "verdict": "success",
        "observations": {
            "scenario_goal_observed": True,
            "scenario_goal_evidence": "Goal reached.",
        },
    }


# ───────────────────────────────────────────────────────────────────
# _matches — element matcher
# ───────────────────────────────────────────────────────────────────


class TestMatches:
    def test_match_by_id(self):
        el = _el(id="username")
        matcher = ElementMatcher(id="username")
        assert _matches(el, matcher) is True

    def test_mismatch_by_id(self):
        el = _el(id="username")
        matcher = ElementMatcher(id="password")
        assert _matches(el, matcher) is False

    def test_match_by_name(self):
        el = _el(name="email_field")
        matcher = ElementMatcher(name="email_field")
        assert _matches(el, matcher) is True

    def test_match_by_tag(self):
        el = _el(tag="textarea")
        matcher = ElementMatcher(tag="textarea")
        assert _matches(el, matcher) is True

    def test_match_by_element_type(self):
        el = _el(element_type="password")
        matcher = ElementMatcher(element_type="password")
        assert _matches(el, matcher) is True

    def test_match_by_role(self):
        el = _el(role="button")
        matcher = ElementMatcher(role="button")
        assert _matches(el, matcher) is True

    def test_match_by_element_value(self):
        el = _el(element_value="active")
        matcher = ElementMatcher(element_value="active")
        assert _matches(el, matcher) is True

    def test_match_by_selector_any_of(self):
        el = _el(selector="#special")
        matcher = ElementMatcher(selector_any_of=["#other", "#special"])
        assert _matches(el, matcher) is True

    def test_selector_any_of_no_match(self):
        el = _el(selector="#nope")
        matcher = ElementMatcher(selector_any_of=["#other", "#special"])
        assert _matches(el, matcher) is False

    def test_match_by_text_contains(self):
        el = _el(text="Submit Form")
        matcher = ElementMatcher(text_contains="Submit")
        assert _matches(el, matcher) is True

    def test_text_contains_no_match(self):
        el = _el(text="Cancel")
        matcher = ElementMatcher(text_contains="Submit")
        assert _matches(el, matcher) is False

    def test_text_contains_element_has_no_text(self):
        el = _el(text="")
        matcher = ElementMatcher(text_contains="Submit")
        assert _matches(el, matcher) is False

    def test_match_by_placeholder_contains(self):
        el = _el(placeholder="Enter your email")
        matcher = ElementMatcher(placeholder_contains="email")
        assert _matches(el, matcher) is True

    def test_placeholder_contains_no_match(self):
        el = _el(placeholder="Enter name")
        matcher = ElementMatcher(placeholder_contains="email")
        assert _matches(el, matcher) is False

    def test_placeholder_contains_element_has_none(self):
        el = _el(placeholder=None)
        matcher = ElementMatcher(placeholder_contains="email")
        assert _matches(el, matcher) is False

    def test_match_by_aria_label_contains(self):
        el = _el(aria_label="Close dialog")
        matcher = ElementMatcher(aria_label_contains="Close")
        assert _matches(el, matcher) is True

    def test_aria_label_contains_no_match(self):
        el = _el(aria_label="Open menu")
        matcher = ElementMatcher(aria_label_contains="Close")
        assert _matches(el, matcher) is False

    def test_aria_label_contains_element_has_none(self):
        el = _el(aria_label=None)
        matcher = ElementMatcher(aria_label_contains="Close")
        assert _matches(el, matcher) is False

    def test_and_combination_all_must_match(self):
        el = _el(id="inp", tag="input", element_type="text")
        matcher = ElementMatcher(id="inp", tag="input")
        assert _matches(el, matcher) is True

    def test_and_combination_one_fails(self):
        el = _el(id="inp", tag="input", element_type="text")
        matcher = ElementMatcher(id="inp", tag="textarea")
        assert _matches(el, matcher) is False

    def test_empty_matcher_matches_nothing(self):
        el = _el()
        matcher = ElementMatcher()
        assert _matches(el, matcher) is False

    def test_selector_any_of_takes_precedence(self):
        el = _el(selector="#sel", id="other_id")
        matcher = ElementMatcher(id="wrong_id", selector_any_of=["#sel"])
        assert _matches(el, matcher) is True


# ───────────────────────────────────────────────────────────────────
# _all_elements / _find_match / _element_actual_category
# ───────────────────────────────────────────────────────────────────


class TestElementHelpers:
    def test_all_elements_flattens(self):
        f = _el(selector="#f", category="fillable")
        s = _el(selector="#s", category="submit", tag="button", element_type="submit")
        h = _el(selector="#h", category="other", visible=False)
        analysis = _analysis(fillable=[f], submit=[s], hidden_interactive=[h])
        all_els = _all_elements(analysis)
        assert len(all_els) == 3
        assert f in all_els and s in all_els and h in all_els

    def test_find_match_returns_first(self):
        e1 = _el(id="a", selector="#a")
        e2 = _el(id="b", selector="#b")
        matcher = ElementMatcher(id="b")
        assert _find_match([e1, e2], matcher) is e2

    def test_find_match_returns_none(self):
        e1 = _el(id="a", selector="#a")
        matcher = ElementMatcher(id="c")
        assert _find_match([e1], matcher) is None

    def test_element_actual_category_fillable(self):
        f = _el(selector="#f")
        analysis = _analysis(fillable=[f])
        assert _element_actual_category(analysis, f) == "fillable"

    def test_element_actual_category_submit(self):
        s = _el(selector="#s", category="submit", tag="button", element_type="submit")
        analysis = _analysis(submit=[s])
        assert _element_actual_category(analysis, s) == "submit"

    def test_element_actual_category_hidden(self):
        h = _el(selector="#h", visible=False)
        analysis = _analysis(hidden_interactive=[h])
        assert _element_actual_category(analysis, h) == "hidden"

    def test_element_actual_category_none(self):
        orphan = _el(selector="#orphan")
        analysis = _analysis()
        assert _element_actual_category(analysis, orphan) is None


# ───────────────────────────────────────────────────────────────────
# _check_element — element recognition
# ───────────────────────────────────────────────────────────────────


class TestCheckElement:
    def test_skipped_when_not_in_scenario(self):
        spec_el = CriticalElementSpec(
            role="alert",
            expected_category="other",
            match_by=ElementMatcher(role="alert"),
            visible_only_on=["other_scenario"],
        )
        analysis = _analysis()
        check = _check_element(spec_el, analysis, "my_scenario")
        assert check.skipped is True
        assert check.found is False

    def test_not_found(self):
        spec_el = CriticalElementSpec(
            role="username_input",
            expected_category="fillable",
            match_by=ElementMatcher(id="username"),
        )
        analysis = _analysis()
        check = _check_element(spec_el, analysis, "my_scenario")
        assert check.found is False
        assert "No element matched" in check.notes

    def test_found_category_match(self):
        el = _el(id="username", selector="#username", semantic_role="username")
        spec_el = CriticalElementSpec(
            role="username_input",
            expected_category="fillable",
            expected_semantic_role="username",
            match_by=ElementMatcher(id="username"),
        )
        analysis = _analysis(fillable=[el])
        check = _check_element(spec_el, analysis, "my_scenario")
        assert check.found is True
        assert check.category_match is True
        assert check.semantic_role_match is True
        assert check.observed_category == "fillable"
        assert check.observed_selector == "#username"
        assert "OK" in check.notes

    def test_found_category_mismatch(self):
        el = _el(id="btn", selector="#btn", category="clickable", tag="button", element_type="button")
        spec_el = CriticalElementSpec(
            role="submit_btn",
            expected_category="submit",
            match_by=ElementMatcher(id="btn"),
        )
        analysis = _analysis(clickable=[el])
        check = _check_element(spec_el, analysis, "my_scenario")
        assert check.found is True
        assert check.category_match is False
        assert "category" in check.notes

    def test_found_semantic_role_mismatch(self):
        el = _el(id="inp", selector="#inp", semantic_role="email")
        spec_el = CriticalElementSpec(
            role="username_input",
            expected_category="fillable",
            expected_semantic_role="username",
            match_by=ElementMatcher(id="inp"),
        )
        analysis = _analysis(fillable=[el])
        check = _check_element(spec_el, analysis, "my_scenario")
        assert check.found is True
        assert check.semantic_role_match is False
        assert "semantic_role" in check.notes

    def test_semantic_role_none_when_spec_not_set(self):
        el = _el(id="inp", selector="#inp", semantic_role="email")
        spec_el = CriticalElementSpec(
            role="input",
            expected_category="fillable",
            match_by=ElementMatcher(id="inp"),
        )
        analysis = _analysis(fillable=[el])
        check = _check_element(spec_el, analysis, "my_scenario")
        assert check.semantic_role_match is None

    def test_visible_only_on_matches_current_scenario(self):
        el = _el(id="alert", selector="#alert", category="other", tag="div")
        spec_el = CriticalElementSpec(
            role="alert",
            expected_category="other",
            match_by=ElementMatcher(id="alert"),
            visible_only_on=["my_scenario"],
        )
        analysis = _analysis(other=[el])
        check = _check_element(spec_el, analysis, "my_scenario")
        assert check.skipped is False
        assert check.found is True


# ───────────────────────────────────────────────────────────────────
# _check_action — action coverage
# ───────────────────────────────────────────────────────────────────


class TestCheckAction:
    def test_malformed_expected(self):
        spec_els = {}
        analysis = _analysis()
        check = _check_action("malformed", spec_els, analysis, [])
        assert check.executed is False
        assert "Malformed" in check.notes

    def test_no_spec_element_for_role(self):
        spec_els = {}
        analysis = _analysis()
        check = _check_action("fill:missing", spec_els, analysis, [])
        assert check.executed is False
        assert "No critical_element" in check.notes

    def test_spec_element_not_discovered(self):
        spec_el = CriticalElementSpec(
            role="username_input",
            expected_category="fillable",
            match_by=ElementMatcher(id="username"),
        )
        spec_els = {"username_input": spec_el}
        analysis = _analysis()
        check = _check_action("fill:username_input", spec_els, analysis, [])
        assert check.executed is False
        assert "never discovered" in check.notes

    def test_action_executed_by_selector(self):
        el = _el(id="username", selector="#username")
        spec_el = CriticalElementSpec(
            role="username_input",
            expected_category="fillable",
            match_by=ElementMatcher(id="username"),
        )
        steps = [
            {"action_type": "fill", "ok": True, "target_selector": "#username", "step_index": 0},
        ]
        check = _check_action(
            "fill:username_input",
            {"username_input": spec_el},
            _analysis(fillable=[el]),
            steps,
        )
        assert check.executed is True
        assert check.step_index == 0

    def test_action_executed_by_id_in_description(self):
        el = _el(id="user", selector=".complex-selector")
        spec_el = CriticalElementSpec(
            role="username_input",
            expected_category="fillable",
            match_by=ElementMatcher(id="user"),
        )
        steps = [
            {"action_type": "fill", "ok": True, "target_description": "id=user field", "step_index": 2},
        ]
        check = _check_action(
            "fill:username_input",
            {"username_input": spec_el},
            _analysis(fillable=[el]),
            steps,
        )
        assert check.executed is True
        assert check.step_index == 2

    def test_action_executed_by_name_in_description(self):
        el = _el(name="email_field", selector=".sel")
        spec_el = CriticalElementSpec(
            role="email_input",
            expected_category="fillable",
            match_by=ElementMatcher(name="email_field"),
        )
        steps = [
            {"action_type": "fill", "ok": True, "target_description": "name=email_field", "step_index": 1},
        ]
        check = _check_action(
            "fill:email_input",
            {"email_input": spec_el},
            _analysis(fillable=[el]),
            steps,
        )
        assert check.executed is True

    def test_action_not_executed_wrong_type(self):
        el = _el(id="username", selector="#username")
        spec_el = CriticalElementSpec(
            role="username_input",
            expected_category="fillable",
            match_by=ElementMatcher(id="username"),
        )
        steps = [
            {"action_type": "click", "ok": True, "target_selector": "#username", "step_index": 0},
        ]
        check = _check_action(
            "fill:username_input",
            {"username_input": spec_el},
            _analysis(fillable=[el]),
            steps,
        )
        assert check.executed is False

    def test_action_not_executed_step_failed(self):
        el = _el(id="username", selector="#username")
        spec_el = CriticalElementSpec(
            role="username_input",
            expected_category="fillable",
            match_by=ElementMatcher(id="username"),
        )
        steps = [
            {"action_type": "fill", "ok": False, "target_selector": "#username", "step_index": 0},
        ]
        check = _check_action(
            "fill:username_input",
            {"username_input": spec_el},
            _analysis(fillable=[el]),
            steps,
        )
        assert check.executed is False


# ───────────────────────────────────────────────────────────────────
# _check_distraction — distraction avoidance
# ───────────────────────────────────────────────────────────────────


class TestCheckDistraction:
    def test_distraction_not_present(self):
        dist = DistractionSpec(role="sidebar_ad", match_by=ElementMatcher(id="ad"))
        analysis = _analysis()
        check = _check_distraction(dist, analysis, [])
        assert check.hit is False
        assert "not present" in check.notes.lower()

    def test_distraction_not_targeted(self):
        el = _el(id="ad", selector="#ad")
        dist = DistractionSpec(role="sidebar_ad", match_by=ElementMatcher(id="ad"))
        steps = [{"action_type": "fill", "ok": True, "target_selector": "#other", "step_index": 0}]
        check = _check_distraction(dist, _analysis(other=[el]), steps)
        assert check.hit is False

    def test_distraction_hit_by_click(self):
        el = _el(id="ad", selector="#ad", category="clickable", tag="div")
        dist = DistractionSpec(role="sidebar_ad", match_by=ElementMatcher(id="ad"))
        steps = [{"action_type": "click", "ok": True, "target_selector": "#ad", "step_index": 3}]
        check = _check_distraction(dist, _analysis(clickable=[el]), steps)
        assert check.hit is True
        assert check.hit_by_step_index == 3

    def test_distraction_hit_by_fill(self):
        el = _el(id="ad", selector="#ad")
        dist = DistractionSpec(role="decoy_input", match_by=ElementMatcher(id="ad"))
        steps = [{"action_type": "fill", "ok": True, "target_selector": "#ad", "step_index": 1}]
        check = _check_distraction(dist, _analysis(fillable=[el]), steps)
        assert check.hit is True

    def test_distraction_ignores_observe_steps(self):
        el = _el(id="ad", selector="#ad", category="clickable", tag="div")
        dist = DistractionSpec(role="ad", match_by=ElementMatcher(id="ad"))
        steps = [{"action_type": "observe", "ok": True, "target_selector": "#ad", "step_index": 0}]
        check = _check_distraction(dist, _analysis(clickable=[el]), steps)
        assert check.hit is False


# ───────────────────────────────────────────────────────────────────
# _check_success_signals / _check_failure_signals
# ───────────────────────────────────────────────────────────────────


class TestSignals:
    def _scenario(self, **kwargs) -> SimpleNamespace:
        return SimpleNamespace(
            success_signals=SuccessSignals(**kwargs.pop("success", {})),
            failure_signals=FailureSignals(**kwargs.pop("failure", {})),
            **kwargs,
        )

    def test_success_url_contains(self):
        result = _result(final_url="http://test/dashboard")
        notes = _check_success_signals(result, self._scenario(success={"url_contains": "dashboard"}))
        assert notes == []

    def test_success_url_contains_fail(self):
        result = _result(final_url="http://test/login")
        notes = _check_success_signals(result, self._scenario(success={"url_contains": "dashboard"}))
        assert len(notes) == 1
        assert "url_contains" in notes[0]

    def test_success_title_contains(self):
        result = _result(final_title="Dashboard - MyApp")
        notes = _check_success_signals(result, self._scenario(success={"title_contains": "Dashboard"}))
        assert notes == []

    def test_success_title_contains_fail(self):
        result = _result(final_title="Login")
        notes = _check_success_signals(result, self._scenario(success={"title_contains": "Dashboard"}))
        assert len(notes) == 1

    def test_success_dom_contains_all_of(self):
        result = _result(final_state={"body_text": "Welcome John"})
        notes = _check_success_signals(
            result, self._scenario(success={"dom_contains_all_of": ["Welcome", "John"]}),
        )
        assert notes == []

    def test_success_dom_contains_all_of_missing(self):
        result = _result(final_state={"body_text": "Welcome"})
        notes = _check_success_signals(
            result, self._scenario(success={"dom_contains_all_of": ["Welcome", "John"]}),
        )
        assert len(notes) == 1
        assert "dom_contains_all_of" in notes[0]

    def test_success_dom_contains_any_of(self):
        result = _result(final_state={"body_text": "Error: invalid"})
        notes = _check_success_signals(
            result, self._scenario(success={"dom_contains_any_of": ["Success", "Error"]}),
        )
        assert notes == []

    def test_success_dom_contains_any_of_none(self):
        result = _result(final_state={"body_text": "Nothing"})
        notes = _check_success_signals(
            result, self._scenario(success={"dom_contains_any_of": ["Success", "Error"]}),
        )
        assert len(notes) == 1

    def test_success_dom_has_test_id(self):
        result = _result(final_state={"test_ids": ["ok-banner", "nav"]})
        notes = _check_success_signals(
            result, self._scenario(success={"dom_has_test_id": "ok-banner"}),
        )
        assert notes == []

    def test_success_dom_has_test_id_missing(self):
        result = _result(final_state={"test_ids": ["other"]})
        notes = _check_success_signals(
            result, self._scenario(success={"dom_has_test_id": "ok-banner"}),
        )
        assert len(notes) == 1

    def test_failure_url_contains(self):
        result = _result(final_url="http://test/login")
        notes = _check_failure_signals(
            result, self._scenario(failure={"url_contains": "login"}),
        )
        assert notes == []

    def test_failure_alert_visible(self):
        result = _result(final_state={"alert_texts": ["Invalid credentials"]})
        notes = _check_failure_signals(
            result, self._scenario(failure={"alert_visible": True}),
        )
        assert notes == []

    def test_failure_alert_visible_missing(self):
        result = _result(final_state={"alert_texts": []})
        notes = _check_failure_signals(
            result, self._scenario(failure={"alert_visible": True}),
        )
        assert len(notes) == 1
        assert "alert_visible" in notes[0]

    def test_failure_alert_text_contains(self):
        result = _result(final_state={"alert_texts": ["Invalid credentials"]})
        notes = _check_failure_signals(
            result, self._scenario(failure={"alert_text_contains_any_of": ["Invalid"]}),
        )
        assert notes == []

    def test_failure_alert_text_contains_miss(self):
        result = _result(final_state={"alert_texts": ["Something else"]})
        notes = _check_failure_signals(
            result, self._scenario(failure={"alert_text_contains_any_of": ["Invalid"]}),
        )
        assert len(notes) == 1

    def test_no_signals_configured(self):
        result = _result()
        notes = _check_success_signals(result, self._scenario())
        assert notes == []
        notes = _check_failure_signals(result, self._scenario())
        assert notes == []


# ───────────────────────────────────────────────────────────────────
# _check_verdict
# ───────────────────────────────────────────────────────────────────


class TestCheckVerdict:
    def _scenario(self, **kwargs) -> SimpleNamespace:
        return SimpleNamespace(
            expected_verdict=kwargs.get("expected_verdict"),
            expected_verdict_not=kwargs.get("expected_verdict_not"),
            must_not_transition_to=kwargs.get("must_not_transition_to"),
            success_signals=SuccessSignals(),
            failure_signals=FailureSignals(),
        )

    def test_expected_verdict_match(self):
        result = _result(verdict="success")
        check = _check_verdict(result, self._scenario(expected_verdict="success"))
        assert check.matches_expectation is True

    def test_expected_verdict_mismatch(self):
        result = _result(verdict="failure")
        check = _check_verdict(result, self._scenario(expected_verdict="success"))
        assert check.matches_expectation is False
        assert "expected verdict" in check.notes

    def test_expected_verdict_not_match(self):
        result = _result(verdict="failure")
        check = _check_verdict(result, self._scenario(expected_verdict_not="success"))
        assert check.matches_expectation is True

    def test_expected_verdict_not_violated(self):
        result = _result(verdict="success")
        check = _check_verdict(result, self._scenario(expected_verdict_not="success"))
        assert check.matches_expectation is False
        assert "must not be" in check.notes

    def test_must_not_transition_to(self):
        result = _result(final_url="http://test/entry")
        check = _check_verdict(result, self._scenario(must_not_transition_to="/entry"))
        assert check.matches_expectation is False
        assert "must not transition" in check.notes

    def test_must_not_transition_ok(self):
        result = _result(final_url="http://test/dashboard")
        check = _check_verdict(result, self._scenario(must_not_transition_to="/entry"))
        assert check.matches_expectation is True

    def test_success_signals_checked(self):
        result = _result(
            verdict="success",
            final_url="http://test/other",
        )
        check = _check_verdict(
            result,
            self._scenario(expected_verdict="success", **{"_sf": None}),
        )
        # success_signals is empty so no failure
        assert check.matches_expectation is True

    def test_failure_signals_checked(self):
        result = _result(
            verdict="failure",
            final_url="http://test/ok",
            final_state={"alert_texts": []},
        )
        scenario = SimpleNamespace(
            expected_verdict=None,
            expected_verdict_not="success",
            must_not_transition_to=None,
            success_signals=SuccessSignals(),
            failure_signals=FailureSignals(alert_visible=True),
        )
        check = _check_verdict(result, scenario)
        assert check.matches_expectation is False


# ───────────────────────────────────────────────────────────────────
# _check_supervisor
# ───────────────────────────────────────────────────────────────────


class TestCheckSupervisor:
    def _scenario(self, expected_verdict="success", expected_verdict_not=None) -> SimpleNamespace:
        return SimpleNamespace(
            expected_verdict=expected_verdict,
            expected_verdict_not=expected_verdict_not,
        )

    def test_score_1_with_goal_observed_and_evidence(self):
        result = _result(supervisor={
            "verdict": "success",
            "observations": {
                "scenario_goal_observed": True,
                "scenario_goal_evidence": "Login succeeded.",
            },
        })
        check = _check_supervisor(result, self._scenario())
        assert check.score == 1.0
        assert "observed scenario goal" in check.notes

    def test_score_0_5_goal_observed_no_evidence(self):
        result = _result(supervisor={
            "verdict": "success",
            "observations": {
                "scenario_goal_observed": True,
                "scenario_goal_evidence": "",
            },
        })
        check = _check_supervisor(result, self._scenario())
        assert check.score == 0.5
        assert "no evidence" in check.notes

    def test_score_0_goal_not_observed(self):
        result = _result(supervisor={
            "verdict": "failure",
            "observations": {
                "scenario_goal_observed": False,
                "scenario_goal_evidence": "",
            },
        })
        check = _check_supervisor(result, self._scenario())
        assert check.score == 0.0
        assert "did not see" in check.notes

    def test_score_0_missing_atom(self):
        result = _result(supervisor={
            "verdict": "success",
            "observations": {},
        })
        check = _check_supervisor(result, self._scenario())
        assert check.score == 0.0
        assert "no supervisor observations" in check.notes

    def test_score_0_no_supervisor(self):
        result = _result(supervisor=None)
        check = _check_supervisor(result, self._scenario())
        assert check.score == 0.0
        assert "missing" in check.notes

    def test_score_0_no_observations(self):
        result = _result(supervisor={"verdict": "success"})
        check = _check_supervisor(result, self._scenario())
        assert check.score == 0.0
        assert "no supervisor observations" in check.notes

    def test_expected_bucket_non_success(self):
        result = _result(supervisor={
            "verdict": "failure",
            "observations": {
                "scenario_goal_observed": True,
                "scenario_goal_evidence": "Error shown.",
            },
        })
        check = _check_supervisor(result, self._scenario(expected_verdict=None, expected_verdict_not="success"))
        assert check.expected_bucket == "non_success"

    def test_expected_bucket_specific(self):
        result = _result(supervisor={
            "verdict": "partial_success",
            "observations": {
                "scenario_goal_observed": True,
                "scenario_goal_evidence": "Partial.",
            },
        })
        check = _check_supervisor(result, self._scenario(expected_verdict="partial_success"))
        assert check.expected_bucket == "partial_success"

    def test_expected_bucket_unspecified(self):
        result = _result(supervisor={
            "verdict": "uncertain",
            "observations": {
                "scenario_goal_observed": True,
                "scenario_goal_evidence": "Something.",
            },
        })
        check = _check_supervisor(result, self._scenario(expected_verdict=None))
        assert check.expected_bucket == "unspecified"


# ───────────────────────────────────────────────────────────────────
# verify_against_spec — integration
# ───────────────────────────────────────────────────────────────────


class TestVerifyAgainstSpec:
    def test_scenario_not_found(self):
        spec = _spec(scenarios={"valid": ScenarioSpec()})
        result = _result()
        with pytest.raises(KeyError, match="not_found"):
            verify_against_spec(result, spec, "not_found")

    def test_all_checks_pass(self):
        el = _el(id="username", selector="#username", semantic_role="username")
        spec = _spec(
            critical_elements=[
                CriticalElementSpec(
                    role="username_input",
                    expected_category="fillable",
                    expected_semantic_role="username",
                    match_by=ElementMatcher(id="username"),
                ),
            ],
            scenarios={
                "valid": ScenarioSpec(
                    expected_actions=["fill:username_input"],
                    expected_verdict="success",
                ),
            },
        )
        result = _result(
            analysis=_analysis(fillable=[el]),
            steps=[{"action_type": "fill", "ok": True, "target_selector": "#username", "step_index": 0}],
            verdict="success",
            supervisor=_ok_supervisor(),
        )
        sc = verify_against_spec(result, spec, "valid")
        assert sc.element_recognition.score == 1.0
        assert sc.action_coverage.score == 1.0
        assert sc.verdict_accuracy.score == 1.0
        assert sc.distraction_avoidance.score == 1.0
        assert sc.supervisor_agreement.score == 1.0
        assert sc.pass_gate.status == "pass"

    def test_element_score_partial(self):
        e1 = _el(id="a", selector="#a")
        e2_missing = _el(id="b", selector="#b")
        spec = _spec(
            critical_elements=[
                CriticalElementSpec(role="a", expected_category="fillable", match_by=ElementMatcher(id="a")),
                CriticalElementSpec(role="b", expected_category="fillable", match_by=ElementMatcher(id="b")),
            ],
            scenarios={"s": ScenarioSpec()},
        )
        result = _result(analysis=_analysis(fillable=[e1]))
        sc = verify_against_spec(result, spec, "s")
        assert sc.element_recognition.score == 0.5
        assert sc.pass_gate.status == "fail"

    def test_no_elements_no_actions_trivially_ok(self):
        spec = _spec(scenarios={"s": ScenarioSpec()})
        result = _result(supervisor=_ok_supervisor())
        sc = verify_against_spec(result, spec, "s")
        assert sc.element_recognition.score == 1.0
        assert sc.action_coverage.score == 1.0

    def test_distraction_score_reduced(self):
        ad = _el(id="ad", selector="#ad", category="clickable", tag="div")
        spec = _spec(
            distractions=[DistractionSpec(role="ad", match_by=ElementMatcher(id="ad"))],
            scenarios={"s": ScenarioSpec()},
        )
        result = _result(
            analysis=_analysis(clickable=[ad]),
            steps=[{"action_type": "click", "ok": True, "target_selector": "#ad", "step_index": 0}],
            supervisor=_ok_supervisor(),
        )
        sc = verify_against_spec(result, spec, "s")
        assert sc.distraction_avoidance.score == 0.0
        assert sc.pass_gate.status == "fail"

    def test_skipped_elements_excluded_from_score(self):
        el = _el(id="alert", selector="#alert", category="other", tag="div")
        spec = _spec(
            critical_elements=[
                CriticalElementSpec(
                    role="alert",
                    expected_category="other",
                    match_by=ElementMatcher(id="alert"),
                    visible_only_on=["other_scenario"],
                ),
            ],
            scenarios={"s": ScenarioSpec()},
        )
        result = _result(supervisor=_ok_supervisor())
        sc = verify_against_spec(result, spec, "s")
        # Skipped elements are excluded → trivially 1.0
        assert sc.element_recognition.score == 1.0


# ───────────────────────────────────────────────────────────────────
# load_spec
# ───────────────────────────────────────────────────────────────────


class TestLoadSpec:
    @staticmethod
    def _write_spec(root: Path, spec_id: str, page_id: str | None = None) -> Path:
        path = root / f"{spec_id}.assertions.json"
        path.write_text(
            json.dumps({
                "page_id": page_id or spec_id,
                "description": f"{spec_id} test spec",
                "critical_elements": [],
                "scenarios": {
                    "s": {
                        "description": "test scenario",
                    },
                },
            }),
            encoding="utf-8",
        )
        return path

    def test_get_spec_root_requires_env_only_when_specs_are_used(self, monkeypatch):
        monkeypatch.delenv("WAF_PAGE_SPEC_ROOT", raising=False)
        with pytest.raises(SpecRootNotConfigured, match="WAF_PAGE_SPEC_ROOT"):
            get_spec_root()

    def test_load_spec_not_found_in_configured_root(self, monkeypatch, tmp_path):
        monkeypatch.setenv("WAF_PAGE_SPEC_ROOT", str(tmp_path))
        with pytest.raises(SpecNotFound, match="not found"):
            load_spec("nonexistent_spec_12345")

    def test_load_spec_uses_configured_external_root_without_fallback(
        self,
        monkeypatch,
        tmp_path,
    ):
        root = tmp_path / "external-specs"
        root.mkdir()
        expected_path = self._write_spec(root, "external_login", page_id="login")
        monkeypatch.setenv("WAF_PAGE_SPEC_ROOT", str(root))

        assert get_spec_root() == root.resolve()
        spec, path = load_spec("external_login")

        assert spec.page_id == "login"
        assert path == expected_path.resolve()
        with pytest.raises(SpecNotFound, match=str(root.resolve())):
            load_spec("login")

    def test_iter_spec_paths_requires_configured_root(self, monkeypatch):
        monkeypatch.delenv("WAF_PAGE_SPEC_ROOT", raising=False)
        with pytest.raises(SpecRootNotConfigured, match="WAF_PAGE_SPEC_ROOT"):
            iter_spec_paths()

    def test_iter_spec_paths_uses_stable_sorted_order(self, monkeypatch, tmp_path):
        root = tmp_path / "external-specs"
        root.mkdir()
        self._write_spec(root, "zeta")
        self._write_spec(root, "alpha")
        monkeypatch.setenv("WAF_PAGE_SPEC_ROOT", str(root))

        assert [path.name for path in iter_spec_paths()] == [
            "alpha.assertions.json",
            "zeta.assertions.json",
        ]

    @pytest.mark.parametrize(
        "spec_id",
        [
            "../login",
            "nested/login",
            "/tmp/login",
            "login/../users",
            r"nested\login",
        ],
    )
    def test_load_spec_rejects_unsafe_spec_id(self, monkeypatch, tmp_path, spec_id):
        monkeypatch.setenv("WAF_PAGE_SPEC_ROOT", str(tmp_path))
        with pytest.raises(UnsafeSpecId, match="Invalid spec_id"):
            load_spec(spec_id)

    def test_spec_routes_keep_health_independent_from_spec_root(
        self,
        monkeypatch,
        client,
    ):
        monkeypatch.delenv("WAF_PAGE_SPEC_ROOT", raising=False)

        health = client.get("/health")
        specs = client.get("/exploration/specs")

        assert health.status_code == 200
        assert specs.status_code == 503
        assert "WAF_PAGE_SPEC_ROOT" in specs.json()["msg"]

    def test_spec_routes_map_missing_spec_to_404(self, monkeypatch, tmp_path, client):
        monkeypatch.setenv("WAF_PAGE_SPEC_ROOT", str(tmp_path))

        response = client.get("/exploration/specs/missing")

        assert response.status_code == 404
        assert "Page verification spec not found" in response.json()["msg"]

    def test_spec_routes_map_unsafe_spec_id_to_400(
        self,
        monkeypatch,
        tmp_path,
        client,
    ):
        monkeypatch.setenv("WAF_PAGE_SPEC_ROOT", str(tmp_path))

        response = client.get("/exploration/specs/%5Cbad")

        assert response.status_code == 400
        assert "Invalid spec_id" in response.json()["msg"]

    def test_list_specs_reads_configured_root_in_sorted_order(
        self,
        monkeypatch,
        tmp_path,
        client,
    ):
        self._write_spec(tmp_path, "zeta")
        self._write_spec(tmp_path, "alpha")
        monkeypatch.setenv("WAF_PAGE_SPEC_ROOT", str(tmp_path))

        response = client.get("/exploration/specs")

        assert response.status_code == 200
        payload = response.json()["data"]
        assert [item["spec_id"] for item in payload] == ["alpha", "zeta"]
