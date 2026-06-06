"""Tests for action_planner — scoring, matching, and plan generation.

Covers: _score_fillable, _score_submit, _score_fallback_submit,
_find_fallback_submit, _match_fillable_for_role, _match_toggle_for_role,
plan_actions (multi-field, single-field, toggle, fallback submit, Enter),
_describe.
"""

from __future__ import annotations

from app.schemas.page_analysis import DiscoveredElement, PageAnalysis
from app.services.learning.action_planner import (
    _describe,
    _find_fallback_submit,
    _match_fillable_for_role,
    _match_toggle_for_role,
    _score_fallback_submit,
    _score_fillable,
    _score_submit,
    plan_actions,
)

# ───────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────


def _el(
    *,
    selector: str = "#inp",
    category: str = "fillable",
    tag: str = "input",
    element_type: str | None = "text",
    id: str | None = None,
    name: str | None = None,
    role: str | None = None,
    text: str = "",
    placeholder: str | None = None,
    aria_label: str | None = None,
    element_value: str | None = None,
    semantic_role: str | None = None,
    label_text: str | None = None,
    readonly: bool = False,
    rect: dict | None = None,
    visible: bool = True,
) -> DiscoveredElement:
    return DiscoveredElement(
        category=category,
        tag=tag,
        element_type=element_type,
        id=id,
        name=name,
        role=role,
        text=text,
        placeholder=placeholder,
        aria_label=aria_label,
        element_value=element_value,
        semantic_role=semantic_role,
        label_text=label_text,
        readonly=readonly,
        selector=selector,
        rect=rect or {},
        visible=visible,
    )


def _analysis(
    fillable=None, submit=None, clickable=None, toggle=None,
    navigation=None, select=None, other=None,
) -> PageAnalysis:
    return PageAnalysis(
        url="http://test/",
        title="Test",
        fillable=fillable or [],
        submit=submit or [],
        clickable=clickable or [],
        toggle=toggle or [],
        navigation=navigation or [],
        select=select or [],
        other=other or [],
    )


# ───────────────────────────────────────────────────────────────────
# _score_fillable
# ───────────────────────────────────────────────────────────────────


class TestScoreFillable:
    def test_basic_input(self):
        el = _el(rect={"x": 0, "y": 0, "w": 200, "h": 30})
        score = _score_fillable(el)
        assert score > 0

    def test_large_area_bonus(self):
        big = _el(rect={"x": 0, "y": 200, "w": 300, "h": 50})
        small = _el(rect={"x": 0, "y": 200, "w": 50, "h": 10})
        assert _score_fillable(big) > _score_fillable(small)

    def test_central_position_bonus(self):
        central = _el(rect={"x": 0, "y": 200, "w": 200, "h": 30})
        top = _el(rect={"x": 0, "y": 10, "w": 200, "h": 30})
        assert _score_fillable(central) > _score_fillable(top)

    def test_placeholder_bonus(self):
        with_ph = _el(placeholder="Enter email", rect={"x": 0, "y": 200, "w": 200, "h": 30})
        no_ph = _el(rect={"x": 0, "y": 200, "w": 200, "h": 30})
        assert _score_fillable(with_ph) > _score_fillable(no_ph)

    def test_name_bonus(self):
        with_name = _el(name="username", rect={"x": 0, "y": 200, "w": 200, "h": 30})
        no_name = _el(rect={"x": 0, "y": 200, "w": 200, "h": 30})
        assert _score_fillable(with_name) > _score_fillable(no_name)

    def test_aria_label_bonus(self):
        with_aria = _el(aria_label="Search", rect={"x": 0, "y": 200, "w": 200, "h": 30})
        no_aria = _el(rect={"x": 0, "y": 200, "w": 200, "h": 30})
        assert _score_fillable(with_aria) > _score_fillable(no_aria)

    def test_searchbox_role_bonus(self):
        sb = _el(role="searchbox", rect={"x": 0, "y": 200, "w": 200, "h": 30})
        plain = _el(rect={"x": 0, "y": 200, "w": 200, "h": 30})
        assert _score_fillable(sb) > _score_fillable(plain)

    def test_textbox_role_bonus(self):
        tb = _el(role="textbox", rect={"x": 0, "y": 200, "w": 200, "h": 30})
        plain = _el(rect={"x": 0, "y": 200, "w": 200, "h": 30})
        assert _score_fillable(tb) > _score_fillable(plain)

    def test_textarea_bonus(self):
        ta = _el(tag="textarea", rect={"x": 0, "y": 200, "w": 200, "h": 30})
        inp = _el(rect={"x": 0, "y": 200, "w": 200, "h": 30})
        assert _score_fillable(ta) > _score_fillable(inp)

    def test_combobox_role_bonus(self):
        cb = _el(role="combobox", rect={"x": 0, "y": 200, "w": 200, "h": 30})
        plain = _el(rect={"x": 0, "y": 200, "w": 200, "h": 30})
        assert _score_fillable(cb) > _score_fillable(plain)


