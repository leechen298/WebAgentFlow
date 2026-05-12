"""Tests for Planning Preview Service (11.1.4).

Covers retrieval + planner orchestration, preview message formatting,
event payload construction, and boundary compliance.
"""

from __future__ import annotations

from app.schemas.conversation import ConversationEventType
from app.schemas.task_planning import (
    AgentDPlannerOutput,
    ConfirmationRequirement,
    LearnedPathCandidate,
    RiskHint,
    RoutePlan,
    RouteStep,
    TaskIntent,
)
from app.services.task_planning.preview import PlanningPreviewResult, PlanningPreviewService

# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubRetrieval:
    def __init__(self, candidates: list[LearnedPathCandidate]) -> None:
        self._candidates = candidates

    def retrieve_candidates(self, task_intent: TaskIntent) -> list[LearnedPathCandidate]:
        return list(self._candidates)


class _StubPlanner:
    def __init__(self, output: AgentDPlannerOutput) -> None:
        self._output = output

    def plan(
        self, task_intent: TaskIntent, candidates: list[LearnedPathCandidate]
    ) -> AgentDPlannerOutput:
        return self._output


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _candidate(
    learned_path_id: str = "lp-001",
    scenario: str = "login",
    page_template: str = "/login",
    trust: str = "confirmed",
    match_reasons: list[str] | None = None,
    warnings: list[str] | None = None,
) -> LearnedPathCandidate:
    return LearnedPathCandidate(
        learned_path_id=learned_path_id,
        scenario=scenario,
        page_template=page_template,
        trust=trust,  # type: ignore[arg-type]
        match_reasons=match_reasons or [],
        warnings=warnings or [],
    )


def _service(
    candidates: list[LearnedPathCandidate] | None = None,
    planner_output: AgentDPlannerOutput | None = None,
) -> PlanningPreviewService:
    retrieval = _StubRetrieval(candidates or [])
    planner = _StubPlanner(
        planner_output
        or AgentDPlannerOutput(
            route_plan=RoutePlan(
                task_intent=TaskIntent(raw_text="log in"),
                steps=[
                    RouteStep(
                        order=0,
                        learned_path_id="lp-001",
                        purpose="Execute login on /login",
                    )
                ],
            )
        )
    )
    return PlanningPreviewService(retrieval, planner)


# ---------------------------------------------------------------------------
# Basic flow
# ---------------------------------------------------------------------------


def test_preview_returns_proposed_for_successful_plan() -> None:
    svc = _service()
    result = svc.preview("log in")

    assert isinstance(result, PlanningPreviewResult)
    assert result.event_type == ConversationEventType.PLAN_PREVIEW_PROPOSED.value
    assert result.confirmation_required is False
    assert result.selected_path_id == "lp-001"
    assert "Plan:" in result.user_response
    assert "Selected path: lp-001" in result.user_response


def test_preview_returns_unable_when_planner_returns_none() -> None:
    svc = _service(
        candidates=[_candidate()],
        planner_output=AgentDPlannerOutput(route_plan=None),
    )
    result = svc.preview("do something impossible")

    assert result.event_type == ConversationEventType.PLAN_PREVIEW_UNABLE.value
    assert result.confirmation_required is False
    assert result.selected_path_id is None
    assert "Unable to plan" in result.user_response


# ---------------------------------------------------------------------------
# Confirmation propagation
# ---------------------------------------------------------------------------


def test_preview_sets_confirmation_required_when_planner_requires_it() -> None:
    svc = _service(
        candidates=[_candidate(trust="provisional")],
        planner_output=AgentDPlannerOutput(
            route_plan=RoutePlan(
                task_intent=TaskIntent(raw_text="log in"),
                steps=[
                    RouteStep(
                        order=0,
                        learned_path_id="lp-prov",
                        purpose="Execute provisional path",
                    )
                ],
                confirmation_required=True,
            ),
            confirmation_requirements=[
                ConfirmationRequirement(
                    reason="provisional_trust",
                    message="Path is provisional.",
                    severity="warning",
                )
            ],
        ),
    )
    result = svc.preview("log in")

    assert result.confirmation_required is True
    assert "Confirmation required" in result.user_response


