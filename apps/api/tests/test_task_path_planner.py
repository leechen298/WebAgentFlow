"""Tests for Task Path Planner (11.1.3).

Covers candidate selection, route-plan generation, warning propagation,
ambiguity detection, and boundary compliance.
"""

from __future__ import annotations

from app.schemas.task_planning import (
    AgentDPlannerOutput,
    LearnedPathCandidate,
    TaskIntent,
)
from app.services.task_planning.planner import TaskPathPlanner

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _candidate(
    learned_path_id: str = "lp-001",
    scenario: str = "login",
    page_template: str = "/login",
    trust: str = "confirmed",
    hit_count: int = 5,
    match_reasons: list[str] | None = None,
    warnings: list[str] | None = None,
    drift_evidence_summary: str | None = None,
    negative_evidence_summary: str | None = None,
) -> LearnedPathCandidate:
    return LearnedPathCandidate(
        learned_path_id=learned_path_id,
        scenario=scenario,
        page_template=page_template,
        trust=trust,  # type: ignore[arg-type]
        hit_count=hit_count,
        match_reasons=match_reasons or [],
        warnings=warnings or [],
        drift_evidence_summary=drift_evidence_summary,
        negative_evidence_summary=negative_evidence_summary,
    )


# ---------------------------------------------------------------------------
# Empty / no-candidate handling
# ---------------------------------------------------------------------------


def test_empty_candidates_returns_unable_to_plan() -> None:
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="log in")
    result = planner.plan(intent, [])

    assert result.route_plan is None
    assert any("No valid" in u for u in result.uncertainty)
    assert any("Unable to plan" in w for w in result.warnings)
    assert any(c.reason == "unable_to_plan" for c in result.confirmation_requirements)
    assert all(
        c.severity == "blocking"
        for c in result.confirmation_requirements
        if c.reason == "unable_to_plan"
    )


def test_empty_candidates_does_not_call_retrieval() -> None:
    """Planner core method accepts candidates directly; it never calls retrieval."""
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="log in")
    # Direct call with empty list — no hidden side effects, no autonomous run.
    result = planner.plan(intent, [])
    assert result.route_plan is None


# ---------------------------------------------------------------------------
# Defensive deprecated filtering
# ---------------------------------------------------------------------------


def test_deprecated_candidate_is_ignored() -> None:
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="log in")
    deprecated = _candidate(learned_path_id="lp-dep", trust="deprecated")
    result = planner.plan(intent, [deprecated])

    assert result.route_plan is None
    assert any("No valid" in u for u in result.uncertainty)


def test_deprecated_ignored_but_confirmed_used() -> None:
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="log in")
    deprecated = _candidate(learned_path_id="lp-dep", trust="deprecated")
    confirmed = _candidate(learned_path_id="lp-ok", trust="confirmed")
    result = planner.plan(intent, [deprecated, confirmed])

    assert result.route_plan is not None
    assert result.route_plan.steps[0].learned_path_id == "lp-ok"


# ---------------------------------------------------------------------------
# Confirmed candidate — minimal route plan
# ---------------------------------------------------------------------------


def test_confirmed_produces_minimal_route_plan() -> None:
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="log in as admin")
    candidate = _candidate(
        learned_path_id="lp-001",
        scenario="login",
        page_template="/login",
        trust="confirmed",
        match_reasons=["exact scenario match: login"],
    )
    result = planner.plan(intent, [candidate])

    assert result.route_plan is not None
    plan = result.route_plan
    assert len(plan.steps) == 1
    step = plan.steps[0]
    assert step.learned_path_id == "lp-001"
    assert step.order == 0
    assert "login" in step.purpose
    assert "/login" in step.purpose
    assert "log in as admin" in step.purpose
    assert step.can_execute is True
    assert step.bound_slots == {}
    # No warnings, no confirmation for a clean confirmed candidate.
    assert plan.confirmation_required is False
    assert result.confirmation_requirements == []
    assert result.risk_hints == []


