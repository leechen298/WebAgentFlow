/**
 * Initial State Sampler — AST tree output.
 *
 * Produces a `StateNode[]` tree that preserves DOM hierarchy.
 * Recursion stops at leaf nodes (input, select, table, button, etc.)
 * and captures their data. Structural containers become section/group nodes.
 */

import type { StateNode, PageInitialState } from '@web-agent-flow/shared-types';
import { getCanonicalPageUrl } from './page-url';
import { captureSimplifiedHTML } from './html-snapshot';
import {
  isFormContainer,
  isNavigationChrome,
  classifyElement,
  getComponentNames,
} from './component-classifier';
import {
  extractUniversalLabel,
  detectRequired,
  detectFieldType,
  findContentArea,
} from './label-extractor';
import { cleanLabel, isVisible, extractItemTitle } from './dom-utils';

const MAX_NODES = 300;
const MAX_DEPTH = 30;

interface Counter { n: number }

/* ── Text helpers ────────────────────────────────────────────────────────── */

function cleanText(text: string | null | undefined): string | undefined {
  if (!text) return undefined;
  const cleaned = text.replace(/\s+/g, ' ').trim();
  return cleaned.length > 0 ? cleaned : undefined;
}

/* ── Skip detection ──────────────────────────────────────────────────────── */

const SKIP_TAGS = new Set([
  'script', 'style', 'svg', 'link', 'meta', 'noscript', 'template', 'iframe',
]);

function shouldSkip(el: Element): boolean {
  const tag = el.tagName.toLowerCase();
  if (SKIP_TAGS.has(tag)) return true;
  if (el instanceof HTMLElement && !isVisible(el)) return true;
  if (tag === 'main') return false;
  if (isNavigationChrome(el)) return true;
  return false;
}

/* ── Heading / title detection ───────────────────────────────────────────── */

const HEADING_TAG_RE = /^h[1-6]$/;
const TITLE_CLASS_RE = /(?:^|[\s_-])(?:title|header|head|heading)(?:$|[\s_-])/;

function isHeadingElement(el: Element): boolean {
  const tag = el.tagName.toLowerCase();
  return HEADING_TAG_RE.test(tag) || tag === 'legend' || el.getAttribute('role') === 'heading';
}

function isLeafLike(el: Element): boolean {
  return !el.querySelector(
    'table, ul, ol, dl, form, input, select, textarea, ' +
      '[contenteditable="true"], [role="grid"], [role="table"]',
  );
}

function extractTitleText(el: Element): string | undefined {
  const clone = el.cloneNode(true) as Element;
  clone
    .querySelectorAll(
      'button, [role="button"], input, select, textarea, svg, ' +
        '[class*="btn"], [class*="close"], [class*="icon"]',
    )
    .forEach((n) => n.remove());
  const text = cleanText(clone.textContent);
  if (!text || text.length > 60) return undefined;
  return cleanLabel(text);
}

function extractInlineTitle(el: Element): string | undefined {
  if (isFormContainer(el)) return undefined;
  if (isHeadingElement(el)) return extractTitleText(el);
  if (!isLeafLike(el)) return undefined;

  const names = getComponentNames(el);
  if (names.some((n) => n === 'header' || n === 'head' || n === 'title')) {
    return extractTitleText(el);
  }

  const cls = (el.className || '').toLowerCase();
  if (TITLE_CLASS_RE.test(cls)) return extractTitleText(el);

  return undefined;
}

/* ── ARIA / semantic section context ─────────────────────────────────────── */

function getNodeLabel(node: Element): string | undefined {
  const role = node.getAttribute('role');
  if (role === 'region' || role === 'group') {
    const label = node.getAttribute('aria-label');
    if (label) return cleanText(label);
    const ids = node.getAttribute('aria-labelledby');
    if (ids) {
      const text = ids
        .split(/\s+/)
        .map((id) => document.getElementById(id)?.textContent)
        .filter(Boolean)
        .join(' ');
      return cleanText(text);
    }
  }
  return undefined;
}

/* ── Structural content inside form items ────────────────────────────────── */

function detectStructuralContent(
  area: Element,
): { type: string; itemCount?: number } | undefined {
  const table = area.querySelector('table');
  if (table) {
    const rows = table.querySelectorAll('tbody > tr');
    return { type: 'table', itemCount: rows.length || undefined };
  }
  if (area.querySelector('[role="grid"], [role="table"]')) return { type: 'table' };

  for (const child of area.children) {
    if (classifyElement(child)?.type === 'table') return { type: 'table' };
    for (const gc of child.children) {
      if (classifyElement(gc)?.type === 'table') return { type: 'table' };
    }
  }
  return undefined;
}