# ───────────────────────────────────────────────────────────────────
# _score_submit
# ───────────────────────────────────────────────────────────────────


class TestScoreSubmit:
    def test_submit_type_bonus(self):
        explicit = _el(
            tag="button",
            element_type="submit",
            rect={"x": 0, "y": 200, "w": 100, "h": 40},
        )
        regular = _el(
            tag="button",
            element_type="button",
            rect={"x": 0, "y": 200, "w": 100, "h": 40},
        )
        assert _score_submit(explicit) > _score_submit(regular)

    def test_position_bonus(self):
        low = _el(tag="button", rect={"x": 0, "y": 200, "w": 100, "h": 40})
        high = _el(tag="button", rect={"x": 0, "y": 10, "w": 100, "h": 40})
        assert _score_submit(low) > _score_submit(high)

    def test_generic_verb_bonus(self):
        with_verb = _el(tag="button", text="Submit", rect={"x": 0, "y": 200, "w": 100, "h": 40})
        no_verb = _el(tag="button", text="Click me", rect={"x": 0, "y": 200, "w": 100, "h": 40})
        assert _score_submit(with_verb) > _score_submit(no_verb)

    def test_chinese_verb_bonus(self):
        cn = _el(tag="button", text="搜索", rect={"x": 0, "y": 200, "w": 100, "h": 40})
        en = _el(tag="button", text="Random", rect={"x": 0, "y": 200, "w": 100, "h": 40})
        assert _score_submit(cn) > _score_submit(en)

    def test_large_area_bonus(self):
        big = _el(tag="button", rect={"x": 0, "y": 200, "w": 200, "h": 80})
        small = _el(tag="button", rect={"x": 0, "y": 200, "w": 30, "h": 10})
        assert _score_submit(big) > _score_submit(small)


# ───────────────────────────────────────────────────────────────────
# _score_fallback_submit / _find_fallback_submit
# ───────────────────────────────────────────────────────────────────


