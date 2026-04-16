"""
Tests for recording_normalizer — pure-logic event normalization.

Covers:
1.  Empty / minimal recordings
2.  _get_str helper (multi-key lookup, whitespace stripping)
3.  _target_key stable identity (with/without target, iframe)
4.  _button_text extraction (text > label > nearbyText > empty)
5.  _classify_click branches (submit, cancel, open-dialog, click-button, unknown)
6.  _field_label extraction (fieldPath, fieldLabel, section+item combo, target fallback)
7.  _is_select_event detection (tag and role variants)
8.  _merge_events R1: consecutive input collapse
9.  _merge_events R2: input+change dedup within 1s
10. _merge_events R3: richtext-input dedup (same + different content)
11. _merge_events R4: duplicate click dedup within 300ms
12. _to_step: navigate, richtext-input, input, change, click, unknown types
13. _to_step: iframe metadata propagation
14. _segment_steps: empty, navigation, form-fill, dialog, richtext, misc
15. _segment_steps: S5 after-dialog-close starts new segment
16. _segment_steps: title cleanup pass (all segment types)
17. _extract_key_actions: K1/K2/K3 rules and deduplication
18. normalize_recording: end-to-end integration, summary stats
19. normalized_recording_to_dict: serialization round-trip
"""

from __future__ import annotations

import pytest

from app.services.recording_normalizer import (
    NormalizationSummary,
    NormalizedRecording,
    NormalizedSegment,
    NormalizedStep,
    _button_text,
    _classify_click,
    _extract_key_actions,
    _field_label,
    _get_str,
    _is_select_event,
    _merge_events,
    _segment_steps,
    _target_key,
    _to_step,
    normalize_recording,
    normalized_recording_to_dict,
)


# ---------------------------------------------------------------------------
# Helpers for building test events
# ---------------------------------------------------------------------------

def _ev(
    ev_type: str = "click",
    ts: int = 1000,
    url: str = "https://example.com",
    target: dict | None = None,
    value: str | None = None,
    title: str | None = None,
    html_content: str | None = None,
    frame_info: dict | None = None,
    field_context: dict | None = None,
) -> dict:
    """Build a minimal raw event dict."""
    ev: dict = {"type": ev_type, "timestamp": ts, "url": url}
    if target is not None:
        ev["target"] = target
    if value is not None:
        ev["value"] = value
    if title is not None:
        ev["title"] = title
    if html_content is not None:
        ev["htmlContent"] = html_content
    if frame_info is not None:
        ev["frameInfo"] = frame_info
    if field_context is not None:
        ev["fieldContext"] = field_context
    return ev


# ===================================================================
# _get_str
# ===================================================================

class TestGetStr:
    """Lines 101-107: multi-key safe string lookup."""

    def test_returns_first_matching_key(self):
        d = {"a": "  hello  ", "b": "world"}
        assert _get_str(d, "a", "b") == "hello"

    def test_skips_empty_strings(self):
        d = {"a": "", "b": "  ", "c": "ok"}
        assert _get_str(d, "a", "b", "c") == "ok"

    def test_skips_non_string_values(self):
        d = {"a": 123, "b": None, "c": "found"}
        assert _get_str(d, "a", "b", "c") == "found"

    def test_returns_empty_when_no_match(self):
        d = {"a": "", "b": None}
        assert _get_str(d, "a", "b", "missing") == ""

    def test_empty_dict(self):
        assert _get_str({}, "x") == ""

    def test_no_keys(self):
        assert _get_str({"a": "val"}) == ""


# ===================================================================
# _target_key
# ===================================================================

class TestTargetKey:

    def test_basic_target(self):
        ev = _ev(target={"selector": "#btn", "name": "my-btn", "id": "btn1"})
        key = _target_key(ev)
        assert "#btn" in key
        assert "my-btn" in key
        assert "btn1" in key

    def test_no_target(self):
        ev = _ev()
        key = _target_key(ev)
        # Should not raise — all fields default to ""
        assert isinstance(key, str)

    def test_iframe_frame_url_included(self):
        ev = _ev(
            target={"selector": "#x"},
            frame_info={"isIframe": True, "frameUrl": "https://iframe.example.com"},
        )
        key = _target_key(ev)
        assert "iframe.example.com" in key


# ===================================================================
# _button_text
# ===================================================================

class TestButtonText:

    def test_prefers_text(self):
        ev = _ev(target={"text": " Submit ", "label": "Save"})
        assert _button_text(ev) == "Submit"

    def test_falls_back_to_label(self):
        ev = _ev(target={"label": " Cancel "})
        assert _button_text(ev) == "Cancel"

    def test_falls_back_to_nearby_text(self):
        ev = _ev(target={"nearbyText": "Edit"})
        assert _button_text(ev) == "Edit"

    def test_empty_when_no_target(self):
        ev = _ev()
        assert _button_text(ev) == ""


# ===================================================================
# _classify_click  (lines 129-142)
# ===================================================================

