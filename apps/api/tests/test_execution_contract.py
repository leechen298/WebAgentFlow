"""
Tests for the execution contract (Phase 7A).

Covers:
1. ExecutionRequest / ExecutionResult schema stability
2. build_execution_request assembles correct structure
3. Locator priority ordering is enforced
4. server_ast_match produces highest-priority hints
5. client astMatch is always lowest priority
6. Missing understanding → degraded mode (empty dict, not error)
7. Missing server_ast_match → no SERVER_AST_MATCH hints
8. Minimal input (step only) → valid request
9. Output schemas serializable and round-trip cleanly
10. LocatorPriority enum ordering
"""

import pytest

from app.schemas.execution import (
    ActionTarget,
    ExecutionRequest,
    ExecutionResult,
    LocatorHint,
    LocatorPriority,
    LocatorResult,
    PageSnapshot,
    PageStateChange,
    LOCATOR_PRIORITY_ORDER,
)
from app.services.execution_contract import build_execution_request


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _step(
    *,
    event_type: str = "click",
    target: str = '<button> "提交"',
    url: str = "https://example.com/form",
    event_index: int = 0,
    server_ast_match: dict | None = None,
) -> dict:
    s = {
        "id": f"s{event_index}",
        "timestamp": 1000,
        "end_timestamp": 2000,
        "url": url,
        "event_index": event_index,
        "event_type": event_type,
        "event_target_summary": target,
        "event_ast_match": None,
        "event_server_ast_match": server_ast_match,
        "mutations": {"total": 1, "by_type": {"childList": 1, "attributes": 0, "characterData": 0}},
        "has_changes": True,
        "change_area": None,
        "summary": f"Click {target}",
    }
    return s


def _event(
    *,
    tag: str = "button",
    text: str = "提交",
    id: str = "",
    name: str = "",
    selector: str = "",
    ast_match: dict | None = None,
    value: str | None = None,
) -> dict:
    target: dict = {"tag": tag, "text": text}
    if id:
        target["id"] = id
    if name:
        target["name"] = name
    if selector:
        target["selector"] = selector
    ev: dict = {"type": "click", "timestamp": 1000, "target": target}
    if ast_match:
        ev["astMatch"] = ast_match
    if value:
        ev["value"] = value
    return ev


def _understanding() -> dict:
    return {
        "page_kind": "form",
        "page_goal": "Submit an order",
        "primary_regions": [{"name": "order form", "role": "data entry"}],
        "primary_actions": [{"name": "提交", "action_type": "submit", "description": "Submit order"}],
        "key_steps": [],
        "interaction_patterns": ["Fill fields then submit"],
        "execution_notes": [],
        "key_entities": ["order"],
        "confidence_notes": [],
    }


def _server_ast_match(
    *,
    match_type: str = "exact",
    path: list[int] | None = None,
    tag: str = "button",
    label: str = "提交",
    region_hint: str | None = None,
    confidence: str = "high",
) -> dict:
    return {
        "match_type": match_type,
        "path": path or [0, 3, 1],
        "tag": tag,
        "label": label,
        "region_hint": region_hint,
        "confidence": confidence,
    }


# ---------------------------------------------------------------------------
# 1. Schema stability — fields exist and have correct defaults
# ---------------------------------------------------------------------------

class TestSchemaStability:
    def test_execution_request_defaults(self):
        req = ExecutionRequest(
            page=PageSnapshot(url="https://x.com"),
            action=ActionTarget(action_type="click", target_description="btn"),
        )
        assert req.understanding == {}
        assert req.locator_hints == []
        assert req.recording_id == ""
        assert req.step_index is None

    def test_execution_result_defaults(self):
        res = ExecutionResult()
        assert res.ok is False
        assert res.action_type == ""
        assert res.error is None
        assert res.warnings == []
        assert res.screenshot_ref is None
        assert res.html_snapshot_ref is None
        assert res.trace == []
        assert res.elapsed_ms is None
        assert isinstance(res.locator, LocatorResult)
        assert isinstance(res.page_change, PageStateChange)

    def test_locator_result_defaults(self):
        lr = LocatorResult()
        assert lr.resolved_locator == ""
        assert lr.strategy_used == ""
        assert lr.confidence == "low"
        assert lr.candidates_considered == 0

    def test_page_state_change_defaults(self):
        psc = PageStateChange()
        assert psc.url_before == ""
        assert psc.url_after == ""