class TestFallbackSubmit:
    def test_too_small_returns_negative(self):
        el = _el(tag="div", category="clickable", rect={"x": 0, "y": 0, "w": 10, "h": 10})
        fillable = _el(rect={"x": 0, "y": 0, "w": 200, "h": 30})
        assert _score_fallback_submit(el, fillable) < 0

    def test_proximity_bonus(self):
        close = _el(tag="div", category="clickable", rect={"x": 200, "y": 200, "w": 100, "h": 40})
        far = _el(tag="div", category="clickable", rect={"x": 800, "y": 800, "w": 100, "h": 40})
        fillable = _el(rect={"x": 200, "y": 200, "w": 200, "h": 30})
        assert _score_fallback_submit(close, fillable) > _score_fallback_submit(far, fillable)

    def test_button_tag_bonus(self):
        button = _el(
            tag="button",
            category="clickable",
            rect={"x": 200, "y": 200, "w": 100, "h": 40},
        )
        div = _el(tag="div", category="clickable", rect={"x": 200, "y": 200, "w": 100, "h": 40})
        fillable = _el(rect={"x": 200, "y": 200, "w": 200, "h": 30})
        assert _score_fallback_submit(button, fillable) > _score_fallback_submit(div, fillable)

    def test_generic_verb_bonus(self):
        search = _el(
            tag="div",
            category="clickable",
            text="Search",
            rect={"x": 200, "y": 200, "w": 100, "h": 40},
        )
        noop = _el(
            tag="div",
            category="clickable",
            text="Help",
            rect={"x": 200, "y": 200, "w": 100, "h": 40},
        )
        fillable = _el(rect={"x": 200, "y": 200, "w": 200, "h": 30})
        assert _score_fallback_submit(search, fillable) > _score_fallback_submit(noop, fillable)

    def test_find_fallback_submit_returns_best(self):
        good = _el(
            tag="button",
            category="clickable",
            text="Search",
            rect={"x": 210, "y": 200, "w": 100, "h": 40},
        )
        bad = _el(
            tag="div",
            category="clickable",
            text="?",
            rect={"x": 800, "y": 800, "w": 10, "h": 10},
        )
        fillable = _el(rect={"x": 200, "y": 200, "w": 200, "h": 30})
        result = _find_fallback_submit(fillable, [good, bad])
        assert result is not None
        assert result[0] is good

    def test_find_fallback_submit_none_when_empty(self):
        fillable = _el(rect={"x": 0, "y": 0, "w": 200, "h": 30})
        assert _find_fallback_submit(fillable, []) is None

    def test_find_fallback_submit_none_when_all_too_small(self):
        tiny = _el(tag="div", category="clickable", rect={"x": 0, "y": 0, "w": 5, "h": 5})
        fillable = _el(rect={"x": 0, "y": 0, "w": 200, "h": 30})
        assert _find_fallback_submit(fillable, [tiny]) is None


# ───────────────────────────────────────────────────────────────────
# _match_fillable_for_role
# ───────────────────────────────────────────────────────────────────


class TestMatchFillableForRole:
    def test_exact_semantic_role_match(self):
        username = _el(selector="#u", semantic_role="username")
        email = _el(selector="#e", semantic_role="email")
        result = _match_fillable_for_role("username", [username, email], set())
        assert result is username

    def test_skip_already_used(self):
        used = _el(selector="#u", semantic_role="username")
        free = _el(selector="#u2", semantic_role="username")
        result = _match_fillable_for_role("username", [used, free], {"#u"})
        assert result is free

    def test_text_role_matches_any_text_or_none(self):
        generic = _el(selector="#g", semantic_role=None)
        text_el = _el(selector="#t", semantic_role="text")
        result = _match_fillable_for_role("text", [generic, text_el], set())
        assert result is not None

    def test_fallback_excludes_mismatched(self):
        pw = _el(selector="#pw", semantic_role="password")
        name = _el(selector="#nm", semantic_role="name")
        result = _match_fillable_for_role("username", [pw, name], set())
        # username should NOT fall back to password
        assert result is name

    def test_password_excludes_most(self):
        username = _el(selector="#u", semantic_role="username")
        email = _el(selector="#e", semantic_role="email")
        result = _match_fillable_for_role("password", [username, email], set())
        # password can't use any of these
        assert result is None

    def test_returns_none_when_all_used(self):
        used = _el(selector="#u", semantic_role="username")
        result = _match_fillable_for_role("username", [used], {"#u"})
        assert result is None

    def test_neutral_business_role_prefers_exact_field_signal_over_search(self):
        search = _el(
            selector="#global-search",
            semantic_role="search",
            role="searchbox",
            placeholder="Search by reference, title, or category",
            label_text="Search",
            rect={"x": 0, "y": 180, "w": 640, "h": 44},
        )
        reference = _el(
            selector="#record-reference",
            id="record-reference",
            name="reference",
            label_text="Reference",
            rect={"x": 0, "y": 260, "w": 180, "h": 32},
        )
        title = _el(
            selector="#record-title",
            id="record-title",
            name="title",
            label_text="Title",
            rect={"x": 0, "y": 300, "w": 180, "h": 32},
        )
        category = _el(
            selector="#record-category",
            id="record-category",
            name="category",
            label_text="Category",
            rect={"x": 0, "y": 340, "w": 180, "h": 32},
        )
        quantity = _el(
            selector="#record-quantity",
            id="record-quantity",
            name="quantity",
            label_text="Quantity",
            rect={"x": 0, "y": 380, "w": 180, "h": 32},
        )

        analysis = _analysis(fillable=[search, reference, title, category, quantity])
        actions = plan_actions(
            analysis,
            fill_values={
                "reference": "REF-001",
                "title": "Alpha Record",
                "category": "General",
                "quantity": "24",
            },
        )

        fill_actions = [a for a in actions if a.action_type == "fill"]
        assert [(a.target_selector, a.value) for a in fill_actions] == [
            ("#record-reference", "REF-001"),
            ("#record-title", "Alpha Record"),
            ("#record-category", "General"),
            ("#record-quantity", "24"),
        ]