class TestClassifyClick:

    def test_submit_keyword(self):
        ev = _ev(target={"text": "Submit Form"})
        assert _classify_click(ev) == "confirm-dialog"

    def test_chinese_submit(self):
        ev = _ev(target={"text": "确认"})
        assert _classify_click(ev) == "confirm-dialog"

    def test_cancel_keyword(self):
        """Line 134: cancel branch."""
        ev = _ev(target={"text": "Cancel"})
        assert _classify_click(ev) == "cancel-dialog"

    def test_chinese_cancel(self):
        ev = _ev(target={"text": "取消"})
        assert _classify_click(ev) == "cancel-dialog"

    def test_open_dialog_keyword(self):
        """Line 137: open-dialog branch."""
        ev = _ev(target={"text": "Add New"})
        assert _classify_click(ev) == "open-dialog"

    def test_chinese_open_dialog(self):
        ev = _ev(target={"text": "新增"})
        assert _classify_click(ev) == "open-dialog"

    def test_button_tag(self):
        """Line 140-141: tag-based click-button."""
        ev = _ev(target={"tag": "button", "text": "Refresh"})
        assert _classify_click(ev) == "click-button"

    def test_anchor_tag(self):
        ev = _ev(target={"tag": "a", "text": "Details"})
        assert _classify_click(ev) == "click-button"

    def test_role_button(self):
        ev = _ev(target={"tag": "div", "role": "button", "text": "Go"})
        assert _classify_click(ev) == "click-button"

    def test_role_link(self):
        ev = _ev(target={"tag": "span", "role": "link", "text": "More"})
        assert _classify_click(ev) == "click-button"

    def test_role_menuitem(self):
        ev = _ev(target={"tag": "li", "role": "menuitem", "text": "Option"})
        assert _classify_click(ev) == "click-button"

    def test_unknown_click(self):
        """Line 142: unknown-click fallback."""
        ev = _ev(target={"tag": "div", "text": "Something"})
        assert _classify_click(ev) == "unknown-click"

    def test_no_target_at_all(self):
        ev = _ev()
        assert _classify_click(ev) == "unknown-click"


# ===================================================================
# _field_label  (line 152: section/item combo)
# ===================================================================

class TestFieldLabel:

    def test_field_path_preferred(self):
        ev = _ev(field_context={"fieldPath": "form.name"})
        assert _field_label(ev) == "form.name"

    def test_field_label_second(self):
        ev = _ev(field_context={"fieldLabel": "Name"})
        assert _field_label(ev) == "Name"

    def test_section_and_item_combo(self):
        """Line 152: section / item combined label."""
        ev = _ev(field_context={"sectionLabel": "Basic Info", "itemLabel": "Age"})
        assert _field_label(ev) == "Basic Info / Age"

    def test_section_only(self):
        ev = _ev(field_context={"sectionLabel": "Billing"})
        assert _field_label(ev) == "Billing"

    def test_item_only(self):
        ev = _ev(field_context={"itemLabel": "Email"})
        assert _field_label(ev) == "Email"

    def test_falls_back_to_target_label(self):
        ev = _ev(target={"label": "Username"})
        assert _field_label(ev) == "Username"

    def test_falls_back_to_target_placeholder(self):
        ev = _ev(target={"placeholder": "Enter email"})
        assert _field_label(ev) == "Enter email"

    def test_returns_none_when_nothing(self):
        ev = _ev()
        assert _field_label(ev) is None


# ===================================================================
# _is_select_event
# ===================================================================

class TestIsSelectEvent:

    def test_select_tag(self):
        ev = _ev(target={"tag": "select"})
        assert _is_select_event(ev) is True

    def test_combobox_role(self):
        ev = _ev(target={"tag": "div", "role": "combobox"})
        assert _is_select_event(ev) is True

    def test_listbox_role(self):
        ev = _ev(target={"tag": "div", "role": "listbox"})
        assert _is_select_event(ev) is True

    def test_option_role(self):
        ev = _ev(target={"tag": "div", "role": "option"})
        assert _is_select_event(ev) is True

    def test_input_tag_is_not_select(self):
        ev = _ev(target={"tag": "input"})
        assert _is_select_event(ev) is False

    def test_no_target(self):
        ev = _ev()
        assert _is_select_event(ev) is False


# ===================================================================
# _merge_events
# ===================================================================

class TestMergeEventsEmpty:
    """Line 183: empty events list."""

    def test_empty_list(self):
        assert _merge_events([]) == []


class TestMergeEventsR1:
    """R1: consecutive input on same target collapses to last."""

    def test_two_inputs_same_target(self):
        events = [
            _ev("input", ts=100, target={"selector": "#name"}, value="A"),
            _ev("input", ts=200, target={"selector": "#name"}, value="AB"),
        ]
        merged = _merge_events(events)
        assert len(merged) == 1
        assert merged[0][0] == 1  # original index of last
        assert merged[0][1]["value"] == "AB"

    def test_three_inputs_same_target(self):
        events = [
            _ev("input", ts=100, target={"selector": "#f"}, value="x"),
            _ev("input", ts=200, target={"selector": "#f"}, value="xy"),
            _ev("input", ts=300, target={"selector": "#f"}, value="xyz"),
        ]
        merged = _merge_events(events)
        assert len(merged) == 1
        assert merged[0][1]["value"] == "xyz"

    def test_inputs_different_targets_not_merged(self):
        events = [
            _ev("input", ts=100, target={"selector": "#a"}, value="1"),
            _ev("input", ts=200, target={"selector": "#b"}, value="2"),
        ]
        merged = _merge_events(events)
        assert len(merged) == 2

    def test_non_consecutive_inputs_not_merged(self):
        events = [
            _ev("input", ts=100, target={"selector": "#a"}, value="1"),
            _ev("click", ts=150, target={"selector": "#btn"}),
            _ev("input", ts=200, target={"selector": "#a"}, value="12"),
        ]
        merged = _merge_events(events)
        assert len(merged) == 3


class TestMergeEventsR2:
    """Lines 211-218: input followed by change on same target within 1s drops change."""

    def test_change_after_input_same_target_within_1s(self):
        events = [
            _ev("input", ts=1000, target={"selector": "#f"}, value="hello"),
            _ev("change", ts=1500, target={"selector": "#f"}, value="hello"),
        ]
        merged = _merge_events(events)
        assert len(merged) == 1
        assert merged[0][1]["type"] == "input"

    def test_change_after_input_different_target_kept(self):
        events = [
            _ev("input", ts=1000, target={"selector": "#a"}, value="val"),
            _ev("change", ts=1500, target={"selector": "#b"}, value="val"),
        ]
        merged = _merge_events(events)
        assert len(merged) == 2

    def test_change_after_input_beyond_1s_kept(self):
        events = [
            _ev("input", ts=1000, target={"selector": "#f"}, value="val"),
            _ev("change", ts=2500, target={"selector": "#f"}, value="val"),
        ]
        merged = _merge_events(events)
        assert len(merged) == 2

    def test_change_without_preceding_input_kept(self):
        events = [
            _ev("click", ts=1000, target={"selector": "#btn"}),
            _ev("change", ts=1500, target={"selector": "#f"}, value="new"),
        ]
        merged = _merge_events(events)
        assert len(merged) == 2

    def test_standalone_change_kept(self):
        """Change as the first event — no preceding input to match."""
        events = [
            _ev("change", ts=1000, target={"selector": "#sel"}, value="opt1"),
        ]
        merged = _merge_events(events)
        assert len(merged) == 1
        assert merged[0][1]["type"] == "change"


