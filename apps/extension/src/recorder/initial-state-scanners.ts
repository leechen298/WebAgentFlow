/**
 * Initial State Scanners — all scanner functions for capturing page state.
 *
 * Scanners:
 *   - scanContainers()       — form-item containers (any UI library)
 *   - scanGenericControls()  — standalone native form controls
 *   - scanStructuredTables() — data tables
 *   - scanStructuredLists()  — repeated item lists
 *   - scanPaginationControls() — pagination components
 *   - scanActiveTabs()       — active tab in tab panels
 *   - scanActiveSteps()      — current step in step wizards
 *   - scanBreadcrumbs()      — breadcrumb navigation paths
 *   - scanDescriptions()     — description list key-value pairs
 *   - scanOpenDialogs()      — currently open dialogs/modals
 */

import type { InitialFieldSnapshot } from '@web-agent-flow/shared-types';
import {
  isFormContainer,
  isNavigationChrome,
  findFormContainer,
  classifyElement,
} from './component-classifier';
import {
  cleanLabel,
  normalizeText,
  buildFieldPath,
  isVisible,
  extractHeadingText,
  findSectionLabel,
  summarizeElementText,
  extractItemTitle,
} from './dom-utils';
import {
  extractUniversalLabel,
  detectRequired,
  detectFieldType,
  findContentArea,
} from './label-extractor';

// ─── Constants ──────────────────────────────────────────────────────────────

const MAX_TABLE_ROWS = 5;
const MAX_STANDALONE_TABLE_ROWS = 10;
const MAX_LIST_ITEMS = 5;

const GENERIC_INPUT_SELECTOR =
  'input:not([type="hidden"]):not([type="button"]):not([type="submit"])' +
  ':not([type="reset"]):not([type="image"])';

const ALL_CONTROLS_SELECTOR = [
  GENERIC_INPUT_SELECTOR,
  'select',
  'textarea',
  '[contenteditable="true"]',
].join(', ');

// ─── Pagination detection ───────────────────────────────────────────────────

function isPaginationElement(el: Element): boolean {
  const cls = (el.getAttribute('class') || '').toLowerCase();
  const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();

  if (cls.includes('pagination') || ariaLabel.includes('pagination')) return true;

  const numEls = Array.from(el.querySelectorAll('li, a, button')).filter((c) =>
    /^\d+$/.test(c.textContent?.trim() ?? ''),
  );
  if (numEls.length >= 3) {
    const hasPrevNext = Boolean(
      el.querySelector(
        '[class*="prev"], [class*="next"], ' +
          '[aria-label*="prev" i], [aria-label*="next" i], ' +
          '[aria-label*="上一"], [aria-label*="下一"]',
      ),
    );
    if (hasPrevNext) return true;
  }

  return false;
}

function isPaginationContext(element: Element): boolean {
  let el: Element | null = element;
  for (let depth = 0; depth < 8 && el; depth++) {
    if (isPaginationElement(el)) return true;
    el = el.parentElement;
  }
  return false;
}

// ─── Generic label for standalone controls ──────────────────────────────────

function findGenericLabel(el: HTMLElement): string | undefined {
  if (el.id) {
    try {
      const label = document.querySelector<HTMLLabelElement>(
        `label[for="${CSS.escape(el.id)}"]`,
      );
      if (label?.textContent?.trim()) {
        return cleanLabel(label.textContent).slice(0, 80);
      }
    } catch { /* CSS.escape may throw */ }
  }

  const labelledBy = el.getAttribute('aria-labelledby');
  if (labelledBy) {
    const ids = labelledBy.split(/\s+/);
    const texts = ids
      .map((id) => document.getElementById(id)?.textContent?.trim())
      .filter(Boolean);
    if (texts.length > 0) return cleanLabel(texts.join(' ')).slice(0, 80);
  }

  const ariaLabel = el.getAttribute('aria-label');
  if (ariaLabel?.trim()) return ariaLabel.trim().slice(0, 80);

  const parentLabel = el.closest('label');
  if (parentLabel) {
    const clone = parentLabel.cloneNode(true) as Element;
    clone.querySelectorAll('input, select, textarea, [contenteditable]').forEach((c) => c.remove());
    const text = clone.textContent?.trim();
    if (text) return cleanLabel(text).slice(0, 80);
  }

  const title = el.getAttribute('title');
  if (title?.trim()) return title.trim().slice(0, 80);

  const prev = el.previousElementSibling;
  if (prev && ['LABEL', 'SPAN', 'DIV', 'TH', 'TD', 'DT', 'P'].includes(prev.tagName)) {
    const text = prev.textContent?.trim();
    if (text && text.length > 0 && text.length < 60) return cleanLabel(text).slice(0, 80);
  }

  const td = el.closest('td');
  if (td) {
    const tr = td.closest('tr');
    if (tr) {
      const th = tr.querySelector('th');
      if (th?.textContent?.trim()) return cleanLabel(th.textContent).slice(0, 80);
      const firstTd = tr.querySelector('td');
      if (firstTd && firstTd !== td && firstTd.textContent?.trim()) {
        const text = firstTd.textContent.trim();
        if (text.length < 60) return cleanLabel(text).slice(0, 80);
      }
    }
  }

  const parent = el.parentElement;
  if (parent) {
    for (const child of parent.children) {
      if (child === el || child.contains(el)) continue;
      if (['LABEL', 'SPAN', 'EM', 'STRONG', 'B'].includes(child.tagName)) {
        const text = child.textContent?.trim();
        if (text && text.length > 0 && text.length < 60) return cleanLabel(text).slice(0, 80);
      }
    }
  }

  return undefined;
}

