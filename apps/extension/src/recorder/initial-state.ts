/**
 * Initial State Sampler — Semantic State Tree output.
 *
 * Three-layer architecture:
 *   1. Semantic State Tree (stateTree) — primary, expresses page semantic blocks
 *   2. Leaf-level local HTML (localHtml) — fallback on complex leaf nodes
 *   3. Raw HTML Snapshot (rawHtmlSnapshot) — debug/fallback only
 *
 * Container nodes (section/group) carry semantic info only (no selector).
 * Leaf nodes (input/select/button/table) carry selector + value + optional localHtml.
 */

import type {
  StateNode,
  PageInitialState,
  TableCellNode,
} from '@web-agent-flow/shared-types';
import { getCanonicalPageUrl } from './page-url';
import { captureSimplifiedHTML } from './html-snapshot';
import {
  isFormContainer,
  classifyElement,
  getComponentNames,
  isInsideCompound,
} from './component-classifier';
import {
  extractUniversalLabel,
  detectRequired,
  detectFieldType,
  findContentArea,
  extractHintOrError,
} from './label-extractor';
import { cleanLabel, isVisible, extractItemTitle } from './dom-utils';

const MAX_NODES = 1000;
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

function cleanTextNodeValue(node: ChildNode | null | undefined): string | undefined {
  if (!node || node.nodeType !== Node.TEXT_NODE) return undefined;
  return cleanText(node.textContent);
}

function getDirectTextSnippets(el: Element): string[] {
  const snippets: string[] = [];
  for (const child of el.childNodes) {
    const text = cleanTextNodeValue(child);
    if (text) snippets.push(text);
  }
  return snippets;
}

function getDirectText(el: Element): string | undefined {
  const snippets = getDirectTextSnippets(el);
  if (snippets.length === 0) return undefined;
  return snippets.join(' ').trim();
}

/* ── Skip detection ──────────────────────────────────────────────────────── */

const SKIP_TAGS = new Set([
  'script', 'style', 'svg', 'link', 'meta', 'noscript', 'template',
]);

