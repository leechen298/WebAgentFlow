/**
 * Universal label, value, and hint extraction — works across all UI libraries.
 *
 * Instead of checking library-specific selectors (`.el-form-item__label`,
 * `.ant-form-item-label > label`, etc.), uses:
 *   1. ARIA attributes (aria-label, aria-labelledby)
 *   2. Component name pattern matching (any class ending with "label")
 *   3. Native HTML elements (<label>, <legend>)
 *   4. Structural heuristics
 */

import { type ComponentType, classifyContainerContent, getComponentNames, isInsideCompound } from './component-classifier';
import { cleanLabel } from './dom-utils';

// ─── Label extraction ───────────────────────────────────────────────────────

/**
 * Extract the visible label from a form-item container.
 * Works for any UI library — priority-based detection.
 */
export function extractUniversalLabel(container: Element): string | undefined {
  // 1. aria-label on the container itself
  const ariaLabel = container.getAttribute('aria-label');
  if (ariaLabel?.trim()) return ariaLabel.trim().slice(0, 80);

  // 2. aria-labelledby → read referenced element text
  const labelledBy = container.getAttribute('aria-labelledby');
  if (labelledBy) {
    const ids = labelledBy.split(/\s+/);
    const texts = ids
      .map((id) => document.getElementById(id)?.textContent?.trim())
      .filter(Boolean);
    if (texts.length > 0) return cleanLabel(texts.join(' ')).slice(0, 80);
  }

  // 3. Find label element by component class pattern — ANY library
  //    Match: el-form-item__label, ant-form-item-label, n-form-item-label, etc.
  const labelEl = Array.from(container.querySelectorAll('*')).find((el) => {
    const names = getComponentNames(el);
    return names.some((name) => /label$/.test(name));
  });
  if (labelEl?.textContent) {
    const t = cleanLabel(labelEl.textContent);
    if (t) return t.slice(0, 80);
  }

  // 4. Native <label> element inside container (direct or one level deep)
  const nativeLabel = container.querySelector(':scope > label, :scope > div > label');
  if (nativeLabel?.textContent) {
    const t = cleanLabel(nativeLabel.textContent);
    if (t) return t.slice(0, 80);
  }

  // 5. <legend> element (for fieldset)
  const legend = container.querySelector('legend');
  if (legend?.textContent) {
    const t = cleanLabel(legend.textContent);
    if (t) return t.slice(0, 80);
  }

  return undefined;
}

// ─── Value extraction ───────────────────────────────────────────────────────

/**
 * Extract the current visible value from a form-item container.
 * Handles tags (multi-select), date ranges, select displays, inputs, textareas.
 */