/** Extract value from a native form control. */
function extractControlValue(el: HTMLElement): {
  value?: string;
  type: string;
  placeholder?: string;
  html?: string;
} {
  const tag = el.tagName.toLowerCase();

  if (tag === 'input') {
    const input = el as HTMLInputElement;
    const type = input.type || 'text';
    if (type === 'checkbox') return { value: input.checked ? 'checked' : undefined, type: 'checkbox' };
    if (type === 'radio') {
      if (!input.checked) return { type: 'radio' };
      const lbl = input.closest('label') ?? input.nextElementSibling;
      return { type: 'radio', value: lbl?.textContent?.trim() || input.value || 'selected' };
    }
    const val = input.value?.trim();
    const ph = input.getAttribute('placeholder') ?? undefined;
    return {
      type,
      value: val && val !== ph ? val.slice(0, 150) : undefined,
      placeholder: ph,
    };
  }

  if (tag === 'select') {
    const select = el as HTMLSelectElement;
    const selected = select.options[select.selectedIndex];
    return {
      type: 'select',
      value: selected?.text?.trim() || select.value?.trim() || undefined,
      placeholder: select.getAttribute('placeholder') ?? undefined,
    };
  }

  if (tag === 'textarea') {
    const textarea = el as HTMLTextAreaElement;
    return {
      type: 'textarea',
      value: textarea.value?.trim().slice(0, 200) || undefined,
      placeholder: textarea.getAttribute('placeholder') ?? undefined,
    };
  }

  if (el.getAttribute('contenteditable') === 'true') {
    const text = (el.textContent ?? '').trim();
    const rawHtml = el.innerHTML ?? '';
    return {
      type: 'richtext',
      value: text ? text.slice(0, 200) : undefined,
      html: rawHtml && rawHtml !== '<br>' && rawHtml !== '<p><br></p>' ? rawHtml.slice(0, 500) : undefined,
    };
  }

  return { type: 'unknown' };
}

// ═══════════════════════════════════════════════════════════════════════════════
// SCANNERS
// ═══════════════════════════════════════════════════════════════════════════════

// ─── Container scanner ──────────────────────────────────────────────────────

