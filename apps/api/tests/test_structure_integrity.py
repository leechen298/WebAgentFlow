"""Deep structural integrity check: Full AST vs Simplified AST.

Verifies that simplify_ast() is a pure attribute projection — the tree
structure must be identical between Full AST and Simplified AST.

Checks per node:
- node_type matches
- tag matches (element nodes)
- text matches (text nodes)
- visible matches
- children count matches
- children order matches (recursive)

Attribute differences are expected and NOT flagged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from app.schemas.ast import ASTNode, FullAST
from app.services.ast_simplifier import simplify_ast
from app.services.html_ast_parser import parse_html

FIXTURE_DIR = (
    Path(__file__).resolve().parents[2]
    / "extension"
    / "src"
    / "__tests__"
    / "fixtures"
)


# ---------------------------------------------------------------------------
# Structural diff engine
# ---------------------------------------------------------------------------


@dataclass
class StructureDiff:
    """A single structural difference between two AST nodes."""

    path: str
    field: str
    full_value: object
    simplified_value: object

    def __str__(self) -> str:
        return (
            f"[{self.path}] {self.field}: "
            f"full={self.full_value!r}  simplified={self.simplified_value!r}"
        )


@dataclass
class DiffReport:
    """Collects all structural differences."""

    diffs: list[StructureDiff] = field(default_factory=list)
    nodes_compared: int = 0

    @property
    def ok(self) -> bool:
        return len(self.diffs) == 0

    def summary(self) -> str:
        if self.ok:
            return f"OK — {self.nodes_compared} nodes compared, no structural differences"
        lines = [
            f"FAIL — {len(self.diffs)} structural difference(s) "
            f"in {self.nodes_compared} nodes:"
        ]
        for d in self.diffs:
            lines.append(f"  {d}")
        return "\n".join(lines)


def compare_structure(
    full_nodes: list[ASTNode],
    simplified_nodes: list[ASTNode],
    path: str = "root",
) -> DiffReport:
    """Recursively compare tree structure between Full AST and Simplified AST.

    Only compares structural properties (node_type, tag, text, visible,
    children count/order). Attribute differences are ignored.
    """
    report = DiffReport()
    _compare_node_lists(full_nodes, simplified_nodes, path, report)
    return report


def _compare_node_lists(
    full: list[ASTNode],
    simplified: list[ASTNode],
    path: str,
    report: DiffReport,
) -> None:
    if len(full) != len(simplified):
        report.diffs.append(
            StructureDiff(path, "children_count", len(full), len(simplified))
        )
        # Compare up to the shorter length, then stop
        min_len = min(len(full), len(simplified))
    else:
        min_len = len(full)

    for i in range(min_len):
        _compare_nodes(full[i], simplified[i], f"{path}[{i}]", report)


def _compare_nodes(
    full: ASTNode,
    simplified: ASTNode,
    path: str,
    report: DiffReport,
) -> None:
    report.nodes_compared += 1

    # node_type
    if full.node_type != simplified.node_type:
        report.diffs.append(
            StructureDiff(path, "node_type", full.node_type, simplified.node_type)
        )
        return  # no point comparing further if types differ

    # tag (element nodes)
    if full.node_type == "element":
        if full.tag != simplified.tag:
            report.diffs.append(
                StructureDiff(path, "tag", full.tag, simplified.tag)
            )

        # visible
        if full.visible != simplified.visible:
            report.diffs.append(
                StructureDiff(path, "visible", full.visible, simplified.visible)
            )

        # Recurse into children
        child_path = f"{path}/{full.tag or '?'}"
        _compare_node_lists(full.children, simplified.children, child_path, report)

    # text (text nodes)
    elif full.node_type == "text":
        if full.text != simplified.text:
            report.diffs.append(
                StructureDiff(path, "text", full.text, simplified.text)
            )

        if full.visible != simplified.visible:
            report.diffs.append(
                StructureDiff(path, "visible", full.visible, simplified.visible)
            )


# ---------------------------------------------------------------------------
# Helper: count nodes
# ---------------------------------------------------------------------------


def _count_nodes(nodes: list[ASTNode]) -> int:
    count = 0
    for n in nodes:
        count += 1
        count += _count_nodes(n.children)
    return count


# ---------------------------------------------------------------------------
# Unit tests with synthetic HTML
# ---------------------------------------------------------------------------


class TestSyntheticStructure:
    """Verify structural integrity on small, controlled HTML inputs."""

    def test_simple_paragraph(self):
        full = parse_html("<p>Hello</p>")
        simplified = simplify_ast(full)
        report = compare_structure(full.nodes, simplified.nodes)
        assert report.ok, report.summary()

    def test_nested_divs(self):
        full = parse_html("<div><div><div><span>deep</span></div></div></div>")
        simplified = simplify_ast(full)
        report = compare_structure(full.nodes, simplified.nodes)
        assert report.ok, report.summary()

    def test_siblings_order(self):
        full = parse_html("<ul><li>A</li><li>B</li><li>C</li></ul>")
        simplified = simplify_ast(full)
        report = compare_structure(full.nodes, simplified.nodes)
        assert report.ok, report.summary()

    def test_mixed_text_and_elements(self):
        full = parse_html("<p>Start <b>bold</b> middle <i>italic</i> end</p>")
        simplified = simplify_ast(full)
        report = compare_structure(full.nodes, simplified.nodes)
        assert report.ok, report.summary()

    def test_hidden_elements_preserved(self):
        full = parse_html(
            '<div>'
            '<p style="display:none">hidden1</p>'
            '<p style="visibility:hidden">hidden2</p>'
            '<p>visible</p>'
            '</div>'
        )
        simplified = simplify_ast(full)
        report = compare_structure(full.nodes, simplified.nodes)
        assert report.ok, report.summary()

    def test_empty_elements(self):
        full = parse_html("<div><br/><hr/><img src='x.png'/></div>")
        simplified = simplify_ast(full)
        report = compare_structure(full.nodes, simplified.nodes)
        assert report.ok, report.summary()

    def test_table_structure(self):
        full = parse_html(
            "<table><thead><tr><th>H1</th><th>H2</th></tr></thead>"
            "<tbody><tr><td>A</td><td>B</td></tr></tbody></table>"
        )
        simplified = simplify_ast(full)
        report = compare_structure(full.nodes, simplified.nodes)
        assert report.ok, report.summary()

    def test_form_elements(self):
        full = parse_html(
            '<form><input type="text" name="q" value="hello"/>'
            '<select><option value="1">One</option>'
            '<option value="2">Two</option></select>'
            '<textarea>content</textarea></form>'
        )
        simplified = simplify_ast(full)
        report = compare_structure(full.nodes, simplified.nodes)
        assert report.ok, report.summary()

    def test_iframe_subtree(self):
        full = parse_html(
            '<div><iframe src="frame.html"></iframe></div>',
            iframe_html={"frame.html": "<p>iframe <b>content</b></p>"},
        )
        simplified = simplify_ast(full)
        report = compare_structure(full.nodes, simplified.nodes)
        assert report.ok, report.summary()

    def test_nested_iframes(self):
        full = parse_html(
            '<iframe data-frame-id="outer"></iframe>',
            iframe_html={
                "outer": '<div>outer <iframe data-frame-id="inner"></iframe></div>',
                "inner": "<p>inner content</p>",
            },
        )
        simplified = simplify_ast(full)
        report = compare_structure(full.nodes, simplified.nodes)
        assert report.ok, report.summary()

    def test_heavily_attributed_html(self):
        """HTML with many attrs that get pruned — structure must survive."""
        full = parse_html(
            '<div class="flex items-center mt-4 bg-white rounded-lg shadow-md"'
            '     _ngcontent-abc="" ng-reflect-model="x" custom-thing="y">'
            '  <span class="text-sm text-gray-500 font-medium"'
            '        data-v-abc123="">Hello</span>'
            '  <button class="el-button px-4 py-2 rounded bg-blue-500 text-white"'
            '          onclick="nope" style="color:red">Click</button>'
            "</div>"
        )
        simplified = simplify_ast(full)
        report = compare_structure(full.nodes, simplified.nodes)
        assert report.ok, report.summary()

    def test_node_count_matches(self):
        full = parse_html(
            "<div><p>Hello <b>world</b></p><ul><li>A</li><li>B</li></ul></div>"
        )
        simplified = simplify_ast(full)
        full_count = _count_nodes(full.nodes)
        simplified_count = _count_nodes(simplified.nodes)
        assert full_count == simplified_count
        assert simplified.stats.node_count == full.node_count


# ---------------------------------------------------------------------------
# Fixture tests — real-world HTML
# ---------------------------------------------------------------------------


_ALL_FIXTURES = [
    "corporate-site.html",
    "admin-sidebar.html",
    "complex-nesting.html",
    "h5-mobile.html",
    "data-dashboard.html",
    "no-semantic-tags.html",
    "multi-nav.html",
    "nested-menu.html",
    "lottery-page.html",
]


def _load_fixture(name: str) -> str:
    path = FIXTURE_DIR / name
    if not path.exists():
        pytest.skip(f"Fixture {name} not found")
    return path.read_text(encoding="utf-8")


class TestFixtureStructuralIntegrity:
    """Run deep structural comparison on every real fixture."""

    @pytest.mark.parametrize("fixture", _ALL_FIXTURES)
    def test_structure_identical(self, fixture: str):
        html = _load_fixture(fixture)
        full = parse_html(html)
        simplified = simplify_ast(full)

        report = compare_structure(full.nodes, simplified.nodes)
        assert report.ok, (
            f"Fixture {fixture}:\n{report.summary()}"
        )

    @pytest.mark.parametrize("fixture", _ALL_FIXTURES)
    def test_node_count_identical(self, fixture: str):
        html = _load_fixture(fixture)
        full = parse_html(html)
        simplified = simplify_ast(full)

        full_count = _count_nodes(full.nodes)
        simplified_count = _count_nodes(simplified.nodes)
        assert full_count == simplified_count, (
            f"Fixture {fixture}: full has {full_count} nodes, "
            f"simplified has {simplified_count}"
        )

    @pytest.mark.parametrize("fixture", _ALL_FIXTURES)
    def test_text_content_identical(self, fixture: str):
        """All text nodes must have identical content and order."""
        html = _load_fixture(fixture)
        full = parse_html(html)
        simplified = simplify_ast(full)

        full_texts = _collect_texts(full.nodes)
        simplified_texts = _collect_texts(simplified.nodes)
        assert full_texts == simplified_texts, (
            f"Fixture {fixture}: text node mismatch"
        )

    @pytest.mark.parametrize("fixture", _ALL_FIXTURES)
    def test_visibility_identical(self, fixture: str):
        """All nodes' visible flags must match."""
        html = _load_fixture(fixture)
        full = parse_html(html)
        simplified = simplify_ast(full)

        full_vis = _collect_visibility(full.nodes)
        simplified_vis = _collect_visibility(simplified.nodes)
        assert full_vis == simplified_vis, (
            f"Fixture {fixture}: visibility mismatch"
        )


def _collect_texts(nodes: list[ASTNode]) -> list[str]:
    """Pre-order collection of all text node content."""
    result: list[str] = []
    for n in nodes:
        if n.node_type == "text" and n.text:
            result.append(n.text)
        result.extend(_collect_texts(n.children))
    return result


def _collect_visibility(nodes: list[ASTNode]) -> list[tuple[str, bool]]:
    """Pre-order collection of (identifier, visible) for every node."""
    result: list[tuple[str, bool]] = []
    for n in nodes:
        if n.node_type == "element":
            result.append((n.tag or "?", n.visible))
        else:
            result.append((f"#text:{n.text!r}", n.visible))
        result.extend(_collect_visibility(n.children))
    return result
