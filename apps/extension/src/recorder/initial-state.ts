/**
 * Initial State Sampler — orchestrator module.
 *
 * Captures form field default values and page state at recording start.
 * Delegates to specialized scanner modules for actual DOM traversal.
 *
 * Three-layer strategy:
 *   Layer 1 — Generic DOM rules (works on ANY page)
 *   Layer 2 — Container-enhanced (UI library pages, any library)
 *   Layer 3 — Merge & deduplicate
 */

import type { InitialFieldSnapshot, PageInitialState } from '@web-agent-flow/shared-types';
import { getCanonicalPageUrl } from './page-url';
import {
  scanContainers,
  scanGenericControls,
  scanStructuredTables,
  scanStructuredLists,
  scanPaginationControls,
  scanActiveTabs,
  scanActiveSteps,
  scanBreadcrumbs,
  scanDescriptions,
  scanOpenDialogs,
} from './initial-state-scanners';
import { captureSimplifiedHTML } from './html-snapshot';

const MAX_FIELDS = 80;

// ─── Scoring & deduplication ────────────────────────────────────────────────

function snapshotScore(snapshot: InitialFieldSnapshot): number {
  let score = 0;
  if (snapshot.fieldLabel) score += 2;
  if (snapshot.fieldPath && snapshot.fieldPath !== snapshot.fieldLabel) score += 2;
  if (snapshot.sectionLabel) score += 1;
  if (snapshot.fieldProp) score += 1;
  if (snapshot.fieldType && snapshot.fieldType !== 'unknown') score += 1;
  if (snapshot.required) score += 1;
  if (snapshot.itemCount) score += 2;
  if (snapshot.defaultValueHtml) score += 2;
  if (snapshot.defaultValueText) {
    score += Math.min(6, Math.ceil(snapshot.defaultValueText.length / 30));
  }
  if (snapshot.placeholder) score += 1;
  return score;
}

function mergeSnapshots(snapshots: InitialFieldSnapshot[]): InitialFieldSnapshot[] {
  const deduped = new Map<string, InitialFieldSnapshot>();

  for (const snapshot of snapshots) {
    const key = [
      snapshot.fieldPath ?? '',
      snapshot.fieldLabel ?? '',
      snapshot.fieldProp ?? '',
    ].join('|');

    const existing = deduped.get(key);
    if (!existing || snapshotScore(snapshot) > snapshotScore(existing)) {
      deduped.set(key, snapshot);
    }
  }

  return Array.from(deduped.values());
}

// ─── Public API ─────────────────────────────────────────────────────────────

/**
 * Capture the initial state of the current page.
 *
 * Strategy:
 *   1. Scan recognized UI containers (Layer 2) — richer context
 *   2. Scan structural elements (tables, lists, pagination, tabs, etc.)
 *   3. Scan standalone form controls not inside containers (Layer 1)
 *   4. Capture simplified HTML snapshot as fallback
 *   5. Merge: container results first, then structured, then standalone
 */
export function captureInitialState(): PageInitialState {
  // Layer 2 — containers provide richer data and mark covered elements
  const { snapshots: containerFields, coveredElements } = scanContainers();

  // Layer 2.5 — structural elements
  const structuredFields = [
    ...scanStructuredTables(),
    ...scanStructuredLists(),
    ...scanPaginationControls(),
    ...scanActiveTabs(),
    ...scanActiveSteps(),
    ...scanBreadcrumbs(),
    ...scanDescriptions(),
    ...scanOpenDialogs(),
  ];

  // Layer 1 — standalone controls not already covered
  const { snapshots: standaloneFields } =
    containerFields.length + structuredFields.length < MAX_FIELDS
      ? scanGenericControls(coveredElements)
      : { snapshots: [], coveredElements: new Set<Element>() };

  const fields = mergeSnapshots([
    ...containerFields,
    ...structuredFields,
    ...standaloneFields,
  ]).slice(0, MAX_FIELDS);

  // Capture simplified HTML snapshot
  let htmlSnapshot: string | undefined;
  try {
    htmlSnapshot = captureSimplifiedHTML();
  } catch { /* degrade gracefully */ }

  return {
    capturedAt: Date.now(),
    pageUrl: getCanonicalPageUrl(location.href),
    pageTitle: document.title,
    fields,
    ...(htmlSnapshot ? { htmlSnapshot } : {}),
  };
}
