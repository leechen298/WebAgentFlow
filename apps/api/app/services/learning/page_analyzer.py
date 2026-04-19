"""Page analyzer — autonomous discovery of interactive elements.

Opens a live Playwright page and discovers all interactive elements without
any pre-written selectors, task definitions, or site-specific knowledge.

This is the first phase of autonomous exploration:
  Page → analyze → discover elements → classify → recommend actions

No site-specific logic. No hardcoded selectors. The analyzer reads
the live DOM and classifies what it finds.
"""

from __future__ import annotations

import logging
import time

from app.schemas.page_analysis import (
    DiscoveredElement,
    ElementCategory,
    PageAnalysis,
)
from app.services.execution.execution_runtime import ExecutionRuntime

logger = logging.getLogger(__name__)


# JavaScript that runs in the browser to discover all interactive elements.
# Returns raw element data — classification happens server-side in Python.
_DISCOVER_JS = """() => {
    const results = [];
    const seen = new Set();

    // All selectors that might indicate interactivity
    const selectors = [
        'input', 'textarea', 'select', 'button',
        'a[href]',
        '[role="button"]', '[role="link"]', '[role="textbox"]',
        '[role="combobox"]', '[role="searchbox"]', '[role="menuitem"]',
        '[role="tab"]', '[role="switch"]', '[role="checkbox"]',
        '[role="radio"]', '[role="listbox"]', '[role="option"]',
        '[role="menuitemcheckbox"]', '[role="menuitemradio"]',
        '[contenteditable="true"]', '[contenteditable=""]',
        '[tabindex]:not([tabindex="-1"])',
        // Class-based button patterns (div/span used as buttons). We
        // start with a loose CSS filter then tighten per-element below
        // so containers like .button-group / .btn-toolbar-list don't
        // sneak in.
        '[class*="btn"]', '[class*="button"]',
    ];

    // Token-boundary check for the loose class-based selectors above.
    // Only keep the element if it has a class TOKEN exactly equal to
    // "btn" / "button", or a token ending in "-btn" / "-button".
    // This excludes .button-group (container) and .toolbar-button-list
    // (container) while still matching .btn, .btn-primary via btn,
    // .submit-button, .v-btn etc.
    function hasButtonLikeClass(el) {
        const raw = el.className;
        const cls = (raw && raw.toString) ? raw.toString() : '';
        if (!cls) return false;
        for (const token of cls.split(/\\s+/)) {
            if (!token) continue;
            if (token === 'btn' || token === 'button') return true;
            if (token.endsWith('-btn') || token.endsWith('-button')) return true;
        }
        return false;
    }

    // Compute a content hint for elements whose innerText is empty.
    // Answers "what's visually inside this button if it has no
    // text?" — so the operator reading the analyzer output can tell
    // one icon button from another. Only populated when the element
    // has NO own text AND NO own aria-label (those are shown
    // separately). Returns null if nothing informative is inside.
    function computeContentHint(el) {
        const ownText = ((el.innerText || el.textContent) || '').trim();
        if (ownText) return null;
        if (el.getAttribute('aria-label')) return null;

        // 1. Descendant aria-label — page author's explicit label.
        const aria = el.querySelector('[aria-label]:not([aria-label=""])');
        if (aria) {
            return 'aria:' + (aria.getAttribute('aria-label') || '').slice(0, 60);
        }

        // 2. <svg data-icon="X"> — Ant Design / Ant Icons convention.
        const svgIcon = el.querySelector('svg[data-icon]');
        if (svgIcon) {
            const name = svgIcon.getAttribute('data-icon') || '';
            if (name) return 'icon:' + name.slice(0, 60);
        }

        // 3. <img> — prefer alt, fall back to filename.
        const img = el.querySelector('img');
        if (img) {
            if (img.alt) return 'img:' + img.alt.slice(0, 60);
            let src = img.src || '';
            if (src) {
                const q = src.indexOf('?');
                if (q >= 0) src = src.slice(0, q);
                const last = src.substring(src.lastIndexOf('/') + 1);
                return 'img:' + (last || 'image').slice(0, 60);
            }
            return 'img';
        }

        // 4. Bare <svg> — "there's an icon but no identifying name".
        if (el.querySelector('svg')) return 'icon';

        return null;
    }

    for (const sel of selectors) {
        const isClassButtonSel = sel === '[class*="btn"]' || sel === '[class*="button"]';
        for (const el of document.querySelectorAll(sel)) {
            if (seen.has(el)) continue;
            // Gate loose class-based matches to real button-shaped tokens.
            if (isClassButtonSel && !hasButtonLikeClass(el)) continue;
            seen.add(el);

            const rect = el.getBoundingClientRect();
            const style = getComputedStyle(el);
            const visible = rect.width > 0 && rect.height > 0
                && style.display !== 'none'
                && style.visibility !== 'hidden'
                && style.opacity !== '0';

            // Build a best-effort unique selector
            let selector = '';
            if (el.id) {
                selector = '#' + CSS.escape(el.id);
            } else if (el.name) {
                selector = el.tagName.toLowerCase()
                    + '[name="' + el.name.replace(/"/g, '\\\\"') + '"]';
            } else if (el.getAttribute('role')) {
                const role = el.getAttribute('role');
                const text = (el.innerText || '').trim().slice(0, 30);
                if (text) {
                    selector = '[role="' + role + '"]';
                }
            }
            if (!selector) {
                // Fallback: tag + class snippet
                const tag = el.tagName.toLowerCase();
                const cls = (el.className.toString() || '').split(/\\s+/)[0];
                selector = cls ? tag + '.' + CSS.escape(cls) : tag;
            }

            // Structural context: is this element inside a <form>?
            const inForm = !!el.closest('form');
            // Explicit button type attribute (empty string if not set)
            const explicitType = el.getAttribute('type') || '';

            // Capture the form-item-like ancestor's outerHTML so the
            // server-side FormLabelExtractor has enough context to
            // find a label. Walk up to 6 levels, remembering the
            // OUTERMOST ancestor whose class contains "form-item" —
            // not the innermost. Ant Design nests wrappers deeply
            // (control-input-content → control-input → control →
            // form-item-row → form-item); only the outer level
            // contains BOTH the label cell and the control cell, so
            // breaking early on the innermost match would hand the
            // extractor a control-only snippet and it wouldn't find
            // the label.
            //
            // "form-item" as a substring covers the major Vue/React
            // UI libraries that share the Form.Item idiom:
            //   ant-form-item (Ant Design)
            //   el-form-item  (Element Plus)
            //   n-form-item   (Naive UI)
            //   arco-form-item (Arco Design)
            //   t-form-item   (TDesign)
            // Keeping the matcher narrow — no speculative keywords
            // like "form-row" / "field-wrapper" — avoids grabbing
            // application-specific classes that merely happen to
            // contain a form-ish word.
            //
            // If nothing matches within the cap, fall back to 3
            // levels of parent so Native <label for=id> siblings
            // still get captured. Finally, truncate to 6 KB to keep
            // the payload bounded.
            let wrapperHtml = el.outerHTML || '';
            {
                let anc = el.parentElement;
                let levels = 0;
                let outermostMatch = null;
                while (anc && levels < 6) {
                    const rawCls = anc.className;
                    const cls = (rawCls && rawCls.toString) ? rawCls.toString() : '';
                    if (cls.indexOf('form-item') !== -1) {
                        outermostMatch = anc;
                    }
                    anc = anc.parentElement;
                    levels++;
                }
                if (outermostMatch && outermostMatch.outerHTML) {
                    wrapperHtml = outermostMatch.outerHTML;
                } else if (el.id) {
                    // No form-item detected. Grab up to 3 levels up so
                    // Native <label for=id> / aria-labelledby siblings
                    // have a chance to show up.
                    let p = el.parentElement;
                    for (let i = 0; p && i < 3; i++) p = p.parentElement;
                    if (p && p.outerHTML) wrapperHtml = p.outerHTML;
                }
            }
            if (wrapperHtml.length > 6000) {
                wrapperHtml = wrapperHtml.slice(0, 6000);
            }

            const rawClass = el.className;
            const className = (rawClass && rawClass.toString) ? rawClass.toString() : '';

            results.push({
                tag: el.tagName.toLowerCase(),
                type: el.type || null,
                explicitType: explicitType,
                id: el.id || null,
                name: el.getAttribute('name') || null,
                role: el.getAttribute('role') || null,
                placeholder: el.placeholder || null,
                text: (el.innerText || el.textContent || '').trim().slice(0, 80),
                value: (el.value || '').slice(0, 80),
                ariaLabel: el.getAttribute('aria-label') || null,
                contentEditable: el.contentEditable === 'true',
                inForm: inForm,
                visible: visible,
                rect: {
                    x: Math.round(rect.x), y: Math.round(rect.y),
                    w: Math.round(rect.width), h: Math.round(rect.height)
                },
                selector: selector,
                href: el.href || null,
                inputMode: el.inputMode || null,
                wrapperHtml: wrapperHtml,
                className: className,
                contentHint: computeContentHint(el),
            });
        }
    }
    return results;
}"""


