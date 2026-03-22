import { createRecordingEvent, getTargetInfo } from './events';
import type { RecordingEvent } from '@web-agent-flow/shared-types';

export interface CaptureCallbacks {
  onEvent: (event: RecordingEvent) => void;
}

/**
 * Handles debouncing input events to avoid capturing every keystroke
 */
class InputDebouncer {
  private timers = new Map<Element, number>();
  private lastValues = new Map<Element, string>();

  constructor(private readonly onInputFinal: (element: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement) => void) {}

  handleInput(element: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement): void {
    // Clear existing timer
    const existingTimer = this.timers.get(element);
    if (existingTimer) {
      window.clearTimeout(existingTimer);
    }

    // Set new timer
    const timer = window.setTimeout(() => {
      this.onInputFinal(element);
      this.timers.delete(element);
      this.lastValues.delete(element);
    }, 500);

    this.timers.set(element, timer);
    this.lastValues.set(element, (element as HTMLInputElement | HTMLTextAreaElement).value);
  }

  cleanup(): void {
    this.timers.forEach((timer) => window.clearTimeout(timer));
    this.timers.clear();
    this.lastValues.clear();
  }
}

/**
 * Event capturer for the content script
 */
export class EventCapturer {
  private isCapturing = false;
  private debouncer: InputDebouncer;
  private boundHandlers: {
    click: (e: MouseEvent) => void;
    input: (e: Event) => void;
    change: (e: Event) => void;
  } | null = null;

  constructor(private readonly callbacks: CaptureCallbacks) {
    this.debouncer = new InputDebouncer((element) => this.handleInputFinal(element));
  }

  start(): void {
    if (this.isCapturing) {
      return;
    }
    this.isCapturing = true;

    // Capture initial page
    this.captureNavigate();

    // Bind event listeners
    this.boundHandlers = {
      click: (e) => this.handleClick(e),
      input: (e) => this.handleInput(e),
      change: (e) => this.handleChange(e),
    };

    document.addEventListener('click', this.boundHandlers.click, true);
    document.addEventListener('input', this.boundHandlers.input, true);
    document.addEventListener('change', this.boundHandlers.change, true);
  }

  stop(): void {
    if (!this.isCapturing) {
      return;
    }
    this.isCapturing = false;

    // Remove event listeners
    if (this.boundHandlers) {
      document.removeEventListener('click', this.boundHandlers.click, true);
      document.removeEventListener('input', this.boundHandlers.input, true);
      document.removeEventListener('change', this.boundHandlers.change, true);
      this.boundHandlers = null;
    }

    this.debouncer.cleanup();
  }

  captureNavigate(): void {
    const event = createRecordingEvent('navigate', window.location.href, {
      title: document.title,
    });
    this.callbacks.onEvent(event);
  }

  private handleClick(e: MouseEvent): void {
    if (!this.isCapturing) return;

    const target = e.target as Element;
    // Ignore clicks on extension UI elements
    if (this.isExtensionElement(target)) {
      return;
    }

    const event = createRecordingEvent('click', window.location.href, {
      target: getTargetInfo(target),
    });
    this.callbacks.onEvent(event);
  }

  private handleInput(e: Event): void {
    if (!this.isCapturing) return;

    const target = e.target as HTMLInputElement | HTMLTextAreaElement;
    if (!target || !this.isInputElement(target)) {
      return;
    }

    // Ignore extension UI elements
    if (this.isExtensionElement(target)) {
      return;
    }

    // Debounce input events
    this.debouncer.handleInput(target);
  }

  private handleInputFinal(
    element: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement,
  ): void {
    const event = createRecordingEvent('input', window.location.href, {
      target: getTargetInfo(element),
      value: (element as HTMLInputElement | HTMLTextAreaElement).value || null,
    });
    this.callbacks.onEvent(event);
  }

  private handleChange(e: Event): void {
    if (!this.isCapturing) return;

    const target = e.target as HTMLSelectElement | HTMLInputElement;
    if (!target) {
      return;
    }

    // Ignore extension UI elements
    if (this.isExtensionElement(target)) {
      return;
    }

    const event = createRecordingEvent('change', window.location.href, {
      target: getTargetInfo(target),
      value: (target as HTMLSelectElement).value || (target as HTMLInputElement).value || null,
    });
    this.callbacks.onEvent(event);
  }

  private isExtensionElement(element: Element): boolean {
    // Check if the element or any parent has extension-related attributes
    let el: Element | null = element;
    while (el) {
      if (el.id && el.id.startsWith('webagentflow-')) {
        return true;
      }
      if (el.classList && el.classList.contains('webagentflow-extension')) {
        return true;
      }
      el = el.parentElement;
    }
    return false;
  }

  private isInputElement(element: HTMLElement): element is HTMLInputElement | HTMLTextAreaElement {
    const tag = element.tagName.toLowerCase();
    return tag === 'input' || tag === 'textarea';
  }
}
