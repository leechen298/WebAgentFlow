"""Tests for page_analyzer — classification, semantic role inference,
button-like class detection, and _to_discovered.

Covers the pure-Python classification and helper logic that does NOT
require a live Playwright page.
"""

from __future__ import annotations

from app.schemas.page_analysis import DiscoveredElement
from app.services.learning.page_analyzer import (
    _build_fallback_selector,
    _classify,
    _first_informative_class_token,
    _has_button_like_class,
    _infer_semantic_role,
    _to_discovered,
)


# ───────────────────────────────────────────────────────────────────
# _classify — structural element classification
# ───────────────────────────────────────────────────────────────────


class TestClassify:
    def test_textarea(self):
        cat, reason = _classify({"tag": "textarea", "type": "", "explicitType": "", "role": "", "contentEditable": False, "inForm": False})
        assert cat == "fillable"
        assert "textarea" in reason

    def test_input_text(self):
        cat, _ = _classify({"tag": "input", "type": "text", "explicitType": "", "role": "", "contentEditable": False, "inForm": False})
        assert cat == "fillable"

    def test_input_search(self):
        cat, _ = _classify({"tag": "input", "type": "search", "explicitType": "", "role": "", "contentEditable": False, "inForm": False})
        assert cat == "fillable"

    def test_input_email(self):
        cat, _ = _classify({"tag": "input", "type": "email", "explicitType": "", "role": "", "contentEditable": False, "inForm": False})
        assert cat == "fillable"

    def test_input_password(self):
        cat, _ = _classify({"tag": "input", "type": "password", "explicitType": "", "role": "", "contentEditable": False, "inForm": False})
        assert cat == "fillable"

    def test_input_no_type(self):
        cat, _ = _classify({"tag": "input", "type": None, "explicitType": "", "role": "", "contentEditable": False, "inForm": False})
        assert cat == "fillable"

    def test_contenteditable(self):
        cat, reason = _classify({"tag": "div", "type": "", "explicitType": "", "role": "", "contentEditable": True, "inForm": False})
        assert cat == "fillable"
        assert "contenteditable" in reason

    def test_role_textbox(self):
        cat, _ = _classify({"tag": "div", "type": "", "explicitType": "", "role": "textbox", "contentEditable": False, "inForm": False})
        assert cat == "fillable"

    def test_role_combobox(self):
        cat, _ = _classify({"tag": "div", "type": "", "explicitType": "", "role": "combobox", "contentEditable": False, "inForm": False})
        assert cat == "fillable"

    def test_role_searchbox(self):
        cat, _ = _classify({"tag": "div", "type": "", "explicitType": "", "role": "searchbox", "contentEditable": False, "inForm": False})
        assert cat == "fillable"

    def test_role_spinbutton(self):
        cat, _ = _classify({"tag": "div", "type": "", "explicitType": "", "role": "spinbutton", "contentEditable": False, "inForm": False})
        assert cat == "fillable"

    def test_input_checkbox(self):
        cat, reason = _classify({"tag": "input", "type": "checkbox", "explicitType": "", "role": "", "contentEditable": False, "inForm": False})
        assert cat == "toggle"
        assert "checkbox" in reason

    def test_input_radio(self):
        cat, _ = _classify({"tag": "input", "type": "radio", "explicitType": "", "role": "", "contentEditable": False, "inForm": False})
        assert cat == "toggle"

    def test_role_switch(self):
        cat, _ = _classify({"tag": "div", "type": "", "explicitType": "", "role": "switch", "contentEditable": False, "inForm": False})
        assert cat == "toggle"

    def test_role_checkbox(self):
        cat, _ = _classify({"tag": "div", "type": "", "explicitType": "", "role": "checkbox", "contentEditable": False, "inForm": False})
        assert cat == "toggle"

    def test_role_radio(self):
        cat, _ = _classify({"tag": "div", "type": "", "explicitType": "", "role": "radio", "contentEditable": False, "inForm": False})
        assert cat == "toggle"

    def test_role_menuitemcheckbox(self):
        cat, _ = _classify({"tag": "div", "type": "", "explicitType": "", "role": "menuitemcheckbox", "contentEditable": False, "inForm": False})
        assert cat == "toggle"

    def test_role_menuitemradio(self):
        cat, _ = _classify({"tag": "div", "type": "", "explicitType": "", "role": "menuitemradio", "contentEditable": False, "inForm": False})
        assert cat == "toggle"

    def test_select_tag(self):
        cat, _ = _classify({"tag": "select", "type": "", "explicitType": "", "role": "", "contentEditable": False, "inForm": False})
        assert cat == "select"

    def test_role_listbox(self):
        cat, _ = _classify({"tag": "div", "type": "", "explicitType": "", "role": "listbox", "contentEditable": False, "inForm": False})
        assert cat == "select"

    def test_role_option(self):
        cat, _ = _classify({"tag": "div", "type": "", "explicitType": "", "role": "option", "contentEditable": False, "inForm": False})
        assert cat == "select"

    def test_input_submit(self):
        cat, reason = _classify({"tag": "input", "type": "submit", "explicitType": "", "role": "", "contentEditable": False, "inForm": False})
        assert cat == "submit"
        assert "submit" in reason

    def test_input_button_type(self):
        cat, _ = _classify({"tag": "input", "type": "button", "explicitType": "", "role": "", "contentEditable": False, "inForm": False})
        assert cat == "submit"

    def test_input_image_type(self):
        cat, _ = _classify({"tag": "input", "type": "image", "explicitType": "", "role": "", "contentEditable": False, "inForm": False})
        assert cat == "submit"

    def test_button_type_submit(self):
        cat, reason = _classify({"tag": "button", "type": "", "explicitType": "submit", "role": "", "contentEditable": False, "inForm": False})
        assert cat == "submit"
        assert "submit" in reason

    def test_button_in_form_default_submit(self):
        cat, reason = _classify({"tag": "button", "type": "", "explicitType": "", "role": "", "contentEditable": False, "inForm": True})
        assert cat == "submit"
        assert "default type=submit" in reason

    def test_button_type_button(self):
        cat, reason = _classify({"tag": "button", "type": "", "explicitType": "button", "role": "", "contentEditable": False, "inForm": False})
        assert cat == "clickable"
        assert "button" in reason

    def test_role_button(self):
        cat, _ = _classify({"tag": "div", "type": "", "explicitType": "", "role": "button", "contentEditable": False, "inForm": False})
        assert cat == "clickable"

    def test_link_with_href(self):
        cat, reason = _classify({"tag": "a", "type": "", "explicitType": "", "role": "", "contentEditable": False, "inForm": False, "href": "http://x"})
        assert cat == "navigation"
        assert "href" in reason

    def test_role_link(self):
        cat, _ = _classify({"tag": "span", "type": "", "explicitType": "", "role": "link", "contentEditable": False, "inForm": False})
        assert cat == "navigation"

    def test_role_menuitem(self):
        cat, _ = _classify({"tag": "li", "type": "", "explicitType": "", "role": "menuitem", "contentEditable": False, "inForm": False})
        assert cat == "navigation"

    def test_role_tab(self):
        cat, _ = _classify({"tag": "div", "type": "", "explicitType": "", "role": "tab", "contentEditable": False, "inForm": False})
        assert cat == "navigation"

    def test_div_with_btn_class(self):
        cat, reason = _classify({"tag": "div", "type": "", "explicitType": "", "role": "", "contentEditable": False, "inForm": False, "className": "btn"})
        assert cat == "clickable"
        assert "class-as-button" in reason

    def test_span_with_submit_button_class(self):
        cat, _ = _classify({"tag": "span", "type": "", "explicitType": "", "role": "", "contentEditable": False, "inForm": False, "className": "submit-button"})
        assert cat == "clickable"

    def test_div_with_tabindex_falls_to_other(self):
        cat, reason = _classify({"tag": "div", "type": "", "explicitType": "", "role": "", "contentEditable": False, "inForm": False, "className": ""})
        assert cat == "other"

    def test_link_without_href_is_other(self):
        cat, _ = _classify({"tag": "a", "type": "", "explicitType": "", "role": "", "contentEditable": False, "inForm": False, "href": None})
        assert cat == "other"


