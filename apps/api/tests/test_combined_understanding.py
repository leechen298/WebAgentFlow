"""Tests for combined understanding service (Phase 6E).

Structural field tests are pure rule-based. Description field tests
mock the lightweight LLM call used for locale-aware generation.
"""

from __future__ import annotations

from unittest.mock import patch

from app.schemas.combined_understanding import AgentPageUnderstanding
from app.schemas.llm import LlmResponse, LlmUsage
from app.schemas.page_understanding import ActionInfo, PageUnderstanding, RegionInfo
from app.schemas.step_understanding import (
    CategorizedStep,
    KeyStepInfo,
    NoChangeStepInfo,
    StepUnderstanding,
)
from app.services.combined_understanding import build_agent_page_understanding


def _mock_description_response(request=None):
    """Return a mock LLM response for description generation."""
    return LlmResponse(
        ok=True,
        text="",
        parsed={
            "page_description": "这是一个表单类型的页面，用于创建新的营销活动。页面包含基础信息表单和高级配置面板。主要操作包括保存、取消和展开高级配置。",
            "operation_description": "用户先填写表单，再展开高级配置，最后保存。保存步骤在当前观察窗口内没有出现明显页面变化，可能在等待异步响应。",
        },
        usage=LlmUsage(prompt_tokens=100, completion_tokens=80, total_tokens=180),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_page_understanding() -> PageUnderstanding:
    return PageUnderstanding(
        page_kind="form",
        page_goal="创建新的营销活动",
        primary_regions=[
            RegionInfo(name="基础信息表单", role="填写活动基础信息"),
            RegionInfo(name="高级配置面板", role="配置高级参数"),
        ],
        primary_actions=[
            ActionInfo(name="保存", action_type="submit", description="提交活动创建表单"),
            ActionInfo(name="取消", action_type="navigate", description="返回列表页"),
            ActionInfo(name="展开高级配置", action_type="expand", description="展开隐藏配置区"),
        ],
        key_entities=["活动", "奖品"],
        confidence_notes=["页面结构较典型"],
    )


def _make_step_understanding() -> StepUnderstanding:
    return StepUnderstanding(
        common_step_patterns=[
            "用户先填写表单，再展开高级配置，最后保存。",
        ],
        likely_key_steps=[
            KeyStepInfo(step_index=2, event_type="input", target='<input> "活动名称"',
                        reason="填写活动名称是核心操作"),
            KeyStepInfo(step_index=6, event_type="click", target='<button> "保存"',
                        reason="最终提交动作"),
        ],
        likely_expand_steps=[
            CategorizedStep(step_index=5, event_type="click",
                            target='<button> "展开高级配置"', description="展开隐藏配置区"),
        ],
        likely_submit_steps=[
            CategorizedStep(step_index=6, event_type="click",
                            target='<button> "保存"', description="提交表单"),
        ],
        likely_no_change_steps=[
            NoChangeStepInfo(step_index=0, event_type="navigate",
                             target="https://example.com/create", likely_reason="navigation"),
            NoChangeStepInfo(step_index=6, event_type="click",
                             target='<button> "保存"', likely_reason="async_pending"),
        ],
        observed_change_patterns=[
            "输入操作导致属性变化，展开操作导致 childList 变化。",
        ],
        confidence_notes=["保存步骤可能需要等待异步响应"],
    )


# ---------------------------------------------------------------------------
# Core synthesis tests
# ---------------------------------------------------------------------------

@patch("app.services.combined_understanding.generate_structured", side_effect=_mock_description_response)
class TestBuildAgentPageUnderstanding:
    def test_page_identity_carried_over(self, _mock):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        assert result.page_kind == "form"
        assert result.page_goal == "创建新的营销活动"

    def test_key_entities_carried_over(self, _mock):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        assert result.key_entities == ["活动", "奖品"]

    def test_regions_enriched_with_step_activity(self, _mock):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        regions = result.primary_regions
        assert len(regions) == 2
        # "高级配置面板" should be marked as having step activity
        # because step target "展开高级配置" contains "高级配置"
        config_region = next(r for r in regions if "高级配置" in r["name"])
        assert config_region.get("step_activity") is True

    def test_actions_enriched_with_observed_flag(self, _mock):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        actions = result.primary_actions
        assert len(actions) == 3
        save_action = next(a for a in actions if a["name"] == "保存")
        assert save_action.get("observed_in_steps") is True
        expand_action = next(a for a in actions if "展开" in a["name"])
        assert expand_action.get("observed_in_steps") is True

    def test_key_steps_distilled_with_roles(self, _mock):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        key_steps = result.key_steps
        # Submit (6), expand (5), key input (2) — sorted by index
        assert len(key_steps) == 3
        assert key_steps[0].step_index == 2
        assert key_steps[0].role == "key_input"
        assert key_steps[1].step_index == 5
        assert key_steps[1].role == "expand"
        assert key_steps[2].step_index == 6
        assert key_steps[2].role == "submit"

    def test_interaction_patterns_merged(self, _mock):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        patterns = result.interaction_patterns
        assert len(patterns) == 2  # 1 common + 1 change pattern
        assert any("填写表单" in p for p in patterns)
        assert any("属性变化" in p for p in patterns)

    def test_execution_notes_from_no_change(self, _mock):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        notes = result.execution_notes
        # Navigation no-change is skipped; only async_pending note remains
        assert len(notes) == 1
        assert "async_pending" in notes[0].note
        assert notes[0].source == "no_change_step"

    def test_confidence_notes_merged_and_deduped(self, _mock):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        assert len(result.confidence_notes) == 2
        assert "页面结构较典型" in result.confidence_notes
        assert "保存步骤可能需要等待异步响应" in result.confidence_notes

    def test_page_description_from_llm(self, _mock):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        assert result.page_description != ""
        assert "表单" in result.page_description
        assert "营销活动" in result.page_description

    def test_operation_description_from_llm(self, _mock):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        assert result.operation_description != ""
        assert "填写" in result.operation_description or "保存" in result.operation_description

    def test_output_is_serializable(self, _mock):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        data = result.model_dump()
        assert isinstance(data, dict)
        assert data["page_kind"] == "form"
        assert isinstance(data["key_steps"], list)
        assert isinstance(data["execution_notes"], list)
        assert isinstance(data["page_description"], str)
        assert isinstance(data["operation_description"], str)

    def test_locale_passed_to_llm(self, mock_gen):
        build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
            locale="zh",
        )

        mock_gen.assert_called_once()
        request = mock_gen.call_args[0][0]
        assert "Chinese" in request.messages[0].content


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

