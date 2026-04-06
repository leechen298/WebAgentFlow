/**
 * Simplified HTML Snapshot — captures a minimal DOM representation of the
 * main content area for cases where structured extraction can't fully cover.
 *
 * Produces ~30-80KB of semantic HTML that preserves:
 *   - Element structure and nesting
 *   - Text content (truncated)
 *   - Key semantic attributes (class, role, aria-*, id, name, type, value, etc.)
 *   - Component structure identifiable by class names
 *
 * Strips: scripts, styles, SVGs, inline styles, event handlers, hidden elements,
 * navigation chrome.
 */

import { isNavigationChrome } from './component-classifier';

const MAX_HTML_SIZE = 80_000;
const MAX_TEXT_NODE = 100;
const MAX_DEPTH = 30;

const STRIP_TAGS = new Set([
  'script', 'style', 'svg', 'path', 'link', 'meta', 'noscript',
]);

const KEEP_ATTRS = new Set([
  'class', 'role', 'id', 'name', 'type', 'value', 'placeholder',
  'href', 'for', 'action', 'method',
  'aria-label', 'aria-labelledby', 'aria-describedby', 'aria-hidden',
  'aria-selected', 'aria-checked', 'aria-expanded', 'aria-disabled',
  'aria-required', 'aria-current', 'aria-haspopup', 'aria-controls',
  'contenteditable', 'readonly', 'disabled', 'required', 'checked',
  'selected', 'open',
  'data-mode-id', 'data-testid', 'data-cy',
]);

const EVENT_ATTR_RE = /^on[a-z]/;

/**
 * Find the main content area — avoids capturing sidebar/nav/footer.
 */
function findMainContent(): Element {
  return document.querySelector(
    '[role="main"], main, .main-content, .page-content, .app-main, ' +
    '[class*="layout-content"], [class*="main-container"]',
  ) ?? document.body;
}

/**
 * Check if an element is hidden (display:none, visibility:hidden, aria-hidden).
 */
function isHidden(el: Element): boolean {
  if (el.getAttribute('aria-hidden') === 'true') return true;
  if (el instanceof HTMLElement) {
    if (el.offsetParent === null && el !== document.body) {
      const style = getComputedStyle(el);
      if (style.display === 'none' || style.visibility === 'hidden') return true;
    }
    if (el.offsetWidth === 0 && el.offsetHeight === 0) return true;
  }
  return false;
}

/**
 * Simplify a DOM node into clean HTML string.
 */
function simplifyNode(node: Node, depth: number, output: string[], size: { current: number }): void {
  if (size.current >= MAX_HTML_SIZE) return;
  if (depth > MAX_DEPTH) return;

  if (node.nodeType === Node.TEXT_NODE) {
    let text = (node.textContent ?? '').replace(/\s+/g, ' ');
    if (!text.trim()) return;
    if (text.length > MAX_TEXT_NODE) {
      text = text.slice(0, MAX_TEXT_NODE) + '…';
    }
    const escaped = escapeHtml(text);
    output.push(escaped);
    size.current += escaped.length;
    return;
  }

  if (node.nodeType !== Node.ELEMENT_NODE) return;

  const el = node as Element;
  const tag = el.tagName.toLowerCase();

  // Strip unwanted tags
  if (STRIP_TAGS.has(tag)) return;

  // Skip hidden elements
  if (isHidden(el)) return;

  // Skip navigation chrome (except at top level)
  if (depth > 1 && isNavigationChrome(el)) return;

  // Build opening tag with filtered attributes
  const attrs = buildAttrs(el);
  const openTag = attrs ? `<${tag} ${attrs}>` : `<${tag}>`;

  // Self-closing tags
  if (['br', 'hr', 'img', 'input'].includes(tag)) {
    const selfClose = attrs ? `<${tag} ${attrs}/>` : `<${tag}/>`;
    output.push(selfClose);
    size.current += selfClose.length;
    return;
  }

  output.push(openTag);
  size.current += openTag.length;

  // Recurse into children
  for (const child of node.childNodes) {
    if (size.current >= MAX_HTML_SIZE) {
      output.push('<!-- truncated -->');
      size.current += 18;
      break;
    }
    simplifyNode(child, depth + 1, output, size);
  }

  const closeTag = `</${tag}>`;
  output.push(closeTag);
  size.current += closeTag.length;
}

/**
 * Build filtered attribute string for an element.
 */
function buildAttrs(el: Element): string {
  const parts: string[] = [];

  for (const attr of el.attributes) {
    const name = attr.name.toLowerCase();

    // Skip inline styles
    if (name === 'style') continue;

    // Skip event handlers
    if (EVENT_ATTR_RE.test(name)) continue;

    // Keep known semantic attributes
    if (KEEP_ATTRS.has(name)) {
      let value = attr.value;
      // Truncate long attribute values
      if (value.length > 100) value = value.slice(0, 100) + '…';
      parts.push(`${name}="${escapeAttr(value)}"`);
      continue;
    }

    // Keep short data-* attributes
    if (name.startsWith('data-') && attr.value.length <= 50) {
      parts.push(`${name}="${escapeAttr(attr.value)}"`);
    }
  }

  return parts.join(' ');
}

function escapeHtml(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function escapeAttr(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/**
 * Capture a simplified HTML snapshot of the main content area.
 * Returns a clean HTML string (~30-80KB) suitable for LLM consumption.
 */
export function captureSimplifiedHTML(): string {
  const root = findMainContent();
  const output: string[] = [];
  const size = { current: 0 };

  simplifyNode(root, 0, output, size);

  return output.join('');
}
