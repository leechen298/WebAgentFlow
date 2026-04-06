/**
 * Field Context Extraction — extracts semantic context for recording events.
 *
 * Uses the component classifier and label extractor for library-agnostic
 * form field detection. No hardcoded library-specific class selectors.
 */

import type { FieldContext } from '@web-agent-flow/shared-types';
import { findFormContainer, classifyElement } from './component-classifier';
import {
  cleanLabel,
  buildFieldPath,
  findSectionLabel,
  summarizeElementText,
  extractItemTitle,
} from './dom-utils';
import {
  extractUniversalLabel,
  extractUniversalValue,
  detectRequired,
  extractHintOrError,
} from './label-extractor';

// ─── Table context ──────────────────────────────────────────────────────────

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
    return extractUniversalLabel(formContainer);
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

  let headers = Array.from(
    table.querySelectorAll('thead th, tr:first-child th'),
  ).map((cell) => cleanLabel(cell.textContent ?? ''));

  // Split-table layout detection
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

// ─── List item context ──────────────────────────────────────────────────────

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
    if (current !== element && isRepeatedItem(current)) {
      // Skip tab/menu items
      const cls = classifyElement(current);
      if (cls && (cls.type === 'menu' || cls.type === 'tabs')) {
        current = current.parentElement;
        depth += 1;
        continue;
      }

      const itemLabel = extractItemTitle(current);
      const formContainer = findFormContainer(current);
      const fieldLabel = formContainer ? extractUniversalLabel(formContainer) : undefined;
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

// ─── Public API ─────────────────────────────────────────────────────────────

/**
 * Extract field-level semantic context for a recording event.
 *
 * Walks up the DOM from `element` to find the nearest form-item container
 * (any UI library), then extracts label, value, required, prop, hint.
 *
 * Returns `undefined` if no recognizable container is found.
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

      const label = extractUniversalLabel(container);
      const sectionLabel = findSectionLabel(container, [label]);
      if (label) ctx.fieldLabel = label;
      if (sectionLabel) ctx.sectionLabel = sectionLabel;

      const fieldPath = buildFieldPath(sectionLabel, label);
      if (fieldPath) ctx.fieldPath = fieldPath;

      const prop = container.getAttribute('prop');
      if (prop) ctx.fieldProp = prop;

      const req = detectRequired(container);
      if (req) ctx.fieldRequired = true;

      const valueText = extractUniversalValue(container);
      if (valueText) ctx.fieldValueText = valueText;

      const hint = extractHintOrError(container);
      if (hint) ctx.fieldHintText = hint;

      return ctx;
    }

    return undefined;
  } catch {
    return undefined;
  }
}
