"""Tests for the planner's toggle_values path (Phase 9 radio support).

Covers three layers:

1. ``extract_group_label`` — the id-less fallback used when a radio /
   checkbox has no self-id and needs to inherit the form-item label.
2. ``_infer_semantic_role`` — now runs for toggles and folds label_text
   into its hint pool.
3. ``_match_toggle_for_role`` + ``plan_actions`` — strict value
   matching, label fallback, and integration with the existing
   multi-field fill path.
"""

from __future__ import annotations

from app.schemas.page_analysis import DiscoveredElement, PageAnalysis
from app.services.analysis.form_label_extractor import extract_group_label
from app.services.learning.action_planner import (
    _describe,
    _match_toggle_for_role,
    plan_actions,
)
from app.services.learning.page_analyzer import _infer_semantic_role, _to_discovered

# ───────────────────────────────────────────────────────────────────
# extract_group_label
# ───────────────────────────────────────────────────────────────────


ANT_STATUS_RADIO_GROUP_HTML = """
<div class="ant-row ant-form-item-row">
  <div class="ant-col ant-form-item-label">
    <label title="Status">Status</label>
  </div>
  <div class="ant-col ant-form-item-control">
    <div class="ant-radio-group" id="search-status">
      <label class="ant-radio-wrapper">
        <span class="ant-radio">
          <input type="radio" class="ant-radio-input" value="">
        </span>
        <span>All</span>
      </label>
      <label class="ant-radio-wrapper">
        <span class="ant-radio">
          <input type="radio" class="ant-radio-input" value="active">
        </span>
        <span>Active</span>
      </label>
    </div>
  </div>
</div>
"""


def test_extract_group_label_ant_design() -> None:
    result = extract_group_label(ANT_STATUS_RADIO_GROUP_HTML)
    assert result.text == "Status"
    assert result.source == "ant-design-group"


def test_extract_group_label_empty_wrapper() -> None:
    result = extract_group_label("")
    assert result.text is None
    assert result.source is None


def test_extract_group_label_ignores_plain_div() -> None:
    result = extract_group_label("<div><input type='radio' value='x'></div>")
    assert result.text is None


def test_extract_group_label_generic_form_item() -> None:
    html = """
    <div class="el-form-item">
      <label class="el-form-item__label">角色</label>
      <div class="el-form-item__content">
        <input type="radio" value="admin">
      </div>
    </div>
    """
    result = extract_group_label(html)
    assert result.text == "角色"
    assert result.source == "generic-group"


# ───────────────────────────────────────────────────────────────────
# _infer_semantic_role — toggle category
# ───────────────────────────────────────────────────────────────────


def _raw(**overrides: object) -> dict:
    base = {
        "tag": "input",
        "type": "radio",
        "id": None,
        "name": None,
        "placeholder": None,
        "ariaLabel": None,
    }
    base.update(overrides)
    return base


def test_toggle_inherits_role_from_label_text() -> None:
    # Radio with no self-identifier relies on the form-item label.
    assert (
        _infer_semantic_role(_raw(), "toggle", label_text="Status")
        == "status"
    )


def test_toggle_inherits_role_from_label_text_zh() -> None:
    assert _infer_semantic_role(_raw(), "toggle", label_text="角色") == "role"


def test_toggle_without_hints_returns_none() -> None:
    # No self-identifier, no label — planner has nothing to match on.
    assert _infer_semantic_role(_raw(), "toggle", label_text=None) is None


def test_toggle_password_type_not_inferred() -> None:
    # The HTML type authoritative rule is fillable-only; a toggle
    # should never try to return "password" even if its type attr
    # happens to be "password" (it shouldn't be anyway).
    raw = _raw(type="password", ariaLabel="pwd-option")
    assert _infer_semantic_role(raw, "toggle") != "password"


def test_fillable_still_returns_text_default() -> None:
    # Regression: the fillable default must remain "text", not None.
    assert _infer_semantic_role(_raw(type="text"), "fillable") == "text"


# ───────────────────────────────────────────────────────────────────
# _match_toggle_for_role
# ───────────────────────────────────────────────────────────────────