# ---------------------------------------------------------------------------
# 2. build_execution_request — basic assembly
# ---------------------------------------------------------------------------

class TestBuildExecutionRequest:
    def test_basic_assembly(self):
        req = build_execution_request(
            recording_id="rec-1",
            step=_step(),
            understanding=_understanding(),
            page_url="https://example.com/form",
            page_title="Order Form",
        )
        assert req.recording_id == "rec-1"
        assert req.page.url == "https://example.com/form"
        assert req.page.title == "Order Form"
        assert req.action.action_type == "click"
        assert req.action.target_description == '<button> "提交"'
        assert req.understanding["page_kind"] == "form"

    def test_step_index_from_event_index(self):
        req = build_execution_request(
            recording_id="r",
            step=_step(event_index=5),
        )
        assert req.step_index == 5

    def test_url_fallback_to_step_url(self):
        """If page_url not provided, falls back to step url."""
        req = build_execution_request(
            recording_id="r",
            step=_step(url="https://from-step.com"),
        )
        assert req.page.url == "https://from-step.com"

    def test_action_type_mapping_input(self):
        req = build_execution_request(
            recording_id="r",
            step=_step(event_type="input"),
        )
        assert req.action.action_type == "fill"

    def test_action_type_mapping_change(self):
        req = build_execution_request(
            recording_id="r",
            step=_step(event_type="change"),
        )
        assert req.action.action_type == "select"

    def test_action_type_mapping_navigate(self):
        req = build_execution_request(
            recording_id="r",
            step=_step(event_type="navigate"),
        )
        assert req.action.action_type == "navigate"

    def test_value_from_raw_event(self):
        req = build_execution_request(
            recording_id="r",
            step=_step(event_type="input"),
            raw_event=_event(value="hello world"),
        )
        assert req.action.value == "hello world"

    def test_region_constraint_from_server_ast_match(self):
        sam = _server_ast_match(region_hint="order form")
        req = build_execution_request(
            recording_id="r",
            step=_step(server_ast_match=sam),
        )
        assert req.action.region_constraint == "order form"


# ---------------------------------------------------------------------------
# 3. Locator priority ordering
# ---------------------------------------------------------------------------

class TestLocatorPriority:
    def test_enum_order(self):
        assert LocatorPriority.SERVER_AST_MATCH < LocatorPriority.STRONG_ATTRIBUTE
        assert LocatorPriority.STRONG_ATTRIBUTE < LocatorPriority.TAG_TEXT_LABEL
        assert LocatorPriority.TAG_TEXT_LABEL < LocatorPriority.REGION_SCOPED
        assert LocatorPriority.REGION_SCOPED < LocatorPriority.FALLBACK_SELECTOR
        assert LocatorPriority.FALLBACK_SELECTOR < LocatorPriority.CLIENT_AST_MATCH

    def test_priority_order_list(self):
        assert LOCATOR_PRIORITY_ORDER[0] == "SERVER_AST_MATCH"
        assert LOCATOR_PRIORITY_ORDER[-1] == "CLIENT_AST_MATCH"
        assert len(LOCATOR_PRIORITY_ORDER) == 6


# ---------------------------------------------------------------------------
# 4. server_ast_match → highest priority hints
# ---------------------------------------------------------------------------