def test_preview_sets_confirmation_required_for_flaky_path() -> None:
    svc = _service(
        candidates=[_candidate(trust="flaky")],
        planner_output=AgentDPlannerOutput(
            route_plan=RoutePlan(
                task_intent=TaskIntent(raw_text="log in"),
                steps=[
                    RouteStep(
                        order=0,
                        learned_path_id="lp-flaky",
                        purpose="Execute flaky path",
                    )
                ],
                confirmation_required=True,
            ),
            confirmation_requirements=[
                ConfirmationRequirement(
                    reason="flaky_trust",
                    message="Path is flaky.",
                    severity="warning",
                )
            ],
            risk_hints=[
                RiskHint(
                    risk_type="flaky_path", reason="Intermittent failures", severity="warning"
                )
            ],
        ),
    )
    result = svc.preview("log in")

    assert result.confirmation_required is True
    assert "Confirmation required" in result.user_response


# ---------------------------------------------------------------------------
# Event payload
# ---------------------------------------------------------------------------


def test_preview_payload_contains_candidate_count_and_raw_text() -> None:
    svc = _service(candidates=[_candidate(), _candidate(learned_path_id="lp-002")])
    result = svc.preview("log in")

    payload = result.event_payload
    assert payload["task_intent_raw_text"] == "log in"
    assert payload["candidate_count"] == 2
    assert payload["planning_status"] == "proposed"


def test_preview_payload_contains_selected_path_when_proposed() -> None:
    svc = _service()
    result = svc.preview("log in")

    payload = result.event_payload
    assert payload["selected_path_id"] == "lp-001"
    assert payload["selected_purpose"] == "Execute login on /login"


def test_preview_payload_contains_warnings_and_risk_hints() -> None:
    svc = _service(
        candidates=[_candidate()],
        planner_output=AgentDPlannerOutput(
            route_plan=RoutePlan(
                task_intent=TaskIntent(raw_text="log in"),
                steps=[
                    RouteStep(
                        order=0,
                        learned_path_id="lp-001",
                        purpose="Execute login",
                        warnings=["drift detected"],
                    )
                ],
            ),
            warnings=["drift detected"],
            risk_hints=[
                RiskHint(risk_type="drift", reason="selector changed", severity="warning")
            ],
        ),
    )
    result = svc.preview("log in")

    payload = result.event_payload
    assert payload["warnings"] == ["drift detected"]
    assert payload["risk_hints"] == [
        {"type": "drift", "reason": "selector changed"}
    ]


def test_preview_payload_contains_confirmation_reasons() -> None:
    svc = _service(
        planner_output=AgentDPlannerOutput(
            route_plan=RoutePlan(
                task_intent=TaskIntent(raw_text="log in"),
                steps=[RouteStep(order=0, learned_path_id="lp-001", purpose="Execute")],
                confirmation_required=True,
            ),
            confirmation_requirements=[
                ConfirmationRequirement(
                    reason="ambiguous_selection",
                    message="Multiple candidates match.",
                    severity="info",
                )
            ],
        ),
    )
    result = svc.preview("log in")

    payload = result.event_payload
    assert payload["confirmation_reasons"] == [
        {"reason": "ambiguous_selection", "message": "Multiple candidates match."}
    ]


# ---------------------------------------------------------------------------
# Boundary compliance
# ---------------------------------------------------------------------------


def test_preview_module_does_not_import_replay_autonomous_or_llm() -> None:
    import app.services.task_planning.preview as preview_mod

    source = preview_mod.__file__
    assert source is not None
    with open(source, encoding="utf-8") as f:
        text = f.read()

    import_lines = [
        line for line in text.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    joined = "\n".join(import_lines).lower()
    forbidden = ["autonomous", "replay", "llm", "html_ast", "playwright"]
    for term in forbidden:
        assert term not in joined, f"preview imports {term}"