function snapshotContainer(container: Element): {
  snapshot: InitialFieldSnapshot | null;
  innerControls: Element[];
} {
  const innerControls = Array.from(container.querySelectorAll(ALL_CONTROLS_SELECTOR));

  try {
    const label = extractUniversalLabel(container);
    const sectionLabel = findSectionLabel(container, [label]);
    const fieldPath = buildFieldPath(sectionLabel, label);
    const prop = container.getAttribute('prop') ?? undefined;
    const required = detectRequired(container) || undefined;

    // Check for tables/lists inside container first
    const contentArea = findContentArea(container);

    // Card/list inside container
    const cards = Array.from(
      contentArea.querySelectorAll<HTMLElement>(
        '[class*="card"]:not([class*="el-card"]):not(.el-form-item), ' +
        '.task-card, .card-item',
      ),
    ).filter((c) => c instanceof HTMLElement && isVisible(c));
    if (cards.length >= 2) {
      const summaries = cards
        .slice(0, MAX_LIST_ITEMS)
        .map((card) => extractItemTitle(card))
        .filter(Boolean) as string[];
      if (summaries.length > 0) {
        return {
          snapshot: {
            ...(label ? { fieldLabel: label } : {}),
            ...(fieldPath ? { fieldPath } : {}),
            ...(sectionLabel ? { sectionLabel } : {}),
            ...(prop ? { fieldProp: prop } : {}),
            ...(required ? { required: true } : {}),
            fieldType: 'list',
            itemCount: cards.length,
            defaultValueText: `共${cards.length}项：${summaries.join('；').slice(0, 420)}`,
          },
          innerControls,
        };
      }
    }

    // Table inside container
    const tableRows = Array.from(
      contentArea.querySelectorAll<HTMLElement>('table tbody tr, [class*="table__row"]'),
    ).filter((row) => row instanceof HTMLElement && isVisible(row));
    if (tableRows.length > 0) {
      let hdrs: string[] = [];
      const innerTable = contentArea.querySelector('table');
      if (innerTable) {
        hdrs = Array.from(innerTable.querySelectorAll('thead th, tr:first-child th'))
          .map((cell) => cleanLabel(cell.textContent ?? ''));
      }
      if (hdrs.length === 0) {
        // Try split-table layout (Element UI, Ant Design, etc.)
        const tableWrapper = contentArea.querySelector('[class*="table"]');
        if (tableWrapper) {
          const headerRoot = tableWrapper.querySelector('[class*="header-wrapper"], [class*="header"], [class*="thead"]');
          if (headerRoot) {
            hdrs = Array.from(headerRoot.querySelectorAll('th'))
              .map((cell) => cleanLabel(cell.textContent ?? ''));
          }
        }
      }
      const rowSummaries = tableRows
        .slice(0, MAX_TABLE_ROWS)
        .map((row) => {
          const cells = Array.from(row.querySelectorAll('td, th'));
          const parts = cells
            .map((cell, i) => {
              const header = hdrs[i];
              if (header && /^(操作|action|actions?)$/i.test(cleanLabel(header))) return undefined;
              const text = summarizeElementText(cell, 80);
              if (!text) return undefined;
              return header ? `${cleanLabel(header)}:${text}` : text;
            })
            .filter(Boolean) as string[];
          return normalizeText(parts.join(' | ')).slice(0, 180) || undefined;
        })
        .filter(Boolean) as string[];

      return {
        snapshot: {
          ...(label ? { fieldLabel: label } : {}),
          ...(fieldPath ? { fieldPath } : {}),
          ...(sectionLabel ? { sectionLabel } : {}),
          ...(prop ? { fieldProp: prop } : {}),
          ...(required ? { required: true } : {}),
          fieldType: 'table',
          itemCount: tableRows.length,
          defaultValueText: rowSummaries.length > 0
            ? `共${tableRows.length}行：${rowSummaries.join('；').slice(0, 420)}`
            : `共${tableRows.length}行`,
        },
        innerControls,
      };
    }

    // Regular field type detection
    const { fieldType, defaultValueText, placeholder, defaultValueHtml } = detectFieldType(container);

    if (!label && !prop && !defaultValueText) {
      return { snapshot: null, innerControls };
    }

    const snapshot: InitialFieldSnapshot = {};
    if (label) snapshot.fieldLabel = label;
    if (fieldPath) snapshot.fieldPath = fieldPath;
    if (sectionLabel) snapshot.sectionLabel = sectionLabel;
    if (prop) snapshot.fieldProp = prop;
    if (fieldType) snapshot.fieldType = fieldType;
    if (required) snapshot.required = true;
    if (defaultValueText) snapshot.defaultValueText = defaultValueText;
    if (placeholder) snapshot.placeholder = placeholder;
    if (defaultValueHtml) snapshot.defaultValueHtml = defaultValueHtml;

    return { snapshot, innerControls };
  } catch {
    return { snapshot: null, innerControls };
  }
}

export function scanContainers(): {
  snapshots: InitialFieldSnapshot[];
  coveredElements: Set<Element>;
} {
  const snapshots: InitialFieldSnapshot[] = [];
  const coveredElements = new Set<Element>();
  const seenContainers = new Set<Element>();

  try {
    // Walk all elements, find form containers using the classifier
    const allElements = document.querySelectorAll('*');
    for (const el of allElements) {
      if (seenContainers.has(el)) continue;
      if (!isFormContainer(el)) continue;
      // Skip containers inside already-processed containers
      if (Array.from(seenContainers).some((s) => s.contains(el))) continue;
      seenContainers.add(el);

      const { snapshot, innerControls } = snapshotContainer(el);
      for (const ctrl of innerControls) coveredElements.add(ctrl);
      if (snapshot) snapshots.push(snapshot);
    }
  } catch { /* degrade gracefully */ }

  return { snapshots, coveredElements };
}