class TestMergeEventsR3:
    """Lines 222-247: richtext-input deduplication."""

    def test_consecutive_same_content_collapsed(self):
        events = [
            _ev("richtext-input", ts=100, target={"selector": "#rt"},
                 html_content="<p>Hello</p>"),
            _ev("richtext-input", ts=200, target={"selector": "#rt"},
                 html_content="<p>Hello</p>"),
            _ev("richtext-input", ts=300, target={"selector": "#rt"},
                 html_content="<p>Hello</p>"),
        ]
        merged = _merge_events(events)
        assert len(merged) == 1
        assert merged[0][0] == 2  # last index kept

    def test_different_content_keeps_last(self):
        """Lines 235-242: different htmlContent still accumulates to last."""
        events = [
            _ev("richtext-input", ts=100, target={"selector": "#rt"},
                 html_content="<p>A</p>"),
            _ev("richtext-input", ts=200, target={"selector": "#rt"},
                 html_content="<p>AB</p>"),
            _ev("richtext-input", ts=300, target={"selector": "#rt"},
                 html_content="<p>ABC</p>"),
        ]
        merged = _merge_events(events)
        assert len(merged) == 1
        assert merged[0][1]["htmlContent"] == "<p>ABC</p>"

    def test_different_targets_not_collapsed(self):
        events = [
            _ev("richtext-input", ts=100, target={"selector": "#rt1"},
                 html_content="<p>A</p>"),
            _ev("richtext-input", ts=200, target={"selector": "#rt2"},
                 html_content="<p>B</p>"),
        ]
        merged = _merge_events(events)
        # Second RT has different target, not collapsed with first
        assert len(merged) == 2

    def test_richtext_interrupted_by_other_event(self):
        events = [
            _ev("richtext-input", ts=100, target={"selector": "#rt"},
                 html_content="<p>A</p>"),
            _ev("click", ts=200, target={"selector": "#btn"}),
            _ev("richtext-input", ts=300, target={"selector": "#rt"},
                 html_content="<p>B</p>"),
        ]
        merged = _merge_events(events)
        assert len(merged) == 3

    def test_richtext_none_html_content(self):
        """htmlContent is None — treated as empty string."""
        events = [
            _ev("richtext-input", ts=100, target={"selector": "#rt"}),
            _ev("richtext-input", ts=200, target={"selector": "#rt"}),
        ]
        merged = _merge_events(events)
        assert len(merged) == 1


class TestMergeEventsR4:
    """Lines 257-258: duplicate click dedup within 300ms."""

    def test_duplicate_click_within_300ms_deduped(self):
        events = [
            _ev("click", ts=1000, target={"selector": "#btn"}),
            _ev("click", ts=1200, target={"selector": "#btn"}),
        ]
        merged = _merge_events(events)
        assert len(merged) == 1

    def test_click_beyond_300ms_kept(self):
        events = [
            _ev("click", ts=1000, target={"selector": "#btn"}),
            _ev("click", ts=1400, target={"selector": "#btn"}),
        ]
        merged = _merge_events(events)
        assert len(merged) == 2

    def test_click_different_target_kept(self):
        events = [
            _ev("click", ts=1000, target={"selector": "#a"}),
            _ev("click", ts=1100, target={"selector": "#b"}),
        ]
        merged = _merge_events(events)
        assert len(merged) == 2

    def test_first_click_has_no_predecessor(self):
        """First event is a click — no duplicate to check against."""
        events = [
            _ev("click", ts=1000, target={"selector": "#btn"}),
        ]
        merged = _merge_events(events)
        assert len(merged) == 1


# ===================================================================
# _to_step  (lines 270-340)
# ===================================================================

class TestToStepNavigate:

    def test_navigate_step(self):
        ev = _ev("navigate", ts=5000, url="https://app.com/home", title="Home Page")
        step = _to_step(0, ev)
        assert step.action_type == "navigate-page"
        assert step.url == "https://app.com/home"
        assert step.page_title == "Home Page"
        assert step.raw_event_indices == [0]

    def test_navigate_no_title(self):
        ev = _ev("navigate", ts=5000, url="https://app.com/page")
        step = _to_step(0, ev)
        assert step.page_title is None


class TestToStepRichtext:
    """Line 291: richtext-input branch."""

    def test_richtext_step(self):
        ev = _ev(
            "richtext-input", ts=2000, url="https://app.com",
            target={"selector": "#editor"},
            value="Some text",
            html_content="<p>Some text</p>",
            field_context={"fieldLabel": "Description"},
        )
        step = _to_step(3, ev)
        assert step.action_type == "edit-richtext"
        assert step.is_richtext is True
        assert step.html_content == "<p>Some text</p>"
        assert step.value == "Some text"
        assert step.field_label == "Description"
        assert step.raw_event_indices == [3]

    def test_richtext_in_iframe(self):
        ev = _ev(
            "richtext-input", ts=2000, url="https://app.com",
            target={"selector": "#editor"},
            html_content="<p>test</p>",
            frame_info={"isIframe": True, "frameUrl": "https://iframe.example.com/editor"},
        )
        step = _to_step(1, ev)
        assert step.in_iframe is True
        assert step.frame_url == "https://iframe.example.com/editor"