/* ── Complex form-item detection ─────────────────────────────────────────── */

function hasSubSections(container: Element): boolean {
  const content = findContentArea(container);
  let titleCount = 0;
  const scan = (el: Element, depth: number): void => {
    if (depth > 4 || titleCount >= 2) return;
    for (const child of el.children) {
      if (titleCount >= 2) return;
      if (extractInlineTitle(child)) {
        titleCount++;
      } else if (!isFormContainer(child)) {
        scan(child, depth + 1);
      }
    }
  };
  scan(content, 0);
  return titleCount >= 2;
}

/* ── Table node building ─────────────────────────────────────────────────── */

function buildTableNode(el: Element, counter: Counter): StateNode {
  const headers: string[] = [];
  for (const th of el.querySelectorAll('thead th, [role="columnheader"]')) {
    const text = cleanText(th.textContent);
    if (text && text.length <= 40) headers.push(text);
  }
  let rowCount = el.querySelectorAll('tbody > tr').length;
  if (!rowCount) {
    const ariaRows = el.querySelectorAll('[role="row"]');
    rowCount = Math.max(0, ariaRows.length - (headers.length > 0 ? 1 : 0));
  }

  counter.n++;
  return {
    type: 'table',
    ...(headers.length > 0 ? { headers } : {}),
    ...(rowCount > 0 ? { itemCount: rowCount } : {}),
  };
}

function buildTableNodeFromArea(area: Element, counter: Counter): StateNode {
  const table = area.querySelector('table, [role="grid"], [role="table"]');
  if (table) return buildTableNode(table, counter);

  // Component-based table
  for (const child of area.children) {
    if (classifyElement(child)?.type === 'table') return buildTableNode(child, counter);
    for (const gc of child.children) {
      if (classifyElement(gc)?.type === 'table') return buildTableNode(gc, counter);
    }
  }
  counter.n++;
  return { type: 'table' };
}

/* ── Button detection ────────────────────────────────────────────────────── */

function isActionButton(el: Element): boolean {
  const tag = el.tagName.toLowerCase();
  if (tag !== 'button' && el.getAttribute('role') !== 'button') return false;
  const text = cleanText(el.textContent);
  if (!text || text.length > 30) return false;
  const cls = (el.className || '').toLowerCase();
  if (/close|icon-only|collapse/.test(cls)) return false;
  return true;
}

/* ── Repeated sibling detection ──────────────────────────────────────────── */

function getPrimaryClass(el: Element): string | undefined {
  const cls = el.getAttribute('class');
  if (!cls) return undefined;
  const classes = cls.split(/\s+/).filter(
    (c) => c.length > 2 && !c.startsWith('is-') && !c.startsWith('has-'),
  );
  return classes[0] || undefined;
}

function hasNestedFormItems(el: Element, maxDepth: number): boolean {
  if (maxDepth <= 0) return false;
  for (const child of el.children) {
    if (isFormContainer(child)) return true;
    if (hasNestedFormItems(child, maxDepth - 1)) return true;
  }
  return false;
}

function findRepeatedGroupEnd(children: Element[], start: number): number {
  const first = children[start];
  if (isFormContainer(first) || isStandaloneControl(first) || isActionButton(first)) {
    return start + 1;
  }
  const cls = classifyElement(first);
  if (cls?.type === 'table') return start + 1;

  const tag = first.tagName;
  const primaryCls = getPrimaryClass(first);
  if (!primaryCls) return start + 1;

  if (hasNestedFormItems(first, 8)) return start + 1;

  let end = start + 1;
  while (end < children.length) {
    const next = children[end];
    if (next.tagName !== tag || getPrimaryClass(next) !== primaryCls) break;
    end++;
  }
  return end;
}

function buildListNode(items: Element[], counter: Counter): StateNode {
  const labels: string[] = [];
  for (const item of items.slice(0, 10)) {
    const label = extractItemTitle(item);
    if (label) labels.push(label);
  }
  counter.n++;
  return {
    type: 'list',
    itemCount: items.length,
    ...(labels.length > 0 ? { value: labels.join(', ') } : {}),
  };
}

/* ── Standalone control detection ────────────────────────────────────────── */

const SKIP_INPUT_TYPES = new Set(['hidden', 'button', 'submit', 'reset', 'image']);