def test_route_plan_preserves_learned_path_id_and_warnings() -> None:
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="update user status")
    candidate = _candidate(
        learned_path_id="lp-002",
        scenario="update_status",
        warnings=["page layout changed recently"],
    )
    result = planner.plan(intent, [candidate])

    step = result.route_plan.steps[0]
    assert step.learned_path_id == "lp-002"
    assert "page layout changed recently" in step.warnings


# ---------------------------------------------------------------------------
# Provisional candidate
# ---------------------------------------------------------------------------


def test_provisional_adds_confirmation_requirement() -> None:
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="reset password")
    candidate = _candidate(learned_path_id="lp-003", trust="provisional")
    result = planner.plan(intent, [candidate])

    assert result.route_plan is not None
    assert result.route_plan.confirmation_required is True
    assert any(c.reason == "provisional_trust" for c in result.confirmation_requirements)
    assert any("provisional trust" in c.message.lower() for c in result.confirmation_requirements)
    assert all(
        c.severity == "warning"
        for c in result.confirmation_requirements
        if c.reason == "provisional_trust"
    )


# ---------------------------------------------------------------------------
# Flaky candidate
# ---------------------------------------------------------------------------


def test_flaky_preserves_warning_and_adds_confirmation() -> None:
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="export report")
    candidate = _candidate(
        learned_path_id="lp-004",
        trust="flaky",
        warnings=["intermittent timeout"],
    )
    result = planner.plan(intent, [candidate])

    assert result.route_plan is not None
    # Candidate warnings preserved on route step.
    assert "intermittent timeout" in result.route_plan.steps[0].warnings
    # Flaky adds risk hint.
    assert any(r.risk_type == "flaky_path" for r in result.risk_hints)
    # Flaky adds confirmation requirement.
    assert any(c.reason == "flaky_trust" for c in result.confirmation_requirements)
    assert result.route_plan.confirmation_required is True


# ---------------------------------------------------------------------------
# Ambiguous candidate detection
# ---------------------------------------------------------------------------


def test_two_confirmed_with_exact_matches_is_ambiguous() -> None:
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="log in")
    first = _candidate(
        learned_path_id="lp-a",
        scenario="login",
        trust="confirmed",
        match_reasons=["exact scenario match: login"],
    )
    second = _candidate(
        learned_path_id="lp-b",
        scenario="sso_login",
        trust="confirmed",
        match_reasons=["exact scenario match: sso_login"],
    )
    result = planner.plan(intent, [first, second])

    assert result.route_plan is not None
    # Top candidate still selected.
    assert result.route_plan.steps[0].learned_path_id == "lp-a"
    # But ambiguity surfaces confirmation requirement.
    assert result.route_plan.confirmation_required is True
    assert any(c.reason == "ambiguous_selection" for c in result.confirmation_requirements)
    assert any("Multiple confirmed" in u for u in result.uncertainty)


def test_two_confirmed_without_strong_second_is_not_ambiguous() -> None:
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="log in")
    first = _candidate(
        learned_path_id="lp-a",
        scenario="login",
        trust="confirmed",
        match_reasons=["exact scenario match: login"],
    )
    second = _candidate(
        learned_path_id="lp-b",
        scenario="login_backup",
        trust="confirmed",
        match_reasons=["page contains: login"],  # not an exact match
    )
    result = planner.plan(intent, [first, second])

    assert result.route_plan is not None
    assert result.route_plan.confirmation_required is False
    assert not any(c.reason == "ambiguous_selection" for c in result.confirmation_requirements)


def test_single_confirmed_is_not_ambiguous() -> None:
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="log in")
    candidate = _candidate(learned_path_id="lp-a", trust="confirmed")
    result = planner.plan(intent, [candidate])

    assert not any(c.reason == "ambiguous_selection" for c in result.confirmation_requirements)


# ---------------------------------------------------------------------------
# Drift and negative evidence propagation
# ---------------------------------------------------------------------------


def test_drift_evidence_propagated_to_risk_hints() -> None:
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="log in")
    candidate = _candidate(
        learned_path_id="lp-005",
        trust="confirmed",
        drift_evidence_summary="button selector changed from #btn to .submit",
    )
    result = planner.plan(intent, [candidate])

    assert any("button selector changed" in w for w in result.warnings)
    assert any(r.risk_type == "drift" for r in result.risk_hints)
    assert any("button selector changed" in r.reason for r in result.risk_hints)