def _toggle(
    *,
    element_value: str | None,
    selector: str,
    label_text: str | None = "Status",
    text: str = "",
    aria_label: str | None = None,
    semantic_role: str | None = "status",
) -> DiscoveredElement:
    return DiscoveredElement(
        category="toggle",
        tag="input",
        element_type="radio",
        element_value=element_value,
        selector=selector,
        semantic_role=semantic_role,
        label_text=label_text,
        text=text,
        aria_label=aria_label,
        rect={"x": 0, "y": 200, "w": 80, "h": 20},
        visible=True,
    )


def test_match_toggle_by_exact_value() -> None:
    toggles = [
        _toggle(element_value="", selector="#r-all"),
        _toggle(element_value="active", selector="#r-active"),
        _toggle(element_value="disabled", selector="#r-disabled"),
    ]
    hit = _match_toggle_for_role("status", "active", toggles, set())
    assert hit is not None
    assert hit.selector == "#r-active"


def test_match_toggle_preserves_empty_value() -> None:
    # Ant Design's "All" radio uses value="" — must still be selectable
    # when the spec asks for empty string.
    toggles = [
        _toggle(element_value="", selector="#r-all"),
        _toggle(element_value="active", selector="#r-active"),
    ]
    hit = _match_toggle_for_role("status", "", toggles, set())
    assert hit is not None
    assert hit.selector == "#r-all"


def test_match_toggle_case_insensitive_value_fallback() -> None:
    toggles = [_toggle(element_value="Active", selector="#r-active")]
    hit = _match_toggle_for_role("status", "active", toggles, set())
    assert hit is not None
    assert hit.selector == "#r-active"


def test_match_toggle_falls_back_to_label_text() -> None:
    # Controls that don't expose a ``value`` attribute — match against
    # the option's own text / label.
    toggles = [
        _toggle(
            element_value=None, selector="#r-active",
            text="Active", label_text="Status",
        ),
    ]
    hit = _match_toggle_for_role("status", "Active", toggles, set())
    assert hit is not None
    assert hit.selector == "#r-active"


def test_match_toggle_respects_already_used() -> None:
    toggles = [_toggle(element_value="active", selector="#r-active")]
    hit = _match_toggle_for_role("status", "active", toggles, {"#r-active"})
    assert hit is None


def test_match_toggle_skips_wrong_role() -> None:
    toggles = [
        _toggle(
            element_value="active", selector="#r-active",
            semantic_role="role",  # misclassified group
        ),
    ]
    hit = _match_toggle_for_role("status", "active", toggles, set())
    assert hit is None


# ───────────────────────────────────────────────────────────────────
# plan_actions — integration with toggle_values
# ───────────────────────────────────────────────────────────────────


def _fillable(**overrides: object) -> DiscoveredElement:
    payload = {
        "category": "fillable",
        "tag": "input",
        "element_type": "text",
        "selector": "#search-name",
        "semantic_role": "name",
        "rect": {"x": 0, "y": 200, "w": 240, "h": 32},
        "visible": True,
    }
    payload.update(overrides)
    return DiscoveredElement(**payload)


def _submit(selector: str = "#btn-search") -> DiscoveredElement:
    return DiscoveredElement(
        category="submit",
        tag="button",
        element_type="submit",
        selector=selector,
        text="Search",
        rect={"x": 0, "y": 240, "w": 80, "h": 32},
        visible=True,
    )


def test_plan_actions_toggle_only_clicks_radio_then_submit() -> None:
    # Mirrors filter_by_status: no text input used, radio drives the
    # filter, then Search.
    analysis = PageAnalysis(
        url="http://t/",
        title="t",
        toggle=[
            _toggle(element_value="", selector="#r-all"),
            _toggle(element_value="active", selector="#r-active"),
            _toggle(element_value="disabled", selector="#r-disabled"),
        ],
        submit=[_submit()],
    )
    plan = plan_actions(analysis, toggle_values={"status": "active"})
    kinds = [(a.action_type, a.target_selector) for a in plan if a.action_type != "observe"]
    assert kinds == [
        ("click", "#r-active"),
        ("click", "#btn-search"),
    ]


