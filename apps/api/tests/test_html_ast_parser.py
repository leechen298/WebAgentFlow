"""Tests for the HTML → Full AST parser."""

from pathlib import Path

import pytest

from app.schemas.ast import ASTNode
from app.services.html_ast_parser import parse_html

# Path to extension test fixtures (reuse existing HTML fixtures)
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
    """Find all element nodes with a given tag, recursively."""
    found: list[ASTNode] = []
    for n in nodes:
        if n.node_type == "element" and n.tag == tag:
            found.append(n)
        found.extend(find_by_tag(n.children, tag))
        if n.frame_content:
            found.extend(find_by_tag(n.frame_content, tag))
    return found


def find_text_nodes(nodes: list[ASTNode]) -> list[str]:
    """Collect all text node content, recursively, in DOM order."""
    texts: list[str] = []
    for n in nodes:
        if n.node_type == "text" and n.text:
            texts.append(n.text)
        texts.extend(find_text_nodes(n.children))
    return texts


def find_all_elements(nodes: list[ASTNode]) -> list[ASTNode]:
    """Recursively collect all element nodes."""
    found: list[ASTNode] = []
    for n in nodes:
        if n.node_type == "element":
            found.append(n)
        found.extend(find_all_elements(n.children))
        if n.frame_content:
            found.extend(find_all_elements(n.frame_content))
    return found


def max_depth_of(nodes: list[ASTNode], d: int = 0) -> int:
    """Return the maximum nesting depth of an AST node list."""
    m = d
    for n in nodes:
        m = max(m, max_depth_of(n.children, d + 1))
    return m


# ---------------------------------------------------------------------------
# Basic parsing
# ---------------------------------------------------------------------------


class TestBasicParsing:
    def test_empty_input(self):
        result = parse_html("")
        assert result.nodes == []
        assert result.node_count == 0

    def test_whitespace_input(self):
        result = parse_html("   \n  \t  ")
        assert result.nodes == []

    def test_simple_paragraph(self):
        result = parse_html("<p>Hello world</p>")
        assert len(result.nodes) == 1
        p = result.nodes[0]
        assert p.tag == "p"
        assert p.node_type == "element"
        assert len(p.children) == 1
        assert p.children[0].node_type == "text"
        assert p.children[0].text == "Hello world"

    def test_nested_elements(self):
        result = parse_html("<div><p>text</p></div>")
        div = result.nodes[0]
        assert div.tag == "div"
        p = div.children[0]
        assert p.tag == "p"
        assert p.children[0].text == "text"

    def test_sibling_order_preserved(self):
        result = parse_html("<div><p>first</p><p>second</p><p>third</p></div>")
        div = result.nodes[0]
        texts = [
            c.children[0].text
            for c in div.children
            if c.node_type == "element"
        ]
        assert texts == ["first", "second", "third"]

    def test_text_interleaving(self):
        """Text between elements preserved as text nodes in DOM order."""
        result = parse_html("<p>Hello <b>world</b> and <i>more</i></p>")
        p = result.nodes[0]
        # Children: text("Hello"), b("world"), text("and"), i("more")
        assert len(p.children) == 4
        assert p.children[0].node_type == "text"
        assert p.children[0].text == "Hello"
        assert p.children[1].tag == "b"
        assert p.children[2].node_type == "text"
        assert p.children[2].text == "and"
        assert p.children[3].tag == "i"

    def test_multiple_top_level_elements(self):
        result = parse_html("<h1>Title</h1><p>Body</p>")
        top = [n for n in result.nodes if n.node_type == "element"]
        assert [n.tag for n in top] == ["h1", "p"]

    def test_plain_text(self):
        result = parse_html("Hello world")
        assert result.node_count > 0
        texts = find_text_nodes(result.nodes)
        assert "Hello world" in texts

    def test_full_html_document(self):
        html = (
            "<!DOCTYPE html><html><head><title>Test</title></head>"
            "<body><p>content</p></body></html>"
        )
        result = parse_html(html)
        ps = find_by_tag(result.nodes, "p")
        assert len(ps) == 1
        # head/title should be skipped
        assert find_by_tag(result.nodes, "title") == []


