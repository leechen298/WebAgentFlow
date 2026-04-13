"""Server-side event → AST matcher.

Given a FullAST (the server-side authoritative page tree) and a list of
recording events, this module finds where each event's target lives in
the server AST.

This is the **server-side authoritative positioning** — it complements
(but does not replace) the client-side astMatch that the extension produces
at recording time. Downstream consumers (step_builder, agent_input) should
prefer server_ast_match when available and fall back to the client astMatch.

Scope:
  - Only events (click, input, change, richtext-input, navigate)
  - NOT mutations (future work)
  - No LLM calls — pure deterministic matching
  - No global nodeId system — uses path-based positioning
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.ast import ASTNode, FullAST

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

class ServerAstMatch(BaseModel):
    """Result of matching a single event to the server-side AST."""

    match_type: Literal["exact", "ancestor", "region", "none"] = "none"
    path: list[int] | None = Field(
        default=None,
        description="Index path from root, e.g. [0, 2, 1] means root_nodes[0].children[2].children[1].",
    )
    tag: str | None = None
    label: str | None = None
    region_hint: str | None = Field(
        default=None,
        description="Label/heading of the nearest containing region.",
    )
    confidence: Literal["high", "medium", "low"] = "low"


# ---------------------------------------------------------------------------
# Internal: AST indexing
# ---------------------------------------------------------------------------

class _IndexedNode:
    """A flattened reference to an element node in the AST."""

    __slots__ = ("node", "path", "text_content", "parent_idx")

    def __init__(
        self,
        node: ASTNode,
        path: list[int],
        text_content: str,
        parent_idx: int | None,
    ):
        self.node = node
        self.path = path
        self.text_content = text_content
        self.parent_idx = parent_idx


def _collect_text(node: ASTNode, max_len: int = 200) -> str:
    """Collect direct text content from a node's immediate text children."""
    parts: list[str] = []
    total = 0
    for child in node.children:
        if child.node_type == "text" and child.text:
            parts.append(child.text.strip())
            total += len(parts[-1])
            if total >= max_len:
                break
    return " ".join(parts)[:max_len]


def _build_index(ast: FullAST) -> list[_IndexedNode]:
    """Flatten the AST into an indexed list of element nodes."""
    result: list[_IndexedNode] = []

    def _walk(nodes: list[ASTNode], prefix: list[int], parent_idx: int | None) -> None:
        child_elem_idx = 0
        for child in nodes:
            if child.node_type != "element" or child.tag is None:
                continue
            path = prefix + [child_elem_idx]
            idx = len(result)
            text = _collect_text(child)
            result.append(_IndexedNode(child, path, text, parent_idx))
            _walk(child.children, path, idx)
            child_elem_idx += 1

    _walk(ast.nodes, [], None)
    return result


# ---------------------------------------------------------------------------
# Internal: selector parsing
# ---------------------------------------------------------------------------

_SELECTOR_RE = re.compile(
    r"^(?P<tag>[a-z][a-z0-9-]*)?"
    r"(?P<id>#[a-zA-Z0-9_-]+)?"
    r"(?P<classes>(?:\.[a-zA-Z0-9_-]+)*)"
)


def _parse_selector(selector: str | None) -> tuple[str | None, str | None, list[str]]:
    """Parse a simple CSS selector into (tag, id, classes).

    Only handles the simple selectors the extension produces:
    ``tag#id.cls1.cls2`` or subsets thereof.
    """
    if not selector:
        return None, None, []
    m = _SELECTOR_RE.match(selector)
    if not m:
        return None, None, []
    tag = m.group("tag") or None
    sel_id = m.group("id")
    sel_id = sel_id[1:] if sel_id else None  # strip leading #
    classes_str = m.group("classes") or ""
    classes = [c for c in classes_str.split(".") if c]
    return tag, sel_id, classes


# ---------------------------------------------------------------------------
# Internal: region detection
# ---------------------------------------------------------------------------

_REGION_TAGS = frozenset({"form", "section", "main", "aside", "nav", "header", "footer", "article"})
_HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})


