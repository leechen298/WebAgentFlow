"""Tests for Agent input contract builder.

Pure data transformation tests — no LLM calls, no DB.
"""

from __future__ import annotations

from app.schemas.ast import ASTNode, SimplifiedAST, SimplifyStats
from app.services.agent_input_builder import (
    build_agent_understanding_input,
    build_page_context,
    build_steps_context,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _make_simplified_ast() -> SimplifiedAST:
    """A small but realistic Simplified AST for testing."""
    return SimplifiedAST(
        nodes=[
            ASTNode(
                node_type="element",
                tag="div",
                attrs={"id": "app"},
                visible=True,
                children=[
                    ASTNode(node_type="text", text="Welcome", visible=True),
                    ASTNode(
                        node_type="element",
                        tag="input",
                        attrs={"type": "text", "name": "username", "placeholder": "Enter name"},
                        visible=True,
                    ),
                    ASTNode(
                        node_type="element",
                        tag="button",
                        attrs={"type": "submit"},
                        visible=True,
                        children=[
                            ASTNode(node_type="text", text="Submit", visible=True),
                        ],
                    ),
                    ASTNode(
                        node_type="element",
                        tag="a",
                        attrs={"href": "/help"},
                        visible=True,
                        children=[
                            ASTNode(node_type="text", text="Help", visible=True),
                        ],
                    ),
                    ASTNode(
                        node_type="element",
                        tag="div",
                        attrs={"role": "combobox"},
                        visible=False,  # hidden dropdown
                    ),
                ],
            ),
        ],
        stats=SimplifyStats(node_count=8, attrs_removed=5, class_tokens_removed=12),
    )


def _make_events() -> list[dict]:
    return [
        {"type": "navigate", "url": "https://example.com/form", "title": "Form Page", "timestamp": 1000},
        {"type": "click", "url": "https://example.com/form", "timestamp": 2000,
         "target": {"tag": "input", "selector": "#username"}},
        {"type": "input", "url": "https://example.com/form", "timestamp": 3000,
         "target": {"tag": "input", "selector": "#username"}, "value": "alice"},
    ]


def _make_agent_step_view() -> dict:
    return {
        "recording_id": "rec-001",
        "steps": [
            {
                "event_type": "navigate",
                "target": "https://example.com/form",
                "has_changes": False,
                "mutation_total": 0,
                "mutation_types": {"childList": 0, "attributes": 0, "characterData": 0},
                "change_area": None,
                "summary": "Navigate to https://example.com/form",
                "no_change_reason": "navigate",
            },
            {
                "event_type": "click",
                "target": '<input> "username"',
                "has_changes": True,
                "mutation_total": 3,
                "mutation_types": {"childList": 1, "attributes": 2, "characterData": 0},
                "change_area": "form",
                "summary": 'Click <input> "username" → +1 node, 2 attr changes',
                "no_change_reason": None,
            },
            {
                "event_type": "input",
                "target": '<input> "username"',
                "has_changes": True,
                "mutation_total": 1,
                "mutation_types": {"childList": 0, "attributes": 1, "characterData": 0},
                "change_area": "form",
                "summary": 'Input <input> "username" → 1 attr change',
                "no_change_reason": None,
            },
        ],
        "step_count": 3,
        "has_mutations": True,
    }


# ---------------------------------------------------------------------------
# PageContext
# ---------------------------------------------------------------------------

class TestBuildPageContext:
    def test_full_build(self):
        ctx = build_page_context("rec-001", _make_events(), _make_simplified_ast())

        assert ctx.recording_id == "rec-001"
        assert ctx.url == "https://example.com/form"
        assert ctx.title == "Form Page"

        # AST preserved
        assert len(ctx.ast_nodes) == 1
        assert ctx.ast_nodes[0].tag == "div"

        # Stats from SimplifyStats
        assert ctx.ast_stats.attrs_removed == 5
        assert ctx.ast_stats.class_tokens_removed == 12

        # Computed summary stats
        assert ctx.top_level_count == 1
        assert ctx.total_node_count == 8  # 5 elements + 3 text
        assert ctx.element_count == 5
        assert ctx.text_node_count == 3
        assert ctx.visible_element_count == 4  # one div is hidden

        # Interactive tags
        assert ctx.interactive_element_tags["input"] == 1
        assert ctx.interactive_element_tags["button"] == 1
        assert ctx.interactive_element_tags["a"] == 1
        assert ctx.interactive_element_tags["[role=combobox]"] == 1

    def test_no_simplified_ast(self):
        ctx = build_page_context("rec-002", _make_events(), None)

        assert ctx.recording_id == "rec-002"
        assert ctx.url == "https://example.com/form"
        assert ctx.title == "Form Page"
        assert ctx.ast_nodes == []
        assert ctx.total_node_count == 0
        assert ctx.interactive_element_tags == {}

    def test_empty_events(self):
        ctx = build_page_context("rec-003", [], _make_simplified_ast())

        assert ctx.url == ""
        assert ctx.title == ""
        # AST still present
        assert ctx.total_node_count == 8

    def test_url_from_non_navigate_event(self):
        """When no navigate event exists, fall back to first event with url."""
        events = [
            {"type": "click", "url": "https://example.com/page", "title": "Click Page",
             "timestamp": 1000, "target": {"tag": "button"}},
        ]
        ctx = build_page_context("rec-004", events, None)

        assert ctx.url == "https://example.com/page"
        assert ctx.title == "Click Page"

    def test_empty_ast_nodes(self):
        """SimplifiedAST with empty nodes list."""
        empty_ast = SimplifiedAST(
            nodes=[],
            stats=SimplifyStats(node_count=0),
        )
        ctx = build_page_context("rec-005", [], empty_ast)

        assert ctx.top_level_count == 0
        assert ctx.total_node_count == 0
        assert ctx.element_count == 0
        assert ctx.interactive_element_tags == {}


# ---------------------------------------------------------------------------
# StepsContext
# ---------------------------------------------------------------------------

class TestBuildStepsContext:
    def test_full_build(self):
        ctx = build_steps_context("rec-001", _make_agent_step_view())

        assert ctx.recording_id == "rec-001"
        assert ctx.step_count == 3
        assert ctx.has_mutations is True
        assert len(ctx.steps) == 3

        # Steps are plain dicts with expected fields
        assert ctx.steps[0]["event_type"] == "navigate"
        assert ctx.steps[1]["has_changes"] is True
        assert ctx.steps[2]["change_area"] == "form"

        # Summary stats
        assert ctx.summary.steps_with_changes == 2
        assert ctx.summary.steps_without_changes == 1
        assert ctx.summary.event_type_counts == {"navigate": 1, "click": 1, "input": 1}
        assert ctx.summary.has_navigate is True

    def test_empty_steps(self):
        ctx = build_steps_context("rec-002", {
            "recording_id": "rec-002",
            "steps": [],
            "step_count": 0,
            "has_mutations": False,
        })

        assert ctx.step_count == 0
        assert ctx.steps == []
        assert ctx.has_mutations is False
        assert ctx.summary.steps_with_changes == 0
        assert ctx.summary.steps_without_changes == 0
        assert ctx.summary.event_type_counts == {}
        assert ctx.summary.has_navigate is False

    def test_all_no_change_steps(self):
        view = {
            "recording_id": "rec-003",
            "steps": [
                {"event_type": "click", "target": '<button> "X"', "has_changes": False,
                 "mutation_total": 0, "mutation_types": {}, "summary": "Click X", "no_change_reason": "no_mutations_observed"},
                {"event_type": "click", "target": '<button> "Y"', "has_changes": False,
                 "mutation_total": 0, "mutation_types": {}, "summary": "Click Y", "no_change_reason": "no_mutations_observed"},
            ],
            "step_count": 2,
            "has_mutations": False,
        }
        ctx = build_steps_context("rec-003", view)

        assert ctx.summary.steps_with_changes == 0
        assert ctx.summary.steps_without_changes == 2
        assert ctx.summary.has_navigate is False


# ---------------------------------------------------------------------------
# AgentUnderstandingInput (combined)
# ---------------------------------------------------------------------------

class TestBuildAgentUnderstandingInput:
    def test_full_build(self):
        inp = build_agent_understanding_input(
            recording_id="rec-001",
            events=_make_events(),
            simplified_ast=_make_simplified_ast(),
            agent_step_view=_make_agent_step_view(),
        )

        assert inp.recording_id == "rec-001"
        assert inp.schema_version == "1"

        # Page context
        assert inp.page.url == "https://example.com/form"
        assert inp.page.total_node_count == 8
        assert inp.page.interactive_element_tags["input"] == 1

        # Steps context
        assert inp.steps.step_count == 3
        assert inp.steps.summary.steps_with_changes == 2
        assert inp.steps.summary.has_navigate is True

    def test_minimal_build(self):
        """Build with no AST and no steps — should still produce valid structure."""
        inp = build_agent_understanding_input(
            recording_id="rec-empty",
            events=[],
            simplified_ast=None,
            agent_step_view={"steps": [], "step_count": 0, "has_mutations": False},
        )

        assert inp.recording_id == "rec-empty"
        assert inp.page.url == ""
        assert inp.page.ast_nodes == []
        assert inp.page.total_node_count == 0
        assert inp.steps.step_count == 0
        assert inp.steps.steps == []

    def test_serializable(self):
        """The entire input should be JSON-serializable (prompt-friendly)."""
        inp = build_agent_understanding_input(
            recording_id="rec-001",
            events=_make_events(),
            simplified_ast=_make_simplified_ast(),
            agent_step_view=_make_agent_step_view(),
        )
        data = inp.model_dump()

        assert isinstance(data, dict)
        assert data["recording_id"] == "rec-001"
        assert isinstance(data["page"]["ast_nodes"], list)
        assert isinstance(data["steps"]["steps"], list)
        assert isinstance(data["steps"]["summary"]["event_type_counts"], dict)

    def test_no_debug_fields_leak(self):
        """Verify the output doesn't include internal/debug fields."""
        inp = build_agent_understanding_input(
            recording_id="rec-001",
            events=_make_events(),
            simplified_ast=_make_simplified_ast(),
            agent_step_view=_make_agent_step_view(),
        )
        data = inp.model_dump()

        # No raw events in the output
        assert "events" not in data
        assert "events" not in data["page"]

        # Steps are clean dicts, no raw mutation records
        for step in data["steps"]["steps"]:
            assert "dom_mutations" not in step
            assert "event_index" not in step