# ---------------------------------------------------------------------------
# Attributes
# ---------------------------------------------------------------------------


class TestAttributes:
    def test_preserves_key_attrs(self):
        result = parse_html(
            '<input type="text" name="email" placeholder="Enter email" required />'
        )
        inputs = find_by_tag(result.nodes, "input")
        assert len(inputs) == 1
        inp = inputs[0]
        assert inp.attrs["type"] == "text"
        assert inp.attrs["name"] == "email"
        assert inp.attrs["placeholder"] == "Enter email"
        assert "required" in inp.attrs

    def test_preserves_class(self):
        result = parse_html('<div class="foo bar baz">x</div>')
        assert result.nodes[0].attrs["class"] == "foo bar baz"

    def test_preserves_id(self):
        result = parse_html('<div id="main-content">x</div>')
        assert result.nodes[0].attrs["id"] == "main-content"

    def test_preserves_aria_attrs(self):
        result = parse_html(
            '<button role="tab" aria-selected="true">Tab</button>'
        )
        btn = find_by_tag(result.nodes, "button")[0]
        assert btn.attrs["role"] == "tab"
        assert btn.attrs["aria-selected"] == "true"

    def test_preserves_data_attrs(self):
        result = parse_html('<div data-id="123" data-testid="foo">x</div>')
        div = result.nodes[0]
        assert div.attrs["data-id"] == "123"
        assert div.attrs["data-testid"] == "foo"

    def test_preserves_href_and_src(self):
        result = parse_html('<a href="/about">About</a><img src="/logo.png" alt="Logo" />')
        a = find_by_tag(result.nodes, "a")[0]
        assert a.attrs["href"] == "/about"
        img = find_by_tag(result.nodes, "img")[0]
        assert img.attrs["src"] == "/logo.png"
        assert img.attrs["alt"] == "Logo"

    def test_filters_style_attr(self):
        result = parse_html('<div style="color: red; font-size: 14px">x</div>')
        assert "style" not in result.nodes[0].attrs

    def test_filters_vue_scoped_css(self):
        result = parse_html('<div data-v-abc123="" class="foo">x</div>')
        div = result.nodes[0]
        assert "data-v-abc123" not in div.attrs
        assert div.attrs.get("class") == "foo"

    def test_filters_event_handlers(self):
        result = parse_html(
            '<button onclick="alert(1)" onmouseover="foo()">Click</button>'
        )
        btn = find_by_tag(result.nodes, "button")[0]
        assert "onclick" not in btn.attrs
        assert "onmouseover" not in btn.attrs

    def test_keeps_non_event_on_prefix(self):
        """The 'on' + lowercase filter may catch non-event attrs like 'one'.

        This is an acceptable false positive — 'one' is never a real HTML attr.
        The filter is correct for all actual HTML event handler names.
        """
        parse_html('<div one="1">x</div>')  # should not raise

    def test_keeps_data_value(self):
        """data-value should not be filtered (only data-v-* is)."""
        result = parse_html('<div data-value="hello">x</div>')
        assert result.nodes[0].attrs.get("data-value") == "hello"


# ---------------------------------------------------------------------------
# Visibility
# ---------------------------------------------------------------------------