// ─── Generic controls scanner ───────────────────────────────────────────────

export function scanGenericControls(excludedElements?: Set<Element>): {
  snapshots: InitialFieldSnapshot[];
  coveredElements: Set<Element>;
} {
  const snapshots: InitialFieldSnapshot[] = [];
  const coveredElements = new Set<Element>();

  const controls = document.querySelectorAll<HTMLElement>(ALL_CONTROLS_SELECTOR);

  for (const el of controls) {
    if (excludedElements?.has(el)) continue;
    if (coveredElements.has(el)) continue;
    if (!isVisible(el)) continue;
    if (isPaginationContext(el)) continue;

    try {
      const label = findGenericLabel(el);
      const sectionLabel = findSectionLabel(el, [label]);
      const fieldPath = buildFieldPath(sectionLabel, label);
      const { value, type, placeholder, html } = extractControlValue(el);
      const name = el.getAttribute('name') ?? undefined;

      if (!label && !name && !value) continue;

      coveredElements.add(el);

      const snapshot: InitialFieldSnapshot = {};
      if (label) snapshot.fieldLabel = label;
      if (fieldPath) snapshot.fieldPath = fieldPath;
      if (sectionLabel) snapshot.sectionLabel = sectionLabel;
      if (name) snapshot.fieldProp = name;
      if (type && type !== 'unknown') snapshot.fieldType = type;
      if (el.hasAttribute('required')) snapshot.required = true;
      if (value) snapshot.defaultValueText = value;
      if (placeholder) snapshot.placeholder = placeholder;
      if (html) snapshot.defaultValueHtml = html;

      snapshots.push(snapshot);
    } catch { /* skip */ }
  }

  return { snapshots, coveredElements };
}

// ─── Table scanner ──────────────────────────────────────────────────────────

function findTableLabel(table: Element): {
  fieldLabel?: string;
  sectionLabel?: string;
  fieldPath?: string;
  required?: boolean;
  fieldProp?: string;
} {
  const container = findFormContainer(table);
  if (container) {
    const fieldLabel = extractUniversalLabel(container);
    const sectionLabel = findSectionLabel(container, [fieldLabel]);
    return {
      fieldLabel,
      sectionLabel,
      fieldPath: buildFieldPath(sectionLabel, fieldLabel),
      required: detectRequired(container) || undefined,
      fieldProp: container.getAttribute('prop') ?? undefined,
    };
  }

  const caption = table.querySelector('caption')?.textContent;
  if (caption?.trim()) {
    const fieldLabel = cleanLabel(caption);
    return { fieldLabel, fieldPath: fieldLabel };
  }

  // Standalone table — look for a real heading near the table
  const tableRoot = (() => {
    let el: Element | null = table;
    for (let i = 0; i < 3 && el; i++) {
      const parent = el.parentElement;
      if (!parent) break;
      const cls = classifyElement(parent);
      if (cls?.type === 'table') { el = parent; continue; }
      break;
    }
    return el;
  })();

  let el: Element | null = tableRoot;
  for (let depth = 0; depth < 5 && el; depth++) {
    let prev: Element | null = el.previousElementSibling;
    let hops = 0;
    while (prev && hops < 3) {
      const heading = prev.matches('h1, h2, h3, h4, [role="heading"]')
        ? prev
        : prev.querySelector('h1, h2, h3, h4, [role="heading"]');
      if (heading) {
        const text = cleanLabel(normalizeText(heading.textContent ?? ''));
        if (text.length >= 2 && text.length <= 40) return { fieldLabel: text, fieldPath: text };
      }
      prev = prev.previousElementSibling;
      hops++;
    }
    el = el.parentElement;
  }

  // Active navigation item
  const activeNav = document.querySelector<HTMLElement>(
    '[aria-current="page"], [class*="menu-item"][class*="active"], [class*="menu-item"][class*="selected"]',
  );
  if (activeNav) {
    const text = cleanLabel(normalizeText(activeNav.textContent ?? ''));
    if (text.length >= 2 && text.length <= 30) return { fieldLabel: text, fieldPath: text };
  }

  // Page title
  if (document.title?.trim()) {
    const parts = document.title
      .split(/\s*[-|｜·•]\s*/)
      .map((p) => cleanLabel(p.trim()))
      .filter((p) => p.length >= 2 && p.length <= 30);
    if (parts.length > 0) return { fieldLabel: parts[0], fieldPath: parts[0] };
  }

  return {};
}