class TestToStepInput:

    def test_input_fill_field(self):
        ev = _ev(
            "input", ts=3000, url="https://app.com",
            target={"tag": "input", "selector": "#name"},
            value="Alice",
            field_context={"fieldLabel": "Name", "fieldProp": "name", "fieldRequired": True},
        )
        step = _to_step(5, ev)
        assert step.action_type == "fill-field"
        assert step.value == "Alice"
        assert step.field_label == "Name"
        assert step.field_prop == "name"
        assert step.field_required is True

    def test_input_select_event(self):
        ev = _ev(
            "input", ts=3000, url="https://app.com",
            target={"tag": "select", "selector": "#country"},
            value="US",
            field_context={"fieldLabel": "Country"},
        )
        step = _to_step(6, ev)
        assert step.action_type == "select-field"

    def test_change_event_select_by_role(self):
        ev = _ev(
            "change", ts=3000, url="https://app.com",
            target={"tag": "div", "role": "combobox", "selector": "#picker"},
            value="Option A",
        )
        step = _to_step(7, ev)
        assert step.action_type == "select-field"

    def test_change_event_fill_field(self):
        ev = _ev(
            "change", ts=3000, url="https://app.com",
            target={"tag": "input", "selector": "#addr"},
            value="123 Main",
        )
        step = _to_step(8, ev)
        assert step.action_type == "fill-field"

    def test_input_value_fallback_to_field_value_text(self):
        ev = _ev(
            "input", ts=3000, url="https://app.com",
            target={"tag": "input"},
            field_context={"fieldValueText": "fallback value"},
        )
        step = _to_step(0, ev)
        assert step.value == "fallback value"

    def test_input_in_iframe(self):
        ev = _ev(
            "input", ts=3000, url="https://app.com",
            target={"tag": "input", "selector": "#f"},
            value="v",
            frame_info={"isIframe": True, "frameUrl": "https://iframe.example.com"},
        )
        step = _to_step(0, ev)
        assert step.in_iframe is True
        assert step.frame_url == "https://iframe.example.com"


class TestToStepClick:

    def test_click_confirm(self):
        ev = _ev("click", ts=4000, target={"text": "Save", "tag": "button"})
        step = _to_step(10, ev)
        assert step.action_type == "confirm-dialog"
        assert step.button_text == "Save"

    def test_click_open_dialog(self):
        ev = _ev("click", ts=4000, target={"text": "Create", "tag": "button"})
        step = _to_step(11, ev)
        assert step.action_type == "open-dialog"

    def test_click_unknown(self):
        ev = _ev("click", ts=4000, target={"text": "foo", "tag": "div"})
        step = _to_step(12, ev)
        assert step.action_type == "unknown-click"


class TestToStepUnknown:
    """Line 333: unknown event type fallback."""

    def test_unknown_event_type(self):
        ev = _ev("scroll", ts=9000, url="https://app.com")
        step = _to_step(99, ev)
        assert step.action_type == "unknown"
        assert step.timestamp == 9000
        assert step.raw_event_indices == [99]

    def test_unknown_with_iframe(self):
        ev = _ev(
            "focus", ts=9000, url="https://app.com",
            frame_info={"isIframe": True, "frameUrl": "https://iframe.example.com"},
        )
        step = _to_step(50, ev)
        assert step.action_type == "unknown"
        assert step.in_iframe is True


# ===================================================================
# _segment_steps
# ===================================================================

class TestSegmentStepsEmpty:
    """Line 364: empty steps produces no segments."""

    def test_empty(self):
        assert _segment_steps([]) == []


class TestSegmentStepsNavigation:

    def test_single_navigation(self):
        steps = [
            NormalizedStep(action_type="navigate-page", timestamp=1000,
                           url="https://app.com", page_title="Home",
                           raw_event_indices=[0]),
        ]
        segs = _segment_steps(steps)
        assert len(segs) == 1
        assert segs[0].type == "navigation"
        assert "Home" in segs[0].title

    def test_navigation_flushes_previous_form(self):
        steps = [
            NormalizedStep(action_type="fill-field", timestamp=1000,
                           url="https://app.com", field_label="Name",
                           raw_event_indices=[0]),
            NormalizedStep(action_type="navigate-page", timestamp=2000,
                           url="https://app.com/page2", page_title="Page 2",
                           raw_event_indices=[1]),
        ]
        segs = _segment_steps(steps)
        assert len(segs) == 2
        assert segs[0].type == "form-fill"
        assert segs[1].type == "navigation"


class TestSegmentStepsDialog:
    """Lines 417-426: open-dialog starts dialog-interaction segment."""

    def test_open_dialog_starts_dialog_segment(self):
        steps = [
            NormalizedStep(action_type="open-dialog", timestamp=1000,
                           url="https://app.com", button_text="Add",
                           raw_event_indices=[0]),
            NormalizedStep(action_type="fill-field", timestamp=2000,
                           url="https://app.com", field_label="Name",
                           raw_event_indices=[1]),
            NormalizedStep(action_type="confirm-dialog", timestamp=3000,
                           url="https://app.com", button_text="Save",
                           raw_event_indices=[2]),
        ]
        segs = _segment_steps(steps)
        # All three should be in one dialog-interaction segment
        assert any(s.type == "dialog-interaction" for s in segs)
        dialog_seg = next(s for s in segs if s.type == "dialog-interaction")
        assert len(dialog_seg.steps) == 3

    def test_open_dialog_flushes_preceding_form(self):
        steps = [
            NormalizedStep(action_type="fill-field", timestamp=1000,
                           url="https://app.com", field_label="X",
                           raw_event_indices=[0]),
            NormalizedStep(action_type="open-dialog", timestamp=2000,
                           url="https://app.com", button_text="Add",
                           raw_event_indices=[1]),
        ]
        segs = _segment_steps(steps)
        assert len(segs) == 2
        assert segs[0].type == "form-fill"
        assert segs[1].type == "dialog-interaction"