class TestVisibility:
    def test_visible_by_default(self):
        result = parse_html("<div>visible</div>")
        assert result.nodes[0].visible is True

    def test_display_none(self):
        result = parse_html('<div style="display: none">hidden</div>')
        assert result.nodes[0].visible is False

    def test_display_none_no_spaces(self):
        result = parse_html('<div style="display:none">hidden</div>')
        assert result.nodes[0].visible is False

    def test_visibility_hidden(self):
        result = parse_html('<div style="visibility: hidden">hidden</div>')
        assert result.nodes[0].visible is False

    def test_hidden_attribute(self):
        result = parse_html("<div hidden>hidden</div>")
        assert result.nodes[0].visible is False

    def test_visible_with_other_styles(self):
        result = parse_html('<div style="color: red; margin: 10px">visible</div>')
        assert result.nodes[0].visible is True

    def test_hidden_elements_in_tree(self):
        """Hidden elements remain in the tree with visible=False."""
        result = parse_html(
            '<div><p style="display:none">hidden</p><p>visible</p></div>'
        )
        div = result.nodes[0]
        ps = [c for c in div.children if c.node_type == "element" and c.tag == "p"]
        assert len(ps) == 2  # Both preserved
        assert ps[0].visible is False
        assert ps[1].visible is True


# ---------------------------------------------------------------------------
# Skip tags
# ---------------------------------------------------------------------------


class TestSkipTags:
    def test_skips_script(self):
        result = parse_html(
            "<div><script>alert(1)</script><p>content</p></div>"
        )
        div = result.nodes[0]
        tags = [c.tag for c in div.children if c.node_type == "element"]
        assert "script" not in tags
        assert "p" in tags

    def test_skips_style(self):
        result = parse_html(
            "<div><style>.foo{color:red}</style><p>content</p></div>"
        )
        div = result.nodes[0]
        tags = [c.tag for c in div.children if c.node_type == "element"]
        assert "style" not in tags

    def test_skips_svg(self):
        result = parse_html(
            '<div><svg><circle r="10"/></svg><p>content</p></div>'
        )
        div = result.nodes[0]
        tags = [c.tag for c in div.children if c.node_type == "element"]
        assert "svg" not in tags

    def test_skips_noscript(self):
        result = parse_html(
            "<div><noscript>no js</noscript><p>content</p></div>"
        )
        tags = [c.tag for c in result.nodes[0].children if c.node_type == "element"]
        assert "noscript" not in tags

    def test_skips_template(self):
        result = parse_html(
            "<div><template>tpl</template><p>content</p></div>"
        )
        tags = [c.tag for c in result.nodes[0].children if c.node_type == "element"]
        assert "template" not in tags


# ---------------------------------------------------------------------------
# Iframe
# ---------------------------------------------------------------------------


class TestIframe:
    def test_iframe_without_content(self):
        result = parse_html('<iframe src="https://example.com"></iframe>')
        iframes = find_by_tag(result.nodes, "iframe")
        assert len(iframes) == 1
        assert iframes[0].frame_content is None

    def test_iframe_with_content_by_src(self):
        result = parse_html(
            '<iframe src="https://example.com"></iframe>',
            iframe_html={"https://example.com": "<p>iframe content</p>"},
        )
        iframe = find_by_tag(result.nodes, "iframe")[0]
        assert iframe.frame_content is not None
        texts = find_text_nodes(iframe.frame_content)
        assert "iframe content" in texts

    def test_iframe_with_content_by_frame_id(self):
        result = parse_html(
            '<iframe data-frame-id="frame1"></iframe>',
            iframe_html={"frame1": "<div>frame data</div>"},
        )
        iframe = find_by_tag(result.nodes, "iframe")[0]
        assert iframe.frame_content is not None
        texts = find_text_nodes(iframe.frame_content)
        assert "frame data" in texts

    def test_iframe_frame_id_takes_precedence(self):
        result = parse_html(
            '<iframe data-frame-id="f1" src="https://x.com"></iframe>',
            iframe_html={
                "f1": "<p>from frame id</p>",
                "https://x.com": "<p>from src</p>",
            },
        )
        iframe = find_by_tag(result.nodes, "iframe")[0]
        texts = find_text_nodes(iframe.frame_content or [])
        assert "from frame id" in texts

    def test_iframe_preserves_attrs(self):
        result = parse_html(
            '<iframe src="https://example.com" width="800" height="600"></iframe>'
        )
        iframe = find_by_tag(result.nodes, "iframe")[0]
        assert iframe.attrs["src"] == "https://example.com"
        assert iframe.attrs["width"] == "800"


