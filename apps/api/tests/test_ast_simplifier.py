"""Tests for the Full AST → Simplified AST projection."""

from pathlib import Path

import pytest

from app.schemas.ast import ASTNode, FullAST
from app.services.ast_simplifier import (
    filter_attrs,
    filter_class_tokens,
    simplify_ast,
)
from app.services.html_ast_parser import parse_html

FIXTURE_DIR = (
    Path(__file__).resolve().parents[2]
    / "extension"
    / "src"
    / "__tests__"
    / "fixtures"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def find_by_tag(nodes: list[ASTNode], tag: str) -> list[ASTNode]:
    found: list[ASTNode] = []
    for n in nodes:
        if n.node_type == "element" and n.tag == tag:
            found.append(n)
        found.extend(find_by_tag(n.children, tag))
    return found


def find_text_nodes(nodes: list[ASTNode]) -> list[str]:
    texts: list[str] = []
    for n in nodes:
        if n.node_type == "text" and n.text:
            texts.append(n.text)
        texts.extend(find_text_nodes(n.children))
    return texts


def collect_tags(nodes: list[ASTNode]) -> list[str]:
    """Collect tag names in pre-order traversal."""
    tags: list[str] = []
    for n in nodes:
        if n.node_type == "element":
            tags.append(n.tag or "")
        elif n.node_type == "text":
            tags.append("#text")
        tags.extend(collect_tags(n.children))
    return tags


# ---------------------------------------------------------------------------
# Class token filtering
# ---------------------------------------------------------------------------


class TestClassFiltering:
    def test_removes_tailwind_layout(self):
        result, removed = filter_class_tokens("el-input flex items-center w-full")
        assert result == "el-input"
        assert removed == 3

    def test_removes_spacing(self):
        result, removed = filter_class_tokens("card mt-2 mb-4 px-4 py-2")
        assert result == "card"
        assert removed == 4

    def test_removes_text_size(self):
        result, removed = filter_class_tokens("title text-sm font-medium")
        assert result == "title"
        assert removed == 2

    def test_removes_bg_color(self):
        result, removed = filter_class_tokens("header bg-white bg-gray-100")
        assert result == "header"
        assert removed == 2

    def test_removes_text_color(self):
        result, removed = filter_class_tokens("label text-gray-500 text-red-600")
        assert result == "label"
        assert removed == 2

    def test_removes_rounded_shadow(self):
        result, removed = filter_class_tokens("btn rounded shadow rounded-lg shadow-md")
        assert result == "btn"
        assert removed == 4

    def test_removes_position(self):
        result, removed = filter_class_tokens("popup absolute top-0 left-0 z-10")
        assert result == "popup"
        assert removed == 4

    def test_removes_border_variants(self):
        result, removed = filter_class_tokens("box border border-gray-200 rounded-md")
        assert result == "box"
        assert removed == 3

    def test_removes_overflow(self):
        result, removed = filter_class_tokens("container overflow-hidden overflow-y-auto")
        # Note: "container" is in _UTILITY_EXACT
        assert result is None
        assert removed == 3

    def test_removes_cursor(self):
        result, removed = filter_class_tokens("link cursor-pointer")
        assert result == "link"
        assert removed == 1

    def test_removes_transition(self):
        result, removed = filter_class_tokens("btn transition duration-200 ease-in-out")
        assert result == "btn"
        assert removed == 3

    def test_removes_negative_margin(self):
        result, removed = filter_class_tokens("item -mt-1 -mx-2")
        assert result == "item"
        assert removed == 2

    def test_removes_hash_runtime(self):
        result, removed = filter_class_tokens("el-button css-abc123 jsx-xyz789 sc-dKJHds")
        assert result == "el-button"
        assert removed == 3

    def test_keeps_component_library_classes(self):
        result, removed = filter_class_tokens("el-input el-form-item ant-table van-cell")
        assert result == "el-input el-form-item ant-table van-cell"
        assert removed == 0

    def test_keeps_bem_classes(self):
        result, removed = filter_class_tokens(
            "el-form-item__label el-input--large nav__link--active"
        )
        assert result == "el-form-item__label el-input--large nav__link--active"
        assert removed == 0

    def test_keeps_business_classes(self):
        result, removed = filter_class_tokens("user-profile order-detail sidebar-menu")
        assert result == "user-profile order-detail sidebar-menu"
        assert removed == 0

    def test_keeps_unknown_classes(self):
        """Conservative: unknown classes are kept."""
        result, removed = filter_class_tokens("my-custom-thing page-wrapper")
        assert result == "my-custom-thing page-wrapper"
        assert removed == 0

    def test_mixed_keep_and_remove(self):
        cls = "el-input flex items-center w-full mt-2 text-sm bg-white"
        result, removed = filter_class_tokens(cls)
        assert result == "el-input"
        assert removed == 6

    def test_all_noise_returns_none(self):
        result, removed = filter_class_tokens("flex grid block absolute")
        assert result is None
        assert removed == 4

    def test_empty_string(self):
        result, removed = filter_class_tokens("")
        assert result is None
        assert removed == 0

    def test_preserves_order(self):
        result, _ = filter_class_tokens("alpha flex beta items-center gamma")
        assert result == "alpha beta gamma"

    def test_flex_grid_detail_removed(self):
        result, removed = filter_class_tokens("wrap flex-row flex-wrap grid-cols-3 col-span-2")
        assert result == "wrap"
        assert removed == 4

    def test_alignment_removed(self):
        result, removed = filter_class_tokens(
            "nav items-center justify-between self-start content-end"
        )
        assert result == "nav"
        assert removed == 4

    def test_gap_space_removed(self):
        result, removed = filter_class_tokens("list gap-4 space-x-2 space-y-3")
        assert result == "list"
        assert removed == 3


# ---------------------------------------------------------------------------
# Attribute filtering
# ---------------------------------------------------------------------------


class TestAttrFiltering:
    def test_keeps_semantic_attrs(self):
        attrs = {
            "id": "main",
            "role": "navigation",
            "name": "email",
            "href": "/about",
            "src": "/logo.png",
            "alt": "Logo",
        }
        result, removed, _ = filter_attrs(attrs)
        assert result == attrs
        assert removed == 0

    def test_keeps_form_attrs(self):
        attrs = {
            "type": "text",
            "value": "hello",
            "placeholder": "Enter text",
            "required": "",
            "disabled": "",
            "readonly": "",
        }
        result, removed, _ = filter_attrs(attrs)
        assert result == attrs
        assert removed == 0

    def test_keeps_aria_attrs(self):
        attrs = {
            "aria-label": "Close",
            "aria-hidden": "true",
            "aria-expanded": "false",
        }
        result, removed, _ = filter_attrs(attrs)
        assert result == attrs
        assert removed == 0

    def test_keeps_data_attrs(self):
        attrs = {
            "data-id": "123",
            "data-testid": "submit-btn",
            "data-frame-src": "https://example.com",
        }
        result, removed, _ = filter_attrs(attrs)
        assert result == attrs
        assert removed == 0

    def test_removes_unknown_attrs(self):
        attrs = {
            "id": "main",
            "custom-runtime-hash": "xyz",
        }
        result, removed, _ = filter_attrs(attrs)
        assert result == {"id": "main"}
        assert removed == 1

    def test_removes_angular_ngcontent(self):
        """_ngcontent-* is Angular scoped CSS — framework noise."""
        attrs = {"id": "box", "_ngcontent-abc123": "", "_ngcontent-xyz": ""}
        result, removed, _ = filter_attrs(attrs)
        assert result == {"id": "box"}
        assert removed == 2

    def test_removes_angular_nghost(self):
        """_nghost-* is Angular host binding — framework noise."""
        attrs = {"role": "dialog", "_nghost-abc": "", "_nghost-xyz789": ""}
        result, removed, _ = filter_attrs(attrs)
        assert result == {"role": "dialog"}
        assert removed == 2

    def test_removes_angular_ng_reflect(self):
        """ng-reflect-* is Angular debug binding — framework noise."""
        attrs = {"name": "email", "ng-reflect-model": "value"}
        result, removed, _ = filter_attrs(attrs)
        assert result == {"name": "email"}
        assert removed == 1

    def test_removes_vue_data_v(self):
        """data-v-* is Vue scoped CSS noise (also filtered by Full AST parser)."""
        attrs = {"data-v-abc123": "", "data-v-xyz": "", "id": "x"}
        result, removed, _ = filter_attrs(attrs)
        assert result == {"id": "x"}
        assert removed == 2

    def test_class_filtered_separately(self):
        attrs = {"class": "el-button flex mt-2", "id": "btn1"}
        result, attrs_removed, class_removed = filter_attrs(attrs)
        assert result == {"class": "el-button", "id": "btn1"}
        assert class_removed == 2
        assert attrs_removed == 0

    def test_class_all_noise_drops_attr(self):
        attrs = {"class": "flex grid block", "id": "box"}
        result, attrs_removed, class_removed = filter_attrs(attrs)
        assert "class" not in result
        assert result == {"id": "box"}
        assert class_removed == 3
        assert attrs_removed == 1  # the class attr itself was dropped

    def test_keeps_table_attrs(self):
        attrs = {"colspan": "2", "rowspan": "3", "scope": "col"}
        result, removed, _ = filter_attrs(attrs)
        assert result == attrs
        assert removed == 0

    def test_keeps_media_attrs(self):
        attrs = {"controls": "", "autoplay": "", "loop": "", "muted": ""}
        result, removed, _ = filter_attrs(attrs)
        assert result == attrs
        assert removed == 0


# ---------------------------------------------------------------------------
# Structure preservation
# ---------------------------------------------------------------------------


class TestStructurePreservation:
    def _make_full(self, html: str, **kw) -> FullAST:
        return parse_html(html, **kw)

    def test_same_tree_shape(self):
        full = self._make_full("<div><p>Hello</p><p>World</p></div>")
        simplified = simplify_ast(full)
        assert collect_tags(full.nodes) == collect_tags(simplified.nodes)

    def test_sibling_order_preserved(self):
        full = self._make_full("<ul><li>A</li><li>B</li><li>C</li></ul>")
        simplified = simplify_ast(full)
        full_texts = find_text_nodes(full.nodes)
        simp_texts = find_text_nodes(simplified.nodes)
        assert full_texts == simp_texts == ["A", "B", "C"]

    def test_parent_child_preserved(self):
        full = self._make_full(
            "<div><section><p>deep</p></section></div>"
        )
        simplified = simplify_ast(full)
        # div > section > p > #text
        div_s = simplified.nodes[0]
        assert div_s.tag == "div"
        sec = div_s.children[0]
        assert sec.tag == "section"
        p = sec.children[0]
        assert p.tag == "p"
        assert p.children[0].text == "deep"

    def test_text_nodes_preserved(self):
        full = self._make_full("<p>Hello <b>world</b> end</p>")
        simplified = simplify_ast(full)
        texts = find_text_nodes(simplified.nodes)
        assert texts == ["Hello", "world", "end"]

    def test_hidden_elements_preserved(self):
        full = self._make_full(
            '<div><p style="display:none">hidden</p><p>visible</p></div>'
        )
        simplified = simplify_ast(full)
        ps = find_by_tag(simplified.nodes, "p")
        assert len(ps) == 2
        assert ps[0].visible is False
        assert ps[1].visible is True

    def test_node_count_unchanged(self):
        full = self._make_full("<div><p>a</p><p>b</p></div>")
        simplified = simplify_ast(full)
        assert simplified.stats.node_count == full.node_count

    def test_iframe_subtree_preserved(self):
        full = self._make_full(
            '<iframe src="x"></iframe>',
            iframe_html={"x": "<p>iframe content</p>"},
        )
        simplified = simplify_ast(full)
        # iframe > frame-body > p > text
        iframes = find_by_tag(simplified.nodes, "iframe")
        assert len(iframes) == 1
        frame_bodies = find_by_tag(iframes[0].children, "frame-body")
        assert len(frame_bodies) == 1
        texts = find_text_nodes(frame_bodies[0].children)
        assert "iframe content" in texts

    def test_nested_iframe_preserved(self):
        full = self._make_full(
            '<iframe data-frame-id="outer"></iframe>',
            iframe_html={
                "outer": '<div><iframe data-frame-id="inner"></iframe></div>',
                "inner": "<p>nested</p>",
            },
        )
        simplified = simplify_ast(full)
        fbs = find_by_tag(simplified.nodes, "frame-body")
        assert len(fbs) == 2
        texts = find_text_nodes(simplified.nodes)
        assert "nested" in texts


# ---------------------------------------------------------------------------
# Attrs actually pruned in simplification
# ---------------------------------------------------------------------------


class TestSimplificationEffect:
    def test_class_tokens_pruned(self):
        full = parse_html(
            '<div class="el-form flex items-center mt-4 bg-white rounded">'
            "<p>content</p></div>"
        )
        simplified = simplify_ast(full)
        div = simplified.nodes[0]
        assert div.attrs.get("class") == "el-form"
        assert simplified.stats.class_tokens_removed >= 5

    def test_attrs_pruned(self):
        # Full AST already filters style/on*/data-v-*, but unknown attrs remain
        full = parse_html(
            '<div id="main" role="main" '
            'custom-internal="xyz" _ng-content="abc">content</div>'
        )
        simplified = simplify_ast(full)
        div = simplified.nodes[0]
        assert "id" in div.attrs
        assert "role" in div.attrs
        assert "custom-internal" not in div.attrs
        assert "_ng-content" not in div.attrs
        assert simplified.stats.attrs_removed >= 2

    def test_key_fields_preserved(self):
        full = parse_html(
            '<a href="/about" title="About Us">About</a>'
            '<img src="/logo.png" alt="Logo" />'
            '<input type="text" name="q" value="search" placeholder="Search..." />'
        )
        simplified = simplify_ast(full)
        a = find_by_tag(simplified.nodes, "a")[0]
        assert a.attrs["href"] == "/about"
        assert a.attrs["title"] == "About Us"
        img = find_by_tag(simplified.nodes, "img")[0]
        assert img.attrs["src"] == "/logo.png"
        assert img.attrs["alt"] == "Logo"
        inp = find_by_tag(simplified.nodes, "input")[0]
        assert inp.attrs["type"] == "text"
        assert inp.attrs["name"] == "q"
        assert inp.attrs["value"] == "search"
        assert inp.attrs["placeholder"] == "Search..."

    def test_iframe_frame_attrs_preserved(self):
        full = parse_html(
            '<iframe data-frame-id="f1" src="https://x.com"></iframe>',
            iframe_html={"f1": "<p>content</p>"},
        )
        simplified = simplify_ast(full)
        iframe = find_by_tag(simplified.nodes, "iframe")[0]
        assert iframe.attrs.get("src") == "https://x.com"
        fb = find_by_tag(iframe.children, "frame-body")[0]
        assert fb.attrs.get("data-frame-id") == "f1"

    def test_stats_reported(self):
        full = parse_html(
            '<div class="box flex mt-2" unknown-attr="x"><p class="text-sm">hi</p></div>'
        )
        simplified = simplify_ast(full)
        assert simplified.stats.class_tokens_removed >= 3  # flex, mt-2, text-sm
        assert simplified.stats.attrs_removed >= 1  # unknown-attr


# ---------------------------------------------------------------------------
# Fixture smoke tests
# ---------------------------------------------------------------------------


def _load_fixture(name: str) -> str:
    path = FIXTURE_DIR / name
    if not path.exists():
        pytest.skip(f"Fixture {name} not found")
    return path.read_text(encoding="utf-8")


class TestFixtures:
    """Simplified AST of real fixtures preserves structure."""

    @pytest.mark.parametrize(
        "fixture",
        [
            "corporate-site.html",
            "admin-sidebar.html",
            "complex-nesting.html",
            "h5-mobile.html",
            "data-dashboard.html",
            "no-semantic-tags.html",
        ],
    )
    def test_structure_preserved(self, fixture: str):
        html = _load_fixture(fixture)
        full = parse_html(html)
        simplified = simplify_ast(full)
        # Same tree shape
        assert collect_tags(full.nodes) == collect_tags(simplified.nodes)
        # Same text content
        assert find_text_nodes(full.nodes) == find_text_nodes(simplified.nodes)
        # Node count matches
        assert simplified.stats.node_count == full.node_count
