"""HTML → Full AST parser.

Uses lxml.html for robust HTML parsing, then walks the lxml tree to produce
the project's Full AST (ASTNode tree). This is the server-side replacement
for the client-side DOM walker.

Design principles:
- Faithful to the HTML structure — no semantic interpretation or restructuring
- Text nodes preserved in DOM order (lxml text/tail model → explicit text nodes)
- Visibility derived from inline style / hidden attribute only
- Skip tags: script, style, svg, noscript, template, link, meta, head, base, title
- Attributes filtered: style (after visibility extraction), data-v-*, on* handlers
"""

from __future__ import annotations

import re

from lxml import html as lxml_html
from lxml.html import HtmlElement

from app.schemas.ast import ASTNode, FullAST

# Tags to skip entirely — no AST node produced for these
SKIP_TAGS: frozenset[str] = frozenset({
    "script", "style", "svg", "noscript", "template",
    "link", "meta", "head", "base", "title",
})

# Regex for visibility in inline style
_DISPLAY_NONE_RE = re.compile(r"display\s*:\s*none", re.IGNORECASE)
_VISIBILITY_HIDDEN_RE = re.compile(r"visibility\s*:\s*hidden", re.IGNORECASE)


def _should_skip_attr(name: str) -> bool:
    """Return True if this attribute should be filtered from the AST."""
    if name == "style":
        return True
    # Vue scoped CSS hashes: data-v-abc123
    if name.startswith("data-v-"):
        return True
    # Event handlers: onclick, onmouseover, onload, etc.
    if name.startswith("on") and len(name) > 2 and name[2:3].islower():
        return True
    return False


def _filter_attrs(element: HtmlElement) -> dict[str, str]:
    """Extract and filter attributes from an lxml element."""
    attrs: dict[str, str] = {}
    for name, value in element.attrib.items():
        if not _should_skip_attr(name):
            attrs[name] = value if value is not None else ""
    return attrs


def _check_visibility(element: HtmlElement) -> bool:
    """Check if element is visible based on inline style and hidden attribute."""
    if element.get("hidden") is not None:
        return False
    style = element.get("style", "")
    if style:
        if _DISPLAY_NONE_RE.search(style):
            return False
        if _VISIBILITY_HIDDEN_RE.search(style):
            return False
    return True


def _make_text_node(text: str) -> ASTNode | None:
    """Create a text ASTNode from raw HTML text (lxml text/tail).

    Returns None for whitespace-only text. Otherwise normalizes whitespace
    to match browser text rendering in normal flow.
    """
    if not text or not text.strip():
        return None
    # Collapse runs of whitespace (including newlines) to single spaces
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return None
    return ASTNode(node_type="text", text=normalized)


class _Counter:
    """Mutable counter for tracking node count during tree walk."""

    __slots__ = ("n",)

    def __init__(self) -> None:
        self.n: int = 0


def _walk_element(
    el: HtmlElement,
    counter: _Counter,
    iframe_html: dict[str, str] | None,
    max_nodes: int,
    max_depth: int,
    depth: int,
) -> ASTNode | None:
    """Convert an lxml element to an ASTNode, recursively."""
    tag = el.tag if isinstance(el.tag, str) else ""
    tag_lower = tag.lower()

    if tag_lower in SKIP_TAGS:
        return None

    if counter.n >= max_nodes or depth >= max_depth:
        return None

    counter.n += 1

    # Build children list, interleaving text nodes in DOM order.
    # lxml model: el.text is before first child; child.tail is after child.
    children: list[ASTNode] = []

    if el.text:
        tn = _make_text_node(el.text)
        if tn:
            counter.n += 1
            children.append(tn)

    for child in el:
        # lxml represents comments / processing instructions with callable tags
        if not isinstance(child.tag, str):
            if child.tail:
                tn = _make_text_node(child.tail)
                if tn:
                    counter.n += 1
                    children.append(tn)
            continue

        child_node = _walk_element(
            child, counter, iframe_html, max_nodes, max_depth, depth + 1
        )
        if child_node is not None:
            children.append(child_node)

        # tail text comes after the child element, before the next sibling
        if child.tail:
            tn = _make_text_node(child.tail)
            if tn:
                counter.n += 1
                children.append(tn)

    attrs = _filter_attrs(el)
    visible = _check_visibility(el)

    node = ASTNode(
        node_type="element",
        tag=tag_lower,
        attrs=attrs,
        children=children,
        visible=visible,
    )

    # Handle iframe: attach frame document as subtree via <frame-body> wrapper
    if tag_lower == "iframe" and iframe_html:
        src = el.get("src", "")
        frame_id = el.get("data-frame-id", "")
        iframe_content_html = iframe_html.get(frame_id) or iframe_html.get(src)
        if iframe_content_html:
            parsed = parse_html(iframe_content_html, iframe_html=iframe_html)
            if parsed.nodes:
                frame_attrs: dict[str, str] = {}
                if src:
                    frame_attrs["data-frame-src"] = src
                if frame_id:
                    frame_attrs["data-frame-id"] = frame_id
                frame_body = ASTNode(
                    node_type="element",
                    tag="frame-body",
                    attrs=frame_attrs,
                    children=parsed.nodes,
                )
                node.children.append(frame_body)

    return node


def parse_html(
    html_str: str,
    *,
    iframe_html: dict[str, str] | None = None,
    max_nodes: int = 10_000,
    max_depth: int = 100,
) -> FullAST:
    """Parse an HTML string into a Full AST.

    Args:
        html_str: The HTML to parse. Can be a fragment or a full document.
        iframe_html: Optional mapping of iframe identifiers (src URL or
            data-frame-id) to their HTML content strings. Parsed and
            attached as a <frame-body> subtree inside <iframe> nodes.
        max_nodes: Maximum number of AST nodes to produce before stopping.
        max_depth: Maximum nesting depth.

    Returns:
        FullAST with the parsed node tree.
    """
    if not html_str or not html_str.strip():
        return FullAST(nodes=[], node_count=0)

    try:
        doc = lxml_html.document_fromstring(html_str)
    except Exception:
        return FullAST(nodes=[], node_count=0)

    counter = _Counter()

    body = doc.find(".//body")
    if body is None:
        body = doc

    # Walk children of body to produce top-level nodes
    nodes: list[ASTNode] = []

    if body.text:
        tn = _make_text_node(body.text)
        if tn:
            counter.n += 1
            nodes.append(tn)

    for child in body:
        if not isinstance(child.tag, str):
            if child.tail:
                tn = _make_text_node(child.tail)
                if tn:
                    counter.n += 1
                    nodes.append(tn)
            continue

        node = _walk_element(
            child, counter, iframe_html, max_nodes, max_depth, 0
        )
        if node is not None:
            nodes.append(node)

        if child.tail:
            tn = _make_text_node(child.tail)
            if tn:
                counter.n += 1
                nodes.append(tn)

    return FullAST(nodes=nodes, node_count=counter.n)
