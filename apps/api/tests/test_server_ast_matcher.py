"""
Tests for the server-side event → AST matcher.

Covers:
1. Strong-feature matching: id, name
2. Selector-based matching: tag + id + classes
3. Tag + text content matching
4. Tag + attribute matching (placeholder, role, href)
5. Fallback to ancestor/region/none
6. Navigate event handling
7. Output structure stability and serialization
8. match_events_to_ast batch API
9. Step builder priority: server_ast_match over client astMatch
10. Fallback when no server_ast_match available
"""

import pytest

from app.schemas.ast import ASTNode, FullAST
from app.services.server_ast_matcher import (
    ServerAstMatch,
    build_ast_index,
    match_event_to_ast,
    match_events_to_ast,
)
from app.services.step_builder import build_steps


# ---------------------------------------------------------------------------
# Fixtures: a small but realistic AST
# ---------------------------------------------------------------------------

def _text(t: str) -> ASTNode:
    return ASTNode(node_type="text", text=t)


def _el(tag: str, attrs: dict | None = None, children: list | None = None, visible: bool = True) -> ASTNode:
    return ASTNode(
        node_type="element",
        tag=tag,
        attrs=attrs or {},
        children=children or [],
        visible=visible,
    )


@pytest.fixture
def sample_ast() -> FullAST:
    """A small page:
    <form>
      <h2>基础信息表单</h2>
      <input id="username" name="user" placeholder="请输入用户名">
      <input id="email" name="email" placeholder="请输入邮箱">
      <button class="el-button el-button--primary">保存</button>
      <a href="/help" role="link">帮助</a>
    </form>
    <nav>
      <a href="/home">首页</a>
      <a href="/settings">设置</a>
    </nav>
    """
    return FullAST(
        nodes=[
            _el("form", {"role": "form"}, [
                _el("h2", {}, [_text("基础信息表单")]),
                _el("input", {"id": "username", "name": "user", "placeholder": "请输入用户名", "type": "text"}),
                _el("input", {"id": "email", "name": "email", "placeholder": "请输入邮箱", "type": "email"}),
                _el("button", {"class": "el-button el-button--primary"}, [_text("保存")]),
                _el("a", {"href": "/help", "role": "link"}, [_text("帮助")]),
            ]),
            _el("nav", {"role": "navigation"}, [
                _el("a", {"href": "/home"}, [_text("首页")]),
                _el("a", {"href": "/settings"}, [_text("设置")]),
            ]),
        ],
        node_count=12,
    )


@pytest.fixture
def index(sample_ast):
    return build_ast_index(sample_ast)


# ---------------------------------------------------------------------------
# 1. Strong-feature matching: id
# ---------------------------------------------------------------------------

class TestMatchById:
    def test_exact_match_by_id(self, index):
        ev = {"type": "click", "target": {"tag": "input", "id": "username"}}
        result = match_event_to_ast(ev, index)
        assert result.match_type == "exact"
        assert result.confidence == "high"
        assert result.tag == "input"
        assert result.path is not None

    def test_id_takes_priority(self, index):
        """id should match even if tag differs (edge case)."""
        ev = {"type": "click", "target": {"tag": "div", "id": "email"}}
        result = match_event_to_ast(ev, index)
        assert result.match_type == "exact"
        assert result.confidence == "high"
        assert result.tag == "input"  # matched the real node


# ---------------------------------------------------------------------------
# 2. Strong-feature matching: name
# ---------------------------------------------------------------------------

class TestMatchByName:
    def test_match_by_name_and_tag(self, index):
        ev = {"type": "input", "target": {"tag": "input", "name": "email"}}
        result = match_event_to_ast(ev, index)
        assert result.match_type == "exact"
        assert result.confidence == "high"
        assert result.tag == "input"


# ---------------------------------------------------------------------------
# 3. Selector-based matching
# ---------------------------------------------------------------------------

