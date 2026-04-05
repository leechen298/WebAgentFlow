import type { FieldContext } from '@web-agent-flow/shared-types';

// ─── Container detection ────────────────────────────────────────────────────

/**
 * Exact class names that identify a form-item container.
 * Covers Element UI/Plus, Ant Design, Naive UI, and common generic patterns.
 */
const FORM_ITEM_CLASSES = [
  'el-form-item',   // Element UI / Element Plus
  'ant-form-item',  // Ant Design
  'n-form-item',    // Naive UI
  'form-item',      // generic
  'form-group',     // Bootstrap / generic
  'form-field',     // generic
];

function normalizeText(raw: string): string {
  return raw.replace(/\s+/g, ' ').trim();
}

/**
 * Walk up the DOM from `element` (at most 10 levels) to find the nearest
 * recognizable form-item container.
 *
 * Stops early at high-level boundaries (form, body, dialog, table) to avoid
 * false positives and excessive traversal.
 */
function findFormContainer(element: Element): Element | undefined {
  let el: Element | null = element.parentElement;
  let depth = 0;

  while (el && depth < 10) {
    const tag = el.tagName.toLowerCase();

    // ── Positive match ───────────────────────────────────────────────────────
    if (
      FORM_ITEM_CLASSES.some((cls) => el!.classList.contains(cls)) ||
      tag === 'fieldset'
    ) {
      return el;
    }

    // ── Stop — left the local field scope ────────────────────────────────────
    if (
      tag === 'form' ||
      tag === 'body' ||
      tag === 'html' ||
      el.getAttribute('role') === 'dialog' ||
      el.getAttribute('role') === 'main' ||
      el.classList.contains('el-table') ||
      el.classList.contains('el-table__body') ||
      el.classList.contains('el-dialog__body') ||
      el.classList.contains('el-dialog__wrapper')
    ) {
      break;
    }

    el = el.parentElement;
    depth++;
  }

  return undefined;
}

// ─── Label extraction ────────────────────────────────────────────────────────

/** Remove trailing label decorations (colons, asterisks, spaces). */
function cleanLabel(raw: string): string {
  return raw.trim().replace(/[\s*：:]+$/, '').trim();
}

function buildFieldPath(...parts: Array<string | undefined>): string | undefined {
  const unique = parts
    .map((part) => (part ? cleanLabel(part) : ''))
    .filter(Boolean)
    .filter((part, index, arr) => arr.indexOf(part) === index);

  return unique.length > 0 ? unique.join(' / ') : undefined;
}

function extractHeadingText(el: Element): string | undefined {
  const text = normalizeText(el.textContent ?? '');
  if (
    text &&
    text.length >= 2 &&
    text.length <= 40 &&
    !/[，。！？;；]$/.test(text)
  ) {
    return cleanLabel(text).slice(0, 80);
  }

  const innerHeading = el.querySelector(
    'h1, h2, h3, h4, h5, h6, [role="heading"], strong, b, ' +
      '.title, .section-title, .module-title, .panel-title, .card-title, .ant-card-head-title, .el-divider__text',
  );
  const innerText = normalizeText(innerHeading?.textContent ?? '');
  if (
    innerText &&
    innerText.length >= 2 &&
    innerText.length <= 40 &&
    !/[，。！？;；]$/.test(innerText)
  ) {
    return cleanLabel(innerText).slice(0, 80);
  }

  return undefined;
}

function findSectionLabel(
  start: Element,
  exclude: Array<string | undefined> = [],
): string | undefined {
  const excluded = new Set(
    exclude.map((item) => (item ? cleanLabel(item) : '')).filter(Boolean),
  );

  let current: Element | null = start;
  let depth = 0;

  while (current && depth < 6) {
    let prev: Element | null = current.previousElementSibling;
    let hops = 0;
    while (prev && hops < 4) {
      const text = extractHeadingText(prev);
      if (text && !excluded.has(text)) return text;
      prev = prev.previousElementSibling;
      hops += 1;
    }

    current = current.parentElement;
    depth += 1;
  }

  return undefined;
}

