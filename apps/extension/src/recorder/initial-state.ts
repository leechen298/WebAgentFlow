/**
 * Initial State Sampler — Task Pack 6.5 v2 (generic-first strategy).
 *
 * Captures form field default values at recording start before any user
 * interaction.  Three-layer strategy:
 *
 *   Layer 1 — Generic DOM rules (works on ANY page):
 *     Scans all native form controls (input/select/textarea/contenteditable),
 *     discovers labels via label[for], aria-*, parent <label>, nearby text,
 *     table headers, etc.
 *
 *   Layer 2 — Container-enhanced (UI library pages):
 *     Recognized containers (.el-form-item, .ant-form-item, .n-form-item, etc.)
 *     provide richer context: structured labels, prop, required, and
 *     component-specific value extraction.
 *
 *   Layer 3 — Merge:
 *     Container-enriched fields first; standalone fields fill gaps.
 *     Deduplication by DOM element prevents double-counting.
 *
 * Design constraints:
 * - Does NOT do a full-page HTML snapshot — only key field data
 * - Degrades gracefully if a field can't be parsed
 * - Capped at MAX_FIELDS to avoid payload bloat
 * - Called once at recording start (or re-called on page navigation)
 */

import type { InitialFieldSnapshot, PageInitialState } from '@web-agent-flow/shared-types';

const MAX_FIELDS = 80;

// ═══════════════════════════════════════════════════════════════════════════════
// SHARED UTILITIES
// ═══════════════════════════════════════════════════════════════════════════════

function cleanLabel(raw: string): string {
  return raw.trim().replace(/[\s*：:]+$/, '').trim();
}

/** True if the element is visible (not display:none, not zero-size). */
function isVisible(el: HTMLElement): boolean {
  // offsetParent is null for display:none (and also for position:fixed, but
  // that's acceptable — form fields are rarely fixed-positioned).
  // For <body> children, offsetParent can be null even if visible.
  if (el.offsetParent === null && el !== document.body) {
    // Double-check: getComputedStyle is expensive, use only as fallback
    const style = getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
  }
  return el.offsetWidth > 0 || el.offsetHeight > 0;
}

// ═══════════════════════════════════════════════════════════════════════════════
// LAYER 1 — GENERIC DOM RULES
// ═══════════════════════════════════════════════════════════════════════════════

// More targeted selector that avoids the double-not issue above
const GENERIC_INPUT_SELECTOR =
  'input:not([type="hidden"]):not([type="button"]):not([type="submit"])' +
  ':not([type="reset"]):not([type="image"])';

const ALL_CONTROLS_SELECTOR = [
  GENERIC_INPUT_SELECTOR,
  'select',
  'textarea',
  '[contenteditable="true"]',
].join(', ');

/**
 * Find a label for a form control using generic DOM heuristics.
 * Priority order (most reliable first):
 *   1. <label for="id">
 *   2. aria-labelledby
 *   3. aria-label
 *   4. Parent <label> wrapping the input
 *   5. title attribute
 *   6. Preceding sibling label/span/div text
 *   7. Table-row header (<th> or first <td>)
 *   8. Adjacent label-like sibling in parent
 */