class TestServerAstMatchHints:
    def test_server_ast_match_produces_top_hint(self):
        sam = _server_ast_match(path=[0, 3, 1])
        req = build_execution_request(
            recording_id="r",
            step=_step(server_ast_match=sam),
        )
        assert len(req.locator_hints) >= 1
        top = req.locator_hints[0]
        assert top.strategy == "SERVER_AST_MATCH"
        assert top.value == "0.3.1"
        assert top.confidence == "high"

    def test_server_ast_match_none_match_type_excluded(self):
        sam = {"match_type": "none", "path": None, "confidence": "low"}
        req = build_execution_request(
            recording_id="r",
            step=_step(server_ast_match=sam),
        )
        # No SERVER_AST_MATCH hint when match_type is "none"
        sam_hints = [h for h in req.locator_hints if h.strategy == "SERVER_AST_MATCH"]
        assert len(sam_hints) == 0

    def test_region_hint_produces_region_scoped_hint(self):
        sam = _server_ast_match(region_hint="sidebar nav")
        req = build_execution_request(
            recording_id="r",
            step=_step(server_ast_match=sam),
        )
        region_hints = [h for h in req.locator_hints if h.strategy == "REGION_SCOPED"]
        assert len(region_hints) == 1
        assert region_hints[0].value == "sidebar nav"


# ---------------------------------------------------------------------------
# 5. client astMatch is always lowest priority
# ---------------------------------------------------------------------------

class TestClientAstMatchPriority:
    def test_client_ast_match_is_last(self):
        sam = _server_ast_match()
        ev = _event(
            id="btn-submit",
            ast_match={"nodeId": "n42", "confidence": "high", "nodeLabel": "Submit"},
        )
        req = build_execution_request(
            recording_id="r",
            step=_step(server_ast_match=sam),
            raw_event=ev,
        )
        # There should be multiple hints; CLIENT_AST_MATCH must be last
        strategies = [h.strategy for h in req.locator_hints]
        assert "CLIENT_AST_MATCH" in strategies
        assert strategies[-1] == "CLIENT_AST_MATCH"

    def test_client_ast_match_only_when_node_id_present(self):
        ev = _event(ast_match={"confidence": "low"})  # no nodeId
        req = build_execution_request(
            recording_id="r",
            step=_step(),
            raw_event=ev,
        )
        cam_hints = [h for h in req.locator_hints if h.strategy == "CLIENT_AST_MATCH"]
        assert len(cam_hints) == 0


# ---------------------------------------------------------------------------
# 6. Missing understanding → degraded mode
# ---------------------------------------------------------------------------

class TestDegradedMode:
    def test_no_understanding(self):
        req = build_execution_request(
            recording_id="r",
            step=_step(),
            understanding=None,
        )
        assert req.understanding == {}

    def test_empty_understanding(self):
        req = build_execution_request(
            recording_id="r",
            step=_step(),
            understanding={},
        )
        assert req.understanding == {}


# ---------------------------------------------------------------------------
# 7. Missing server_ast_match → no SERVER_AST_MATCH hints
# ---------------------------------------------------------------------------

class TestMissingServerAstMatch:
    def test_step_without_server_ast_match(self):
        step = _step(server_ast_match=None)
        req = build_execution_request(recording_id="r", step=step)
        sam_hints = [h for h in req.locator_hints if h.strategy == "SERVER_AST_MATCH"]
        assert len(sam_hints) == 0

    def test_step_without_server_ast_match_still_has_event_hints(self):
        step = _step(server_ast_match=None)
        ev = _event(id="my-btn", selector="button#my-btn")
        req = build_execution_request(recording_id="r", step=step, raw_event=ev)
        strategies = [h.strategy for h in req.locator_hints]
        assert "STRONG_ATTRIBUTE" in strategies
        assert "FALLBACK_SELECTOR" in strategies


# ---------------------------------------------------------------------------
# 8. Minimal input — step only
# ---------------------------------------------------------------------------

