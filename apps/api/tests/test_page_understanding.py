"""Tests for page understanding service (Phase 6C).

All tests use mock provider — no real LLM calls.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from app.schemas.agent_input import PageContext
from app.schemas.ast import ASTNode, SimplifyStats
from app.schemas.llm import LlmError, LlmResponse, LlmUsage
from app.schemas.page_understanding import PAGE_UNDERSTANDING_SCHEMA, PageUnderstanding
from app.services.page_understanding import (
    build_page_understanding_prompt,
    generate_page_understanding,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_page_context() -> PageContext:
    return PageContext(
        recording_id="rec-001",
        url="https://example.com/activities/create",
        title="创建活动",
        ast_nodes=[
            ASTNode(
                node_type="element",
                tag="div",
                attrs={"id": "app"},
                visible=True,
                children=[
                    ASTNode(node_type="text", text="创建活动", visible=True),
                    ASTNode(
                        node_type="element",
                        tag="input",
                        attrs={"type": "text", "name": "activity_name", "placeholder": "活动名称"},
                        visible=True,
                    ),
                    ASTNode(
                        node_type="element",
                        tag="button",
                        attrs={"type": "submit"},
                        visible=True,
                        children=[ASTNode(node_type="text", text="提交", visible=True)],
                    ),
                ],
            ),
        ],
        ast_stats=SimplifyStats(node_count=5, attrs_removed=3, class_tokens_removed=8),
        total_node_count=5,
        element_count=3,
        text_node_count=2,
        visible_element_count=3,
        top_level_count=1,
        interactive_element_tags={"input": 1, "button": 1},
    )


def _make_good_llm_response() -> LlmResponse:
    parsed = {
        "page_kind": "form",
        "page_goal": "创建新的活动记录",
        "primary_regions": [
            {"name": "基础信息表单", "role": "填写活动基础信息"},
        ],
        "primary_actions": [
            {"name": "提交", "action_type": "submit", "description": "提交活动创建表单"},
        ],
        "key_entities": ["活动"],
        "confidence_notes": [],
    }
    return LlmResponse(
        ok=True,
        text=json.dumps(parsed, ensure_ascii=False),
        parsed=parsed,
        usage=LlmUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        model="MiniMax-M2.7",
    )


def _make_empty_page_context() -> PageContext:
    return PageContext(recording_id="rec-empty")


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestPageUnderstandingSchema:
    def test_schema_is_valid_json_schema(self):
        """PAGE_UNDERSTANDING_SCHEMA should be a valid JSON Schema dict."""
        assert isinstance(PAGE_UNDERSTANDING_SCHEMA, dict)
        assert PAGE_UNDERSTANDING_SCHEMA.get("type") == "object"
        assert "properties" in PAGE_UNDERSTANDING_SCHEMA
        assert "page_kind" in PAGE_UNDERSTANDING_SCHEMA["properties"]
        assert "page_goal" in PAGE_UNDERSTANDING_SCHEMA["properties"]
        assert "primary_regions" in PAGE_UNDERSTANDING_SCHEMA["properties"]
        assert "primary_actions" in PAGE_UNDERSTANDING_SCHEMA["properties"]
        assert "key_entities" in PAGE_UNDERSTANDING_SCHEMA["properties"]

    def test_default_values(self):
        pu = PageUnderstanding()
        assert pu.page_kind == "unknown"
        assert pu.page_goal == ""
        assert pu.primary_regions == []
        assert pu.primary_actions == []
        assert pu.key_entities == []
        assert pu.confidence_notes == []

    def test_full_construction(self):
        pu = PageUnderstanding(
            page_kind="form",
            page_goal="创建活动",
            primary_regions=[{"name": "表单", "role": "填写信息"}],
            primary_actions=[{"name": "提交", "action_type": "submit", "description": ""}],
            key_entities=["活动", "奖品"],
            confidence_notes=["页面结构较简单"],
        )
        assert pu.page_kind == "form"
        assert len(pu.primary_regions) == 1
        assert pu.primary_regions[0].name == "表单"


# ---------------------------------------------------------------------------
# Prompt construction tests
# ---------------------------------------------------------------------------

class TestPromptConstruction:
    def test_prompt_includes_page_info(self):
        page = _make_page_context()
        prompt = build_page_understanding_prompt(page)

        assert "https://example.com/activities/create" in prompt
        assert "创建活动" in prompt
        assert "Total nodes: 5" in prompt
        assert "visible elements: 3" in prompt
        assert "top-level regions: 1" in prompt

    def test_prompt_includes_interactive_tags(self):
        page = _make_page_context()
        prompt = build_page_understanding_prompt(page)

        assert "input: 1" in prompt
        assert "button: 1" in prompt

    def test_prompt_includes_ast(self):
        page = _make_page_context()
        prompt = build_page_understanding_prompt(page)

        assert "Simplified AST:" in prompt
        assert "activity_name" in prompt  # from AST nodes

    def test_prompt_empty_page(self):
        page = _make_empty_page_context()
        prompt = build_page_understanding_prompt(page)

        assert "empty page" in prompt
        assert "Total nodes: 0" in prompt

    def test_prompt_no_url(self):
        page = PageContext(recording_id="rec-x", title="Test")
        prompt = build_page_understanding_prompt(page)

        assert "Page URL" not in prompt
        assert "Test" in prompt


# ---------------------------------------------------------------------------
# Service tests (mock provider)
# ---------------------------------------------------------------------------

class TestGeneratePageUnderstanding:
    @patch("app.services.page_understanding.generate_structured")
    def test_success(self, mock_gen):
        mock_gen.return_value = _make_good_llm_response()
        page = _make_page_context()

        result = generate_page_understanding(page)

        assert result["ok"] is True
        assert result["error"] is None
        assert result["understanding"]["page_kind"] == "form"
        assert result["understanding"]["page_goal"] == "创建新的活动记录"
        assert len(result["understanding"]["primary_regions"]) == 1
        assert len(result["understanding"]["primary_actions"]) == 1
        assert result["understanding"]["key_entities"] == ["活动"]
        assert result["usage"]["total_tokens"] == 150

    @patch("app.services.page_understanding.generate_structured")
    def test_provider_error(self, mock_gen):
        mock_gen.return_value = LlmResponse(
            ok=False,
            error=LlmError(kind="timeout", message="Request timed out", retryable=True),
            usage=LlmUsage(),
        )
        page = _make_page_context()

        result = generate_page_understanding(page)

        assert result["ok"] is False
        assert result["understanding"] is None
        assert result["error"]["kind"] == "timeout"

    @patch("app.services.page_understanding.generate_structured")
    def test_parse_error(self, mock_gen):
        mock_gen.return_value = LlmResponse(
            ok=False,
            error=LlmError(kind="parse_error", message="Failed to parse JSON"),
            usage=LlmUsage(prompt_tokens=100, completion_tokens=0, total_tokens=100),
        )

        result = generate_page_understanding(_make_page_context())

        assert result["ok"] is False
        assert result["error"]["kind"] == "parse_error"

    @patch("app.services.page_understanding.generate_structured")
    def test_validation_error(self, mock_gen):
        """Provider returns valid JSON but with wrong field types."""
        mock_gen.return_value = LlmResponse(
            ok=True,
            text='{"page_kind": 123}',
            parsed={"page_kind": 123},  # should be string
            usage=LlmUsage(prompt_tokens=100, completion_tokens=20, total_tokens=120),
            model="MiniMax-M2.7",
        )

        result = generate_page_understanding(_make_page_context())

        assert result["ok"] is False
        assert result["error"]["kind"] == "validation_error"
        # Raw parsed is preserved for debugging
        assert result["understanding"] is not None

    @patch("app.services.page_understanding.generate_structured")
    def test_empty_page(self, mock_gen):
        """Even an empty page should go through the flow without crashing."""
        mock_gen.return_value = LlmResponse(
            ok=True,
            text='{"page_kind":"unknown","page_goal":"","primary_regions":[],"primary_actions":[],"key_entities":[],"confidence_notes":[]}',
            parsed={
                "page_kind": "unknown",
                "page_goal": "",
                "primary_regions": [],
                "primary_actions": [],
                "key_entities": [],
                "confidence_notes": [],
            },
            usage=LlmUsage(prompt_tokens=50, completion_tokens=30, total_tokens=80),
        )

        result = generate_page_understanding(_make_empty_page_context())

        assert result["ok"] is True
        assert result["understanding"]["page_kind"] == "unknown"

    @patch("app.services.page_understanding.generate_structured")
    def test_request_uses_provider_layer(self, mock_gen):
        """Verify the service calls generate_structured with proper schema."""
        mock_gen.return_value = _make_good_llm_response()

        generate_page_understanding(_make_page_context())

        mock_gen.assert_called_once()
        request = mock_gen.call_args[0][0]
        assert request.response_schema is not None
        assert "page_kind" in str(request.response_schema)
        assert request.system is not None
        assert len(request.messages) == 1