def _find_region_hint(index: list[_IndexedNode], node_idx: int) -> str | None:
    """Walk up ancestors to find the nearest region label."""
    visited = 0
    cur = node_idx
    while cur is not None and visited < 20:
        entry = index[cur]
        node = entry.node
        tag = node.tag or ""
        role = node.attrs.get("role", "")

        is_region = (
            tag in _REGION_TAGS
            or role in ("region", "form", "navigation", "main", "complementary", "banner", "contentinfo")
        )

        if is_region:
            # Look for a heading/label in this region's direct children
            label = node.attrs.get("aria-label") or node.attrs.get("title") or ""
            if not label:
                for child in node.children:
                    if child.node_type == "element" and child.tag in _HEADING_TAGS:
                        label = _collect_text(child, 80)
                        break
            if not label:
                label = _collect_text(node, 60)
            return label.strip() or tag

        cur = entry.parent_idx
        visited += 1
    return None


# ---------------------------------------------------------------------------
# Internal: matching strategies
# ---------------------------------------------------------------------------

def _node_has_class(node: ASTNode, cls: str) -> bool:
    class_str = node.attrs.get("class", "")
    return cls in class_str.split()


def _match_by_id(index: list[_IndexedNode], target_id: str) -> _IndexedNode | None:
    """Find node by id attribute — strongest signal."""
    for entry in index:
        if entry.node.attrs.get("id") == target_id:
            return entry
    return None


def _match_by_name_and_tag(
    index: list[_IndexedNode], target_name: str, target_tag: str | None
) -> _IndexedNode | None:
    """Find node by name attribute, optionally constrained by tag."""
    for entry in index:
        if entry.node.attrs.get("name") == target_name:
            if target_tag is None or entry.node.tag == target_tag:
                return entry
    return None


def _match_by_selector(
    index: list[_IndexedNode],
    sel_tag: str | None,
    sel_id: str | None,
    sel_classes: list[str],
) -> _IndexedNode | None:
    """Match using parsed selector components."""
    if not sel_tag and not sel_id and not sel_classes:
        return None

    # If we have an id, use it directly
    if sel_id:
        return _match_by_id(index, sel_id)

    # Tag + classes
    best: _IndexedNode | None = None
    best_score = 0
    for entry in index:
        node = entry.node
        score = 0
        if sel_tag and node.tag == sel_tag:
            score += 1
        elif sel_tag and node.tag != sel_tag:
            continue  # tag mismatch → skip
        for cls in sel_classes:
            if _node_has_class(node, cls):
                score += 2
            else:
                score -= 5  # class mismatch penalty
        if score > best_score:
            best = entry
            best_score = score
    return best if best_score > 0 else None


def _match_by_tag_and_text(
    index: list[_IndexedNode],
    target_tag: str,
    target_text: str,
) -> _IndexedNode | None:
    """Match by tag + text content similarity."""
    target_text_lower = target_text.lower().strip()
    if not target_text_lower:
        return None

    for entry in index:
        if entry.node.tag != target_tag:
            continue
        node_text = entry.text_content.lower().strip()
        if not node_text:
            continue
        # Exact or substring match
        if target_text_lower == node_text or target_text_lower in node_text or node_text in target_text_lower:
            return entry
    return None


