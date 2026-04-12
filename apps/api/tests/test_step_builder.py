"""
Tests for the step_builder service — event → mutation correlation.

Covers:
1. Mutations within time window are correlated to the preceding event
2. Events with no mutations produce steps with hasChanges=False
3. Mutations are assigned to the closest preceding event (no cross-contamination)
4. Same-frame mutations are included
5. Time window respects event type (click=2000ms, input=500ms)
6. Step ordering is stable (follows event order)
7. Empty events / empty mutations edge cases
"""

import pytest

from app.services.step_builder import build_steps


def _ev(
    idx: int,
    ev_type: str = "click",
    ts: int = 1000,
    url: str = "https://example.com",
    target_tag: str = "button",
    target_text: str = "",
    frame_iframe: bool = False,
    frame_url: str = "",
    ast_match: dict | None = None,
) -> dict:
    ev: dict = {
        "id": f"e{idx}",
        "type": ev_type,
        "timestamp": ts,
        "url": url,
        "target": {"tag": target_tag, "text": target_text},
    }
    if frame_iframe:
        ev["frameInfo"] = {"isIframe": True, "frameUrl": frame_url or url}
    if ast_match:
        ev["astMatch"] = ast_match
    return ev


def _mut(
    mid: str,
    ts: int = 1500,
    mut_type: str = "childList",
    target_tag: str = "div",
    frame_iframe: bool = False,
    frame_url: str = "",
    area_label: str = "",
) -> dict:
    detail: dict
    if mut_type == "childList":
        detail = {"type": "childList", "addedNodes": [{"tag": "div", "text": "new"}], "removedNodes": []}
    elif mut_type == "attributes":
        detail = {"type": "attributes", "attributeName": "class", "oldValue": "old", "newValue": "new"}
    else:
        detail = {"type": "characterData", "oldValue": "old", "newValue": "new text"}

    m: dict = {
        "id": mid,
        "timestamp": ts,
        "mutationType": mut_type,
        "url": "https://example.com",
        "targetTag": target_tag,
        "detail": detail,
    }
    if frame_iframe:
        m["frameInfo"] = {"isIframe": True, "frameUrl": frame_url or "https://example.com/iframe"}
    if area_label:
        m["areaLabel"] = area_label
    return m


class TestBasicCorrelation:
    """Mutations within a time window are assigned to the preceding event."""

    def test_click_with_mutations_in_window(self):
        events = [_ev(0, "click", ts=1000)]
        mutations = [
            _mut("m0", ts=1200, mut_type="childList"),
            _mut("m1", ts=1500, mut_type="attributes"),
        ]
        result = build_steps("rec1", events, mutations)
        assert len(result["steps"]) == 1
        step = result["steps"][0]
        assert step["has_changes"] is True
        assert step["mutations"]["total"] == 2
        assert set(step["mutations"]["mutation_ids"]) == {"m0", "m1"}
        assert step["mutations"]["by_type"]["childList"] == 1
        assert step["mutations"]["by_type"]["attributes"] == 1
        assert result["mutations_correlated"] == 2
        assert result["mutations_uncorrelated"] == 0

    def test_mutation_outside_window_not_correlated(self):
        events = [_ev(0, "click", ts=1000)]
        mutations = [_mut("m0", ts=3500)]  # 2500ms after click, outside 2000ms window
        result = build_steps("rec1", events, mutations)
        step = result["steps"][0]
        assert step["has_changes"] is False
        assert step["mutations"]["total"] == 0
        assert result["mutations_uncorrelated"] == 1

    def test_input_shorter_window(self):
        events = [_ev(0, "input", ts=1000)]
        # 800ms after input — outside 500ms window
        mutations = [_mut("m0", ts=1800)]
        result = build_steps("rec1", events, mutations)
        assert result["steps"][0]["has_changes"] is False
        assert result["mutations_uncorrelated"] == 1

    def test_input_within_window(self):
        events = [_ev(0, "input", ts=1000)]
        mutations = [_mut("m0", ts=1300)]  # 300ms — within 500ms window
        result = build_steps("rec1", events, mutations)
        assert result["steps"][0]["has_changes"] is True
        assert result["steps"][0]["mutations"]["total"] == 1


class TestNoMutationSteps:
    """Events without mutations still produce steps."""

    def test_click_no_mutations(self):
        events = [_ev(0, "click", ts=1000)]
        result = build_steps("rec1", events, [])
        assert len(result["steps"]) == 1
        step = result["steps"][0]
        assert step["has_changes"] is False
        assert step["mutations"]["total"] == 0
        assert "no observable changes" in step["summary"]

    def test_navigate_no_mutations(self):
        events = [_ev(0, "navigate", ts=1000)]
        result = build_steps("rec1", events, [])
        step = result["steps"][0]
        assert step["event_type"] == "navigate"
        assert step["has_changes"] is False