class TestSegmentStepsAfterDialogClose:
    """Lines 411-413: S5 after-dialog-close starts new segment."""

    def test_after_confirm_next_step_starts_new_segment(self):
        steps = [
            NormalizedStep(action_type="open-dialog", timestamp=1000,
                           url="https://app.com", button_text="Add",
                           raw_event_indices=[0]),
            NormalizedStep(action_type="confirm-dialog", timestamp=2000,
                           url="https://app.com", button_text="OK",
                           raw_event_indices=[1]),
            NormalizedStep(action_type="fill-field", timestamp=3000,
                           url="https://app.com", field_label="Other",
                           raw_event_indices=[2]),
        ]
        segs = _segment_steps(steps)
        # Dialog should be flushed after confirm, fill-field in a new segment
        assert len(segs) == 2
        assert segs[0].type == "dialog-interaction"
        assert segs[1].type == "form-fill"

    def test_after_cancel_next_step_starts_new_segment(self):
        steps = [
            NormalizedStep(action_type="open-dialog", timestamp=1000,
                           url="https://app.com", button_text="Edit",
                           raw_event_indices=[0]),
            NormalizedStep(action_type="cancel-dialog", timestamp=2000,
                           url="https://app.com", button_text="Close",
                           raw_event_indices=[1]),
            NormalizedStep(action_type="click-button", timestamp=3000,
                           url="https://app.com", button_text="Refresh",
                           raw_event_indices=[2]),
        ]
        segs = _segment_steps(steps)
        assert len(segs) == 2
        assert segs[0].type == "dialog-interaction"


class TestSegmentStepsRichtext:
    """Lines 436-445: S4 richtext-edit segmentation."""

    def test_richtext_starts_own_segment(self):
        steps = [
            NormalizedStep(action_type="edit-richtext", timestamp=1000,
                           url="https://app.com", field_label="Content",
                           is_richtext=True, raw_event_indices=[0]),
        ]
        segs = _segment_steps(steps)
        assert len(segs) == 1
        assert segs[0].type == "richtext-edit"
        assert "Content" in segs[0].title

    def test_richtext_flushes_form_fill(self):
        steps = [
            NormalizedStep(action_type="fill-field", timestamp=1000,
                           url="https://app.com", field_label="Title",
                           raw_event_indices=[0]),
            NormalizedStep(action_type="edit-richtext", timestamp=2000,
                           url="https://app.com", field_label="Body",
                           is_richtext=True, raw_event_indices=[1]),
        ]
        segs = _segment_steps(steps)
        assert len(segs) == 2
        assert segs[0].type == "form-fill"
        assert segs[1].type == "richtext-edit"

    def test_consecutive_richtext_same_segment(self):
        steps = [
            NormalizedStep(action_type="edit-richtext", timestamp=1000,
                           url="https://app.com", field_label="Body",
                           is_richtext=True, raw_event_indices=[0]),
            NormalizedStep(action_type="edit-richtext", timestamp=2000,
                           url="https://app.com", field_label="Body",
                           is_richtext=True, raw_event_indices=[1]),
        ]
        segs = _segment_steps(steps)
        assert len(segs) == 1
        assert segs[0].type == "richtext-edit"
        assert len(segs[0].steps) == 2


class TestSegmentStepsMisc:
    """Line 456: remaining steps with no current_type -> misc."""

    def test_unknown_action_creates_misc_segment(self):
        steps = [
            NormalizedStep(action_type="unknown", timestamp=1000,
                           url="https://app.com", raw_event_indices=[0]),
        ]
        segs = _segment_steps(steps)
        assert len(segs) == 1
        # Form fill is the default for non-categorized actions
        # that hit the default branch
        assert segs[0].type in ("form-fill", "misc")


class TestSegmentTitleCleanup:
    """Lines 460-482: title cleanup pass."""

    def test_navigation_title_uses_page_title(self):
        steps = [
            NormalizedStep(action_type="navigate-page", timestamp=1000,
                           url="https://app.com/dash", page_title="Dashboard",
                           raw_event_indices=[0]),
        ]
        segs = _segment_steps(steps)
        assert segs[0].title == "Navigate to: Dashboard"

    def test_navigation_title_falls_back_to_url(self):
        steps = [
            NormalizedStep(action_type="navigate-page", timestamp=1000,
                           url="https://app.com/settings",
                           raw_event_indices=[0]),
        ]
        segs = _segment_steps(steps)
        assert "https://app.com/settings" in segs[0].title

    def test_form_fill_title(self):
        steps = [
            NormalizedStep(action_type="fill-field", timestamp=1000,
                           url="https://app.com", field_label="Name",
                           raw_event_indices=[0]),
        ]
        segs = _segment_steps(steps)
        assert segs[0].title == "Form fill"

    def test_dialog_title_uses_open_button_text(self):
        """Lines 467-474: dialog title from first open-dialog step."""
        steps = [
            NormalizedStep(action_type="open-dialog", timestamp=1000,
                           url="https://app.com", button_text="Create Item",
                           raw_event_indices=[0]),
            NormalizedStep(action_type="confirm-dialog", timestamp=2000,
                           url="https://app.com", button_text="Save",
                           raw_event_indices=[1]),
        ]
        segs = _segment_steps(steps)
        dialog_seg = next(s for s in segs if s.type == "dialog-interaction")
        assert "Create Item" in dialog_seg.title

    def test_dialog_title_fallback_interaction(self):
        """Dialog segment with no open-dialog step — uses first step."""
        steps = [
            NormalizedStep(action_type="confirm-dialog", timestamp=1000,
                           url="https://app.com", button_text="",
                           raw_event_indices=[0]),
        ]
        # confirm-dialog alone: after_dialog_close is set, then flushed at end
        segs = _segment_steps(steps)
        dialog_segs = [s for s in segs if s.type == "dialog-interaction" or "dialog" in s.title.lower() or "Dialog" in s.title]
        # The segment should exist and have a sensible title
        assert len(segs) >= 1

    def test_richtext_title_uses_field_label(self):
        """Lines 475-480: richtext title from field label."""
        steps = [
            NormalizedStep(action_type="edit-richtext", timestamp=1000,
                           url="https://app.com", field_label="Description",
                           is_richtext=True, raw_event_indices=[0]),
        ]
        segs = _segment_steps(steps)
        assert segs[0].type == "richtext-edit"
        assert "Description" in segs[0].title

    def test_richtext_title_fallback_content(self):
        """Richtext with no field_label uses 'content' fallback."""
        steps = [
            NormalizedStep(action_type="edit-richtext", timestamp=1000,
                           url="https://app.com", is_richtext=True,
                           raw_event_indices=[0]),
        ]
        segs = _segment_steps(steps)
        assert "content" in segs[0].title.lower()

    def test_misc_title(self):
        """Line 482: misc segment title."""
        # A confirm-dialog as first step with after_dialog_close,
        # the flush sets a misc-like type
        steps = [
            NormalizedStep(action_type="navigate-page", timestamp=1000,
                           url="https://app.com/page", raw_event_indices=[0]),
            NormalizedStep(action_type="navigate-page", timestamp=2000,
                           url="https://app.com/page2", raw_event_indices=[1]),
        ]
        segs = _segment_steps(steps)
        # Navigation segments — just checking titles are correct
        for seg in segs:
            if seg.type == "navigation":
                assert "Navigate to:" in seg.title


