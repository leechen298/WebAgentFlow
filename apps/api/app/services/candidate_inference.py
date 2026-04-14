"""Interactive candidate element inference — rule-based MVP.

Walks a Full AST and scores each element node by structural, attribute,
and mutation-linkage signals to identify likely interactive elements.
Produces CandidateElement and InteractionHint lists for guided exploration.

Phase 2 MVP: rule-driven only, no LLM, no execution.

Signal sources:
  - AST structural: tag, role, aria-*, type, tabindex, contenteditable
  - AST class hints: btn, button, submit, tab, dropdown, menu, item, etc.
  - AST state: disabled, readonly, visible
  - Mutation linkage: whether the element (or nearby ancestors) appeared
    as mutation targets during recording
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.schemas.ast import ASTNode, FullAST

# ---------------------------------------------------------------------------
# Constants — signal definitions
# ---------------------------------------------------------------------------

# Tags that are natively interactive
_INTERACTIVE_TAGS: dict[str, list[str]] = {
    "button": ["click"],
    "a": ["click"],
    "input": ["input"],
    "textarea": ["input"],
    "select": ["select"],
    "details": ["toggle"],
    "summary": ["click"],
}

# Input types that map to specific actions
_INPUT_TYPE_ACTIONS: dict[str, list[str]] = {
    "submit": ["click"],
    "button": ["click"],
    "reset": ["click"],
    "checkbox": ["toggle"],
    "radio": ["toggle"],
    "file": ["click"],
    "image": ["click"],
    "color": ["click"],
    "range": ["input"],
}

# ARIA roles that imply interactivity
_INTERACTIVE_ROLES: dict[str, list[str]] = {
    "button": ["click"],
    "link": ["click"],
    "tab": ["click"],
    "menuitem": ["click"],
    "menuitemcheckbox": ["toggle"],
    "menuitemradio": ["toggle"],
    "option": ["click"],
    "switch": ["toggle"],
    "checkbox": ["toggle"],
    "radio": ["toggle"],
    "slider": ["input"],
    "spinbutton": ["input"],
    "searchbox": ["input"],
    "textbox": ["input"],
    "combobox": ["input", "click"],
    "listbox": ["select"],
    "treeitem": ["click"],
    "gridcell": ["click"],
}

# Class token patterns that hint at interactivity
_CLASS_HINT_PATTERNS: list[tuple[re.Pattern[str], list[str]]] = [
    (re.compile(r"(?:^|[-_])btn(?:$|[-_])", re.I), ["click"]),
    (re.compile(r"(?:^|[-_])button(?:$|[-_])", re.I), ["click"]),
    (re.compile(r"(?:^|[-_])submit(?:$|[-_])", re.I), ["click"]),
    (re.compile(r"(?:^|[-_])link(?:$|[-_])", re.I), ["click"]),
    (re.compile(r"(?:^|[-_])tab(?:$|[-_])", re.I), ["click"]),
    (re.compile(r"(?:^|[-_])dropdown(?:$|[-_])", re.I), ["click"]),
    (re.compile(r"(?:^|[-_])menu(?:$|[-_])", re.I), ["click"]),
    (re.compile(r"(?:^|[-_])item(?:$|[-_])", re.I), ["click"]),
    (re.compile(r"(?:^|[-_])toggle(?:$|[-_])", re.I), ["toggle"]),
    (re.compile(r"(?:^|[-_])switch(?:$|[-_])", re.I), ["toggle"]),
    (re.compile(r"(?:^|[-_])select(?:$|[-_])", re.I), ["select"]),
    (re.compile(r"(?:^|[-_])picker(?:$|[-_])", re.I), ["click"]),
    (re.compile(r"(?:^|[-_])input(?:$|[-_])", re.I), ["input"]),
    (re.compile(r"(?:^|[-_])search(?:$|[-_])", re.I), ["input"]),
    (re.compile(r"(?:^|[-_])clickable(?:$|[-_])", re.I), ["click"]),
    (re.compile(r"(?:^|[-_])hoverable(?:$|[-_])", re.I), ["hover"]),
]

# ARIA attributes that signal interactivity
_ARIA_INTERACTIVE_ATTRS = frozenset({
    "aria-expanded",
    "aria-haspopup",
    "aria-controls",
    "aria-pressed",
    "aria-checked",
    "aria-selected",
})


# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------

_SCORE_TAG = 0.35
_SCORE_ROLE = 0.25
_SCORE_CLASS_HINT = 0.10
_SCORE_ARIA = 0.10
_SCORE_TABINDEX = 0.05
_SCORE_CONTENTEDITABLE = 0.15
_SCORE_MUTATION_LINKAGE = 0.20

_PENALTY_DISABLED = -0.30
_PENALTY_HIDDEN = -0.40


# ---------------------------------------------------------------------------
# Internal types
# ---------------------------------------------------------------------------

@dataclass
class _CandidateRaw:
    """Internal candidate before final scoring."""

    path: list[int]
    tag: str
    attrs: dict[str, str]
    visible: bool
    actions: set[str] = field(default_factory=set)
    score: float = 0.0
    evidence_tag: str | None = None
    evidence_class_hints: list[str] = field(default_factory=list)
    evidence_role: str | None = None
    evidence_aria: dict[str, str] = field(default_factory=dict)
    evidence_mutation_linkage: bool = False


# ---------------------------------------------------------------------------
# Core inference
# ---------------------------------------------------------------------------

def infer_candidates(
    ast: FullAST,
    mutations: list[dict[str, Any]] | None = None,
    *,
    score_threshold: float = 0.10,
    max_candidates: int = 200,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Infer interactive candidate elements from a Full AST.

    Args:
        ast: Full AST from html_ast_parser.parse_html().
        mutations: Optional list of DomMutationRecord dicts from recording meta.
        score_threshold: Minimum score to include a candidate.
        max_candidates: Maximum number of candidates to return.

    Returns:
        Tuple of (candidate_elements, interaction_hints) matching the
        CandidateElement / InteractionHint shapes in shared-types.
    """
    # Build mutation target index for linkage scoring
    mutation_targets = _build_mutation_target_index(mutations or [])

    # Walk AST and collect raw candidates
    raw_candidates: list[_CandidateRaw] = []
    for i, node in enumerate(ast.nodes):
        _walk_node(node, [i], raw_candidates, mutation_targets)

    # Filter by threshold, sort by score desc, limit
    raw_candidates = [c for c in raw_candidates if c.score >= score_threshold]
    raw_candidates.sort(key=lambda c: c.score, reverse=True)
    raw_candidates = raw_candidates[:max_candidates]

    # Assign priority ranks
    candidates = []
    for rank, raw in enumerate(raw_candidates, start=1):
        candidates.append(_to_candidate_element(raw, rank))

    # Generate hints from top candidates
    hints = _generate_hints(raw_candidates)

    return candidates, hints