# ───────────────────────────────────────────────────────────────────
# _has_button_like_class
# ───────────────────────────────────────────────────────────────────


class TestHasButtonLikeClass:
    def test_exact_btn(self):
        assert _has_button_like_class({"className": "btn"}) is True

    def test_exact_button(self):
        assert _has_button_like_class({"className": "button"}) is True

    def test_suffix_btn(self):
        assert _has_button_like_class({"className": "submit-btn"}) is True

    def test_suffix_button(self):
        assert _has_button_like_class({"className": "primary-button"}) is True

    def test_container_excluded(self):
        assert _has_button_like_class({"className": "button-group"}) is False

    def test_toolbar_excluded(self):
        assert _has_button_like_class({"className": "btn-toolbar-list"}) is False

    def test_empty(self):
        assert _has_button_like_class({"className": ""}) is False

    def test_none(self):
        assert _has_button_like_class({"className": None}) is False

    def test_multiple_classes(self):
        assert _has_button_like_class({"className": "ant-btn css-hash ant-btn-primary"}) is True


# ───────────────────────────────────────────────────────────────────
# _infer_semantic_role
# ───────────────────────────────────────────────────────────────────


class TestInferSemanticRole:
    def test_password_type(self):
        assert _infer_semantic_role({"type": "password"}, "fillable") == "password"

    def test_email_type(self):
        assert _infer_semantic_role({"type": "email"}, "fillable") == "email"

    def test_search_type(self):
        assert _infer_semantic_role({"type": "search"}, "fillable") == "search"

    def test_username_in_name(self):
        assert _infer_semantic_role({"name": "username", "id": "", "placeholder": "", "ariaLabel": ""}, "fillable") == "username"

    def test_login_in_id(self):
        assert _infer_semantic_role({"name": "", "id": "login-input", "placeholder": "", "ariaLabel": ""}, "fillable") == "username"

    def test_email_in_placeholder(self):
        assert _infer_semantic_role({"name": "", "id": "", "placeholder": "Enter email", "ariaLabel": ""}, "fillable") == "email"

    def test_name_fragment(self):
        assert _infer_semantic_role({"name": "filter_name", "id": "", "placeholder": "", "ariaLabel": ""}, "fillable") == "name"

    def test_role_fragment(self):
        assert _infer_semantic_role({"name": "access_role", "id": "", "placeholder": "", "ariaLabel": ""}, "fillable") == "role"

    def test_status_fragment(self):
        assert _infer_semantic_role({"name": "", "id": "", "placeholder": "", "ariaLabel": "status filter"}, "fillable") == "status"

    def test_search_fragment(self):
        assert _infer_semantic_role({"name": "", "id": "", "placeholder": "Search...", "ariaLabel": ""}, "fillable") == "search"

    def test_chinese_username(self):
        assert _infer_semantic_role({"name": "", "id": "", "placeholder": "请输入用户", "ariaLabel": ""}, "fillable") == "username"

    def test_japanese_email(self):
        assert _infer_semantic_role({"name": "", "id": "", "placeholder": "メールアドレス", "ariaLabel": ""}, "fillable") == "email"

    def test_default_text_for_fillable(self):
        assert _infer_semantic_role({"name": "", "id": "", "placeholder": "", "ariaLabel": ""}, "fillable") == "text"

    def test_none_for_toggle_no_hints(self):
        assert _infer_semantic_role({"name": "", "id": "", "placeholder": "", "ariaLabel": ""}, "toggle") is None

    def test_toggle_with_label_text(self):
        assert _infer_semantic_role({"name": "", "id": "", "placeholder": "", "ariaLabel": ""}, "toggle", label_text="Status") == "status"

    def test_none_for_other_category(self):
        assert _infer_semantic_role({"name": "username", "id": "", "placeholder": "", "ariaLabel": ""}, "clickable") is None

    def test_password_type_overrides_name_hint(self):
        """password type wins over name hint."""
        assert _infer_semantic_role({"type": "password", "name": "username", "id": "", "placeholder": "", "ariaLabel": ""}, "fillable") == "password"

    def test_chinese_role(self):
        assert _infer_semantic_role({"name": "", "id": "", "placeholder": "角色", "ariaLabel": ""}, "fillable") == "role"

    def test_chinese_status(self):
        assert _infer_semantic_role({"name": "", "id": "", "placeholder": "状态", "ariaLabel": ""}, "fillable") == "status"

    def test_japanese_search(self):
        assert _infer_semantic_role({"name": "", "id": "", "placeholder": "検索", "ariaLabel": ""}, "fillable") == "search"