export function scanStructuredTables(): InitialFieldSnapshot[] {
  const snapshots: InitialFieldSnapshot[] = [];
  const tables = document.querySelectorAll<HTMLElement>('table');
  const seen = new Set<Element>();

  for (const table of tables) {
    if (seen.has(table)) continue;
    seen.add(table);
    if (!(table instanceof HTMLElement) || !isVisible(table)) continue;

    const rows = Array.from(table.querySelectorAll('tbody tr')).filter((row) =>
      Array.from(row.children).some((cell) => ['TD', 'TH'].includes(cell.tagName)),
    );
    if (rows.length === 0) continue;

    let headers = Array.from(
      table.querySelectorAll('thead th, tr:first-child th'),
    ).map((cell) => cleanLabel(cell.textContent ?? ''));

    // Split-table layout detection (Element UI, Ant Design, etc.)
    if (headers.length === 0) {
      const tableWrapper = table.closest('[class*="table"]');
      if (tableWrapper) {
        const headerRoot = tableWrapper.querySelector(
          '[class*="header-wrapper"], [class*="header"], [class*="thead"]',
        );
        if (headerRoot) {
          headers = Array.from(headerRoot.querySelectorAll('th'))
            .map((cell) => cleanLabel(cell.textContent ?? ''));
        }
      }
    }

    const isInsideContainer = !!findFormContainer(table);
    const rowLimit = isInsideContainer ? MAX_TABLE_ROWS : MAX_STANDALONE_TABLE_ROWS;
    const rowSummaries = rows
      .slice(0, rowLimit)
      .map((row) => {
        const cells = Array.from(row.querySelectorAll('td, th'));
        const parts = cells
          .map((cell, index) => {
            const header = headers[index];
            if (header && /^(操作|action|actions?)$/i.test(cleanLabel(header))) return undefined;
            const text = summarizeElementText(cell, 80);
            if (!text) return undefined;
            return header ? `${cleanLabel(header)}:${text}` : text;
          })
          .filter(Boolean) as string[];
        const joined = normalizeText(parts.join(' | '));
        return joined ? joined.slice(0, 180) : undefined;
      })
      .filter(Boolean) as string[];

    const { fieldLabel, sectionLabel, fieldPath, required, fieldProp } = findTableLabel(table);

    if (!fieldLabel && !sectionLabel && rowSummaries.length === 0) continue;

    snapshots.push({
      fieldLabel: fieldLabel ?? sectionLabel ?? '表格',
      fieldPath: fieldPath ?? buildFieldPath(sectionLabel, fieldLabel),
      sectionLabel,
      fieldProp,
      fieldType: 'table',
      required,
      itemCount: rows.length,
      defaultValueText: rowSummaries.length > 0
        ? `共${rows.length}行：${rowSummaries.join('；').slice(0, 420)}`
        : `共${rows.length}行`,
    });
  }

  return snapshots;
}

// ─── List scanner ───────────────────────────────────────────────────────────

function findListLabel(container: Element): {
  fieldLabel?: string;
  sectionLabel?: string;
  fieldPath?: string;
  required?: boolean;
  fieldProp?: string;
} {
  const formContainer = findFormContainer(container);
  if (formContainer) {
    const fieldLabel = extractUniversalLabel(formContainer);
    const sectionLabel = findSectionLabel(formContainer, [fieldLabel]);
    return {
      fieldLabel,
      sectionLabel,
      fieldPath: buildFieldPath(sectionLabel, fieldLabel),
      required: detectRequired(formContainer) || undefined,
      fieldProp: formContainer.getAttribute('prop') ?? undefined,
    };
  }

  const sectionLabel = findSectionLabel(container);
  const fieldLabel = sectionLabel ?? extractHeadingText(container) ?? '列表';
  return { fieldLabel, sectionLabel, fieldPath: buildFieldPath(sectionLabel, fieldLabel) };
}

