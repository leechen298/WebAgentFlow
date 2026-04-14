"""Tests for step understanding service (Phase 6D).

All tests use mock provider — no real LLM calls.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from app.schemas.agent_input import StepsContext, StepsSummaryStats
from app.schemas.llm import LlmError, LlmResponse, LlmUsage
from app.schemas.step_understanding import STEP_UNDERSTANDING_SCHEMA, StepDescription, StepUnderstanding
from app.services.step_understanding import (
    build_step_understanding_prompt,
    generate_step_understanding,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_steps_context() -> StepsContext:
    return StepsContext(
        recording_id="rec-001",
        steps=[
            {
                "event_type": "navigate",
                "target": "https://admin.example.com/activities/create",
                "has_changes": False,
                "mutation_total": 0,
                "mutation_types": {"childList": 0, "attributes": 0, "characterData": 0},
                "change_area": None,
                "summary": "Navigate to https://admin.example.com/activities/create",
                "no_change_reason": "navigate",
            },
            {
                "event_type": "click",
                "target": '<input> "活动名称"',
                "has_changes": True,
                "mutation_total": 2,
                "mutation_types": {"childList": 0, "attributes": 2, "characterData": 0},
                "change_area": "form",
                "summary": 'Click <input> "活动名称" → 2 attr changes',
                "no_change_reason": None,
            },
            {
                "event_type": "input",
                "target": '<input> "活动名称"',
                "has_changes": True,
                "mutation_total": 1,
                "mutation_types": {"childList": 0, "attributes": 1, "characterData": 0},
                "change_area": "form",
                "summary": 'Input <input> "活动名称" → 1 attr change',
                "no_change_reason": None,
            },
            {
                "event_type": "click",
                "target": '<button> "展开高级配置"',
                "has_changes": True,
                "mutation_total": 5,
                "mutation_types": {"childList": 3, "attributes": 2, "characterData": 0},
                "change_area": "config-panel",
                "summary": 'Click <button> "展开高级配置" → +3 nodes, 2 attr changes',
                "no_change_reason": None,
            },
            {
                "event_type": "click",
                "target": '<button> "保存"',
                "has_changes": False,
                "mutation_total": 0,
                "mutation_types": {"childList": 0, "attributes": 0, "characterData": 0},
                "change_area": None,
                "summary": 'Click <button> "保存" → no observed changes',
                "no_change_reason": "no_mutations_observed",
            },
        ],
        step_count=5,
        has_mutations=True,
        summary=StepsSummaryStats(
            steps_with_changes=3,
            steps_without_changes=2,
            event_type_counts={"navigate": 1, "click": 3, "input": 1},
            has_navigate=True,
        ),
    )


def _make_good_llm_response() -> LlmResponse:
    parsed = {
        "step_descriptions": [
            {"step_index": 0, "description": "导航到活动创建页面。"},
            {"step_index": 1, "description": "点击活动名称输入框，准备填写。"},
            {"step_index": 2, "description": "在活动名称输入框中输入活动名称。"},
            {"step_index": 3, "description": "点击「展开高级配置」按钮，展开更多设置项。"},
            {"step_index": 4, "description": "点击保存按钮，但当前观察窗口内没有看到明显页面变化。"},
        ],
        "common_step_patterns": [
            "用户先导航到活动创建页面，填写表单字段，展开高级配置后尝试保存。",
        ],
        "likely_key_steps": [
            {
                "step_index": 2,
                "event_type": "input",
                "target": '<input> "活动名称"',
                "reason": "填写活动名称是创建活动的核心操作",
            },
            {
                "step_index": 4,
                "event_type": "click",
                "target": '<button> "保存"',
                "reason": "保存是最终提交动作",
            },
        ],
        "likely_expand_steps": [
            {
                "step_index": 3,
                "event_type": "click",
                "target": '<button> "展开高级配置"',
                "description": "展开隐藏的配置区域",
            },
        ],
        "likely_submit_steps": [
            {
                "step_index": 4,
                "event_type": "click",
                "target": '<button> "保存"',
                "description": "提交活动创建表单",
            },
        ],
        "likely_no_change_steps": [
            {
                "step_index": 0,
                "event_type": "navigate",
                "target": "https://admin.example.com/activities/create",
                "likely_reason": "navigation",
            },
            {
                "step_index": 4,
                "event_type": "click",
                "target": '<button> "保存"',
                "likely_reason": "async_pending",
            },
        ],
        "observed_change_patterns": [
            "输入操作导致属性变化，展开操作导致 childList 变化。",
            "保存按钮点击未观察到变化，可能是异步提交。",
        ],
        "confidence_notes": [],
    }
    return LlmResponse(
        ok=True,
        text=json.dumps(parsed, ensure_ascii=False),
        parsed=parsed,
        usage=LlmUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300),
        model="MiniMax-M2.7",
    )


def _make_empty_steps_context() -> StepsContext:
    return StepsContext(
        recording_id="rec-empty",
        steps=[],
        step_count=0,
        has_mutations=False,
        summary=StepsSummaryStats(),
    )


def _make_all_no_change_context() -> StepsContext:
    return StepsContext(
        recording_id="rec-noop",
        steps=[
            {
                "event_type": "click",
                "target": '<button> "X"',
                "has_changes": False,
                "mutation_total": 0,
                "mutation_types": {},
                "summary": "Click X → no changes",
                "no_change_reason": "no_mutations_observed",
            },
            {
                "event_type": "click",
                "target": '<button> "Y"',
                "has_changes": False,
                "mutation_total": 0,
                "mutation_types": {},
                "summary": "Click Y → no changes",
                "no_change_reason": "no_mutations_observed",
            },
        ],
        step_count=2,
        has_mutations=False,
        summary=StepsSummaryStats(
            steps_with_changes=0,
            steps_without_changes=2,
            event_type_counts={"click": 2},
        ),
    )


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestStepUnderstandingSchema:
    def test_schema_is_valid(self):
        assert isinstance(STEP_UNDERSTANDING_SCHEMA, dict)
        assert STEP_UNDERSTANDING_SCHEMA.get("type") == "object"
        props = STEP_UNDERSTANDING_SCHEMA["properties"]
        assert "common_step_patterns" in props
        assert "likely_key_steps" in props
        assert "likely_expand_steps" in props
        assert "likely_submit_steps" in props
        assert "likely_no_change_steps" in props
        assert "observed_change_patterns" in props
        assert "step_descriptions" in props

    def test_default_values(self):
        su = StepUnderstanding()
        assert su.common_step_patterns == []
        assert su.likely_key_steps == []
        assert su.likely_expand_steps == []
        assert su.likely_submit_steps == []
        assert su.likely_no_change_steps == []
        assert su.observed_change_patterns == []
        assert su.step_descriptions == []
        assert su.confidence_notes == []

    def test_full_construction(self):
        su = StepUnderstanding(
            common_step_patterns=["填写表单后提交"],
            likely_key_steps=[{
                "step_index": 0, "event_type": "click",
                "target": "button", "reason": "main action",
            }],
            likely_submit_steps=[{
                "step_index": 0, "event_type": "click",
                "target": "button", "description": "save",
            }],
            likely_no_change_steps=[{
                "step_index": 1, "event_type": "click",
                "target": "link", "likely_reason": "async_pending",
            }],
            step_descriptions=[
                {"step_index": 0, "description": "点击保存按钮提交表单。"},
                {"step_index": 1, "description": "点击链接，但当前观察窗口内没有明显变化。"},
            ],
        )
        assert len(su.likely_key_steps) == 1
        assert su.likely_key_steps[0].step_index == 0
        assert su.likely_no_change_steps[0].likely_reason == "async_pending"
        assert len(su.step_descriptions) == 2
        assert su.step_descriptions[0].step_index == 0
        assert su.step_descriptions[1].description == "点击链接，但当前观察窗口内没有明显变化。"

    def test_step_description_model(self):
        sd = StepDescription(step_index=0, description="导航到页面。")
        assert sd.step_index == 0
        assert sd.description == "导航到页面。"


# ---------------------------------------------------------------------------
# Prompt construction tests
# ---------------------------------------------------------------------------

class TestPromptConstruction:
    def test_prompt_includes_stats(self):
        prompt = build_step_understanding_prompt(_make_steps_context())

        assert "Total steps: 5" in prompt
        assert "Any mutations observed: True" in prompt
        assert "Steps with changes: 3" in prompt
        assert "without changes: 2" in prompt

    def test_prompt_includes_event_type_breakdown(self):
        prompt = build_step_understanding_prompt(_make_steps_context())

        assert "click: 3" in prompt
        assert "input: 1" in prompt
        assert "navigate: 1" in prompt

    def test_prompt_includes_step_details(self):
        prompt = build_step_understanding_prompt(_make_steps_context())

        assert "[0] navigate" in prompt
        assert "[3] click" in prompt
        assert "展开高级配置" in prompt
        assert "no_change_reason: navigate" in prompt
        assert "area: config-panel" in prompt

    def test_prompt_includes_summaries(self):
        prompt = build_step_understanding_prompt(_make_steps_context())

        assert "summary:" in prompt
        assert "2 attr changes" in prompt

    def test_prompt_empty_steps(self):
        prompt = build_step_understanding_prompt(_make_empty_steps_context())

        assert "Total steps: 0" in prompt
        assert "no steps recorded" in prompt

    def test_prompt_no_change_steps(self):
        prompt = build_step_understanding_prompt(_make_all_no_change_context())

        assert "Steps with changes: 0" in prompt
        assert "without changes: 2" in prompt


# ---------------------------------------------------------------------------
# Service tests (mock provider)
# ---------------------------------------------------------------------------

class TestGenerateStepUnderstanding:
    @patch("app.services.step_understanding.generate_structured")
    def test_success(self, mock_gen):
        mock_gen.return_value = _make_good_llm_response()

        result = generate_step_understanding(_make_steps_context())

        assert result["ok"] is True
        assert result["error"] is None
        u = result["understanding"]
        assert len(u["common_step_patterns"]) >= 1
        assert len(u["likely_key_steps"]) == 2
        assert u["likely_key_steps"][0]["step_index"] == 2
        assert len(u["likely_expand_steps"]) == 1
        assert u["likely_expand_steps"][0]["step_index"] == 3
        assert len(u["likely_submit_steps"]) == 1
        assert len(u["likely_no_change_steps"]) == 2
        assert len(u["observed_change_patterns"]) >= 1
        assert result["usage"]["total_tokens"] == 300

    @patch("app.services.step_understanding.generate_structured")
    def test_step_descriptions_cover_all_steps(self, mock_gen):
        mock_gen.return_value = _make_good_llm_response()

        result = generate_step_understanding(_make_steps_context())

        assert result["ok"] is True
        u = result["understanding"]
        descs = u["step_descriptions"]
        assert len(descs) == 5  # matches step_count
        indices = [d["step_index"] for d in descs]
        assert indices == [0, 1, 2, 3, 4]
        # Each description is non-empty
        assert all(d["description"] for d in descs)

    @patch("app.services.step_understanding.generate_structured")
    def test_no_change_step_description_not_failure(self, mock_gen):
        mock_gen.return_value = _make_good_llm_response()

        result = generate_step_understanding(_make_steps_context())

        u = result["understanding"]
        # Step 4 is a no-change step (save button)
        save_desc = next(d for d in u["step_descriptions"] if d["step_index"] == 4)
        desc_lower = save_desc["description"].lower()
        assert "失败" not in desc_lower
        assert "错误" not in desc_lower
        assert "error" not in desc_lower
        assert "fail" not in desc_lower

    @patch("app.services.step_understanding.generate_structured")
    def test_provider_error(self, mock_gen):
        mock_gen.return_value = LlmResponse(
            ok=False,
            error=LlmError(kind="timeout", message="timed out", retryable=True),
            usage=LlmUsage(),
        )

        result = generate_step_understanding(_make_steps_context())

        assert result["ok"] is False
        assert result["understanding"] is None
        assert result["error"]["kind"] == "timeout"

    @patch("app.services.step_understanding.generate_structured")
    def test_validation_error(self, mock_gen):
        mock_gen.return_value = LlmResponse(
            ok=True,
            text='{"likely_key_steps": "not_a_list"}',
            parsed={"likely_key_steps": "not_a_list"},
            usage=LlmUsage(prompt_tokens=50, completion_tokens=10, total_tokens=60),
        )

        result = generate_step_understanding(_make_steps_context())

        assert result["ok"] is False
        assert result["error"]["kind"] == "validation_error"
        assert result["understanding"] is not None  # raw preserved

    @patch("app.services.step_understanding.generate_structured")
    def test_empty_steps(self, mock_gen):
        mock_gen.return_value = LlmResponse(
            ok=True,
            text='{"common_step_patterns":[],"likely_key_steps":[],"likely_expand_steps":[],"likely_submit_steps":[],"likely_no_change_steps":[],"observed_change_patterns":[],"confidence_notes":["No steps to analyze"]}',
            parsed={
                "common_step_patterns": [],
                "likely_key_steps": [],
                "likely_expand_steps": [],
                "likely_submit_steps": [],
                "likely_no_change_steps": [],
                "observed_change_patterns": [],
                "confidence_notes": ["No steps to analyze"],
            },
            usage=LlmUsage(prompt_tokens=30, completion_tokens=20, total_tokens=50),
        )

        result = generate_step_understanding(_make_empty_steps_context())

        assert result["ok"] is True
        assert result["understanding"]["likely_key_steps"] == []

    @patch("app.services.step_understanding.generate_structured")
    def test_all_no_change(self, mock_gen):
        mock_gen.return_value = LlmResponse(
            ok=True,
            text=json.dumps({
                "common_step_patterns": ["用户点击了两个按钮，均未产生可观察变化。"],
                "likely_key_steps": [],
                "likely_expand_steps": [],
                "likely_submit_steps": [],
                "likely_no_change_steps": [
                    {"step_index": 0, "event_type": "click", "target": '<button> "X"', "likely_reason": "unknown"},
                    {"step_index": 1, "event_type": "click", "target": '<button> "Y"', "likely_reason": "unknown"},
                ],
                "observed_change_patterns": ["所有步骤均无 DOM 变化。"],
                "confidence_notes": ["无变化不代表操作失败"],
            }, ensure_ascii=False),
            parsed={
                "common_step_patterns": ["用户点击了两个按钮，均未产生可观察变化。"],
                "likely_key_steps": [],
                "likely_expand_steps": [],
                "likely_submit_steps": [],
                "likely_no_change_steps": [
                    {"step_index": 0, "event_type": "click", "target": '<button> "X"', "likely_reason": "unknown"},
                    {"step_index": 1, "event_type": "click", "target": '<button> "Y"', "likely_reason": "unknown"},
                ],
                "observed_change_patterns": ["所有步骤均无 DOM 变化。"],
                "confidence_notes": ["无变化不代表操作失败"],
            },
            usage=LlmUsage(prompt_tokens=60, completion_tokens=40, total_tokens=100),
        )

        result = generate_step_understanding(_make_all_no_change_context())

        assert result["ok"] is True
        u = result["understanding"]
        assert len(u["likely_no_change_steps"]) == 2
        assert u["likely_no_change_steps"][0]["likely_reason"] == "unknown"

    @patch("app.services.step_understanding.generate_structured")
    def test_request_uses_provider_layer(self, mock_gen):
        mock_gen.return_value = _make_good_llm_response()

        generate_step_understanding(_make_steps_context())

        mock_gen.assert_called_once()
        request = mock_gen.call_args[0][0]
        assert request.response_schema is not None
        assert "likely_key_steps" in str(request.response_schema)
        assert "step_descriptions" in str(request.response_schema)
        assert request.system is not None