function isStandaloneControl(el: Element): boolean {
  const tag = el.tagName.toLowerCase();
  if (tag === 'input') return !SKIP_INPUT_TYPES.has((el as HTMLInputElement).type);
  if (tag === 'select' || tag === 'textarea') return true;
  if (el.getAttribute('contenteditable') === 'true') return true;
  return false;
}

function extractControlLabel(el: Element): string | undefined {
  const ariaLabel = el.getAttribute('aria-label');
  if (ariaLabel) return cleanText(ariaLabel);

  const labelledBy = el.getAttribute('aria-labelledby');
  if (labelledBy) {
    const text = labelledBy
      .split(/\s+/)
      .map((id) => document.getElementById(id)?.textContent)
      .filter(Boolean)
      .join(' ');
    if (text) return cleanText(text);
  }

  if (el.id) {
    const lbl = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
    if (lbl?.textContent) return cleanText(lbl.textContent);
  }

  const ph = el.getAttribute('placeholder');
  if (ph) return cleanText(ph);

  const parentLabel = el.closest('label');
  if (parentLabel) {
    const clone = parentLabel.cloneNode(true) as Element;
    clone.querySelectorAll('input, select, textarea, button').forEach((c) => c.remove());
    return cleanText(clone.textContent);
  }

  return undefined;
}

function extractControlValue(
  el: Element,
): { value?: string; type?: string; placeholder?: string } {
  const tag = el.tagName.toLowerCase();
  if (tag === 'input') {
    const input = el as HTMLInputElement;
    const type = input.type || 'text';
    if (type === 'checkbox' || type === 'radio') {
      return { type, value: input.checked ? 'checked' : undefined };
    }
    return {
      type,
      value: cleanText(input.value),
      placeholder: cleanText(input.getAttribute('placeholder')),
    };
  }
  if (tag === 'select') {
    const select = el as HTMLSelectElement;
    const selected = select.options[select.selectedIndex];
    return {
      type: 'select',
      value: selected ? cleanText(selected.text || select.value) : undefined,
    };
  }
  if (tag === 'textarea') {
    return { type: 'textarea', value: cleanText((el as HTMLTextAreaElement).value) };
  }
  if (el.hasAttribute('contenteditable')) {
    return { type: 'richtext', value: cleanText(el.textContent) };
  }
  return {};
}

/* ── Form-item processing ────────────────────────────────────────────────── */

function processFormItem(
  container: Element,
  depth: number,
  counter: Counter,
): StateNode[] {
  const label = extractUniversalLabel(container);

  // Complex form-item with titled sub-sections → group node with children
  if (hasSubSections(container)) {
    const children = walkChildren(container, depth, counter);
    if (children.length === 0) return [];
    counter.n++;
    return [{
      type: 'group',
      ...(label ? { label } : {}),
      children,
    }];
  }

  // Simple form-item → leaf node
  const detected = detectFieldType(container);
  let { fieldType } = detected;
  const { placeholder, defaultValueText, defaultValueHtml } = detected;

  // Check structural content override
  const BASIC_CONTROL_TYPES = new Set(['input', 'number', 'textarea']);
  if (BASIC_CONTROL_TYPES.has(fieldType)) {
    const structural = detectStructuralContent(findContentArea(container));
    if (structural) {
      fieldType = structural.type;
    }
  }

  // Table inside form-item → form-item wrapping a table child
  if (fieldType === 'table') {
    const tableChild = buildTableNodeFromArea(findContentArea(container), counter);
    counter.n++;
    return [{
      type: 'group',
      ...(label ? { label } : {}),
      ...(detectRequired(container) ? { required: true } : {}),
      ...(extractProp(container) ? { fieldProp: extractProp(container) } : {}),
      children: [tableChild],
    }];
  }

  // Extract prop
  const prop = extractProp(container);

  counter.n++;
  const node: StateNode = {
    type: fieldType,
    ...(label ? { label } : {}),
    ...(defaultValueText ? { value: defaultValueText } : {}),
    ...(placeholder ? { placeholder } : {}),
    ...(detectRequired(container) ? { required: true } : {}),
    ...(prop ? { fieldProp: prop } : {}),
    ...(detected.itemCount ? { itemCount: detected.itemCount } : {}),
  };
  if (defaultValueHtml) node.htmlContent = defaultValueHtml;

  return [node];
}

function extractProp(container: Element): string | undefined {
  const control = container.querySelector<HTMLElement>(
    'input, select, textarea, [contenteditable="true"]',
  );
  return (
    control?.getAttribute('data-prop') ||
    control?.getAttribute('name') ||
    control?.getAttribute('id') ||
    undefined
  );
}