# ───────────────────────────────────────────────────────────────────
# Classification logic
# ───────────────────────────────────────────────────────────────────

_FILLABLE_TAGS = {"input", "textarea"}
_FILLABLE_INPUT_TYPES = {
    "text", "search", "email", "password", "tel", "url", "number", None, "",
}
_SUBMIT_INPUT_TYPES = {"submit", "button", "image"}
_TOGGLE_INPUT_TYPES = {"checkbox", "radio"}

_FILLABLE_ROLES = {"textbox", "combobox", "searchbox", "spinbutton"}
_BUTTON_ROLES = {"button"}
_NAV_ROLES = {"link", "menuitem", "tab"}
_TOGGLE_ROLES = {"checkbox", "radio", "switch", "menuitemcheckbox", "menuitemradio"}
_SELECT_ROLES = {"listbox", "option"}


def _classify(raw: dict) -> tuple[ElementCategory, str]:
    """Classify a raw element dict into a category based on STRUCTURAL signals.

    Classification uses only: tag, type attribute, role, form context,
    contenteditable. NO text/keyword matching — text can be any language and
    keyword-based classification would be site-specific.
    """
    tag = raw["tag"]
    input_type = (raw.get("type") or "").lower()
    explicit_type = (raw.get("explicitType") or "").lower()
    role = (raw.get("role") or "").lower()
    is_ce = raw.get("contentEditable", False)
    in_form = raw.get("inForm", False)

    # Fillable: text inputs, textareas, contenteditable, fillable roles.
    # <textarea> has no meaningful type attribute (JS reports type="textarea"),
    # so don't filter it by input_type.
    if tag == "textarea":
        return "fillable", "<textarea>"
    if tag == "input" and input_type in _FILLABLE_INPUT_TYPES:
        return "fillable", f"<input> type={input_type or 'text'}"
    if is_ce:
        return "fillable", f"<{tag}> contenteditable"
    if role in _FILLABLE_ROLES:
        return "fillable", f"role={role}"

    # Toggle: checkboxes, radios, switches
    if tag == "input" and input_type in _TOGGLE_INPUT_TYPES:
        return "toggle", f"<input type={input_type}>"
    if role in _TOGGLE_ROLES:
        return "toggle", f"role={role}"

    # Select
    if tag == "select":
        return "select", "<select>"
    if role in _SELECT_ROLES:
        return "select", f"role={role}"

    # Submit vs clickable — purely structural:
    #   <input type=submit>    → submit
    #   <button type=submit>   → submit
    #   <button> in <form> with no type attr → submit (HTML default)
    #   everything else → clickable
    if tag == "input" and input_type in _SUBMIT_INPUT_TYPES:
        return "submit", f"<input type={input_type}>"
    if tag == "button":
        if explicit_type == "submit":
            return "submit", "<button type=submit>"
        if not explicit_type and in_form:
            # HTML default type for <button> inside <form> is "submit"
            return "submit", "<button> in <form> (default type=submit)"
        return "clickable", f"<button> type={explicit_type or 'button'}"
    if role in _BUTTON_ROLES:
        return "clickable", f"role={role}"

    # Navigation: links, menu items, tabs
    if tag == "a" and raw.get("href"):
        return "navigation", "<a href>"
    if role in _NAV_ROLES:
        return "navigation", f"role={role}"

    # Custom buttons: elements with a class token of "btn" / "button"
    # or ending in "-btn" / "-button". Picked up here rather than at
    # selector time so the rest of the classifier has first chance at
    # stronger signals (real <button> tag, role="button", etc.).
    if _has_button_like_class(raw):
        return "clickable", f"<{tag}> class-as-button"

    return "other", f"<{tag}> tabindex or unknown"


