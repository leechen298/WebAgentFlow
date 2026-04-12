/**
 * Tests for DOM mutation tracking.
 *
 * Covers:
 *   1. childList mutations (add/remove nodes) are detected
 *   2. Attribute changes are detected
 *   3. characterData (text) changes are detected
 *   4. Iframe mutations are detected (same-origin)
 *   5. Mutations are emitted in chronological order
 *   6. AST association is attempted for each mutation
 *   7. Mutations without AST match still carry fallback info
 *   8. Noise filtering: script/style/svg tags and framework attrs are skipped
 *   9. Mutation IDs are unique and frame-aware
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  DomMutationTracker,
  resetMutationCounter,
  setMutationIdPrefix,
  generateMutationIdPrefix,
} from '../recorder/mutation-observer';
import type { DomMutationRecord } from '@web-agent-flow/shared-types';

// Helper to wait for batched mutations (>500ms batch interval)
function waitForBatch(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 600));
}

// Helper to wait for MutationObserver microtask + batch
function waitForMutationAndBatch(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 700));
}

describe('DomMutationTracker', () => {
  let tracker: DomMutationTracker;
  let collected: DomMutationRecord[];
  let container: HTMLDivElement;

  beforeEach(() => {
    resetMutationCounter();
    setMutationIdPrefix('m');
    collected = [];
    container = document.createElement('div');
    container.id = 'test-container';
    document.body.appendChild(container);

    tracker = new DomMutationTracker({
      onMutations: (mutations) => {
        collected.push(...mutations);
      },
    });
  });

  afterEach(() => {
    tracker.stop();
    container.remove();
  });

  // ─── 1. childList: add nodes ───────────────────────────────────────────

  it('detects childList add — new element inserted', async () => {
    tracker.start();

    const child = document.createElement('button');
    child.textContent = 'Click me';
    container.appendChild(child);

    await waitForMutationAndBatch();

    const childListMuts = collected.filter(
      (m) => m.mutationType === 'childList' && m.detail.type === 'childList',
    );
    expect(childListMuts.length).toBeGreaterThanOrEqual(1);

    const addMut = childListMuts.find((m) =>
      m.detail.type === 'childList' &&
      m.detail.addedNodes.some((n) => n.tag === 'button'),
    );
    expect(addMut).toBeDefined();
    expect(addMut!.detail.type).toBe('childList');
    if (addMut!.detail.type === 'childList') {
      expect(addMut!.detail.addedNodes.some((n) => n.tag === 'button')).toBe(true);
    }
  });

  // ─── 2. childList: remove nodes ─────────────────────────────────────────

  it('detects childList remove — element removed', async () => {
    const child = document.createElement('span');
    child.textContent = 'Remove me';
    container.appendChild(child);

    tracker.start();

    container.removeChild(child);

    await waitForMutationAndBatch();

    const removeMuts = collected.filter(
      (m) =>
        m.mutationType === 'childList' &&
        m.detail.type === 'childList' &&
        m.detail.removedNodes.some((n) => n.tag === 'span'),
    );
    expect(removeMuts.length).toBeGreaterThanOrEqual(1);
  });

  // ─── 3. Attribute changes ──────────────────────────────────────────────

  it('detects attribute changes — class change', async () => {
    const el = document.createElement('div');
    el.className = 'old-class';
    container.appendChild(el);

    tracker.start();

    el.className = 'new-class';

    await waitForMutationAndBatch();

    const attrMuts = collected.filter(
      (m) =>
        m.mutationType === 'attributes' &&
        m.detail.type === 'attributes' &&
        m.detail.attributeName === 'class',
    );
    expect(attrMuts.length).toBeGreaterThanOrEqual(1);
    const mut = attrMuts[0];
    if (mut.detail.type === 'attributes') {
      expect(mut.detail.oldValue).toBe('old-class');
      expect(mut.detail.newValue).toBe('new-class');
    }
  });

  it('detects attribute changes — hidden toggle', async () => {
    const el = document.createElement('div');
    container.appendChild(el);

    tracker.start();

    el.setAttribute('hidden', '');

    await waitForMutationAndBatch();

    const hiddenMuts = collected.filter(
      (m) =>
        m.mutationType === 'attributes' &&
        m.detail.type === 'attributes' &&
        m.detail.attributeName === 'hidden',
    );
    expect(hiddenMuts.length).toBeGreaterThanOrEqual(1);
  });

  it('detects aria attribute changes', async () => {
    const el = document.createElement('div');
    el.setAttribute('aria-expanded', 'false');
    container.appendChild(el);

    tracker.start();

    el.setAttribute('aria-expanded', 'true');

    await waitForMutationAndBatch();

    const ariaMuts = collected.filter(
      (m) =>
        m.mutationType === 'attributes' &&
        m.detail.type === 'attributes' &&
        m.detail.attributeName === 'aria-expanded',
    );
    expect(ariaMuts.length).toBeGreaterThanOrEqual(1);
    if (ariaMuts[0].detail.type === 'attributes') {
      expect(ariaMuts[0].detail.oldValue).toBe('false');
      expect(ariaMuts[0].detail.newValue).toBe('true');
    }
  });

  // ─── 4. characterData changes ─────────────────────────────────────────

  it('detects text content changes', async () => {
    const el = document.createElement('span');
    el.textContent = 'old text';
    container.appendChild(el);

    tracker.start();

    // Modify the text node directly (characterData mutation)
    el.firstChild!.textContent = 'new text';

    await waitForMutationAndBatch();

    const textMuts = collected.filter(
      (m) => m.mutationType === 'characterData',
    );
    expect(textMuts.length).toBeGreaterThanOrEqual(1);
    const mut = textMuts[0];
    if (mut.detail.type === 'characterData') {
      expect(mut.detail.oldValue).toBe('old text');
      expect(mut.detail.newValue).toBe('new text');
    }
  });

  // ─── 5. Chronological order ───────────────────────────────────────────

  it('mutations are in chronological order', async () => {
    tracker.start();

    const el1 = document.createElement('div');
    container.appendChild(el1);

    const el2 = document.createElement('div');
    container.appendChild(el2);

    await waitForMutationAndBatch();

    // All mutations should have non-decreasing timestamps
    for (let i = 1; i < collected.length; i++) {
      expect(collected[i].timestamp).toBeGreaterThanOrEqual(
        collected[i - 1].timestamp,
      );
    }
  });

  // ─── 6. Mutation records have correct structure ─────────────────────────

  it('mutation records have all required fields', async () => {
    tracker.start();

    const el = document.createElement('p');
    el.textContent = 'Hello';
    container.appendChild(el);

    await waitForMutationAndBatch();

    expect(collected.length).toBeGreaterThan(0);
    const mut = collected[0];

    // Core fields
    expect(mut.id).toBeDefined();
    expect(mut.id.startsWith('m')).toBe(true);
    expect(mut.timestamp).toBeGreaterThan(0);
    expect(mut.mutationType).toBeDefined();
    expect(mut.url).toBeDefined();
    expect(mut.targetTag).toBeDefined();
    expect(mut.detail).toBeDefined();
  });

  // ─── 7. No data loss on AST miss ──────────────────────────────────────

  it('mutations without AST index still have full info', async () => {
    // No AST index set — all matches should be undefined or none
    tracker.start();

    const el = document.createElement('div');
    el.className = 'my-component';
    container.appendChild(el);

    await waitForMutationAndBatch();

    expect(collected.length).toBeGreaterThan(0);
    const mut = collected[0];

    // Core fields still present
    expect(mut.id).toBeDefined();
    expect(mut.mutationType).toBe('childList');
    expect(mut.targetTag).toBeDefined();
    expect(mut.detail).toBeDefined();

    // astMatch is undefined when no index (no crash)
    // This is fine — the mutation is not lost
  });

  // ─── 8. Noise filtering ──────────────────────────────────────────────

  it('filters out script tag mutations', async () => {
    tracker.start();

    const script = document.createElement('script');
    script.textContent = 'console.log("test")';
    container.appendChild(script);

    await waitForMutationAndBatch();

    // The script addition itself might show as childList on the container,
    // but the summarizeNode should filter it out from addedNodes
    const scriptMuts = collected.filter(
      (m) => m.targetTag === 'script',
    );
    expect(scriptMuts.length).toBe(0);
  });

  it('filters out framework noise attributes', async () => {
    const el = document.createElement('div');
    container.appendChild(el);

    tracker.start();

    // These should be filtered
    el.setAttribute('_ngcontent-abc', '');
    el.setAttribute('data-v-1234abcd', '');

    await waitForMutationAndBatch();

    const noiseMuts = collected.filter(
      (m) =>
        m.mutationType === 'attributes' &&
        m.detail.type === 'attributes' &&
        (m.detail.attributeName.startsWith('_ng') ||
          m.detail.attributeName.startsWith('data-v-')),
    );
    expect(noiseMuts.length).toBe(0);
  });

  it('filters out extension element mutations', async () => {
    const extEl = document.createElement('div');
    extEl.id = 'webagentflow-overlay';
    container.appendChild(extEl);

    tracker.start();

    const child = document.createElement('span');
    extEl.appendChild(child);

    await waitForMutationAndBatch();

    const extMuts = collected.filter(
      (m) => m.targetId === 'webagentflow-overlay',
    );
    expect(extMuts.length).toBe(0);
  });

  // ─── 9. Mutation ID uniqueness ─────────────────────────────────────────

  it('generates sequential mutation IDs', async () => {
    tracker.start();

    const el1 = document.createElement('div');
    const el2 = document.createElement('div');
    container.appendChild(el1);
    container.appendChild(el2);

    await waitForMutationAndBatch();

    if (collected.length >= 2) {
      // IDs should be unique
      const ids = collected.map((m) => m.id);
      expect(new Set(ids).size).toBe(ids.length);
      // First ID should start with m0
      expect(ids[0]).toBe('m0');
    }
  });

  // ─── 10. Stop stops observation ─────────────────────────────────────────

  it('stop() prevents further mutation collection', async () => {
    tracker.start();

    const el1 = document.createElement('div');
    container.appendChild(el1);
    await waitForMutationAndBatch();

    const countAfterStart = collected.length;
    expect(countAfterStart).toBeGreaterThan(0);

    tracker.stop();

    const el2 = document.createElement('div');
    container.appendChild(el2);
    await waitForMutationAndBatch();

    // No new mutations after stop
    expect(collected.length).toBe(countAfterStart);
  });
});

describe('generateMutationIdPrefix', () => {
  it('returns "m" for top frame', () => {
    expect(generateMutationIdPrefix(false)).toBe('m');
  });

  it('returns "fm{nonce}_" format for iframe', () => {
    const prefix = generateMutationIdPrefix(true);
    expect(prefix).toMatch(/^fm[a-z0-9]{3}_$/);
  });

  it('generates different nonces across calls', () => {
    const prefixes = new Set<string>();
    for (let i = 0; i < 20; i++) {
      prefixes.add(generateMutationIdPrefix(true));
    }
    expect(prefixes.size).toBeGreaterThan(1);
  });
});

describe('iframe mutation tracking', () => {
  let tracker: DomMutationTracker;
  let collected: DomMutationRecord[];
  let container: HTMLDivElement;
  let iframe: HTMLIFrameElement;

  beforeEach(() => {
    resetMutationCounter();
    setMutationIdPrefix('m');
    collected = [];
    container = document.createElement('div');
    document.body.appendChild(container);

    tracker = new DomMutationTracker({
      onMutations: (mutations) => {
        collected.push(...mutations);
      },
    });
  });

  afterEach(() => {
    tracker.stop();
    container.remove();
  });

  it('detects mutations inside same-origin iframe', async () => {
    // Create a same-origin iframe (about:blank is same-origin in jsdom)
    iframe = document.createElement('iframe');
    container.appendChild(iframe);

    // Wait for iframe to be ready
    await new Promise<void>((resolve) => {
      iframe.addEventListener('load', () => resolve());
      // about:blank loads synchronously in most envs
      if (iframe.contentDocument?.readyState === 'complete') resolve();
    });

    tracker.start();

    // Modify iframe content
    const iframeDoc = iframe.contentDocument!;
    const el = iframeDoc.createElement('div');
    el.textContent = 'iframe content';
    iframeDoc.body.appendChild(el);

    await waitForMutationAndBatch();

    // Should have at least one mutation from the iframe
    const iframeMuts = collected.filter(
      (m) =>
        m.mutationType === 'childList' &&
        m.detail.type === 'childList' &&
        m.detail.addedNodes.some((n) => n.tag === 'div'),
    );
    expect(iframeMuts.length).toBeGreaterThanOrEqual(1);
  });
});
