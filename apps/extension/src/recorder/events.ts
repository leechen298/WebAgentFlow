import type {
  RecordingEvent,
  RecordingEventType,
  RecordingEventTarget,
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
 * Get target info from an element
 */
export function getTargetInfo(element: Element): RecordingEventTarget {
  const target: RecordingEventTarget = {
    tag: element.tagName.toLowerCase(),
  };

  // Add ID
  if (element.id) {
    target.id = element.id;
  }

  // Add name attribute
  if (element.hasAttribute('name')) {
    target.name = element.getAttribute('name') || undefined;
  }

  // Add text content (trimmed, max 100 chars)
  const text = element.textContent?.trim();
  if (text && text.length > 0) {
    target.text = text.slice(0, 100);
  }

  // Add label from associated label element or aria-label
  const ariaLabel = element.getAttribute('aria-label');
  if (ariaLabel) {
    target.label = ariaLabel;
  } else {
    // Try to find a label for form elements
    const inputElement = element as HTMLInputElement;
    if (inputElement.labels && inputElement.labels.length > 0) {
      target.label = inputElement.labels[0].textContent?.trim().slice(0, 100);
    }
  }

  // Add selector
  target.selector = getSimpleSelector(element);

  return target;
}