def _walk_node(
    node: ASTNode,
    path: list[int],
    out: list[_CandidateRaw],
    mutation_targets: set[str],
) -> None:
    """Recursively walk the AST and score each element node."""
    if node.node_type != "element" or not node.tag:
        return

    candidate = _score_node(node, path, mutation_targets)
    if candidate is not None:
        out.append(candidate)

    for i, child in enumerate(node.children):
        _walk_node(child, [*path, i], out, mutation_targets)


def _score_node(
    node: ASTNode,
    path: list[int],
    mutation_targets: set[str],
) -> _CandidateRaw | None:
    """Score a single element node. Returns None if clearly non-interactive."""
    tag = node.tag or ""
    attrs = node.attrs
    score = 0.0
    actions: set[str] = set()

    candidate = _CandidateRaw(
        path=list(path),
        tag=tag,
        attrs=dict(attrs),
        visible=node.visible,
    )

    # --- Signal 1: Native interactive tag ---
    if tag in _INTERACTIVE_TAGS:
        score += _SCORE_TAG
        actions.update(_INTERACTIVE_TAGS[tag])
        candidate.evidence_tag = tag

        # Refine input actions by type attribute
        if tag == "input":
            input_type = attrs.get("type", "text").lower()
            if input_type in _INPUT_TYPE_ACTIONS:
                actions = set(_INPUT_TYPE_ACTIONS[input_type])
            else:
                actions = {"input"}

    # --- Signal 2: ARIA role ---
    role = attrs.get("role", "").lower().strip()
    if role and role in _INTERACTIVE_ROLES:
        score += _SCORE_ROLE
        actions.update(_INTERACTIVE_ROLES[role])
        candidate.evidence_role = role

    # --- Signal 3: Class hints ---
    class_str = attrs.get("class", "")
    if class_str:
        matched_hints: list[str] = []
        for pattern, hint_actions in _CLASS_HINT_PATTERNS:
            if pattern.search(class_str):
                matched_hints.append(pattern.pattern)
                actions.update(hint_actions)
        if matched_hints:
            score += _SCORE_CLASS_HINT * min(len(matched_hints), 3)
            candidate.evidence_class_hints = _extract_matching_tokens(
                class_str, matched_hints
            )

    # --- Signal 4: ARIA interactive attributes ---
    aria_evidence: dict[str, str] = {}
    for aria_attr in _ARIA_INTERACTIVE_ATTRS:
        if aria_attr in attrs:
            aria_evidence[aria_attr] = attrs[aria_attr]
    if aria_evidence:
        score += _SCORE_ARIA * min(len(aria_evidence), 3)
        candidate.evidence_aria = aria_evidence
        if not actions:
            actions.add("click")

    # --- Signal 5: tabindex ---
    if "tabindex" in attrs:
        try:
            ti = int(attrs["tabindex"])
            if ti >= 0:
                score += _SCORE_TABINDEX
                if not actions:
                    actions.add("click")
        except ValueError:
            pass

    # --- Signal 6: contenteditable ---
    if attrs.get("contenteditable", "").lower() in ("true", ""):
        if "contenteditable" in attrs:
            score += _SCORE_CONTENTEDITABLE
            actions.add("input")

    # --- Signal 7: Mutation linkage ---
    node_key = _node_key(node, path)
    if node_key in mutation_targets:
        score += _SCORE_MUTATION_LINKAGE
        candidate.evidence_mutation_linkage = True

    # --- Penalties ---
    if attrs.get("disabled") is not None:
        score += _PENALTY_DISABLED
    if not node.visible:
        score += _PENALTY_HIDDEN

    # Skip if no interactive signal at all
    if score <= 0 and not actions:
        return None

    candidate.score = max(0.0, min(1.0, score))
    candidate.actions = actions
    return candidate