# ───────────────────────────────────────────────────────────────────
# _match_toggle_for_role
# ───────────────────────────────────────────────────────────────────


class TestMatchToggleForRole:
    def test_exact_value_match(self):
        active = _el(selector="#a", category="toggle", tag="input", element_type="radio",
                     semantic_role="status", element_value="active")
        disabled = _el(selector="#d", category="toggle", tag="input", element_type="radio",
                       semantic_role="status", element_value="disabled")
        result = _match_toggle_for_role("status", "active", [active, disabled], set())
        assert result is active

    def test_case_insensitive_value_match(self):
        el = _el(selector="#a", category="toggle", tag="input", element_type="radio",
                 semantic_role="status", element_value="Active")
        result = _match_toggle_for_role("status", "active", [el], set())
        assert result is el

    def test_label_text_match(self):
        el = _el(selector="#a", category="toggle", tag="input", element_type="radio",
                 semantic_role="status", label_text="Active")
        result = _match_toggle_for_role("status", "active", [el], set())
        assert result is el

    def test_text_match(self):
        el = _el(selector="#a", category="toggle", tag="input", element_type="radio",
                 semantic_role="status", text="Active")
        result = _match_toggle_for_role("status", "active", [el], set())
        assert result is el

    def test_aria_label_match(self):
        el = _el(selector="#a", category="toggle", tag="input", element_type="radio",
                 semantic_role="status", aria_label="Active")
        result = _match_toggle_for_role("status", "active", [el], set())
        assert result is el

    def test_no_candidates_for_role(self):
        el = _el(selector="#a", category="toggle", tag="input", element_type="radio",
                 semantic_role="name", element_value="high")
        result = _match_toggle_for_role("status", "active", [el], set())
        assert result is None

    def test_no_match_returns_none(self):
        el = _el(selector="#a", category="toggle", tag="input", element_type="radio",
                 semantic_role="status", element_value="disabled")
        result = _match_toggle_for_role("status", "active", [el], set())
        assert result is None

    def test_skip_already_used(self):
        used = _el(selector="#a", category="toggle", tag="input", element_type="radio",
                   semantic_role="status", element_value="active")
        result = _match_toggle_for_role("status", "active", [used], {"#a"})
        assert result is None

    def test_empty_string_value_match(self):
        """Ant Design's 'All' radio with value=''."""
        all_radio = _el(selector="#all", category="toggle", tag="input", element_type="radio",
                        semantic_role="status", element_value="")
        result = _match_toggle_for_role("status", "", [all_radio], set())
        assert result is all_radio


# ───────────────────────────────────────────────────────────────────
# plan_actions
# ───────────────────────────────────────────────────────────────────


