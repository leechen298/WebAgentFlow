"""Tests for services.analysis.form_label_extractor.

The extractor operates on HTML fragments as pure strings — no
Playwright, no browser. Tests just feed in fixture HTML for each
framework shape we care about and assert the returned label text +
source.
"""

from __future__ import annotations

from app.services.analysis.form_label_extractor import (
    AntDesignExtractor,
    NativeLabelExtractor,
    extract_label,
)


# ───────────────────────────────────────────────────────────────────
# Ant Design
# ───────────────────────────────────────────────────────────────────


ANT_FORM_ITEM_HTML = """
<div class="ant-row ant-form-item-row css-dev-only-do-not-override-1p3hq3p">
  <div class="ant-col ant-form-item-label css-dev-only-do-not-override-1p3hq3p">
    <label class="" title="姓名">姓名</label>
  </div>
  <div class="ant-col ant-form-item-control css-dev-only-do-not-override-1p3hq3p">
    <div class="ant-form-item-control-input">
      <div class="ant-form-item-control-input-content">
        <span class="ant-input-affix-wrapper">
          <input type="text" class="ant-input" placeholder="例如 alice" id="search-name" value="alice">
        </span>
      </div>
    </div>
  </div>
</div>
"""


def test_ant_design_extractor_matches_basic_form_item() -> None:
    result = extract_label(ANT_FORM_ITEM_HTML, "search-name")
    assert result.source == "ant-design"
    assert result.text == "姓名"


# Regression: the exact shape the analyzer receives at runtime —
# `.ant-form-item` wrapping `.ant-form-item-row` wrapping the label
# cell AND an `.ant-form-item-control` cell with multiple nested
# wrappers around the actual <input>. If the JS passes this outer
# wrapper in, the extractor must still walk down to the row and
# read the label. This was reported on 2026-04-19 as label_text=null
# during an autonomous run on /users.
ANT_FORM_ITEM_FULL_REAL_HTML = """
<div class="ant-col ant-col-xs-24 ant-col-sm-12 ant-col-lg-8 css-dev-only-do-not-override-1p3hq3p"
     style="padding-left: 8px; padding-right: 8px;">
  <div class="ant-form-item css-dev-only-do-not-override-1p3hq3p">
    <div class="ant-row ant-form-item-row css-dev-only-do-not-override-1p3hq3p">
      <div class="ant-col ant-form-item-label css-dev-only-do-not-override-1p3hq3p">
        <label class="" title="姓名">姓名</label>
      </div>
      <div class="ant-col ant-form-item-control css-dev-only-do-not-override-1p3hq3p">
        <div class="ant-form-item-control-input">
          <div class="ant-form-item-control-input-content">
            <span class="ant-input-affix-wrapper css-dev-only-do-not-override-1p3hq3p">
              <input type="text" class="ant-input css-dev-only-do-not-override-1p3hq3p"
                     placeholder="例如 alice" id="search-name" value="alice">
              <span class="ant-input-suffix"></span>
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
"""


def test_ant_design_extractor_handles_real_deep_nesting() -> None:
    result = extract_label(ANT_FORM_ITEM_FULL_REAL_HTML, "search-name")
    assert result.source == "ant-design"
    assert result.text == "姓名"


def test_ant_design_extractor_finds_label_when_wrapper_is_form_item_level() -> None:
    # The JS might hand us the `.ant-form-item` ancestor rather than
    # the `.ant-form-item-row`. Both shapes have to work.
    inner = ANT_FORM_ITEM_FULL_REAL_HTML
    # Strip the outer ant-col grid cell so root = .ant-form-item
    stripped = inner[inner.index('<div class="ant-form-item '):]
    result = extract_label(stripped, "search-name")
    assert result.source == "ant-design"
    assert result.text == "姓名"


# ───────────────────────────────────────────────────────────────────
# Drift-avoidance regressions
# ───────────────────────────────────────────────────────────────────
# These tests lock in the behaviour that the extractor picks the
# label for the form-item the control is DIRECTLY in, not any
# ancestor form-item that transitively contains the control.


def test_ant_design_picks_innermost_when_form_items_are_nested() -> None:
    # Pathological nesting: an inner form-item lives inside the outer
    # form-item's control cell. Without drift protection the old
    # "scan all matching rows from outside in" logic would have
    # returned "外层标签" because the outer row DOES transitively
    # contain #target. The correct answer is the inner form-item's
    # label, because that's where the control actually lives.
    html = """
    <div class="ant-form-item-row">
      <div class="ant-form-item-label"><label>外层标签</label></div>
      <div class="ant-form-item-control">
        <div class="ant-form-item-row">
          <div class="ant-form-item-label"><label>内层标签</label></div>
          <div class="ant-form-item-control">
            <input id="target">
          </div>
        </div>
      </div>
    </div>
    """
    result = extract_label(html, "target")
    assert result.source == "ant-design"
    assert result.text == "内层标签"


def test_ant_design_ignores_label_cells_from_unrelated_rows() -> None:
    # Two sibling form-items in the same wrapper. Each row has its
    # own label cell; the extractor must not mix them up even when
    # the markup ordering is weird.
    html = """
    <div>
      <div class="ant-form-item-row">
        <div class="ant-form-item-label"><label>姓名</label></div>
        <div class="ant-form-item-control"><input id="a"></div>
      </div>
      <div class="ant-form-item-row">
        <div class="ant-form-item-label"><label>邮箱</label></div>
        <div class="ant-form-item-control"><input id="b"></div>
      </div>
    </div>
    """
    assert extract_label(html, "a").text == "姓名"
    assert extract_label(html, "b").text == "邮箱"