def test_plan_actions_fill_then_toggle_then_submit() -> None:
    # Mixed: fill a text field, select a radio, click Search.
    analysis = PageAnalysis(
        url="http://t/",
        title="t",
        fillable=[_fillable()],
        toggle=[
            _toggle(element_value="active", selector="#r-active"),
        ],
        submit=[_submit()],
    )
    plan = plan_actions(
        analysis,
        fill_values={"name": "alice"},
        toggle_values={"status": "active"},
    )
    kinds = [(a.action_type, a.target_selector) for a in plan if a.action_type != "observe"]
    assert kinds == [
        ("fill", "#search-name"),
        ("click", "#r-active"),
        ("click", "#btn-search"),
    ]


def test_plan_actions_without_toggle_values_is_unchanged() -> None:
    # Regression: the existing fill-only path must not grow a spurious
    # toggle click just because the page has toggles.
    analysis = PageAnalysis(
        url="http://t/",
        title="t",
        fillable=[_fillable()],
        toggle=[_toggle(element_value="active", selector="#r-active")],
        submit=[_submit()],
    )
    plan = plan_actions(analysis, fill_values={"name": "alice"})
    kinds = [(a.action_type, a.target_selector) for a in plan if a.action_type != "observe"]
    assert kinds == [
        ("fill", "#search-name"),
        ("click", "#btn-search"),
    ]


def test_to_discovered_radio_pipeline() -> None:
    # End-to-end pipeline test for an Ant Design status radio: raw dict
    # mirrors what the JS emits (post-depth-bump), and the resulting
    # DiscoveredElement must have semantic_role + label_text wired in so
    # the planner's toggle path can target it.
    #
    # Pins the contract between the JS-side depth walk (must reach
    # .ant-form-item-row for the radio) and the Python-side label +
    # role inference (must fold the group label into the hint pool).
    raw = {
        "tag": "input",
        "type": "radio",
        "id": None,
        "name": None,
        "role": None,
        "placeholder": None,
        "text": "",
        "value": "active",
        "ariaLabel": None,
        "contentEditable": False,
        "visible": True,
        "rect": {"x": 104, "y": 266, "w": 16, "h": 16},
        "selector": "input.ant-radio-input",
        "className": "ant-radio-input",
        "contentHint": None,
        "wrapperHtml": ANT_STATUS_RADIO_GROUP_HTML,
    }
    elem = _to_discovered(raw, "toggle", "<input type=radio>")
    assert elem.element_value == "active"
    assert elem.visible is True
    assert elem.label_text == "Status"
    assert elem.label_source == "ant-design-group"
    assert elem.semantic_role == "status"


def test_describe_radio_folds_in_value_and_label() -> None:
    # The readable step description for a bare Ant Design radio was
    # just "<input>" — no id, name, placeholder, or text is set on
    # the native <input>. Include element_value and label_text so the
    # operator can tell "status=active" from "status=disabled" at a
    # glance in the timeline + scorecard + supervisor prompt.
    el = _toggle(
        element_value="active",
        selector='input[type="radio"][value="active"]',
        label_text="Status",
    )
    description = _describe(el)
    assert "value='active'" in description
    assert "label='Status'" in description


def test_describe_fillable_unchanged_when_value_absent() -> None:
    # Regression: text fillables with no value/label shouldn't
    # accidentally grow noise. Only populated fields appear.
    el = DiscoveredElement(
        category="fillable",
        tag="input",
        element_type="text",
        id="search-name",
        placeholder="e.g. alice",
        selector="#search-name",
        semantic_role="name",
        rect={"x": 0, "y": 0, "w": 10, "h": 10},
    )
    description = _describe(el)
    assert "id=search-name" in description
    assert "placeholder='e.g. alice'" in description
    # element_value was not set → no stray value='' clause.
    assert "value=" not in description
    # label_text was not set → no stray label='' clause.
    assert "label=" not in description


def test_plan_actions_unmatched_toggle_is_skipped() -> None:
    # If the spec asks for a status value that doesn't exist, we skip
    # rather than click the wrong radio. Scorecard will flag the miss.
    analysis = PageAnalysis(
        url="http://t/",
        title="t",
        toggle=[
            _toggle(element_value="active", selector="#r-active"),
        ],
        submit=[_submit()],
    )
    plan = plan_actions(analysis, toggle_values={"status": "pending"})
    kinds = [(a.action_type, a.target_selector) for a in plan if a.action_type != "observe"]
    assert kinds == [("click", "#btn-search")]