class TestPlanActions:
    def test_multi_field_fill(self):
        username = _el(selector="#u", semantic_role="username")
        password = _el(selector="#pw", semantic_role="password", element_type="password")
        submit = _el(selector="#btn", category="submit", tag="button", element_type="submit")
        analysis = _analysis(fillable=[username, password], submit=[submit])
        actions = plan_actions(analysis, fill_values={"username": "admin", "password": "secret"})
        assert len(actions) >= 3  # fill user, fill pw, click submit, observe
        fill_actions = [a for a in actions if a.action_type == "fill"]
        assert len(fill_actions) == 2
        assert any(a.value == "admin" for a in fill_actions)
        assert any(a.value == "secret" for a in fill_actions)

    def test_single_field_fill(self):
        inp = _el(selector="#q", semantic_role="search")
        submit = _el(selector="#btn", category="submit", tag="button", element_type="submit")
        analysis = _analysis(fillable=[inp], submit=[submit])
        actions = plan_actions(analysis, fill_value="hello")
        fill = [a for a in actions if a.action_type == "fill"]
        assert len(fill) == 1
        assert fill[0].value == "hello"

    def test_toggle_values(self):
        radio = _el(
            selector="#r1", category="toggle", tag="input", element_type="radio",
            semantic_role="status", element_value="active",
        )
        analysis = _analysis(toggle=[radio])
        actions = plan_actions(analysis, toggle_values={"status": "active"})
        clicks = [a for a in actions if a.action_type == "click" and a.target_selector == "#r1"]
        assert len(clicks) == 1
        assert clicks[0].value == "active"

    def test_toggle_no_match_skipped(self):
        radio = _el(
            selector="#r1", category="toggle", tag="input", element_type="radio",
            semantic_role="status", element_value="disabled",
        )
        analysis = _analysis(toggle=[radio])
        actions = plan_actions(analysis, toggle_values={"status": "active"})
        clicks = [a for a in actions if a.target_selector == "#r1"]
        assert len(clicks) == 0

    def test_native_select_from_fill_values(self):
        status = _el(
            selector="#status",
            category="select",
            tag="select",
            id="status",
            name="status",
            element_type=None,
            semantic_role=None,
            label_text="Status",
            element_value="active",
        )
        submit = _el(selector="#btn", category="submit", tag="button", element_type="submit")
        analysis = _analysis(select=[status], submit=[submit])

        actions = plan_actions(analysis, fill_values={"status": "active"})

        assert [(a.action_type, a.target_selector, a.value) for a in actions[:2]] == [
            ("select", "#status", "active"),
            ("click", "#btn", None),
        ]

    def test_readonly_date_picker_uses_set_value(self):
        registered = _el(
            selector="#registered",
            category="fillable",
            tag="input",
            element_type=None,
            id="registered",
            label_text="Registered",
            placeholder="Select date",
            readonly=True,
            rect={"x": 0, "y": 200, "w": 180, "h": 32},
        )
        submit = _el(selector="#btn", category="submit", tag="button", element_type="submit")
        analysis = _analysis(fillable=[registered], submit=[submit])

        actions = plan_actions(analysis, fill_values={"registered": "2026-01-01"})

        assert [(a.action_type, a.target_selector, a.value) for a in actions[:2]] == [
            ("set_value", "#registered", "2026-01-01"),
            ("click", "#btn", None),
        ]

    def test_combobox_uses_first_option_selection(self):
        role = _el(
            selector="#role",
            category="fillable",
            tag="input",
            element_type="search",
            role="combobox",
            id="role",
            label_text="Role",
            semantic_role="role",
            readonly=True,
            rect={"x": 0, "y": 200, "w": 180, "h": 32},
        )
        submit = _el(selector="#btn", category="submit", tag="button", element_type="submit")
        analysis = _analysis(fillable=[role], submit=[submit])

        actions = plan_actions(analysis, fill_values={"role": "admin"})

        assert [(a.action_type, a.target_selector, a.value) for a in actions[:2]] == [
            ("select_first_option", "#role", "admin"),
            ("click", "#btn", None),
        ]

    def test_fallback_submit_from_clickables(self):
        inp = _el(selector="#q", semantic_role="search")
        btn = _el(
            selector="#btn", category="clickable", tag="button",
            text="Search", rect={"x": 200, "y": 200, "w": 100, "h": 40},
        )
        analysis = _analysis(fillable=[inp], clickable=[btn])
        actions = plan_actions(analysis, fill_value="test")
        click = [a for a in actions if a.action_type == "click"]
        assert len(click) == 1

    def test_enter_fallback_when_no_submit_or_clickable(self):
        inp = _el(selector="#q", semantic_role="search")
        analysis = _analysis(fillable=[inp])
        actions = plan_actions(analysis, fill_value="test")
        press = [a for a in actions if a.action_type == "press"]
        assert len(press) == 1
        assert press[0].value == "Enter"

    def test_enter_fallback_when_clickable_too_small(self):
        inp = _el(selector="#q", semantic_role="search")
        tiny = _el(
            selector="#t", category="clickable", tag="div",
            rect={"x": 0, "y": 0, "w": 5, "h": 5},
        )
        analysis = _analysis(fillable=[inp], clickable=[tiny])
        actions = plan_actions(analysis, fill_value="test")
        press = [a for a in actions if a.action_type == "press"]
        assert len(press) == 1

    def test_always_ends_with_observe(self):
        analysis = _analysis()
        actions = plan_actions(analysis)
        assert actions[-1].action_type == "observe"

    def test_no_fillable_just_observe(self):
        analysis = _analysis()
        actions = plan_actions(analysis)
        assert len(actions) == 1
        assert actions[0].action_type == "observe"

    def test_submit_without_fill(self):
        submit = _el(selector="#btn", category="submit", tag="button", element_type="submit")
        analysis = _analysis(submit=[submit])
        actions = plan_actions(analysis)
        click = [a for a in actions if a.action_type == "click"]
        assert len(click) == 1

    def test_fill_order_matches_role_order(self):
        """username should be filled before password."""
        username = _el(selector="#u", semantic_role="username")
        password = _el(selector="#pw", semantic_role="password", element_type="password")
        analysis = _analysis(fillable=[username, password])
        actions = plan_actions(analysis, fill_values={"password": "s", "username": "u"})
        fill = [a for a in actions if a.action_type == "fill"]
        assert fill[0].target_selector == "#u"
        assert fill[1].target_selector == "#pw"

    def test_enter_fallback_when_no_submit_and_has_last_filled(self):
        inp = _el(selector="#q", semantic_role="search")
        analysis = _analysis(fillable=[inp], submit=[], clickable=[])
        actions = plan_actions(analysis, fill_value="test")
        press = [a for a in actions if a.action_type == "press"]
        assert len(press) == 1
        assert press[0].value == "Enter"


