import { createRecordingEvent, getTargetInfo } from './events';
import { getFieldContext } from './context';
import type { RecordingEvent, FrameInfo } from '@web-agent-flow/shared-types';

export interface CaptureCallbacks {
  onEvent: (event: RecordingEvent) => void;
}

type InputLikeElement = HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;

// ─── InputDebouncer ──────────────────────────────────────────────────────────
// Handles standard form inputs (input, textarea).
// If a change event fires while a debounced input is pending, the debounce is
// cancelled so only one event is emitted per field fill.

class InputDebouncer {
  private timers = new Map<Element, number>();

  constructor(
    private readonly onInputFinal: (el: InputLikeElement) => void,
    private readonly onChangeFinal: (el: InputLikeElement) => void,
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
    this.timers.forEach((t) => window.clearTimeout(t));
    this.timers.clear();
  }
}

// ─── ContentEditableManager ──────────────────────────────────────────────────
// Handles rich-text / contenteditable elements and iframe-embedded editors
// (TinyMCE, CKEditor, Quill, ProseMirror, custom editors).
//
// Strategy:
//   • handleInput  – debounced at 800 ms; emit if content changed from last emit
//   • handleFocusOut – fires on blur; cancel pending debounce, emit final value
//   • Deduplication – never re-emit the same content twice for the same element

class ContentEditableManager {
  private debounceTimers = new Map<Element, number>();
  private lastEmitted = new Map<Element, string>();

  constructor(private readonly onCapture: (element: Element) => void) {}

  handleInput(element: Element): void {
    const existing = this.debounceTimers.get(element);
    if (existing) window.clearTimeout(existing);
    const timer = window.setTimeout(() => {
      this.debounceTimers.delete(element);
      this.tryCapture(element);
    }, 800);
    this.debounceTimers.set(element, timer);
  }

  /** Fires on focusout/blur — captures the final value and cancels debounce. */
  handleFocusOut(element: Element): void {
    const existing = this.debounceTimers.get(element);
    if (existing) {
      window.clearTimeout(existing);
      this.debounceTimers.delete(element);
    }
    this.tryCapture(element);
  }

  private tryCapture(element: Element): void {
    const current = (element as HTMLElement).textContent?.trim() ?? '';
    if (!current) return;
    if (current === this.lastEmitted.get(element)) return; // no change
    this.lastEmitted.set(element, current);
    this.onCapture(element);
  }

  cleanup(): void {
    this.debounceTimers.forEach((t) => window.clearTimeout(t));
    this.debounceTimers.clear();
    this.lastEmitted.clear();
  }
}

// ─── EventCapturer ───────────────────────────────────────────────────────────

export class EventCapturer {
  private isCapturing = false;
  private debouncer: InputDebouncer;
  private ceManager: ContentEditableManager;

  private boundHandlers: {
    click: (e: MouseEvent) => void;
    input: (e: Event) => void;
    change: (e: Event) => void;
    focusout: (e: Event) => void;
  } | null = null;

  /** Cleanup callbacks for dynamically attached iframe listeners / observers. */
  private cleanupFns: Array<() => void> = [];
  /** Documents we have already attached to — avoids double-attaching. */
  private attachedDocs = new Set<Document>();

  constructor(
    private readonly callbacks: CaptureCallbacks,
    private readonly frameInfo?: FrameInfo,
  ) {
    this.debouncer = new InputDebouncer(
      (el) => this.emitInput(el),
      (el) => this.emitChange(el),
    );
    this.ceManager = new ContentEditableManager((el) => this.emitRichTextInput(el));
  }

  start(): void {
    if (this.isCapturing) return;
    this.isCapturing = true;

    this.captureNavigate();

    this.boundHandlers = {
      click: (e) => this.handleClick(e),
      input: (e) => this.handleInput(e),
      change: (e) => this.handleChange(e),
      focusout: (e) => this.handleFocusOut(e),
    };

    document.addEventListener('click', this.boundHandlers.click, true);
    document.addEventListener('input', this.boundHandlers.input, true);
    document.addEventListener('change', this.boundHandlers.change, true);
    // focusout bubbles; capture phase ensures we see it before any handler stops it
    document.addEventListener('focusout', this.boundHandlers.focusout, true);

    // Scan same-origin / about:blank iframes that host rich-text editors
    this.scanIframesAndAttach(document);
  }

