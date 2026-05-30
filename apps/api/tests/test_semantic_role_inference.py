"""Tests for semantic_role inference + planner matching.

Covers the Phase 9 ``name`` / ``role`` / ``status`` buckets plus
regression coverage for the pre-existing ``username`` / ``password`` /
``email`` / ``search`` classifications against both fixture shapes
(login + users).
"""

from __future__ import annotations

from app.schemas.page_analysis import DiscoveredElement, PageAnalysis
from app.services.learning.action_planner import (
    _match_fillable_for_role,
    plan_actions,
)
from app.services.learning.page_analyzer import _infer_semantic_role


def _raw(**overrides: object) -> dict:
    base = {
        "tag": "input",
        "type": "text",
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
        "rect": {"x": 0, "y": 0, "w": 200, "h": 32},
        "selector": "",
        "href": None,
        "inputMode": None,
        "wrapperHtml": "",
        "className": "",
        "contentHint": None,
    }
    base.update(overrides)
    return base


# ───────────────────────────────────────────────────────────────────
# _infer_semantic_role — new buckets
# ───────────────────────────────────────────────────────────────────


def test_infer_name_from_id() -> None:
    assert _infer_semantic_role(_raw(id="name-field"), "fillable") == "name"


def test_infer_name_from_placeholder_zh() -> None:
    assert _infer_semantic_role(_raw(placeholder="请输入姓名"), "fillable") == "name"


def test_infer_name_from_placeholder_ja() -> None:
    assert _infer_semantic_role(_raw(placeholder="名前を入力"), "fillable") == "name"


def test_infer_role_from_id() -> None:
    assert _infer_semantic_role(_raw(id="filter-role"), "fillable") == "role"


def test_infer_role_from_aria_label_zh() -> None:
    assert _infer_semantic_role(_raw(ariaLabel="角色"), "fillable") == "role"


def test_infer_status_from_id() -> None:
    assert _infer_semantic_role(_raw(id="filter-status"), "fillable") == "status"


def test_infer_status_from_name_attr() -> None:
    assert _infer_semantic_role(_raw(name="state"), "fillable") == "status"


def test_infer_status_from_placeholder_ja() -> None:
    assert (
        _infer_semantic_role(_raw(placeholder="ステータスを選択"), "fillable")
        == "status"
    )


# ───────────────────────────────────────────────────────────────────
# Regression — existing buckets must not degrade
# ───────────────────────────────────────────────────────────────────


def test_login_username_still_username_not_name() -> None:
    # #username contains the substring "name" but must still classify
    # as username because _USERNAME_FRAGMENTS is checked first.
    assert _infer_semantic_role(_raw(id="username"), "fillable") == "username"


def test_login_user_name_still_username() -> None:
    assert _infer_semantic_role(_raw(name="user-name"), "fillable") == "username"


def test_password_type_stays_password() -> None:
    assert (
        _infer_semantic_role(_raw(id="pwd", type="password"), "fillable")
        == "password"
    )


def test_email_fragment_still_email() -> None:
    # #search-email contains both "search" and "email" substrings —
    # email comes before name/search, so classifies as email.
    assert (
        _infer_semantic_role(_raw(id="search-email"), "fillable") == "email"
    )


def test_generic_search_input_still_search() -> None:
    assert _infer_semantic_role(_raw(id="q", placeholder="Search"), "fillable") == "search"


def test_non_fillable_returns_none() -> None:
    assert _infer_semantic_role(_raw(id="name-field"), "clickable") is None


# ───────────────────────────────────────────────────────────────────
# _match_fillable_for_role — strict match picks the right slot
# ───────────────────────────────────────────────────────────────────


def _elem(semantic_role: str | None, selector: str, **overrides: object) -> DiscoveredElement:
    payload = {
        "category": "fillable",
        "tag": "input",
        "selector": selector,
        "semantic_role": semantic_role,
        "rect": {"x": 0, "y": 200, "w": 200, "h": 32},
        "visible": True,
    }
    payload.update(overrides)
    return DiscoveredElement(**payload)


def test_match_name_picks_name_not_email() -> None:
    fillables = [
        _elem("email", "#search-email"),
        _elem("name", "#name-field"),
    ]
    hit = _match_fillable_for_role("name", fillables, set())
    assert hit is not None
    assert hit.selector == "#name-field"


def test_match_role_picks_role_not_status() -> None:
    fillables = [
        _elem("status", "#filter-status"),
        _elem("role", "#filter-role"),
    ]
    hit = _match_fillable_for_role("role", fillables, set())
    assert hit is not None
    assert hit.selector == "#filter-role"


def test_match_name_avoids_password() -> None:
    # Only a password fillable and a plain-text one exist; name slot
    # must pick the text, never password.
    fillables = [
        _elem("password", "#pwd"),
        _elem("text", "#any-text"),
    ]
    hit = _match_fillable_for_role("name", fillables, set())
    assert hit is not None
    assert hit.selector == "#any-text"


def test_match_password_avoids_new_roles() -> None:
    # Inverse: password slot must not bleed into name/role/status fields.
    fillables = [
        _elem("name", "#name-field"),
        _elem("role", "#filter-role"),
        _elem("status", "#filter-status"),
        _elem("password", "#pwd"),
    ]
    hit = _match_fillable_for_role("password", fillables, set())
    assert hit is not None
    assert hit.selector == "#pwd"


def test_match_text_slot_still_prefers_text() -> None:
    # Regression: text slot must still fall back to None/text fillables.
    fillables = [
        _elem("name", "#name-field"),
        _elem(None, "#generic"),
    ]
    hit = _match_fillable_for_role("text", fillables, set())
    assert hit is not None
    assert hit.selector == "#generic"


# ───────────────────────────────────────────────────────────────────
# plan_actions — end-to-end fixture shape assertions
# ───────────────────────────────────────────────────────────────────


def _page(fillable: list[DiscoveredElement]) -> PageAnalysis:
    return PageAnalysis(url="http://test/", title="t", fillable=fillable)


def test_plan_actions_users_filter_by_name_routes_to_name_input() -> None:
    # Neutral multi-filter shape: exact name role should beat broader search.
    analysis = _page([
        _elem("email", "#search-email"),
        _elem("name", "#name-field"),
        _elem("search", "#search-department"),
    ])
    plan = plan_actions(analysis, fill_values={"name": "alice"})
    fill_steps = [s for s in plan if s.action_type == "fill"]
    assert len(fill_steps) == 1
    assert fill_steps[0].target_selector == "#name-field"
    assert fill_steps[0].value == "alice"


def test_plan_actions_login_still_routes_username_password() -> None:
    # Regression: the login fixture shape must still produce the
    # username→password fill order.
    analysis = _page([
        _elem("username", "#username"),
        _elem("password", "#password"),
    ])
    plan = plan_actions(
        analysis,
        fill_values={"username": "admin", "password": "123456"},
    )
    fill_steps = [s for s in plan if s.action_type == "fill"]
    assert [s.target_selector for s in fill_steps] == ["#username", "#password"]
    assert [s.value for s in fill_steps] == ["admin", "123456"]