export function extractUniversalValue(container: Element, type?: ComponentType): string | undefined {
  void type; // used for future type-specific extraction
  // 1. Selected tags — multi-select chips (any library)
  //    Small spans with close buttons inside a container
  const tags = container.querySelectorAll(
    '[class*="tag"]:not([class*="tag-close"]):not([class*="tag__close"])',
  );
  if (tags.length > 0) {
    const tagTexts: string[] = [];
    for (const tag of Array.from(tags).slice(0, 10)) {
      // Check it looks like a tag chip: has text and optionally a close button
      const names = getComponentNames(tag);
      const isTagComponent = names.some((n) => n === 'tag');
      if (!isTagComponent && !tag.querySelector('[class*="close"], [aria-label="close"], [aria-label="delete"]')) {
        continue;
      }
      const clone = tag.cloneNode(true) as Element;
      clone.querySelectorAll('[class*="close"], [aria-label="close"], [aria-label="delete"]').forEach((x) => x.remove());
      const text = clone.textContent?.trim();
      if (text) tagTexts.push(text);
    }
    if (tagTexts.length > 0) return tagTexts.join(', ').slice(0, 150);
  }

  // 2. Date/time range: two adjacent readonly inputs
  const rangeInputs = container.querySelectorAll<HTMLInputElement>(
    'input[readonly], [class*="range-input"]',
  );
  if (rangeInputs.length >= 2) {
    const values = Array.from(rangeInputs)
      .slice(0, 2)
      .map((i) => i.value?.trim())
      .filter(Boolean);
    if (values.length >= 1) {
      return values.join(' ~ ').slice(0, 150);
    }
  }

  // 3. Select display text — find *-selection-item, *-selected-item, etc.
  const selectionItem = Array.from(container.querySelectorAll('*')).find((el) => {
    const names = getComponentNames(el);
    return names.some((n) => /selection-item|selected-item|selection-label/.test(n));
  });
  if (selectionItem?.textContent?.trim()) {
    // Skip placeholder-style items (transparent / placeholder class)
    const cls = selectionItem.getAttribute('class') || '';
    if (!cls.includes('transparent') && !cls.includes('placeholder')) {
      return selectionItem.textContent.trim().slice(0, 150);
    }
  }

  // 4. Check for proxy input inside a select (readonly input with value)
  const selectInputs = container.querySelectorAll<HTMLInputElement>(
    'input:not([type="hidden"]):not([type="button"]):not([type="submit"])' +
    ':not([type="checkbox"]):not([type="radio"]):not([type="file"])',
  );
  for (const inp of selectInputs) {
    if (isInsideCompound(inp)) {
      const val = inp.value?.trim();
      const ph = inp.getAttribute('placeholder')?.trim();
      if (val && val !== ph) return val.slice(0, 150);
      continue; // Skip proxy inputs for plain input detection below
    }
  }

  // 5. Plain input (text/number/date/etc.)
  for (const inp of selectInputs) {
    if (isInsideCompound(inp)) continue;
    const val = inp.value?.trim();
    const ph = inp.getAttribute('placeholder')?.trim();
    if (val && val !== ph) return val.slice(0, 150);
  }

  // 6. <textarea>
  const ta = container.querySelector<HTMLTextAreaElement>('textarea');
  if (ta?.value?.trim()) return ta.value.trim().slice(0, 150);

  // 7. Native <select>
  const select = container.querySelector<HTMLSelectElement>('select');
  if (select) {
    const selected = select.options[select.selectedIndex];
    const text = selected?.text?.trim() || select.value?.trim();
    if (text) return text.slice(0, 150);
  }

  // 8. contenteditable
  const richtext = container.querySelector<HTMLElement>('[contenteditable="true"]');
  if (richtext) {
    const text = (richtext.textContent ?? '').trim();
    if (text) return text.slice(0, 200);
  }

  return undefined;
}

// ─── Hint / error text ──────────────────────────────────────────────────────

/**
 * Extract inline error or hint message from a form-item container.
 * Uses component name matching instead of library-specific selectors.
 */
export function extractHintOrError(container: Element): string | undefined {
  // 1. Find elements whose component name ends with "error", "feedback", or "explain"
  const hintEl = Array.from(container.querySelectorAll('*')).find((el) => {
    const names = getComponentNames(el);
    if (names.some((n) => /error|feedback|explain/.test(n))) return true;
    // Also check generic class patterns
    const cls = (el.getAttribute('class') || '').toLowerCase();
    return /form-item[_-]*error|form-error|field-error|form-hint/.test(cls);
  });

  const text = hintEl?.textContent?.trim();
  return text ? text.slice(0, 100) : undefined;
}

// ─── Required detection ─────────────────────────────────────────────────────

/**
 * Detect if a form field is required. Checks:
 *   1. is-required / required class on container
 *   2. Asterisk (*) in label text
 *   3. [required] attribute on any input inside
 *   4. aria-required on container or inputs
 */