function looksLikeRepeatedItemContainer(container: Element): boolean {
  const directChildren = Array.from(container.children).filter(
    (child) =>
      child instanceof HTMLElement &&
      isVisible(child) &&
      !isFormContainer(child) &&
      !['TABLE', 'TBODY', 'THEAD', 'TR'].includes(child.tagName),
  );

  if (directChildren.length < 2 || directChildren.length > 12) return false;

  const meaningfulChildren = directChildren.filter((child) => {
    const text = summarizeElementText(child, 120);
    return Boolean(text && text.length >= 4);
  });
  if (meaningfulChildren.length < 2) return false;

  const titledChildren = directChildren.filter((child) => extractItemTitle(child));
  const interactiveChildren = directChildren.filter((child) =>
    Boolean(child.querySelector('button, a, [role="button"]')),
  );

  return titledChildren.length >= 2 || interactiveChildren.length >= 2;
}

export function scanStructuredLists(): InitialFieldSnapshot[] {
  const snapshots: InitialFieldSnapshot[] = [];
  const candidates = document.querySelectorAll<HTMLElement>(
    'section, article, ul, ol, [role="list"], ' +
      '[class*="list"], [class*="List"], [class*="task"], [class*="Task"], [class*="card"], [class*="Card"]',
  );
  const seen = new Set<Element>();

  for (const container of candidates) {
    if (seen.has(container)) continue;
    seen.add(container);
    if (!isVisible(container)) continue;

    // Skip navigation chrome using classifier
    if (container.closest('nav, aside, header, footer')) continue;
    if (isNavigationChrome(container)) continue;

    // Skip menu-like containers
    const menuItemCount = Array.from(container.children).filter((c) =>
      c.matches('[role="menuitem"]') || (() => {
        const cls = classifyElement(c);
        return cls?.type === 'menu';
      })(),
    ).length;
    if (menuItemCount >= 2) continue;

    if (!looksLikeRepeatedItemContainer(container)) continue;

    const { fieldLabel, sectionLabel, fieldPath, required, fieldProp } = findListLabel(container);
    const items = Array.from(container.children).filter(
      (child) => child instanceof HTMLElement && isVisible(child),
    );
    const summaries = items
      .slice(0, MAX_LIST_ITEMS)
      .map((item) => {
        const title = extractItemTitle(item);
        const detail = summarizeElementText(item, 160);
        const normalizedDetail =
          detail && title && detail.startsWith(title)
            ? detail.slice(title.length).replace(/^[\s:：|-]+/, '')
            : detail;
        return [title, normalizedDetail].filter(Boolean).join(' | ').slice(0, 180);
      })
      .filter(Boolean);

    if (summaries.length === 0) continue;

    snapshots.push({
      fieldLabel,
      fieldPath,
      sectionLabel,
      fieldProp,
      fieldType: 'list',
      required,
      itemCount: items.length,
      defaultValueText: `共${items.length}项：${summaries.join('；').slice(0, 420)}`,
    });
  }

  return snapshots;
}

// ─── Pagination scanner ────────────────────────────────────────────────────

export function scanPaginationControls(): InitialFieldSnapshot[] {
  const snapshots: InitialFieldSnapshot[] = [];
  const seen = new Set<Element>();

  const candidates = Array.from(
    document.querySelectorAll<HTMLElement>('div, nav, section, span'),
  ).filter((el) => isPaginationElement(el) && isVisible(el));

  for (const el of candidates) {
    if (seen.has(el)) continue;
    if (Array.from(seen).some((s) => s.contains(el))) continue;
    seen.add(el);

    const text = el.textContent ?? '';

    const totalMatch = text.match(/共\s*(\d[\d,]*)\s*条/) ?? text.match(/total[:\s]+(\d[\d,]*)/i);
    const total = totalMatch ? parseInt(totalMatch[1].replace(/,/g, ''), 10) : undefined;

    const activePage = el.querySelector(
      '.active, .is-active, [aria-current="page"], [class*="active"]',
    );
    const currentPageNum =
      activePage && /^\d+$/.test(activePage.textContent?.trim() ?? '')
        ? parseInt(activePage.textContent!.trim(), 10)
        : undefined;
    const currentPage = currentPageNum || 1;

    const allNums = Array.from(el.querySelectorAll('li, a, button'))
      .map((c) => parseInt(c.textContent?.trim() ?? '', 10))
      .filter((n) => !isNaN(n) && n > 0 && n < 100000);
    const maxPage = allNums.length > 0 ? Math.max(...allNums) : undefined;

    const pageSize = (() => {
      const selectedOpt = el.querySelector('[aria-selected="true"], .selected');
      const m = selectedOpt?.textContent?.match(/\d+/);
      if (m) return parseInt(m[0], 10);
      const proxyInput = el.querySelector<HTMLInputElement>('input[readonly]');
      const m2 = proxyInput?.value?.match(/\d+/);
      if (m2) return parseInt(m2[0], 10);
      return undefined;
    })();

    const parts: string[] = [];
    if (total !== undefined) parts.push(`共${total}条`);
    if (pageSize) parts.push(`${pageSize}条/页`);
    if (maxPage) parts.push(`第${currentPage}页/共${maxPage}页`);

    if (parts.length === 0) continue;

    const label = findSectionLabel(el) ?? '分页';
    snapshots.push({
      fieldLabel: label,
      fieldType: 'pagination',
      defaultValueText: parts.join(' | '),
    });
  }

  return snapshots;
}