class TestMatchBySelector:
    def test_selector_with_tag_and_classes(self, index):
        ev = {"type": "click", "target": {"tag": "button", "selector": "button.el-button.el-button--primary"}}
        result = match_event_to_ast(ev, index)
        assert result.match_type == "exact"
        assert result.tag == "button"

    def test_selector_with_id(self, index):
        ev = {"type": "click", "target": {"tag": "input", "selector": "input#username"}}
        result = match_event_to_ast(ev, index)
        assert result.match_type == "exact"
        assert result.confidence == "high"


# ---------------------------------------------------------------------------
# 4. Tag + text matching
# ---------------------------------------------------------------------------

class TestMatchByTagAndText:
    def test_button_by_text(self, index):
        ev = {"type": "click", "target": {"tag": "button", "text": "保存"}}
        result = match_event_to_ast(ev, index)
        assert result.match_type == "exact"
        assert result.tag == "button"

    def test_link_by_text(self, index):
        ev = {"type": "click", "target": {"tag": "a", "text": "设置"}}
        result = match_event_to_ast(ev, index)
        assert result.match_type == "exact"
        assert result.tag == "a"


# ---------------------------------------------------------------------------
# 5. Tag + attribute matching
# ---------------------------------------------------------------------------

class TestMatchByAttrs:
    def test_match_by_placeholder(self, index):
        ev = {"type": "click", "target": {"tag": "input", "placeholder": "请输入邮箱"}}
        result = match_event_to_ast(ev, index)
        assert result.match_type == "exact"
        assert result.tag == "input"

    def test_match_by_href(self, index):
        ev = {"type": "click", "target": {"tag": "a", "href": "/settings"}}
        result = match_event_to_ast(ev, index)
        assert result.match_type == "exact"
        assert result.tag == "a"

    def test_match_by_role(self, index):
        ev = {"type": "click", "target": {"tag": "a", "role": "link"}}
        result = match_event_to_ast(ev, index)
        assert result.match_type == "exact"
        assert result.tag == "a"


# ---------------------------------------------------------------------------
# 6. Fallback / no match
# ---------------------------------------------------------------------------

class TestFallback:
    def test_no_match_returns_none(self, index):
        ev = {"type": "click", "target": {"tag": "span", "text": "不存在的内容"}}
        result = match_event_to_ast(ev, index)
        assert result.match_type == "none"
        assert result.confidence == "low"

    def test_no_target_returns_none(self, index):
        ev = {"type": "click"}
        result = match_event_to_ast(ev, index)
        assert result.match_type == "none"

    def test_empty_target_returns_none(self, index):
        ev = {"type": "click", "target": {}}
        result = match_event_to_ast(ev, index)
        assert result.match_type == "none"


# ---------------------------------------------------------------------------
# 7. Navigate event handling
# ---------------------------------------------------------------------------

class TestNavigateEvent:
    def test_navigate_returns_none(self, index):
        ev = {"type": "navigate", "url": "https://example.com/page"}
        result = match_event_to_ast(ev, index)
        assert result.match_type == "none"
        assert result.confidence == "low"


# ---------------------------------------------------------------------------
# 8. Region hint detection
# ---------------------------------------------------------------------------

class TestRegionHint:
    def test_form_child_gets_region_hint(self, index):
        ev = {"type": "click", "target": {"tag": "input", "id": "username"}}
        result = match_event_to_ast(ev, index)
        assert result.region_hint is not None
        # Should find the form's heading "基础信息表单"
        assert "基础信息" in result.region_hint or "form" in result.region_hint.lower()

    def test_nav_child_gets_region_hint(self, index):
        ev = {"type": "click", "target": {"tag": "a", "text": "首页"}}
        result = match_event_to_ast(ev, index)
        assert result.region_hint is not None


# ---------------------------------------------------------------------------
# 9. Output structure
# ---------------------------------------------------------------------------

