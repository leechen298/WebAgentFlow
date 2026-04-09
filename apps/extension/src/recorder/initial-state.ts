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
const SELECTOR_MAX_DEPTH = 5;

interface Counter { n: number }

/* ── Selector builder ────────────────────────────────────────────────────── */

/**
 * Build a short, reasonably unique CSS selector for the given element.
 * Walks up to SELECTOR_MAX_DEPTH ancestors or until hitting an #id.
 */
function buildSelector(el: Element): string {
  const parts: string[] = [];
  let current: Element | null = el;

  for (let d = 0; d < SELECTOR_MAX_DEPTH && current && current !== document.body; d++) {
    const tag = current.tagName.toLowerCase();
    const id = current.getAttribute('id');

    // If element has an id, use it and stop
    if (id && /^[a-zA-Z][\w-]*$/.test(id)) {
      parts.unshift(`#${id}`);
      break;
    }

    // Build tag + distinguishing attributes
    let segment = tag;

    // Prefer data-prop, name for form elements
    const dataProp = current.getAttribute('data-prop');
    const name = current.getAttribute('name');
    if (dataProp) {
      segment += `[data-prop="${dataProp}"]`;
    } else if (name) {
      segment += `[name="${name}"]`;
    } else {
      // Use classes (filter out state classes and very long ones)
      const classes = Array.from(current.classList).filter(
        (c) => c.length <= 30 && !/^(is-|has-|el-icon|ant-icon|active|focus|hover|disabled)/.test(c),
      );
      if (classes.length > 0) {
        segment += '.' + classes.slice(0, 3).join('.');
      }
    }

    // nth-of-type when siblings share the same tag+class
    const parent = current.parentElement;
    if (parent && !id) {
      const siblings = Array.from(parent.children).filter(
        (s) => s.tagName === current!.tagName,
      );
      if (siblings.length > 1) {
        const idx = siblings.indexOf(current) + 1;
        segment += `:nth-of-type(${idx})`;
      }
    }

    parts.unshift(segment);
    current = parent;
  }

  return parts.join(' > ');
}

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

const MAX_TABLE_ROWS = 20;
const MAX_CELL_TEXT = 60;

function extractCellText(cell: Element): string {
  // Check for input/select value inside cell
  const input = cell.querySelector<HTMLInputElement>(
    'input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"])',
  );
  if (input?.value?.trim()) return input.value.trim().slice(0, MAX_CELL_TEXT);

  const select = cell.querySelector<HTMLSelectElement>('select');
  if (select) {
    const selected = select.options[select.selectedIndex];
    const val = selected?.text?.trim() || select.value?.trim();
    if (val) return val.slice(0, MAX_CELL_TEXT);
  }

  const text = cleanText(cell.textContent);
  return text ? text.slice(0, MAX_CELL_TEXT) : '';
}

function buildTableNode(el: Element, counter: Counter): StateNode {
  const headers: string[] = [];
  for (const th of el.querySelectorAll('thead th, [role="columnheader"]')) {
    const text = cleanText(th.textContent);
    if (text && text.length <= 40) headers.push(text);
  }

  // Extract row data
  let dataRows = Array.from(el.querySelectorAll('tbody > tr'));
  if (!dataRows.length) {
    // ARIA table: skip the first row if headers were found (it's the header row)
    const allRows = Array.from(el.querySelectorAll('[role="row"]'));
    dataRows = headers.length > 0 ? allRows.slice(1) : allRows;
  }

  const rows: string[][] = [];
  for (const tr of dataRows.slice(0, MAX_TABLE_ROWS)) {
    const cells = tr.querySelectorAll('td, [role="gridcell"], [role="cell"]');
    if (cells.length === 0) continue;
    rows.push(Array.from(cells).map(extractCellText));
  }

  counter.n++;
  return {
    type: 'table',
    selector: buildSelector(el),
    ...(headers.length > 0 ? { headers } : {}),
    ...(rows.length > 0 ? { rows, itemCount: dataRows.length } : {}),
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
    selector: buildSelector(items[0]),
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

  const sel = buildSelector(container);

  // Complex form-item with titled sub-sections → group node with children
  if (hasSubSections(container)) {
    const children = walkChildren(container, depth, counter);
    if (children.length === 0) return [];
    counter.n++;
    return [{
      type: 'group',
      selector: sel,
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
      selector: sel,
      ...(label ? { label } : {}),
      ...(detectRequired(container) ? { required: true } : {}),
      ...(extractProp(container) ? { fieldProp: extractProp(container) } : {}),
      children: [tableChild],
    }];
  }

  // Fallback value extraction: if classifier returned a type but no value,
  // try reading visible non-label text from the content area.
  let value = defaultValueText;
  if (!value) {
    const content = findContentArea(container);
    // Tags / chips (multi-select display)
    const tagEls = content.querySelectorAll('[class*="tag"]:not([class*="close"])');
    const tagTexts: string[] = [];
    for (const tag of Array.from(tagEls).slice(0, 10)) {
      const clone = tag.cloneNode(true) as Element;
      clone.querySelectorAll('[class*="close"], [aria-label="close"]').forEach((x) => x.remove());
      const t = clone.textContent?.trim();
      if (t && t.length <= 40) tagTexts.push(t);
    }
    if (tagTexts.length > 0) {
      value = tagTexts.join(', ').slice(0, 200);
    }
  }

  // Upload: extract file URLs from <img> or <a> inside the upload area
  if (fieldType === 'upload' && !value) {
    const content = findContentArea(container);
    const urls: string[] = [];
    for (const img of content.querySelectorAll<HTMLImageElement>('img[src]')) {
      const src = img.src;
      if (src && !src.startsWith('data:') && !src.includes('placeholder')) {
        urls.push(src);
      }
    }
    if (urls.length === 0) {
      for (const a of content.querySelectorAll<HTMLAnchorElement>('a[href]')) {
        const href = a.href;
        if (href && href !== '#' && !href.startsWith('javascript:')) {
          urls.push(href);
        }
      }
    }
    if (urls.length > 0) value = urls.join(', ').slice(0, 500);
  }

  // Extract prop
  const prop = extractProp(container);

  counter.n++;
  const node: StateNode = {
    type: fieldType,
    selector: sel,
    ...(label ? { label } : {}),
    ...(value ? { value } : {}),
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
      selector: buildSelector(node),
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
    return [{ type: 'button', selector: buildSelector(node), label: text }];
  }

  // Transparent container → recurse, possibly wrap in section
  const children = walkChildren(node, depth, counter);

  const ctx = getNodeLabel(node);
  if (ctx && children.length > 0) {
    counter.n++;
    return [{ type: 'section', selector: buildSelector(node), label: ctx, children }];
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
