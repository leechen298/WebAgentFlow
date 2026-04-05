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
      el.hasAttribute('prop') || // Element UI: <el-form-item prop="fieldName">
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
    const container = findFormContainer(element);
    if (!container) return undefined;

    const ctx: FieldContext = { containerType: 'form-item' };

    const label = extractLabel(container);
    if (label) ctx.fieldLabel = label;

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
  } catch {
    // Any unexpected DOM error — degrade gracefully
    return undefined;
  }
}