function summarizeElementText(
  el: Element,
  maxLength = 150,
  options: { stripInteractive?: boolean } = {},
): string | undefined {
  const input = el.querySelector<HTMLInputElement>(
    'input:not([type="hidden"]):not([type="button"]):not([type="submit"])' +
      ':not([type="reset"]):not([type="image"]):not([type="file"])',
  );
  if (input?.value?.trim()) {
    return normalizeText(input.value).slice(0, maxLength);
  }

  const select = el.querySelector<HTMLSelectElement>('select');
  if (select) {
    const selected = select.options[select.selectedIndex];
    const value = normalizeText(selected?.text ?? select.value ?? '');
    if (value) return value.slice(0, maxLength);
  }

  const textarea = el.querySelector<HTMLTextAreaElement>('textarea');
  if (textarea?.value?.trim()) {
    return normalizeText(textarea.value).slice(0, maxLength);
  }

  const clone = el.cloneNode(true) as Element;
  clone
    .querySelectorAll(
      'script, style, svg, use, path, textarea, select, input[type="hidden"], [aria-hidden="true"]',
    )
    .forEach((node) => node.remove());

  if (options.stripInteractive !== false) {
    clone
      .querySelectorAll(
        'button, a, [role="button"], [class*="btn"], [class*="button"], [class*="close"], [class*="icon"]',
      )
      .forEach((node) => node.remove());
  }

  const text = normalizeText(clone.textContent ?? '');
  if (text) return text.slice(0, maxLength);
  if (el.querySelector('img')) return '[image]';
  return undefined;
}

function extractItemTitle(item: Element): string | undefined {
  const heading = item.querySelector(
    'h1, h2, h3, h4, h5, h6, strong, b, ' +
      '.title, .item-title, .task-title, .card-title, .name, .label, [class*="title"], [class*="name"]',
  );
  const headingText = normalizeText(heading?.textContent ?? '');
  if (headingText && headingText.length <= 80) {
    return headingText.slice(0, 80);
  }

  const summary = summarizeElementText(item, 120);
  if (!summary) return undefined;
  return summary.split(/[,，;；]/)[0]?.slice(0, 80);
}

function extractLabel(container: Element): string | undefined {
  // Element UI / Plus
  const elLabel = container.querySelector('.el-form-item__label');
  if (elLabel?.textContent) {
    const t = cleanLabel(elLabel.textContent);
    if (t) return t.slice(0, 80);
  }

  // Ant Design
  const antLabel = container.querySelector('.ant-form-item-label > label');
  if (antLabel?.textContent) {
    const t = cleanLabel(antLabel.textContent);
    if (t) return t.slice(0, 80);
  }

  // Naive UI
  const nLabel = container.querySelector('.n-form-item-label');
  if (nLabel?.textContent) {
    const t = cleanLabel(nLabel.textContent);
    if (t) return t.slice(0, 80);
  }

  // Native <label>
  const labelEl = container.querySelector('label');
  if (labelEl?.textContent) {
    const t = cleanLabel(labelEl.textContent);
    if (t) return t.slice(0, 80);
  }

  // <fieldset><legend>
  const legend = container.querySelector('legend');
  if (legend?.textContent) {
    const t = cleanLabel(legend.textContent);
    if (t) return t.slice(0, 80);
  }

  return undefined;
}

// ─── Value extraction ────────────────────────────────────────────────────────