# ---------------------------------------------------------------------------
# Mutation linkage
# ---------------------------------------------------------------------------

def _build_mutation_target_index(
    mutations: list[dict[str, Any]],
) -> set[str]:
    """Build a set of mutation target keys for fast lookage.

    Extracts identifiable info from mutation records: tag+id, tag+class,
    tag+selector patterns.
    """
    targets: set[str] = set()
    for m in mutations:
        tag = (m.get("targetTag") or "").lower()
        if not tag:
            continue
        # By id
        tid = m.get("targetId")
        if tid:
            targets.add(f"id:{tid}")
        # By class
        tcls = m.get("targetClassName")
        if tcls:
            targets.add(f"class:{tcls}")
        # By tag
        targets.add(f"tag:{tag}")
    return targets


def _node_key(node: ASTNode, path: list[int]) -> str:
    """Generate lookup keys to check against mutation target index.

    Returns a single key; we check multiple key forms against the set.
    """
    # This is intentionally simple — just check by id first, then class
    nid = node.attrs.get("id")
    if nid:
        return f"id:{nid}"
    cls = node.attrs.get("class", "").split()
    if cls:
        return f"class:{cls[0]}"
    return f"tag:{node.tag}"


def _node_matches_mutation_targets(node: ASTNode, path: list[int], targets: set[str]) -> bool:
    """Check if a node matches any mutation target."""
    nid = node.attrs.get("id")
    if nid and f"id:{nid}" in targets:
        return True
    cls = node.attrs.get("class", "").split()
    for c in cls[:3]:
        if f"class:{c}" in targets:
            return True
    if f"tag:{node.tag}" in targets:
        return True
    return False


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _to_candidate_element(raw: _CandidateRaw, priority: int) -> dict[str, Any]:
    """Convert internal candidate to CandidateElement dict."""
    element_key = _make_element_key(raw)
    evidence: dict[str, Any] = {}
    if raw.evidence_tag:
        evidence["tag"] = raw.evidence_tag
    if raw.evidence_class_hints:
        evidence["class_hints"] = raw.evidence_class_hints
    if raw.evidence_role:
        evidence["role"] = raw.evidence_role
    if raw.evidence_aria:
        evidence["aria"] = raw.evidence_aria
    if raw.evidence_mutation_linkage:
        evidence["mutation_linkage"] = True

    return {
        "element_key": element_key,
        "inferred_actions": sorted(raw.actions),
        "score": round(raw.score, 3),
        "evidence": evidence,
        "priority": priority,
    }


