"""Full AST → Simplified AST projection.

Produces a structure-preserving projection of the Full AST:
1. Class token filtering — removes Tailwind/atomic CSS, hash/runtime noise
2. Attribute filtering — whitelist of semantically valuable attrs

The tree structure is NEVER modified: same nodes, same children order,
same sibling order, same parent-child boundaries.

Class filtering and attrs filtering are implemented as separate functions.
"""

from __future__ import annotations

import re

from app.schemas.ast import ASTNode, FullAST, SimplifiedAST, SimplifyStats

# ===================================================================
# Class token filtering
# ===================================================================

# Exact-match single-word Tailwind/atomic utilities
_UTILITY_EXACT: frozenset[str] = frozenset({
    # Layout / display
    "flex", "grid", "block", "inline-block", "inline", "inline-flex", "inline-grid",
    "contents", "flow-root", "list-item",
    # Position
    "static", "fixed", "absolute", "relative", "sticky",
    # Visibility (as utility, not semantic)
    "visible", "invisible", "collapse",
    # Hide (Tailwind utility)
    "hidden",
    # Misc layout
    "isolate", "truncate", "container",
    # Typography style
    "antialiased", "subpixel-antialiased",
    "italic", "not-italic",
    "uppercase", "lowercase", "capitalize", "normal-case",
    "underline", "overline", "line-through", "no-underline",
    # Accessibility
    "sr-only", "not-sr-only",
    # Bare keywords
    "rounded", "shadow", "border", "transition", "transform",
    # Flex
    "grow", "grow-0", "shrink", "shrink-0",
    # Float / clear
    "float-left", "float-right", "float-none",
    "clear-left", "clear-right", "clear-both", "clear-none",
    # Box sizing
    "box-border", "box-content",
})

# Regex patterns for structured Tailwind utilities
_UTILITY_PATTERNS: list[re.Pattern[str]] = [
    # Spacing: m-2, mt-4, px-8, -mb-1, py-[12px]
    re.compile(r"^-?[mp][trblxyse]?-(?:\d|auto|\[)"),
    # Sizing: w-full, h-screen, min-w-0, max-h-[200px]
    re.compile(r"^(?:min-|max-)?[wh]-(?:\d|auto|full|screen|min|max|fit|svh|dvh|lvh|\[|px)"),
    re.compile(r"^size-"),
    # Gap / space
    re.compile(r"^(?:gap|space-[xy])-"),
    # Position offsets: top-0, -left-2, inset-x-0
    re.compile(r"^-?(?:top|right|bottom|left|inset(?:-[xy])?)-"),
    # Flex/grid alignment: items-center, justify-between, etc.
    re.compile(
        r"^(?:items|justify|content|self|place)-"
        r"(?:start|end|center|between|around|evenly|stretch|baseline|auto)$"
    ),
    # Flex/grid detail: flex-row, grid-cols-3, col-span-2
    re.compile(r"^(?:flex|grid|col|row|auto-cols|auto-rows|grid-cols|grid-rows|col-span|row-span)-"),
    # Text size: text-sm, text-2xl
    re.compile(r"^text-(?:xs|sm|base|lg|xl|[2-9]xl)$"),
    # Text alignment: text-left, text-center
    re.compile(r"^text-(?:left|center|right|justify|start|end|wrap|nowrap|balance|pretty)$"),
    # Font weight: font-medium, font-bold
    re.compile(
        r"^font-(?:thin|extralight|light|normal|medium|semibold|bold|extrabold|black)$"
    ),
    # Leading / tracking
    re.compile(r"^(?:leading|tracking)-"),
    # Border/rounded/shadow with values
    re.compile(r"^(?:rounded|shadow|border)-"),
    # Z-index, opacity, order with numeric values
    re.compile(r"^(?:z|opacity|order)-\d"),
    # Overflow
    re.compile(r"^overflow-(?:[xy]-)?(?:auto|hidden|visible|scroll|clip)$"),
    # Cursor
    re.compile(r"^cursor-"),
    # Transition / animation
    re.compile(r"^(?:transition|duration|delay|ease|animate)-"),
    # Transform detail
    re.compile(r"^(?:rotate|scale|translate|skew)-"),
    # Misc utilities
    re.compile(r"^(?:object|pointer-events|select|resize|whitespace|break|hyphens|appearance)-"),
    re.compile(r"^(?:float|clear)-"),
    re.compile(r"^(?:decoration|underline-offset)-"),
    re.compile(r"^align-"),
    re.compile(r"^basis-"),
    re.compile(r"^order-(?:\d|first|last|none)"),
    re.compile(r"^(?:ring|outline)-"),
    re.compile(r"^(?:columns|divide|table)-"),
    re.compile(r"^(?:fill|stroke)-"),
    re.compile(r"^(?:backdrop|blur|brightness|contrast|grayscale|invert|saturate|sepia)-"),
    re.compile(r"^(?:scroll|snap|touch|will-change|accent|caret)-"),
    re.compile(r"^aspect-"),
    re.compile(r"^list-(?:none|disc|decimal|inside|outside|image)"),
]

# Tailwind color names — used to detect color utilities like text-red-500, bg-blue
_TW_COLORS: frozenset[str] = frozenset({
    "inherit", "current", "transparent", "black", "white",
    "slate", "gray", "zinc", "neutral", "stone",
    "red", "orange", "amber", "yellow", "lime", "green", "emerald",
    "teal", "cyan", "sky", "blue", "indigo", "violet", "purple",
    "fuchsia", "pink", "rose",
})

