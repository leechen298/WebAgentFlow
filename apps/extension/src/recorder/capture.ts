import { createRecordingEvent, getTargetInfo } from './events';
import type { RecordingEvent, FrameInfo } from '@web-agent-flow/shared-types';

export interface CaptureCallbacks {
  onEvent: (event: RecordingEvent) => void;
}

type InputLikeElement = HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;

/**
 * Debounces input events for standard form elements.
 * If a change event fires for an element with a pending debounced input,
 * the debounce is cancelled and only the change event is emitted — giving
 * exactly one event per field fill in the common "type → blur" flow.
 */
class InputDebouncer {
  private timers = new Map<Element, number>();

  constructor(
    private readonly onInputFinal: (element: InputLikeElement) => void,
    private readonly onChangeFinal: (element: InputLikeElement) => void,
  ) {}

  handleInput(element: InputLikeElement): void {
    const existing = this.timers.get(element);
    if (existing) window.clearTimeout(existing);
    const timer = window.setTimeout(() => {
      this.timers.delete(element);
      this.onInputFinal(element);
    }, 600);
    this.timers.set(element, timer);
  }

  handleChange(element: InputLikeElement): void {
    const existing = this.timers.get(element);
    if (existing) {
      window.clearTimeout(existing);
      this.timers.delete(element);
    }
    this.onChangeFinal(element);
  }

  cleanup(): void {
    this.timers.forEach((timer) => window.clearTimeout(timer));
    this.timers.clear();
  }
}

/**
 * Debounces input events for contenteditable (rich text) elements.
 * Uses a longer debounce since rich text typing tends to be more continuous.
 */
class ContentEditableDebouncer {
  private timers = new Map<Element, number>();

  constructor(private readonly onFinal: (element: Element) => void) {}

  handle(element: Element): void {
    const existing = this.timers.get(element);
    if (existing) window.clearTimeout(existing);
    const timer = window.setTimeout(() => {
      this.timers.delete(element);
      this.onFinal(element);
    }, 800);
    this.timers.set(element, timer);
  }

  cleanup(): void {
    this.timers.forEach((t) => window.clearTimeout(t));
    this.timers.clear();
  }
}

/**
 * Event capturer for the content script.
 * Accepts optional frameInfo to tag events from iframes.
 *
 * In addition to standard form events, it scans for same-origin / about:blank
 * iframes (e.g. TinyMCE, CKEditor) and attaches contenteditable input listeners
 * so that rich-text editor content is captured even though those nested frames
 * cannot receive extension content scripts via all_frames.
 */
export class EventCapturer {
  private isCapturing = false;
  private debouncer: InputDebouncer;
  private ceDebouncer: ContentEditableDebouncer;
  private boundHandlers: {
    click: (e: MouseEvent) => void;
    input: (e: Event) => void;
    change: (e: Event) => void;
  } | null = null;

  // Tracks cleanup functions for all dynamically attached iframe listeners
  private cleanupFns: Array<() => void> = [];
  // Tracks documents we have already attached to (avoid double-attaching)
  private attachedDocs = new Set<Document>();

  constructor(
    private readonly callbacks: CaptureCallbacks,
    private readonly frameInfo?: FrameInfo,
  ) {
    this.debouncer = new InputDebouncer(
      (el) => this.emitInput(el),
      (el) => this.emitChange(el),
    );
    this.ceDebouncer = new ContentEditableDebouncer((el) => this.emitContentEditable(el));
  }

  start(): void {
    if (this.isCapturing) return;
    this.isCapturing = true;

    this.captureNavigate();

    this.boundHandlers = {
      click: (e) => this.handleClick(e),
      input: (e) => this.handleInput(e),
      change: (e) => this.handleChange(e),
    };

    document.addEventListener('click', this.boundHandlers.click, true);
    document.addEventListener('input', this.boundHandlers.input, true);
    document.addEventListener('change', this.boundHandlers.change, true);

    // Scan for same-origin / about:blank iframes that may host rich text editors
    this.scanIframesAndAttach(document);
  }

  stop(): void {
    if (!this.isCapturing) return;
    this.isCapturing = false;

    if (this.boundHandlers) {
      document.removeEventListener('click', this.boundHandlers.click, true);
      document.removeEventListener('input', this.boundHandlers.input, true);
      document.removeEventListener('change', this.boundHandlers.change, true);
      this.boundHandlers = null;
    }

    this.debouncer.cleanup();
    this.ceDebouncer.cleanup();

    this.cleanupFns.forEach((fn) => fn());
    this.cleanupFns = [];
    this.attachedDocs.clear();
  }

  captureNavigate(): void {
    const event = createRecordingEvent('navigate', window.location.href, {
      title: document.title,
      frameInfo: this.frameInfo,
    });
    this.callbacks.onEvent(event);
  }

  // ─── Standard form event handlers ──────────────────────────────────────────

  private handleClick(e: MouseEvent): void {
    if (!this.isCapturing) return;
    const target = e.target as Element;
    if (this.isExtensionElement(target)) return;

    const event = createRecordingEvent('click', window.location.href, {
      title: document.title,
      target: getTargetInfo(target),
      frameInfo: this.frameInfo,
    });
    this.callbacks.onEvent(event);
  }

