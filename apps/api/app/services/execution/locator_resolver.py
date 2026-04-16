"""Locator resolver (Phase 7C).

Resolves an ``ExecutionRequest`` into a ``ResolvedLocator`` by walking
the 6-level ``LocatorPriority`` chain against the live Playwright page.

The resolver does NOT execute actions — it only answers:
  "Which element on the page should be operated on, and how to find it?"

Scope — Phase 7C is ONLY the locator resolution layer:
  - NOT an action executor          (7D)
  - NOT a post-action observer      (7E)
  - NOT a wait/retry/recovery system
  - NOT a task planner

Strategy priority (from ``LocatorPriority``):
  1. SERVER_AST_MATCH  — server-side authoritative AST path + tag + label
  2. STRONG_ATTRIBUTE  — id / name / href / placeholder / role
  3. TAG_TEXT_LABEL    — tag + visible text / aria-label
  4. REGION_SCOPED     — narrow search to a region, then match
  5. FALLBACK_SELECTOR — recorded CSS selector
  6. CLIENT_AST_MATCH  — client-side astMatch (lowest, degraded)
"""

from __future__ import annotations

import logging
import re
from typing import Any

from playwright.sync_api import Page

from app.schemas.execution import ExecutionRequest, LocatorHint, LocatorPriority
from app.schemas.locator import ResolvedLocator, SelectorDescriptor
from app.services.execution.execution_runtime import ExecutionRuntime, PageObservationError

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────
# Internal: per-strategy resolvers
# ───────────────────────────────────────────────────────────────────

def _try_server_ast_match(hint: LocatorHint, page: Page, trace: list[str]) -> SelectorDescriptor | None:
    """Strategy 1: SERVER_AST_MATCH — use tag + label from server AST."""
    meta = hint.meta or {}
    tag = meta.get("tag")
    label = meta.get("label")
    match_type = meta.get("match_type")

    if not tag:
        trace.append("SERVER_AST_MATCH: no tag in meta, skip")
        return None

    # Try tag + exact text match first
    if label:
        # For interactive elements, use role-based if possible
        role = _tag_to_role(tag)
        if role:
            desc = SelectorDescriptor(
                selector_type="role",
                role=role,
                name=label,
                exact=False,
            )
            count = _count_matches(page, desc)
            if count == 1:
                trace.append(f"SERVER_AST_MATCH: role={role} name={label!r} → 1 match")
                return desc
            elif count > 1:
                trace.append(f"SERVER_AST_MATCH: role={role} name={label!r} → {count} matches, ambiguous")
                # Fall through to try CSS

        # CSS: tag + text content
        desc = _css_tag_has_text(tag, label)
        count = _count_matches(page, desc)
        if count == 1:
            trace.append(f"SERVER_AST_MATCH: {tag}:has-text({label!r}) → 1 match")
            return desc
        elif count > 1:
            # Try with region_hint to narrow
            region = meta.get("region_hint")
            if region:
                scoped = _scope_to_region(page, region, desc, trace, "SERVER_AST_MATCH")
                if scoped:
                    return scoped
            trace.append(f"SERVER_AST_MATCH: {tag}:has-text({label!r}) → {count} matches, no unique")
        else:
            trace.append(f"SERVER_AST_MATCH: {tag}:has-text({label!r}) → 0 matches")

    # Bare tag match as last resort within this strategy
    if match_type == "exact" and tag:
        trace.append("SERVER_AST_MATCH: no label, cannot produce unique locator from tag alone")

    return None