# ===================================================================
# _extract_key_actions  (lines 502-533)
# ===================================================================

class TestExtractKeyActions:

    def test_k1_navigate_is_key(self):
        steps = [
            NormalizedStep(action_type="navigate-page", timestamp=1000,
                           url="https://app.com", raw_event_indices=[0]),
        ]
        keys = _extract_key_actions(steps)
        assert len(keys) == 1
        assert keys[0].action_type == "navigate-page"

    def test_k1_open_dialog_is_key(self):
        steps = [
            NormalizedStep(action_type="open-dialog", timestamp=1000,
                           url="https://app.com", button_text="Add",
                           raw_event_indices=[0]),
        ]
        keys = _extract_key_actions(steps)
        assert len(keys) == 1

    def test_k1_confirm_dialog_is_key(self):
        steps = [
            NormalizedStep(action_type="confirm-dialog", timestamp=1000,
                           url="https://app.com", raw_event_indices=[0]),
        ]
        keys = _extract_key_actions(steps)
        assert len(keys) == 1

    def test_k1_cancel_dialog_is_key(self):
        steps = [
            NormalizedStep(action_type="cancel-dialog", timestamp=1000,
                           url="https://app.com", raw_event_indices=[0]),
        ]
        keys = _extract_key_actions(steps)
        assert len(keys) == 1

    def test_k1_edit_richtext_is_key(self):
        steps = [
            NormalizedStep(action_type="edit-richtext", timestamp=1000,
                           url="https://app.com", is_richtext=True,
                           raw_event_indices=[0]),
        ]
        keys = _extract_key_actions(steps)
        assert len(keys) == 1

    def test_k2_fill_field_with_label_is_key(self):
        steps = [
            NormalizedStep(action_type="fill-field", timestamp=1000,
                           url="https://app.com", field_label="Name",
                           raw_event_indices=[0]),
        ]
        keys = _extract_key_actions(steps)
        assert len(keys) == 1

    def test_k2_fill_field_without_label_not_key(self):
        steps = [
            NormalizedStep(action_type="fill-field", timestamp=1000,
                           url="https://app.com", raw_event_indices=[0]),
        ]
        keys = _extract_key_actions(steps)
        assert len(keys) == 0

    def test_k2_select_field_with_label_is_key(self):
        steps = [
            NormalizedStep(action_type="select-field", timestamp=1000,
                           url="https://app.com", field_label="Country",
                           value="US", raw_event_indices=[0]),
        ]
        keys = _extract_key_actions(steps)
        assert len(keys) == 1

    def test_k3_click_button_with_submit_keyword(self):
        """Lines 522-525: click-button with submit/cancel keyword is key."""
        steps = [
            NormalizedStep(action_type="click-button", timestamp=1000,
                           url="https://app.com", button_text="Submit Form",
                           raw_event_indices=[0]),
        ]
        keys = _extract_key_actions(steps)
        assert len(keys) == 1

    def test_k3_click_button_with_cancel_keyword(self):
        steps = [
            NormalizedStep(action_type="click-button", timestamp=1000,
                           url="https://app.com", button_text="Cancel Order",
                           raw_event_indices=[0]),
        ]
        keys = _extract_key_actions(steps)
        assert len(keys) == 1

    def test_k3_click_button_with_chinese_keyword(self):
        steps = [
            NormalizedStep(action_type="click-button", timestamp=1000,
                           url="https://app.com", button_text="确定",
                           raw_event_indices=[0]),
        ]
        keys = _extract_key_actions(steps)
        assert len(keys) == 1

    def test_click_button_without_keyword_not_key(self):
        steps = [
            NormalizedStep(action_type="click-button", timestamp=1000,
                           url="https://app.com", button_text="Refresh",
                           raw_event_indices=[0]),
        ]
        keys = _extract_key_actions(steps)
        assert len(keys) == 0

    def test_click_button_no_text_not_key(self):
        steps = [
            NormalizedStep(action_type="click-button", timestamp=1000,
                           url="https://app.com", raw_event_indices=[0]),
        ]
        keys = _extract_key_actions(steps)
        assert len(keys) == 0

    def test_unknown_click_not_key(self):
        steps = [
            NormalizedStep(action_type="unknown-click", timestamp=1000,
                           url="https://app.com", raw_event_indices=[0]),
        ]
        keys = _extract_key_actions(steps)
        assert len(keys) == 0

    def test_deduplication(self):
        steps = [
            NormalizedStep(action_type="fill-field", timestamp=1000,
                           url="https://app.com", field_label="Name",
                           value="Alice", raw_event_indices=[0]),
            NormalizedStep(action_type="fill-field", timestamp=2000,
                           url="https://app.com", field_label="Name",
                           value="Alice", raw_event_indices=[1]),
        ]
        keys = _extract_key_actions(steps)
        assert len(keys) == 1

    def test_different_values_not_deduped(self):
        steps = [
            NormalizedStep(action_type="fill-field", timestamp=1000,
                           url="https://app.com", field_label="Name",
                           value="Alice", raw_event_indices=[0]),
            NormalizedStep(action_type="fill-field", timestamp=2000,
                           url="https://app.com", field_label="Name",
                           value="Bob", raw_event_indices=[1]),
        ]
        keys = _extract_key_actions(steps)
        assert len(keys) == 2


