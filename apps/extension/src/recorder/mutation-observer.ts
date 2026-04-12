/**
 * DOM Mutation Tracker — observes DOM changes in top-level document and
 * same-origin iframe documents during recording.
 *
 * Mutations are batched (coalesced over short windows), mapped to the current
 * AST when possible, and emitted as structured DomMutationRecord arrays.
 *
 * Design notes:
 *   - Mutations are batched at ~500ms intervals to avoid flooding
 *   - Each mutation carries AST association (exact/ancestor/none + fallback)
 *   - Iframe documents are observed recursively (same-origin only)
 *   - Noise filtering: skips script/style/svg mutations, extension elements,
 *     and framework bookkeeping attributes (_ngcontent, data-v-, etc.)
 */

import type {
  DomMutationRecord,
  DomMutationDetail,
  ChildListDetail,
  AttributeDetail,
  CharacterDataDetail,
  MutationNodeSummary,
  FrameInfo,
  AstMatch,
} from '@web-agent-flow/shared-types';
import type { AstIndex } from './ast-index';
import { getSimpleSelector } from './events';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Tags whose mutations are always ignored (no semantic value) */
const IGNORE_TAGS = new Set([
  'script', 'style', 'link', 'meta', 'noscript', 'svg', 'path',
  'br', 'wbr', 'head',
]);

/** Attribute names that are framework noise or irrelevant for mutation tracking */
const IGNORE_ATTR_PATTERNS = [
  /^_ng/, // Angular _ngcontent, _nghost
  /^data-v-/, // Vue scoped style
  /^data-reactid/, // React legacy
  /^data-reactroot/,
];

/**
 * Attributes whose changes are always interesting for business state tracking.
 *
 * Focused on attributes that reflect user-visible state changes rather than
 * visual styling or framework internals. This supports the downstream use case
 * of "execute action → wait for expected page change" in future execution.
 */
const INTERESTING_ATTRS = new Set([
  'class', 'hidden', 'disabled', 'readonly', 'checked', 'selected',
  'value', 'src', 'href', 'aria-hidden', 'aria-disabled', 'aria-expanded',
  'aria-selected', 'aria-checked', 'aria-label', 'aria-describedby',
  'role', 'tabindex', 'open',
  'placeholder', 'title', 'alt',
]);

/**
 * For `style` attribute changes, only these CSS properties are considered
 * business-state-relevant. All other style changes (animation, color,
 * transform, dimensions, etc.) are filtered as visual noise.
 */
const BUSINESS_STATE_STYLE_PROPS = ['display', 'visibility', 'pointer-events'];

/** Maximum text content length stored in summaries */
const MAX_TEXT_LEN = 200;

/** Batch interval (ms) — mutations are coalesced within this window */
const BATCH_INTERVAL_MS = 500;

/** Maximum mutations per batch (overflow protection) */
const MAX_MUTATIONS_PER_BATCH = 100;

// ---------------------------------------------------------------------------
// Mutation ID generation
// ---------------------------------------------------------------------------

let mutationCounter = 0;
let mutationIdPrefix = 'm';

export function resetMutationCounter(): void {
  mutationCounter = 0;
}

export function setMutationIdPrefix(prefix: string): void {
  mutationIdPrefix = prefix;
}