def _try_strong_attribute(hint: LocatorHint, page: Page, trace: list[str]) -> SelectorDescriptor | None:
    """Strategy 2: STRONG_ATTRIBUTE — id / name / href / placeholder / role."""
    meta = hint.meta or {}
    attr = meta.get("attribute", "")
    tag = meta.get("tag", "")

    # Parse "attr=value" from hint.value
    parts = hint.value.split("=", 1)
    if len(parts) != 2:
        trace.append(f"STRONG_ATTRIBUTE: cannot parse {hint.value!r}")
        return None
    attr_name, attr_val = parts[0], parts[1]

    if attr_name == "id":
        desc = SelectorDescriptor(selector_type="css", selector=f"#{_css_escape(attr_val)}")
        count = _count_matches(page, desc)
        if count >= 1:
            trace.append(f"STRONG_ATTRIBUTE: #{attr_val} → {count} match(es)")
            return desc
        trace.append(f"STRONG_ATTRIBUTE: #{attr_val} → 0 matches")
        return None

    if attr_name == "placeholder":
        desc = SelectorDescriptor(selector_type="placeholder", name=attr_val)
        count = _count_matches(page, desc)
        if count >= 1:
            trace.append(f"STRONG_ATTRIBUTE: placeholder={attr_val!r} → {count} match(es)")
            return desc
        trace.append(f"STRONG_ATTRIBUTE: placeholder={attr_val!r} → 0 matches")
        return None

    if attr_name == "role":
        desc = SelectorDescriptor(selector_type="role", role=attr_val)
        count = _count_matches(page, desc)
        if count >= 1:
            trace.append(f"STRONG_ATTRIBUTE: role={attr_val} → {count} match(es)")
            return desc
        trace.append(f"STRONG_ATTRIBUTE: role={attr_val} → 0 matches")
        return None

    # Generic attribute selector: [attr="value"]
    tag_prefix = tag if tag else ""
    sel = f'{tag_prefix}[{attr_name}="{_css_escape_attr(attr_val)}"]'
    desc = SelectorDescriptor(selector_type="css", selector=sel)
    count = _count_matches(page, desc)
    if count >= 1:
        trace.append(f"STRONG_ATTRIBUTE: {sel} → {count} match(es)")
        return desc
    trace.append(f"STRONG_ATTRIBUTE: {sel} → 0 matches")
    return None


def _try_tag_text_label(hint: LocatorHint, page: Page, trace: list[str]) -> SelectorDescriptor | None:
    """Strategy 3: TAG_TEXT_LABEL — tag + visible text / aria-label."""
    # hint.value format: "tag::text content"
    parts = hint.value.split("::", 1)
    if len(parts) != 2:
        trace.append(f"TAG_TEXT_LABEL: cannot parse {hint.value!r}")
        return None
    tag, text = parts[0], parts[1].strip()

    if not text:
        trace.append("TAG_TEXT_LABEL: empty text, skip")
        return None

    # Try role-based first
    role = _tag_to_role(tag)
    if role:
        desc = SelectorDescriptor(selector_type="role", role=role, name=text, exact=False)
        count = _count_matches(page, desc)
        if count == 1:
            trace.append(f"TAG_TEXT_LABEL: role={role} name={text!r} → 1 match")
            return desc
        if count > 1:
            # Try exact match to narrow
            desc_exact = SelectorDescriptor(selector_type="role", role=role, name=text, exact=True)
            count_exact = _count_matches(page, desc_exact)
            if count_exact == 1:
                trace.append(f"TAG_TEXT_LABEL: role={role} name={text!r} exact → 1 match")
                return desc_exact
            trace.append(f"TAG_TEXT_LABEL: role={role} name={text!r} → {count} matches")

    # CSS with :has-text()
    desc = _css_tag_has_text(tag, text)
    count = _count_matches(page, desc)
    if count == 1:
        trace.append(f"TAG_TEXT_LABEL: {tag}:has-text({text!r}) → 1 match")
        return desc
    if count > 1:
        trace.append(f"TAG_TEXT_LABEL: {tag}:has-text({text!r}) → {count} matches, ambiguous")
    else:
        trace.append(f"TAG_TEXT_LABEL: {tag}:has-text({text!r}) → 0 matches")
    return None


def _try_region_scoped(hint: LocatorHint, page: Page, trace: list[str],
                       request: ExecutionRequest) -> SelectorDescriptor | None:
    """Strategy 4: REGION_SCOPED — narrow search to a region, then match."""
    region_name = hint.value
    if not region_name:
        trace.append("REGION_SCOPED: empty region name, skip")
        return None

    # We need the action target info to know what to look for inside the region
    action = request.action
    target_desc = action.target_description

    # Extract tag from target description (format: '<tag> "text"' or '<tag> selector')
    tag, text = _parse_target_description(target_desc)

    if not tag and not text:
        trace.append(f"REGION_SCOPED: region={region_name!r} but no parseable target info")
        return None

    # Build a scoped selector: find the region first, then the target within it
    if tag and text:
        inner = _css_tag_has_text(tag, text)
    elif text:
        inner = SelectorDescriptor(selector_type="text", name=text)
    else:
        inner = SelectorDescriptor(selector_type="css", selector=tag)

    scoped = _scope_to_region(page, region_name, inner, trace, "REGION_SCOPED")
    return scoped


def _try_fallback_selector(hint: LocatorHint, page: Page, trace: list[str]) -> SelectorDescriptor | None:
    """Strategy 5: FALLBACK_SELECTOR — recorded CSS selector."""
    selector = hint.value
    if not selector:
        trace.append("FALLBACK_SELECTOR: empty selector, skip")
        return None

    desc = SelectorDescriptor(selector_type="css", selector=selector)
    count = _count_matches(page, desc)
    if count >= 1:
        trace.append(f"FALLBACK_SELECTOR: {selector!r} → {count} match(es)")
        return desc
    trace.append(f"FALLBACK_SELECTOR: {selector!r} → 0 matches")
    return None


