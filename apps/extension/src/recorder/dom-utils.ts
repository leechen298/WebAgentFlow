/**
 * Shared DOM utilities — extracted from initial-state.ts and context.ts
 * to eliminate duplication.
 */

/** Remove trailing label decorations (colons, asterisks, spaces). */
export function cleanLabel(raw: string): string {
  return raw.trim().replace(/[\s*：:]+$/, '').trim();
}

/** Collapse whitespace to single spaces. */
export function normalizeText(raw: string): string {
  return raw.replace(/\s+/g, ' ').trim();
}

/** Build a hierarchical path from label parts, deduplicating. */
export function buildFieldPath(...parts: Array<string | undefined>): string | undefined {
  const unique = parts
    .map((part) => (part ? cleanLabel(part) : ''))
    .filter(Boolean)
    .filter((part, index, arr) => arr.indexOf(part) === index);

  return unique.length > 0 ? unique.join(' / ') : undefined;
}

/** True if the element is visible (not display:none, not zero-size). */
export function isVisible(el: HTMLElement): boolean {
  if (el.offsetParent === null && el !== document.body) {
    const style = getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
  }
  return el.offsetWidth > 0 || el.offsetHeight > 0;
}

/**
 * Extract a short heading-like text from an element.
 * Checks direct text first, then looks for inner heading elements.
 */
export function extractHeadingText(el: Element): string | undefined {
  const directText = normalizeText(el.textContent ?? '');
  if (
    directText &&
    directText.length >= 2 &&
    directText.length <= 40 &&
    !/[，。！？;；]$/.test(directText)
  ) {
    return cleanLabel(directText).slice(0, 80);
  }

  const innerHeading = el.querySelector(
    'h1, h2, h3, h4, h5, h6, [role="heading"], strong, b, ' +
      '.title, .section-title, .module-title, .panel-title, .card-title, ' +
      '[class*="card-head-title"], [class*="divider__text"]',
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

/**
 * Walk up the DOM looking for a nearby section label
 * (heading, title, divider text).
 */
export function findSectionLabel(
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

    const parent = current.parentElement;
    if (parent) {
      const heading = Array.from(parent.children)
        .slice(0, 4)
        .map((child) => extractHeadingText(child))
        .find((text) => text && !excluded.has(text));
      if (heading) return heading;
    }

    current = current.parentElement;
    depth += 1;
  }

  return undefined;
}

/**
 * Summarize the visible text content of an element, suitable for
 * field values or table cell content.
 */
export function summarizeElementText(
  el: Element,
  maxLength = 150,
  options: { stripInteractive?: boolean } = {},
): string | undefined {
  const input = el.querySelector<HTMLInputElement>(
    'input:not([type="hidden"]):not([type="button"]):not([type="submit"])' +
      ':not([type="reset"]):not([type="image"]):not([type="file"])',
  );
  if (input) {
    const val = input.value?.trim();
    if (val) return normalizeText(val).slice(0, maxLength);
    const ariaVal = input.getAttribute('aria-valuenow');
    if (ariaVal !== null && ariaVal !== '') return ariaVal.slice(0, maxLength);
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
      'script, style, svg, use, path, textarea, select, ' +
        'input[type="hidden"], input[type="button"], input[type="submit"], input[type="reset"], ' +
        '[aria-hidden="true"]',
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

/**
 * Extract a title/heading from a list item or card element.
 */
export function extractItemTitle(item: Element): string | undefined {
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