export function generateMutationIdPrefix(isIframe: boolean): string {
  if (!isIframe) return 'm';
  const nonce = Math.random().toString(36).slice(2, 5);
  return `fm${nonce}_`;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isIgnoredTag(el: Element): boolean {
  return IGNORE_TAGS.has(el.tagName.toLowerCase());
}

function isExtensionElement(el: Element): boolean {
  let current: Element | null = el;
  while (current) {
    if (current.id?.startsWith('webagentflow-')) return true;
    if (current.classList?.contains('webagentflow-extension')) return true;
    current = current.parentElement;
  }
  return false;
}

function isNoiseAttribute(name: string): boolean {
  return IGNORE_ATTR_PATTERNS.some((pat) => pat.test(name));
}

function isInterestingAttribute(name: string): boolean {
  if (INTERESTING_ATTRS.has(name)) return true;
  if (name.startsWith('aria-')) return true;
  // style is handled specially — see buildAttributeDetail
  // data-* is filtered by default — framework internals, not business state
  return false;
}

/**
 * For style attribute changes, extract only business-state-relevant properties.
 * Returns a filtered "old → new" pair containing only display/visibility/pointer-events,
 * or null if none of those properties changed.
 */
function extractBusinessStyleChange(
  oldStyle: string | null,
  newStyle: string | null,
): { oldValue: string | null; newValue: string | null } | null {
  const parseProps = (s: string | null): Map<string, string> => {
    const map = new Map<string, string>();
    if (!s) return map;
    for (const decl of s.split(';')) {
      const colon = decl.indexOf(':');
      if (colon < 0) continue;
      const prop = decl.slice(0, colon).trim().toLowerCase();
      const val = decl.slice(colon + 1).trim();
      if (BUSINESS_STATE_STYLE_PROPS.includes(prop)) {
        map.set(prop, val);
      }
    }
    return map;
  };

  const oldProps = parseProps(oldStyle);
  const newProps = parseProps(newStyle);

  // Check if any tracked property actually changed
  let changed = false;
  for (const prop of BUSINESS_STATE_STYLE_PROPS) {
    if ((oldProps.get(prop) ?? '') !== (newProps.get(prop) ?? '')) {
      changed = true;
      break;
    }
  }
  if (!changed) return null;

  // Build compact representations of only the business-state properties
  const formatProps = (m: Map<string, string>): string | null => {
    if (m.size === 0) return null;
    return Array.from(m.entries()).map(([k, v]) => `${k}: ${v}`).join('; ');
  };

  return {
    oldValue: formatProps(oldProps),
    newValue: formatProps(newProps),
  };
}

function summarizeNode(node: Node): MutationNodeSummary | null {
  if (node.nodeType === Node.TEXT_NODE) {
    const text = node.textContent?.trim();
    if (!text) return null;
    return { tag: '#text', text: text.slice(0, MAX_TEXT_LEN) };
  }
  if (node.nodeType !== Node.ELEMENT_NODE) return null;
  const el = node as Element;
  if (isIgnoredTag(el)) return null;

  const summary: MutationNodeSummary = {
    tag: el.tagName.toLowerCase(),
  };
  if (el.id) summary.id = el.id;
  if (el.classList?.[0]) summary.className = el.classList[0];
  const text = el.textContent?.trim();
  if (text) summary.text = text.slice(0, MAX_TEXT_LEN);
  const childCount = el.children?.length ?? 0;
  if (childCount > 0) summary.childCount = childCount;
  return summary;
}

function findNearestAreaLabel(element: Element): string | undefined {
  let el: Element | null = element.parentElement;
  for (let i = 0; i < 10 && el && el !== document.body; i++) {
    const heading = el.querySelector('h1, h2, h3, h4, [class*="title"], [class*="header"]');
    if (heading && !heading.contains(element)) {
      const text = heading.textContent?.trim();
      if (text && text.length <= 80) return text;
    }
    const ariaLabel = el.getAttribute('aria-label');
    if (ariaLabel) return ariaLabel.slice(0, 80);
    el = el.parentElement;
  }
  return undefined;
}

// ---------------------------------------------------------------------------
// DomMutationTracker
// ---------------------------------------------------------------------------

export interface MutationTrackerCallbacks {
  /** Called with a batch of coalesced mutation records */
  onMutations: (records: DomMutationRecord[]) => void;
}

export class DomMutationTracker {
  private isTracking = false;
  private observers: MutationObserver[] = [];
  private cleanupFns: Array<() => void> = [];
  private attachedDocs = new Set<Document>();
  private pendingBatch: DomMutationRecord[] = [];
  private batchTimer: number | null = null;
  private astIndex: AstIndex | null = null;

  constructor(
    private readonly callbacks: MutationTrackerCallbacks,
    private readonly frameInfo?: FrameInfo,
  ) {}

  setAstIndex(index: AstIndex | null): void {
    this.astIndex = index;
  }

  start(): void {
    if (this.isTracking) return;
    this.isTracking = true;
    resetMutationCounter();
    this.observeDocument(document);
    this.scanIframes(document);
  }

  stop(): void {
    if (!this.isTracking) return;
    this.isTracking = false;
    this.flushBatch();

    for (const obs of this.observers) {
      obs.disconnect();
    }
    this.observers = [];
    for (const fn of this.cleanupFns) {
      fn();
    }
    this.cleanupFns = [];
    this.attachedDocs.clear();
  }

  // ─── Core observation ────────────────────────────────────────────────────

  private observeDocument(doc: Document): void {
    if (this.attachedDocs.has(doc)) return;
    this.attachedDocs.add(doc);

    const root = doc.documentElement ?? doc.body;
    if (!root) return;

    const observer = new MutationObserver((mutations) => {
      if (!this.isTracking) return;
      this.processMutations(mutations, doc);
    });

    observer.observe(root, {
      childList: true,
      attributes: true,
      characterData: true,
      subtree: true,
      attributeOldValue: true,
      characterDataOldValue: true,
    });

    this.observers.push(observer);
  }

  // ─── Iframe scanning ─────────────────────────────────────────────────────

  private scanIframes(doc: Document): void {
    // Existing iframes
    doc.querySelectorAll('iframe').forEach((iframe) => {
      this.tryAttachIframe(iframe);
      const onLoad = () => this.tryAttachIframe(iframe);
      iframe.addEventListener('load', onLoad);
      this.cleanupFns.push(() => iframe.removeEventListener('load', onLoad));
    });

    // Dynamically added iframes
    const observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        for (const node of m.addedNodes) {
          if (node instanceof HTMLIFrameElement) {
            const onLoad = () => this.tryAttachIframe(node);
            node.addEventListener('load', onLoad);
            this.cleanupFns.push(() => node.removeEventListener('load', onLoad));
            this.tryAttachIframe(node);
          }
        }
      }
    });

    const root = doc.documentElement ?? doc.body;
    if (root) {
      observer.observe(root, { childList: true, subtree: true });
      this.observers.push(observer);
    }
  }

  private tryAttachIframe(iframe: HTMLIFrameElement): void {
    try {
      const doc = iframe.contentDocument;
      if (!doc || this.attachedDocs.has(doc)) return;
      this.observeDocument(doc);
      this.scanIframes(doc);
    } catch {
      // Cross-origin — skip silently
    }
  }

  // ─── Mutation processing ─────────────────────────────────────────────────

  private processMutations(mutations: MutationRecord[], _doc: Document): void {
    const now = Date.now();

    for (const mutation of mutations) {
      const target = mutation.target;
      if (!target) continue;

      // Skip text nodes with no parent element
      const targetEl = target.nodeType === Node.ELEMENT_NODE
        ? (target as Element)
        : target.parentElement;
      if (!targetEl) continue;

      // Noise filters
      if (isIgnoredTag(targetEl)) continue;
      if (isExtensionElement(targetEl)) continue;

      const record = this.buildRecord(mutation, targetEl, now);
      if (record) {
        this.pendingBatch.push(record);
      }
    }

    // Schedule batch flush
    if (this.pendingBatch.length > 0 && this.batchTimer === null) {
      this.batchTimer = window.setTimeout(() => {
        this.flushBatch();
      }, BATCH_INTERVAL_MS);
    }

    // Overflow protection: flush immediately if too many pending
    if (this.pendingBatch.length >= MAX_MUTATIONS_PER_BATCH) {
      this.flushBatch();
    }
  }

  private buildRecord(
    mutation: MutationRecord,
    targetEl: Element,
    timestamp: number,
  ): DomMutationRecord | null {
    let detail: DomMutationDetail | null = null;

    switch (mutation.type) {
      case 'childList':
        detail = this.buildChildListDetail(mutation);
        break;
      case 'attributes':
        detail = this.buildAttributeDetail(mutation, targetEl);
        break;
      case 'characterData':
        detail = this.buildCharacterDataDetail(mutation);
        break;
    }

    if (!detail) return null;

    // AST matching
    let astMatch: AstMatch | undefined;
    if (this.astIndex) {
      astMatch = this.astIndex.matchElement(targetEl);
    }

    const areaLabel = findNearestAreaLabel(targetEl);

    return {
      id: `${mutationIdPrefix}${mutationCounter++}`,
      timestamp,
      mutationType: mutation.type as DomMutationRecord['mutationType'],
      url: targetEl.ownerDocument?.location?.href ?? window.location.href,
      frameInfo: this.frameInfo,
      targetTag: targetEl.tagName.toLowerCase(),
      targetSelector: getSimpleSelector(targetEl),
      targetText: targetEl.textContent?.trim().slice(0, MAX_TEXT_LEN) || undefined,
      targetId: targetEl.id || undefined,
      targetClassName: targetEl.classList?.[0] || undefined,
      astMatch,
      detail,
      areaLabel,
    };
  }

  private buildChildListDetail(mutation: MutationRecord): ChildListDetail | null {
    const addedNodes: MutationNodeSummary[] = [];
    const removedNodes: MutationNodeSummary[] = [];

    for (const node of mutation.addedNodes) {
      const summary = summarizeNode(node);
      if (summary) addedNodes.push(summary);
    }
    for (const node of mutation.removedNodes) {
      const summary = summarizeNode(node);
      if (summary) removedNodes.push(summary);
    }

    // Skip if no meaningful nodes were added or removed
    if (addedNodes.length === 0 && removedNodes.length === 0) return null;

    return { type: 'childList', addedNodes, removedNodes };
  }

  private buildAttributeDetail(
    mutation: MutationRecord,
    targetEl: Element,
  ): AttributeDetail | null {
    const attrName = mutation.attributeName;
    if (!attrName) return null;

    // Skip framework noise attributes (_ngcontent, data-v-, data-reactid, etc.)
    if (isNoiseAttribute(attrName)) return null;

    // Special handling for `style` — only track business-state properties
    if (attrName === 'style') {
      const oldValue = mutation.oldValue;
      const newValue = targetEl.getAttribute('style');
      const result = extractBusinessStyleChange(oldValue, newValue);
      if (!result) return null;
      return {
        type: 'attributes',
        attributeName: 'style',
        oldValue: result.oldValue,
        newValue: result.newValue,
      };
    }

    // Filter data-* attributes — mostly framework internals, not business state
    if (attrName.startsWith('data-')) return null;

    // Only track attributes on the interesting list
    if (!isInterestingAttribute(attrName)) return null;

    const oldValue = mutation.oldValue;
    const newValue = targetEl.getAttribute(attrName);

    // Skip if value didn't actually change
    if (oldValue === newValue) return null;

    return {
      type: 'attributes',
      attributeName: attrName,
      oldValue: oldValue?.slice(0, MAX_TEXT_LEN) ?? null,
      newValue: newValue?.slice(0, MAX_TEXT_LEN) ?? null,
    };
  }

  private buildCharacterDataDetail(mutation: MutationRecord): CharacterDataDetail | null {
    const oldValue = mutation.oldValue?.trim() ?? null;
    const newValue = mutation.target.textContent?.trim() ?? null;

    // Skip if text didn't actually change
    if (oldValue === newValue) return null;
    // Skip empty text mutations
    if (!oldValue && !newValue) return null;

    return {
      type: 'characterData',
      oldValue: oldValue?.slice(0, MAX_TEXT_LEN) ?? null,
      newValue: newValue?.slice(0, MAX_TEXT_LEN) ?? null,
    };
  }

  // ─── Batch management ────────────────────────────────────────────────────

  private flushBatch(): void {
    if (this.batchTimer !== null) {
      window.clearTimeout(this.batchTimer);
      this.batchTimer = null;
    }

    if (this.pendingBatch.length === 0) return;

    const batch = this.pendingBatch;
    this.pendingBatch = [];
    this.callbacks.onMutations(batch);
  }
}