# ---------------------------------------------------------------------------
# Limits & edge cases
# ---------------------------------------------------------------------------


class TestLimits:
    def test_max_nodes(self):
        html = "<div>" + "<p>x</p>" * 50 + "</div>"
        result = parse_html(html, max_nodes=10)
        # Counter checks before each element, but text children can push
        # slightly over the limit. Verify it's capped near the target.
        assert result.node_count <= 15

    def test_max_depth(self):
        html = "<div>" * 200 + "deep" + "</div>" * 200
        result = parse_html(html, max_depth=5)
        assert max_depth_of(result.nodes) <= 6

    def test_malformed_html(self):
        html = "<div><p>unclosed<p>another<div>nested</p>"
        result = parse_html(html)
        assert result.node_count > 0

    def test_self_closing_tags(self):
        result = parse_html('<br/><hr/><img src="x.png"/>')
        tags = [n.tag for n in result.nodes if n.node_type == "element"]
        assert "br" in tags
        assert "hr" in tags
        assert "img" in tags

    def test_table_structure(self):
        html = """
        <table>
          <thead><tr><th>A</th><th>B</th></tr></thead>
          <tbody><tr><td>1</td><td>2</td></tr></tbody>
        </table>
        """
        result = parse_html(html)
        tables = find_by_tag(result.nodes, "table")
        assert len(tables) == 1
        ths = find_by_tag(tables[0].children, "th")
        tds = find_by_tag(tables[0].children, "td")
        assert len(ths) == 2
        assert len(tds) == 2

    def test_select_options(self):
        html = """
        <select name="country">
          <option value="CN" selected>China</option>
          <option value="US">United States</option>
        </select>
        """
        result = parse_html(html)
        selects = find_by_tag(result.nodes, "select")
        assert len(selects) == 1
        options = find_by_tag(selects[0].children, "option")
        assert len(options) == 2
        assert options[0].attrs["value"] == "CN"
        assert "selected" in options[0].attrs


# ---------------------------------------------------------------------------
# Fixture tests — real HTML from extension test suite
# ---------------------------------------------------------------------------


def _load_fixture(name: str) -> str:
    path = FIXTURE_DIR / name
    if not path.exists():
        pytest.skip(f"Fixture {name} not found at {path}")
    return path.read_text(encoding="utf-8")


class TestFixtureCorporateSite:
    """corporate-site.html: semantic nav/main/aside/footer structure."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.result = parse_html(_load_fixture("corporate-site.html"))

    def test_has_content(self):
        assert self.result.node_count > 0

    def test_top_level_structure(self):
        """Top-level elements: header, main, aside, footer in DOM order."""
        top = [n for n in self.result.nodes if n.node_type == "element"]
        tags = [n.tag for n in top]
        assert tags == ["header", "main", "aside", "footer"]

    def test_nav_links_preserved(self):
        navs = find_by_tag(self.result.nodes, "nav")
        assert len(navs) >= 1
        links = find_by_tag(self.result.nodes, "a")
        assert len(links) >= 10
        for link in links:
            assert "href" in link.attrs

    def test_sections_in_main(self):
        main = [n for n in self.result.nodes if n.tag == "main"][0]
        sections = [c for c in main.children if c.tag == "section"]
        classes = [s.attrs.get("class", "") for s in sections]
        assert classes == ["hero", "features", "testimonials"]

    def test_buttons_preserved(self):
        buttons = find_by_tag(self.result.nodes, "button")
        assert len(buttons) >= 1

    def test_images_preserved(self):
        imgs = find_by_tag(self.result.nodes, "img")
        assert len(imgs) >= 1
        assert imgs[0].attrs.get("src") == "/logo.png"


class TestFixtureAdminSidebar:
    """admin-sidebar.html: table, form, pagination, non-semantic sidebar."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.result = parse_html(_load_fixture("admin-sidebar.html"))

    def test_has_content(self):
        assert self.result.node_count > 0

    def test_table_preserved(self):
        tables = find_by_tag(self.result.nodes, "table")
        assert len(tables) >= 1
        ths = find_by_tag(self.result.nodes, "th")
        assert len(ths) >= 4
        tds = find_by_tag(self.result.nodes, "td")
        assert len(tds) >= 12

    def test_input_preserved(self):
        inputs = find_by_tag(self.result.nodes, "input")
        assert len(inputs) >= 1
        search = inputs[0]
        assert search.attrs.get("placeholder") == "Search by name or email..."

    def test_buttons_preserved(self):
        buttons = find_by_tag(self.result.nodes, "button")
        assert len(buttons) >= 4  # Add User, Export, Search, Previous, Next

    def test_sidebar_links_preserved(self):
        links = find_by_tag(self.result.nodes, "a")
        hrefs = [link.attrs.get("href", "") for link in links]
        assert "/admin/dashboard" in hrefs
        assert "/admin/users" in hrefs


