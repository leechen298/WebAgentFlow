"""Tests for M11.3 learning run service."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.exploration_run import ExplorationRun, ExplorationRunStatus
from app.models.learned_capability import LearnedCapability
from app.models.learned_path import LearnedPath
from app.models.learning_batch import LearningBatch, LearningBatchStatus
from app.schemas.learning_batch import BoundedLearningPolicy
from app.schemas.page_analysis import (
    AutonomousExplorationResult,
    DiscoveredElement,
    PageAnalysis,
)
from app.services.learning.capability_discovery import CapabilityScenario
from app.services.learning.learning_run_service import (
    LearningRunRequest,
    LearningRunService,
    _expected_bindings_have_action_evidence,
)


class _DummyRuntimeFactory:
    def __init__(self) -> None:
        self.call_count = 0
        self.enter_count = 0
        self.exit_count = 0
        self.page_state = {
            "controls": [],
            "result_regions": {
                "tableRows": 0,
                "roleRows": 0,
                "listItems": 0,
                "options": 0,
                "alerts": 0,
                "dialogs": 0,
                "modals": 0,
            },
        }
        self.runtime = SimpleNamespace(
            page=SimpleNamespace(evaluate=lambda _script: self.page_state),
            context=None,
            navigated_urls=[],
            navigate=lambda url: self.runtime.navigated_urls.append(url),
            current_url=lambda: self.runtime.navigated_urls[-1]
            if self.runtime.navigated_urls
            else "https://example.invalid/entry",
            current_title=lambda: "Dummy",
        )

    def __call__(self, config):
        self.call_count += 1
        return self

    def __enter__(self):
        self.enter_count += 1
        return self.runtime

    def __exit__(self, exc_type, exc, tb):
        self.exit_count += 1
        return False


def _exploration_result(
    *,
    url: str = "https://example.invalid/entry",
    title: str = "Sign in",
    final_url: str = "https://example.invalid/dashboard",
    final_title: str = "Dashboard",
    verdict: str = "success",
    success: bool = True,
    supervisor: dict[str, object] | None = None,
    steps: list[dict[str, object]] | None = None,
    final_state: dict[str, object] | None = None,
    page_analysis: PageAnalysis | None = None,
    terminal_state_verdict: dict[str, object] | None = None,
) -> AutonomousExplorationResult:
    return AutonomousExplorationResult(
        page_analysis=page_analysis or PageAnalysis(url=url, title=title),
        steps=steps
        or [
            {"step": 1, "action_type": "fill", "target_selector": "#username", "value": "admin"},
            {"step": 2, "action_type": "fill", "target_selector": "#password", "value": "123456"},
            {"step": 3, "action_type": "click", "target_selector": "button[type=submit]"},
        ],
        total_steps=len(steps or [1, 2, 3]),
        final_url=final_url,
        final_title=final_title,
        final_state=final_state or {},
        terminal_state_verdict=terminal_state_verdict
        or {
            "terminal_outcome": "terminal_detected",
            "terminal_type": "navigation",
            "evidence_strength": "strong",
            "stop_decision": "stop",
            "matched_action_ids": ["action-step-3"],
            "matched_step_indices": [3],
            "matched_action_types": ["click"],
            "source": "deterministic",
        },
        verdict=verdict,
        success=success,
        summary="login ok",
        supervisor=supervisor,
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
            url="https://example.invalid/entry",
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


def test_learning_service_blocks_unverified_terminal_state_ingest(
    db_session: Session,
) -> None:
    def explorer(**kwargs):
        return _exploration_result(
            terminal_state_verdict={
                "terminal_outcome": "terminal_unverified",
                "terminal_type": "no_observable_change",
                "evidence_strength": "weak",
                "stop_decision": "unverified_stop",
                "source": "deterministic",
            }
        )

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
            url="https://example.invalid/entry",
            spec_id="login",
            scenario="valid_credentials",
            goal="学习登录",
            fill_values={"username": "admin", "password": "123456"},
        )
    )

    assert result.status == "failed"
    assert result.learned_path_id is None
    assert list(db_session.scalars(select(LearnedPath)).all()) == []
    run = db_session.get(ExplorationRun, result.run_id)
    assert run is not None
    evaluation = (run.result_snapshot_json or {}).get("attempt_ingest_evaluation")
    assert evaluation["ingest_status"] == "unverified"
    assert evaluation["failure_category"] == "terminal_unverified"


def test_product_learning_does_not_load_validation_spec_and_labels_login_action(
    db_session: Session,
) -> None:
    explorer_calls = []

    def explorer(**kwargs):
        explorer_calls.append(kwargs)
        return _exploration_result(
            url="http://localhost:8080/login",
            title="登录入口",
            final_url="http://localhost:8080/account",
            final_title="账户首页",
        )

    def spec_loader(spec_id: str):
        raise AssertionError(f"product learning must not load spec: {spec_id}")

    service = LearningRunService(
        db_session,
        runtime_factory=_DummyRuntimeFactory(),
        explorer=explorer,
        spec_loader=spec_loader,
    )

    result = service.run(
        LearningRunRequest(
            url="http://localhost:8080/login",
            goal=(
                "学习一下这个登录页怎么登录，地址是 "
                "http://localhost:8080/login，操作员账号是 demo，访问口令是 123456"
            ),
            fill_values={"username": "demo", "password": "123456"},
            product_level=True,
        )
    )

    assert result.status == "learned"
    assert result.run_id is not None
    assert result.learned_path_id is not None
    assert result.scenario is None
    assert result.action_label == "登录"
    assert result.suggested_utterances == ["帮我登录", "登录一下"]
    assert "scenario_name" not in explorer_calls[0]
    assert explorer_calls[0]["fill_values"] == {"username": "demo", "password": "123456"}


def test_product_learning_strips_generic_named_value_from_action_label(
    db_session: Session,
) -> None:
    def explorer(**kwargs):
        return _exploration_result(
            url="http://example.test/records",
            title="记录",
            final_url="http://example.test/records",
            final_title="记录",
        )

    service = LearningRunService(
        db_session,
        runtime_factory=_DummyRuntimeFactory(),
        explorer=explorer,
    )

    result = service.run(
        LearningRunRequest(
            url="http://example.test/records",
            goal="学习创建记录，名称叫 Alpha-1",
            fill_values={"entity_name": "Alpha-1"},
            product_level=True,
        )
    )

    assert result.status == "learned"
    assert result.action_label == "创建记录"
    assert result.suggested_utterances == ["帮我创建记录", "创建记录一下"]


def test_product_learning_preserves_structured_business_identity(
    db_session: Session,
) -> None:
    def explorer(**kwargs):
        return _exploration_result(
            url="http://example.test/orders",
            title="Orders",
            final_url="http://example.test/orders",
            final_title="Orders",
        )

    service = LearningRunService(
        db_session,
        runtime_factory=_DummyRuntimeFactory(),
        explorer=explorer,
    )

    result = service.run(
        LearningRunRequest(
            url="http://example.test/orders",
            goal="Learn how to create purchase order named Alpha-1",
            fill_values={"order_name": "Alpha-1"},
            product_level=True,
            action_goal="Create purchase order",
            canonical_goal="create_purchase_order",
            action_aliases=["add purchase order", "Create purchase order"],
        )
    )

    assert result.status == "learned"
    assert result.action_label == "Create purchase orde"
    assert result.suggested_utterances == [
        "Create purchase order",
        "Help me create purchase order",
        "add purchase order",
    ]
    assert result.business_goal == "Create purchase order"
    assert result.canonical_goal == "create_purchase_order"
    assert result.action_aliases == ["add purchase order", "Create purchase order"]
    assert result.business_object == "purchase order"
    assert result.match_terms == [
        "Create purchase order",
        "create_purchase_order",
        "add purchase order",
        "purchase order",
    ]
    assert "Alpha-1" not in result.match_terms


def test_product_learning_uses_clean_canonical_when_action_goal_contains_slot_value(
    db_session: Session,
) -> None:
    def explorer(**kwargs):
        return _exploration_result(
            url="http://example.test/orders",
            title="Orders",
            final_url="http://example.test/orders",
            final_title="Orders",
        )

    service = LearningRunService(
        db_session,
        runtime_factory=_DummyRuntimeFactory(),
        explorer=explorer,
    )

    result = service.run(
        LearningRunRequest(
            url="http://example.test/orders",
            goal="Learn how to create purchase order named Alpha-1",
            fill_values={"order_name": "Alpha-1"},
            product_level=True,
            action_goal="Create purchase order Alpha-1",
            canonical_goal="create_purchase_order",
            action_aliases=["add purchase order"],
        )
    )

    assert result.status == "learned"
    assert result.action_label == "create purchase orde"
    assert result.suggested_utterances == [
        "create purchase order",
        "Help me create purchase order",
        "add purchase order",
    ]
    assert result.business_goal == "create purchase order"
    assert result.canonical_goal == "create_purchase_order"
    assert result.action_aliases == ["add purchase order"]
    assert result.business_object == "purchase order"
    assert result.match_terms == [
        "create purchase order",
        "create_purchase_order",
        "add purchase order",
        "purchase order",
    ]
    assert "Alpha-1" not in result.action_label
    assert all("Alpha-1" not in utterance for utterance in result.suggested_utterances)
    assert "Alpha-1" not in result.business_goal
    assert "Alpha-1" not in result.match_terms


def test_product_learning_excludes_verb_only_alias_from_suggested_utterances(
    db_session: Session,
) -> None:
    def explorer(**kwargs):
        return _exploration_result(
            url="http://example.test/orders",
            title="Orders",
            final_url="http://example.test/orders",
            final_title="Orders",
        )

    service = LearningRunService(
        db_session,
        runtime_factory=_DummyRuntimeFactory(),
        explorer=explorer,
    )

    result = service.run(
        LearningRunRequest(
            url="http://example.test/orders",
            goal="Learn how to create purchase order named Alpha-1",
            fill_values={"order_name": "Alpha-1"},
            product_level=True,
            action_goal="Create purchase order",
            canonical_goal="create_purchase_order",
            action_aliases=["create", "submit purchase order"],
        )
    )

    assert result.status == "learned"
    assert result.suggested_utterances == [
        "Create purchase order",
        "Help me create purchase order",
        "submit purchase order",
    ]
    assert "create" not in result.suggested_utterances
    assert all("Alpha-1" not in utterance for utterance in result.suggested_utterances)


def test_product_learning_saves_path_when_visible_text_confirms_user_value(
    db_session: Session,
) -> None:
    def explorer(**kwargs):
        return _exploration_result(
            url="http://example.test/records",
            title="记录",
            final_url="http://example.test/records",
            final_title="记录",
            verdict="failure",
            success=False,
            final_state={"body_text": "Alpha 已创建", "alert_texts": []},
            steps=[
                {
                    "step": 1,
                    "action_type": "fill",
                    "target_selector": "#record-name",
                    "value": "Alpha",
                },
                {
                    "step": 2,
                    "action_type": "click",
                    "target_selector": "button[type=submit]",
                },
            ],
            supervisor={
                "verdict": "failure",
                "should_save_path": False,
                "_supervisor_source": "fallback",
            },
        )

    service = LearningRunService(
        db_session,
        runtime_factory=_DummyRuntimeFactory(),
        explorer=explorer,
    )

    result = service.run(
        LearningRunRequest(
            url="http://example.test/records",
            goal="学习创建记录，名称叫 Alpha",
            fill_values={"entity_name": "Alpha"},
            product_level=True,
        )
    )

    assert result.status == "learned"
    assert result.learned_path_id is not None

    path = db_session.get(LearnedPath, result.learned_path_id)
    assert path is not None
    assert path.actions[0]["value_slot"] == "entity_name"


def test_product_learning_parameterizes_record_name_fill_action(
    db_session: Session,
) -> None:
    def explorer(**kwargs):
        return _exploration_result(
            url="http://example.test/records",
            title="Records",
            final_url="http://example.test/records",
            final_title="Records",
            steps=[
                {
                    "step": 1,
                    "action_type": "fill",
                    "target_selector": "[data-testid='record-name-input']",
                    "target_description": "记录名称",
                    "value": "Alpha Record",
                },
                {
                    "step": 2,
                    "action_type": "click",
                    "target_selector": "[data-testid='record-create-submit']",
                },
            ],
        )

    service = LearningRunService(
        db_session,
        runtime_factory=_DummyRuntimeFactory(),
        explorer=explorer,
    )

    result = service.run(
        LearningRunRequest(
            url="http://example.test/records",
            goal="学习创建记录，名称叫Alpha Record",
            fill_values={"record_name": "Alpha Record"},
            product_level=True,
        )
    )

    assert result.status == "learned"
    assert result.learned_path_id is not None
    path = db_session.get(LearnedPath, result.learned_path_id)
    assert path is not None
    assert path.actions[0]["value_slot"] == "record_name"
    assert path.actions[0]["value"] == "Alpha Record"


def test_product_learning_accepts_llm_supervisor_save_path_when_url_is_static(
    db_session: Session,
) -> None:
    def explorer(**kwargs):
        return _exploration_result(
            url="http://example.test/records",
            title="Records",
            final_url="http://example.test/records",
            final_title="Records",
            verdict="failure",
            success=False,
            supervisor={
                "verdict": "success",
                "should_save_path": True,
                "_supervisor_source": "llm",
                "_supervisor_partial_parse": False,
            },
            steps=[
                {
                    "step": 1,
                    "action_type": "fill",
                    "target_selector": "[data-testid='record-name-input']",
                    "target_description": "记录名称",
                    "value": "Alpha Record",
                },
                {
                    "step": 2,
                    "action_type": "click",
                    "target_selector": "[data-testid='record-create-submit']",
                },
            ],
        )

    service = LearningRunService(
        db_session,
        runtime_factory=_DummyRuntimeFactory(),
        explorer=explorer,
    )

    result = service.run(
        LearningRunRequest(
            url="http://example.test/records",
            goal="学习创建记录，名称叫Alpha Record",
            fill_values={"record_name": "Alpha Record"},
            product_level=True,
        )
    )

    assert result.status == "learned"
    assert result.learned_path_id is not None
    path = db_session.get(LearnedPath, result.learned_path_id)
    assert path is not None
    assert path.actions[0]["value_slot"] == "record_name"


def test_product_learning_parameterizes_matching_fill_values_without_route_gate(
    db_session: Session,
) -> None:
    def explorer(**kwargs):
        return _exploration_result(
            url="http://localhost:8080/login",
            title="登录入口",
            final_url="http://localhost:8080/account",
            final_title="账户首页",
            steps=[
                {
                    "step": 1,
                    "action_type": "fill",
                    "target_selector": "#username",
                    "target_description": "Username",
                    "value": "demo",
                },
                {
                    "step": 2,
                    "action_type": "fill",
                    "target_selector": "#password",
                    "target_description": "Password",
                    "value": "123456",
                },
            ],
        )

    service = LearningRunService(
        db_session,
        runtime_factory=_DummyRuntimeFactory(),
        explorer=explorer,
    )

    result = service.run(
        LearningRunRequest(
            url="http://localhost:8080/login",
            goal="学习登录",
            fill_values={"account_name": "demo", "password": "123456"},
            product_level=True,
        )
    )

    assert result.status == "learned"
    assert result.learned_path_id is not None
    path = db_session.get(LearnedPath, result.learned_path_id)
    assert path is not None
    assert path.actions[0]["value_slot"] == "account_name"
    assert path.actions[1]["value_slot"] == "password"


def test_product_learning_dedup_metadata_merge_adds_missing_value_slot(
    db_session: Session,
) -> None:
    def explorer(**kwargs):
        return _exploration_result(
            url="http://example.test/records",
            title="Records",
            final_url="http://example.test/records",
            final_title="Records",
            steps=[
                {
                    "step": 1,
                    "action_type": "fill",
                    "target_selector": "[data-testid='record-name-input']",
                    "target_description": "记录名称",
                    "value": "Alpha Record",
                }
            ],
        )

    service = LearningRunService(
        db_session,
        runtime_factory=_DummyRuntimeFactory(),
        explorer=explorer,
    )

    first = service.run(
        LearningRunRequest(
            url="http://example.test/records",
            goal="学习创建记录，名称叫Alpha Record",
            fill_values={},
            product_level=True,
        )
    )
    second = service.run(
        LearningRunRequest(
            url="http://example.test/records",
            goal="学习创建记录，名称叫Alpha Record",
            fill_values={"record_name": "Alpha Record"},
            product_level=True,
        )
    )

    assert first.learned_path_id == second.learned_path_id
    assert second.learned_path_id is not None
    path = db_session.get(LearnedPath, second.learned_path_id)
    assert path is not None
    assert path.hit_count == 2
    assert path.actions[0]["value_slot"] == "record_name"


def _filter_page_analysis() -> PageAnalysis:
    return PageAnalysis(
        url="http://example.test/users",
        title="Users",
        fillable=[
            DiscoveredElement(
                category="fillable",
                tag="input",
                element_type="search",
                id="keyword",
                name="keyword",
                placeholder="Keyword",
                selector="#keyword",
                label_text="Keyword",
                semantic_role="search",
                rect={"x": 10, "y": 20, "w": 200, "h": 32},
                reason="keyword filter",
            ),
            DiscoveredElement(
                category="fillable",
                tag="input",
                element_type="email",
                id="email",
                name="email",
                placeholder="Email",
                selector="#email",
                label_text="Email",
                semantic_role="email",
                rect={"x": 10, "y": 60, "w": 200, "h": 32},
                reason="email filter",
            ),
            DiscoveredElement(
                category="fillable",
                tag="input",
                element_type="text",
                id="role",
                name="role",
                placeholder="Role",
                selector="#role",
                label_text="Role",
                semantic_role="role",
                rect={"x": 10, "y": 100, "w": 200, "h": 32},
                reason="role filter",
            ),
        ],
        submit=[
            DiscoveredElement(
                category="submit",
                tag="button",
                element_type="submit",
                text="Search",
                selector="#btn-search",
                rect={"x": 10, "y": 160, "w": 100, "h": 32},
                reason="search button",
            )
        ],
        total_discovered=4,
        total_visible=4,
    )


def test_product_url_only_filter_learning_generates_capability_scenario_runs(
    db_session: Session,
) -> None:
    calls: list[dict[str, object]] = []
    analysis_runtimes: list[object] = []
    analysis = _filter_page_analysis()

    def explorer(**kwargs):
        calls.append(kwargs)
        scenario_name = kwargs.get("scenario_name")
        if scenario_name is None:
            return _exploration_result(
                url=analysis.url,
                title=analysis.title,
                verdict="failure",
                success=False,
                page_analysis=analysis,
                steps=[
                    {
                        "step": 1,
                        "action_type": "click",
                        "target_selector": "#btn-search",
                    }
                ],
                supervisor={
                    "verdict": "failure",
                    "should_save_path": False,
                    "_supervisor_source": "llm",
                },
            )
        fill_values = kwargs.get("fill_values") or {}
        steps = [
            {
                "step": index + 1,
                "action_type": "fill",
                "target_selector": f"#{key}",
                "value": value,
            }
            for index, (key, value) in enumerate(dict(fill_values).items())
        ]
        steps.append(
            {
                "step": len(steps) + 1,
                "action_type": "click",
                "target_selector": "#btn-search",
            }
        )
        return _exploration_result(
            url=analysis.url,
            title=analysis.title,
            verdict="success",
            success=True,
            page_analysis=analysis,
            steps=steps,
        )

    runtime_factory = _DummyRuntimeFactory()

    def page_analyzer(runtime):
        analysis_runtimes.append(runtime)
        return analysis

    service = LearningRunService(
        db_session,
        runtime_factory=runtime_factory,
        explorer=explorer,
        page_analyzer=page_analyzer,
    )

    result = service.run(
        LearningRunRequest(
            url=analysis.url,
            goal="学习这个页面上的操作",
            product_level=True,
        )
    )

    assert result.status == "learned"
    assert result.learning_outcome == "success"
    assert result.discovery_batch_id is not None
    assert result.learning_batch_id == result.discovery_batch_id
    assert result.learning_batch_status == LearningBatchStatus.COMPLETED
    assert result.learning_batch_summary["planned_count"] == 3
    assert result.learning_batch_summary["attempted_count"] == 3
    assert result.learning_batch_summary["browser_session_reuse"] is True
    assert result.learning_batch_summary["scenario_reset_count"] == 3
    assert len(result.learned_path_ids) == 3
    assert len(result.capability_summaries) == 3
    assert len([call for call in calls if call.get("scenario_name")]) == 3
    assert all(call.get("scenario_name") for call in calls)
    assert runtime_factory.call_count == 1
    assert runtime_factory.enter_count == 1
    assert runtime_factory.exit_count == 1
    assert all(call["runtime"] is runtime_factory.runtime for call in calls)
    assert analysis_runtimes == [runtime_factory.runtime] * 4
    assert runtime_factory.runtime.navigated_urls == [analysis.url] * 4

    scenario_runs = [
        run
        for run in db_session.scalars(select(ExplorationRun)).all()
        if (run.strategy_json or {}).get("kind") == "filter_capability_discovery"
    ]
    assert len(scenario_runs) == 3
    assert all(
        run.strategy_json["learning_batch_id"] == result.learning_batch_id
        for run in scenario_runs
    )
    assert {
        run.strategy_json["scenario_kind"]
        for run in scenario_runs
    } == {"single_filter"}

    learned_paths = list(db_session.scalars(select(LearnedPath)).all())
    assert len(learned_paths) == 3
    assert all(path.scenario != "product_level" for path in learned_paths)
    learned_capabilities = list(db_session.scalars(select(LearnedCapability)).all())
    assert len(learned_capabilities) == 3
    batch = db_session.get(LearningBatch, result.learning_batch_id)
    assert batch is not None
    assert batch.created_run_ids_json == result.run_ids
    assert batch.created_learned_path_ids_json == result.learned_path_ids
    assert set(batch.created_capability_ids_json) == {
        str(row.id) for row in learned_capabilities
    }


def test_product_url_only_filter_learning_stops_when_scenario_reset_fails(
    db_session: Session,
) -> None:
    analysis = _filter_page_analysis()

    class ResetFailureRuntimeFactory(_DummyRuntimeFactory):
        def __init__(self) -> None:
            super().__init__()
            self.navigate_count = 0

            def navigate(url: str) -> None:
                self.navigate_count += 1
                self.runtime.navigated_urls.append(url)
                if self.navigate_count > 1:
                    raise RuntimeError("reset #private failed")

            self.runtime.navigate = navigate

    runtime_factory = ResetFailureRuntimeFactory()
    explorer_calls: list[dict[str, object]] = []

    def explorer(**kwargs):
        explorer_calls.append(kwargs)
        return _exploration_result(page_analysis=analysis)

    service = LearningRunService(
        db_session,
        runtime_factory=runtime_factory,
        explorer=explorer,
        page_analyzer=lambda runtime: analysis,
    )

    result = service.run(
        LearningRunRequest(
            url=analysis.url,
            goal="学习这个页面上的操作",
            product_level=True,
        )
    )

    assert result.status == "failed"
    assert result.learning_outcome == "unverified"
    assert result.learning_batch_status == LearningBatchStatus.UNVERIFIED
    assert result.learning_batch_summary["terminal_reason"] == "scenario_reset_failed"
    assert result.learning_batch_summary["attempted_count"] == 0
    assert result.learning_batch_summary["unverified_count"] == 1
    assert result.learning_batch_summary["skipped_count"] == 2
    assert result.learning_batch_summary["scenario_reset_count"] == 1
    assert result.learning_batch_summary["browser_session_reuse"] is True
    assert "scenario_reset_warnings" in result.learning_batch_summary
    assert len(result.learning_batch_summary["warnings"]) == len(
        set(result.learning_batch_summary["warnings"])
    )
    assert len(result.learning_batch_summary["scenario_reset_warnings"]) == len(
        set(result.learning_batch_summary["scenario_reset_warnings"])
    )
    assert "[redacted-selector]" in str(result.learning_batch_summary)
    assert explorer_calls == []
    assert len(result.run_ids) == 1
    reset_run = db_session.get(ExplorationRun, result.run_ids[0])
    assert reset_run is not None
    assert reset_run.status == ExplorationRunStatus.FAILED
    assert (reset_run.strategy_json or {})["reset_failed"] is True
    assert (reset_run.result_snapshot_json or {})["attempt_ingest_evaluation"][
        "ingest_status"
    ] == "unverified"
    assert list(db_session.scalars(select(LearnedPath)).all()) == []
    assert runtime_factory.enter_count == 1
    assert runtime_factory.exit_count == 1


def test_product_url_only_filter_learning_rejects_reset_baseline_mismatch(
    db_session: Session,
) -> None:
    analysis = _filter_page_analysis()
    polluted_analysis = analysis.model_copy(update={"title": "Polluted"})
    analysis_calls = iter([analysis, polluted_analysis])
    explorer_calls: list[dict[str, object]] = []

    def explorer(**kwargs):
        explorer_calls.append(kwargs)
        return _exploration_result(page_analysis=analysis)

    service = LearningRunService(
        db_session,
        runtime_factory=_DummyRuntimeFactory(),
        explorer=explorer,
        page_analyzer=lambda runtime: next(analysis_calls),
    )

    result = service.run(
        LearningRunRequest(
            url=analysis.url,
            goal="学习这个页面上的操作",
            product_level=True,
        )
    )

    assert result.status == "failed"
    assert result.learning_outcome == "unverified"
    assert result.learning_batch_status == LearningBatchStatus.UNVERIFIED
    assert result.learning_batch_summary["terminal_reason"] == "scenario_reset_failed"
    assert result.learning_batch_summary["unverified_count"] == 1
    assert result.learning_batch_summary["skipped_count"] == 2
    assert "scenario reset baseline title changed" in str(result.learning_batch_summary)
    assert explorer_calls == []
    assert len(result.run_ids) == 1
    reset_run = db_session.get(ExplorationRun, result.run_ids[0])
    assert reset_run is not None
    assert (reset_run.strategy_json or {})["reset_failed"] is True
    assert list(db_session.scalars(select(LearnedPath)).all()) == []


def test_product_url_only_filter_learning_rejects_dirty_control_state_reset(
    db_session: Session,
) -> None:
    analysis = _filter_page_analysis()
    runtime_factory = _DummyRuntimeFactory()
    clean_state = {
        "controls": [
            {
                "index": 0,
                "tag": "input",
                "type": "search",
                "role": "",
                "checked": False,
                "selectedIndex": None,
                "optionState": [],
                "valueLength": 0,
                "valueHash": "empty",
                "disabled": False,
                "readonly": False,
            }
        ],
        "result_regions": {
            "tableRows": 0,
            "roleRows": 0,
            "listItems": 0,
            "options": 0,
            "alerts": 0,
            "dialogs": 0,
            "modals": 0,
        },
    }
    dirty_state = {
        **clean_state,
        "controls": [
            {
                **clean_state["controls"][0],
                "valueLength": 6,
                "valueHash": "cached-hash",
            }
        ],
    }
    states = iter([clean_state, dirty_state])
    runtime_factory.runtime.page = SimpleNamespace(evaluate=lambda _script: next(states))
    explorer_calls: list[dict[str, object]] = []

    def explorer(**kwargs):
        explorer_calls.append(kwargs)
        return _exploration_result(page_analysis=analysis)

    service = LearningRunService(
        db_session,
        runtime_factory=runtime_factory,
        explorer=explorer,
        page_analyzer=lambda runtime: analysis,
    )

    result = service.run(
        LearningRunRequest(
            url=analysis.url,
            goal="学习这个页面上的操作",
            product_level=True,
        )
    )

    assert result.status == "failed"
    assert result.learning_batch_status == LearningBatchStatus.UNVERIFIED
    assert result.learning_batch_summary["terminal_reason"] == "scenario_reset_failed"
    assert "scenario reset baseline control state changed" in str(
        result.learning_batch_summary
    )
    assert "scenario reset baseline page state changed" in str(
        result.learning_batch_summary
    )
    assert explorer_calls == []
    assert len(result.run_ids) == 1
    reset_run = db_session.get(ExplorationRun, result.run_ids[0])
    assert reset_run is not None
    assert (reset_run.strategy_json or {})["reset_failed"] is True
    assert list(db_session.scalars(select(LearnedPath)).all()) == []


def test_product_url_only_filter_learning_rejects_dirty_result_region_content_reset(
    db_session: Session,
) -> None:
    analysis = _filter_page_analysis()
    runtime_factory = _DummyRuntimeFactory()
    controls = []
    clean_result_regions = {
        "tableRows": 2,
        "roleRows": 0,
        "listItems": 0,
        "options": 0,
        "alerts": 0,
        "dialogs": 0,
        "modals": 0,
        "tableFingerprints": [
            {
                "tag": "table",
                "role": "",
                "childCount": 1,
                "textLength": 24,
                "textHash": "seed-table",
                "structureHash": "same-structure",
                "rows": [
                    {
                        "tag": "tr",
                        "role": "",
                        "childCount": 2,
                        "textLength": 12,
                        "textHash": "seed-row-1",
                        "cells": [
                            {
                                "tag": "td",
                                "role": "",
                                "childCount": 0,
                                "textLength": 6,
                                "textHash": "seed-cell-a",
                            }
                        ],
                    }
                ],
            }
        ],
        "rowFingerprints": [],
        "listFingerprints": [],
        "regionFingerprints": [],
    }
    dirty_result_regions = {
        **clean_result_regions,
        "tableFingerprints": [
            {
                **clean_result_regions["tableFingerprints"][0],
                "textHash": "dirty-table",
                "rows": [
                    {
                        **clean_result_regions["tableFingerprints"][0]["rows"][0],
                        "textHash": "dirty-row-1",
                        "cells": [
                            {
                                **clean_result_regions["tableFingerprints"][0]["rows"][0][
                                    "cells"
                                ][0],
                                "textHash": "dirty-cell-a",
                            }
                        ],
                    }
                ],
            }
        ],
    }
    states = iter(
        [
            {"controls": controls, "result_regions": clean_result_regions},
            {"controls": controls, "result_regions": dirty_result_regions},
        ]
    )
    runtime_factory.runtime.page = SimpleNamespace(evaluate=lambda _script: next(states))
    explorer_calls: list[dict[str, object]] = []

    def explorer(**kwargs):
        explorer_calls.append(kwargs)
        return _exploration_result(page_analysis=analysis)

    service = LearningRunService(
        db_session,
        runtime_factory=runtime_factory,
        explorer=explorer,
        page_analyzer=lambda runtime: analysis,
    )

    result = service.run(
        LearningRunRequest(
            url=analysis.url,
            goal="学习这个页面上的操作",
            product_level=True,
        )
    )

    assert result.status == "failed"
    assert result.learning_outcome == "unverified"
    assert result.learning_batch_status == LearningBatchStatus.UNVERIFIED
    assert result.learning_batch_summary["terminal_reason"] == "scenario_reset_failed"
    assert result.learning_batch_summary["scenario_reset_count"] == 1
    assert "scenario reset baseline result region changed" in str(
        result.learning_batch_summary
    )
    assert "scenario reset baseline page state changed" in str(
        result.learning_batch_summary
    )
    assert explorer_calls == []
    assert len(result.run_ids) == 1
    reset_run = db_session.get(ExplorationRun, result.run_ids[0])
    assert reset_run is not None
    assert reset_run.status == ExplorationRunStatus.FAILED
    assert (reset_run.strategy_json or {})["reset_failed"] is True
    snapshot = reset_run.result_snapshot_json or {}
    assert snapshot["reset_result"]["baseline_summary"]["result_region_summary"][
        "tableRows"
    ] == 2
    assert snapshot["reset_result"]["baseline_summary"]["result_region_summary"][
        "content_structure_fingerprint"
    ]
    assert "dirty-cell-a" not in str(snapshot)
    assert list(db_session.scalars(select(LearnedPath)).all()) == []
    assert list(db_session.scalars(select(LearnedCapability)).all()) == []
    assert runtime_factory.enter_count == 1
    assert runtime_factory.exit_count == 1


def test_product_url_only_filter_learning_reports_failed_when_reset_fails_after_asset(
    db_session: Session,
) -> None:
    analysis = _filter_page_analysis()

    class ResetFailureAfterFirstScenarioFactory(_DummyRuntimeFactory):
        def __init__(self) -> None:
            super().__init__()
            self.navigate_count = 0

            def navigate(url: str) -> None:
                self.navigate_count += 1
                self.runtime.navigated_urls.append(url)
                if self.navigate_count > 2:
                    raise RuntimeError("late reset failed")

            self.runtime.navigate = navigate

    runtime_factory = ResetFailureAfterFirstScenarioFactory()

    def explorer(**kwargs):
        fill_values = kwargs.get("fill_values") or {}
        steps = [
            {
                "step": 1,
                "action_type": "fill",
                "target_selector": f"#{key}",
                "value": value,
            }
            for key, value in dict(fill_values).items()
        ]
        steps.append(
            {
                "step": len(steps) + 1,
                "action_type": "click",
                "target_selector": "#btn-search",
            }
        )
        return _exploration_result(
            url=analysis.url,
            title=analysis.title,
            verdict="success",
            success=True,
            page_analysis=analysis,
            steps=steps,
        )

    service = LearningRunService(
        db_session,
        runtime_factory=runtime_factory,
        explorer=explorer,
        page_analyzer=lambda runtime: analysis,
    )

    result = service.run(
        LearningRunRequest(
            url=analysis.url,
            goal="学习这个页面上的操作",
            product_level=True,
        )
    )

    assert result.status == "failed"
    assert result.learning_outcome == "partial_success"
    assert result.learning_batch_status == LearningBatchStatus.PARTIAL_SUCCESS
    assert result.learning_batch_summary["terminal_reason"] == "scenario_reset_failed"
    assert result.learning_batch_summary["attempted_count"] == 1
    assert result.learning_batch_summary["unverified_count"] == 1
    assert result.learning_batch_summary["skipped_count"] == 1
    assert len(result.learned_path_ids) == 1
    assert len(result.run_ids) == 2
    reset_run = db_session.get(ExplorationRun, result.run_ids[-1])
    assert reset_run is not None
    assert (reset_run.strategy_json or {})["reset_failed"] is True
    assert result.error == "Scenario reset failed before remaining capabilities could be verified."
    assert runtime_factory.enter_count == 1
    assert runtime_factory.exit_count == 1


def test_product_url_only_filter_learning_does_not_ingest_click_only_scenarios(
    db_session: Session,
) -> None:
    calls: list[dict[str, object]] = []
    analysis = _filter_page_analysis()

    def explorer(**kwargs):
        calls.append(kwargs)
        return _exploration_result(
            url=analysis.url,
            title=analysis.title,
            verdict="success",
            success=True,
            page_analysis=analysis,
            steps=[
                {
                    "step": 1,
                    "action_type": "click",
                    "target_selector": "#btn-search",
                }
            ],
        )

    service = LearningRunService(
        db_session,
        runtime_factory=_DummyRuntimeFactory(),
        explorer=explorer,
        page_analyzer=lambda runtime: analysis,
    )

    result = service.run(
        LearningRunRequest(
            url=analysis.url,
            goal="学习这个页面上的操作",
            product_level=True,
        )
    )

    assert result.status == "failed"
    assert result.learning_outcome == "failed"
    assert result.learning_batch_id is not None
    assert result.learning_batch_status == LearningBatchStatus.FAILED
    assert result.learning_batch_summary["planned_count"] == 3
    assert result.learning_batch_summary["attempted_count"] == 1
    assert result.learning_batch_summary["failed_count"] == 1
    assert result.learning_batch_summary["skipped_count"] == 2
    assert result.learning_batch_summary["terminal_reason"] == "bounded_policy_stop"
    assert result.learned_path_ids == []
    assert result.run_ids
    assert len([call for call in calls if call.get("scenario_name")]) == 1
    assert len(result.failed_scenario_summaries) == 1
    assert list(db_session.scalars(select(LearnedPath)).all()) == []


def test_product_url_only_filter_learning_stops_after_consecutive_no_new_capability(
    db_session: Session,
) -> None:
    calls: list[dict[str, object]] = []
    analysis = _filter_page_analysis()

    def explorer(**kwargs):
        calls.append(kwargs)
        return _exploration_result(
            url=analysis.url,
            title=analysis.title,
            verdict="uncertain",
            success=False,
            page_analysis=analysis,
            steps=[],
        )

    service = LearningRunService(
        db_session,
        runtime_factory=_DummyRuntimeFactory(),
        explorer=explorer,
        page_analyzer=lambda runtime: analysis,
    )

    result = service.run(
        LearningRunRequest(
            url=analysis.url,
            goal="学习这个页面上的操作",
            product_level=True,
            bounded_policy=BoundedLearningPolicy(
                max_failures_per_adapter=10,
                max_consecutive_no_new_capability=2,
            ),
        )
    )

    assert result.status == "failed"
    assert result.learning_outcome == "unverified"
    assert result.learning_batch_status == LearningBatchStatus.UNVERIFIED
    assert result.learning_batch_summary["planned_count"] == 3
    assert result.learning_batch_summary["attempted_count"] == 2
    assert result.learning_batch_summary["unverified_count"] == 2
    assert result.learning_batch_summary["skipped_count"] == 1
    assert result.learning_batch_summary["terminal_reason"] == "bounded_policy_stop"
    assert len([call for call in calls if call.get("scenario_name")]) == 2
    assert len(result.unverified_scenario_summaries) == 2


def test_product_url_only_filter_learning_records_timeout_after_scenario(
    db_session: Session,
) -> None:
    ticks = iter([0.0, 0.0, 0.0, 10.0])
    analysis = _filter_page_analysis()

    def explorer(**kwargs):
        fill_values = kwargs.get("fill_values") or {}
        steps = [
            {
                "step": 1,
                "action_type": "fill",
                "target_selector": "#keyword",
                "value": next(iter(dict(fill_values).values()), "keyword"),
            },
            {"step": 2, "action_type": "click", "target_selector": "#btn-search"},
        ]
        return _exploration_result(
            url=analysis.url,
            title=analysis.title,
            verdict="success",
            success=True,
            page_analysis=analysis,
            steps=steps,
        )

    service = LearningRunService(
        db_session,
        runtime_factory=_DummyRuntimeFactory(),
        explorer=explorer,
        page_analyzer=lambda runtime: analysis,
        clock=lambda: next(ticks, 10.0),
    )

    result = service.run(
        LearningRunRequest(
            url=analysis.url,
            goal="学习这个页面上的操作",
            product_level=True,
            bounded_policy=BoundedLearningPolicy(max_scenario_count=1, max_wall_clock_seconds=5),
        )
    )

    assert result.status == "learned"
    assert result.learning_batch_status == LearningBatchStatus.PARTIAL_SUCCESS
    assert result.learning_batch_summary["timeout_occurred"] is True
    assert result.learning_batch_summary["terminal_reason"] == "timed_out"
    assert result.learning_batch_summary["attempted_count"] == 1


def test_product_url_only_filter_learning_rejected_capability_ingest_is_failed(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analysis = _filter_page_analysis()
    scenario = CapabilityScenario(
        scenario_id="scenario-unsupported-binding",
        capability_id="cap-unsupported",
        scenario_kind="single_filter",
        human_label="Unsupported filter",
        input_bindings=[
            {
                "capability_id": "cap-unsupported",
                "adapter_type": "unsupported",
                "binding_key": "keyword",
                "value": "keyword",
                "selector": "#keyword",
                "label": "Keyword",
            }
        ],
        expected_observation_target={"kind": "generic_result_change"},
        discovery_batch_id="batch-before-service",
        source_capability_ids=["cap-unsupported"],
        fill_values={"keyword": "keyword"},
    )
    monkeypatch.setattr(
        "app.services.learning.learning_run_service.generate_filter_scenarios",
        lambda inventory, *, discovery_batch_id: [scenario],
    )

    def explorer(**kwargs):
        return _exploration_result(
            url=analysis.url,
            title=analysis.title,
            verdict="success",
            success=True,
            page_analysis=analysis,
            steps=[
                {
                    "step": 1,
                    "action_type": "fill",
                    "target_selector": "#keyword",
                    "value": "keyword",
                },
                {"step": 2, "action_type": "click", "target_selector": "#btn-search"},
            ],
        )

    service = LearningRunService(
        db_session,
        runtime_factory=_DummyRuntimeFactory(),
        explorer=explorer,
        page_analyzer=lambda runtime: analysis,
    )

    result = service.run(
        LearningRunRequest(
            url=analysis.url,
            goal="学习这个页面上的操作",
            product_level=True,
        )
    )

    assert result.status == "failed"
    assert result.learning_batch_status == LearningBatchStatus.FAILED
    assert result.learned_path_ids == []
    assert result.capability_summaries == []
    assert result.learning_batch_summary["failed_count"] == 1
    assert result.learning_batch_summary["failed_scenarios"][0]["warnings"]
    batch = db_session.get(LearningBatch, result.learning_batch_id)
    assert batch is not None
    assert batch.created_capability_ids_json == []
    assert batch.created_learned_path_ids_json


def test_product_url_only_filter_learning_closes_batch_when_seed_analysis_fails(
    db_session: Session,
) -> None:
    runtime_factory = _DummyRuntimeFactory()
    service = LearningRunService(
        db_session,
        runtime_factory=runtime_factory,
        explorer=lambda **kwargs: _exploration_result(),
        page_analyzer=lambda runtime: (_ for _ in ()).throw(
            RuntimeError("seed #private failed")
        ),
    )

    result = service.run(
        LearningRunRequest(
            url="http://example.test/customers",
            goal="学习这个页面上的操作",
            product_level=True,
        )
    )

    assert result.status == "failed"
    assert result.learning_batch_id is not None
    assert result.learning_batch_status == LearningBatchStatus.FAILED
    assert result.learning_batch_summary["terminal_reason"] == "exception_seed_analysis"
    assert result.learning_batch_summary["failed_count"] == 1
    assert result.learning_batch_summary["browser_session_reuse"] is True
    assert result.learning_batch_summary["scenario_reset_count"] == 0
    assert "[redacted-selector]" in result.error
    batch = db_session.get(LearningBatch, result.learning_batch_id)
    assert batch is not None
    assert batch.status == LearningBatchStatus.FAILED
    assert runtime_factory.enter_count == 1
    assert runtime_factory.exit_count == 1


def test_product_url_only_filter_learning_reports_browser_session_setup_failure(
    db_session: Session,
) -> None:
    class RuntimeSetupFailureFactory(_DummyRuntimeFactory):
        def __enter__(self):
            self.enter_count += 1
            raise RuntimeError("browser setup failed")

    runtime_factory = RuntimeSetupFailureFactory()
    service = LearningRunService(
        db_session,
        runtime_factory=runtime_factory,
        explorer=lambda **kwargs: _exploration_result(),
        page_analyzer=lambda runtime: _filter_page_analysis(),
    )

    result = service.run(
        LearningRunRequest(
            url="https://example.invalid/entry",
            goal="学习这个页面上的操作",
            product_level=True,
        )
    )

    assert result.status == "failed"
    assert result.learning_batch_status == LearningBatchStatus.FAILED
    assert result.learning_batch_summary["terminal_reason"] == "exception_browser_session"
    assert result.learning_batch_summary["browser_session_reuse"] is False
    assert result.learning_batch_summary["browser_session_setup_failed"] is True
    assert result.learning_batch_summary["scenario_reset_count"] == 0
    assert runtime_factory.call_count == 1
    assert runtime_factory.enter_count == 1
    assert runtime_factory.exit_count == 0


def test_product_url_only_filter_learning_closes_batch_when_scenario_explorer_fails(
    db_session: Session,
) -> None:
    analysis = _filter_page_analysis()

    def explorer(**kwargs):
        raise RuntimeError("scenario failed")

    runtime_factory = _DummyRuntimeFactory()
    service = LearningRunService(
        db_session,
        runtime_factory=runtime_factory,
        explorer=explorer,
        page_analyzer=lambda runtime: analysis,
    )

    result = service.run(
        LearningRunRequest(
            url=analysis.url,
            goal="学习这个页面上的操作",
            product_level=True,
        )
    )

    assert result.status == "failed"
    assert result.learning_batch_id is not None
    assert result.learning_batch_status == LearningBatchStatus.FAILED
    assert result.learning_batch_summary["terminal_reason"] == "exception_scenario_execution"
    assert result.learning_batch_summary["planned_count"] == 3
    assert result.learning_batch_summary["attempted_count"] == 1
    assert result.learning_batch_summary["failed_count"] == 1
    assert result.learning_batch_summary["failed_scenarios"][0]["scenario_id"]
    assert result.learning_batch_summary["browser_session_reuse"] is True
    assert result.learning_batch_summary["scenario_reset_count"] == 1
    assert runtime_factory.enter_count == 1
    assert runtime_factory.exit_count == 1


def test_product_url_only_filter_learning_closes_batch_when_persist_fails(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    analysis = _filter_page_analysis()

    def explorer(**kwargs):
        fill_values = kwargs.get("fill_values") or {}
        return _exploration_result(
            url=analysis.url,
            title=analysis.title,
            verdict="success",
            success=True,
            page_analysis=analysis,
            steps=[
                {
                    "step": 1,
                    "action_type": "fill",
                    "target_selector": "#keyword",
                    "value": next(iter(dict(fill_values).values()), "keyword"),
                },
                {"step": 2, "action_type": "click", "target_selector": "#btn-search"},
            ],
        )

    runtime_factory = _DummyRuntimeFactory()
    service = LearningRunService(
        db_session,
        runtime_factory=runtime_factory,
        explorer=explorer,
        page_analyzer=lambda runtime: analysis,
    )

    def fail_persist(**kwargs):
        raise RuntimeError("persist failed")

    monkeypatch.setattr(service, "_persist_finished_run", fail_persist)

    result = service.run(
        LearningRunRequest(
            url=analysis.url,
            goal="学习这个页面上的操作",
            product_level=True,
        )
    )

    assert result.status == "failed"
    assert result.learning_batch_id is not None
    assert result.learning_batch_status == LearningBatchStatus.FAILED
    assert result.learning_batch_summary["terminal_reason"] == "exception_scenario_execution"
    assert result.learning_batch_summary["planned_count"] == 3
    assert result.learning_batch_summary["attempted_count"] == 1
    assert result.learning_batch_summary["failed_count"] == 1
    assert result.learning_batch_summary["browser_session_reuse"] is True
    assert result.learning_batch_summary["scenario_reset_count"] == 1
    assert runtime_factory.enter_count == 1
    assert runtime_factory.exit_count == 1


def test_binding_evidence_counts_duplicate_expected_values() -> None:
    final_data = {
        "steps": [
            {
                "step": 1,
                "action_type": "set_value",
                "target_selector": "#registered-from",
                "value": "2026-01-01",
            }
        ]
    }

    assert not _expected_bindings_have_action_evidence(
        final_data,
        fill_values={
            "registered_from": "2026-01-01",
            "registered_to": "2026-01-01",
        },
        toggle_values={},
    )

    final_data["steps"].append(
        {
            "step": 2,
            "action_type": "set_value",
            "target_selector": "#registered-to",
            "value": "2026-01-01",
        }
    )

    assert _expected_bindings_have_action_evidence(
        final_data,
        fill_values={
            "registered_from": "2026-01-01",
            "registered_to": "2026-01-01",
        },
        toggle_values={},
    )