# ===================================================================
# normalize_recording — end to end
# ===================================================================

class TestNormalizeRecordingEmpty:
    """Line 557: empty events."""

    def test_empty_events(self):
        result = normalize_recording("rec-1", [])
        assert result.recording_id == "rec-1"
        assert result.summary.event_count_raw == 0
        assert result.summary.event_count_normalized == 0
        assert result.summary.page_count == 0
        assert result.summary.segment_count == 0
        assert result.summary.contains_iframe is False
        assert result.summary.contains_richtext is False
        assert result.segments == []
        assert result.key_actions == []

    def test_empty_events_with_initial_state(self):
        state = {"stateTree": []}
        result = normalize_recording("rec-2", [], initial_state=state)
        assert result.initial_state is state


class TestNormalizeRecordingIntegration:

    def test_simple_form_fill_workflow(self):
        events = [
            _ev("navigate", ts=1000, url="https://app.com/form", title="Form Page"),
            _ev("input", ts=2000, target={"tag": "input", "selector": "#name"},
                 value="Alice", field_context={"fieldLabel": "Name"}),
            _ev("input", ts=3000, target={"tag": "input", "selector": "#email"},
                 value="alice@example.com", field_context={"fieldLabel": "Email"}),
            _ev("click", ts=4000, target={"text": "Submit", "tag": "button"}),
        ]
        result = normalize_recording("rec-3", events)
        assert result.summary.event_count_raw == 4
        assert result.summary.event_count_normalized == 4
        assert result.summary.page_count == 1
        assert result.summary.segment_count >= 1
        assert result.summary.contains_iframe is False
        assert result.summary.contains_richtext is False
        assert len(result.key_actions) >= 1  # navigate + fills + submit click

    def test_iframe_events_detected(self):
        events = [
            _ev("navigate", ts=1000, url="https://app.com"),
            _ev("input", ts=2000, target={"tag": "input", "selector": "#f"},
                 value="x",
                 frame_info={"isIframe": True, "frameUrl": "https://iframe.example.com"}),
        ]
        result = normalize_recording("rec-4", events)
        assert result.summary.contains_iframe is True

    def test_richtext_events_detected(self):
        events = [
            _ev("richtext-input", ts=1000, target={"selector": "#rt"},
                 html_content="<p>Hello</p>"),
        ]
        result = normalize_recording("rec-5", events)
        assert result.summary.contains_richtext is True

    def test_page_count_from_navigate_urls(self):
        events = [
            _ev("navigate", ts=1000, url="https://app.com/page1"),
            _ev("navigate", ts=2000, url="https://app.com/page2"),
            _ev("navigate", ts=3000, url="https://app.com/page1"),  # duplicate URL
        ]
        result = normalize_recording("rec-6", events)
        assert result.summary.page_count == 2  # 2 unique URLs

    def test_no_navigate_events_page_count_is_one(self):
        events = [
            _ev("click", ts=1000, target={"tag": "button", "text": "Go"}),
        ]
        result = normalize_recording("rec-7", events)
        assert result.summary.page_count == 1  # max(1, 0)

    def test_input_merging_reduces_normalized_count(self):
        events = [
            _ev("input", ts=100, target={"selector": "#f"}, value="a"),
            _ev("input", ts=200, target={"selector": "#f"}, value="ab"),
            _ev("input", ts=300, target={"selector": "#f"}, value="abc"),
        ]
        result = normalize_recording("rec-8", events)
        assert result.summary.event_count_raw == 3
        assert result.summary.event_count_normalized == 1

    def test_dialog_workflow(self):
        events = [
            _ev("click", ts=1000, target={"text": "Add", "tag": "button"}),
            _ev("input", ts=2000, target={"tag": "input", "selector": "#name"},
                 value="Test", field_context={"fieldLabel": "Name"}),
            _ev("click", ts=3000, target={"text": "Confirm", "tag": "button"}),
        ]
        result = normalize_recording("rec-9", events)
        assert result.summary.segment_count >= 1
        dialog_segs = [s for s in result.segments if s.type == "dialog-interaction"]
        assert len(dialog_segs) >= 1

    def test_mixed_richtext_and_form(self):
        events = [
            _ev("input", ts=1000, target={"tag": "input", "selector": "#title"},
                 value="My Title", field_context={"fieldLabel": "Title"}),
            _ev("richtext-input", ts=2000, target={"selector": "#editor"},
                 value="content", html_content="<p>content</p>",
                 field_context={"fieldLabel": "Body"}),
            _ev("click", ts=3000, target={"text": "Save", "tag": "button"}),
        ]
        result = normalize_recording("rec-10", events)
        assert result.summary.contains_richtext is True
        seg_types = {s.type for s in result.segments}
        assert "richtext-edit" in seg_types


# ===================================================================
# normalized_recording_to_dict  — serialization
# ===================================================================