def _try_client_ast_match(hint: LocatorHint, page: Page, trace: list[str]) -> SelectorDescriptor | None:
    """Strategy 6: CLIENT_AST_MATCH — lowest priority, degraded path."""
    meta = hint.meta or {}
    node_label = meta.get("nodeLabel", "")
    area_label = meta.get("areaLabel", "")

    trace.append("CLIENT_AST_MATCH: attempting degraded client-side match")

    # Try to use nodeLabel as text match
    if node_label:
        desc = SelectorDescriptor(selector_type="text", name=node_label)
        count = _count_matches(page, desc)
        if count == 1:
            trace.append(f"CLIENT_AST_MATCH: text={node_label!r} → 1 match (degraded)")
            return desc
        if count > 1 and area_label:
            # Try scoping to area
            scoped = _scope_to_region(page, area_label, desc, trace, "CLIENT_AST_MATCH")
            if scoped:
                return scoped
        trace.append(f"CLIENT_AST_MATCH: text={node_label!r} → {count} matches")

    trace.append("CLIENT_AST_MATCH: no usable info for resolution")
    return None


# ───────────────────────────────────────────────────────────────────
# Strategy dispatch table
# ───────────────────────────────────────────────────────────────────

_STRATEGY_HANDLERS = {
    LocatorPriority.SERVER_AST_MATCH.name: _try_server_ast_match,
    LocatorPriority.STRONG_ATTRIBUTE.name: _try_strong_attribute,
    LocatorPriority.TAG_TEXT_LABEL.name: _try_tag_text_label,
    # REGION_SCOPED handled specially (needs request)
    LocatorPriority.FALLBACK_SELECTOR.name: _try_fallback_selector,
    LocatorPriority.CLIENT_AST_MATCH.name: _try_client_ast_match,
}


# ───────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────

_ROLE_MAP: dict[str, str] = {
    "button": "button",
    "a": "link",
    "input": "textbox",
    "textarea": "textbox",
    "select": "combobox",
    "img": "img",
    "nav": "navigation",
    "dialog": "dialog",
    "table": "table",
    "th": "columnheader",
}


def _tag_to_role(tag: str) -> str:
    """Map an HTML tag to a probable ARIA role, or empty string."""
    return _ROLE_MAP.get(tag.lower(), "")


def _css_escape(val: str) -> str:
    """Minimal CSS identifier escaping."""
    return re.sub(r'([^a-zA-Z0-9_-])', r'\\\1', val)


def _css_escape_attr(val: str) -> str:
    """Escape a value for CSS attribute selector [attr="value"]."""
    return val.replace("\\", "\\\\").replace('"', '\\"')


def _css_tag_has_text(tag: str, text: str) -> SelectorDescriptor:
    """Build a CSS selector: tag:has-text("text")."""
    escaped = text.replace('"', '\\"')
    return SelectorDescriptor(
        selector_type="css",
        selector=f'{tag}:has-text("{escaped}")',
    )


def _count_matches(page: Page, desc: SelectorDescriptor) -> int:
    """Count how many elements match a descriptor on the page."""
    try:
        loc = to_playwright_locator(page, desc)
        return loc.count()
    except Exception:
        return 0


def to_playwright_locator(page: Page, desc: SelectorDescriptor):
    """Convert a SelectorDescriptor to a Playwright Locator object."""
    if desc.selector_type == "css":
        loc = page.locator(desc.selector)
    elif desc.selector_type == "xpath":
        loc = page.locator(f"xpath={desc.selector}")
    elif desc.selector_type == "role":
        kwargs: dict[str, Any] = {}
        if desc.name:
            kwargs["name"] = desc.name
            kwargs["exact"] = desc.exact
        loc = page.get_by_role(desc.role, **kwargs)
    elif desc.selector_type == "text":
        loc = page.get_by_text(desc.name, exact=desc.exact)
    elif desc.selector_type == "label":
        loc = page.get_by_label(desc.name, exact=desc.exact)
    elif desc.selector_type == "placeholder":
        loc = page.get_by_placeholder(desc.name, exact=desc.exact)
    elif desc.selector_type == "test_id":
        loc = page.get_by_test_id(desc.name)
    else:
        loc = page.locator(desc.selector)

    if desc.nth is not None:
        loc = loc.nth(desc.nth)

    return loc