function shouldSkip(el: Element): boolean {
  const tag = el.tagName.toLowerCase();
  if (SKIP_TAGS.has(tag)) return true;
  // No visibility skip — hidden elements are still parsed and marked with cssState.
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
    'table, ul, ol, dl, form, input, select, textarea, button, [role="button"], ' +
      'a[href], [contenteditable="true"], [role="grid"], [role="table"]',
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

function getContainerLabel(node: Element): string | undefined {
  const aria = cleanText(node.getAttribute('aria-label'));
  if (aria) return aria;

  const titleAttr = cleanText(node.getAttribute('title'));
  if (titleAttr && titleAttr.length <= 120) return titleAttr;

  for (const child of Array.from(node.children)) {
    if (!isHeadingElement(child) && !extractInlineTitle(child)) continue;
    const text = extractTitleText(child);
    if (text) return text;
  }

  return getNodeLabel(node);
}

function inferPreservedContainerType(node: Element): string {
  const cls = (node.className || '').toLowerCase();
  const role = (node.getAttribute('role') || '').toLowerCase();
  const tag = node.tagName.toLowerCase();

  if (role === 'alert' || /\bel-alert\b|\balert\b|\btip\b/.test(cls)) return 'alert';
  if (/\bsection-title\b/.test(cls) || isHeadingElement(node) || extractInlineTitle(node)) return 'heading';
  if (/\btask-card\b/.test(cls)) return 'task-card';
  if (/\btask-header\b/.test(cls)) return 'task-header';
  if (/\btask-actions\b/.test(cls) || /\bmove-buttons\b/.test(cls) || /\bbatch-actions\b/.test(cls)) {
    return 'button-group';
  }
  if (/\bprobability-sum\b|\bstatus\b/.test(cls)) return 'status-block';
  if (/\bcustom-config\b/.test(cls)) return 'custom-config';
  if (/\bel-dialog__footer\b|\bdialog-footer\b|\bcomplex-footer\b/.test(cls)) return 'dialog-footer';
  if (/\baction-wrapper\b/.test(cls)) return 'button-group';
  if (/\btable-wrapper\b/.test(cls)) return 'table-wrapper';
  if (/\bitem-container\b|\bcontent\b|\bwrapper\b|\bcontainer\b/.test(cls)) return 'group';
  if (/\bitem\b|\bsection\b/.test(cls)) return 'section';
  if (role === 'group' || role === 'region') return 'group';
  if (tag === 'header' || tag === 'footer' || tag === 'aside' || tag === 'main' || tag === 'section') {
    return 'section';
  }
  return 'group';
}

function hasMeaningfulContainerSignal(node: Element): boolean {
  const cls = (node.className || '').toLowerCase();
  const role = node.getAttribute('role');
  const tag = node.tagName.toLowerCase();

  if (role && role !== 'presentation' && role !== 'none') return true;
  if (tag === 'section' || tag === 'main' || tag === 'header' || tag === 'footer' || tag === 'aside') {
    return true;
  }
  if (
    /\b(item|section|content|wrapper|container|footer|header|body|card|panel|config|actions?|toolbar|dialog|alert|tip|status|sum)\b/.test(
      cls,
    )
  ) {
    return true;
  }

  return false;
}

function applyVisibilityState<T extends { cssState?: string; visible?: boolean }>(
  node: T,
  cssState: string | undefined,
): T {
  if (!cssState) return node;
  node.cssState = cssState;
  node.visible = false;
  return node;
}

function buildTextNode(
  text: string,
  parent: Element,
  index: number,
  hiddenCss?: string,
): StateNode {
  return applyVisibilityState({
    type: 'text',
    label: text,
    selector: `${buildSelector(parent)} ::text(${index})`,
  }, hiddenCss);
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

function buildTableCell(cell: Element, counter: Counter): TableCellNode {
  const selector = buildSelector(cell);
  const cssState = cell instanceof HTMLElement ? detectCssState(cell) : undefined;
  const directText = getDirectText(cell);
  const children = walkChildren(cell, 20, counter);

  const img = cell.querySelector<HTMLImageElement>('img[src]');
  if (img) {
    return applyVisibilityState({
      type: 'image',
      selector,
      src: img.getAttribute('src') || img.src || undefined,
      ...(cleanText(img.getAttribute('alt')) ? { text: cleanText(img.getAttribute('alt')) } : {}),
      ...(children.length > 0 ? { children } : {}),
      ...(captureLocalHtml(cell) ? { localHtml: captureLocalHtml(cell) } : {}),
    }, cssState);
  }

  const buttonNodes = children.filter((child) => child.type === 'button');
  if (buttonNodes.length > 1) {
    return applyVisibilityState({
      type: 'button-group',
      selector,
      actions: buttonNodes,
      children,
      ...(captureLocalHtml(cell) ? { localHtml: captureLocalHtml(cell) } : {}),
    }, cssState);
  }
  if (buttonNodes.length === 1 && children.length === 1) {
    return applyVisibilityState({
      type: 'button',
      selector,
      text: buttonNodes[0].label,
      actions: buttonNodes,
      children,
    }, cssState);
  }

  const controlNode = children.find((child) =>
    ['number', 'input', 'text', 'textarea', 'select', 'checkbox', 'radio', 'color', 'upload'].includes(child.type),
  );
  if (controlNode) {
    const nodeType = controlNode.type === 'number' ? 'input-number' : controlNode.type;
    return applyVisibilityState({
      type: nodeType,
      selector,
      ...(controlNode.value ? { value: controlNode.value } : {}),
      ...(controlNode.placeholder ? { placeholder: controlNode.placeholder } : {}),
      children,
      ...(captureLocalHtml(cell) ? { localHtml: captureLocalHtml(cell) } : {}),
    }, cssState);
  }

  if (children.length === 0 && !directText) {
    return applyVisibilityState({ type: 'empty', selector }, cssState);
  }

  if (children.length === 1 && children[0].type === 'text') {
    return applyVisibilityState({
      type: 'text',
      selector,
      text: children[0].label,
      children,
    }, cssState);
  }

  if (children.length === 0 && directText) {
    return applyVisibilityState({
      type: 'text',
      selector,
      text: directText,
    }, cssState);
  }

  return applyVisibilityState({
    type: 'custom',
    selector,
    ...(directText ? { text: directText } : {}),
    ...(children.length > 0 ? { children } : {}),
    ...(captureLocalHtml(cell) ? { localHtml: captureLocalHtml(cell) } : {}),
  }, cssState);
}

function buildFooterTips(tableEl: Element, counter: Counter): StateNode[] | undefined {
  const parent = tableEl.parentElement;
  if (!parent) return undefined;

  const footerTips: StateNode[] = [];
  let afterTable = false;

  for (const child of Array.from(parent.children)) {
    if (child === tableEl) {
      afterTable = true;
      continue;
    }
    if (!afterTable) continue;

    const cls = (child.className || '').toLowerCase();
    if (!/tip|hint|desc|description|help|alert|extra/.test(cls) && child.getAttribute('role') !== 'alert') {
      continue;
    }

    footerTips.push(...walkNode(child, 20, counter));
  }

  return footerTips.length > 0 ? footerTips : undefined;
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
    const allRows = Array.from(el.querySelectorAll('[role="row"]'));
    dataRows = headers.length > 0 ? allRows.slice(1) : allRows;
  }

  const rows: TableCellNode[][] = [];
  for (const tr of dataRows.slice(0, MAX_TABLE_ROWS)) {
    const cells = tr.querySelectorAll('td, [role="gridcell"], [role="cell"]');
    if (cells.length === 0) continue;
    rows.push(Array.from(cells).map((cell) => buildTableCell(cell, counter)));
  }

  // If table has complex content (images, buttons, inputs), preserve localHtml
  // so the full structure isn't lost in the text-only rows format.
  const hasComplexContent = el.querySelector(
    'img, button, [role="button"], input:not([type="hidden"]), select, [contenteditable="true"]',
  );
  let tableLocalHtml: string | undefined;
  if (hasComplexContent) {
    try {
      const clone = el.cloneNode(true) as Element;
      clone.querySelectorAll('script, style, svg, link, [aria-hidden="true"]').forEach((n) => n.remove());
      cleanHtmlTree(clone);
      const raw = clone.innerHTML?.trim();
      if (raw && raw.length >= 10) tableLocalHtml = raw;
    } catch { /* degrade gracefully */ }
  }

  const footerTips = buildFooterTips(el, counter);
  const cssState = el instanceof HTMLElement ? detectCssState(el) : undefined;
  counter.n++;
  return applyVisibilityState({
    type: 'table',
    selector: buildSelector(el),
    ...(headers.length > 0 ? { headers } : {}),
    ...(rows.length > 0 ? { rows, itemCount: dataRows.length } : {}),
    ...(footerTips ? { footerTips } : {}),
    ...(tableLocalHtml ? { localHtml: tableLocalHtml } : {}),
  }, cssState);
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
  // Use title attribute as fallback for icon-only buttons (e.g. move-up/down)
  const text = cleanText(el.textContent) || cleanText(el.getAttribute('title'));
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

/**
 * Build a list node from repeated sibling elements.
 * Expands the first few items fully via walkNode to preserve internal structure
 * (buttons, tables, nested content). Remaining items are summarized as titles.
 */
const MAX_EXPANDED_LIST_ITEMS = 3;

function buildListNode(items: Element[], counter: Counter): StateNode {
  const children: StateNode[] = [];

  // Expand first few items fully to preserve internal structure
  for (const item of items.slice(0, MAX_EXPANDED_LIST_ITEMS)) {
    if (counter.n >= MAX_NODES) break;
    const itemChildren = walkNode(item, 20, counter);
    if (itemChildren.length > 0) {
      // Wrap in a group if multiple nodes returned, otherwise use directly
      if (itemChildren.length === 1) {
        children.push(itemChildren[0]);
      } else {
        const title = extractItemTitle(item);
        counter.n++;
        children.push({
          type: 'group',
          ...(title ? { label: title } : {}),
          children: itemChildren,
        });
      }
    }
  }

  // Remaining items: preserve localHtml for future expansion
  if (items.length > MAX_EXPANDED_LIST_ITEMS) {
    const remaining = items.slice(MAX_EXPANDED_LIST_ITEMS);
    // Create a wrapper div with all remaining items, capture its HTML
    const wrapper = document.createElement('div');
    for (const item of remaining) {
      wrapper.appendChild(item.cloneNode(true));
    }
    wrapper.querySelectorAll('script, style, svg, link, [aria-hidden="true"]').forEach((n) => n.remove());
    cleanHtmlTree(wrapper);
    const html = wrapper.innerHTML?.trim();
    counter.n++;
    children.push({
      type: 'custom',
      label: `其他 ${remaining.length} 项`,
      ...(html ? { localHtml: html } : {}),
    });
  }

  counter.n++;
  return {
    type: 'list',
    selector: buildSelector(items[0]),
    itemCount: items.length,
    ...(children.length > 0 ? { children } : {}),
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

interface ControlValueResult {
  value?: string;
  type?: string;
  placeholder?: string;
  options?: { label: string; selected?: boolean }[];
}

function extractControlValue(el: Element): ControlValueResult {
  const tag = el.tagName.toLowerCase();
  if (tag === 'input') {
    const input = el as HTMLInputElement;
    const type = input.type || 'text';
    if (type === 'checkbox' || type === 'radio') {
      // For standalone radio/checkbox, also find sibling options in same name group
      const options = extractRadioCheckboxOptions(input);
      return {
        type,
        value: input.checked ? 'checked' : undefined,
        ...(options.length > 0 ? { options } : {}),
      };
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
    const options: { label: string; selected?: boolean }[] = [];
    for (const opt of select.options) {
      const label = cleanText(opt.text);
      if (label) options.push({ label, ...(opt.selected ? { selected: true } : {}) });
    }
    return {
      type: 'select',
      value: selected ? cleanText(selected.text || select.value) : undefined,
      ...(options.length > 0 ? { options } : {}),
    };
  }
  if (tag === 'textarea') {
    return { type: 'textarea', value: cleanText((el as HTMLTextAreaElement).value) };
  }
  if (el.hasAttribute('contenteditable')) {
    return { type: 'richtext', value: cleanText(el.textContent) };
  }

  // Component library control (e.g. el-input-number, ant-slider) — non-native element.
  // Try to extract value from inner input, aria attributes, or visible text.
  const cls = classifyElement(el);
  if (cls) {
    // Color picker: extract selected color from inner color-display element's background
    if (cls.type === 'color') {
      const colorInner = el.querySelector(
        '[class*="color-inner"], [class*="color__value"], [class*="color-block"]',
      ) as HTMLElement | null;
      const bgColor = colorInner?.style?.backgroundColor;
      return {
        type: 'color',
        ...(bgColor ? { value: bgColor } : {}),
      };
    }

    // Upload: extract file URLs from img/a elements inside the component
    if (cls.type === 'upload') {
      const urls: string[] = [];
      for (const img of el.querySelectorAll<HTMLImageElement>('img[src]')) {
        const src = img.src || img.getAttribute('src') || '';
        if (src && !src.startsWith('data:') && !src.includes('placeholder')) {
          urls.push(src);
        }
      }
      if (urls.length === 0) {
        for (const a of el.querySelectorAll<HTMLAnchorElement>('a[href]')) {
          const href = a.href;
          if (href && href !== '#' && !href.startsWith('javascript:')) {
            urls.push(href);
          }
        }
      }
      return {
        type: 'upload',
        ...(urls.length > 0 ? { value: urls.join(', ').slice(0, 500) } : {}),
      };
    }

    const innerInput = el.querySelector<HTMLInputElement>('input:not([type="hidden"])');
    const ariaValue = el.getAttribute('aria-valuenow') || innerInput?.getAttribute('aria-valuenow');
    const inputValue = innerInput?.value;
    const value = cleanText(ariaValue || inputValue);
    const placeholder = cleanText(
      innerInput?.getAttribute('placeholder') || el.getAttribute('placeholder'),
    );
    return {
      type: cls.type,
      ...(value ? { value } : {}),
      ...(placeholder ? { placeholder } : {}),
    };
  }

  return {};
}

/**
 * Extract options from a radio/checkbox group by finding siblings with same name.
 */
function extractRadioCheckboxOptions(input: HTMLInputElement): { label: string; selected?: boolean }[] {
  const name = input.getAttribute('name');
  if (!name) return [];
  const form = input.closest('form') || document.body;
  const siblings = form.querySelectorAll<HTMLInputElement>(
    `input[type="${input.type}"][name="${CSS.escape(name)}"]`,
  );
  const options: { label: string; selected?: boolean }[] = [];
  for (const sib of siblings) {
    // Find label text: <label> wrapper, adjacent text, or value attribute
    let label: string | undefined;
    const parentLabel = sib.closest('label');
    if (parentLabel) {
      const clone = parentLabel.cloneNode(true) as Element;
      clone.querySelectorAll('input').forEach((c) => c.remove());
      label = cleanText(clone.textContent);
    }
    if (!label) {
      // Check next sibling text
      const next = sib.nextSibling;
      if (next?.nodeType === Node.TEXT_NODE) label = cleanText(next.textContent);
    }
    if (!label) label = sib.value || undefined;
    if (label) {
      options.push({ label, ...(sib.checked ? { selected: true } : {}) });
    }
  }
  return options;
}

/* ── Options extraction for select/radio/checkbox ────────────────────────── */

/**
 * Extract available options from a form field's content area.
 * Handles native <select>/<input[radio|checkbox]> and component library patterns.
 */
function extractFieldOptions(
  contentArea: Element,
  fieldType: string,
): { label: string; selected?: boolean }[] {
  const options: { label: string; selected?: boolean }[] = [];
  const MAX_OPTIONS = 50;

  // 1. Native <select> options
  const select = contentArea.querySelector('select');
  if (select) {
    for (const opt of (select as HTMLSelectElement).options) {
      if (options.length >= MAX_OPTIONS) break;
      const label = cleanText(opt.text);
      if (label) options.push({ label, ...(opt.selected ? { selected: true } : {}) });
    }
    if (options.length > 0) return options;
  }

  // 2. Native radio/checkbox inputs
  const inputs = contentArea.querySelectorAll<HTMLInputElement>(
    'input[type="radio"], input[type="checkbox"]',
  );
  if (inputs.length > 0) {
    for (const input of inputs) {
      if (options.length >= MAX_OPTIONS) break;
      let label: string | undefined;
      // Label from wrapping <label>
      const parentLabel = input.closest('label');
      if (parentLabel) {
        const clone = parentLabel.cloneNode(true) as Element;
        clone.querySelectorAll('input').forEach((c) => c.remove());
        label = cleanText(clone.textContent);
      }
      // Label from adjacent text/span
      if (!label) {
        const next = input.nextElementSibling;
        if (next) label = cleanText(next.textContent);
      }
      if (!label) label = input.value || undefined;
      if (label) {
        options.push({ label, ...(input.checked ? { selected: true } : {}) });
      }
    }
    if (options.length > 0) return options;
  }

  // 3. Component library radio/checkbox items (el-radio, ant-radio, etc.)
  const componentItems = contentArea.querySelectorAll(
    '[class*="radio"], [class*="checkbox"], [role="radio"], [role="checkbox"]',
  );
  const seen = new Set<string>();
  for (const item of componentItems) {
    if (options.length >= MAX_OPTIONS) break;
    // Skip container elements (radio-group, checkbox-group)
    const cls = (item.className || '').toLowerCase();
    if (/group|wrapper|button-group/.test(cls)) continue;
    const label = cleanText(item.textContent);
    if (!label || label.length > 60 || seen.has(label)) continue;
    seen.add(label);
    const isSelected = cls.includes('is-checked') || cls.includes('is-active') ||
      cls.includes('checked') || item.getAttribute('aria-checked') === 'true';
    options.push({ label, ...(isSelected ? { selected: true } : {}) });
  }
  if (options.length > 0) return options;

  // 4. Component library select dropdown items (may be in a popup, not always accessible)
  // Try to find options within the component's DOM
  const selectItems = contentArea.querySelectorAll(
    '[class*="option"]:not([class*="group"]), [role="option"]',
  );
  for (const item of selectItems) {
    if (options.length >= MAX_OPTIONS) break;
    const label = cleanText(item.textContent);
    if (!label || label.length > 60 || seen.has(label)) continue;
    seen.add(label);
    const isSelected = (item.className || '').toLowerCase().includes('selected') ||
      item.getAttribute('aria-selected') === 'true';
    options.push({ label, ...(isSelected ? { selected: true } : {}) });
  }

  return options;
}

/* ── Leaf-level local HTML capture ────────────────────────────────────────── */

const MAX_LOCAL_HTML = 500;

/**
 * Capture a small HTML snippet from a content area for complex leaf nodes.
 * Strips scripts, styles, SVGs, hidden elements. Returns undefined if trivial.
 */
/**
 * Clean up a cloned DOM tree for localHtml storage:
 * 1. Strip inline styles, keeping only display/visibility (affect operability)
 * 2. Remove framework-generated noise attributes (Vue scoped, Dark Reader, etc.)
 * 3. Remove HTML comments
 */
const NOISE_ATTR_RE = /^(data-v-|data-darkreader|data-old-)/;
const KEEP_DATA_ATTRS = new Set(['data-id', 'data-prop', 'data-type', 'data-name', 'data-key']);

function cleanHtmlTree(root: Element): void {
  for (const el of root.querySelectorAll('*')) {
    // 1. Strip decorative inline styles, keep display/visibility
    if (el.hasAttribute('style')) {
      const style = (el as HTMLElement).style;
      const keep: string[] = [];
      if (style.display && style.display !== '') keep.push(`display:${style.display}`);
      if (style.visibility && style.visibility !== '') keep.push(`visibility:${style.visibility}`);
      if (keep.length > 0) {
        el.setAttribute('style', keep.join(';'));
      } else {
        el.removeAttribute('style');
      }
    }
    // 2. Remove framework noise attributes
    const toRemove: string[] = [];
    for (const attr of el.attributes) {
      if (NOISE_ATTR_RE.test(attr.name) && !KEEP_DATA_ATTRS.has(attr.name)) {
        toRemove.push(attr.name);
      }
    }
    for (const name of toRemove) el.removeAttribute(name);
  }
}

function captureLocalHtml(area: Element): string | undefined {
  const clone = area.cloneNode(true) as Element;
  clone.querySelectorAll(
    'script, style, svg, link, [aria-hidden="true"], [class*="icon"]',
  ).forEach((n) => n.remove());
  cleanHtmlTree(clone);
  const html = clone.innerHTML?.trim();
  if (!html || html.length < 10) return undefined;
  return html.slice(0, MAX_LOCAL_HTML);
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
    if (children.length === 0) return []; // backtrack to walkNode's generic path
    counter.n++;
    return [{
      type: 'group',
      ...(label ? { label } : {}),
      children,
    }];
  }

  // ── walkNode-first: try walking the content area through the unified pipeline ──
  // If walkNode produces meaningful results, use them (enriched with form metadata).
  // Otherwise, fall back to the existing specialized extraction below.
  // Note: walkChildren filters out self-closing elements (input/img), so we
  // explicitly find form controls and walk the content area together.
  const contentAreaForWalk = findContentArea(container);
  const walkedChildren: StateNode[] = [];
  // Walk the content area — walkNode handles transparent containers
  const contentWalkResult = walkNode(contentAreaForWalk, depth + 1, counter);
  walkedChildren.push(...contentWalkResult);
  // Also capture standalone inputs that walkChildren's pre-filter may have skipped
  // (self-closing elements like <input> have no children and no textContent).
  // Walk them explicitly through walkNode if not already captured.
  // Also capture standalone inputs that walkChildren's pre-filter may have skipped
  // (self-closing <input> has no children and no textContent).
  // Only capture top-level controls, NOT inputs deep inside compound components.
  if (walkedChildren.length <= 1) {
    const walkedSelectors = new Set(walkedChildren.map((c) => c.selector).filter(Boolean));
    const controls = contentAreaForWalk.querySelectorAll(
      'input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]), ' +
      'select, textarea, [contenteditable="true"]',
    );
    for (const ctrl of controls) {
      if (counter.n >= MAX_NODES) break;
      // Skip controls that are inside known compound components (el-select, etc.)
      if (isInsideCompound(ctrl as Element)) continue;
      const ctrlSel = buildSelector(ctrl as Element);
      if (walkedSelectors.has(ctrlSel)) continue;
      const ctrlNodes = walkNode(ctrl as Element, depth + 2, counter);
      walkedChildren.push(...ctrlNodes);
    }
  }
  if (walkedChildren.length > 0) {
    const required = detectRequired(container);
    const prop = extractProp(container);
    const hint = extractHintOrError(container);

    if (walkedChildren.length === 1 && !walkedChildren[0].children) {
      // Single leaf control — merge form metadata into it
      const child = walkedChildren[0];
      if (label) child.label = label; // form-item label is authoritative
      if (!child.required && required) child.required = true;
      if (prop && !child.fieldProp) child.fieldProp = prop;
      if (hint) {
        child.hint = hint;
        child.helpText = hint;
        child.tips = [hint];
      }
      // Extract options if applicable
      const OPTION_TYPES = new Set(['select', 'radio', 'checkbox', 'cascader']);
      if (OPTION_TYPES.has(child.type) && !child.options) {
        const opts = extractFieldOptions(contentAreaForWalk, child.type);
        if (opts.length > 0) child.options = opts;
      }
      return [child];
    }

    // Multiple children — wrap in group with form metadata
    counter.n++;
    return [{
      type: 'group',
      selector: sel,
      ...(label ? { label } : {}),
      ...(required ? { required: true } : {}),
      ...(prop ? { fieldProp: prop } : {}),
      ...(hint ? { hint, helpText: hint, tips: [hint] } : {}),
      children: walkedChildren,
    }];
  }

  // ── Fallback: walkNode produced nothing — use existing specialized extraction ──
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

  // Complex content detection: if the content area contains multiple actionable
  // elements or nested structures, expand via walkChildren instead of collapsing
  // into a single leaf node. This prevents loss of internal structure.
  const SIMPLE_FIELD_TYPES = new Set([
    'input', 'number', 'textarea', 'select', 'checkbox', 'radio', 'switch',
    'slider', 'rate', 'date', 'time', 'color', 'upload', 'cascader',
    'autocomplete', 'transfer',
  ]);
  {
    const contentArea = findContentArea(container);
    // Count distinct VISIBLE actionable elements (exclude elements inside
    // display:none ancestors like hidden dropdown panels / popup menus).
    // Hidden popup buttons should not trigger complex field expansion.
    const isInsideHidden = (el: Element): boolean => {
      let cur = el.parentElement;
      while (cur && cur !== contentArea) {
        if ((cur as HTMLElement).style?.display === 'none') return true;
        cur = cur.parentElement;
      }
      return false;
    };
    const countVisible = (selector: string): number => {
      let count = 0;
      for (const el of contentArea.querySelectorAll(selector)) {
        if (!isInsideHidden(el)) count++;
      }
      return count;
    };
    const radios = countVisible('input[type="radio"]');
    const checkboxes = countVisible('input[type="checkbox"]');
    const otherActionables = countVisible(
      'input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]), ' +
      'select, textarea, button, [role="button"], ' +
      'table, [contenteditable="true"], a[href]',
    );
    // Treat all radios as 1 control, all checkboxes as 1 control
    const actionableCount = otherActionables + (radios > 0 ? 1 : 0) + (checkboxes > 0 ? 1 : 0);
    // Even "simple" field types should expand if there are many sibling controls
    // (e.g. a form-item containing 3 inputs + 1 select = address block)
    const threshold = SIMPLE_FIELD_TYPES.has(fieldType) ? 3 : 2;
    if (actionableCount >= threshold) {
      const children = walkChildren(container, depth, counter);
      if (children.length > 0) {
        counter.n++;
        return [{
          type: 'group',
          ...(label ? { label } : {}),
          ...(detectRequired(container) ? { required: true } : {}),
          ...(extractProp(container) ? { fieldProp: extractProp(container) } : {}),
          children,
        }];
      }
      return []; // backtrack
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

  // Fallback: read readonly input value (common in pseudo-selects / date pickers)
  if (!value) {
    const content = findContentArea(container);
    const readonlyInputs = content.querySelectorAll<HTMLInputElement>('input[readonly], input[disabled]');
    const vals: string[] = [];
    for (const inp of readonlyInputs) {
      const v = inp.value?.trim();
      const ph = inp.getAttribute('placeholder')?.trim();
      if (v && v !== ph && v.length <= 100) vals.push(v);
    }
    if (vals.length === 1) {
      value = vals[0];
    } else if (vals.length >= 2) {
      // Date range pattern: two readonly inputs
      value = vals.slice(0, 2).join(' ~ ');
    }
  }

  // Fallback: read visible text from display-only spans/divs (custom components)
  if (!value) {
    const content = findContentArea(container);
    // Look for display text in common patterns: *-selection, *-content, *-value, *-text
    const displayEl = Array.from(content.querySelectorAll('*')).find((el) => {
      const names = getComponentNames(el);
      return names.some((n) =>
        /^(selection-item|selected-item|selection-label|input-content|suffix|value-text)$/.test(n),
      );
    });
    if (displayEl?.textContent?.trim()) {
      const text = displayEl.textContent.trim();
      const cls = (displayEl.className || '').toLowerCase();
      if (!cls.includes('placeholder') && !cls.includes('transparent') && text.length <= 150) {
        value = text;
      }
    }
  }

  // Fallback: for types that normally show text, read non-label visible content
  if (!value && !placeholder && !['input', 'textarea', 'number'].includes(fieldType)) {
    const content = findContentArea(container);
    const clone = content.cloneNode(true) as Element;
    // Remove label elements, icons, hidden elements
    clone.querySelectorAll(
      'label, legend, [class*="label"], svg, [class*="icon"], [aria-hidden="true"], ' +
      'script, style, button, [role="button"]',
    ).forEach((x) => x.remove());
    const visibleText = cleanText(clone.textContent);
    if (visibleText && visibleText.length >= 1 && visibleText.length <= 120) {
      value = visibleText;
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

  // Color picker: extract selected color from background-color style
  if (fieldType === 'color' && !value) {
    const content = findContentArea(container);
    const colorInner = content.querySelector('[class*="color-inner"], [class*="color__value"], [class*="color-block"]') as HTMLElement | null;
    if (colorInner?.style.backgroundColor) {
      value = colorInner.style.backgroundColor;
    }
  }

  // Extract prop
  const prop = extractProp(container);

  // Leaf-level local HTML: for richtext or complex nodes where value alone is insufficient
  let localHtml: string | undefined;
  if (defaultValueHtml) {
    localHtml = defaultValueHtml;
  } else if (!value && fieldType !== 'input' && fieldType !== 'textarea' && fieldType !== 'number') {
    const contentArea = findContentArea(container);
    localHtml = captureLocalHtml(contentArea);
  }

  // Extract embedded action buttons inside this form-item (e.g. "城市管理", "选择")
  const embeddedButtons: string[] = [];
  const contentArea2 = findContentArea(container);
  for (const btn of contentArea2.querySelectorAll('button, [role="button"]')) {
    const btnText = cleanText(btn.textContent);
    if (btnText && btnText.length <= 20 && btnText.length >= 1) {
      const btnCls = (btn.className || '').toLowerCase();
      if (!/close|icon-only/.test(btnCls)) {
        embeddedButtons.push(btnText);
      }
    }
  }

  // Extract options for select/radio/checkbox fields
  const OPTION_TYPES = new Set(['select', 'radio', 'checkbox', 'cascader']);
  let options: { label: string; selected?: boolean }[] | undefined;
  if (OPTION_TYPES.has(fieldType)) {
    options = extractFieldOptions(findContentArea(container), fieldType);
  }

  // Backtrack: if no label and no value — this form-item container has no
  // meaningful form content. Return [] so walkNode falls back to generic
  // walkChildren (e.g. el-form-item__actions that only has buttons).
  if (!label && !value && !placeholder) {
    return []; // backtrack
  }

  counter.n++;
  const node: StateNode = {
    type: fieldType,
    selector: sel,
    ...(label ? { label } : {}),
    ...(value ? { value } : {}),
    ...(placeholder ? { placeholder } : {}),
    ...(options && options.length > 0 ? { options } : {}),
    ...(detectRequired(container) ? { required: true } : {}),
    ...(prop ? { fieldProp: prop } : {}),
    ...(detected.itemCount ? { itemCount: detected.itemCount } : {}),
  };
  if (localHtml) node.localHtml = localHtml;
  if (embeddedButtons.length > 0) node.actions = embeddedButtons;

  // Extract hint/tip/description text from the form-item container
  const hint = extractHintOrError(container);
  if (hint) {
    node.hint = hint;
    node.helpText = hint;
    node.tips = [hint];
  }

  return [node];
}

function extractProp(container: Element): string | undefined {
  // 1. Check container-level prop attribute (Element UI/Plus, Ant Design)
  const containerProp = container.getAttribute('prop') || container.getAttribute('data-prop');
  if (containerProp) return containerProp;

  // 2. Check inner control attributes
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
  const results: StateNode[] = [];
  const hiddenCss = parent instanceof HTMLElement ? detectCssState(parent) : undefined;

  let textIndex = 0;
  for (const childNode of Array.from(parent.childNodes)) {
    if (counter.n >= MAX_NODES) break;

    if (childNode.nodeType === Node.TEXT_NODE) {
      const text = cleanTextNodeValue(childNode);
      if (!text) continue;
      counter.n++;
      results.push(buildTextNode(text, parent, textIndex++, hiddenCss));
      continue;
    }

    if (childNode.nodeType !== Node.ELEMENT_NODE) continue;
    const child = childNode as Element;
    if (shouldSkip(child)) continue;
    if (!child.children.length && !child.textContent?.trim()) continue;
    results.push(...walkNode(child, depth + 1, counter));
  }

  return results;
}

/* ── Unified node classification ────────────────────────────────────────── */

type NodeClassification =
  | 'iframe' | 'form-item' | 'table' | 'dialog'
  | 'standalone-control' | 'button' | 'card' | 'link'
  | null; // null = no specific classification, treat as generic container

/**
 * Classify a DOM node into a semantic type. Priority order:
 *   1. Cross-document: iframe
 *   2. Known component library: via classifyElement() (e.g. el-select → 'table', 'dialog')
 *   3. Form container: via isFormContainer() (e.g. el-form-item, ant-form-item)
 *   4. Standard HTML: native <input>, <select>, <textarea>, <table>, <button>, <a>
 *   5. Class/id/tag identifiable: card, panel patterns
 *   6. null → generic container, walk children
 */
function classifyNode(node: Element): NodeClassification {
  const tag = node.tagName.toLowerCase();

  // 1. Iframe — cross-document boundary
  if (tag === 'iframe') return 'iframe';

  // 2. Known component library via classifier
  const cls = classifyElement(node);
  if (cls) {
    if (cls.type === 'table') return 'table';
    if (cls.type === 'dialog') return 'dialog';
    // Known control types (input, number, select, etc.) detected by component
    // classifier on non-native elements (e.g. el-input-number is a <div>).
    // Treat as standalone control so processStandaloneControl can extract value.
    const CONTROL_TYPES = new Set([
      'input', 'number', 'textarea', 'select', 'checkbox', 'radio', 'switch',
      'slider', 'rate', 'date', 'time', 'color', 'cascader', 'autocomplete',
      'upload', 'transfer',
    ]);
    if (CONTROL_TYPES.has(cls.type)) return 'standalone-control';
  }

  // 3. Form container (el-form-item, ant-form-item, fieldset, etc.)
  if (isFormContainer(node)) return 'form-item';

  // 4. Standard HTML native elements
  if (tag === 'table') return 'table';
  if (isStandaloneControl(node)) return 'standalone-control';
  if (isActionButton(node)) return 'button';
  if (tag === 'a' && node.hasAttribute('href')) return 'link';

  // 5. Class/id identifiable patterns
  const nodeCls = (node.className || '').toLowerCase();
  if (
    /(?:^|[\s_-])(?:card|panel)(?:$|[\s_-])/.test(nodeCls) &&
    !/(card-body|panel-body|card-content|task-card)/.test(nodeCls)
  ) {
    return 'card';
  }

  return null; // generic container
}

/* ── Specialized processors ─────────────────────────────────────────────── */

function processIframe(node: Element, depth: number, counter: Counter): StateNode[] {
  const buildIframeNode = (contentRoot: Element): StateNode[] => {
    const children = walkChildren(contentRoot, depth + 1, counter);
    if (children.length === 0) return [];
    counter.n++;
    const label =
      cleanText(
        node.getAttribute('title') ||
        node.getAttribute('aria-label') ||
        node.getAttribute('data-title'),
      ) || 'Iframe';
    return [{ type: 'section', label, blockType: 'iframe-content', children }];
  };

  try {
    const iframe = node as HTMLIFrameElement;
    const iframeDoc = iframe.contentDocument;
    if (iframeDoc?.body) {
      const docResult = buildIframeNode(iframeDoc.body);
      if (docResult.length > 0) return docResult;
    }
  } catch {
    // Cross-origin iframe — skip silently
  }

  // Offline HTML snapshots may inline iframe content directly as child nodes
  // instead of providing a live contentDocument. Preserve and parse that DOM too.
  const inlineBody = node.querySelector(':scope > body');
  if (inlineBody) {
    const inlineResult = buildIframeNode(inlineBody);
    if (inlineResult.length > 0) return inlineResult;
  }

  const inlineRoot = node.firstElementChild;
  if (inlineRoot) {
    const inlineResult = buildIframeNode(inlineRoot);
    if (inlineResult.length > 0) return inlineResult;
  }

  const inlineHtml = node.innerHTML?.trim();
  if (inlineHtml && /<\w+/i.test(inlineHtml)) {
    try {
      const parsed = new DOMParser().parseFromString(inlineHtml, 'text/html');
      if (parsed.body) {
        const parsedResult = buildIframeNode(parsed.body);
        if (parsedResult.length > 0) return parsedResult;
      }
    } catch {
      // Ignore malformed offline iframe HTML and fall through
    }
  }

  return [];
}

function processDialog(node: Element, depth: number, counter: Counter): StateNode[] {
  const children = walkChildren(node, depth, counter);
  if (children.length === 0) return [];
  counter.n++;
  return [{
    type: 'section',
    label: cleanText(node.getAttribute('aria-label') || node.getAttribute('title')) || 'Dialog',
    blockType: 'dialog',
    children,
  }];
}

function processStandaloneControl(node: Element, counter: Counter): StateNode[] {
  const label = extractControlLabel(node);
  const { value, type, placeholder, options } = extractControlValue(node);
  // Don't backtrack for classified component types — they ARE controls even
  // without extractable label/value (prevents walking into internal structure
  // like hidden popups in color pickers).
  const isClassified = !!classifyElement(node);
  if (!isClassified && !label && !value && !placeholder) return []; // backtrack
  counter.n++;
  return [{
    type: type || 'input',
    selector: buildSelector(node),
    ...(label ? { label } : {}),
    ...(value ? { value } : {}),
    ...(placeholder ? { placeholder } : {}),
    ...(options && options.length > 0 ? { options } : {}),
    ...(node.hasAttribute('required') || node.getAttribute('aria-required') === 'true'
      ? { required: true } : {}),
  }];
}

function processButton(node: Element, counter: Counter): StateNode[] {
  // Use title attribute as fallback for icon-only buttons (e.g. move-up/down)
  const text = cleanText(node.textContent) || cleanText(node.getAttribute('title'));
  if (!text) return []; // backtrack
  counter.n++;
  return [{ type: 'button', selector: buildSelector(node), label: text }];
}

function processLink(node: Element, counter: Counter): StateNode[] {
  const text = cleanText(node.textContent);
  if (!text || text.length > 80) return []; // backtrack
  const href = node.getAttribute('href');
  counter.n++;
  return [{
    type: 'link',
    label: text,
    selector: buildSelector(node),
    ...(href && href !== '#' && href !== 'javascript:void(0)' ? { href } : {}),
  }];
}

function processCard(node: Element, depth: number, counter: Counter): StateNode[] {
  const children = walkChildren(node, depth, counter);
  if (children.length === 0) return []; // backtrack
  const titleEl = node.querySelector(':scope > [class*="header"] [class*="title"], :scope > [class*="head"] [class*="title"]');
  const cardTitle = titleEl ? cleanText(titleEl.textContent) : undefined;
  const cssState = node instanceof HTMLElement ? detectCssState(node) : undefined;
  counter.n++;
  return [applyVisibilityState({
    type: inferPreservedContainerType(node),
    selector: buildSelector(node),
    ...(cardTitle ? { label: cardTitle } : {}),
    ...(inferBlockType(children, node) ? { blockType: inferBlockType(children, node) } : {}),
    children,
    ...(captureLocalHtml(node) ? { localHtml: captureLocalHtml(node) } : {}),
  }, cssState)];
}

/* ── Main walk logic: classify → try → backtrack → fallback ─────────────── */

/**
 * Check if an element has enough visible content to warrant a localHtml fallback.
 */
function hasVisibleContent(el: Element): boolean {
  const text = el.textContent?.trim();
  if (text && text.length >= 2) return true;
  if (el.querySelector('img, video, canvas, [contenteditable]')) return true;
  return false;
}

function shouldPreserveContainerBoundary(node: Element, children: StateNode[], cssState?: string): boolean {
  if (cssState) return true;
  if (children.length === 0) return false;
  if (children.length > 1) {
    return hasMeaningfulContainerSignal(node) || !!getDirectText(node);
  }
  if (getDirectText(node)) return true;
  if (hasMeaningfulContainerSignal(node)) return true;
  if (node instanceof HTMLElement && node.dataset && Object.keys(node.dataset).length > 0) return true;
  return false;
}

/**
 * Process a single DOM node using unified classify → try → backtrack → fallback.
 *
 * 1. classifyNode(el) → determine semantic type
 * 2. tryProcess with specialized processor
 * 3. If processor returns [] → BACKTRACK to generic walkChildren
 * 4. If walkChildren also empty + element has visible content → localHtml fallback
 */
function walkNode(
  node: Element,
  depth: number,
  counter: Counter,
): StateNode[] {
  if (counter.n >= MAX_NODES || depth > MAX_DEPTH) return [];

  const classification = classifyNode(node);

  // ── Step 1: Try specialized processor ──
  let result: StateNode[] | undefined;

  switch (classification) {
    case 'iframe':
      // Iframe has no meaningful backtrack — cross-document boundary
      return processIframe(node, depth, counter);

    case 'form-item':
      result = processFormItem(node, depth, counter);
      break;

    case 'table':
      result = [buildTableNode(node, counter)];
      break;

    case 'dialog':
      result = processDialog(node, depth, counter);
      break;

    case 'standalone-control':
      result = processStandaloneControl(node, counter);
      break;

    case 'button':
      result = processButton(node, counter);
      break;

    case 'link':
      result = processLink(node, counter);
      break;

    case 'card':
      result = processCard(node, depth, counter);
      break;
  }

  // If specialized processor succeeded → return (with cssState if hidden)
  if (result && result.length > 0) {
    if (node instanceof HTMLElement) {
      const css = detectCssState(node);
      if (css) {
        for (const r of result) applyVisibilityState(r, css);
      }
    }
    return result;
  }

  // ── Step 2: Backtrack — generic recursive walk ──
  const children = walkChildren(node, depth, counter);
  const cssState = node instanceof HTMLElement ? detectCssState(node) : undefined;
  const label = getContainerLabel(node);
  const directText = getDirectText(node);

  if (children.length > 0 && shouldPreserveContainerBoundary(node, children, cssState)) {
    counter.n++;
    const blockType = inferBlockType(children, node);
    const containerNode: StateNode = {
      type: inferPreservedContainerType(node),
      selector: buildSelector(node),
      ...(label ? { label } : {}),
      ...(blockType ? { blockType } : {}),
      ...(captureLocalHtml(node) ? { localHtml: captureLocalHtml(node) } : {}),
      children,
    };

    if (directText) {
      if (containerNode.type === 'status-block') {
        containerNode.statusText = directText;
      } else if (containerNode.type === 'alert') {
        containerNode.description = directText;
        containerNode.tips = [directText];
      }
    }

    return [applyVisibilityState(containerNode, cssState)];
  }

  if (children.length > 0) {
    if (cssState) {
      for (const child of children) applyVisibilityState(child, cssState);
    }
    return children;
  }

  // ── Step 3: localHtml fallback for non-empty visible elements ──
  // Per CLAUDE.md: walkChildren returns empty + visible content → localHtml fallback.
  // No classification guard — ANY element with extractable content gets a fallback.
  if (hasVisibleContent(node)) {
    const snippet = captureLocalHtml(node);
    if (snippet) {
      counter.n++;
      return [applyVisibilityState({
        type: 'custom',
        selector: buildSelector(node),
        ...(label ? { label } : {}),
        localHtml: snippet,
      }, cssState)];
    }
    // captureLocalHtml returned undefined (short/trivial HTML) but element has
    // visible text content — create a lightweight label-only custom node.
    const text = cleanText(node.textContent);
    if (text && text.length >= 2) {
      counter.n++;
      return [applyVisibilityState({
        type: 'custom',
        selector: buildSelector(node),
        label: text.slice(0, 200),
      }, cssState)];
    }
  }

  return [];
}

/* ── Page-level info extraction ──────────────────────────────────────────── */

/**
 * Extract the main visible heading from the page content area.
 * Tries: h1 > h2 > page-header title > card header > prominent heading element.
 */
function extractPageHeading(root: Element): string | undefined {
  // 1. Look for h1/h2 directly in the main content
  for (const sel of ['h1', 'h2', '[class*="page-header"] [class*="title"]', '[class*="page-title"]']) {
    const el = root.querySelector(sel);
    if (el) {
      const text = cleanText(el.textContent);
      if (text && text.length <= 80 && text.length >= 2) return text;
    }
  }

  // 2. ARIA heading
  const ariaHeading = root.querySelector('[role="heading"]');
  if (ariaHeading) {
    const text = cleanText(ariaHeading.textContent);
    if (text && text.length <= 80 && text.length >= 2) return text;
  }

  return undefined;
}

/**
 * Extract primary CTA buttons visible on the page (save, submit, cancel, etc.).
 * Scans top-level button areas and footer/toolbar regions.
 */
const CTA_KEYWORDS_RE =
  /保存|提交|确认|确定|发布|创建|新增|取消|返回|下一步|上一步|编辑|删除|导入|导出|上传|save|submit|confirm|cancel|publish|create|next|back|edit|delete|import|export|upload/i;

function extractPrimaryActions(root: Element): string[] | undefined {
  const actions: string[] = [];
  const seen = new Set<string>();

  // Scan visible buttons in the content area
  const buttons = root.querySelectorAll('button, [role="button"], a[class*="btn"], a[class*="button"]');
  for (const btn of buttons) {
    if (!(btn instanceof HTMLElement) || !isVisible(btn)) continue;
    // Skip small icon-only buttons
    const text = cleanText(btn.textContent);
    if (!text || text.length > 20 || text.length < 1) continue;
    const cls = (btn.className || '').toLowerCase();
    if (/close|icon-only|collapse|dropdown/.test(cls)) continue;

    if (CTA_KEYWORDS_RE.test(text) && !seen.has(text)) {
      seen.add(text);
      actions.push(text);
      if (actions.length >= 6) break;
    }
  }

  return actions.length > 0 ? actions : undefined;
}

/* ── Block type inference ──────────────────────────────────────────────────── */

/**
 * Infer a semantic block type for a section/group node based on its children.
 * Used to add blockType to structural nodes.
 */
function inferBlockType(children: StateNode[], el?: Element): string | undefined {
  if (!children || children.length === 0) return undefined;

  // Check if the element itself has clues
  if (el) {
    const cls = (el.className || '').toLowerCase();
    const role = el.getAttribute('role');

    if (role === 'dialog' || /dialog|modal|drawer/.test(cls)) return 'dialog';
    if (role === 'toolbar' || /toolbar|action-bar|btn-group|button-group|footer-action/.test(cls)) return 'toolbar';
    if (/card|panel/.test(cls) && !/card-body|panel-body/.test(cls)) return 'card-block';
  }

  // Classify by children content
  const types = children.map((c) => c.type);
  const hasFormFields = types.some((t) =>
    ['input', 'select', 'checkbox', 'radio', 'textarea', 'richtext',
     'date', 'time', 'number', 'switch', 'slider', 'rate', 'upload',
     'cascader', 'autocomplete', 'color', 'transfer', 'custom'].includes(t),
  );
  const hasTable = types.includes('table');
  const hasList = types.includes('list');
  const hasButtons = types.filter((t) => t === 'button').length >= 2;
  const hasRichtext = types.includes('richtext');

  if (hasButtons && !hasFormFields && !hasTable) return 'toolbar';
  if (hasRichtext && types.length <= 3) return 'richtext-block';
  if (hasFormFields) return 'form-section';
  if (hasTable) return 'content-block';
  if (hasList) return 'list-block';

  return 'content-block';
}

/* ── Navigation scanning ─────────────────────────────────────────────────── */

const ACTIVE_SELECTORS = '.active, .is-active, .router-link-active, .router-link-exact-active, [aria-current="page"], [aria-current="true"], [aria-selected="true"]';
const ACTIVE_CLASS_RE = /(?:^|[\s_-])(?:active|selected|current|is-active)(?:$|[\s_-])/;

function isActiveItem(el: Element): boolean {
  try { if (el.matches(ACTIVE_SELECTORS)) return true; } catch { /* ignore */ }
  return ACTIVE_CLASS_RE.test((el.className || '').toLowerCase());
}

/* (MAX_NAV_ITEMS/MAX_NAV_DEPTH removed — nav areas now use localHtml, not detailed extraction) */

/**
 * Detect key CSS visibility state of an element or its ancestors.
 * Returns a string like 'display:none' or 'visibility:hidden', or undefined if visible.
 */
function detectCssState(el: HTMLElement): string | undefined {
  let current: HTMLElement | null = el;
  while (current && current !== document.body) {
    const style = current.style;
    if (style.display === 'none') return 'display:none';
    if (style.visibility === 'hidden') return 'visibility:hidden';
    // Check computed style for class-driven hiding
    try {
      const computed = window.getComputedStyle(current);
      if (computed.display === 'none') return 'display:none';
      if (computed.visibility === 'hidden') return 'visibility:hidden';
    } catch {
      // getComputedStyle may fail in some contexts
    }
    current = current.parentElement as HTMLElement | null;
  }
  return undefined;
}

/**
 * Infer a navigation area label from element attributes or tag.
 */
function getNavLabel(el: Element): string {
  const ariaLabel = cleanText(el.getAttribute('aria-label'));
  if (ariaLabel) return ariaLabel;

  const tag = el.tagName.toLowerCase();
  const cls = (el.className || '').toLowerCase();

  // Check for common patterns
  if (/sidebar|side-bar|sider/.test(cls)) return 'Sidebar';
  if (/top-?bar|header-?nav|head-?bar/.test(cls)) return 'Header';
  if (tag === 'header') return 'Header';
  if (tag === 'footer') return 'Footer';
  if (tag === 'aside') return 'Sidebar';
  if (tag === 'nav') {
    // Try to infer from position or class
    if (/breadcrumb/.test(cls)) return 'Breadcrumb';
    return 'Navigation';
  }

  return 'Navigation';
}

/**
 * Scan navigation areas (header, nav, aside, footer) outside the main content root.
 * Returns lightweight section nodes with blockType 'navigation'.
 */
function scanNavigation(mainRoot: Element, counter: Counter): StateNode[] {
  const navNodes: StateNode[] = [];
  const processed = new Set<Element>();

  // Collect candidate nav elements from body level
  const candidates = document.body.querySelectorAll('nav, aside, header, footer, [role="navigation"], [role="banner"], [role="complementary"], [role="contentinfo"]');

  for (const el of candidates) {
    if (counter.n >= MAX_NODES) break;
    if (!(el instanceof HTMLElement)) continue;
    // Skip if inside the main content root (those are handled by walkChildren)
    if (mainRoot.contains(el) && el !== mainRoot) continue;
    // Skip if already processed (ancestor was already captured)
    if (processed.has(el)) continue;
    // Skip if a parent nav is already in our list
    let parentProcessed = false;
    for (const p of processed) {
      if (p.contains(el)) { parentProcessed = true; break; }
    }
    if (parentProcessed) continue;

    // Navigation areas are stored as lightweight summary + localHtml.
    // Full nav structure is preserved as raw HTML for future expansion,
    // but NOT expanded into detailed link/button children — keeps the
    // Agent's analysis focused on actual page content.
    const label = getNavLabel(el);
    // No size limit — style/attribute cleanup already reduces size significantly
    let html: string | undefined;
    try {
      const clone = el.cloneNode(true) as Element;
      clone.querySelectorAll('script, style, svg, link, [aria-hidden="true"]').forEach((n) => n.remove());
      cleanHtmlTree(clone);
      const raw = clone.innerHTML?.trim();
      if (raw && raw.length >= 10) html = raw;
    } catch { /* degrade gracefully */ }
    if (!html && !el.textContent?.trim()) continue;

    // Extract just the active/current item as quick reference
    const activeEl = el.querySelector(ACTIVE_SELECTORS) as HTMLElement | null;
    const activeLabel = activeEl ? cleanText(activeEl.textContent) : undefined;

    processed.add(el);
    counter.n++;
    navNodes.push({
      type: 'section',
      label,
      blockType: 'navigation',
      ...(activeLabel ? { summaryText: `当前: ${activeLabel}` } : {}),
      ...(html ? { localHtml: html } : {}),
    });
  }

  return navNodes;
}

/* ── Entry point ─────────────────────────────────────────────────────────── */

export function captureInitialState(): PageInitialState {
  const counter: Counter = { n: 0 };

  const root =
    document.querySelector(
      'main, [role="main"], .main-content, .app-main, .el-main, .ant-layout-content',
    ) || document.body;

  // Scan navigation areas outside main content
  const navNodes = root !== document.body ? scanNavigation(root, counter) : [];

  const stateTree = [...navNodes, ...walkChildren(root, 0, counter)];

  // Assign blockType to top-level section/group nodes
  for (const node of stateTree) {
    if ((node.type === 'section' || node.type === 'group') && node.children && !node.blockType) {
      node.blockType = inferBlockType(node.children);
    }
  }

  // Raw HTML snapshot — debug/fallback layer only (not used in primary analysis)
  let rawHtmlSnapshot: string | undefined;
  try {
    rawHtmlSnapshot = captureSimplifiedHTML();
  } catch {
    // degrade gracefully
  }

  const pageHeading = extractPageHeading(root);
  const primaryActions = extractPrimaryActions(root);

  return {
    capturedAt: Date.now(),
    pageUrl: getCanonicalPageUrl(location.href),
    pageTitle: document.title,
    ...(pageHeading ? { pageHeading } : {}),
    ...(primaryActions ? { primaryActions } : {}),
    stateTree,
    ...(rawHtmlSnapshot ? { rawHtmlSnapshot } : {}),
  };
}