class TestMinimalInput:
    def test_step_only(self):
        req = build_execution_request(
            recording_id="r",
            step={"event_type": "click", "event_target_summary": "<button>"},
        )
        assert req.action.action_type == "click"
        assert req.page.url == ""
        assert req.locator_hints == []
        assert req.understanding == {}

    def test_step_missing_fields_uses_defaults(self):
        req = build_execution_request(
            recording_id="r",
            step={},
        )
        assert req.action.action_type == "click"  # default
        assert req.action.target_description == ""


# ---------------------------------------------------------------------------
# 9. Serialization round-trip
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_execution_request_round_trip(self):
        req = build_execution_request(
            recording_id="rec-1",
            step=_step(server_ast_match=_server_ast_match()),
            raw_event=_event(id="btn-1"),
            understanding=_understanding(),
            page_url="https://example.com",
            page_title="Test",
        )
        data = req.model_dump()
        restored = ExecutionRequest.model_validate(data)
        assert restored.recording_id == req.recording_id
        assert len(restored.locator_hints) == len(req.locator_hints)
        assert restored.action.action_type == req.action.action_type

    def test_execution_result_round_trip(self):
        res = ExecutionResult(
            ok=True,
            action_type="click",
            target_summary="Submit button",
            locator=LocatorResult(
                resolved_locator='button:has-text("Submit")',
                strategy_used="TAG_TEXT_LABEL",
                confidence="high",
                candidates_considered=3,
            ),
            page_change=PageStateChange(
                url_before="https://a.com",
                url_after="https://a.com/done",
            ),
            warnings=["Slow page load"],
            trace=["Tried SERVER_AST_MATCH", "Fell back to TAG_TEXT_LABEL"],
        )
        data = res.model_dump()
        restored = ExecutionResult.model_validate(data)
        assert restored.ok is True
        assert restored.locator.strategy_used == "TAG_TEXT_LABEL"
        assert len(restored.trace) == 2

    def test_json_serialization(self):
        req = build_execution_request(
            recording_id="r",
            step=_step(),
        )
        json_str = req.model_dump_json()
        assert '"recording_id"' in json_str
        assert '"action_type"' in json_str


# ---------------------------------------------------------------------------
# 10. Hint ordering — mixed sources sorted correctly
# ---------------------------------------------------------------------------

class TestHintOrdering:
    def test_full_hint_ordering(self):
        """All hint sources present → sorted by LocatorPriority."""
        sam = _server_ast_match(region_hint="form area")
        ev = _event(
            id="submit-btn",
            name="submit",
            selector="button#submit-btn",
            ast_match={"nodeId": "n1", "confidence": "high"},
        )
        req = build_execution_request(
            recording_id="r",
            step=_step(server_ast_match=sam),
            raw_event=ev,
        )
        strategies = [h.strategy for h in req.locator_hints]

        # SERVER_AST_MATCH must come first
        assert strategies[0] == "SERVER_AST_MATCH"

        # CLIENT_AST_MATCH must come last
        assert strategies[-1] == "CLIENT_AST_MATCH"

        # STRONG_ATTRIBUTE before TAG_TEXT_LABEL
        strong_idx = [i for i, s in enumerate(strategies) if s == "STRONG_ATTRIBUTE"]
        tag_idx = [i for i, s in enumerate(strategies) if s == "TAG_TEXT_LABEL"]
        if strong_idx and tag_idx:
            assert min(strong_idx) < min(tag_idx)

    def test_no_duplicate_strategies_from_same_source(self):
        """Multiple strong attributes produce multiple hints, all STRONG_ATTRIBUTE."""
        ev = _event(id="x", name="y")
        req = build_execution_request(
            recording_id="r",
            step=_step(),
            raw_event=ev,
        )
        strong = [h for h in req.locator_hints if h.strategy == "STRONG_ATTRIBUTE"]
        assert len(strong) == 2  # id + name
        assert {h.meta.get("attribute") for h in strong} == {"id", "name"}