def _scope_to_region(
    page: Page,
    region_name: str,
    inner_desc: SelectorDescriptor,
    trace: list[str],
    strategy_name: str,
) -> SelectorDescriptor | None:
    """Try to find inner_desc within a named region on the page."""
    # Look for region containers by common patterns
    region_selectors = [
        f'section:has-text("{region_name}")',
        f'[aria-label="{region_name}"]',
        f'fieldset:has(legend:has-text("{region_name}"))',
        f'div:has(> h1:has-text("{region_name}")), div:has(> h2:has-text("{region_name}")), div:has(> h3:has-text("{region_name}"))',
    ]

    for region_sel in region_selectors:
        try:
            region_loc = page.locator(region_sel)
            if region_loc.count() == 0:
                continue

            # Scope inner match within the region container
            inner_expr = inner_desc.selector if inner_desc.selector_type == "css" else f"text={inner_desc.name}"
            scoped_loc = region_loc.first.locator(inner_expr)
            count = scoped_loc.count()
            if count == 1:
                # Build a combined CSS selector
                combined_sel = f'{region_sel} >> {inner_desc.selector if inner_desc.selector_type == "css" else f"text={inner_desc.name}"}'
                trace.append(f"{strategy_name}: scoped to region {region_name!r} → 1 match")
                return SelectorDescriptor(selector_type="css", selector=combined_sel)
            if count > 1:
                trace.append(f"{strategy_name}: scoped to region {region_name!r} → {count} matches, still ambiguous")
        except Exception:
            continue

    trace.append(f"{strategy_name}: region {region_name!r} not found or no inner match")
    return None


def _parse_target_description(desc: str) -> tuple[str, str]:
    """Parse '<tag> "text"' or '<tag> selector' format from target_description."""
    # Match: <tag> "text"
    m = re.match(r'^<(\w+)>\s+"([^"]*)"', desc)
    if m:
        return m.group(1), m.group(2)
    # Match: <tag> anything
    m = re.match(r'^<(\w+)>\s*(.*)', desc)
    if m:
        return m.group(1), m.group(2).strip()
    # Just text
    return "", desc.strip()


def _get_element_info(page: Page, desc: SelectorDescriptor) -> tuple[str, str]:
    """Get tag and text of the first matched element."""
    try:
        loc = to_playwright_locator(page, desc)
        if loc.count() == 0:
            return "", ""
        tag = loc.first.evaluate("el => el.tagName.toLowerCase()") or ""
        text = (loc.first.text_content() or "")[:80]
        return tag, text
    except Exception:
        return "", ""


# ───────────────────────────────────────────────────────────────────
# Public API
# ───────────────────────────────────────────────────────────────────

def resolve_locator(
    request: ExecutionRequest,
    runtime: ExecutionRuntime,
) -> ResolvedLocator:
    """Resolve the target element from an ExecutionRequest.

    Walks the ``LocatorPriority`` chain in order, validating each
    candidate against the live page.  Returns the first match or a
    structured failure.

    This is the **single entry point** for locator resolution.
    Phase 7D consumes the result — it does NOT re-resolve.
    """
    trace: list[str] = []
    page = runtime.page

    if page is None or page.is_closed():
        return ResolvedLocator(
            ok=False,
            trace=["No usable page — runtime not started or page was closed."],
        )

    hints = request.locator_hints
    if not hints:
        trace.append("No locator hints provided")

    # Walk hints in priority order (they come pre-sorted from build_execution_request)
    for hint in hints:
        strategy = hint.strategy

        if strategy == LocatorPriority.REGION_SCOPED.name:
            desc = _try_region_scoped(hint, page, trace, request)
        else:
            handler = _STRATEGY_HANDLERS.get(strategy)
            if handler is None:
                trace.append(f"Unknown strategy: {strategy}")
                continue
            desc = handler(hint, page, trace)

        if desc is not None:
            matched_count = _count_matches(page, desc)
            matched_tag, matched_text = _get_element_info(page, desc)
            is_fallback = LocatorPriority[strategy].value > LocatorPriority.REGION_SCOPED.value

            return ResolvedLocator(
                ok=True,
                source=strategy,
                confidence=hint.confidence,
                descriptor=desc,
                matched_tag=matched_tag,
                matched_text=matched_text,
                matched_count=matched_count,
                trace=trace,
                fallback_used=is_fallback,
            )

    # All strategies exhausted — structured failure
    trace.append("All strategies exhausted, no match found")
    return ResolvedLocator(
        ok=False,
        source="",
        confidence="low",
        trace=trace,
        fallback_used=True,
    )