class TestOutputStructure:
    def test_serialization(self, index):
        ev = {"type": "click", "target": {"tag": "input", "id": "username"}}
        result = match_event_to_ast(ev, index)
        d = result.model_dump()
        assert set(d.keys()) == {"match_type", "path", "tag", "label", "region_hint", "confidence"}
        assert isinstance(d["path"], list)
        assert all(isinstance(x, int) for x in d["path"])

    def test_none_result_serialization(self, index):
        ev = {"type": "navigate", "url": "https://example.com"}
        result = match_event_to_ast(ev, index)
        d = result.model_dump()
        assert d["match_type"] == "none"
        assert d["path"] is None


# ---------------------------------------------------------------------------
# 10. Batch API: match_events_to_ast
# ---------------------------------------------------------------------------

class TestBatchApi:
    def test_enhances_all_events(self, sample_ast):
        events = [
            {"type": "navigate", "url": "https://example.com"},
            {"type": "click", "target": {"tag": "input", "id": "username"}},
            {"type": "input", "target": {"tag": "input", "name": "email"}, "value": "test@test.com"},
        ]
        enhanced = match_events_to_ast(events, sample_ast)
        assert len(enhanced) == 3
        for ev in enhanced:
            assert "server_ast_match" in ev

    def test_original_events_not_mutated(self, sample_ast):
        events = [{"type": "click", "target": {"tag": "input", "id": "username"}}]
        original_keys = set(events[0].keys())
        match_events_to_ast(events, sample_ast)
        assert set(events[0].keys()) == original_keys  # no mutation


# ---------------------------------------------------------------------------
# 11. Step builder integration: server_ast_match priority
# ---------------------------------------------------------------------------

class TestStepBuilderIntegration:
    def test_server_ast_match_provides_change_area(self):
        """When server_ast_match has region_hint, it should be used for change_area."""
        events = [
            {
                "id": "e0", "type": "click", "timestamp": 1000,
                "url": "https://example.com",
                "target": {"tag": "button", "text": "保存"},
                "server_ast_match": {
                    "match_type": "exact", "path": [0, 3],
                    "tag": "button", "label": "保存",
                    "region_hint": "基础信息表单", "confidence": "high",
                },
            },
        ]
        mutations = [
            {
                "id": "m0", "timestamp": 1500, "mutationType": "childList",
                "url": "https://example.com", "targetTag": "div",
                "detail": {"type": "childList", "addedNodes": [{"tag": "div"}], "removedNodes": []},
            },
        ]
        result = build_steps("test", events, mutations)
        step = result["steps"][0]
        assert step["change_area"] is not None

    def test_fallback_to_client_ast_when_no_server(self):
        """When no server_ast_match, should fall back to client astMatch."""
        events = [
            {
                "id": "e0", "type": "click", "timestamp": 1000,
                "url": "https://example.com",
                "target": {"tag": "button", "text": "Save"},
                "astMatch": {
                    "confidence": "exact", "nodeId": "n5",
                    "areaLabel": "Client-side区域",
                },
            },
        ]
        mutations = []  # no mutations → change_area not from mutations
        result = build_steps("test", events, mutations)
        step = result["steps"][0]
        # No mutations means change_area comes from event AST
        # With no mutations, _determine_change_area is not called (assigned is empty)
        # But event_server_ast_match should still be stored
        assert step.get("event_server_ast_match") is None  # no server match
        assert step.get("event_ast_match") is not None  # client match present

    def test_server_match_stored_on_step(self):
        """event_server_ast_match should be present on step output."""
        events = [
            {
                "id": "e0", "type": "click", "timestamp": 1000,
                "url": "https://example.com",
                "target": {"tag": "button"},
                "server_ast_match": {
                    "match_type": "exact", "path": [0, 1],
                    "tag": "button", "label": "OK",
                    "region_hint": "Dialog", "confidence": "high",
                },
            },
        ]
        result = build_steps("test", events, [])
        step = result["steps"][0]
        assert step["event_server_ast_match"] is not None
        assert step["event_server_ast_match"]["match_type"] == "exact"