def _generate_hints(
    candidates: list[_CandidateRaw],
    max_hints: int = 30,
) -> list[dict[str, Any]]:
    """Generate InteractionHint list from top candidates.

    Groups by primary action type and picks the best candidates for each.
    """
    hints: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    for raw in candidates:
        if len(hints) >= max_hints:
            break
        key = _make_element_key(raw)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        primary_action = _pick_primary_action(raw)
        reason = _build_reason(raw)
        expected_effect = _guess_expected_effect(raw)

        hints.append({
            "element_key": key,
            "action": primary_action,
            "reason": reason,
            "expected_effect": expected_effect,
            "priority": len(hints) + 1,
        })

    return hints


def _make_element_key(raw: _CandidateRaw) -> str:
    """Build a human-readable element key."""
    tag = raw.tag
    nid = raw.attrs.get("id")
    if nid:
        return f"{tag}#{nid}"
    role = raw.attrs.get("role")
    if role:
        label = (
            raw.attrs.get("aria-label")
            or raw.attrs.get("title")
            or raw.attrs.get("name")
            or ""
        )
        if label:
            return f"{tag}[role={role}][{label}]"
        return f"{tag}[role={role}]@{'.'.join(str(i) for i in raw.path)}"
    name = raw.attrs.get("name")
    if name:
        return f"{tag}[name={name}]"
    # Fallback: tag + path
    return f"{tag}@{'.'.join(str(i) for i in raw.path)}"


def _pick_primary_action(raw: _CandidateRaw) -> str:
    """Pick the single most likely action for a hint."""
    # Priority: input > select > toggle > click > hover
    for pref in ("input", "select", "toggle", "click", "hover"):
        if pref in raw.actions:
            return pref
    return "click"


def _build_reason(raw: _CandidateRaw) -> str:
    """Build a short human-readable reason string."""
    parts: list[str] = []
    if raw.evidence_tag:
        parts.append(f"native <{raw.evidence_tag}> element")
    if raw.evidence_role:
        parts.append(f"role=\"{raw.evidence_role}\"")
    if raw.evidence_class_hints:
        parts.append(f"class hints: {', '.join(raw.evidence_class_hints[:3])}")
    if raw.evidence_aria:
        parts.append(f"aria attrs: {', '.join(raw.evidence_aria.keys())}")
    if raw.evidence_mutation_linkage:
        parts.append("linked to observed mutations")
    if not parts:
        parts.append("structural signal")
    return "; ".join(parts)


def _guess_expected_effect(raw: _CandidateRaw) -> str | None:
    """Guess expected effect based on element type — rough heuristic."""
    tag = raw.tag
    attrs = raw.attrs
    role = attrs.get("role", "")

    if tag == "a" and attrs.get("href"):
        return "navigation"
    if attrs.get("type") == "submit" or "submit" in attrs.get("class", ""):
        return "form submission"
    if attrs.get("aria-haspopup"):
        return "popup/dropdown opens"
    if attrs.get("aria-expanded") is not None:
        return "section expands/collapses"
    if role == "tab":
        return "tab panel switches"
    if tag == "select":
        return "dropdown options appear"
    if tag in ("input", "textarea"):
        return "accepts text input"
    if raw.evidence_mutation_linkage:
        return "DOM changes observed in previous recording"
    return None


def _extract_matching_tokens(class_str: str, patterns: list[str]) -> list[str]:
    """Extract class tokens that matched hint patterns."""
    tokens = class_str.split()
    matched: list[str] = []
    for token in tokens:
        for p in patterns:
            if re.search(p, token, re.I):
                matched.append(token)
                break
    return matched[:5]