# ───────────────────────────────────────────────────────────────────
# _first_informative_class_token
# ───────────────────────────────────────────────────────────────────


class TestFirstInformativeClassToken:
    def test_skips_dev_only(self):
        assert _first_informative_class_token(
            "css-dev-only-do-not-override-abc123 ant-btn"
        ) == "ant-btn"

    def test_all_dev_only(self):
        assert _first_informative_class_token(
            "css-dev-only-do-not-override-abc123"
        ) is None

    def test_normal_class(self):
        assert _first_informative_class_token("my-button primary") == "my-button"

    def test_empty(self):
        assert _first_informative_class_token("") is None


# ───────────────────────────────────────────────────────────────────
# _build_fallback_selector
# ───────────────────────────────────────────────────────────────────


class TestBuildFallbackSelector:
    def test_radio_with_value(self):
        raw = {"tag": "input", "type": "radio", "value": "active", "className": ""}
        assert _build_fallback_selector(raw) == 'input[type="radio"][value="active"]'

    def test_checkbox_with_value(self):
        raw = {"tag": "input", "type": "checkbox", "value": "agree", "className": ""}
        assert _build_fallback_selector(raw) == 'input[type="checkbox"][value="agree"]'

    def test_radio_value_with_quotes(self):
        raw = {"tag": "input", "type": "radio", "value": 'a"b', "className": ""}
        assert 'input[type="radio"][value="a\\"b"' in _build_fallback_selector(raw)

    def test_radio_value_with_backslash(self):
        raw = {"tag": "input", "type": "radio", "value": "a\\b", "className": ""}
        sel = _build_fallback_selector(raw)
        assert "a\\\\b" in sel

    def test_input_with_class(self):
        raw = {"tag": "input", "type": "text", "className": "ant-input"}
        assert _build_fallback_selector(raw) == "input.ant-input"

    def test_input_no_class(self):
        raw = {"tag": "input", "type": "text", "className": ""}
        assert _build_fallback_selector(raw) == "input"

    def test_div_with_class(self):
        raw = {"tag": "div", "className": "my-class"}
        assert _build_fallback_selector(raw) == "div.my-class"

    def test_div_no_class(self):
        raw = {"tag": "div", "className": ""}
        assert _build_fallback_selector(raw) == "div"

    def test_skips_dev_only_class(self):
        raw = {"tag": "div", "className": "css-dev-only-do-not-override-abc123 ant-btn"}
        assert _build_fallback_selector(raw) == "div.ant-btn"