_COLOR_PREFIXES: tuple[str, ...] = (
    "text-", "bg-", "border-", "ring-", "outline-", "shadow-",
    "accent-", "fill-", "stroke-", "decoration-", "caret-", "placeholder-",
    "from-", "via-", "to-",
)

# Hash / runtime class prefixes
_HASH_PREFIXES: tuple[str, ...] = ("css-", "jsx-", "sc-")


def _is_tw_color_class(token: str) -> bool:
    """Check if token is a Tailwind color utility like text-red-500, bg-blue."""
    for prefix in _COLOR_PREFIXES:
        if token.startswith(prefix):
            rest = token[len(prefix) :]
            color = rest.split("-", 1)[0]
            if color in _TW_COLORS:
                return True
    return False


def _is_noise_class_token(token: str) -> bool:
    """Return True if the class token is low-value noise to be removed."""
    if token in _UTILITY_EXACT:
        return True
    for pattern in _UTILITY_PATTERNS:
        if pattern.match(token):
            return True
    if _is_tw_color_class(token):
        return True
    for prefix in _HASH_PREFIXES:
        if token.startswith(prefix):
            return True
    # Negative utilities: -mt-2 → check mt-2
    if token.startswith("-") and len(token) > 2:
        return _is_noise_class_token(token[1:])
    return False


def filter_class_tokens(class_str: str) -> tuple[str | None, int]:
    """Filter class string, removing noise tokens.

    Returns (filtered_class_or_None, removed_count).
    """
    tokens = class_str.split()
    kept: list[str] = []
    removed = 0
    for t in tokens:
        if _is_noise_class_token(t):
            removed += 1
        else:
            kept.append(t)
    return (" ".join(kept) if kept else None, removed)


# ===================================================================
# Attribute filtering
# ===================================================================

# Whitelist: attrs to keep (by exact name)
_KEEP_ATTRS: frozenset[str] = frozenset({
    "id", "class",
    "role", "name", "title", "placeholder", "label", "summary",
    "href", "src", "alt", "for", "action", "method", "target",
    "type", "value", "checked", "selected", "disabled", "readonly", "required",
    "hidden", "contenteditable", "tabindex",
    "min", "max", "step", "pattern", "maxlength", "minlength",
    "multiple", "autofocus",
    "width", "height", "rows", "cols",
    "colspan", "rowspan", "scope", "headers",
    "open", "loading", "slot", "is",
    "autocomplete", "spellcheck", "inputmode",
    "accept", "capture", "download", "rel",
    "dir", "lang", "translate",
    "controls", "autoplay", "loop", "muted", "preload",
    "wrap", "size", "list",
    "start", "reversed",
    "cite", "datetime",
    "form", "formaction", "formmethod",
})

# Attr prefixes to always keep
_KEEP_ATTR_PREFIXES: tuple[str, ...] = ("aria-", "data-")


def _should_keep_attr(name: str) -> bool:
    """Decide if an attribute should be kept in Simplified AST."""
    if name in _KEEP_ATTRS:
        return True
    for prefix in _KEEP_ATTR_PREFIXES:
        if name.startswith(prefix):
            return True
    return False


def filter_attrs(attrs: dict[str, str]) -> tuple[dict[str, str], int, int]:
    """Filter attributes for Simplified AST.

    Class tokens are filtered separately from other attrs.

    Returns (filtered_attrs, attrs_removed_count, class_tokens_removed_count).
    """
    result: dict[str, str] = {}
    attrs_removed = 0
    class_tokens_removed = 0

    for name, value in attrs.items():
        if name == "class":
            filtered_class, removed = filter_class_tokens(value)
            class_tokens_removed += removed
            if filtered_class:
                result["class"] = filtered_class
            else:
                # All class tokens were noise — drop the attr entirely
                attrs_removed += 1
        elif _should_keep_attr(name):
            result[name] = value
        else:
            attrs_removed += 1

    return result, attrs_removed, class_tokens_removed


# ===================================================================
# Projection: Full AST → Simplified AST
# ===================================================================


def _simplify_node(
    node: ASTNode,
    stats: _MutableStats,
) -> ASTNode:
    """Create a simplified copy of an ASTNode (recursive)."""
    if node.node_type == "text":
        return ASTNode(node_type="text", text=node.text, visible=node.visible)

    filtered_attrs, a_removed, c_removed = filter_attrs(node.attrs)
    stats.attrs_removed += a_removed
    stats.class_tokens_removed += c_removed

    simplified_children = [_simplify_node(ch, stats) for ch in node.children]

    return ASTNode(
        node_type="element",
        tag=node.tag,
        attrs=filtered_attrs,
        children=simplified_children,
        visible=node.visible,
    )


class _MutableStats:
    __slots__ = ("attrs_removed", "class_tokens_removed")

    def __init__(self) -> None:
        self.attrs_removed = 0
        self.class_tokens_removed = 0


def simplify_ast(full: FullAST) -> SimplifiedAST:
    """Project a Full AST into a Simplified AST.

    Structure-preserving: same tree shape, same children order, same siblings.
    Only attrs and class tokens are pruned.
    """
    stats = _MutableStats()
    simplified_nodes = [_simplify_node(n, stats) for n in full.nodes]

    return SimplifiedAST(
        nodes=simplified_nodes,
        stats=SimplifyStats(
            node_count=full.node_count,
            attrs_removed=stats.attrs_removed,
            class_tokens_removed=stats.class_tokens_removed,
        ),
    )
