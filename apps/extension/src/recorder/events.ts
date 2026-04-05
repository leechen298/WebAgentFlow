import type {
  RecordingEvent,
  RecordingEventType,
  RecordingEventTarget,
  FrameInfo,
} from '@web-agent-flow/shared-types';

/**
 * Create a recording event with the given properties
 */
export function createRecordingEvent(
  type: RecordingEventType,
  url: string,
  options: {
    title?: string;
    target?: RecordingEventTarget;
    value?: string | null;
    frameInfo?: FrameInfo;
  } = {},
): RecordingEvent {
  return {
    type,
    timestamp: Date.now(),
    url,
    ...options,
  };
}

/**
 * Find nearby descriptive text for an element (label, aria-labelledby, title, surrounding text)
 */
function getNearbyText(element: Element): string | undefined {
  // 1. aria-labelledby — most reliable for custom components
  const labelledby = element.getAttribute('aria-labelledby');
  if (labelledby) {
    const texts = labelledby
      .split(/\s+/)
      .map((id) => document.getElementById(id)?.textContent?.trim())
      .filter(Boolean);
    if (texts.length > 0) return texts.join(' ').slice(0, 100);
  }

  // 2. title attribute
  const title = element.getAttribute('title');
  if (title) return title.slice(0, 100);

  // 3. Wrapping <label> element — get text excluding the input itself
  const parent = element.parentElement;
  if (parent?.tagName.toLowerCase() === 'label') {
    const labelText = Array.from(parent.childNodes)
      .filter((n) => n !== element && n.textContent?.trim())
      .map((n) => n.textContent?.trim())
      .filter(Boolean)
      .join(' ')
      .trim();
    if (labelText) return labelText.slice(0, 100);
  }

  // 4. Previous sibling element text (short enough to be a label)
  const prevEl = element.previousElementSibling;
  if (prevEl) {
    const text = prevEl.textContent?.trim();
    if (text && text.length <= 60) return text;
  }

  return undefined;
}

/**
 * Generate a simple CSS selector for an element
 */
export function getSimpleSelector(element: Element): string {
  const parts: string[] = [];

  // Add ID if available
  if (element.id) {
    parts.push(`#${element.id}`);
  }

  // Add tag name
  parts.push(element.tagName.toLowerCase());

  // Add classes (first 2)
  if (element.classList && element.classList.length > 0) {
    const classes = Array.from(element.classList).slice(0, 2);
    parts.push(classes.map((cls) => `.${cls}`).join(''));
  }

  // Add name attribute if available
  if (element.hasAttribute('name')) {
    parts.push(`[name="${element.getAttribute('name')}"]`);
  }

  return parts.join('');
}

/**
 * Get target info from an element, with richer context fields
 */
export function getTargetInfo(element: Element): RecordingEventTarget {
  const target: RecordingEventTarget = {
    tag: element.tagName.toLowerCase(),
  };

  // ID
  if (element.id) {
    target.id = element.id;
  }

  // name attribute
  if (element.hasAttribute('name')) {
    target.name = element.getAttribute('name') || undefined;
  }

  // Text content (trimmed, max 100 chars) — skip for inputs to avoid exposing values
  const tag = element.tagName.toLowerCase();
  if (!['input', 'textarea', 'select'].includes(tag)) {
    const text = element.textContent?.trim();
    if (text && text.length > 0) {
      target.text = text.slice(0, 100);
    }
  }

  // Label: aria-label first, then associated <label> element
  const ariaLabel = element.getAttribute('aria-label');
  if (ariaLabel) {
    target.label = ariaLabel;
  } else {
    const inputElement = element as HTMLInputElement;
    if (inputElement.labels && inputElement.labels.length > 0) {
      target.label = inputElement.labels[0].textContent?.trim().slice(0, 100);
    }
  }

  // Selector
  target.selector = getSimpleSelector(element);

  // Placeholder (for form inputs)
  const placeholder = element.getAttribute('placeholder');
  if (placeholder) {
    target.placeholder = placeholder.slice(0, 100);
  }

  // CSS classes (up to 5, space-separated)
  if (element.classList.length > 0) {
    target.className = Array.from(element.classList).slice(0, 5).join(' ');
  }

  // ARIA role
  const role = element.getAttribute('role');
  if (role) {
    target.role = role;
  }

  // Nearby descriptive text (aria-labelledby, title, wrapping label, prev sibling)
  const nearby = getNearbyText(element);
  if (nearby) {
    target.nearbyText = nearby;
  }

  return target;
}