  private handleInput(e: Event): void {
    if (!this.isCapturing) return;
    const target = e.target as HTMLElement;
    if (!target) return;
    if (this.isExtensionElement(target)) return;

    if (this.isInputElement(target)) {
      this.debouncer.handleInput(target as InputLikeElement);
    } else if (this.isContentEditable(target)) {
      // contenteditable element directly in the current (top) document
      this.ceDebouncer.handle(target);
    }
  }

  private handleChange(e: Event): void {
    if (!this.isCapturing) return;
    const target = e.target as InputLikeElement;
    if (!target) return;
    if (this.isExtensionElement(target)) return;

    if (this.isInputElement(target)) {
      // Route through debouncer so it cancels any pending input event
      this.debouncer.handleChange(target);
    } else {
      // select, checkbox, radio — emit directly
      this.emitChange(target);
    }
  }

  // ─── Emit helpers ───────────────────────────────────────────────────────────

  private emitInput(element: InputLikeElement): void {
    const event = createRecordingEvent('input', window.location.href, {
      title: document.title,
      target: getTargetInfo(element),
      value: (element as HTMLInputElement | HTMLTextAreaElement).value || null,
      frameInfo: this.frameInfo,
    });
    this.callbacks.onEvent(event);
  }

  private emitChange(element: InputLikeElement): void {
    const event = createRecordingEvent('change', window.location.href, {
      title: document.title,
      target: getTargetInfo(element),
      value: (element as HTMLSelectElement | HTMLInputElement).value || null,
      frameInfo: this.frameInfo,
    });
    this.callbacks.onEvent(event);
  }

  /**
   * Emit an event for a contenteditable rich-text element.
   * value = plain-text content (capped at 5000 chars).
   * target.role is overridden to 'rich-text' to distinguish from normal inputs.
   */
  private emitContentEditable(element: Element): void {
    const text = element.textContent?.trim() || '';
    if (!text) return; // ignore empty editor state

    const targetInfo = getTargetInfo(element);
    targetInfo.role = 'rich-text';

    const event = createRecordingEvent('input', window.location.href, {
      title: document.title,
      target: targetInfo,
      value: text.slice(0, 5000),
      frameInfo: this.frameInfo,
    });
    this.callbacks.onEvent(event);
  }

  // ─── Iframe / contenteditable scanning ─────────────────────────────────────

  /**
   * Scan all iframes in `doc` and try to attach contenteditable listeners.
   * Also installs a MutationObserver to catch iframes added after page load
   * (common for lazily initialised rich-text editors like TinyMCE).
   */
  private scanIframesAndAttach(doc: Document): void {
    const root = doc.documentElement || doc;

    // Attach to iframes that already exist
    doc.querySelectorAll('iframe').forEach((iframe) => {
      this.tryAttachToIframe(iframe);
      // Watch for the iframe to (re)load — editors sometimes reinitialise
      const onLoad = () => this.tryAttachToIframe(iframe);
      iframe.addEventListener('load', onLoad);
      this.cleanupFns.push(() => iframe.removeEventListener('load', onLoad));
    });

    // Watch for iframes added dynamically (e.g. TinyMCE init happens after page load)
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node instanceof HTMLIFrameElement) {
            const onLoad = () => this.tryAttachToIframe(node);
            node.addEventListener('load', onLoad);
            this.cleanupFns.push(() => node.removeEventListener('load', onLoad));
            // Also try immediately in case it's already loaded
            this.tryAttachToIframe(node);
          }
        }
      }
    });

    observer.observe(root, { childList: true, subtree: true });
    this.cleanupFns.push(() => observer.disconnect());
  }

  /**
   * Try to attach a contenteditable input listener to an iframe's document.
   * Silently skips cross-origin iframes (SecurityError on contentDocument access).
   */
  private tryAttachToIframe(iframe: HTMLIFrameElement): void {
    try {
      const doc = iframe.contentDocument;
      if (!doc || this.attachedDocs.has(doc)) return;
      this.attachedDocs.add(doc);

      const handler = (e: Event) => {
        if (!this.isCapturing) return;
        const target = e.target as HTMLElement;
        if (!target || !this.isContentEditable(target)) return;
        this.ceDebouncer.handle(target);
      };

      doc.addEventListener('input', handler, true);
      this.cleanupFns.push(() => {
        try {
          doc.removeEventListener('input', handler, true);
        } catch {
          // Document may already be gone (iframe navigated away)
        }
      });

      // Recursively scan for nested iframes (e.g. editor inside an iframe inside an iframe)
      this.scanIframesAndAttach(doc);
    } catch {
      // Cross-origin iframe — contentDocument access throws SecurityError, skip silently
    }
  }

  // ─── Element type helpers ───────────────────────────────────────────────────

  private isExtensionElement(element: Element): boolean {
    let el: Element | null = element;
    while (el) {
      if (el.id && el.id.startsWith('webagentflow-')) return true;
      if (el.classList && el.classList.contains('webagentflow-extension')) return true;
      el = el.parentElement;
    }
    return false;
  }

  private isInputElement(element: HTMLElement): element is HTMLInputElement | HTMLTextAreaElement {
    const tag = element.tagName.toLowerCase();
    return tag === 'input' || tag === 'textarea';
  }

  private isContentEditable(element: HTMLElement): boolean {
    return element.contentEditable === 'true';
  }
}
