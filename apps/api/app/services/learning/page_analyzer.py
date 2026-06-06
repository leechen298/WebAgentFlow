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
from app.services.learning.capability_hints import build_capability_hints

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
            // Native <input type=radio|checkbox> are frequently painted
            // with opacity:0 by component libraries (Ant Design,
            // Element Plus, Naive, Arco, TDesign) so the framework's
            // styled wrapper can own the visible pixels. The input
            // itself stays in layout and is clickable (Playwright's
            // actionability check doesn't care about opacity either —
            // only display / visibility / pointer-events). Treat them
            // as visible whenever rect has size and display / visibility
            // are normal. For any OTHER element, keep opacity:0 as an
            // invisibility signal — a bare opacity:0 div is almost
            // always something the page is deliberately hiding.
            const isNativeToggle = el.tagName === 'INPUT'
                && (el.type === 'radio' || el.type === 'checkbox');
            let effectiveRect = rect;
            let clickSelector = '';
            if (isNativeToggle && (rect.width === 0 || rect.height === 0)) {
                const wrapper = el.closest('label');
                if (wrapper) {
                    effectiveRect = wrapper.getBoundingClientRect();
                    const rawValue = el.getAttribute('value');
                    if (rawValue !== null) {
                        const escapedValue = rawValue
                            .replace(/\\\\/g, '\\\\\\\\')
                            .replace(/"/g, '\\\\"');
                        clickSelector = 'label:has(input[type="' + el.type
                            + '"][value="' + escapedValue + '"])';
                    }
                }
            }
            const visible = effectiveRect.width > 0 && effectiveRect.height > 0
                && style.display !== 'none'
                && style.visibility !== 'hidden'
                && (isNativeToggle || style.opacity !== '0');

            // Build a best-effort unique selector. Only the strong
            // attributes (id / name / role+text) are resolved here;
            // the class-based fallback is left to Python so it can
            // filter out Ant Design 5's dev-only hash class token
            // (``css-dev-only-do-not-override-<hash>``), which has
            // zero discriminating power within a single app.
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

            // Structural context: is this element inside a <form>?
            const inForm = !!el.closest('form');
            // Explicit button type attribute (empty string if not set)
            const explicitType = el.getAttribute('type') || '';

            // Capture the form-item-like ancestor's outerHTML so the
            // server-side FormLabelExtractor has enough context to
            // find a label. Walk up to 10 levels, remembering the
            // OUTERMOST ancestor whose class contains "form-item" —
            // not the innermost. Ant Design nests wrappers deeply;
            // only the outer level contains BOTH the label cell and
            // the control cell, so breaking early on the innermost
            // match would hand the extractor a control-only snippet
            // and it wouldn't find the label.
            //
            // Depth of 10 is picked because Ant Design radio groups
            // bury the native <input type=radio> the deepest:
            //   input → span.ant-radio → label.ant-radio-wrapper
            //   → div.ant-radio-group → div.form-item-control-input-content
            //   → div.form-item-control-input → div.form-item-control
            //   → div.form-item-row
            // which is 7 parent hops before we reach the row. Depth 6
            // stopped at form-item-control, a cell that holds the
            // control but NOT the label cell, so extract_group_label
            // returned None for every radio. 10 covers radios plus a
            // margin for any similarly-nested future component. Going
            // arbitrarily deep is safe because non-form-item ancestors
            // never set outermostMatch.
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
                while (anc && levels < 10) {
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
                readOnly: !!el.readOnly,
                inForm: inForm,
                visible: visible,
                rect: {
                    x: Math.round(effectiveRect.x), y: Math.round(effectiveRect.y),
                    w: Math.round(effectiveRect.width), h: Math.round(effectiveRect.height)
                },
                selector: selector,
                clickSelector: clickSelector || null,
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
# Selector fallback
# ───────────────────────────────────────────────────────────────────

# Ant Design 5 injects ``css-dev-only-do-not-override-<hash>`` on every
# component it renders. The hash is stable within one app, so the class
# has zero discriminating power and is useless for a fallback selector.
_DEV_ONLY_CLASS_PREFIX = "css-dev-only-do-not-override-"


def _first_informative_class_token(class_string: str) -> str | None:
    """Return the first class token that isn't an Ant Design 5 dev-only
    hash class, or ``None`` if no token remains.

    Component-level classes can discriminate between otherwise similar
    elements, but test-page-only tokens should not be treated as a special
    success path. The dev-only token is shared across every Ant Design
    component in a single app, so selecting by it collapses unrelated
    elements into one selector.
    """
    for token in class_string.split():
        if token.startswith(_DEV_ONLY_CLASS_PREFIX):
            continue
        return token
    return None


def _build_fallback_selector(raw: dict) -> str:
    """Build a fallback CSS selector for elements without id / name /
    role+text, skipping Ant Design 5's dev-only hash class.

    Native toggles in a radio / checkbox group share every structural
    attribute (tag, class, name) except ``value`` — the option key.
    Emit ``input[type="radio"][value="active"]`` so the planner's
    target selector uniquely identifies which radio to click. Without
    this the fallback would hand back ``input.ant-radio-input`` for
    all three Status radios and the executor would click whichever
    happens to be first in the DOM.

    Worst case returns the bare tag — still better than a class shared
    by every component on the page.
    """
    tag = raw["tag"]

    click_selector = raw.get("clickSelector")
    if isinstance(click_selector, str) and click_selector:
        return click_selector

    if tag == "input":
        input_type = (raw.get("type") or "").lower()
        raw_value = raw.get("value")
        if input_type in ("radio", "checkbox") and isinstance(raw_value, str):
            escaped = (
                raw_value.replace("\\", "\\\\")
                         .replace('"', '\\"')
            )
            return f'input[type="{input_type}"][value="{escaped}"]'

    token = _first_informative_class_token(raw.get("className") or "")
    return f"{tag}.{token}" if token else tag


# ───────────────────────────────────────────────────────────────────
# Classification logic
# ───────────────────────────────────────────────────────────────────

_FILLABLE_TAGS = {"input", "textarea"}
_FILLABLE_INPUT_TYPES = {
    "text", "search", "email", "password", "tel", "url", "number",
    "date", "datetime-local", "month", "time", "week",
    None, "",
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
# "name" / "role" / "status" appear on admin-style list pages as
# column filters. They sit below username/email in the precedence
# order so that ``username`` on a login form (which also contains
# the substring "name") still classifies as ``username``.
_NAME_FRAGMENTS = (
    "name",
    "姓名", "名称",
    "名前",
)
_ROLE_FRAGMENTS = (
    "role",
    "角色",
    "役職", "役割",
)
_STATUS_FRAGMENTS = (
    "status", "state",
    "状态", "状態",
    "ステータス",
)
_SEARCH_FRAGMENTS = (
    "search", "query",
    "搜索", "查询", "検索",
)


def _infer_semantic_role(
    raw: dict,
    category: ElementCategory,
    label_text: str | None = None,
) -> str | None:
    """Infer semantic_role for fillable / toggle elements from structural signals.

    Signals used (in priority order):
      1. HTML input type attribute (most authoritative, fillable only)
      2. autocomplete hints would be good but we don't capture them yet
      3. name / id / placeholder / aria-label fragments (universal words only)
      4. label_text — folded in because radios and checkboxes in a group
         typically lack self-identifiers (all three Status radios share
         ``type=radio`` with different ``value`` attributes and no id),
         so the form-item label ("Status") is the only signal that
         distinguishes the group's semantic purpose.
    """
    if category not in ("fillable", "toggle"):
        return None

    # Rule 1: HTML type attribute. password / email / search as input
    # types only make sense on fillables; radio / checkbox have their
    # own type values but are already classified by category=toggle.
    if category == "fillable":
        input_type = (raw.get("type") or "").lower()
        if input_type == "password":
            return "password"
        if input_type == "email":
            return "email"
        if input_type == "search":
            return "search"

    # Rule 2: scan identifiers for universal word fragments. Include
    # label_text so toggles with no self-identifier inherit the group
    # role from their form-item label.
    hints = " ".join(filter(None, [
        raw.get("name"), raw.get("id"),
        raw.get("placeholder"), raw.get("ariaLabel"),
        label_text or "",
    ])).lower()

    if any(f in hints for f in _USERNAME_FRAGMENTS):
        return "username"
    if any(f in hints for f in _EMAIL_FRAGMENTS):
        return "email"
    # name / role / status sit between the identity fragments above
    # and the catch-all ``search`` below so admin-table filters like
    # ``search-field`` / ``filter-role`` / ``status-select`` get more
    # specific buckets than the generic ``search`` role.
    if any(f in hints for f in _NAME_FRAGMENTS):
        return "name"
    if any(f in hints for f in _ROLE_FRAGMENTS):
        return "role"
    if any(f in hints for f in _STATUS_FRAGMENTS):
        return "status"
    if any(f in hints for f in _SEARCH_FRAGMENTS):
        return "search"

    # Default: generic text for fillables; None for toggles since we
    # don't have a "generic toggle" semantic bucket.
    return "text" if category == "fillable" else None


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
    from app.services.analysis.form_label_extractor import (
        extract_group_label,
        extract_label,
    )

    wrapper_html: str = raw.get("wrapperHtml") or ""
    element_id: str | None = raw.get("id") or None
    label = (
        extract_label(wrapper_html, element_id)
        if wrapper_html and element_id
        else None
    )
    # Toggles (radio / checkbox) usually lack a self-id — the form-item
    # label belongs to the whole group, and every radio within the
    # group legitimately inherits it. Fall back to a group-label lookup
    # that scans the wrapper for an ant-form-item / generic form-item
    # label cell without anchoring on a specific id.
    if (label is None or not label.text) and category == "toggle" and wrapper_html:
        label = extract_group_label(wrapper_html)
    label_text = label.text if label else None

    selector = raw.get("selector") or _build_fallback_selector(raw)

    raw_value = raw.get("value")
    element_value = raw_value if isinstance(raw_value, str) else None

    return DiscoveredElement(
        category=category,
        tag=raw["tag"],
        element_type=raw.get("type"),
        element_value=element_value,
        id=raw.get("id"),
        name=raw.get("name"),
        role=raw.get("role"),
        placeholder=raw.get("placeholder"),
        text=(raw.get("text") or "")[:80],
        aria_label=raw.get("ariaLabel"),
        content_editable=raw.get("contentEditable", False),
        readonly=raw.get("readOnly", False),
        visible=raw.get("visible", False),
        rect=raw.get("rect", {}),
        selector=selector,
        reason=reason,
        semantic_role=_infer_semantic_role(raw, category, label_text),
        label_text=label_text,
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

    analysis = PageAnalysis(
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
    analysis.capability_hints = build_capability_hints(analysis)
    return analysis