@patch("app.services.combined_understanding.generate_structured", side_effect=_mock_description_response)
class TestEdgeCases:
    def test_empty_page_understanding(self, mock_gen):
        """When page is empty but steps exist, LLM is called for step descriptions."""
        # Override mock to return step-only descriptions
        mock_gen.side_effect = lambda req: LlmResponse(
            ok=True, text="", parsed={
                "page_description": "",
                "operation_description": "用户点击了几个按钮。",
            }, usage=LlmUsage(),
        )
        result = build_agent_page_understanding(
            PageUnderstanding(), _make_step_understanding(),
        )

        assert result.page_kind == "unknown"
        assert result.page_goal == ""
        assert result.primary_regions == []
        assert result.primary_actions == []
        assert len(result.key_steps) >= 1

    def test_empty_step_understanding(self, mock_gen):
        mock_gen.side_effect = lambda req: LlmResponse(
            ok=True, text="", parsed={
                "page_description": "这是一个表单页面。",
                "operation_description": "",
            }, usage=LlmUsage(),
        )
        result = build_agent_page_understanding(
            _make_page_understanding(), StepUnderstanding(),
        )

        assert result.page_kind == "form"
        assert result.page_goal == "创建新的营销活动"
        assert len(result.primary_regions) == 2
        assert all("step_activity" not in r for r in result.primary_regions)
        assert result.key_steps == []
        assert result.interaction_patterns == []
        assert result.execution_notes == []

    def test_both_empty(self, _mock):
        """When both are empty, no LLM call is made, descriptions are empty."""
        result = build_agent_page_understanding(
            PageUnderstanding(), StepUnderstanding(),
        )

        assert result.page_kind == "unknown"
        assert result.key_steps == []
        assert result.primary_regions == []
        assert result.interaction_patterns == []
        assert result.execution_notes == []
        assert result.confidence_notes == []
        assert result.page_description == ""
        assert result.operation_description == ""
        # LLM should NOT be called when both are empty
        _mock.assert_not_called()

    def test_no_execution_planning_in_output(self, _mock):
        """Verify the output doesn't contain execution-planner fields."""
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        data = result.model_dump()
        assert "next_action" not in data
        assert "action_plan" not in data
        assert "wait_condition" not in data
        assert "retry_strategy" not in data

    def test_all_no_change_steps_operation_description(self, mock_gen):
        """When all steps are no-change, LLM still generates description."""
        mock_gen.side_effect = lambda req: LlmResponse(
            ok=True, text="", parsed={
                "page_description": "",
                "operation_description": "用户点击了两个按钮，均未产生可观察变化。",
            }, usage=LlmUsage(),
        )
        steps = StepUnderstanding(
            common_step_patterns=["所有操作均未产生可观察变化。"],
            likely_no_change_steps=[
                NoChangeStepInfo(step_index=0, event_type="click",
                                 target='<button> "X"', likely_reason="unknown"),
                NoChangeStepInfo(step_index=1, event_type="click",
                                 target='<button> "Y"', likely_reason="genuine_noop"),
            ],
        )
        result = build_agent_page_understanding(PageUnderstanding(), steps)

        assert result.operation_description != ""
        assert "失败" not in result.operation_description
        assert "错误" not in result.operation_description

    def test_description_llm_failure_fallback(self, mock_gen):
        """When description LLM call fails, descriptions fall back to empty."""
        mock_gen.side_effect = lambda req: LlmResponse(
            ok=False, usage=LlmUsage(),
        )
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        # Structural fields still work
        assert result.page_kind == "form"
        assert len(result.key_steps) == 3
        # Descriptions fall back to empty
        assert result.page_description == ""
        assert result.operation_description == ""

    def test_interaction_patterns_capped_at_5(self, _mock):
        steps = StepUnderstanding(
            common_step_patterns=["p1", "p2", "p3"],
            observed_change_patterns=["c1", "c2", "c3"],
        )

        result = build_agent_page_understanding(PageUnderstanding(), steps)

        assert len(result.interaction_patterns) <= 5

    def test_duplicate_step_index_deduped(self, _mock):
        """Step 6 appears in both key_steps and submit_steps — should appear once."""
        steps = StepUnderstanding(
            likely_key_steps=[
                KeyStepInfo(step_index=6, event_type="click", target="save", reason="submit"),
            ],
            likely_submit_steps=[
                CategorizedStep(step_index=6, event_type="click", target="save", description="save form"),
            ],
        )

        result = build_agent_page_understanding(PageUnderstanding(), steps)

        indices = [s.step_index for s in result.key_steps]
        assert indices.count(6) == 1
        assert result.key_steps[0].role == "submit"