def _has_button_like_class(raw: dict) -> bool:
    """True if the element's className contains a token that reads as
    a button class per common conventions (``btn`` / ``button`` as an
    exact token, or a token ending in ``-btn`` / ``-button``).

    This is what catches ``<div class="btn">`` / ``<span
    class="submit-button">`` patterns without picking up container
    classes like ``button-group`` / ``btn-toolbar-list``.
    """
    cls = raw.get("className") or ""
    for token in cls.split():
        if token in ("btn", "button"):
            return True
        if token.endswith("-btn") or token.endswith("-button"):
            return True
    return False


# Generic word fragments that hint at a field's semantic purpose.
# Keep these to universal substrings common to English + Chinese + Japanese.
# NO site-specific names (no baidu/google/bing/etc.).
_USERNAME_FRAGMENTS = (
    "user", "login", "account", "uid",
    "用户", "账号", "账户", "帐号", "登录",
    "ユーザー", "ログイン",
)
_EMAIL_FRAGMENTS = (
    "email", "mail", "邮箱", "邮件", "メール",
)
_SEARCH_FRAGMENTS = (
    "search", "query",
    "搜索", "查询", "検索",
)


def _infer_semantic_role(raw: dict, category: ElementCategory) -> str | None:
    """Infer semantic_role for fillable elements using structural signals only.

    Signals used (in priority order):
      1. HTML input type attribute (most authoritative)
      2. autocomplete hints would be good but we don't capture them yet
      3. name / id / placeholder / aria-label fragments (universal words only)
    """
    if category != "fillable":
        return None

    input_type = (raw.get("type") or "").lower()
    # Rule 1: HTML type attribute is authoritative
    if input_type == "password":
        return "password"
    if input_type == "email":
        return "email"
    if input_type == "search":
        return "search"

    # Rule 2: scan identifiers for universal word fragments
    hints = " ".join(filter(None, [
        raw.get("name"), raw.get("id"),
        raw.get("placeholder"), raw.get("ariaLabel"),
    ])).lower()

    if any(f in hints for f in _USERNAME_FRAGMENTS):
        return "username"
    if any(f in hints for f in _EMAIL_FRAGMENTS):
        return "email"
    if any(f in hints for f in _SEARCH_FRAGMENTS):
        return "search"

    # Default for a text-input-like fillable
    return "text"