function extractValueText(container: Element): string | undefined {
  // 1. Selected tags — multi-select (el-tag, ant-tag, n-tag)
  //    Captures values like "永春" from <span class="el-tag">永春 ×</span>
  const tags = container.querySelectorAll('.el-tag, .ant-tag, .n-tag');
  if (tags.length > 0) {
    const texts = Array.from(tags)
      .slice(0, 10)
      .map((t) => {
        // Clone to strip close-button text before reading
        const clone = t.cloneNode(true) as Element;
        clone.querySelector('.el-tag__close, [class*="tag__close"], [class*="tag-close"]')?.remove();
        return clone.textContent?.trim();
      })
      .filter(Boolean);
    if (texts.length > 0) return texts.join(', ').slice(0, 150);
  }

  // 2. Date / datetime range inputs (start ~ end)
  const rangeInputs = container.querySelectorAll<HTMLInputElement>('.el-range-input');
  if (rangeInputs.length >= 2) {
    const start = rangeInputs[0].value?.trim();
    const end = rangeInputs[1].value?.trim();
    if (start || end) return [start, end].filter(Boolean).join(' ~ ').slice(0, 150);
  }

  // 3. Ant Design Select display
  const antSelectItem = container.querySelector('.ant-select-selection-item');
  if (antSelectItem?.textContent?.trim()) {
    return antSelectItem.textContent.trim().slice(0, 150);
  }

  // 4. Plain text input (not hidden, button, submit, checkbox, radio, file)
  const inp = container.querySelector<HTMLInputElement>(
    'input:not([type="hidden"]):not([type="button"]):not([type="submit"])' +
      ':not([type="checkbox"]):not([type="radio"]):not([type="file"])',
  );
  if (inp) {
    const val = inp.value?.trim();
    // Skip placeholder-only inputs
    if (val && val !== inp.placeholder?.trim()) return val.slice(0, 150);
  }

  // 5. <textarea>
  const ta = container.querySelector<HTMLTextAreaElement>('textarea');
  if (ta?.value?.trim()) return ta.value.trim().slice(0, 150);

  return undefined;
}

// ─── Required detection ──────────────────────────────────────────────────────

function detectRequired(container: Element): true | undefined {
  // Element UI adds is-required class to the container
  if (container.classList.contains('is-required')) return true;

  // Asterisk in label text
  const labelText =
    container.querySelector('.el-form-item__label, .ant-form-item-label > label, label, legend')
      ?.textContent ?? '';
  if (labelText.includes('*')) return true;

  // Native required attribute on any input within the field
  if (container.querySelector('[required]')) return true;

  return undefined;
}

// ─── Hint / error text ───────────────────────────────────────────────────────

function extractHintText(container: Element): string | undefined {
  const hint = container.querySelector(
    '.el-form-item__error, ' +
      '.ant-form-item-explain-error, ' +
      '.n-form-item-feedback--error, ' +
      '[class*="form-item__error"], ' +
      '[class*="form-error"], ' +
      '[class*="field-error"], ' +
      '[class*="form-hint"]',
  );
  const text = hint?.textContent?.trim();
  return text ? text.slice(0, 100) : undefined;
}