class TestMultiEventNonOverlap:
    """Each mutation is assigned to at most one step (latest event wins)."""

    def test_two_events_mutations_go_to_closest(self):
        events = [
            _ev(0, "click", ts=1000),
            _ev(1, "click", ts=2000),
        ]
        mutations = [
            _mut("m0", ts=1200),  # Within ev0 window only
            _mut("m1", ts=2100),  # Within ev1 window (also technically ev0 window, but ev1 is later)
            _mut("m2", ts=2500),  # Within ev1 window only
        ]
        result = build_steps("rec1", events, mutations)
        s0 = result["steps"][0]
        s1 = result["steps"][1]

        assert s0["mutations"]["total"] == 1
        assert "m0" in s0["mutations"]["mutation_ids"]

        assert s1["mutations"]["total"] == 2
        assert "m1" in s1["mutations"]["mutation_ids"]
        assert "m2" in s1["mutations"]["mutation_ids"]

    def test_mutations_between_events_assigned_to_later(self):
        """When a mutation falls in the overlap of two event windows, the later event wins."""
        events = [
            _ev(0, "click", ts=1000),
            _ev(1, "click", ts=1500),
        ]
        mutations = [
            _mut("m0", ts=1600),  # In both windows — should go to ev1 (later)
        ]
        result = build_steps("rec1", events, mutations)
        assert result["steps"][0]["mutations"]["total"] == 0
        assert result["steps"][1]["mutations"]["total"] == 1


class TestFrameHandling:
    """Frame info is preserved on steps."""

    def test_iframe_event_includes_frame_info(self):
        events = [_ev(0, "click", ts=1000, frame_iframe=True, frame_url="https://example.com/frame")]
        result = build_steps("rec1", events, [])
        step = result["steps"][0]
        assert step["frame_info"] is not None
        assert step["frame_info"]["isIframe"] is True

    def test_top_frame_event_no_frame_info(self):
        events = [_ev(0, "click", ts=1000)]
        result = build_steps("rec1", events, [])
        assert result["steps"][0]["frame_info"] is None


class TestStepOrdering:
    """Steps maintain the original event order."""

    def test_order_matches_events(self):
        events = [
            _ev(0, "navigate", ts=1000),
            _ev(1, "click", ts=2000),
            _ev(2, "input", ts=3000),
        ]
        result = build_steps("rec1", events, [])
        assert [s["id"] for s in result["steps"]] == ["s0", "s1", "s2"]
        assert [s["event_type"] for s in result["steps"]] == ["navigate", "click", "input"]
        assert [s["event_index"] for s in result["steps"]] == [0, 1, 2]


class TestEdgeCases:
    """Empty inputs and boundary conditions."""

    def test_empty_events(self):
        result = build_steps("rec1", [], [_mut("m0", ts=100)])
        assert result["steps"] == []
        assert result["event_count"] == 0
        assert result["mutations_uncorrelated"] == 1

    def test_empty_mutations(self):
        result = build_steps("rec1", [_ev(0, "click", ts=1000)], [])
        assert len(result["steps"]) == 1
        assert result["mutation_count"] == 0

    def test_empty_both(self):
        result = build_steps("rec1", [], [])
        assert result["steps"] == []
        assert result["event_count"] == 0
        assert result["mutation_count"] == 0

    def test_mutation_before_first_event_uncorrelated(self):
        events = [_ev(0, "click", ts=2000)]
        mutations = [_mut("m0", ts=500)]
        result = build_steps("rec1", events, mutations)
        assert result["steps"][0]["has_changes"] is False
        assert result["mutations_uncorrelated"] == 1


class TestSummaryAndHighlights:
    """Summary and highlight generation."""

    def test_click_summary_with_changes(self):
        events = [_ev(0, "click", ts=1000, target_text="Submit")]
        mutations = [_mut("m0", ts=1200)]
        result = build_steps("rec1", events, mutations)
        step = result["steps"][0]
        assert "Submit" in step["summary"]
        assert len(step["mutations"]["highlights"]) == 1

    def test_navigate_summary(self):
        events = [{
            "id": "e0",
            "type": "navigate",
            "timestamp": 1000,
            "url": "https://example.com/page",
            "title": "My Page",
        }]
        result = build_steps("rec1", events, [])
        assert "My Page" in result["steps"][0]["summary"]

    def test_change_area_from_mutation_area_label(self):
        events = [_ev(0, "click", ts=1000)]
        mutations = [
            _mut("m0", ts=1200, area_label="Prize Config"),
            _mut("m1", ts=1300, area_label="Prize Config"),
        ]
        result = build_steps("rec1", events, mutations)
        assert result["steps"][0]["change_area"] == "Prize Config"


class TestEndTimestamp:
    """end_timestamp reflects the latest mutation or event timestamp."""

    def test_end_timestamp_with_mutations(self):
        events = [_ev(0, "click", ts=1000)]
        mutations = [
            _mut("m0", ts=1200),
            _mut("m1", ts=1800),
        ]
        result = build_steps("rec1", events, mutations)
        assert result["steps"][0]["end_timestamp"] == 1800

    def test_end_timestamp_no_mutations(self):
        events = [_ev(0, "click", ts=1000)]
        result = build_steps("rec1", events, [])
        assert result["steps"][0]["end_timestamp"] == 1000