  stop(): void {
    if (!this.isCapturing) return;
    this.isCapturing = false;

    if (this.boundHandlers) {
      document.removeEventListener('click', this.boundHandlers.click, true);
      document.removeEventListener('input', this.boundHandlers.input, true);
      document.removeEventListener('change', this.boundHandlers.change, true);
      document.removeEventListener('focusout', this.boundHandlers.focusout, true);
      this.boundHandlers = null;
    }

    this.debouncer.cleanup();
    this.ceManager.cleanup();

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

  // ─── Standard form event handlers ─────────────────────────────────────────

  private handleClick(e: MouseEvent): void {
    if (!this.isCapturing) return;
    const target = e.target as Element;
    if (this.isExtensionElement(target)) return;

    this.callbacks.onEvent(
      createRecordingEvent('click', window.location.href, {
        title: document.title,
        target: getTargetInfo(target),
        frameInfo: this.frameInfo,
        fieldContext: getFieldContext(target),
      }),
    );
  }

  private handleInput(e: Event): void {
    if (!this.isCapturing) return;
    const target = e.target as HTMLElement;
    if (!target || this.isExtensionElement(target)) return;

    if (this.isFormInput(target)) {
      this.debouncer.handleInput(target as InputLikeElement);
    } else if (this.isRichText(target)) {
      this.ceManager.handleInput(target);
    }
  }

  private handleChange(e: Event): void {
    if (!this.isCapturing) return;
    const target = e.target as InputLikeElement;
    if (!target || this.isExtensionElement(target)) return;

    if (this.isFormInput(target)) {
      this.debouncer.handleChange(target);
    } else {
      this.emitChange(target);
    }
  }

  private handleFocusOut(e: Event): void {
    if (!this.isCapturing) return;
    const target = e.target as HTMLElement;
    if (!target || this.isExtensionElement(target)) return;

    if (this.isRichText(target)) {
      this.ceManager.handleFocusOut(target);
    }
  }

  // ─── Emit helpers ──────────────────────────────────────────────────────────

  private emitInput(element: InputLikeElement): void {
    this.callbacks.onEvent(
      createRecordingEvent('input', window.location.href, {
        title: document.title,
        target: getTargetInfo(element),
        value: (element as HTMLInputElement | HTMLTextAreaElement).value || null,
        frameInfo: this.frameInfo,
        fieldContext: getFieldContext(element),
      }),
    );
  }

  private emitChange(element: InputLikeElement): void {
    this.callbacks.onEvent(
      createRecordingEvent('change', window.location.href, {
        title: document.title,
        target: getTargetInfo(element),
        value: (element as HTMLSelectElement | HTMLInputElement).value || null,
        frameInfo: this.frameInfo,
        fieldContext: getFieldContext(element),
      }),
    );
  }

  /**
   * Emit a richtext-input event.
   *   value       = plain-text content  (max 5000 chars)
   *   htmlContent = raw innerHTML snippet (max 2000 chars) for richer context
   *   target.isRichText = true, target.role = 'rich-text'
   */
  private emitRichTextInput(element: Element): void {
    const el = element as HTMLElement;
    const text = el.textContent?.trim() ?? '';
    if (!text) return;

    const targetInfo = getTargetInfo(element);
    targetInfo.isRichText = true;
    if (!targetInfo.role) targetInfo.role = 'rich-text';

    this.callbacks.onEvent(
      createRecordingEvent('richtext-input', window.location.href, {
        title: document.title,
        target: targetInfo,
        value: text.slice(0, 5000),
        htmlContent: el.innerHTML?.slice(0, 2000),
        frameInfo: this.frameInfo,
        fieldContext: getFieldContext(element),
      }),
    );
  }

  // ─── Iframe / contenteditable scanning ────────────────────────────────────

  /**
   * Attach contenteditable listeners to all existing and future iframes in `doc`.
   * Works by accessing iframe.contentDocument — only possible for same-origin and
   * about:blank frames. Cross-origin frames silently skip.
   */
  private scanIframesAndAttach(doc: Document): void {
    const root = doc.documentElement ?? doc;

    // Existing iframes
    doc.querySelectorAll('iframe').forEach((iframe) => {
      this.tryAttachToIframe(iframe);
      // Re-try on load in case the editor writes a new document via document.write()
      const onLoad = () => this.tryAttachToIframe(iframe);
      iframe.addEventListener('load', onLoad);
      this.cleanupFns.push(() => iframe.removeEventListener('load', onLoad));
    });

    // Iframes added dynamically (e.g. TinyMCE init runs after page load)
    const observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node instanceof HTMLIFrameElement) {
            const onLoad = () => this.tryAttachToIframe(node);
            node.addEventListener('load', onLoad);
            this.cleanupFns.push(() => node.removeEventListener('load', onLoad));
            this.tryAttachToIframe(node); // also try immediately
          }
        }
      }
    });

    observer.observe(root, { childList: true, subtree: true });
    this.cleanupFns.push(() => observer.disconnect());
  }

  /**
   * Try to attach rich-text capture listeners to an iframe's contentDocument.
   *
   * Three complementary mechanisms are used:
   *   1. `input` event listener  — standard DOM input events from contenteditable
   *   2. `focusout` event listener — captures final value when editor loses focus
   *   3. MutationObserver on body — fallback for editors that update the DOM
   *      without firing standard input events (rare but exists in some libraries)
   */
  private tryAttachToIframe(iframe: HTMLIFrameElement): void {
    try {
      const doc = iframe.contentDocument;
      if (!doc || this.attachedDocs.has(doc)) return;
      this.attachedDocs.add(doc);

      // 1. Input event delegation
      const inputHandler = (e: Event) => {
        if (!this.isCapturing) return;
        const target = e.target as HTMLElement;
        if (target && this.isRichText(target)) this.ceManager.handleInput(target);
      };

      // 2. Focusout event delegation (fires when editor loses focus → final value)
      const focusoutHandler = (e: Event) => {
        if (!this.isCapturing) return;
        const target = e.target as HTMLElement;
        if (target && this.isRichText(target)) this.ceManager.handleFocusOut(target);
      };

      doc.addEventListener('input', inputHandler, true);
      doc.addEventListener('focusout', focusoutHandler, true);

      this.cleanupFns.push(() => {
        try {
          doc.removeEventListener('input', inputHandler, true);
          doc.removeEventListener('focusout', focusoutHandler, true);
        } catch {
          // Doc may already be gone (iframe navigated away)
        }
      });

      // 3. MutationObserver fallback on body (if it's a rich-text body)
      const body = doc.body;
      if (body && this.isRichText(body)) {
        this.attachMutationObserverFallback(body);
      } else if (body) {
        // Body might not be contenteditable yet — watch for the attribute to be set
        const attrObserver = new MutationObserver(() => {
          if (body && this.isRichText(body)) {
            this.attachMutationObserverFallback(body);
            attrObserver.disconnect();
          }
        });
        attrObserver.observe(body, { attributes: true, attributeFilter: ['contenteditable'] });
        this.cleanupFns.push(() => attrObserver.disconnect());
      }

      // Recurse into nested iframes
      this.scanIframesAndAttach(doc);
    } catch {
      // SecurityError from cross-origin iframe — skip silently
    }
  }

  /**
   * Attach a MutationObserver to a contenteditable element as a fallback.
   * Fires ceManager.handleInput on any character-level or structural DOM change.
   */
  private attachMutationObserverFallback(element: Element): void {
    const mo = new MutationObserver(() => {
      if (!this.isCapturing) return;
      this.ceManager.handleInput(element);
    });
    mo.observe(element, { characterData: true, subtree: true, childList: true });
    this.cleanupFns.push(() => mo.disconnect());
  }

  // ─── Element type helpers ──────────────────────────────────────────────────

  private isExtensionElement(element: Element): boolean {
    let el: Element | null = element;
    while (el) {
      if (el.id?.startsWith('webagentflow-')) return true;
      if (el.classList?.contains('webagentflow-extension')) return true;
      el = el.parentElement;
    }
    return false;
  }

  private isFormInput(element: HTMLElement): element is HTMLInputElement | HTMLTextAreaElement {
    const tag = element.tagName.toLowerCase();
    return tag === 'input' || tag === 'textarea';
  }

  /**
   * Returns true for any element that is a rich-text editing surface:
   *   - contenteditable="true"  (Quill, ProseMirror, Draft.js, TinyMCE body, etc.)
   *   - ownerDocument.designMode === 'on'  (legacy editors; entire doc is editable)
   */
  private isRichText(element: HTMLElement): boolean {
    if (element.contentEditable === 'true') return true;
    try {
      if (element.ownerDocument?.designMode === 'on') return true;
    } catch {
      // Cross-origin — access denied
    }
    return false;
  }
}