function summarizeTableCell(cell: Element, header?: string): string | undefined {
  if (header && /^(操作|action|actions?)$/i.test(cleanLabel(header))) {
    return undefined;
  }

  const text = summarizeElementText(cell, 80);
  if (!text) return undefined;

  if (!header || /^(序号|#)$/i.test(cleanLabel(header))) {
    return text;
  }

  return `${cleanLabel(header)}:${text}`;
}

function getTableLabel(table: Element): string | undefined {
  const formContainer = findFormContainer(table);
  if (formContainer) {
    return extractLabel(formContainer);
  }

  const caption = table.querySelector('caption')?.textContent;
  if (caption?.trim()) return cleanLabel(caption);

  return findSectionLabel(table);
}

function getTableRowContext(element: Element): FieldContext | undefined {
  const row = element.closest('tr');
  const table = row?.closest('table');
  if (!row || !table) return undefined;
  const tableRow = row as HTMLTableRowElement;

  const cells = Array.from(row.querySelectorAll('td, th'));
  if (cells.length === 0) return undefined;

  const headers = Array.from(
    table.querySelectorAll('thead th, tr:first-child th'),
  ).map((cell) => cleanLabel(cell.textContent ?? ''));
  const parts = cells
    .map((cell, index) => summarizeTableCell(cell, headers[index]))
    .filter(Boolean) as string[];
  if (parts.length === 0) return undefined;

  const fieldLabel = getTableLabel(table);
  const rowIndex =
    tableRow.sectionRowIndex >= 0 ? tableRow.sectionRowIndex + 1 : tableRow.rowIndex + 1;
  const itemLabel = extractItemTitle(row) ?? `第${rowIndex}行`;
  const sectionLabel = findSectionLabel(table, [fieldLabel, itemLabel]);

  return {
    containerType: 'table-row',
    fieldLabel: fieldLabel ?? itemLabel,
    fieldPath: buildFieldPath(sectionLabel, fieldLabel, itemLabel),
    sectionLabel,
    itemLabel,
    fieldValueText: parts.join(' | ').slice(0, 180),
  };
}

function isRepeatedItem(item: Element): boolean {
  const parent = item.parentElement;
  if (!parent) return false;

  const siblings = Array.from(parent.children).filter(
    (child) =>
      child instanceof HTMLElement &&
      child !== item &&
      child.tagName === item.tagName &&
      summarizeElementText(child, 120),
  );

  return siblings.length >= 1;
}

function getListItemContext(element: Element): FieldContext | undefined {
  let current: Element | null = element;
  let depth = 0;

  while (current && depth < 6) {
    if (
      current !== element &&
      isRepeatedItem(current) &&
      !current.matches('li.ant-menu-item, .ant-tabs-tab')
    ) {
      const itemLabel = extractItemTitle(current);
      const formContainer = findFormContainer(current);
      const fieldLabel = formContainer ? extractLabel(formContainer) : undefined;
      const sectionLabel = findSectionLabel(formContainer ?? current, [fieldLabel, itemLabel]);
      const value = summarizeElementText(current, 180);
      if (!itemLabel && !value) return undefined;

      return {
        containerType: 'list-item',
        fieldLabel: fieldLabel ?? itemLabel ?? sectionLabel,
        fieldPath: buildFieldPath(sectionLabel, fieldLabel, itemLabel),
        sectionLabel,
        itemLabel,
        fieldValueText: value,
      };
    }

    current = current.parentElement;
    depth += 1;
  }

  return undefined;
}

// ─── Public API ──────────────────────────────────────────────────────────────

/**
 * Extract field-level semantic context for a recording event.
 *
 * Walks up the DOM from `element` to find the nearest form-item container
 * (Element UI `.el-form-item`, Ant Design `.ant-form-item`, native `<fieldset>`,
 * or any element with a `prop` attribute), then extracts:
 *
 *   fieldLabel     — visible label text (e.g. "活动城市")
 *   fieldValueText — current value(s) in the field (e.g. "永春")
 *   fieldRequired  — whether the field is marked required
 *   fieldProp      — validation prop name (e.g. "cityCodes")
 *   fieldHintText  — inline error / hint message
 *
 * Returns `undefined` if no recognizable container is found, so callers can
 * omit the field entirely rather than storing an empty object.
 */
export function getFieldContext(element: Element): FieldContext | undefined {
  try {
    const tableCtx = getTableRowContext(element);
    if (tableCtx) return tableCtx;

    const listCtx = getListItemContext(element);
    if (listCtx) return listCtx;

    const container = findFormContainer(element);
    if (container) {
      const ctx: FieldContext = { containerType: 'form-item' };

      const label = extractLabel(container);
      const sectionLabel = findSectionLabel(container, [label]);
      if (label) ctx.fieldLabel = label;
      if (sectionLabel) ctx.sectionLabel = sectionLabel;

      const fieldPath = buildFieldPath(sectionLabel, label);
      if (fieldPath) ctx.fieldPath = fieldPath;

      // prop attribute is the primary identifier on Element UI form items
      const prop = container.getAttribute('prop');
      if (prop) ctx.fieldProp = prop;

      const req = detectRequired(container);
      if (req) ctx.fieldRequired = true;

      const valueText = extractValueText(container);
      if (valueText) ctx.fieldValueText = valueText;

      const hint = extractHintText(container);
      if (hint) ctx.fieldHintText = hint;

      return ctx;
    }

    return undefined;
  } catch {
    // Any unexpected DOM error — degrade gracefully
    return undefined;
  }
}