def _match_by_attrs(
    index: list[_IndexedNode],
    target_tag: str | None,
    attrs_to_check: dict[str, str],
) -> _IndexedNode | None:
    """Match by tag + specific attribute values (href, placeholder, role, etc.)."""
    if not attrs_to_check:
        return None

    best: _IndexedNode | None = None
    best_score = 0
    for entry in index:
        node = entry.node
        if target_tag and node.tag != target_tag:
            continue
        score = 0
        for key, val in attrs_to_check.items():
            node_val = node.attrs.get(key, "")
            if node_val and val and (node_val == val or val in node_val):
                score += 2
        if score > best_score:
            best = entry
            best_score = score
    return best if best_score > 0 else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def match_event_to_ast(
    event: dict[str, Any],
    index: list[_IndexedNode],
) -> ServerAstMatch:
    """Match a single recording event to a node in the indexed AST.

    Matching priority:
      1. target.id → attrs.id (exact, high)
      2. target.name + target.tag → attrs.name (exact, high)
      3. Parsed target.selector → tag + id + classes (exact, high/medium)
      4. target.tag + target.text → tag + text content (exact, medium)
      5. target.tag + attrs (placeholder, role, href, label) (exact, medium)
      6. fieldContext.fieldLabel + region-level search (region, low)
      7. No match → none
    """
    event_type = event.get("type", "")

    # navigate has no meaningful target node
    if event_type == "navigate":
        return ServerAstMatch(match_type="none", confidence="low")

    target = event.get("target") or {}
    if not target:
        return ServerAstMatch(match_type="none", confidence="low")

    tag = (target.get("tag") or "").lower()
    target_id = target.get("id") or ""
    target_name = target.get("name") or ""
    target_text = target.get("text") or ""
    target_selector = target.get("selector") or ""
    target_label = target.get("label") or ""
    target_placeholder = target.get("placeholder") or ""
    target_role = target.get("role") or ""
    target_nearby = target.get("nearbyText") or ""

    def _build_result(
        entry: _IndexedNode,
        match_type: Literal["exact", "ancestor", "region"] = "exact",
        confidence: Literal["high", "medium", "low"] = "medium",
    ) -> ServerAstMatch:
        idx = index.index(entry)
        region = _find_region_hint(index, idx)
        node_label = (
            entry.node.attrs.get("aria-label")
            or entry.node.attrs.get("title")
            or entry.text_content[:80]
            or None
        )
        return ServerAstMatch(
            match_type=match_type,
            path=entry.path,
            tag=entry.node.tag,
            label=node_label,
            region_hint=region,
            confidence=confidence,
        )

    # --- Strategy 1: id ---
    if target_id:
        hit = _match_by_id(index, target_id)
        if hit:
            return _build_result(hit, "exact", "high")

    # --- Strategy 2: name + tag ---
    if target_name:
        hit = _match_by_name_and_tag(index, target_name, tag or None)
        if hit:
            return _build_result(hit, "exact", "high")

    # --- Strategy 3: parsed selector ---
    sel_tag, sel_id, sel_classes = _parse_selector(target_selector)
    if sel_tag or sel_id or sel_classes:
        hit = _match_by_selector(index, sel_tag, sel_id, sel_classes)
        if hit:
            conf: Literal["high", "medium"] = "high" if sel_id else "medium"
            return _build_result(hit, "exact", conf)

    # --- Strategy 4: tag + text ---
    if tag and target_text:
        hit = _match_by_tag_and_text(index, tag, target_text)
        if hit:
            return _build_result(hit, "exact", "medium")

    # --- Strategy 5: tag + attrs ---
    check_attrs: dict[str, str] = {}
    if target_placeholder:
        check_attrs["placeholder"] = target_placeholder
    if target_role:
        check_attrs["role"] = target_role
    if target_label:
        check_attrs["aria-label"] = target_label
    href = target.get("href") or ""
    if href:
        check_attrs["href"] = href

    if tag and check_attrs:
        hit = _match_by_attrs(index, tag, check_attrs)
        if hit:
            return _build_result(hit, "exact", "medium")

    # --- Strategy 6: tag + nearbyText / fieldContext label → region fallback ---
    field_ctx = event.get("fieldContext") or {}
    field_label = field_ctx.get("fieldLabel") or target_nearby or target_label
    if tag and field_label:
        # Search for a node whose ancestor region contains this label
        label_lower = field_label.lower().strip()
        for entry in index:
            if entry.node.tag != tag:
                continue
            idx = index.index(entry)
            region = _find_region_hint(index, idx)
            if region and label_lower in region.lower():
                return ServerAstMatch(
                    match_type="region",
                    path=entry.path,
                    tag=entry.node.tag,
                    label=field_label,
                    region_hint=region,
                    confidence="low",
                )

    # --- No match ---
    return ServerAstMatch(match_type="none", confidence="low")


def build_ast_index(ast: FullAST) -> list[_IndexedNode]:
    """Build a flat index from a FullAST for repeated matching.

    Call once per page, then pass to match_event_to_ast() for each event.
    """
    return _build_index(ast)


def match_events_to_ast(
    events: list[dict[str, Any]],
    ast: FullAST,
) -> list[dict[str, Any]]:
    """Enhance a list of events with server_ast_match.

    Returns a **new** list of event dicts, each with an added
    ``server_ast_match`` key. Original events are not mutated.
    """
    index = build_ast_index(ast)
    result: list[dict[str, Any]] = []
    for ev in events:
        enhanced = dict(ev)  # shallow copy
        match = match_event_to_ast(ev, index)
        enhanced["server_ast_match"] = match.model_dump()
        result.append(enhanced)
    return result
