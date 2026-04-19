"""Wiring tests for the toggle_values path (Phase 9 radio scope).

The planner-level logic is covered by test_toggle_values.py. This file
pins down the glue:

- ``ScenarioSpec`` accepts a ``selections`` field.
- ``users.assertions.json`` parses cleanly and the ``filter_by_status``
  scenario carries the expected ``selections``.
- ``ElementMatcher`` accepts ``element_value`` so critical_elements can
  pinpoint a specific radio within a group.
- ``AutonomousExplorePayload`` accepts ``toggle_values``.
- ``SpecScenarioSummary`` surfaces ``selections`` so the workbench can
  hydrate the toggle editor.
"""

from __future__ import annotations

from app.routers.exploration import AutonomousExplorePayload, SpecScenarioSummary
from app.schemas.page_verification import ElementMatcher, ScenarioSpec
from app.services.learning.page_verification import load_spec


def test_scenario_spec_accepts_selections() -> None:
    sc = ScenarioSpec(selections={"status": "active"})
    assert sc.selections == {"status": "active"}
    assert sc.inputs == {}


def test_scenario_spec_selections_default_empty() -> None:
    sc = ScenarioSpec()
    assert sc.selections == {}


def test_element_matcher_accepts_element_value() -> None:
    m = ElementMatcher(tag="input", element_type="radio", element_value="active")
    assert m.element_value == "active"


def test_users_spec_loads_with_filter_by_status() -> None:
    spec, _ = load_spec("users")
    assert "filter_by_status" in spec.scenarios
    sc = spec.scenarios["filter_by_status"]
    assert sc.selections == {"status": "active"}
    # Text inputs stay empty for this scenario — it drives the toggle
    # path only.
    assert sc.inputs == {}
    assert "click:status_radio_active" in sc.expected_actions
    assert "click:search_button" in sc.expected_actions


def test_users_spec_has_status_radio_active_critical_element() -> None:
    spec, _ = load_spec("users")
    roles = [ce.role for ce in spec.critical_elements]
    assert "status_radio_active" in roles
    ce = next(ce for ce in spec.critical_elements if ce.role == "status_radio_active")
    assert ce.expected_category == "toggle"
    assert ce.match_by.element_type == "radio"
    assert ce.match_by.element_value == "active"


def test_autonomous_explore_payload_accepts_toggle_values() -> None:
    payload = AutonomousExplorePayload(
        url="http://test/",
        toggle_values={"status": "active"},
    )
    assert payload.toggle_values == {"status": "active"}


def test_autonomous_explore_payload_toggle_values_default_none() -> None:
    payload = AutonomousExplorePayload(url="http://test/")
    assert payload.toggle_values is None


def test_spec_scenario_summary_carries_selections() -> None:
    summary = SpecScenarioSummary(
        key="filter_by_status",
        selections={"status": "active"},
    )
    assert summary.selections == {"status": "active"}
    assert summary.inputs == {}
