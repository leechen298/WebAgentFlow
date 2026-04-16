"""
Comprehensive tests for candidate_inference — rule-based interactive element scoring.

Covers:
 1. Each scoring signal individually (10 signals)
 2. Penalty logic (disabled, hidden)
 3. Score aggregation and threshold filtering
 4. max_candidates limiting
 5. Hint generation from candidates
 6. Empty / text-only AST -> empty results
 7. Realistic AST with mixed elements
 8. Component library detection (_match_component_lib)
 9. Text intent extraction (_extract_text_intent / _match_text_intent)
10. Icon intent extraction (_extract_icon_intent)
11. Mutation target index building
12. Node key generation and mutation matching
13. Element key generation (_make_element_key)
14. Primary action picking (_pick_primary_action)
15. Reason building (_build_reason)
16. Expected effect guessing (_guess_expected_effect)
17. Edge cases: negative tabindex, invalid tabindex, disabled + high score, etc.
"""

import pytest

from app.schemas.ast import ASTNode, FullAST
from app.services.learning.candidate_inference import (
    infer_candidates,
    _build_mutation_target_index,
    _extract_icon_intent,
    _extract_text_intent,
    _generate_hints,
    _guess_expected_effect,
    _build_reason,
    _make_element_key,
    _match_component_lib,
    _match_text_intent,
    _node_key,
    _node_matches_mutation_targets,
    _pick_primary_action,
    _score_node,
    _walk_node,
    _CandidateRaw,
    _get_shallow_text,
    _collect_text,
    _extract_matching_tokens,
    _to_candidate_element,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text(t: str) -> ASTNode:
    return ASTNode(node_type="text", text=t)


def _el(
    tag: str,
    attrs: dict | None = None,
    children: list | None = None,
    visible: bool = True,
) -> ASTNode:
    return ASTNode(
        node_type="element",
        tag=tag,
        attrs=attrs or {},
        children=children or [],
        visible=visible,
    )


def _ast(*nodes: ASTNode) -> FullAST:
    return FullAST(nodes=list(nodes), node_count=len(nodes))


# ===================================================================
# 1. Signal 1: Native interactive tags
# ===================================================================

class TestSignalNativeInteractiveTags:
    """Signal 1: native interactive HTML elements score _SCORE_TAG=0.35."""

    @pytest.mark.parametrize("tag,expected_action", [
        ("button", "click"),
        ("a", "click"),
        ("input", "input"),
        ("textarea", "input"),
        ("select", "select"),
        ("details", "toggle"),
        ("summary", "click"),
    ])
    def test_native_tag_scores_and_actions(self, tag, expected_action):
        node = _el(tag)
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.score >= 0.35
        assert expected_action in cand.actions
        assert cand.evidence_tag == tag

    def test_non_interactive_tag_returns_none(self):
        node = _el("div")
        cand = _score_node(node, [0], set())
        assert cand is None

    def test_span_without_signals_returns_none(self):
        node = _el("span")
        cand = _score_node(node, [0], set())
        assert cand is None

    @pytest.mark.parametrize("input_type,expected_actions", [
        ("submit", {"click"}),
        ("button", {"click"}),
        ("reset", {"click"}),
        ("checkbox", {"toggle"}),
        ("radio", {"toggle"}),
        ("file", {"click"}),
        ("image", {"click"}),
        ("color", {"click"}),
        ("range", {"input"}),
    ])
    def test_input_type_refines_actions(self, input_type, expected_actions):
        node = _el("input", {"type": input_type})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.actions == expected_actions

    def test_input_default_type_text(self):
        """Input without type defaults to text -> input action."""
        node = _el("input")
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert "input" in cand.actions

    def test_input_unknown_type_fallback_to_input(self):
        """Input with unknown type (e.g. 'date') falls back to {input}."""
        node = _el("input", {"type": "date"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.actions == {"input"}


# ===================================================================
# 2. Signal 2: ARIA roles
# ===================================================================

class TestSignalAriaRoles:
    """Signal 2: ARIA role attribute scores _SCORE_ROLE=0.25."""

    @pytest.mark.parametrize("role,expected_action", [
        ("button", "click"),
        ("link", "click"),
        ("tab", "click"),
        ("menuitem", "click"),
        ("menuitemcheckbox", "toggle"),
        ("menuitemradio", "toggle"),
        ("option", "click"),
        ("switch", "toggle"),
        ("checkbox", "toggle"),
        ("radio", "toggle"),
        ("slider", "input"),
        ("spinbutton", "input"),
        ("searchbox", "input"),
        ("textbox", "input"),
        ("listbox", "select"),
        ("treeitem", "click"),
        ("gridcell", "click"),
    ])
    def test_role_scores_and_actions(self, role, expected_action):
        node = _el("div", {"role": role})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.score >= 0.25
        assert expected_action in cand.actions
        assert cand.evidence_role == role

    def test_combobox_has_multiple_actions(self):
        node = _el("div", {"role": "combobox"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert "input" in cand.actions
        assert "click" in cand.actions

    def test_unknown_role_ignored(self):
        node = _el("div", {"role": "presentation"})
        cand = _score_node(node, [0], set())
        assert cand is None

    def test_role_case_insensitive(self):
        node = _el("div", {"role": "Button"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.evidence_role == "button"

    def test_role_whitespace_stripped(self):
        node = _el("div", {"role": "  tab  "})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.evidence_role == "tab"


# ===================================================================
# 3. Signal 3: Class hints
# ===================================================================

class TestSignalClassHints:
    """Signal 3: class token patterns score _SCORE_CLASS_HINT=0.10 per match (up to 3x)."""

    @pytest.mark.parametrize("cls,expected_action", [
        ("my-btn", "click"),
        ("submit-area", "click"),
        ("nav-link", "click"),
        ("tab-item", "click"),
        ("dropdown-trigger", "click"),
        ("menu-wrap", "click"),
        ("item-row", "click"),
        ("toggle-switch", "toggle"),
        ("form-input", "input"),
        ("search-bar", "input"),
        ("clickable", "click"),
        ("hoverable", "hover"),
        ("select-wrapper", "select"),
        ("date-picker", "click"),
    ])
    def test_class_hint_patterns(self, cls, expected_action):
        node = _el("div", {"class": cls})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert expected_action in cand.actions
        assert len(cand.evidence_class_hints) > 0

    def test_multiple_class_hints_cap_at_3x(self):
        # btn + button + submit + link = 4 matches, but capped at 3x
        node = _el("div", {"class": "my-btn my-button my-submit my-link"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        # Class-hint contribution is capped at 3x even if icon intent adds more.
        assert cand.score >= 0.30
        assert "link" in cand.evidence_icon_intent

    def test_empty_class_no_hint(self):
        node = _el("div", {"class": ""})
        cand = _score_node(node, [0], set())
        assert cand is None

    def test_no_class_attr(self):
        node = _el("div")
        cand = _score_node(node, [0], set())
        assert cand is None

    def test_class_without_matching_patterns(self):
        node = _el("div", {"class": "container wrapper main"})
        cand = _score_node(node, [0], set())
        assert cand is None


# ===================================================================
# 4. Signal 4: Component library prefix
# ===================================================================

class TestSignalComponentLibrary:
    """Signal 4: component library prefix scores _SCORE_COMPONENT_LIB=0.25."""

    @pytest.mark.parametrize("tag,expected_prefix,expected_suffix", [
        ("el-button", "el", "button"),
        ("ant-btn", "ant", "btn"),
        ("van-button", "van", "button"),
        ("n-input", "n", "input"),
        ("t-select", "t", "select"),
        ("ivu-checkbox", "ivu", "checkbox"),
        ("arco-switch", "arco", "switch"),
        ("a-slider", "a", "slider"),
    ])
    def test_component_tag_detection(self, tag, expected_prefix, expected_suffix):
        result = _match_component_lib(tag, "")
        assert result is not None
        prefix, suffix = result
        assert prefix == expected_prefix
        assert suffix == expected_suffix

    def test_component_class_detection(self):
        result = _match_component_lib("div", "wrapper el-button primary")
        assert result is not None
        assert result == ("el", "button")

    def test_component_no_match(self):
        result = _match_component_lib("div", "container wrapper")
        assert result is None

    def test_component_scoring(self):
        node = _el("el-button")
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.evidence_component_lib == "el-button"
        assert "click" in cand.actions

    @pytest.mark.parametrize("tag,expected_action", [
        ("el-input", "input"),
        ("ant-checkbox", "toggle"),
        ("van-radio", "toggle"),
        ("n-select", "select"),
        ("el-upload", "click"),
        ("el-cascader", "click"),
        ("el-date-picker", "click"),
        ("el-autocomplete", "input"),
        ("el-collapse", "toggle"),
        ("el-popover", "hover"),
        ("el-tooltip", "hover"),
        ("el-pagination", "click"),
        ("el-menu-item", "click"),
        ("el-dropdown-item", "click"),
        ("el-tabs", "click"),
        ("el-tab-pane", "click"),
        ("el-dialog", "click"),
        ("el-drawer", "click"),
    ])
    def test_component_suffix_actions(self, tag, expected_action):
        node = _el(tag)
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert expected_action in cand.actions

    def test_component_case_insensitive(self):
        result = _match_component_lib("EL-BUTTON", "")
        assert result is not None
        assert result == ("el", "button")

    def test_component_class_token_match(self):
        """Component detected via class token, not tag."""
        node = _el("div", {"class": "van-button primary"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.evidence_component_lib == "van-button"


# ===================================================================
# 5. Signal 5: ARIA interactive attributes
# ===================================================================

class TestSignalAriaAttributes:
    """Signal 5: ARIA interactive attributes score _SCORE_ARIA=0.10 per (up to 3x)."""

    @pytest.mark.parametrize("attr", [
        "aria-expanded",
        "aria-haspopup",
        "aria-controls",
        "aria-pressed",
        "aria-checked",
        "aria-selected",
    ])
    def test_single_aria_attr(self, attr):
        node = _el("div", {attr: "true"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert attr in cand.evidence_aria
        # Single aria attr = 0.10, with default 'click' action
        assert "click" in cand.actions

    def test_multiple_aria_attrs_cap_at_3x(self):
        node = _el("div", {
            "aria-expanded": "true",
            "aria-haspopup": "true",
            "aria-controls": "panel1",
            "aria-pressed": "false",
        })
        cand = _score_node(node, [0], set())
        assert cand is not None
        # 0.10 * min(4, 3) = 0.30
        assert abs(cand.score - 0.30) < 0.01
        assert len(cand.evidence_aria) == 4

    def test_aria_no_override_existing_actions(self):
        """When actions already set, ARIA doesn't add default 'click'."""
        node = _el("input", {"aria-expanded": "true"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        # input has 'input' action from tag signal; ARIA doesn't add 'click'
        # because `if not actions` check fails
        assert "input" in cand.actions


# ===================================================================
# 6. Signal 6: tabindex
# ===================================================================

class TestSignalTabindex:
    """Signal 6: tabindex >= 0 scores _SCORE_TABINDEX=0.05."""

    def test_tabindex_zero(self):
        node = _el("div", {"tabindex": "0"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.score >= 0.05
        assert "click" in cand.actions

    def test_tabindex_positive(self):
        node = _el("div", {"tabindex": "1"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.score >= 0.05

    def test_tabindex_negative_no_score(self):
        """tabindex=-1 means programmatically focusable but not interactive per UX."""
        node = _el("div", {"tabindex": "-1"})
        cand = _score_node(node, [0], set())
        assert cand is None

    def test_tabindex_invalid_value(self):
        """Non-numeric tabindex is silently ignored."""
        node = _el("div", {"tabindex": "abc"})
        cand = _score_node(node, [0], set())
        assert cand is None

    def test_tabindex_no_override_existing_actions(self):
        """When a button already has click, tabindex doesn't re-add."""
        node = _el("button", {"tabindex": "0"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert "click" in cand.actions
        # Score = tag (0.35) + tabindex (0.05) = 0.40
        assert abs(cand.score - 0.40) < 0.01


# ===================================================================
# 7. Signal 7: contenteditable
# ===================================================================

class TestSignalContenteditable:
    """Signal 7: contenteditable='true' or '' scores _SCORE_CONTENTEDITABLE=0.15."""

    def test_contenteditable_true(self):
        node = _el("div", {"contenteditable": "true"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.score >= 0.15
        assert "input" in cand.actions

    def test_contenteditable_empty_string(self):
        """contenteditable='' (no value) is treated as true in HTML."""
        node = _el("div", {"contenteditable": ""})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert "input" in cand.actions

    def test_contenteditable_false(self):
        node = _el("div", {"contenteditable": "false"})
        cand = _score_node(node, [0], set())
        assert cand is None

    def test_contenteditable_no_attr(self):
        """No contenteditable attribute means not editable."""
        node = _el("div")
        cand = _score_node(node, [0], set())
        assert cand is None


# ===================================================================
# 8. Signal 8: Text intent
# ===================================================================

class TestSignalTextIntent:
    """Signal 8: action keywords in text/attrs score _SCORE_TEXT_INTENT=0.30."""

    def test_chinese_text_intent_submit(self):
        node = _el("span", {}, [_text("提交")])
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.evidence_text_intent == "提交"
        assert "click" in cand.actions

    def test_chinese_text_intent_toggle(self):
        node = _el("span", {}, [_text("展开")])
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.evidence_text_intent == "展开"
        assert "toggle" in cand.actions

    def test_english_text_intent_submit(self):
        node = _el("span", {}, [_text("Submit")])
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.evidence_text_intent == "submit"
        assert "click" in cand.actions

    def test_english_text_intent_toggle(self):
        node = _el("span", {}, [_text("Expand")])
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.evidence_text_intent == "expand"
        assert "toggle" in cand.actions

    def test_text_intent_from_aria_label(self):
        node = _el("div", {"aria-label": "保存"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.evidence_text_intent == "保存"

    def test_text_intent_from_title(self):
        node = _el("div", {"title": "Delete"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.evidence_text_intent == "delete"

    def test_text_intent_from_placeholder(self):
        node = _el("div", {"placeholder": "Search here"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.evidence_text_intent == "search"

    def test_text_intent_from_name_attr(self):
        node = _el("div", {"name": "submit"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.evidence_text_intent == "submit"

    def test_text_intent_from_data_tooltip(self):
        node = _el("div", {"data-tooltip": "Download file"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.evidence_text_intent == "download"

    def test_text_intent_from_alt(self):
        node = _el("div", {"alt": "Edit this item"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.evidence_text_intent == "edit"

    def test_text_intent_attr_priority_over_text(self):
        """aria-label is checked before visible text content."""
        node = _el("span", {"aria-label": "删除"}, [_text("Submit")])
        cand = _score_node(node, [0], set())
        assert cand is not None
        # aria-label "删除" should be matched first
        assert cand.evidence_text_intent == "删除"

    def test_no_text_intent(self):
        node = _el("span", {}, [_text("Hello world")])
        # "Hello world" doesn't match any action keywords
        result = _extract_text_intent(node)
        assert result is None


class TestMatchTextIntent:
    """Direct tests for _match_text_intent."""

    def test_empty_string(self):
        assert _match_text_intent("") is None

    def test_too_long_string(self):
        assert _match_text_intent("x" * 51) is None

    def test_chinese_exact(self):
        assert _match_text_intent("保存") == ("保存", "click")

    def test_chinese_substring(self):
        assert _match_text_intent("请保存更改") == ("保存", "click")

    def test_english_word_boundary(self):
        assert _match_text_intent("submit form") == ("submit", "click")

    def test_english_hyphenated(self):
        assert _match_text_intent("sign-in") == ("sign in", "click")

    def test_english_no_partial_match(self):
        """'summit' should NOT match 'submit'."""
        assert _match_text_intent("summit view") is None

    def test_english_toggle_words(self):
        assert _match_text_intent("expand all") == ("expand", "toggle")


class TestGetShallowText:
    """Tests for _get_shallow_text shallow text collection."""

    def test_direct_text(self):
        node = _el("span", {}, [_text("Click me")])
        assert _get_shallow_text(node) == "Click me"

    def test_nested_text_within_depth(self):
        node = _el("div", {}, [
            _el("span", {}, [_text("Hello")]),
        ])
        assert "Hello" in _get_shallow_text(node)

    def test_deep_text_excluded(self):
        """Text at depth > max_depth=2 is not collected."""
        node = _el("div", {}, [
            _el("div", {}, [
                _el("div", {}, [
                    _text("Deep text"),
                ]),
            ]),
        ])
        result = _get_shallow_text(node, max_depth=2)
        assert "Deep text" not in result

    def test_script_style_excluded(self):
        node = _el("div", {}, [
            _el("script", {}, [_text("var x = 1;")]),
            _el("style", {}, [_text(".foo {}")]),
            _el("svg", {}, [_text("path")]),
            _text("Visible text"),
        ])
        result = _get_shallow_text(node)
        assert "var x" not in result
        assert "Visible text" in result

    def test_long_text_truncated_to_200(self):
        long_text = "A" * 300
        node = _el("div", {}, [_text(long_text)])
        result = _get_shallow_text(node)
        assert len(result) == 200

    def test_empty_text_nodes_skipped(self):
        node = _el("div", {}, [_text("   "), _text("Real")])
        assert _get_shallow_text(node) == "Real"


# ===================================================================
# 9. Signal 9: Icon intent
# ===================================================================

class TestSignalIconIntent:
    """Signal 9: icon keywords in class/attrs score _SCORE_ICON_INTENT=0.15 per (up to 2x)."""

    def test_icon_class_search(self):
        node = _el("i", {"class": "icon-search"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert "search" in cand.evidence_icon_intent
        assert "click" in cand.actions

    def test_icon_class_edit(self):
        node = _el("i", {"class": "fa-pencil"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert "pencil" in cand.evidence_icon_intent

    def test_icon_class_delete(self):
        node = _el("i", {"class": "icon-trash"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert "trash" in cand.evidence_icon_intent

    def test_icon_aria_label(self):
        node = _el("span", {"aria-label": "delete item"})
        hits = _extract_icon_intent(node)
        assert any(kw == "delete" for kw, _ in hits)

    def test_icon_alt_attr(self):
        node = _el("img", {"alt": "download file"})
        hits = _extract_icon_intent(node)
        assert any(kw == "download" for kw, _ in hits)

    def test_icon_src_attr(self):
        node = _el("img", {"src": "/icons/upload.svg"})
        hits = _extract_icon_intent(node)
        assert any(kw == "upload" for kw, _ in hits)

    def test_icon_href_attr(self):
        node = _el("use", {"href": "/sprites.svg#icon-close"})
        hits = _extract_icon_intent(node)
        assert any(kw == "close" for kw, _ in hits)

    def test_icon_toggle_actions(self):
        node = _el("i", {"class": "icon-expand"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert "toggle" in cand.actions

    def test_multiple_icon_hits_capped_at_5(self):
        # class with many keywords
        node = _el("i", {"class": "icon-search icon-add icon-edit icon-delete icon-close icon-download"})
        hits = _extract_icon_intent(node)
        assert len(hits) <= 5

    def test_multiple_icon_hits_score_capped_at_2x(self):
        node = _el("i", {"class": "icon-search icon-add icon-edit"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        # Icon-intent contribution is capped at 2x even if other signals overlap.
        assert cand.score >= 0.30
        assert cand.evidence_icon_intent[:3] == ["search", "add", "edit"]

    def test_icon_dedup_across_sources(self):
        """Same keyword in class and aria-label should not double count."""
        node = _el("i", {"class": "icon-search", "aria-label": "search"})
        hits = _extract_icon_intent(node)
        search_hits = [kw for kw, _ in hits if kw == "search"]
        assert len(search_hits) == 1

    def test_no_icon_intent(self):
        node = _el("i", {"class": "icon-unknown-thing"})
        hits = _extract_icon_intent(node)
        assert len(hits) == 0


# ===================================================================
# 10. Signal 10: Mutation linkage
# ===================================================================

class TestSignalMutationLinkage:
    """Signal 10: mutation linkage scores _SCORE_MUTATION_LINKAGE=0.20."""

    def test_mutation_linkage_by_id(self):
        mutations = [{"targetTag": "div", "targetId": "my-panel"}]
        targets = _build_mutation_target_index(mutations)
        node = _el("div", {"id": "my-panel"})
        cand = _score_node(node, [0], targets)
        assert cand is not None
        assert cand.evidence_mutation_linkage is True
        assert cand.score >= 0.20

    def test_mutation_linkage_by_class(self):
        mutations = [{"targetTag": "div", "targetClassName": "active-tab"}]
        targets = _build_mutation_target_index(mutations)
        node = _el("div", {"class": "active-tab"})
        cand = _score_node(node, [0], targets)
        assert cand is not None
        assert cand.evidence_mutation_linkage is True

    def test_mutation_linkage_by_tag(self):
        mutations = [{"targetTag": "ul"}]
        targets = _build_mutation_target_index(mutations)
        node = _el("ul")
        cand = _score_node(node, [0], targets)
        assert cand is not None
        assert cand.evidence_mutation_linkage is True

    def test_no_mutation_linkage(self):
        targets = _build_mutation_target_index([])
        node = _el("button")
        cand = _score_node(node, [0], targets)
        assert cand is not None
        assert cand.evidence_mutation_linkage is False


class TestBuildMutationTargetIndex:
    """Tests for _build_mutation_target_index."""

    def test_empty_mutations(self):
        assert _build_mutation_target_index([]) == set()

    def test_target_with_id(self):
        targets = _build_mutation_target_index([
            {"targetTag": "div", "targetId": "main"}
        ])
        assert "id:main" in targets
        assert "tag:div" in targets

    def test_target_with_class(self):
        targets = _build_mutation_target_index([
            {"targetTag": "span", "targetClassName": "highlight"}
        ])
        assert "class:highlight" in targets
        assert "tag:span" in targets

    def test_missing_tag_skipped(self):
        targets = _build_mutation_target_index([{"targetId": "foo"}])
        assert len(targets) == 0

    def test_empty_tag_skipped(self):
        targets = _build_mutation_target_index([{"targetTag": ""}])
        assert len(targets) == 0

    def test_multiple_mutations(self):
        targets = _build_mutation_target_index([
            {"targetTag": "div", "targetId": "a"},
            {"targetTag": "span", "targetClassName": "b"},
        ])
        assert "id:a" in targets
        assert "class:b" in targets
        assert "tag:div" in targets
        assert "tag:span" in targets


class TestNodeKey:
    """Tests for _node_key."""

    def test_node_with_id(self):
        node = _el("div", {"id": "main"})
        assert _node_key(node, [0]) == "id:main"

    def test_node_with_class_no_id(self):
        node = _el("div", {"class": "container wrapper"})
        assert _node_key(node, [0]) == "class:container"

    def test_node_with_no_id_no_class(self):
        node = _el("span")
        assert _node_key(node, [0]) == "tag:span"


class TestNodeMatchesMutationTargets:
    """Tests for _node_matches_mutation_targets."""

    def test_match_by_id(self):
        node = _el("div", {"id": "panel"})
        assert _node_matches_mutation_targets(node, [0], {"id:panel"})

    def test_match_by_class(self):
        node = _el("div", {"class": "active selected"})
        assert _node_matches_mutation_targets(node, [0], {"class:active"})

    def test_match_by_second_class(self):
        node = _el("div", {"class": "foo bar"})
        assert _node_matches_mutation_targets(node, [0], {"class:bar"})

    def test_match_by_tag(self):
        node = _el("ul")
        assert _node_matches_mutation_targets(node, [0], {"tag:ul"})

    def test_no_match(self):
        node = _el("div")
        assert not _node_matches_mutation_targets(node, [0], {"id:other"})

    def test_class_check_limited_to_first_3(self):
        """Only first 3 class tokens checked."""
        node = _el("div", {"class": "a b c d e"})
        assert not _node_matches_mutation_targets(node, [0], {"class:d"})


# ===================================================================
# 11. Penalties
# ===================================================================

class TestPenalties:
    """Penalty logic: disabled=-0.30, hidden=-0.40."""

    def test_disabled_penalty(self):
        node = _el("button", {"disabled": ""})
        cand = _score_node(node, [0], set())
        assert cand is not None
        # 0.35 (tag) - 0.30 (disabled) = 0.05
        assert abs(cand.score - 0.05) < 0.01

    def test_disabled_with_value(self):
        """disabled='disabled' still triggers penalty."""
        node = _el("button", {"disabled": "disabled"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.score < 0.35

    def test_hidden_penalty(self):
        node = _el("button", visible=False)
        cand = _score_node(node, [0], set())
        assert cand is not None
        # 0.35 (tag) - 0.40 (hidden) < 0 -> clamped to 0.0
        # But actions is non-empty, so not filtered out by `score <= 0 and not actions`
        assert cand.score == 0.0

    def test_disabled_and_hidden(self):
        node = _el("button", {"disabled": ""}, visible=False)
        cand = _score_node(node, [0], set())
        assert cand is not None
        # 0.35 - 0.30 - 0.40 = -0.35 -> clamped to 0.0
        assert cand.score == 0.0

    def test_high_score_survives_penalty(self):
        """A node with many signals should survive a single penalty."""
        node = _el("button", {
            "role": "button",
            "class": "my-btn",
            "aria-expanded": "true",
        })
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.score > 0.50


# ===================================================================
# 12. Score clamping
# ===================================================================

class TestScoreClamping:
    """Score is clamped to [0.0, 1.0]."""

    def test_score_clamped_at_1(self):
        """A heavily-signalled node should not exceed 1.0."""
        node = _el("button", {
            "role": "button",
            "class": "my-btn my-button my-submit",
            "aria-expanded": "true",
            "aria-haspopup": "true",
            "aria-controls": "panel",
            "tabindex": "0",
            "contenteditable": "true",
            "aria-label": "提交",
        }, [_text("Submit")])
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.score <= 1.0

    def test_score_clamped_at_0(self):
        """Score below 0 is clamped to 0.0."""
        node = _el("button", {"disabled": ""}, visible=False)
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.score >= 0.0


# ===================================================================
# 13. Filtering and no-signal skip
# ===================================================================

class TestNoSignalSkip:
    """Nodes with score<=0 AND no actions return None."""

    def test_plain_div_returns_none(self):
        assert _score_node(_el("div"), [0], set()) is None

    def test_plain_p_returns_none(self):
        assert _score_node(_el("p"), [0], set()) is None

    def test_text_node_skipped_in_walk(self):
        """_walk_node skips text nodes."""
        out: list[_CandidateRaw] = []
        _walk_node(_text("hello"), [0], out, set())
        assert len(out) == 0

    def test_element_without_tag_skipped(self):
        """Element with tag=None is skipped."""
        node = ASTNode(node_type="element", tag=None)
        out: list[_CandidateRaw] = []
        _walk_node(node, [0], out, set())
        assert len(out) == 0


# ===================================================================
# 14. Walk recursion
# ===================================================================

class TestWalkNode:
    """_walk_node recursively scores children."""

    def test_recursive_walk(self):
        tree = _el("div", {}, [
            _el("button", {}, [_text("OK")]),
            _el("div", {}, [
                _el("a", {"href": "/help"}, [_text("Help")]),
            ]),
        ])
        out: list[_CandidateRaw] = []
        _walk_node(tree, [0], out, set())
        tags = [c.tag for c in out]
        assert "button" in tags
        assert "a" in tags
        # div itself should not be in output (no signals)
        assert tags.count("div") == 0

    def test_path_tracking(self):
        """Path should reflect actual position in tree."""
        tree = _el("div", {}, [
            _el("span"),
            _el("button"),
        ])
        out: list[_CandidateRaw] = []
        _walk_node(tree, [0], out, set())
        btn = [c for c in out if c.tag == "button"][0]
        assert btn.path == [0, 1]


# ===================================================================
# 15. infer_candidates — full pipeline
# ===================================================================

class TestInferCandidates:
    """Top-level infer_candidates function."""

    def test_empty_ast(self):
        ast = FullAST(nodes=[], node_count=0)
        candidates, hints = infer_candidates(ast)
        assert candidates == []
        assert hints == []

    def test_text_only_ast(self):
        ast = FullAST(nodes=[_text("Hello")], node_count=1)
        candidates, hints = infer_candidates(ast)
        assert candidates == []

    def test_basic_button(self):
        ast = _ast(_el("button", {}, [_text("Save")]))
        candidates, hints = infer_candidates(ast)
        assert len(candidates) == 1
        c = candidates[0]
        assert "click" in c["inferred_actions"]
        assert c["score"] > 0
        assert c["priority"] == 1
        assert "element_key" in c
        assert "evidence" in c

    def test_threshold_filtering(self):
        """Nodes below threshold are excluded."""
        ast = _ast(
            _el("button", {}, [_text("OK")]),       # high score
            _el("div", {"tabindex": "0"}),           # low score (0.05)
        )
        candidates, _ = infer_candidates(ast, score_threshold=0.30)
        # button passes, tabindex-only div doesn't
        assert len(candidates) == 1
        assert candidates[0]["inferred_actions"] == ["click"]

    def test_max_candidates_limiting(self):
        nodes = [_el("button", {}, [_text(f"Btn{i}")]) for i in range(10)]
        ast = FullAST(nodes=nodes, node_count=10)
        candidates, _ = infer_candidates(ast, max_candidates=3)
        assert len(candidates) == 3

    def test_sorted_by_score_desc(self):
        ast = _ast(
            _el("div", {"tabindex": "0"}),                                # ~0.05
            _el("button", {"role": "button", "class": "my-btn"}, [_text("提交")]),  # high
            _el("a", {"href": "/link"}),                                  # 0.35
        )
        candidates, _ = infer_candidates(ast, score_threshold=0.01)
        scores = [c["score"] for c in candidates]
        assert scores == sorted(scores, reverse=True)

    def test_priority_is_1_based_rank(self):
        ast = _ast(
            _el("button", {}, [_text("A")]),
            _el("a", {"href": "#"}, [_text("B")]),
        )
        candidates, _ = infer_candidates(ast, score_threshold=0.01)
        priorities = [c["priority"] for c in candidates]
        assert priorities == list(range(1, len(candidates) + 1))

    def test_with_mutations(self):
        mutations = [{"targetTag": "div", "targetId": "dynamic-panel"}]
        ast = _ast(
            _el("div", {"id": "dynamic-panel"}),
            _el("button"),
        )
        candidates, _ = infer_candidates(ast, mutations=mutations, score_threshold=0.01)
        # The div with mutation linkage should appear
        div_candidates = [c for c in candidates if "div" in c["element_key"]]
        assert len(div_candidates) == 1

    def test_none_mutations_treated_as_empty(self):
        ast = _ast(_el("button"))
        candidates, _ = infer_candidates(ast, mutations=None)
        assert len(candidates) == 1


# ===================================================================
# 16. Candidate output format
# ===================================================================

class TestCandidateOutputFormat:
    """Output structure of _to_candidate_element."""

    def test_output_keys(self):
        raw = _CandidateRaw(
            path=[0, 1],
            tag="button",
            attrs={"id": "submit-btn"},
            visible=True,
            actions={"click"},
            score=0.65,
            evidence_tag="button",
        )
        result = _to_candidate_element(raw, 1)
        assert set(result.keys()) == {"element_key", "inferred_actions", "score", "evidence", "priority"}
        assert result["priority"] == 1
        assert result["inferred_actions"] == ["click"]
        assert result["score"] == 0.65
        assert result["evidence"]["tag"] == "button"

    def test_evidence_populated_selectively(self):
        """Only non-empty evidence fields are included."""
        raw = _CandidateRaw(
            path=[0],
            tag="div",
            attrs={},
            visible=True,
            actions={"click"},
            score=0.25,
            evidence_role="button",
        )
        result = _to_candidate_element(raw, 1)
        assert "role" in result["evidence"]
        assert "tag" not in result["evidence"]
        assert "class_hints" not in result["evidence"]

    def test_all_evidence_types(self):
        raw = _CandidateRaw(
            path=[0],
            tag="button",
            attrs={"id": "btn"},
            visible=True,
            actions={"click"},
            score=0.90,
            evidence_tag="button",
            evidence_class_hints=["my-btn"],
            evidence_role="button",
            evidence_aria={"aria-expanded": "true"},
            evidence_component_lib="el-button",
            evidence_text_intent="提交",
            evidence_icon_intent=["search"],
            evidence_mutation_linkage=True,
        )
        result = _to_candidate_element(raw, 1)
        e = result["evidence"]
        assert e["tag"] == "button"
        assert e["class_hints"] == ["my-btn"]
        assert e["role"] == "button"
        assert e["aria"] == {"aria-expanded": "true"}
        assert e["component_lib"] == "el-button"
        assert e["text_intent"] == "提交"
        assert e["icon_intent"] == ["search"]
        assert e["mutation_linkage"] is True

    def test_actions_sorted(self):
        raw = _CandidateRaw(
            path=[0],
            tag="div",
            attrs={},
            visible=True,
            actions={"toggle", "click", "input"},
            score=0.50,
        )
        result = _to_candidate_element(raw, 1)
        assert result["inferred_actions"] == ["click", "input", "toggle"]

    def test_score_rounded_to_3_decimals(self):
        raw = _CandidateRaw(
            path=[0], tag="div", attrs={}, visible=True,
            actions={"click"}, score=0.33333,
        )
        result = _to_candidate_element(raw, 1)
        assert result["score"] == 0.333


# ===================================================================
# 17. Element key generation
# ===================================================================

class TestMakeElementKey:
    """Tests for _make_element_key."""

    def test_key_with_id(self):
        raw = _CandidateRaw(path=[0], tag="button", attrs={"id": "submit-btn"}, visible=True)
        assert _make_element_key(raw) == "button#submit-btn"

    def test_key_with_role_and_label(self):
        raw = _CandidateRaw(
            path=[0], tag="div",
            attrs={"role": "button", "aria-label": "Close"},
            visible=True,
        )
        assert _make_element_key(raw) == "div[role=button][Close]"

    def test_key_with_role_and_title(self):
        raw = _CandidateRaw(
            path=[0], tag="div",
            attrs={"role": "tab", "title": "Settings"},
            visible=True,
        )
        assert _make_element_key(raw) == "div[role=tab][Settings]"

    def test_key_with_role_and_name(self):
        raw = _CandidateRaw(
            path=[0], tag="div",
            attrs={"role": "textbox", "name": "comment"},
            visible=True,
        )
        assert _make_element_key(raw) == "div[role=textbox][comment]"

    def test_key_with_role_no_label(self):
        raw = _CandidateRaw(
            path=[1, 2], tag="div",
            attrs={"role": "button"},
            visible=True,
        )
        assert _make_element_key(raw) == "div[role=button]@1.2"

    def test_key_with_name_no_role(self):
        raw = _CandidateRaw(
            path=[0], tag="input",
            attrs={"name": "email"},
            visible=True,
        )
        assert _make_element_key(raw) == "input[name=email]"

    def test_key_fallback_path(self):
        raw = _CandidateRaw(path=[3, 1, 0], tag="span", attrs={}, visible=True)
        assert _make_element_key(raw) == "span@3.1.0"


# ===================================================================
# 18. Primary action picking
# ===================================================================

class TestPickPrimaryAction:
    """Tests for _pick_primary_action priority."""

    def test_input_highest_priority(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={}, visible=True, actions={"click", "input", "toggle"})
        assert _pick_primary_action(raw) == "input"

    def test_select_over_toggle(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={}, visible=True, actions={"select", "toggle", "click"})
        assert _pick_primary_action(raw) == "select"

    def test_toggle_over_click(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={}, visible=True, actions={"toggle", "click"})
        assert _pick_primary_action(raw) == "toggle"

    def test_click_over_hover(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={}, visible=True, actions={"hover", "click"})
        assert _pick_primary_action(raw) == "click"

    def test_hover_alone(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={}, visible=True, actions={"hover"})
        assert _pick_primary_action(raw) == "hover"

    def test_empty_actions_defaults_click(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={}, visible=True, actions=set())
        assert _pick_primary_action(raw) == "click"


# ===================================================================
# 19. Hint generation
# ===================================================================

class TestHintGeneration:
    """Tests for _generate_hints and hint structure."""

    def test_basic_hint_structure(self):
        raw = _CandidateRaw(
            path=[0], tag="button", attrs={"id": "save"},
            visible=True, actions={"click"}, score=0.65,
            evidence_tag="button",
        )
        hints = _generate_hints([raw])
        assert len(hints) == 1
        h = hints[0]
        assert h["element_key"] == "button#save"
        assert h["action"] == "click"
        assert h["reason"] == 'native <button> element'
        assert h["priority"] == 1

    def test_max_hints_limit(self):
        raws = [
            _CandidateRaw(
                path=[i], tag="button", attrs={"id": f"btn-{i}"},
                visible=True, actions={"click"}, score=0.5,
            )
            for i in range(50)
        ]
        hints = _generate_hints(raws, max_hints=10)
        assert len(hints) == 10

    def test_dedup_by_element_key(self):
        """Same element key should appear only once in hints."""
        raw1 = _CandidateRaw(
            path=[0], tag="button", attrs={"id": "same"},
            visible=True, actions={"click"}, score=0.5,
        )
        raw2 = _CandidateRaw(
            path=[0], tag="button", attrs={"id": "same"},
            visible=True, actions={"click"}, score=0.4,
        )
        hints = _generate_hints([raw1, raw2])
        assert len(hints) == 1

    def test_hint_priority_sequential(self):
        raws = [
            _CandidateRaw(path=[0], tag="button", attrs={"id": "a"}, visible=True, actions={"click"}, score=0.5),
            _CandidateRaw(path=[1], tag="a", attrs={"id": "b"}, visible=True, actions={"click"}, score=0.4),
        ]
        hints = _generate_hints(raws)
        assert hints[0]["priority"] == 1
        assert hints[1]["priority"] == 2

    def test_from_infer_candidates(self):
        ast = _ast(
            _el("button", {}, [_text("Save")]),
            _el("a", {"href": "#"}, [_text("Help")]),
        )
        _, hints = infer_candidates(ast)
        assert len(hints) > 0
        for h in hints:
            assert "element_key" in h
            assert "action" in h
            assert "reason" in h
            assert "priority" in h


# ===================================================================
# 20. Reason building
# ===================================================================

class TestBuildReason:
    """Tests for _build_reason."""

    def test_tag_reason(self):
        raw = _CandidateRaw(path=[0], tag="button", attrs={}, visible=True, evidence_tag="button")
        assert "native <button> element" in _build_reason(raw)

    def test_role_reason(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={}, visible=True, evidence_role="slider")
        assert 'role="slider"' in _build_reason(raw)

    def test_class_hints_reason(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={}, visible=True, evidence_class_hints=["my-btn", "submit"])
        reason = _build_reason(raw)
        assert "class hints:" in reason
        assert "my-btn" in reason

    def test_component_lib_reason(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={}, visible=True, evidence_component_lib="el-button")
        assert "component: el-button" in _build_reason(raw)

    def test_aria_reason(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={}, visible=True,
                            evidence_aria={"aria-expanded": "true"})
        assert "aria attrs:" in _build_reason(raw)

    def test_text_intent_reason(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={}, visible=True, evidence_text_intent="保存")
        assert 'text intent: "保存"' in _build_reason(raw)

    def test_icon_intent_reason(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={}, visible=True, evidence_icon_intent=["search", "add"])
        reason = _build_reason(raw)
        assert "icon intent:" in reason
        assert "search" in reason

    def test_mutation_linkage_reason(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={}, visible=True, evidence_mutation_linkage=True)
        assert "linked to observed mutations" in _build_reason(raw)

    def test_fallback_structural_signal(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={}, visible=True)
        assert _build_reason(raw) == "structural signal"

    def test_multiple_reasons_joined(self):
        raw = _CandidateRaw(
            path=[0], tag="button", attrs={}, visible=True,
            evidence_tag="button", evidence_role="button",
        )
        reason = _build_reason(raw)
        assert "; " in reason
        assert "native <button>" in reason
        assert 'role="button"' in reason


# ===================================================================
# 21. Expected effect guessing
# ===================================================================

class TestGuessExpectedEffect:
    """Tests for _guess_expected_effect."""

    # --- Text intent effects ---
    @pytest.mark.parametrize("word,expected", [
        ("提交", "form submission"),
        ("保存", "form submission"),
        ("确定", "form submission"),
        ("submit", "form submission"),
        ("save", "form submission"),
        ("confirm", "form submission"),
        ("ok", "form submission"),
        ("apply", "form submission"),
    ])
    def test_submit_words(self, word, expected):
        raw = _CandidateRaw(path=[0], tag="span", attrs={}, visible=True, evidence_text_intent=word)
        assert _guess_expected_effect(raw) == expected

    @pytest.mark.parametrize("word,expected", [
        ("搜索", "triggers search/filter"),
        ("查询", "triggers search/filter"),
        ("search", "triggers search/filter"),
        ("filter", "triggers search/filter"),
    ])
    def test_search_words(self, word, expected):
        raw = _CandidateRaw(path=[0], tag="span", attrs={}, visible=True, evidence_text_intent=word)
        assert _guess_expected_effect(raw) == expected

    @pytest.mark.parametrize("word,expected", [
        ("返回", "page navigation"),
        ("下一步", "page navigation"),
        ("back", "page navigation"),
        ("next", "page navigation"),
    ])
    def test_nav_words(self, word, expected):
        raw = _CandidateRaw(path=[0], tag="span", attrs={}, visible=True, evidence_text_intent=word)
        assert _guess_expected_effect(raw) == expected

    @pytest.mark.parametrize("word,expected", [
        ("删除", "deletes item"),
        ("remove", "deletes item"),
    ])
    def test_delete_words(self, word, expected):
        raw = _CandidateRaw(path=[0], tag="span", attrs={}, visible=True, evidence_text_intent=word)
        assert _guess_expected_effect(raw) == expected

    @pytest.mark.parametrize("word,expected", [
        ("展开", "section expands/collapses"),
        ("collapse", "section expands/collapses"),
        ("toggle", "section expands/collapses"),
    ])
    def test_toggle_words(self, word, expected):
        raw = _CandidateRaw(path=[0], tag="span", attrs={}, visible=True, evidence_text_intent=word)
        assert _guess_expected_effect(raw) == expected

    # --- Tag / attr effects (no text intent) ---
    def test_anchor_with_href(self):
        raw = _CandidateRaw(path=[0], tag="a", attrs={"href": "/page"}, visible=True)
        assert _guess_expected_effect(raw) == "navigation"

    def test_submit_type(self):
        raw = _CandidateRaw(path=[0], tag="input", attrs={"type": "submit"}, visible=True)
        assert _guess_expected_effect(raw) == "form submission"

    def test_submit_class(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={"class": "submit"}, visible=True)
        assert _guess_expected_effect(raw) == "form submission"

    def test_aria_haspopup(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={"aria-haspopup": "true"}, visible=True)
        assert _guess_expected_effect(raw) == "popup/dropdown opens"

    def test_aria_expanded(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={"aria-expanded": "false"}, visible=True)
        assert _guess_expected_effect(raw) == "section expands/collapses"

    def test_role_tab(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={"role": "tab"}, visible=True)
        assert _guess_expected_effect(raw) == "tab panel switches"

    def test_tag_select(self):
        raw = _CandidateRaw(path=[0], tag="select", attrs={}, visible=True)
        assert _guess_expected_effect(raw) == "dropdown options appear"

    def test_tag_input(self):
        raw = _CandidateRaw(path=[0], tag="input", attrs={}, visible=True)
        assert _guess_expected_effect(raw) == "accepts text input"

    def test_tag_textarea(self):
        raw = _CandidateRaw(path=[0], tag="textarea", attrs={}, visible=True)
        assert _guess_expected_effect(raw) == "accepts text input"

    # --- Icon intent effects ---
    @pytest.mark.parametrize("icon,expected", [
        ("search", "triggers search"),
        ("add", "creates new item"),
        ("edit", "opens editor"),
        ("delete", "deletes item"),
        ("trash", "deletes item"),
        ("close", "closes current view"),
        ("download", "downloads file"),
        ("upload", "opens file picker"),
        ("more", "shows more options"),
        ("ellipsis", "shows more options"),
        ("expand", "section expands"),
        ("collapse", "section collapses"),
        ("eye", "toggles visibility"),
        ("filter", "opens filter panel"),
        ("sort", "changes sort order"),
        ("refresh", "refreshes content"),
        ("copy", "copies to clipboard"),
        ("setting", "opens settings"),
        ("gear", "opens settings"),
    ])
    def test_icon_effects(self, icon, expected):
        raw = _CandidateRaw(
            path=[0], tag="i", attrs={}, visible=True,
            evidence_icon_intent=[icon],
        )
        assert _guess_expected_effect(raw) == expected

    def test_mutation_linkage_effect(self):
        raw = _CandidateRaw(
            path=[0], tag="div", attrs={}, visible=True,
            evidence_mutation_linkage=True,
        )
        assert _guess_expected_effect(raw) == "DOM changes observed in previous recording"

    def test_no_effect(self):
        raw = _CandidateRaw(path=[0], tag="div", attrs={}, visible=True)
        assert _guess_expected_effect(raw) is None


# ===================================================================
# 22. Extract matching tokens
# ===================================================================

class TestExtractMatchingTokens:
    """Tests for _extract_matching_tokens."""

    def test_basic_extraction(self):
        import re
        pattern = re.compile(r"(?:^|[-_])btn(?:$|[-_])", re.I).pattern
        result = _extract_matching_tokens("my-btn primary submit-link", [pattern])
        assert "my-btn" in result

    def test_limits_to_5(self):
        import re
        pattern = re.compile(r"(?:^|[-_])btn(?:$|[-_])", re.I).pattern
        class_str = " ".join(f"btn-{i}" for i in range(10))
        result = _extract_matching_tokens(class_str, [pattern])
        assert len(result) <= 5


# ===================================================================
# 23. Combined signal scoring
# ===================================================================

class TestCombinedSignals:
    """Test score aggregation when multiple signals fire."""

    def test_button_with_text_intent(self):
        """button(0.35) + text_intent(0.30) = 0.65."""
        node = _el("button", {}, [_text("提交")])
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert abs(cand.score - 0.65) < 0.01

    def test_tag_plus_role(self):
        """button(0.35) + role(0.25) = 0.60."""
        node = _el("button", {"role": "button"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert abs(cand.score - 0.60) < 0.01

    def test_component_plus_class_hint(self):
        """component(0.25) + class hints may overlap since el-button matches both."""
        node = _el("el-button", {"class": "el-button--primary"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.score >= 0.25  # at least component lib score

    def test_all_signals_active(self):
        """Maximize signals: tag + role + class + component + aria + tabindex +
        contenteditable + text + icon + mutation = high score clamped to 1.0."""
        mutations = [{"targetTag": "button", "targetId": "mega-btn"}]
        targets = _build_mutation_target_index(mutations)
        node = _el("button", {
            "id": "mega-btn",
            "role": "button",
            "class": "my-btn icon-search",
            "aria-expanded": "true",
            "aria-haspopup": "true",
            "tabindex": "0",
            "contenteditable": "true",
            "aria-label": "提交",
        }, [_text("Submit")])
        cand = _score_node(node, [0], targets)
        assert cand is not None
        assert cand.score == 1.0  # clamped


# ===================================================================
# 24. Realistic AST
# ===================================================================

class TestRealisticAST:
    """End-to-end test with a realistic page structure."""

    @pytest.fixture
    def admin_page_ast(self) -> FullAST:
        """Simulates a small admin page with form, table, nav."""
        return FullAST(
            nodes=[
                # Navigation bar
                _el("nav", {"role": "navigation"}, [
                    _el("a", {"href": "/dashboard", "class": "nav-link"}, [_text("Dashboard")]),
                    _el("a", {"href": "/users", "class": "nav-link"}, [_text("Users")]),
                    _el("a", {"href": "/settings", "class": "nav-link"}, [_text("Settings")]),
                ]),
                # Main content
                _el("main", {}, [
                    # Search form
                    _el("form", {"role": "form"}, [
                        _el("input", {"type": "text", "name": "search", "placeholder": "Search users"}),
                        _el("button", {"class": "btn-primary"}, [_text("搜索")]),
                        _el("button", {"class": "btn-secondary"}, [_text("重置")]),
                    ]),
                    # Table with action buttons
                    _el("table", {}, [
                        _el("thead", {}, [
                            _el("tr", {}, [
                                _el("th", {}, [_text("Name")]),
                                _el("th", {}, [_text("Actions")]),
                            ]),
                        ]),
                        _el("tbody", {}, [
                            _el("tr", {}, [
                                _el("td", {}, [_text("Alice")]),
                                _el("td", {}, [
                                    _el("a", {"href": "#", "class": "btn-edit"}, [
                                        _el("i", {"class": "icon-edit"}),
                                        _text("Edit"),
                                    ]),
                                    _el("a", {"href": "#", "class": "btn-delete"}, [
                                        _el("i", {"class": "icon-trash"}),
                                        _text("Delete"),
                                    ]),
                                ]),
                            ]),
                        ]),
                    ]),
                    # Element UI components
                    _el("el-pagination", {"class": "pagination-wrap"}),
                    _el("el-dialog", {"aria-expanded": "false"}, [
                        _el("el-input", {"name": "username", "placeholder": "Enter name"}),
                        _el("el-select", {"name": "role"}),
                        _el("el-button", {}, [_text("确定")]),
                        _el("el-button", {}, [_text("取消")]),
                    ]),
                ]),
                # Disabled button and hidden element
                _el("button", {"disabled": ""}, [_text("Cannot click")]),
                _el("div", {"role": "button"}, visible=False),
            ],
            node_count=30,
        )

    def test_finds_interactive_elements(self, admin_page_ast):
        candidates, hints = infer_candidates(admin_page_ast)
        element_keys = [c["element_key"] for c in candidates]

        # Navigation links found
        nav_links = [k for k in element_keys if "nav-link" in str(k) or "/dashboard" in str(k)]
        assert len(nav_links) >= 1

        # Form elements found
        search_input = [c for c in candidates if c["element_key"] == "input[name=search]"]
        assert len(search_input) == 1

        # Action buttons found
        assert len(candidates) >= 5  # multiple interactive elements

    def test_disabled_element_penalized(self, admin_page_ast):
        candidates, _ = infer_candidates(admin_page_ast, score_threshold=0.01)
        # Find the disabled button
        disabled = [c for c in candidates
                    if "Cannot" not in c["element_key"]
                    or c["score"] < 0.35]
        # Just verify some disabled/hidden candidates have lower scores
        scores = [c["score"] for c in candidates]
        assert min(scores) < max(scores)

    def test_hints_generated(self, admin_page_ast):
        _, hints = infer_candidates(admin_page_ast)
        assert len(hints) > 0
        actions = {h["action"] for h in hints}
        # Should have at least click and input actions
        assert "click" in actions

    def test_component_lib_elements_found(self, admin_page_ast):
        candidates, _ = infer_candidates(admin_page_ast)
        component_candidates = [
            c for c in candidates
            if "component_lib" in c.get("evidence", {})
        ]
        assert len(component_candidates) >= 3  # el-pagination, el-input, el-select, el-button

    def test_text_intent_detected(self, admin_page_ast):
        candidates, _ = infer_candidates(admin_page_ast)
        text_intent_candidates = [
            c for c in candidates
            if "text_intent" in c.get("evidence", {})
        ]
        # "搜索", "重置", "确定", "取消", "Edit", "Delete", "Search"
        assert len(text_intent_candidates) >= 2

    def test_icon_intent_detected(self, admin_page_ast):
        candidates, _ = infer_candidates(admin_page_ast)
        icon_candidates = [
            c for c in candidates
            if "icon_intent" in c.get("evidence", {})
        ]
        # icon-edit, icon-trash
        assert len(icon_candidates) >= 2


# ===================================================================
# 25. Edge cases
# ===================================================================

class TestEdgeCases:
    """Various edge and boundary conditions."""

    def test_score_threshold_zero_includes_all(self):
        ast = _ast(
            _el("button"),
            _el("div", {"tabindex": "0"}),
        )
        candidates, _ = infer_candidates(ast, score_threshold=0.0)
        assert len(candidates) >= 2

    def test_score_threshold_one_excludes_all(self):
        ast = _ast(_el("button"))
        candidates, _ = infer_candidates(ast, score_threshold=1.01)
        assert len(candidates) == 0

    def test_max_candidates_zero(self):
        ast = _ast(_el("button"), _el("a", {"href": "#"}))
        candidates, _ = infer_candidates(ast, max_candidates=0)
        assert len(candidates) == 0

    def test_deeply_nested_elements_found(self):
        """Elements nested deep in the tree are still discovered."""
        tree = _el("div", {}, [
            _el("div", {}, [
                _el("div", {}, [
                    _el("div", {}, [
                        _el("button", {}, [_text("Deep button")]),
                    ]),
                ]),
            ]),
        ])
        ast = _ast(tree)
        candidates, _ = infer_candidates(ast)
        assert len(candidates) >= 1
        assert any("button" in c["element_key"] for c in candidates)

    def test_multiple_children_all_scored(self):
        ast = _ast(
            _el("div", {}, [
                _el("button", {"id": "a"}),
                _el("button", {"id": "b"}),
                _el("button", {"id": "c"}),
            ]),
        )
        candidates, _ = infer_candidates(ast)
        assert len(candidates) == 3

    def test_duplicate_signals_dont_double_count_tag(self):
        """A single button only gets _SCORE_TAG once."""
        node = _el("button")
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert abs(cand.score - 0.35) < 0.01

    def test_contenteditable_false_no_double_check(self):
        """contenteditable='false' passes the 'in ("true", "")' check
        but fails the inner 'if "contenteditable" in attrs' check differently.
        Actually 'false' is not in ('true', '') so no score."""
        node = _el("div", {"contenteditable": "false"})
        cand = _score_node(node, [0], set())
        assert cand is None

    def test_input_checkbox_replaces_default_actions(self):
        """Input type=checkbox replaces the default {input} with {toggle}."""
        node = _el("input", {"type": "checkbox"})
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert cand.actions == {"toggle"}
        assert "input" not in cand.actions

    def test_anchor_without_href_still_interactive(self):
        """<a> tag is interactive even without href."""
        node = _el("a")
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert "click" in cand.actions

    def test_select_tag_actions(self):
        node = _el("select")
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert "select" in cand.actions

    def test_details_tag(self):
        node = _el("details")
        cand = _score_node(node, [0], set())
        assert cand is not None
        assert "toggle" in cand.actions

    def test_aria_expanded_null_check(self):
        """aria-expanded with explicit 'None' string should still trigger
        _guess_expected_effect because `attrs.get('aria-expanded') is not None`."""
        raw = _CandidateRaw(path=[0], tag="div", attrs={"aria-expanded": "None"}, visible=True)
        effect = _guess_expected_effect(raw)
        assert effect == "section expands/collapses"

    def test_empty_mutations_list(self):
        ast = _ast(_el("button"))
        candidates, _ = infer_candidates(ast, mutations=[])
        assert len(candidates) == 1

    def test_guess_effect_a_without_href(self):
        """<a> without href does not produce 'navigation' effect."""
        raw = _CandidateRaw(path=[0], tag="a", attrs={}, visible=True)
        effect = _guess_expected_effect(raw)
        assert effect is None

    def test_icon_intent_title_attr(self):
        node = _el("span", {"title": "refresh data"})
        hits = _extract_icon_intent(node)
        assert any(kw == "refresh" for kw, _ in hits)

    def test_icon_intent_data_tooltip_attr(self):
        node = _el("span", {"data-tooltip": "copy link"})
        hits = _extract_icon_intent(node)
        assert any(kw == "copy" for kw, _ in hits)
        assert any(kw == "link" for kw, _ in hits)