export function detectRequired(container: Element): boolean {
  if (container.classList.contains('is-required')) return true;
  if (container.classList.contains('required')) return true;
  if (container.getAttribute('aria-required') === 'true') return true;

  // Check label for asterisk
  const label = extractUniversalLabel(container);
  if (label?.includes('*')) return true;

  // Check direct label elements (avoid extracting full label again)
  const labelEls = container.querySelectorAll('label, legend, [class*="label"]');
  for (const el of labelEls) {
    if (el.textContent?.includes('*')) return true;
  }

  // Native required attribute on inputs
  if (container.querySelector('[required]')) return true;
  if (container.querySelector('[aria-required="true"]')) return true;

  return false;
}

// ─── Container field type detection ─────────────────────────────────────────

/**
 * Detect the primary field type inside a form container.
 * Uses the classifier's nesting resolution for correct results.
 */
export function detectFieldType(container: Element): { fieldType: string; placeholder?: string; defaultValueText?: string; defaultValueHtml?: string; itemCount?: number } {
  // Check richtext first (contenteditable)
  const richtext = container.querySelector<HTMLElement>('[contenteditable="true"]');
  if (richtext) {
    const text = (richtext.textContent ?? '').trim();
    const html = richtext.innerHTML ?? '';
    return {
      fieldType: 'richtext',
      defaultValueText: text ? text.slice(0, 200) : undefined,
      defaultValueHtml: html && html !== '<br>' && html !== '<p><br></p>' ? html.slice(0, 500) : undefined,
    };
  }

  // Check native select
  const select = container.querySelector<HTMLSelectElement>('select');
  if (select) {
    const selected = select.options[select.selectedIndex];
    return {
      fieldType: 'select',
      defaultValueText: selected?.text?.trim() || select.value?.trim() || undefined,
      placeholder: select.getAttribute('placeholder') ?? undefined,
    };
  }

  // Check checkboxes
  const checkboxes = container.querySelectorAll<HTMLInputElement>('input[type="checkbox"]');
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
      defaultValueText: checkedLabels.length > 0 ? checkedLabels.join(', ') : undefined,
    };
  }

  // Check radio buttons
  const checkedRadio = container.querySelector<HTMLInputElement>('input[type="radio"]:checked');
  if (checkedRadio) {
    const lbl = checkedRadio.closest('label') ?? checkedRadio.nextElementSibling;
    return {
      fieldType: 'radio',
      defaultValueText: lbl?.textContent?.trim() || checkedRadio.value || undefined,
    };
  }
  if (container.querySelector('input[type="radio"]')) {
    return { fieldType: 'radio' };
  }

  // Use classifier for compound component detection
  //   Find the content area (not the label area)
  const contentArea = findContentArea(container);
  const classifiedType = classifyContainerContent(contentArea);

  // Map classified type to field type string
  const typeStr = classifiedType as string;

  // Get value based on detected type
  const value = extractUniversalValue(container, classifiedType);

  // Get placeholder from first non-compound input
  let placeholder: string | undefined;
  const inp = container.querySelector<HTMLInputElement>(
    'input:not([type="hidden"]):not([type="button"]):not([type="submit"])' +
    ':not([type="checkbox"]):not([type="radio"]):not([type="file"])',
  );
  if (inp) {
    placeholder = inp.getAttribute('placeholder') ?? undefined;
  }

  return {
    fieldType: typeStr,
    defaultValueText: value,
    placeholder,
  };
}

/**
 * Find the content area inside a form container (not the label area).
 * Uses component name matching instead of library-specific selectors.
 */
export function findContentArea(container: Element): Element {
  // Look for content/control area by component name pattern
  const contentEl = Array.from(container.querySelectorAll('*')).find((el) => {
    const names = getComponentNames(el);
    return names.some((n) => /^(content|control|blank|control-input-content)$/.test(n));
  });
  if (contentEl) return contentEl;

  // Fallback: last child div that isn't the label area
  const lastDiv = container.querySelector(':scope > div:last-child');
  if (lastDiv) return lastDiv;

  return container;
}
