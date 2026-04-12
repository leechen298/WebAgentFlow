"""Full AST schema — faithful DOM representation.

The Full AST preserves the original HTML structure without semantic
interpretation or restructuring. Each HTML element becomes an ASTNode,
and text content becomes text-type ASTNodes. The tree faithfully represents:
- Original parent-child relationships
- Sibling order
- Key attributes
- Visibility state (from inline style / hidden attribute)
- iframe placeholder for separate content

This is the "fact layer" — downstream consumers can derive semantic
views (Simplified AST) from it, but the Full AST itself does not
reorganize, merge, or interpret the structure.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ASTNode(BaseModel):
    """A node in the Full AST tree.

    Either an HTML element (node_type="element") or a text node (node_type="text").
    """

    node_type: Literal["element", "text"] = "element"

    # --- Element fields ---
    tag: str | None = None
    """Lowercase HTML tag name. Only set for element nodes."""

    attrs: dict[str, str] = {}
    """HTML attributes. Noisy attributes (style, data-v-*, on*) are filtered out."""

    children: list[ASTNode] = []
    """Child nodes (elements and text) in DOM order."""

    # --- Text fields ---
    text: str | None = None
    """Text content. Set for text nodes; None for element nodes."""

    # --- Computed ---
    visible: bool = True
    """False when inline style contains display:none or visibility:hidden,
    or the hidden HTML attribute is present."""

    # --- Iframe ---
    frame_content: list[ASTNode] | None = None
    """For <iframe> elements: parsed AST of the iframe document body.
    None when iframe HTML was not provided or is cross-origin."""


ASTNode.model_rebuild()


class FullAST(BaseModel):
    """Top-level Full AST result."""

    nodes: list[ASTNode]
    """Top-level AST nodes from the parsed HTML body."""

    node_count: int = 0
    """Total number of nodes in the tree (elements + text)."""