function findGenericLabel(el: HTMLElement): string | undefined {
  // 1. <label for="id">
  if (el.id) {
    try {
      const label = document.querySelector<HTMLLabelElement>(
        `label[for="${CSS.escape(el.id)}"]`,
      );
      if (label?.textContent?.trim()) {
        return cleanLabel(label.textContent).slice(0, 80);
      }
    } catch {
      // CSS.escape or querySelector may throw in edge cases
    }
  }

  // 2. aria-labelledby
  const labelledBy = el.getAttribute('aria-labelledby');
  if (labelledBy) {
    const ids = labelledBy.split(/\s+/);
    const texts = ids
      .map((id) => document.getElementById(id)?.textContent?.trim())
      .filter(Boolean);
    if (texts.length > 0) {
      return cleanLabel(texts.join(' ')).slice(0, 80);
    }
  }

  // 3. aria-label
  const ariaLabel = el.getAttribute('aria-label');
  if (ariaLabel?.trim()) return ariaLabel.trim().slice(0, 80);

  // 4. Parent <label> wrapping the input
  const parentLabel = el.closest('label');
  if (parentLabel) {
    const clone = parentLabel.cloneNode(true) as Element;
    // Remove the control itself and other controls to isolate label text
    clone
      .querySelectorAll('input, select, textarea, [contenteditable]')
      .forEach((c) => c.remove());
    const text = clone.textContent?.trim();
    if (text) return cleanLabel(text).slice(0, 80);
  }

  // 5. title attribute
  const title = el.getAttribute('title');
  if (title?.trim()) return title.trim().slice(0, 80);

  // 6. Preceding sibling with label-like text
  const prev = el.previousElementSibling;
  if (
    prev &&
    ['LABEL', 'SPAN', 'DIV', 'TH', 'TD', 'DT', 'P'].includes(prev.tagName)
  ) {
    const text = prev.textContent?.trim();
    if (text && text.length > 0 && text.length < 60) {
      return cleanLabel(text).slice(0, 80);
    }
  }

  // 7. Table-based forms: <tr><th>Label</th><td><input/></td></tr>
  const td = el.closest('td');
  if (td) {
    const tr = td.closest('tr');
    if (tr) {
      const th = tr.querySelector('th');
      if (th && th.textContent?.trim()) {
        return cleanLabel(th.textContent).slice(0, 80);
      }
      // Some tables use first <td> as label
      const firstTd = tr.querySelector('td');
      if (firstTd && firstTd !== td && firstTd.textContent?.trim()) {
        const text = firstTd.textContent.trim();
        if (text.length < 60) return cleanLabel(text).slice(0, 80);
      }
    }
  }

  // 8. Sibling in parent that looks label-like
  const parent = el.parentElement;
  if (parent) {
    for (const child of parent.children) {
      if (child === el || child.contains(el)) continue;
      if (['LABEL', 'SPAN', 'EM', 'STRONG', 'B'].includes(child.tagName)) {
        const text = child.textContent?.trim();
        if (text && text.length > 0 && text.length < 60) {
          return cleanLabel(text).slice(0, 80);
        }
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

    if (type === 'checkbox') {
      return { value: input.checked ? 'checked' : undefined, type: 'checkbox' };
    }
    if (type === 'radio') {
      if (!input.checked) return { type: 'radio' };
      const lbl = input.closest('label') ?? input.nextElementSibling;
      return {
        type: 'radio',
        value: lbl?.textContent?.trim() || input.value || 'selected',
      };
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

  // contenteditable
  if (el.getAttribute('contenteditable') === 'true') {
    const text = (el.textContent ?? '').trim();
    const rawHtml = el.innerHTML ?? '';
    return {
      type: 'richtext',
      value: text ? text.slice(0, 200) : undefined,
      html:
        rawHtml && rawHtml !== '<br>' && rawHtml !== '<p><br></p>'
          ? rawHtml.slice(0, 500)
          : undefined,
    };
  }

  return { type: 'unknown' };
}

/**
 * Layer 1: Scan all form controls on the page.
 * Returns snapshots and the set of DOM elements already covered.
 */
function scanGenericControls(excludedElements?: Set<Element>): {
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

    try {
      const label = findGenericLabel(el);
      const { value, type, placeholder, html } = extractControlValue(el);
      const name = el.getAttribute('name') ?? undefined;

      // Skip if no useful identifying or value data
      if (!label && !name && !value) continue;

      coveredElements.add(el);

      const snapshot: InitialFieldSnapshot = {};
      if (label) snapshot.fieldLabel = label;
      if (name) snapshot.fieldProp = name;
      if (type && type !== 'unknown') snapshot.fieldType = type;
      if (el.hasAttribute('required')) snapshot.required = true;
      if (value) snapshot.defaultValueText = value;
      if (placeholder) snapshot.placeholder = placeholder;
      if (html) snapshot.defaultValueHtml = html;

      snapshots.push(snapshot);
    } catch {
      // Skip problematic elements
    }
  }

  return { snapshots, coveredElements };
}

// ═══════════════════════════════════════════════════════════════════════════════
// LAYER 2 — CONTAINER-ENHANCED (UI library pages)
// ═══════════════════════════════════════════════════════════════════════════════

const FORM_ITEM_CLASSES = [
  'el-form-item', // Element UI / Element Plus
  'ant-form-item', // Ant Design
  'n-form-item', // Naive UI
  'form-item', // generic
  'form-group', // Bootstrap / generic
  'form-field', // generic
] as const;

const CONTAINER_SELECTOR = FORM_ITEM_CLASSES.map((cls) => `.${cls}`).join(', ');

// ─── Container label extraction (library-aware) ─────────────────────────────

function extractContainerLabel(container: Element): string | undefined {
  // UI library structured labels (most reliable inside containers)
  // — Element UI / Plus
  const elLabel = container.querySelector('.el-form-item__label');
  if (elLabel?.textContent) {
    const t = cleanLabel(elLabel.textContent);
    if (t) return t.slice(0, 80);
  }
  // — Ant Design
  const antLabel = container.querySelector('.ant-form-item-label > label');
  if (antLabel?.textContent) {
    const t = cleanLabel(antLabel.textContent);
    if (t) return t.slice(0, 80);
  }
  // — Naive UI
  const nLabel = container.querySelector('.n-form-item-label');
  if (nLabel?.textContent) {
    const t = cleanLabel(nLabel.textContent);
    if (t) return t.slice(0, 80);
  }
  // — Generic: native <label>, <legend>
  const labelEl = container.querySelector(
    ':scope > label, :scope > div > label',
  );
  if (labelEl?.textContent) {
    const t = cleanLabel(labelEl.textContent);
    if (t) return t.slice(0, 80);
  }
  const legend = container.querySelector('legend');
  if (legend?.textContent) {
    const t = cleanLabel(legend.textContent);
    if (t) return t.slice(0, 80);
  }
  return undefined;
}

// ─── Container required detection ───────────────────────────────────────────

function detectRequired(container: Element): boolean {
  if (container.classList.contains('is-required')) return true;
  const labelText =
    container
      .querySelector(
        '.el-form-item__label, .ant-form-item-label > label, label, legend',
      )
      ?.textContent ?? '';
  if (labelText.includes('*')) return true;
  if (container.querySelector('[required]')) return true;
  return false;
}

// ─── Container field value extraction (layered) ─────────────────────────────

interface FieldData {
  fieldType?: string;
  defaultValueText?: string;
  placeholder?: string;
  defaultValueHtml?: string;
}

function isSelectProxyInput(input: HTMLInputElement): boolean {
  const role = input.getAttribute('role');
  const ariaHasPopup = input.getAttribute('aria-haspopup');
  const className = input.className || '';

  return (
    role === 'combobox' ||
    ariaHasPopup === 'listbox' ||
    className.includes('selection-search-input') ||
    className.includes('select__input')
  );
}

function extractContainerFieldData(container: Element): FieldData {
  // ── A. Generic native controls (works everywhere) ──────────────────────

  // A1. contenteditable (richtext)
  const richtext = container.querySelector<HTMLElement>(
    '[contenteditable="true"]',
  );
  if (richtext) {
    const text = (richtext.textContent ?? '').trim();
    const html = richtext.innerHTML ?? '';
    return {
      fieldType: 'richtext',
      defaultValueText: text ? text.slice(0, 200) : undefined,
      defaultValueHtml:
        html && html !== '<br>' && html !== '<p><br></p>'
          ? html.slice(0, 500)
          : undefined,
    };
  }

  // A2. Native <select>
  const select = container.querySelector<HTMLSelectElement>('select');
  if (select) {
    const selected = select.options[select.selectedIndex];
    return {
      fieldType: 'select',
      defaultValueText:
        selected?.text?.trim() || select.value?.trim() || undefined,
      placeholder: select.getAttribute('placeholder') ?? undefined,
    };
  }

  // A3. Checkboxes
  const checkboxes = container.querySelectorAll<HTMLInputElement>(
    'input[type="checkbox"]',
  );
  if (checkboxes.length > 0) {
    const checkedLabels = Array.from(checkboxes)
      .filter((cb) => cb.checked)
      .map((cb) => {
        const lbl = cb.closest('label') ?? cb.nextElementSibling;
        return (lbl?.textContent?.trim() || cb.value || '').slice(0, 30);
      })
      .filter(Boolean);
    return {
      fieldType: 'checkbox',
      defaultValueText:
        checkedLabels.length > 0 ? checkedLabels.join(', ') : undefined,
    };
  }

  // A4. Radio buttons
  const checkedRadio = container.querySelector<HTMLInputElement>(
    'input[type="radio"]:checked',
  );
  if (checkedRadio) {
    const lbl = checkedRadio.closest('label') ?? checkedRadio.nextElementSibling;
    return {
      fieldType: 'radio',
      defaultValueText:
        lbl?.textContent?.trim() || checkedRadio.value || undefined,
    };
  }
  if (container.querySelector('input[type="radio"]')) {
    return { fieldType: 'radio' };
  }

  // ── B. Common visual patterns (DOM shape, not library-specific) ────────

  // B1. Selected tags (multi-select visual pattern)
  //     Tags are small colored chips inside the control area with close buttons.
  const tags = container.querySelectorAll(
    '.el-tag, .ant-tag, .n-tag, [class*="tag-item"], [class*="tag_item"]',
  );
  if (tags.length > 0) {
    const texts = Array.from(tags)
      .slice(0, 10)
      .map((t) => {
        const clone = t.cloneNode(true) as Element;
        // Remove close/delete buttons from tag text
        clone
          .querySelectorAll(
            '[class*="tag__close"], [class*="tag-close"], [class*="close"], [aria-label="close"], [aria-label="delete"]',
          )
          .forEach((x) => x.remove());
        return clone.textContent?.trim();
      })
      .filter(Boolean) as string[];
    if (texts.length > 0) {
      return {
        fieldType: 'select',
        defaultValueText: texts.join(', ').slice(0, 150),
      };
    }
  }

  // B2. Date/time range pattern: two adjacent readonly inputs
  const rangeInputs = container.querySelectorAll<HTMLInputElement>(
    'input[readonly], .el-range-input',
  );
  if (rangeInputs.length >= 2) {
    const values = Array.from(rangeInputs)
      .slice(0, 2)
      .map((i) => i.value?.trim())
      .filter(Boolean);
    if (values.length >= 1) {
      return {
        fieldType: 'date-range',
        defaultValueText: values.join(' ~ ').slice(0, 150),
      };
    }
  }

  // A5. Plain input (text/number/date/email/etc.)
  // Skip proxy inputs used by custom selects or range widgets so later layers
  // can extract the actual displayed value.
  const inp = container.querySelector<HTMLInputElement>(
    'input:not([type="hidden"]):not([type="button"]):not([type="submit"])' +
      ':not([type="checkbox"]):not([type="radio"]):not([type="file"])',
  );
  if (inp) {
    const val = inp.value?.trim();
    const ph = inp.getAttribute('placeholder') ?? undefined;
    const readonly = inp.hasAttribute('readonly');

    if (!(readonly && (!val || isSelectProxyInput(inp)))) {
      return {
        fieldType: inp.getAttribute('type') || 'text',
        defaultValueText: val && val !== ph ? val.slice(0, 150) : undefined,
        placeholder: ph,
      };
    }
  }

  // A6. Textarea
  const ta = container.querySelector<HTMLTextAreaElement>('textarea');
  if (ta) {
    return {
      fieldType: 'textarea',
      defaultValueText: ta.value?.trim().slice(0, 150) || undefined,
      placeholder: ta.getAttribute('placeholder') ?? undefined,
    };
  }

  // ── C. Component library enhancement (specific selector fallbacks) ─────

  // C1. Ant Design Select
  const antSelectItem = container.querySelector('.ant-select-selection-item');
  if (antSelectItem?.textContent?.trim()) {
    return {
      fieldType: 'select',
      defaultValueText: antSelectItem.textContent.trim().slice(0, 150),
    };
  }

  // C2. Element Plus v2 Select (.el-select__wrapper)
  const elSelectWrapper = container.querySelector('.el-select__wrapper');
  if (elSelectWrapper) {
    const selectedItem = elSelectWrapper.querySelector<HTMLElement>(
      '.el-select__selected-item:not(.is-transparent):not(.el-select__placeholder)',
    );
    if (selectedItem?.textContent?.trim()) {
      return {
        fieldType: 'select',
        defaultValueText: selectedItem.textContent.trim().slice(0, 150),
      };
    }
    return { fieldType: 'select' };
  }

  // C3. Element UI / older Element Plus Select (.el-select)
  const elSelect = container.querySelector('.el-select');
  if (elSelect) {
    const inner = container.querySelector<HTMLInputElement>('.el-input__inner');
    const val = inner?.value?.trim();
    const ph = inner?.getAttribute('placeholder') ?? undefined;
    return {
      fieldType: 'select',
      defaultValueText: val && val !== ph ? val.slice(0, 150) : undefined,
      placeholder: ph,
    };
  }

  // C4. Naive UI Select
  const nSelect = container.querySelector('.n-base-selection');
  if (nSelect) {
    const label = nSelect.querySelector<HTMLElement>(
      '.n-base-selection-label, .n-base-selection-input',
    );
    const text = label?.textContent?.trim();
    if (text) {
      return { fieldType: 'select', defaultValueText: text.slice(0, 150) };
    }
    return { fieldType: 'select' };
  }

  // ── D. Generic visible-text fallback ───────────────────────────────────
  //    For custom components: try to read visible text inside the control
  //    area, excluding labels and error messages.

  const contentEl =
    container.querySelector('.el-form-item__content') ??
    container.querySelector('.ant-form-item-control-input-content') ??
    container.querySelector('.n-form-item-blank') ??
    // Generic: last child div that isn't the label area
    container.querySelector(':scope > div:last-child');
  if (contentEl) {
    const clone = contentEl.cloneNode(true) as Element;
    // Remove noise: error messages, hints, labels
    clone
      .querySelectorAll(
        '[class*="error"], [class*="Error"], [class*="hint"], [class*="Hint"], ' +
          '[class*="feedback"], [class*="explain"], label, legend',
      )
      .forEach((el) => el.remove());
    const text = clone.textContent?.trim();
    if (text && text.length > 0 && text.length < 200) {
      return { fieldType: 'custom', defaultValueText: text.slice(0, 150) };
    }
  }

  return {};
}

// ─── Per-container snapshot ─────────────────────────────────────────────────

/**
 * Snapshot a recognized container.
 * Returns the snapshot and the set of form controls found inside (for dedup).
 */
function snapshotContainer(container: Element): {
  snapshot: InitialFieldSnapshot | null;
  innerControls: Element[];
} {
  const innerControls = Array.from(
    container.querySelectorAll(ALL_CONTROLS_SELECTOR),
  );

  try {
    const label = extractContainerLabel(container);
    const prop = container.getAttribute('prop') ?? undefined;
    const required = detectRequired(container) || undefined;
    const { fieldType, defaultValueText, placeholder, defaultValueHtml } =
      extractContainerFieldData(container);

    // Skip containers with no useful data
    if (!label && !prop && !defaultValueText) {
      return { snapshot: null, innerControls };
    }

    const snapshot: InitialFieldSnapshot = {};
    if (label) snapshot.fieldLabel = label;
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

/**
 * Layer 2: Scan recognized UI library containers.
 * Returns snapshots and the set of form control elements already covered.
 */
function scanContainers(): {
  snapshots: InitialFieldSnapshot[];
  coveredElements: Set<Element>;
} {
  const snapshots: InitialFieldSnapshot[] = [];
  const coveredElements = new Set<Element>();
  const seenContainers = new Set<Element>();

  try {
    const containers = document.querySelectorAll(CONTAINER_SELECTOR);
    for (const container of containers) {
      if (seenContainers.has(container)) continue;
      seenContainers.add(container);

      const { snapshot, innerControls } = snapshotContainer(container);
      // Mark all inner controls as covered regardless of snapshot success
      for (const el of innerControls) coveredElements.add(el);

      if (snapshot) snapshots.push(snapshot);
    }
  } catch {
    // Degrade gracefully
  }

  return { snapshots, coveredElements };
}

// ═══════════════════════════════════════════════════════════════════════════════
// LAYER 3 — MERGE & PUBLIC API
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Capture the initial state of the current page.
 *
 * Strategy:
 *   1. Scan recognized UI containers (Layer 2) — richer context
 *   2. Scan standalone form controls not inside containers (Layer 1) — broad coverage
 *   3. Merge: container results first, then standalone, capped at MAX_FIELDS
 *
 * Called once after recording starts (with a small delay to allow dynamic
 * framework rendering to settle).
 */
export function captureInitialState(): PageInitialState {
  // Layer 2 first — containers provide richer data and mark covered elements
  const { snapshots: containerFields, coveredElements } = scanContainers();

  // Layer 1 — find standalone controls not already covered by containers
  const { snapshots: standaloneFields } =
    containerFields.length < MAX_FIELDS
      ? scanGenericControls(coveredElements)
      : { snapshots: [], coveredElements: new Set<Element>() };

  const fields = [...containerFields, ...standaloneFields].slice(0, MAX_FIELDS);

  return {
    capturedAt: Date.now(),
    pageUrl: location.href,
    pageTitle: document.title,
    fields,
  };
}