def test_negative_evidence_preserved_in_warnings() -> None:
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="log in")
    candidate = _candidate(
        learned_path_id="lp-006",
        trust="confirmed",
        negative_evidence_summary="failed 2 out of 10 replays",
    )
    result = planner.plan(intent, [candidate])

    assert any("failed 2 out of 10" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# Output contract checks
# ---------------------------------------------------------------------------


def test_output_is_agent_d_planner_output() -> None:
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="do something")
    candidate = _candidate()
    result = planner.plan(intent, [candidate])

    assert isinstance(result, AgentDPlannerOutput)


def test_route_plan_contains_task_intent() -> None:
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="specific task")
    candidate = _candidate()
    result = planner.plan(intent, [candidate])

    assert result.route_plan is not None
    assert result.route_plan.task_intent.raw_text == "specific task"


# ---------------------------------------------------------------------------
# Boundary / contract compliance
# ---------------------------------------------------------------------------


def test_planner_does_not_import_replay_autonomous_or_llm() -> None:
    """Verify planner module does not import disallowed subsystems."""
    import app.services.task_planning.planner as planner_mod

    source = planner_mod.__file__
    assert source is not None
    with open(source, encoding="utf-8") as f:
        text = f.read()

    # Check import lines only (exclude docstrings and comments).
    import_lines = [
        line for line in text.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    joined = "\n".join(import_lines).lower()
    forbidden = ["autonomous", "replay", "llm", "html_ast", "playwright"]
    for term in forbidden:
        assert term not in joined, f"planner imports {term}: {joined}"


def test_planner_does_not_call_retrieval_service() -> None:
    """Planner.plan receives candidates directly; no internal retrieval call."""
    # The service shape is plan(task_intent, candidates) -> output.
    # There is no retrieval dependency in the method signature or body.
    import inspect

    sig = inspect.signature(TaskPathPlanner.plan)
    params = list(sig.parameters.keys())
    assert "candidates" in params
    # No repo or retrieval service parameter.
    assert "repo" not in params
    assert "retrieval" not in params


def test_no_identity_or_tenant_fields_in_output() -> None:
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="log in")
    candidate = _candidate()
    result = planner.plan(intent, [candidate])

    # RoutePlan and AgentDPlannerOutput schemas do not contain user/account/tenant.
    raw = result.model_dump()
    flat = str(raw).lower()
    assert "user_id" not in flat
    assert "account_id" not in flat
    assert "tenant" not in flat
    assert "org_id" not in flat


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_all_deprecated_returns_unable_to_plan() -> None:
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="log in")
    candidates = [
        _candidate(learned_path_id="lp-1", trust="deprecated"),
        _candidate(learned_path_id="lp-2", trust="deprecated"),
    ]
    result = planner.plan(intent, candidates)
    assert result.route_plan is None


def test_planner_trusts_ranked_order_over_trust_level() -> None:
    """Planner does NOT re-rank by trust; it trusts the pre-sorted candidate order."""
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="log in")
    provisional = _candidate(learned_path_id="lp-prov", trust="provisional")
    confirmed = _candidate(learned_path_id="lp-conf", trust="confirmed")
    result = planner.plan(intent, [provisional, confirmed])

    # If provisional is ranked first by retrieval, planner selects it.
    assert result.route_plan.steps[0].learned_path_id == "lp-prov"


def test_match_reasons_propagated_to_output_warnings() -> None:
    """Retrieval match_reasons are copied into output warnings for auditability."""
    planner = TaskPathPlanner()
    intent = TaskIntent(raw_text="log in")
    candidate = _candidate(
        learned_path_id="lp-007",
        match_reasons=["exact scenario match: login", "page contains: auth"],
    )
    result = planner.plan(intent, [candidate])

    # Match reasons appear as structured warnings in AgentDPlannerOutput.
    assert any("exact scenario match: login" in w for w in result.warnings)
    assert any("page contains: auth" in w for w in result.warnings)
    assert any(w.startswith("Retrieval match:") for w in result.warnings)