# ───────────────────────────────────────────────────────────────────
# _describe
# ───────────────────────────────────────────────────────────────────


class TestDescribe:
    def test_basic(self):
        desc = _describe(_el(tag="input"))
        assert "<input>" in desc

    def test_with_id(self):
        desc = _describe(_el(tag="input", id="username"))
        assert "id=username" in desc

    def test_with_name(self):
        desc = _describe(_el(tag="input", name="email"))
        assert "name=email" in desc

    def test_with_role(self):
        desc = _describe(_el(tag="div", role="button"))
        assert "role=button" in desc

    def test_with_element_value(self):
        desc = _describe(_el(tag="input", element_value="active"))
        assert "value='active'" in desc

    def test_with_text(self):
        desc = _describe(_el(tag="button", text="Submit Form"))
        assert "text='Submit Form'" in desc

    def test_with_placeholder(self):
        desc = _describe(_el(tag="input", placeholder="Enter email"))
        assert "placeholder='Enter email'" in desc

    def test_with_label_text(self):
        desc = _describe(_el(tag="input", label_text="Username"))
        assert "label='Username'" in desc

    def test_value_truncated(self):
        long_val = "x" * 50
        desc = _describe(_el(tag="input", element_value=long_val))
        assert len(desc) < 200  # truncated
