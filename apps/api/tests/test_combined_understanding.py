"""Tests for combined understanding service (Phase 6E).

Pure rule-based synthesis tests — no LLM calls.
"""

from __future__ import annotations

from app.schemas.combined_understanding import AgentPageUnderstanding
from app.schemas.page_understanding import ActionInfo, PageUnderstanding, RegionInfo
from app.schemas.step_understanding import (
    CategorizedStep,
    KeyStepInfo,
    NoChangeStepInfo,
    StepUnderstanding,
)
from app.services.combined_understanding import build_agent_page_understanding


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

class TestBuildAgentPageUnderstanding:
    def test_page_identity_carried_over(self):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        assert result.page_kind == "form"
        assert result.page_goal == "创建新的营销活动"

    def test_key_entities_carried_over(self):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        assert result.key_entities == ["活动", "奖品"]

    def test_regions_enriched_with_step_activity(self):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        regions = result.primary_regions
        assert len(regions) == 2
        # "高级配置面板" should be marked as having step activity
        # because step target "展开高级配置" contains "高级配置"
        config_region = next(r for r in regions if "高级配置" in r["name"])
        assert config_region.get("step_activity") is True

    def test_actions_enriched_with_observed_flag(self):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        actions = result.primary_actions
        assert len(actions) == 3
        save_action = next(a for a in actions if a["name"] == "保存")
        assert save_action.get("observed_in_steps") is True
        expand_action = next(a for a in actions if "展开" in a["name"])
        assert expand_action.get("observed_in_steps") is True

    def test_key_steps_distilled_with_roles(self):
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

    def test_interaction_patterns_merged(self):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        patterns = result.interaction_patterns
        assert len(patterns) == 2  # 1 common + 1 change pattern
        assert any("填写表单" in p for p in patterns)
        assert any("属性变化" in p for p in patterns)

    def test_execution_notes_from_no_change(self):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        notes = result.execution_notes
        # Navigation no-change is skipped; only async_pending note remains
        assert len(notes) == 1
        assert "async_pending" in notes[0].note
        assert notes[0].source == "no_change_step"

    def test_confidence_notes_merged_and_deduped(self):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        assert len(result.confidence_notes) == 2
        assert "页面结构较典型" in result.confidence_notes
        assert "保存步骤可能需要等待异步响应" in result.confidence_notes

    def test_page_description_generated(self):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        assert result.page_description != ""
        # Should mention page type (Chinese label) or goal
        assert "表单" in result.page_description or "活动" in result.page_description
        # Should mention regions
        assert "基础信息" in result.page_description or "高级配置" in result.page_description
        # Should mention actions
        assert "保存" in result.page_description or "取消" in result.page_description

    def test_operation_description_generated(self):
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        assert result.operation_description != ""
        # Should reflect the common patterns
        assert "填写" in result.operation_description or "保存" in result.operation_description
        # Should mention no-change observation (step 6 async_pending)
        assert "变化" in result.operation_description or "异步" in result.operation_description

    def test_output_is_serializable(self):
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


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_page_understanding(self):
        result = build_agent_page_understanding(
            PageUnderstanding(), _make_step_understanding(),
        )

        assert result.page_kind == "unknown"
        assert result.page_goal == ""
        assert result.primary_regions == []
        assert result.primary_actions == []
        # Steps still produce key_steps
        assert len(result.key_steps) >= 1
        # page_description empty when no page info
        assert result.page_description == ""
        # operation_description still generated from steps
        assert result.operation_description != ""

    def test_empty_step_understanding(self):
        result = build_agent_page_understanding(
            _make_page_understanding(), StepUnderstanding(),
        )

        assert result.page_kind == "form"
        assert result.page_goal == "创建新的营销活动"
        # Regions and actions present but no step enrichment
        assert len(result.primary_regions) == 2
        assert all("step_activity" not in r for r in result.primary_regions)
        assert result.key_steps == []
        assert result.interaction_patterns == []
        assert result.execution_notes == []
        # page_description still generated from page info
        assert result.page_description != ""
        # operation_description empty when no steps
        assert result.operation_description == ""

    def test_both_empty(self):
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

    def test_no_execution_planning_in_output(self):
        """Verify the output doesn't contain execution-planner fields."""
        result = build_agent_page_understanding(
            _make_page_understanding(), _make_step_understanding(),
        )

        data = result.model_dump()
        # Should NOT have execution planner concepts
        assert "next_action" not in data
        assert "action_plan" not in data
        assert "wait_condition" not in data
        assert "retry_strategy" not in data

    def test_all_no_change_steps_operation_description(self):
        """When all steps are no-change, operation_description still works."""
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
        # Should not contain "failure" language
        assert "失败" not in result.operation_description
        assert "错误" not in result.operation_description

    def test_interaction_patterns_capped_at_5(self):
        steps = StepUnderstanding(
            common_step_patterns=["p1", "p2", "p3"],
            observed_change_patterns=["c1", "c2", "c3"],
        )

        result = build_agent_page_understanding(PageUnderstanding(), steps)

        assert len(result.interaction_patterns) <= 5

    def test_duplicate_step_index_deduped(self):
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
        # Submit role takes precedence (processed first)
        assert result.key_steps[0].role == "submit"
