"""Tests for page_signature pure functions."""

from __future__ import annotations

import pytest

from app.schemas.page_analysis import DiscoveredElement, PageAnalysis
from app.services.learning.page_signature import (
    dom_fingerprint,
    path_template,
    query_signature,
)

# ---------------------------------------------------------------------------
# path_template
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("input_", "expected"),
    [
        ("/", "/"),
        ("/records", "/records"),
        ("/users/", "/records"),
        ("/detail/1", "/detail/:num"),
        ("/detail/2", "/detail/:num"),
        ("/users/42/edit", "/users/:num/edit"),
        ("/users/42/edit/", "/users/:num/edit"),
        (
            "/records/550e8400-e29b-41d4-a716-446655440000",
            "/records/:uuid",
        ),
        ("https://example.com/users/7", "/users/:num"),
        ("http://a/b?q=1", "/b"),
        ("http://a/b#frag", "/b"),
        ("", "/"),
        ("not a url", "/"),                # garbage in → root
        ("garbage", "/"),                  # bare token, no slash, no scheme
    ],
)
def test_path_template_normalises(input_: str, expected: str) -> None:
    assert path_template(input_) == expected


def test_detail_1_and_2_collapse() -> None:
    assert path_template("/detail/1") == path_template("/detail/2") == "/detail/:num"


# ---------------------------------------------------------------------------
# query_signature
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("input_", "expected"),
    [
        ("", {}),
        ("/x", {}),
        ("/x?", {}),
        ("/create?type=edit", {"type": "edit"}),
        ("/create?type=view", {"type": "view"}),
        ("/create?type=Edit", {"type": "edit"}),
        ("/create?id=2", {"id": "*"}),
        ("/users?status=active", {"status": "active"}),
        ("/x?userId=abc-uuid-here", {"userid": "*"}),
        ("/x?token=abcdefghij", {"token": "*"}),  # 10 chars > 8
        ("/x?type=a1b", {"type": "*"}),           # alphanumeric
        ("/x?q=中文", {"q": "*"}),
        ("/x?mode=view&id=5", {"id": "*", "mode": "view"}),
        ("/x?a=1&a=2", {"a": "*"}),               # repeated key → first value
        ("/x?Type=Edit&type=view", {"type": "edit"}),  # key lowercased, first wins
        ("type=edit", {"type": "edit"}),          # bare query without path
        ("/x?type=edit#frag", {"type": "edit"}),  # fragment stripped, not leaked
        ("type=edit#frag", {"type": "edit"}),     # bare kv + fragment
        ("/x?id=2#section", {"id": "*"}),         # fragment doesn't rescue concrete value
        ("https://example.com/create?type=edit#section", {"type": "edit"}),
    ],
)
def test_query_signature(input_: str, expected: dict[str, str]) -> None:
    assert query_signature(input_) == expected


def test_query_signature_keys_are_sorted() -> None:
    sig = query_signature("/x?z=yes&a=no&m=maybe")
    assert list(sig.keys()) == ["a", "m", "z"]


# ---------------------------------------------------------------------------
# dom_fingerprint
# ---------------------------------------------------------------------------


def _fillable(
    *,
    semantic_role: str | None = None,
    element_type: str | None = "text",
    name: str | None = None,
    label_text: str | None = None,
    tag: str = "input",
    id_: str | None = None,
    placeholder: str | None = None,
) -> DiscoveredElement:
    return DiscoveredElement(
        category="fillable",
        tag=tag,
        element_type=element_type,
        id=id_,
        name=name,
        placeholder=placeholder,
        label_text=label_text,
        semantic_role=semantic_role,
    )


def _clickable(text: str = "", aria_label: str | None = None) -> DiscoveredElement:
    return DiscoveredElement(
        category="clickable",
        tag="button",
        text=text,
        aria_label=aria_label,
    )


def _submit(text: str = "") -> DiscoveredElement:
    return DiscoveredElement(
        category="submit",
        tag="button",
        element_type="submit",
        text=text,
    )


def _page(*, fillable: list | None = None, submit: list | None = None,
          clickable: list | None = None, title: str = "Test Page") -> PageAnalysis:
    return PageAnalysis(
        url="https://example.com/users",
        title=title,
        fillable=fillable or [],
        submit=submit or [],
        clickable=clickable or [],
    )


def test_same_structure_produces_same_fingerprint() -> None:
    a = _page(
        fillable=[_fillable(semantic_role="username", label_text="Username")],
        submit=[_submit("Login")],
    )
    b = _page(
        fillable=[_fillable(semantic_role="username", label_text="Username")],
        submit=[_submit("Login")],
    )
    assert dom_fingerprint(a) == dom_fingerprint(b)


def test_autoid_differences_are_ignored() -> None:
    a = _page(
        fillable=[
            _fillable(
                semantic_role="username",
                id_="rc_select_1234",
                label_text="Username",
            ),
        ],
    )
    b = _page(
        fillable=[
            _fillable(
                semantic_role="username",
                id_="rc_select_9999",
                label_text="Username",
            ),
        ],
    )
    assert dom_fingerprint(a) == dom_fingerprint(b)


def test_ant_dev_class_tokens_in_name_are_stripped() -> None:
    a = _page(
        fillable=[
            _fillable(
                semantic_role="search",
                name="q css-dev-only-do-not-override-1p3hq3p",
                label_text="Search",
            )
        ]
    )
    b = _page(
        fillable=[
            _fillable(
                semantic_role="search",
                name="q css-dev-only-do-not-override-xyz",
                label_text="Search",
            )
        ]
    )
    assert dom_fingerprint(a) == dom_fingerprint(b)


def test_different_form_shape_yields_different_fingerprint() -> None:
    a = _page(
        fillable=[_fillable(semantic_role="username", label_text="Username")],
    )
    b = _page(
        fillable=[_fillable(semantic_role="email", label_text="Email")],
    )
    assert dom_fingerprint(a) != dom_fingerprint(b)


def test_button_order_does_not_matter() -> None:
    a = _page(
        submit=[_submit("Login"), _submit("Cancel")],
    )
    b = _page(
        submit=[_submit("Cancel"), _submit("Login")],
    )
    assert dom_fingerprint(a) == dom_fingerprint(b)


def test_login_vs_users_page_collide_naturally() -> None:
    """Login page and users admin page render to different
    fingerprints because they have different forms / buttons.

    This is the "login redirect" case from conversation: hitting
    ``/records`` without a session lands on the login DOM, which has
    the login page's fingerprint, not the users page's.
    """
    login = _page(
        title="Login",
        fillable=[
            _fillable(semantic_role="username", label_text="Email"),
            _fillable(semantic_role="password", label_text="Password"),
        ],
        submit=[_submit("Sign in")],
    )
    users = _page(
        title="Users",
        fillable=[
            _fillable(semantic_role="name", label_text="Name"),
            _fillable(semantic_role="status", label_text="Status"),
        ],
        clickable=[_clickable("Search")],
    )
    assert dom_fingerprint(login) != dom_fingerprint(users)


def test_fingerprint_is_64_char_hex() -> None:
    page = _page(
        fillable=[_fillable(semantic_role="search", label_text="Search")],
    )
    fp = dom_fingerprint(page)
    assert len(fp) == 64
    assert all(c in "0123456789abcdef" for c in fp)