def _to_discovered(raw: dict, category: ElementCategory, reason: str) -> DiscoveredElement:
    """Convert raw JS element data to DiscoveredElement.

    Runs the FormLabelExtractor against the element's wrapper HTML when
    the element has an ``id`` (the extractors key off ``#id``). When no
    handler matches, ``label_text`` / ``label_source`` stay ``None`` —
    we deliberately don't guess from nearby text nodes.
    """
    # Lazy import: keep the analysis package optional-feeling from
    # this file's top, and it makes module-load cheaper for callers
    # that only need the schema.
    from app.services.analysis.form_label_extractor import extract_label

    wrapper_html: str = raw.get("wrapperHtml") or ""
    element_id: str | None = raw.get("id") or None
    label = (
        extract_label(wrapper_html, element_id)
        if wrapper_html and element_id
        else None
    )

    return DiscoveredElement(
        category=category,
        tag=raw["tag"],
        element_type=raw.get("type"),
        id=raw.get("id"),
        name=raw.get("name"),
        role=raw.get("role"),
        placeholder=raw.get("placeholder"),
        text=(raw.get("text") or "")[:80],
        aria_label=raw.get("ariaLabel"),
        content_editable=raw.get("contentEditable", False),
        visible=raw.get("visible", False),
        rect=raw.get("rect", {}),
        selector=raw.get("selector", ""),
        reason=reason,
        semantic_role=_infer_semantic_role(raw, category),
        label_text=label.text if label else None,
        label_source=label.source if label else None,
        content_hint=raw.get("contentHint") or None,
    )


# ───────────────────────────────────────────────────────────────────
# Public API
# ───────────────────────────────────────────────────────────────────

def analyze_page(runtime: ExecutionRuntime) -> PageAnalysis:
    """Analyze the current page and discover all interactive elements.

    The runtime must already have a page loaded (navigate first).
    Returns a PageAnalysis with classified elements and stats.
    """
    page = runtime.page
    if page is None or page.is_closed():
        raise RuntimeError("Cannot analyze: no page loaded in runtime.")

    ts = int(time.time() * 1000)

    # Take a screenshot of the page before analysis
    screenshot_ref = None
    try:
        screenshot_ref = runtime.screenshot()
    except Exception as exc:
        logger.warning("Screenshot failed during analysis: %s", exc)

    # Run discovery JS
    raw_elements: list[dict] = page.evaluate(_DISCOVER_JS)
    logger.info("Discovered %d raw elements on %s", len(raw_elements), page.url)

    # Classify each element
    buckets: dict[ElementCategory, list[DiscoveredElement]] = {
        "fillable": [], "submit": [], "clickable": [], "navigation": [],
        "select": [], "toggle": [], "other": [],
    }
    hidden: list[DiscoveredElement] = []

    for raw in raw_elements:
        category, reason = _classify(raw)
        elem = _to_discovered(raw, category, reason)
        if elem.visible:
            buckets[category].append(elem)
        else:
            hidden.append(elem)

    total_visible = sum(len(v) for v in buckets.values())

    return PageAnalysis(
        url=page.url,
        title=page.title(),
        timestamp_ms=ts,
        screenshot_ref=screenshot_ref,
        fillable=buckets["fillable"],
        submit=buckets["submit"],
        clickable=buckets["clickable"],
        navigation=buckets["navigation"],
        select=buckets["select"],
        toggle=buckets["toggle"],
        other=buckets["other"],
        hidden_interactive=hidden,
        total_discovered=len(raw_elements),
        total_visible=total_visible,
        total_hidden=len(hidden),
    )