def test_ant_design_does_not_read_label_from_nested_form_item_descendant() -> None:
    # The target's own form-item has NO label cell. A descendant
    # form-item (sitting inside the control) does have one. Previously
    # a descendant-searching selector would have picked up the
    # descendant's label by mistake. With direct-child iteration the
    # extractor correctly returns None.
    html = """
    <div class="ant-form-item-row">
      <div class="ant-form-item-control">
        <input id="outer-target">
        <div class="ant-form-item-row">
          <div class="ant-form-item-label"><label>内层无关标签</label></div>
          <div class="ant-form-item-control"><input id="inner"></div>
        </div>
      </div>
    </div>
    """
    result = extract_label(html, "outer-target")
    # Outer form-item has no label cell as a direct child of the row,
    # so the correct answer is None — NOT the inner "内层无关标签".
    assert result.text is None
    assert result.source is None


def test_ant_design_extractor_can_handle_check() -> None:
    ex = AntDesignExtractor()
    assert ex.can_handle(ANT_FORM_ITEM_HTML)
    assert not ex.can_handle("<div><input id='x'></div>")


def test_ant_design_extractor_strips_trailing_colon() -> None:
    html = """
    <div class="ant-form-item-row">
      <div class="ant-form-item-label"><label>Email：</label></div>
      <div class="ant-form-item-control">
        <input id="x-email">
      </div>
    </div>
    """
    result = extract_label(html, "x-email")
    assert result.text == "Email"


def test_ant_design_extractor_strips_required_marker() -> None:
    html = """
    <div class="ant-form-item-row">
      <div class="ant-form-item-label"><label>* 必填项</label></div>
      <div class="ant-form-item-control">
        <input id="foo">
      </div>
    </div>
    """
    result = extract_label(html, "foo")
    assert result.text == "必填项"


def test_ant_design_extractor_picks_correct_row_among_multiple() -> None:
    # Two form items in the same wrapper blob; extractor must pick
    # the one whose control matches element_id.
    html = f"""
    <div>
      <div class="ant-form-item-row">
        <div class="ant-form-item-label"><label>姓名</label></div>
        <div class="ant-form-item-control"><input id="search-name"></div>
      </div>
      <div class="ant-form-item-row">
        <div class="ant-form-item-label"><label>邮箱</label></div>
        <div class="ant-form-item-control"><input id="search-email"></div>
      </div>
    </div>
    """
    assert extract_label(html, "search-name").text == "姓名"
    assert extract_label(html, "search-email").text == "邮箱"


def test_ant_design_extractor_returns_none_when_id_not_found() -> None:
    result = extract_label(ANT_FORM_ITEM_HTML, "not-present")
    assert result.text is None
    assert result.source is None


# ───────────────────────────────────────────────────────────────────
# Native HTML5
# ───────────────────────────────────────────────────────────────────


def test_native_label_for_attribute() -> None:
    html = """
    <form>
      <label for="username">Username</label>
      <input id="username" type="text">
    </form>
    """
    result = extract_label(html, "username")
    assert result.source == "native"
    assert result.text == "Username"


def test_native_label_wrapping_input() -> None:
    html = """
    <label>
      Email
      <input id="email" type="email">
    </label>
    """
    result = extract_label(html, "email")
    assert result.source == "native"
    assert result.text == "Email"


def test_native_aria_labelledby_single() -> None:
    html = """
    <div>
      <span id="pw-lbl">Password</span>
      <input id="pw" type="password" aria-labelledby="pw-lbl">
    </div>
    """
    result = extract_label(html, "pw")
    assert result.source == "native"
    assert result.text == "Password"


def test_native_aria_labelledby_multiple_ids() -> None:
    html = """
    <div>
      <span id="a">Work</span>
      <span id="b">Email</span>
      <input id="work-email" aria-labelledby="a b">
    </div>
    """
    result = extract_label(html, "work-email")
    assert result.source == "native"
    assert result.text == "Work Email"


def test_native_extractor_can_handle_check() -> None:
    ex = NativeLabelExtractor()
    assert ex.can_handle('<label for="x">X</label><input id="x">')
    assert ex.can_handle('<input aria-labelledby="lbl"><span id="lbl">X</span>')
    assert not ex.can_handle("<div><input id='x'></div>")


# ───────────────────────────────────────────────────────────────────
# Dispatcher behaviour
# ───────────────────────────────────────────────────────────────────


def test_ant_takes_precedence_over_native_when_both_match() -> None:
    # Contrived HTML that would satisfy both extractors; Ant Design is
    # registered first, so it should win.
    html = """
    <div class="ant-form-item-row">
      <div class="ant-form-item-label"><label for="dual">Ant Label</label></div>
      <div class="ant-form-item-control"><input id="dual"></div>
    </div>
    """
    result = extract_label(html, "dual")
    assert result.source == "ant-design"
    assert result.text == "Ant Label"


def test_empty_inputs_return_empty_result() -> None:
    assert extract_label("", "id").text is None
    assert extract_label("<div></div>", "").text is None


def test_no_match_returns_none_not_nearby_guess() -> None:
    # There's text floating around — we MUST NOT fall back to picking
    # it as a label. Failure is silent by design (per product decision).
    html = """
    <div>
      <p>Some instructions that look label-ish</p>
      <div><input id="x"></div>
      <p>Some trailing help text</p>
    </div>
    """
    result = extract_label(html, "x")
    assert result.text is None
    assert result.source is None


def test_malformed_html_does_not_raise() -> None:
    # Partial HTML / missing closing tags must not crash the extractor.
    result = extract_label('<div class="ant-form-item-row"><label>Partial', "x")
    # No crash; result may or may not be None depending on lxml's
    # tolerance. Either outcome is acceptable as long as it doesn't
    # raise.
    assert result is not None
