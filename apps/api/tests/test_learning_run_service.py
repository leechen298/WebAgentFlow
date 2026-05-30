"""Tests for M11.3 learning run service."""

from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.models.learned_path import LearnedPath
from app.schemas.page_analysis import AutonomousExplorationResult, PageAnalysis
from app.services.learning.learning_run_service import LearningRunRequest, LearningRunService


class _DummyRuntimeFactory:
    def __call__(self, config):
        return self

    def __enter__(self):
        return SimpleNamespace(page=None)

    def __exit__(self, exc_type, exc, tb):
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
) -> AutonomousExplorationResult:
    return AutonomousExplorationResult(
        page_analysis=PageAnalysis(url=url, title=title),
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