/* ── Main AST traversal ──────────────────────────────────────────────────── */

/**
 * Walk a parent's children: detect headings (→ section nodes), detect repeated
 * siblings (→ list nodes), and recurse into content nodes.
 */
function walkChildren(
  parent: Element,
  depth: number,
  counter: Counter,
): StateNode[] {
  // Pre-filter to visible, non-empty children
  const visible: Element[] = [];
  for (const child of parent.children) {
    if (shouldSkip(child)) continue;
    if (!child.children.length && !(child.textContent?.trim())) continue;
    visible.push(child);
  }

  const results: StateNode[] = [];
  let heading: string | undefined;
  let sectionChildren: StateNode[] = [];
  let i = 0;

  while (i < visible.length) {
    if (counter.n >= MAX_NODES) break;
    const child = visible[i];

    // Check for inline title → start new section
    const title = extractInlineTitle(child);
    if (title) {
      // Flush previous section
      if (heading && sectionChildren.length > 0) {
        counter.n++;
        results.push({ type: 'section', label: heading, children: sectionChildren });
      } else {
        results.push(...sectionChildren);
      }
      heading = title;
      sectionChildren = [];
      i++;
      continue;
    }

    // Detect 3+ consecutive similar siblings → list node
    const groupEnd = findRepeatedGroupEnd(visible, i);
    if (groupEnd - i >= 3) {
      sectionChildren.push(buildListNode(visible.slice(i, groupEnd), counter));
      i = groupEnd;
      continue;
    }

    // Normal node
    const childNodes = walkNode(child, depth + 1, counter);
    sectionChildren.push(...childNodes);
    i++;
  }

  // Flush final section
  if (heading && sectionChildren.length > 0) {
    counter.n++;
    results.push({ type: 'section', label: heading, children: sectionChildren });
  } else {
    results.push(...sectionChildren);
  }

  return results;
}

/**
 * Process a single DOM node → returns 0, 1, or many StateNode items.
 * Transparent containers are flattened (children returned directly).
 * ARIA-labeled regions become section nodes.
 */
function walkNode(
  node: Element,
  depth: number,
  counter: Counter,
): StateNode[] {
  if (counter.n >= MAX_NODES || depth > MAX_DEPTH) return [];

  // Form-item: leaf (simple) or group (complex)
  if (isFormContainer(node)) {
    return processFormItem(node, depth, counter);
  }

  // Table / grid → leaf node
  const classification = classifyElement(node);
  if (classification?.type === 'table') {
    return [buildTableNode(node, counter)];
  }

  // Standalone form control not wrapped in a form-item
  if (isStandaloneControl(node)) {
    const label = extractControlLabel(node);
    const { value, type, placeholder } = extractControlValue(node);
    if (!label && !value) return [];

    counter.n++;
    return [{
      type: type || 'input',
      ...(label ? { label } : {}),
      ...(value ? { value } : {}),
      ...(placeholder ? { placeholder } : {}),
      ...(node.hasAttribute('required') || node.getAttribute('aria-required') === 'true'
        ? { required: true }
        : {}),
    }];
  }

  // Action button (not icon-only / close)
  if (isActionButton(node)) {
    const text = cleanText(node.textContent);
    if (!text) return [];
    counter.n++;
    return [{ type: 'button', label: text }];
  }

  // Transparent container → recurse, possibly wrap in section
  const children = walkChildren(node, depth, counter);

  const ctx = getNodeLabel(node);
  if (ctx && children.length > 0) {
    counter.n++;
    return [{ type: 'section', label: ctx, children }];
  }

  return children; // flatten
}

/* ── Entry point ─────────────────────────────────────────────────────────── */

export function captureInitialState(): PageInitialState {
  const counter: Counter = { n: 0 };

  const root =
    document.querySelector(
      'main, [role="main"], .main-content, .app-main, .el-main, .ant-layout-content',
    ) || document.body;

  const stateTree = walkChildren(root, 0, counter);

  let htmlSnapshot: string | undefined;
  try {
    htmlSnapshot = captureSimplifiedHTML();
  } catch {
    // degrade gracefully
  }

  return {
    capturedAt: Date.now(),
    pageUrl: getCanonicalPageUrl(location.href),
    pageTitle: document.title,
    stateTree,
    ...(htmlSnapshot ? { htmlSnapshot } : {}),
  };
}