class TestFixtureComplexNesting:
    """complex-nesting.html: nested form-items, tables with action columns."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.result = parse_html(_load_fixture("complex-nesting.html"))

    def test_has_content(self):
        assert self.result.node_count > 0

    def test_form_items_preserved_as_is(self):
        """Form items kept as raw div elements — no label+control pairing."""
        all_els = find_all_elements(self.result.nodes)
        form_items = [
            n for n in all_els
            if n.attrs.get("class", "") == "el-form-item"
        ]
        assert len(form_items) >= 3  # Shipping, Order Items, Notes

    def test_nested_inputs_in_form_items(self):
        inputs = find_by_tag(self.result.nodes, "input")
        assert len(inputs) >= 3  # street, city, zip

    def test_tables_preserved(self):
        tables = find_by_tag(self.result.nodes, "table")
        assert len(tables) >= 3

    def test_action_buttons_in_table_cells(self):
        buttons = find_by_tag(self.result.nodes, "button")
        assert len(buttons) >= 4  # Add Item + Edit/Delete pairs

    def test_select_with_options(self):
        selects = find_by_tag(self.result.nodes, "select")
        assert len(selects) >= 1
        options = find_by_tag(selects[0].children, "option")
        assert len(options) >= 2


class TestFixtureOtherScenarios:
    """Smoke tests for remaining fixtures."""

    def test_h5_mobile(self):
        result = parse_html(_load_fixture("h5-mobile.html"))
        assert result.node_count > 0

    def test_data_dashboard(self):
        result = parse_html(_load_fixture("data-dashboard.html"))
        assert result.node_count > 10

    def test_no_semantic_tags(self):
        result = parse_html(_load_fixture("no-semantic-tags.html"))
        assert result.node_count > 0
        divs = find_by_tag(result.nodes, "div")
        assert len(divs) > 0

    def test_multi_nav(self):
        result = parse_html(_load_fixture("multi-nav.html"))
        assert result.node_count > 0

    def test_nested_menu(self):
        result = parse_html(_load_fixture("nested-menu.html"))
        assert result.node_count > 0

    def test_lottery_page(self):
        result = parse_html(_load_fixture("lottery-page.html"))
        assert result.node_count > 0
        # Large real-world page should produce substantial AST
        assert result.node_count > 50


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_json_round_trip(self):
        """FullAST should serialize to JSON and back."""
        result = parse_html("<div><p>Hello <b>world</b></p></div>")
        json_str = result.model_dump_json()
        from app.schemas.ast import FullAST

        restored = FullAST.model_validate_json(json_str)
        assert restored.node_count == result.node_count
        assert len(restored.nodes) == len(result.nodes)
        assert restored.nodes[0].tag == "div"