// ─── Tabs scanner ───────────────────────────────────────────────────────────

export function scanActiveTabs(): InitialFieldSnapshot[] {
  const snapshots: InitialFieldSnapshot[] = [];

  // Find tablists (ARIA or classified)
  const tablists = document.querySelectorAll<HTMLElement>('[role="tablist"]');
  const seen = new Set<Element>();

  for (const tablist of tablists) {
    if (!isVisible(tablist)) continue;
    if (seen.has(tablist)) continue;
    seen.add(tablist);

    const activeTab = tablist.querySelector<HTMLElement>(
      '[role="tab"][aria-selected="true"], [class*="tab"][class*="active"], .is-active',
    );
    if (!activeTab) continue;

    const tabLabel = cleanLabel(normalizeText(activeTab.textContent ?? ''));
    if (!tabLabel || tabLabel.length > 60) continue;

    // Count all tabs
    const allTabs = tablist.querySelectorAll('[role="tab"], [class*="tab-pane"], [class*="tab-nav"]');
    const tabCount = allTabs.length || undefined;

    const sectionLabel = findSectionLabel(tablist, [tabLabel]);

    snapshots.push({
      fieldLabel: sectionLabel ?? '选项卡',
      fieldType: 'tabs',
      defaultValueText: tabLabel,
      ...(tabCount ? { itemCount: tabCount } : {}),
      ...(sectionLabel ? { sectionLabel } : {}),
    });
  }

  return snapshots;
}

// ─── Steps scanner ──────────────────────────────────────────────────────────

export function scanActiveSteps(): InitialFieldSnapshot[] {
  const snapshots: InitialFieldSnapshot[] = [];

  // Find step containers by class pattern or structural detection
  const allElements = document.querySelectorAll<HTMLElement>('*');
  const seen = new Set<Element>();

  for (const el of allElements) {
    const cls = classifyElement(el);
    if (cls?.type !== 'steps') continue;
    if (!isVisible(el)) continue;
    if (seen.has(el)) continue;
    // Skip children of already-found steps containers
    if (Array.from(seen).some((s) => s.contains(el))) continue;
    seen.add(el);

    // Find active/current step
    const activeStep = el.querySelector<HTMLElement>(
      '[class*="step"][class*="active"], [class*="step"][class*="process"], ' +
      '[class*="step"][class*="current"], [aria-current="step"]',
    );
    if (!activeStep) continue;

    const stepLabel = cleanLabel(normalizeText(activeStep.textContent ?? ''));
    if (!stepLabel || stepLabel.length > 80) continue;

    const allSteps = el.querySelectorAll('[class*="step"]:not([class*="steps"])');
    const stepCount = allSteps.length || undefined;

    const sectionLabel = findSectionLabel(el, [stepLabel]);

    snapshots.push({
      fieldLabel: sectionLabel ?? '步骤',
      fieldType: 'steps',
      defaultValueText: stepLabel,
      ...(stepCount ? { itemCount: stepCount } : {}),
      ...(sectionLabel ? { sectionLabel } : {}),
    });
  }

  return snapshots;
}

// ─── Breadcrumb scanner ─────────────────────────────────────────────────────