# ───────────────────────────────────────────────────────────────────
# _to_discovered
# ───────────────────────────────────────────────────────────────────


class TestToDiscovered:
    def test_basic_conversion(self):
        raw = {
            "tag": "input", "type": "text", "id": "username", "name": None,
            "role": None, "placeholder": "Enter user", "text": "",
            "ariaLabel": None, "contentEditable": False, "visible": True,
            "rect": {"x": 10, "y": 20, "w": 200, "h": 30},
            "selector": "#username", "className": "", "wrapperHtml": "",
            "value": "", "contentHint": None,
        }
        elem = _to_discovered(raw, "fillable", "test reason")
        assert elem.tag == "input"
        assert elem.id == "username"
        assert elem.category == "fillable"
        assert elem.placeholder == "Enter user"
        assert elem.selector == "#username"

    def test_element_value_string(self):
        raw = {
            "tag": "input", "type": "radio", "id": None, "name": None,
            "role": None, "placeholder": None, "text": "",
            "ariaLabel": None, "contentEditable": False, "visible": True,
            "rect": {}, "selector": "", "className": "", "wrapperHtml": "",
            "value": "active", "contentHint": None,
        }
        elem = _to_discovered(raw, "toggle", "toggle reason")
        assert elem.element_value == "active"

    def test_element_value_none_when_not_string(self):
        raw = {
            "tag": "input", "type": "text", "id": None, "name": None,
            "role": None, "placeholder": None, "text": "",
            "ariaLabel": None, "contentEditable": False, "visible": True,
            "rect": {}, "selector": "", "className": "", "wrapperHtml": "",
            "value": None, "contentHint": None,
        }
        elem = _to_discovered(raw, "fillable", "reason")
        assert elem.element_value is None

    def test_content_hint_preserved(self):
        raw = {
            "tag": "button", "type": "", "id": None, "name": None,
            "role": "button", "placeholder": None, "text": "",
            "ariaLabel": None, "contentEditable": False, "visible": True,
            "rect": {}, "selector": "", "className": "", "wrapperHtml": "",
            "value": "", "contentHint": "icon:search",
        }
        elem = _to_discovered(raw, "clickable", "reason")
        assert elem.content_hint == "icon:search"

    def test_content_hint_none_when_empty(self):
        raw = {
            "tag": "button", "type": "", "id": None, "name": None,
            "role": None, "placeholder": None, "text": "",
            "ariaLabel": None, "contentEditable": False, "visible": True,
            "rect": {}, "selector": "", "className": "", "wrapperHtml": "",
            "value": "", "contentHint": "",
        }
        elem = _to_discovered(raw, "clickable", "reason")
        assert elem.content_hint is None

    def test_fallback_selector_used_when_empty(self):
        raw = {
            "tag": "div", "type": "", "id": None, "name": None,
            "role": None, "placeholder": None, "text": "",
            "ariaLabel": None, "contentEditable": False, "visible": True,
            "rect": {}, "selector": "", "className": "my-btn", "wrapperHtml": "",
            "value": "", "contentHint": None,
        }
        elem = _to_discovered(raw, "clickable", "reason")
        assert elem.selector == "div.my-btn"

    def test_text_truncated(self):
        raw = {
            "tag": "button", "type": "", "id": None, "name": None,
            "role": None, "placeholder": None, "text": "x" * 100,
            "ariaLabel": None, "contentEditable": False, "visible": True,
            "rect": {}, "selector": "#b", "className": "", "wrapperHtml": "",
            "value": "", "contentHint": None,
        }
        elem = _to_discovered(raw, "clickable", "reason")
        assert len(elem.text) <= 80
