"""Form-label extractor — pull the human-readable label for a form
control out of its surrounding HTML.

Why this module exists
----------------------
The autonomous page analyzer discovers fillable / submit / clickable
elements but only captures their own DOM attributes (id, name,
placeholder, aria-label). That's not enough for an operator reading
the analyzer output: 5 inputs that all look like
``<input type="text">`` are indistinguishable unless their visible
label is surfaced too.

HTML5 says the right way to associate a label with a control is
either ``<label for="id">`` or wrapping the control in a ``<label>``
element. In practice, UI libraries build labels out of arbitrary
div/span structures that don't use ``<label>`` semantically. This
module supplies a small set of framework-aware extractors so the
common cases land.

Design
------
- Each ``FormLabelExtractor`` is a small, focused handler that either
  says "I recognise this framework's wrapper shape" (``can_handle``)
  and returns the label text, or declines.
- ``extract_label`` walks the registered extractors in order and
  returns the first hit. No fuzzy fallback (we deliberately do not
  return "nearby text") because that produces more noise than signal.
- Extractors are pure — they take an HTML string and return a
  string or ``None``. No Playwright, no DOM live references. Testable
  with plain fixture HTML.

Adding a new framework handler
------------------------------
Implement ``FormLabelExtractor`` and append the instance to
``EXTRACTORS``. Keep ``can_handle`` a cheap substring check and keep
``extract`` defensive — extractors MUST NOT raise on malformed input,
they return ``None`` instead.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

import lxml.html


@dataclass(frozen=True)
class LabelResult:
    """Output of :func:`extract_label`."""

    text: str | None = None
    source: str | None = None
    """Which extractor matched — ``"ant-design"`` / ``"native"`` / ``None``."""


class FormLabelExtractor(Protocol):
    framework: str

    def can_handle(self, wrapper_html: str) -> bool:
        """Cheap pre-filter. Return True if this extractor might match."""

    def extract(self, wrapper_html: str, element_id: str) -> str | None:
        """Return the control's label text, or ``None`` if not found.

        MUST NOT raise on malformed / partial HTML.
        """


# ───────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────


def _parse(html: str):
    """Parse an HTML fragment, returning the root element or ``None``.

    Wraps ``lxml.html.fromstring`` so every extractor gets consistent
    error handling: empty / malformed input yields ``None`` instead
    of raising.
    """
    try:
        return lxml.html.fromstring(html)
    except Exception:
        return None


def _text_of(node) -> str:
    """Concatenate descendant text nodes, strip, collapse whitespace."""
    if node is None:
        return ""
    raw = "".join(node.itertext())
    return " ".join(raw.split()).strip()


def _closest_class_ancestor(node, class_names: set[str]):
    """Return the closest ancestor-or-self whose class contains any of
    ``class_names`` as an **exact token**. So ``"ant-form-item"``
    matches the class attribute ``"ant-form-item foo"`` but NOT
    ``"ant-form-item-row"``.

    Walking up from the target means we always pick the wrapper that
    actually owns this control, not some grandparent that happens to
    also contain us. This is the piece that prevents drift when pages
    have nested form-items.
    """
    cur = node
    while cur is not None:
        raw = cur.get("class") or ""
        if class_names.intersection(raw.split()):
            return cur
        cur = cur.getparent()
    return None


# Matches a class token that IS, or ends with "-<family>", where
# family is one of the three form-container conventions we trust.
# Using a regex with a dash / start-of-string boundary is stricter
# than a raw endswith check — it correctly rejects tokens like
# "conform-item" or "uniform-item" where "form-item" happens to
# appear at the tail of the string but without a word boundary in
# front of it.
_FORM_CONTAINER_RE = re.compile(r"(?:^|-)(?:form-item|form-group|form-field)$")


def _closest_class_token_matches(node, pattern: re.Pattern[str]):
    """Return the closest ancestor-or-self whose class attribute has
    any whitespace-separated token that matches ``pattern``.

    Passing a pre-compiled regex keeps this helper general — the
    caller owns the exact token shape they care about.
    """
    cur = node
    while cur is not None:
        raw = cur.get("class") or ""
        for token in raw.split():
            if pattern.search(token):
                return cur
        cur = cur.getparent()
    return None


def _clean_label_text(text: str) -> str:
    """Strip common decorative markers from label text.

    Handles the required-field asterisk on either side of the label
    and trailing colons (both half-width ``:`` and full-width ``：``),
    with any surrounding whitespace. This matches how Ant Design,
    Element Plus, and most other form libraries decorate a bare label
    string.
    """
    return text.strip().strip("*").strip(":：").strip()


# ───────────────────────────────────────────────────────────────────
# Ant Design · 4.x / 5.x
# ───────────────────────────────────────────────────────────────────


class AntDesignExtractor:
    """Pulls labels from Ant Design 4/5 form items.

    Ant Design renders form items as ::

        <div class="ant-form-item-row">
          <div class="ant-form-item-label">
            <label title="姓名">姓名</label>
          </div>
          <div class="ant-form-item-control">
            <div class="ant-form-item-control-input">
              <div class="ant-form-item-control-input-content">
                <input id="search-name" ...>
              </div>
            </div>
          </div>
        </div>

    The ``<label>`` element usually does NOT have a ``for`` attribute
    pointing at the control (Ant Design wires focus via JS), so
    matching by ``for=id`` wouldn't work.

    To avoid drift on malformed or nested pages (a form-item inside
    another form-item's control cell, which can happen with custom
    render props), this extractor starts at the target control and
    walks UP to its closest ``.ant-form-item-row`` (or
    ``.ant-form-item``) ancestor — guaranteeing the row we pick is
    the one that actually owns the control. Inside that row we only
    consider DIRECT-CHILD label cells, so nested form-items further
    down don't contaminate the match either.
    """

    framework = "ant-design"

    def can_handle(self, wrapper_html: str) -> bool:
        return "ant-form-item" in wrapper_html

    def extract(self, wrapper_html: str, element_id: str) -> str | None:
        root = _parse(wrapper_html)
        if root is None or not element_id:
            return None

        targets = root.cssselect(f"#{element_id}")
        if not targets:
            return None
        target = targets[0]

        row = _closest_class_ancestor(
            target, {"ant-form-item-row", "ant-form-item"}
        )
        if row is None:
            return None

        # Only direct-child label cells count. A nested form-item
        # sitting inside this row's control would also have a
        # .ant-form-item-label, but reading that would return the
        # wrong label for *this* row's control.
        for child in row.iterchildren():
            classes = (child.get("class") or "").split()
            if "ant-form-item-label" not in classes:
                continue
            # The standard layout puts a <label> inside the cell, but
            # Ant Design also supports custom label nodes (via the
            # `label` prop / slot). Try the <label> first, fall back
            # to the cell's own text.
            inner = child.cssselect("label")
            text = _text_of(inner[0]) if inner else _text_of(child)
            if text:
                return _clean_label_text(text)
        return None


# ───────────────────────────────────────────────────────────────────
# Native HTML5
# ───────────────────────────────────────────────────────────────────


class NativeLabelExtractor:
    """Standard HTML5 label/control associations.

    Covers, in order of precedence:

    1. ``<label for="id">…</label>`` — explicit
    2. ``aria-labelledby`` on the control → text of each referenced node
    3. Ancestor ``<label>…<input id="id">…</label>`` — implicit wrapping

    ``aria-label`` itself is intentionally NOT handled here because
    the page analyzer already captures it directly on the element;
    this extractor is for the "label-next-to-input" shape.
    """

    framework = "native"

    def can_handle(self, wrapper_html: str) -> bool:
        # Any HTML with a <label> element, or an aria-labelledby, is
        # a plausible target. Keep the check cheap.
        return "<label" in wrapper_html or "aria-labelledby" in wrapper_html

    def extract(self, wrapper_html: str, element_id: str) -> str | None:
        root = _parse(wrapper_html)
        if root is None or not element_id:
            return None

        # 1. <label for="id">
        for lbl in root.cssselect(f'label[for="{element_id}"]'):
            text = _text_of(lbl)
            if text:
                return text

        # 2. aria-labelledby on the element — resolve each id to text.
        target = root.cssselect(f"#{element_id}")
        if target:
            aria = target[0].get("aria-labelledby")
            if aria:
                parts: list[str] = []
                for ref_id in aria.split():
                    matches = root.cssselect(f"#{ref_id}")
                    if matches:
                        parts.append(_text_of(matches[0]))
                text = " ".join(p for p in parts if p).strip()
                if text:
                    return text

            # 3. Ancestor <label> that wraps the control.
            cur = target[0].getparent()
            while cur is not None:
                if cur.tag == "label":
                    # Exclude the control's own text descendants so the
                    # label reads like what a human sees next to the
                    # input, not the input's placeholder-rendered value.
                    clone = lxml.html.fromstring(lxml.html.tostring(cur))
                    for inp in clone.cssselect("input, select, textarea"):
                        inp.drop_tree()
                    text = _text_of(clone)
                    if text:
                        return text
                    break
                cur = cur.getparent()
        return None


# ───────────────────────────────────────────────────────────────────
# Generic form-item container
# ───────────────────────────────────────────────────────────────────


class GenericFormItemExtractor:
    """Fallback for the Form.Item idiom used by libraries the specific
    handlers don't recognise.

    Triggers on any ancestor whose class token CONTAINS one of three
    form-specific substrings — ``form-item``, ``form-group``,
    ``form-field`` — which covers Element Plus (``el-form-item``),
    Naive UI (``n-form-item``), Arco Design (``arco-form-item``),
    TDesign (``t-form-item``), Bootstrap 3/4 (``form-group``), and
    Material-ish libraries (``mat-form-field``), while deliberately
    refusing to match unrelated container patterns like
    ``menu-item``, ``list-item``, or ``card-item`` that happen to be
    common in the wild but are not form containers.

    Within the matched container the search is strict: only the
    direct children of the container are considered label candidates,
    and the child that contains the target input is skipped (so a
    label nested inside the control cell can't contaminate the
    match). Candidates are:

    - a direct child whose tag is ``<label>``
    - a direct child whose class token contains ``label`` (covers
      ``el-form-item__label``, ``n-form-item-label``, etc.)

    Anything that falls outside these shapes returns ``None`` rather
    than guessing from nearby text.
    """

    framework = "generic"
    # Cheap pre-filter — the real boundary-respecting match is done
    # by ``_FORM_CONTAINER_RE`` once we're iterating ancestors.
    _CAN_HANDLE_SUBSTRINGS = ("form-item", "form-group", "form-field")

    def can_handle(self, wrapper_html: str) -> bool:
        return any(s in wrapper_html for s in self._CAN_HANDLE_SUBSTRINGS)

    def extract(self, wrapper_html: str, element_id: str) -> str | None:
        root = _parse(wrapper_html)
        if root is None or not element_id:
            return None

        targets = root.cssselect(f"#{element_id}")
        if not targets:
            return None
        target = targets[0]

        container = _closest_class_token_matches(target, _FORM_CONTAINER_RE)
        if container is None:
            return None

        # The direct child of `container` that holds the input — we
        # will NOT look for labels inside that subtree, because a
        # label sitting in the same branch as the input is ambiguous
        # (it might belong to a nested form-item in that control).
        target_holding_child = None
        target_id_css = f"#{element_id}"
        for child in container.iterchildren():
            if child is target or child.cssselect(target_id_css):
                target_holding_child = child
                break

        for child in container.iterchildren():
            if child is target_holding_child:
                continue
            text = self._label_text_from(child)
            if text:
                return _clean_label_text(text)
        return None

    @staticmethod
    def _label_text_from(node) -> str | None:
        """Return the node's label text if it looks like a label cell.

        Two patterns count:
          1. ``node.tag == "label"`` — plain HTML label sibling.
          2. ``node`` has a class token that contains ``"label"``,
             e.g. ``el-form-item__label`` / ``n-form-item-label``.
             When a nested ``<label>`` is present inside the cell,
             read from it; otherwise read the cell's own text.

        Anything else → ``None`` (do not guess).
        """
        if node.tag == "label":
            text = _text_of(node)
            return text or None

        classes = (node.get("class") or "").split()
        if any("label" in c for c in classes):
            inner = node.cssselect("label")
            text = _text_of(inner[0]) if inner else _text_of(node)
            return text or None

        return None


# ───────────────────────────────────────────────────────────────────
# Dispatcher
# ───────────────────────────────────────────────────────────────────


EXTRACTORS: list[FormLabelExtractor] = [
    AntDesignExtractor(),
    NativeLabelExtractor(),
    GenericFormItemExtractor(),
]


def extract_label(wrapper_html: str, element_id: str) -> LabelResult:
    """Find the human-readable label for ``element_id`` within ``wrapper_html``.

    Walks :data:`EXTRACTORS` in order; first hit wins. If nothing
    matches (or ``element_id`` is empty), returns a
    :class:`LabelResult` with both fields ``None``.
    """
    if not wrapper_html or not element_id:
        return LabelResult()

    for ex in EXTRACTORS:
        if not ex.can_handle(wrapper_html):
            continue
        try:
            text = ex.extract(wrapper_html, element_id)
        except Exception:
            # Extractors are meant to be defensive; swallow any stray
            # error so one bad handler can't break the pipeline.
            continue
        if text:
            return LabelResult(text=text, source=ex.framework)

    return LabelResult()


# ───────────────────────────────────────────────────────────────────
# Group-label fallback (no anchor id)
# ───────────────────────────────────────────────────────────────────


def extract_group_label(wrapper_html: str) -> LabelResult:
    """Pull the form-item label from a wrapper without anchoring on an id.

    Used when the specific element has no ``id`` — most commonly a
    ``<input type=radio>`` / ``<input type=checkbox>`` that lives inside
    a form-item whose label belongs to the whole group. All radios /
    checkboxes in one form-item share that label, so returning it is
    semantically correct for the group's purpose (even if "label of
    this exact element" is technically ambiguous).

    Only honors the two shapes the analyzer already pins down:

    - Ant Design ``.ant-form-item-label`` direct child of a
      ``.ant-form-item-row`` / ``.ant-form-item``.
    - Generic form-item container (Element Plus / Naive / Arco /
      TDesign / Bootstrap / …) with a direct-child ``<label>`` or a
      child whose class token contains ``label``.

    Returns a :class:`LabelResult` with source ``"ant-design-group"``
    or ``"generic-group"``; returns ``LabelResult()`` when the wrapper
    has no recognisable form-item shape.
    """
    if not wrapper_html:
        return LabelResult()
    root = _parse(wrapper_html)
    if root is None:
        return LabelResult()

    # Ant Design: the root itself IS the form-item-row when the JS
    # captured the outermost form-item ancestor, so look for a direct
    # .ant-form-item-label child.
    candidates_ant = [root]
    candidates_ant.extend(root.cssselect(".ant-form-item-row, .ant-form-item"))
    for node in candidates_ant:
        for child in node.iterchildren():
            classes = (child.get("class") or "").split()
            if "ant-form-item-label" not in classes:
                continue
            inner = child.cssselect("label")
            text = _text_of(inner[0]) if inner else _text_of(child)
            if text:
                return LabelResult(
                    text=_clean_label_text(text), source="ant-design-group",
                )

    # Generic: walk root + any descendant whose class has a form-item
    # boundary, then pick the first direct-child label cell.
    candidates_generic = [root]
    for el in root.iter():
        raw_class = el.get("class") or ""
        for token in raw_class.split():
            if _FORM_CONTAINER_RE.search(token):
                candidates_generic.append(el)
                break
    for node in candidates_generic:
        for child in node.iterchildren():
            text = GenericFormItemExtractor._label_text_from(child)
            if text:
                return LabelResult(
                    text=_clean_label_text(text), source="generic-group",
                )

    return LabelResult()
