"""Tests for M11.3 learning run service."""

from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.schemas.page_analysis import AutonomousExplorationResult, PageAnalysis
from app.services.learning.learning_run_service import LearningRunRequest, LearningRunService


class _DummyRuntimeFactory:
    def __call__(self, config):
        return self

    def __enter__(self):
        return SimpleNamespace(page=None)

    def __exit__(self, exc_type, exc, tb):
        return False


def _exploration_result() -> AutonomousExplorationResult:
    return AutonomousExplorationResult(
        page_analysis=PageAnalysis(url="http://localhost:5175/login", title="Sign in"),
        steps=[
            {"step": 1, "action_type": "fill", "target_selector": "#username", "value": "admin"},
            {"step": 2, "action_type": "fill", "target_selector": "#password", "value": "123456"},
            {"step": 3, "action_type": "click", "target_selector": "button[type=submit]"},
        ],
        total_steps=3,
        final_url="http://localhost:5175/dashboard",
        final_title="Dashboard",
        verdict="success",
        success=True,
        summary="login ok",
    )


def test_learning_service_returns_run_id_and_queryable_learned_path_id(
    db_session: Session,
) -> None:
    def explorer(**kwargs):
        return _exploration_result()

    scorecard = SimpleNamespace(
        model_dump=lambda: {
            "pass_gate": {"status": "pass", "reasons": []},
            "verdict_check": {"matches_expectation": True},
        }
    )
    spec = SimpleNamespace(
        page_id="login",
        scenarios={
            "valid_credentials": SimpleNamespace(
                description="Valid login",
                inputs={"username": "admin", "password": "123456"},
            )
        },
    )
    service = LearningRunService(
        db_session,
        runtime_factory=_DummyRuntimeFactory(),
        explorer=explorer,
        spec_loader=lambda spec_id: (spec, "login.assertions.json"),
        verifier=lambda result, loaded_spec, scenario: scorecard,
    )

    result = service.run(
        LearningRunRequest(
            url="http://localhost:5175/login",
            spec_id="login",
            scenario="valid_credentials",
            goal="学习登录",
            fill_values={"username": "admin", "password": "123456"},
        )
    )

    assert result.status == "learned"
    assert result.run_id is not None
    assert result.learned_path_id is not None
    assert result.action_label == "登录"
    assert result.suggested_utterances == ["帮我登录", "登录一下"]
