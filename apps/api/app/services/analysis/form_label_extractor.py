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
    ``class_names``. Matches by exact class-token equality, so
    ``"ant-form-item"`` matches the class attribute ``"ant-form-item
    foo"`` but NOT ``"ant-form-item-row"``.

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
                return text.lstrip("*").rstrip(":").rstrip("：").strip()
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
# Dispatcher
# ───────────────────────────────────────────────────────────────────


EXTRACTORS: list[FormLabelExtractor] = [
    AntDesignExtractor(),
    NativeLabelExtractor(),
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