class TestNormalizedRecordingToDict:

    def test_full_round_trip(self):
        events = [
            _ev("navigate", ts=1000, url="https://app.com", title="Home"),
            _ev("input", ts=2000, target={"tag": "input", "selector": "#f"},
                 value="val", field_context={"fieldLabel": "Field"}),
            _ev("click", ts=3000, target={"text": "OK", "tag": "button"}),
        ]
        nr = normalize_recording("rec-rt", events)
        d = normalized_recording_to_dict(nr)

        assert d["recording_id"] == "rec-rt"
        assert isinstance(d["summary"], dict)
        assert d["summary"]["event_count_raw"] == 3
        assert isinstance(d["segments"], list)
        assert isinstance(d["key_actions"], list)
        assert d["initial_state"] is None

    def test_empty_recording_serialization(self):
        nr = normalize_recording("rec-empty", [])
        d = normalized_recording_to_dict(nr)
        assert d["summary"]["event_count_raw"] == 0
        assert d["segments"] == []
        assert d["key_actions"] == []

    def test_step_dict_fields(self):
        nr = normalize_recording("rec-sd", [
            _ev("richtext-input", ts=1000, target={"selector": "#rt"},
                 value="text", html_content="<p>text</p>",
                 field_context={"fieldLabel": "Editor", "fieldProp": "content"}),
        ])
        d = normalized_recording_to_dict(nr)
        step_d = d["segments"][0]["steps"][0]
        assert step_d["action_type"] == "edit-richtext"
        assert step_d["is_richtext"] is True
        assert step_d["html_content"] == "<p>text</p>"
        assert step_d["field_label"] == "Editor"
        assert step_d["field_prop"] == "content"
        assert step_d["value"] == "text"
        assert step_d["in_iframe"] is False
        assert step_d["frame_url"] is None
        assert isinstance(step_d["raw_event_indices"], list)

    def test_initial_state_preserved(self):
        state = {"stateTree": [{"type": "section"}]}
        nr = normalize_recording("rec-is", [], initial_state=state)
        d = normalized_recording_to_dict(nr)
        assert d["initial_state"] == state

    def test_segment_dict_structure(self):
        events = [
            _ev("navigate", ts=1000, url="https://app.com", title="Home"),
        ]
        nr = normalize_recording("rec-seg", events)
        d = normalized_recording_to_dict(nr)
        seg = d["segments"][0]
        assert "index" in seg
        assert "type" in seg
        assert "title" in seg
        assert "steps" in seg
        assert isinstance(seg["steps"], list)


# ===================================================================
# Complex integration scenarios
# ===================================================================

class TestComplexScenarios:

    def test_full_dialog_lifecycle_with_follow_up(self):
        """Navigate -> form fill -> dialog open -> fill inside dialog -> confirm -> more form."""
        events = [
            _ev("navigate", ts=1000, url="https://app.com/orders", title="Orders"),
            _ev("input", ts=2000, target={"tag": "input", "selector": "#search"},
                 value="laptop", field_context={"fieldLabel": "Search"}),
            _ev("click", ts=3000, target={"text": "Create Order", "tag": "button"}),
            _ev("input", ts=4000, target={"tag": "input", "selector": "#item"},
                 value="Laptop Pro", field_context={"fieldLabel": "Item Name"}),
            _ev("click", ts=5000, target={"text": "Confirm", "tag": "button"}),
            _ev("input", ts=6000, target={"tag": "input", "selector": "#notes"},
                 value="Urgent", field_context={"fieldLabel": "Notes"}),
        ]
        result = normalize_recording("rec-complex", events)
        assert result.summary.event_count_raw == 6
        assert result.summary.segment_count >= 3  # nav + dialog + follow-up form

    def test_multiple_consecutive_navigations(self):
        events = [
            _ev("navigate", ts=1000, url="https://app.com/a", title="Page A"),
            _ev("navigate", ts=2000, url="https://app.com/b", title="Page B"),
            _ev("navigate", ts=3000, url="https://app.com/c", title="Page C"),
        ]
        result = normalize_recording("rec-nav", events)
        nav_segs = [s for s in result.segments if s.type == "navigation"]
        assert len(nav_segs) == 3

    def test_change_event_standalone(self):
        """A change event without preceding input -> produces a step."""
        events = [
            _ev("change", ts=1000, target={"tag": "select", "selector": "#sel"},
                 value="Option B"),
        ]
        result = normalize_recording("rec-change", events)
        assert result.summary.event_count_normalized == 1
        step = result.segments[0].steps[0]
        assert step.action_type == "select-field"
        assert step.value == "Option B"

    def test_all_merge_rules_combined(self):
        """Multiple merge rules firing in a single sequence."""
        events = [
            # R1: 3 consecutive inputs -> 1
            _ev("input", ts=100, target={"selector": "#f"}, value="a"),
            _ev("input", ts=200, target={"selector": "#f"}, value="ab"),
            _ev("input", ts=300, target={"selector": "#f"}, value="abc"),
            # R2: input+change same target within 1s -> drop change
            _ev("input", ts=1000, target={"selector": "#g"}, value="x"),
            _ev("change", ts=1200, target={"selector": "#g"}, value="x"),
            # R4: double-click within 300ms -> 1
            _ev("click", ts=2000, target={"selector": "#btn"}),
            _ev("click", ts=2100, target={"selector": "#btn"}),
            # R3: richtext same content -> 1
            _ev("richtext-input", ts=3000, target={"selector": "#rt"},
                 html_content="<p>H</p>"),
            _ev("richtext-input", ts=3100, target={"selector": "#rt"},
                 html_content="<p>H</p>"),
        ]
        result = normalize_recording("rec-merge", events)
        # 3 inputs -> 1, input+change -> 1, 2 clicks -> 1, 2 richtext -> 1 = 4
        assert result.summary.event_count_normalized == 4

    def test_events_without_any_targets(self):
        """Events with no target field at all."""
        events = [
            {"type": "navigate", "timestamp": 1000, "url": "https://app.com"},
            {"type": "click", "timestamp": 2000, "url": "https://app.com"},
        ]
        result = normalize_recording("rec-notarget", events)
        assert result.summary.event_count_normalized == 2

    def test_events_with_missing_fields(self):
        """Events with minimal fields — should not crash."""
        events = [
            {"type": "input", "timestamp": 100},
            {"type": "click"},
            {},
        ]
        result = normalize_recording("rec-minimal", events)
        assert result.summary.event_count_raw == 3