export function scanBreadcrumbs(): InitialFieldSnapshot[] {
  const snapshots: InitialFieldSnapshot[] = [];

  // Find breadcrumb containers
  const breadcrumbs = document.querySelectorAll<HTMLElement>(
    '[aria-label="breadcrumb" i], [role="navigation"][aria-label*="bread" i], ' +
    '[class*="breadcrumb"]',
  );

  for (const bc of breadcrumbs) {
    if (!isVisible(bc)) continue;

    const items = bc.querySelectorAll('a, span, li');
    const texts: string[] = [];
    for (const item of items) {
      const text = cleanLabel(normalizeText(item.textContent ?? ''));
      if (text && text.length > 0 && text.length < 60) {
        // Avoid duplicates from nested elements
        if (texts.length === 0 || texts[texts.length - 1] !== text) {
          texts.push(text);
        }
      }
    }

    if (texts.length < 2) continue; // At least 2 segments to be useful

    snapshots.push({
      fieldLabel: '面包屑',
      fieldType: 'breadcrumb',
      defaultValueText: texts.join(' > '),
    });
  }

  return snapshots;
}

// ─── Descriptions scanner ───────────────────────────────────────────────────

export function scanDescriptions(): InitialFieldSnapshot[] {
  const snapshots: InitialFieldSnapshot[] = [];

  // Find description lists — native <dl> or component-classified
  const dlElements = document.querySelectorAll<HTMLElement>('dl');
  for (const dl of dlElements) {
    if (!isVisible(dl)) continue;
    const pairs: string[] = [];
    const dts = dl.querySelectorAll('dt');
    for (const dt of dts) {
      const label = cleanLabel(normalizeText(dt.textContent ?? ''));
      const dd = dt.nextElementSibling;
      const value = dd?.tagName === 'DD' ? normalizeText(dd.textContent ?? '').slice(0, 100) : '';
      if (label) pairs.push(value ? `${label}: ${value}` : label);
    }
    if (pairs.length >= 2) {
      const sectionLabel = findSectionLabel(dl);
      snapshots.push({
        fieldLabel: sectionLabel ?? '描述列表',
        fieldType: 'descriptions',
        itemCount: pairs.length,
        defaultValueText: pairs.join('；').slice(0, 420),
        ...(sectionLabel ? { sectionLabel } : {}),
      });
    }
  }

  // Also find UI library description components
  const allElements = document.querySelectorAll<HTMLElement>('*');
  const seen = new Set<Element>();
  for (const el of allElements) {
    const cls = classifyElement(el);
    if (cls?.type !== 'descriptions') continue;
    if (!isVisible(el)) continue;
    if (seen.has(el)) continue;
    seen.add(el);

    // Extract label-value pairs from component description items
    const items = el.querySelectorAll('[class*="descriptions-item"], [class*="description-item"]');
    const pairs: string[] = [];
    for (const item of items) {
      const labelEl = item.querySelector('[class*="label"]');
      const contentEl = item.querySelector('[class*="content"]');
      const label = cleanLabel(normalizeText(labelEl?.textContent ?? ''));
      const value = normalizeText(contentEl?.textContent ?? '').slice(0, 100);
      if (label) pairs.push(value ? `${label}: ${value}` : label);
    }
    if (pairs.length >= 2) {
      const sectionLabel = findSectionLabel(el);
      snapshots.push({
        fieldLabel: sectionLabel ?? '描述列表',
        fieldType: 'descriptions',
        itemCount: pairs.length,
        defaultValueText: pairs.join('；').slice(0, 420),
        ...(sectionLabel ? { sectionLabel } : {}),
      });
    }
  }

  return snapshots;
}

// ─── Dialog scanner ─────────────────────────────────────────────────────────

export function scanOpenDialogs(): InitialFieldSnapshot[] {
  const snapshots: InitialFieldSnapshot[] = [];

  const dialogs = document.querySelectorAll<HTMLElement>(
    '[role="dialog"], [role="alertdialog"], dialog[open]',
  );

  for (const dialog of dialogs) {
    if (!isVisible(dialog)) continue;

    // Get dialog title
    const titleEl = dialog.querySelector(
      '[class*="dialog-title"], [class*="modal-title"], [class*="drawer-title"], ' +
      '[class*="header"] h1, [class*="header"] h2, [class*="header"] h3, ' +
      'h1, h2, h3',
    );
    const title = titleEl ? cleanLabel(normalizeText(titleEl.textContent ?? '')) : undefined;

    if (!title) continue;

    snapshots.push({
      fieldLabel: title,
      fieldType: 'dialog',
      defaultValueText: '已打开',
    });
  }

  return snapshots;
}
