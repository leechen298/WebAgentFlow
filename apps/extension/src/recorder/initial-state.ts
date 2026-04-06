/**
 * Initial State Sampler — simple DOM structure capture.
 *
 * Directly traverses the DOM and captures form fields + a clean HTML snapshot.
 * No complex heuristics, just preserves the actual page structure.
 */

import type { InitialFieldSnapshot, PageInitialState } from '@web-agent-flow/shared-types';
import { getCanonicalPageUrl } from './page-url';
import { captureSimplifiedHTML } from './html-snapshot';

const MAX_FIELDS = 100;

function cleanText(text: string | null | undefined): string | undefined {
  if (!text) return undefined;
  const cleaned = text.replace(/\s+/g, ' ').trim();
  return cleaned.length > 0 ? cleaned : undefined;
}

function extractLabel(el: Element): string | undefined {
  // aria-label
  const ariaLabel = el.getAttribute('aria-label');
  if (ariaLabel) return cleanText(ariaLabel);

  // labelled-by
  const labelledBy = el.getAttribute('aria-labelledby');
  if (labelledBy) {
    const ids = labelledBy.split(/\s+/);
    const labels = ids
      .map((id) => document.getElementById(id)?.textContent)
      .filter(Boolean)
      .join(' ');
    if (labels) return cleanText(labels);
  }

  // label[for]
  if (el.id) {
    const label = document.querySelector(`label[for="${el.id}"]`);
    if (label?.textContent) return cleanText(label.textContent);
  }

  // placeholder
  const placeholder = el.getAttribute('placeholder');
  if (placeholder) return cleanText(placeholder);

  // closest label parent
  const parentLabel = el.closest('label');
  if (parentLabel) {
    const clone = parentLabel.cloneNode(true) as Element;
    clone.querySelectorAll('input, select, textarea, button').forEach((c) => c.remove());
    return cleanText(clone.textContent);
  }

  return undefined;
}

function extractValue(el: Element): { value?: string; type?: string; placeholder?: string } {
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
      placeholder: cleanText(select.getAttribute('placeholder')),
    };
  }

  if (tag === 'textarea') {
    const textarea = el as HTMLTextAreaElement;
    return {
      type: 'textarea',
      value: cleanText(textarea.value),
      placeholder: cleanText(textarea.getAttribute('placeholder')),
    };
  }

  if (el.hasAttribute('contenteditable')) {
    return {
      type: 'richtext',
      value: cleanText(el.textContent),
    };
  }

  return {};
}

function traverseDOM(root: Element, fields: InitialFieldSnapshot[], path: string[]): void {
  if (fields.length >= MAX_FIELDS) return;

  // Collect form fields at this level
  const controls = root.querySelectorAll<HTMLElement>(
    'input:not([type="hidden"]):not([type="button"]):not([type="submit"]):not([type="reset"]), select, textarea, [contenteditable="true"]',
  );

  for (const el of controls) {
    // Skip if already inside a form-item container that we'll process separately
    if (el.closest('.el-form-item, .ant-form-item, .n-form-item, .form-item') !== root &&
        el.closest('.el-form-item, .ant-form-item, .n-form-item, .form-item')) {
      continue;
    }

    const label = extractLabel(el);
    const { value, type, placeholder } = extractValue(el);

    if (label || value) {
      fields.push({
        fieldLabel: label,
        fieldPath: path.length > 0 ? path.join(' / ') : undefined,
        sectionLabel: path[path.length - 1],
        fieldType: type,
        required: el.hasAttribute('required') || el.getAttribute('aria-required') === 'true',
        defaultValueText: value,
        placeholder,
      });
    }
  }

  // Process form-item containers
  const containers = root.querySelectorAll(
    '.el-form-item, .ant-form-item, .n-form-item, .form-item',
  );

  for (const container of containers) {
    if (fields.length >= MAX_FIELDS) break;

    // Get label from the container
    const labelEl = container.querySelector(
      '.el-form-item__label, .ant-form-item-label, .n-form-item-label, label',
    );
    const label = cleanText(labelEl?.textContent);

    // Find the control inside
    const control = container.querySelector<HTMLElement>(
      'input:not([type="hidden"]):not([type="button"]):not([type="submit"]):not([type="reset"]), select, textarea, [contenteditable="true"]',
    );

    if (control) {
      const { value, type, placeholder } = extractValue(control);
      const prop = control.getAttribute('data-prop') || control.getAttribute('name') || control.getAttribute('id') || undefined;

      fields.push({
        fieldLabel: label,
        fieldPath: path.length > 0 ? [...path, label].filter(Boolean).join(' / ') : label,
        sectionLabel: path[path.length - 1],
        fieldProp: prop,
        fieldType: type,
        required: control.hasAttribute('required') || control.getAttribute('aria-required') === 'true' ||
                  container.classList.contains('is-required'),
        defaultValueText: value,
        placeholder,
      });
    }
  }

  // Recurse into sections with their own path context
  const sections = root.querySelectorAll<HTMLElement>(
    '.el-card, .ant-card, .section, [class*="-section"], fieldset, [role="region"]',
  );

  for (const section of sections) {
    if (fields.length >= MAX_FIELDS) break;

    // Get section title
    const titleEl = section.querySelector(
      '.el-card__header, .ant-card-head, .section-title, legend, h1, h2, h3, h4, h5, h6',
    );
    const sectionTitle = cleanText(titleEl?.textContent);

    if (sectionTitle) {
      traverseDOM(section, fields, [...path, sectionTitle]);
    }
  }
}

/**
 * Capture the initial state of the current page.
 *
 * Simple strategy:
 *   1. Traverse DOM and extract form fields with path context
 *   2. Capture a clean HTML snapshot for reference
 */
export function captureInitialState(): PageInitialState {
  const fields: InitialFieldSnapshot[] = [];

  // Start traversal from main content area
  const mainContent =
    document.querySelector('main, [role="main"], .main-content, .app-main, .el-main, .ant-layout-content') ||
    document.body;

  traverseDOM(mainContent, fields, []);

  // Capture simplified HTML snapshot
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
    fields: fields.slice(0, MAX_FIELDS),
    ...(htmlSnapshot ? { htmlSnapshot } : {}),
  };
}
