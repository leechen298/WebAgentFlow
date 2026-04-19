"""Tests for the fallback selector helpers in page_analyzer.

The JS discovery step emits an empty ``selector`` when the element has
no strong attribute (id / name / role+text). Python then chooses a
fallback from tag + className while skipping Ant Design 5's dev-only
hash class token (``css-dev-only-do-not-override-<hash>``), which is
shared across every component in one app and therefore useless as a
discriminator.
"""

from __future__ import annotations

from app.services.learning.page_analyzer import (
    _build_fallback_selector,
    _first_informative_class_token,
    _to_discovered,
)

# ───────────────────────────────────────────────────────────────────
# _first_informative_class_token
# ───────────────────────────────────────────────────────────────────


def test_first_informative_token_skips_dev_only_prefix() -> None:
    token = _first_informative_class_token(
        "css-dev-only-do-not-override-1p3hq3p ant-btn ant-btn-link"
    )
    assert token == "ant-btn"


def test_first_informative_token_dev_only_alone_returns_none() -> None:
    assert (
        _first_informative_class_token("css-dev-only-do-not-override-1p3hq3p")
        is None
    )


def test_first_informative_token_empty_string() -> None:
    assert _first_informative_class_token("") is None


def test_first_informative_token_extra_whitespace() -> None:
    token = _first_informative_class_token(
        "  css-dev-only-do-not-override-abc\t\tant-btn  "
    )
    assert token == "ant-btn"


def test_first_informative_token_non_dev_only_first() -> None:
    token = _first_informative_class_token(
        "my-custom-class css-dev-only-do-not-override-xyz ant-btn"
    )
    assert token == "my-custom-class"


# ───────────────────────────────────────────────────────────────────
# _build_fallback_selector
# ───────────────────────────────────────────────────────────────────


def test_build_fallback_selector_skips_dev_only() -> None:
    raw = {
        "tag": "button",
        "className": "css-dev-only-do-not-override-1p3hq3p ant-btn ant-btn-link",
    }
    assert _build_fallback_selector(raw) == "button.ant-btn"


def test_build_fallback_selector_only_dev_only_returns_tag() -> None:
    raw = {
        "tag": "button",
        "className": "css-dev-only-do-not-override-1p3hq3p",
    }
    assert _build_fallback_selector(raw) == "button"


def test_build_fallback_selector_no_class_returns_tag() -> None:
    assert _build_fallback_selector({"tag": "div", "className": ""}) == "div"
    assert _build_fallback_selector({"tag": "span"}) == "span"


def test_build_fallback_selector_prefers_first_non_dev_class() -> None:
    raw = {
        "tag": "div",
        "className": "my-btn css-dev-only-do-not-override-abc",
    }
    assert _build_fallback_selector(raw) == "div.my-btn"


# ───────────────────────────────────────────────────────────────────
# Native toggle discriminator — attribute-value selector
# ───────────────────────────────────────────────────────────────────


def test_build_fallback_selector_radio_with_value() -> None:
    # Ant Design radios share tag + class; only `value` discriminates.
    # The fallback MUST emit the value attribute so the planner's
    # click target is unique.
    raw = {
        "tag": "input",
        "type": "radio",
        "value": "active",
        "className": "ant-radio-input",
    }
    assert (
        _build_fallback_selector(raw)
        == 'input[type="radio"][value="active"]'
    )


def test_build_fallback_selector_radio_empty_value_kept() -> None:
    # Ant Design's "All" radio uses value="" — still a meaningful
    # selection, must be selectable.
    raw = {
        "tag": "input",
        "type": "radio",
        "value": "",
        "className": "ant-radio-input",
    }
    assert _build_fallback_selector(raw) == 'input[type="radio"][value=""]'


def test_build_fallback_selector_checkbox_with_value() -> None:
    raw = {
        "tag": "input",
        "type": "checkbox",
        "value": "newsletter",
        "className": "ant-checkbox-input",
    }
    assert (
        _build_fallback_selector(raw)
        == 'input[type="checkbox"][value="newsletter"]'
    )


def test_build_fallback_selector_radio_without_value_falls_back_to_class() -> None:
    # No value attribute at all (rare, but the analyzer gates on
    # isinstance(raw_value, str), so value=None should NOT produce an
    # attribute selector — fall through to tag/class).
    raw = {
        "tag": "input",
        "type": "radio",
        "value": None,
        "className": "my-radio",
    }
    assert _build_fallback_selector(raw) == "input.my-radio"


def test_build_fallback_selector_text_input_unchanged() -> None:
    # The carve-out is radio/checkbox only — plain text inputs should
    # use the class-based fallback regardless of their value attr.
    raw = {
        "tag": "input",
        "type": "text",
        "value": "alice",
        "className": "ant-input",
    }
    assert _build_fallback_selector(raw) == "input.ant-input"


def test_build_fallback_selector_escapes_quote_in_value() -> None:
    raw = {
        "tag": "input",
        "type": "radio",
        "value": 'ab"cd',
        "className": "x",
    }
    # Quote must be backslash-escaped so the selector stays valid.
    assert (
        _build_fallback_selector(raw)
        == r'input[type="radio"][value="ab\"cd"]'
    )


# ───────────────────────────────────────────────────────────────────
# _to_discovered integration — JS-emitted empty selector gets filled in
# ───────────────────────────────────────────────────────────────────


def _base_raw(**overrides: object) -> dict:
    raw = {
        "tag": "button",
        "type": None,
        "explicitType": "",
        "id": None,
        "name": None,
        "role": None,
        "placeholder": None,
        "text": "",
        "value": "",
        "ariaLabel": None,
        "contentEditable": False,
        "inForm": False,
        "visible": True,
        "rect": {"x": 0, "y": 0, "w": 10, "h": 10},
        "selector": "",
        "href": None,
        "inputMode": None,
        "wrapperHtml": "",
        "className": "",
        "contentHint": None,
    }
    raw.update(overrides)
    return raw


def test_to_discovered_fills_empty_selector_from_className() -> None:
    raw = _base_raw(
        className="css-dev-only-do-not-override-1p3hq3p ant-btn ant-btn-link",
    )
    elem = _to_discovered(raw, "clickable", "test")
    assert elem.selector == "button.ant-btn"


def test_to_discovered_preserves_nonempty_js_selector() -> None:
    raw = _base_raw(id="foo", selector="#foo", className="ant-btn")
    elem = _to_discovered(raw, "clickable", "test")
    assert elem.selector == "#foo"
