"""Interactive candidate element inference — rule-based MVP.

Walks a Full AST and scores each element node by structural, attribute,
semantic, and mutation-linkage signals to identify likely interactive
elements. Produces CandidateElement and InteractionHint lists for guided
exploration.

Phase 2 MVP: rule-driven only, no LLM, no execution.

Signal sources (10 layers):
  - AST structural: tag, role, aria-*, type, tabindex, contenteditable
  - AST class hints: btn, button, submit, tab, dropdown, menu, item, etc.
  - Component library: el-button, ant-btn, van-button, n-input, etc.
  - AST state: disabled, readonly, visible
  - Text intent: visible text / aria-label / title containing action words
    (提交, 保存, 搜索, submit, save, search, etc.)
  - Icon intent: class tokens / aria-label / alt containing icon keywords
    (search, add, edit, delete, close, download, etc.)
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

# ---------------------------------------------------------------------------
# Component library prefix detection
# ---------------------------------------------------------------------------

# Known UI library prefixes (tag or class prefix before the component suffix)
_COMPONENT_PREFIXES = frozenset({
    "el", "ant", "van", "n", "t", "ivu", "arco",
    "a", "v", "bp", "semi", "taro", "nut",
    "at", "u", "uni", "weui", "mui", "chakra",
})

# Component suffix → inferred actions
_COMPONENT_SUFFIX_ACTIONS: dict[str, list[str]] = {
    "button": ["click"],
    "btn": ["click"],
    "link": ["click"],
    "input": ["input"],
    "textarea": ["input"],
    "field": ["input"],
    "select": ["select"],
    "option": ["click"],
    "checkbox": ["toggle"],
    "radio": ["toggle"],
    "switch": ["toggle"],
    "slider": ["input"],
    "rate": ["click"],
    "upload": ["click"],
    "uploader": ["click"],
    "cascader": ["click"],
    "transfer": ["click"],
    "picker": ["click"],
    "date-picker": ["click"],
    "time-picker": ["click"],
    "color-picker": ["click"],
    "autocomplete": ["input"],
    "auto-complete": ["input"],
    "search": ["input"],
    "stepper": ["input"],
    "tab": ["click"],
    "tabs": ["click"],
    "tab-pane": ["click"],
    "menu": ["click"],
    "menu-item": ["click"],
    "submenu": ["click"],
    "sub-menu": ["click"],
    "dropdown": ["click"],
    "dropdown-item": ["click"],
    "dropdown-menu": ["click"],
    "collapse": ["toggle"],
    "collapse-item": ["toggle"],
    "tag": ["click"],
    "pagination": ["click"],
    "pager": ["click"],
    "dialog": ["click"],
    "modal": ["click"],
    "drawer": ["click"],
    "popover": ["hover"],
    "tooltip": ["hover"],
}

# Pre-compiled regex: matches "prefix-suffix" in tag name or class token
_COMPONENT_RE = re.compile(
    r"^(" + "|".join(re.escape(p) for p in sorted(_COMPONENT_PREFIXES, key=len, reverse=True))
    + r")[-]("
    + "|".join(re.escape(s) for s in sorted(_COMPONENT_SUFFIX_ACTIONS, key=len, reverse=True))
    + r")$",
    re.I,
)

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
# Text intent — action words that imply the element is an operation entry
# ---------------------------------------------------------------------------

# Chinese action keywords → inferred action
_TEXT_INTENT_ZH: dict[str, str] = {
    "提交": "click",
    "保存": "click",
    "确定": "click",
    "确认": "click",
    "下一步": "click",
    "上一步": "click",
    "查询": "click",
    "搜索": "click",
    "重置": "click",
    "导出": "click",
    "导入": "click",
    "新建": "click",
    "新增": "click",
    "添加": "click",
    "删除": "click",
    "移除": "click",
    "编辑": "click",
    "修改": "click",
    "返回": "click",
    "取消": "click",
    "关闭": "click",
    "更多": "click",
    "展开": "toggle",
    "收起": "toggle",
    "折叠": "toggle",
    "刷新": "click",
    "登录": "click",
    "注册": "click",
    "发送": "click",
    "上传": "click",
    "下载": "click",
    "复制": "click",
    "粘贴": "click",
    "筛选": "click",
    "过滤": "click",
    "排序": "click",
    "审批": "click",
    "同意": "click",
    "拒绝": "click",
    "撤回": "click",
}

# English action keywords → inferred action
_TEXT_INTENT_EN: dict[str, str] = {
    "submit": "click",
    "save": "click",
    "confirm": "click",
    "ok": "click",
    "next": "click",
    "previous": "click",
    "back": "click",
    "search": "click",
    "query": "click",
    "reset": "click",
    "export": "click",
    "import": "click",
    "create": "click",
    "add": "click",
    "new": "click",
    "delete": "click",
    "remove": "click",
    "edit": "click",
    "modify": "click",
    "update": "click",
    "cancel": "click",
    "close": "click",
    "more": "click",
    "expand": "toggle",
    "collapse": "toggle",
    "toggle": "toggle",
    "refresh": "click",
    "login": "click",
    "sign in": "click",
    "sign up": "click",
    "register": "click",
    "send": "click",
    "upload": "click",
    "download": "click",
    "copy": "click",
    "filter": "click",
    "sort": "click",
    "approve": "click",
    "reject": "click",
    "apply": "click",
}

# Attributes to check for text intent (in priority order)
_TEXT_INTENT_ATTRS = ("aria-label", "title", "alt", "name", "data-tooltip", "placeholder")

# ---------------------------------------------------------------------------
# Icon intent — class/attribute patterns that indicate icon-based actions
# ---------------------------------------------------------------------------

# Icon keywords found in class tokens, aria-label, alt, or filenames
_ICON_INTENT_KEYWORDS: dict[str, str] = {
    "search": "click",
    "add": "click",
    "plus": "click",
    "create": "click",
    "edit": "click",
    "pencil": "click",
    "pen": "click",
    "delete": "click",
    "trash": "click",
    "remove": "click",
    "close": "click",
    "times": "click",
    "download": "click",
    "upload": "click",
    "more": "click",
    "ellipsis": "click",
    "dots": "click",
    "next": "click",
    "prev": "click",
    "arrow": "click",
    "chevron": "click",
    "caret": "click",
    "back": "click",
    "forward": "click",
    "refresh": "click",
    "reload": "click",
    "sync": "click",
    "copy": "click",
    "clipboard": "click",
    "share": "click",
    "link": "click",
    "expand": "toggle",
    "collapse": "toggle",
    "eye": "toggle",
    "visibility": "toggle",
    "star": "toggle",
    "favorite": "toggle",
    "heart": "toggle",
    "like": "toggle",
    "bookmark": "toggle",
    "pin": "toggle",
    "lock": "toggle",
    "unlock": "toggle",
    "setting": "click",
    "gear": "click",
    "cog": "click",
    "config": "click",
    "filter": "click",
    "sort": "click",
    "menu": "click",
    "hamburger": "click",
    "drag": "click",
    "grip": "click",
    "handle": "click",
}

# Regex to match icon keywords in class tokens (word-boundary aware)
_ICON_KEYWORD_RE = re.compile(
    r"(?:^|[-_])("
    + "|".join(re.escape(k) for k in _ICON_INTENT_KEYWORDS)
    + r")(?:$|[-_])",
    re.I,
)


# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------

_SCORE_TAG = 0.35
_SCORE_ROLE = 0.25
_SCORE_CLASS_HINT = 0.10
_SCORE_ARIA = 0.10
_SCORE_TABINDEX = 0.05
_SCORE_CONTENTEDITABLE = 0.15
_SCORE_TEXT_INTENT = 0.30
_SCORE_ICON_INTENT = 0.15
_SCORE_COMPONENT_LIB = 0.25
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
    evidence_text_intent: str | None = None
    evidence_icon_intent: list[str] = field(default_factory=list)
    evidence_component_lib: str | None = None
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

    # --- Signal 4: Component library prefix ---
    comp_match = _match_component_lib(tag, class_str)
    if comp_match:
        prefix, suffix = comp_match
        score += _SCORE_COMPONENT_LIB
        actions.update(_COMPONENT_SUFFIX_ACTIONS.get(suffix, ["click"]))
        candidate.evidence_component_lib = f"{prefix}-{suffix}"

    # --- Signal 5: ARIA interactive attributes ---
    aria_evidence: dict[str, str] = {}
    for aria_attr in _ARIA_INTERACTIVE_ATTRS:
        if aria_attr in attrs:
            aria_evidence[aria_attr] = attrs[aria_attr]
    if aria_evidence:
        score += _SCORE_ARIA * min(len(aria_evidence), 3)
        candidate.evidence_aria = aria_evidence
        if not actions:
            actions.add("click")

    # --- Signal 6: tabindex ---
    if "tabindex" in attrs:
        try:
            ti = int(attrs["tabindex"])
            if ti >= 0:
                score += _SCORE_TABINDEX
                if not actions:
                    actions.add("click")
        except ValueError:
            pass

    # --- Signal 7: contenteditable ---
    if attrs.get("contenteditable", "").lower() in ("true", ""):
        if "contenteditable" in attrs:
            score += _SCORE_CONTENTEDITABLE
            actions.add("input")

    # --- Signal 8: Text intent ---
    text_intent = _extract_text_intent(node)
    if text_intent:
        word, action = text_intent
        score += _SCORE_TEXT_INTENT
        actions.add(action)
        candidate.evidence_text_intent = word

    # --- Signal 9: Icon intent ---
    icon_hits = _extract_icon_intent(node)
    if icon_hits:
        score += _SCORE_ICON_INTENT * min(len(icon_hits), 2)
        for _kw, icon_action in icon_hits:
            actions.add(icon_action)
        candidate.evidence_icon_intent = [kw for kw, _ in icon_hits]

    # --- Signal 10: Mutation linkage ---
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
# Component library detection
# ---------------------------------------------------------------------------

def _match_component_lib(tag: str, class_str: str) -> tuple[str, str] | None:
    """Match tag or class tokens against known component library patterns.

    Returns (prefix, suffix) if matched, e.g. ("el", "button"), or None.
    Checks the tag name first, then class tokens.
    """
    # 1. Check tag name (e.g. <el-button>, <van-cell>)
    m = _COMPONENT_RE.match(tag)
    if m:
        return m.group(1).lower(), m.group(2).lower()

    # 2. Check class tokens
    if class_str:
        for token in class_str.split():
            m = _COMPONENT_RE.match(token)
            if m:
                return m.group(1).lower(), m.group(2).lower()

    return None


# ---------------------------------------------------------------------------
# Text intent extraction
# ---------------------------------------------------------------------------

def _extract_text_intent(node: ASTNode) -> tuple[str, str] | None:
    """Extract action-word intent from element text and attributes.

    Checks (in order): aria-label, title, alt, name, data-tooltip,
    placeholder, then visible child text. Returns (matched_word, action)
    or None.
    """
    attrs = node.attrs

    # 1. Check label-like attributes first (most intentional)
    for attr_name in _TEXT_INTENT_ATTRS:
        val = attrs.get(attr_name, "").strip()
        if val:
            hit = _match_text_intent(val)
            if hit:
                return hit

    # 2. Check shallow visible text (direct text children only, not deep)
    text = _get_shallow_text(node)
    if text:
        hit = _match_text_intent(text)
        if hit:
            return hit

    return None


def _match_text_intent(text: str) -> tuple[str, str] | None:
    """Match text against known action words. Returns (word, action) or None."""
    normalized = text.strip().lower()
    if not normalized or len(normalized) > 50:
        return None

    # Chinese keywords — exact substring match
    for word, action in _TEXT_INTENT_ZH.items():
        if word in text:
            return word, action

    # English keywords — word-boundary match
    for word, action in _TEXT_INTENT_EN.items():
        if re.search(r"(?:^|\s|[-_])" + re.escape(word) + r"(?:$|\s|[-_])", normalized):
            return word, action

    return None


def _get_shallow_text(node: ASTNode, max_depth: int = 2) -> str:
    """Extract visible text from a node and its immediate children.

    Only goes max_depth levels deep to avoid pulling in huge subtree text.
    Limits total length to avoid noise from large containers.
    """
    parts: list[str] = []
    _collect_text(node, parts, 0, max_depth)
    result = " ".join(parts).strip()
    return result[:200] if result else ""


def _collect_text(
    node: ASTNode, parts: list[str], depth: int, max_depth: int,
) -> None:
    """Recursively collect text nodes up to max_depth."""
    if depth > max_depth:
        return
    for child in node.children:
        if child.node_type == "text" and child.text:
            stripped = child.text.strip()
            if stripped:
                parts.append(stripped)
        elif child.node_type == "element" and child.tag not in ("script", "style", "svg"):
            _collect_text(child, parts, depth + 1, max_depth)


# ---------------------------------------------------------------------------
# Icon intent extraction
# ---------------------------------------------------------------------------

def _extract_icon_intent(node: ASTNode) -> list[tuple[str, str]]:
    """Extract icon-based intent from class tokens and attributes.

    Returns list of (keyword, action) tuples.
    """
    hits: list[tuple[str, str]] = []
    seen: set[str] = set()
    attrs = node.attrs

    # 1. Check class tokens for icon keywords
    class_str = attrs.get("class", "")
    if class_str:
        for m in _ICON_KEYWORD_RE.finditer(class_str):
            kw = m.group(1).lower()
            if kw not in seen and kw in _ICON_INTENT_KEYWORDS:
                seen.add(kw)
                hits.append((kw, _ICON_INTENT_KEYWORDS[kw]))

    # 2. Check icon-related attributes
    for attr_name in ("aria-label", "title", "alt", "data-tooltip"):
        val = attrs.get(attr_name, "").strip().lower()
        if val:
            for kw, action in _ICON_INTENT_KEYWORDS.items():
                if kw in val and kw not in seen:
                    seen.add(kw)
                    hits.append((kw, action))

    # 3. Check src/href for icon filenames (img/svg use patterns)
    for src_attr in ("src", "href"):
        src = attrs.get(src_attr, "").lower()
        if src:
            for kw, action in _ICON_INTENT_KEYWORDS.items():
                if kw in src and kw not in seen:
                    seen.add(kw)
                    hits.append((kw, action))

    return hits[:5]


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
    if raw.evidence_component_lib:
        evidence["component_lib"] = raw.evidence_component_lib
    if raw.evidence_text_intent:
        evidence["text_intent"] = raw.evidence_text_intent
    if raw.evidence_icon_intent:
        evidence["icon_intent"] = raw.evidence_icon_intent
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
    if raw.evidence_component_lib:
        parts.append(f"component: {raw.evidence_component_lib}")
    if raw.evidence_aria:
        parts.append(f"aria attrs: {', '.join(raw.evidence_aria.keys())}")
    if raw.evidence_text_intent:
        parts.append(f"text intent: \"{raw.evidence_text_intent}\"")
    if raw.evidence_icon_intent:
        parts.append(f"icon intent: {', '.join(raw.evidence_icon_intent[:3])}")
    if raw.evidence_mutation_linkage:
        parts.append("linked to observed mutations")
    if not parts:
        parts.append("structural signal")
    return "; ".join(parts)


def _guess_expected_effect(raw: _CandidateRaw) -> str | None:
    """Guess expected effect based on element type and intent — rough heuristic."""
    tag = raw.tag
    attrs = raw.attrs
    role = attrs.get("role", "")

    # Text intent gives strong effect hints
    ti = raw.evidence_text_intent
    if ti:
        _SUBMIT_WORDS = {"提交", "保存", "确定", "确认", "submit", "save", "confirm", "ok", "apply"}
        _SEARCH_WORDS = {"搜索", "查询", "筛选", "过滤", "search", "query", "filter"}
        _NAV_WORDS = {"返回", "下一步", "上一步", "back", "next", "previous"}
        _DELETE_WORDS = {"删除", "移除", "delete", "remove"}
        _TOGGLE_WORDS = {"展开", "收起", "折叠", "expand", "collapse", "toggle"}
        if ti in _SUBMIT_WORDS:
            return "form submission"
        if ti in _SEARCH_WORDS:
            return "triggers search/filter"
        if ti in _NAV_WORDS:
            return "page navigation"
        if ti in _DELETE_WORDS:
            return "deletes item"
        if ti in _TOGGLE_WORDS:
            return "section expands/collapses"

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

    # Icon intent effect hints
    if raw.evidence_icon_intent:
        icon = raw.evidence_icon_intent[0]
        _ICON_EFFECTS: dict[str, str] = {
            "search": "triggers search",
            "add": "creates new item",
            "plus": "creates new item",
            "create": "creates new item",
            "edit": "opens editor",
            "pencil": "opens editor",
            "delete": "deletes item",
            "trash": "deletes item",
            "close": "closes current view",
            "times": "closes current view",
            "download": "downloads file",
            "upload": "opens file picker",
            "more": "shows more options",
            "ellipsis": "shows more options",
            "expand": "section expands",
            "collapse": "section collapses",
            "eye": "toggles visibility",
            "filter": "opens filter panel",
            "sort": "changes sort order",
            "refresh": "refreshes content",
            "copy": "copies to clipboard",
            "setting": "opens settings",
            "gear": "opens settings",
        }
        if icon in _ICON_EFFECTS:
            return _ICON_EFFECTS[icon]

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
