/**
 * Shared display helpers for the autonomous exploration UI.
 *
 * The workbench (live SSE stream) and the history detail page (saved
 * snapshot) render the same analysis / step / verdict data and
 * previously had their own local copies of these functions. When the
 * vocabulary shifted (e.g. F unifying verdict enum, or adding a new
 * toggle bucket), the two pages could drift apart. Pulling them here
 * keeps both surfaces in sync.
 */

import i18n from '@/i18n';
import { resolveApiConfig } from '@/api/client';

const apiBase = resolveApiConfig().baseURL;

/**
 * Turn a backend screenshot_ref (e.g. ``/exploration/screenshots/x.png``)
 * into a URL the browser can load. In proxy mode we prepend ``/api``;
 * in direct mode we prepend the configured API base.
 */
export function toScreenshotUrl(ref: string | null | undefined): string {
  if (!ref) return '';
  return ref.startsWith('http') ? ref : `${apiBase}${ref}`;
}

/**
 * Color for a step-result tag in the timeline. Neutral blue is the
 * in-progress state — kept so the live-SSE workbench can render a
 * step before ``ok`` is known.
 */
export function stepColor(step: { ok?: boolean | null }): string {
  if (step.ok === true) return 'green';
  if (step.ok === false) return 'red';
  return 'blue';
}

/**
 * Color for a verdict tag (self-assessment or supervisor).
 *
 * Both rule-side and LLM-side now share one OutcomeVerdict vocabulary
 * (success / partial_success / failure / uncertain). Anything outside
 * that set falls through to the neutral default color — keeps the UI
 * from colouring stale / legacy verdict strings as pass/fail.
 */
export function verdictColor(v: string | null | undefined): string {
  if (!v) return 'default';
  if (v === 'success') return 'green';
  if (v === 'failure') return 'red';
  if (v === 'partial_success') return 'orange';
  if (v === 'uncertain') return 'default';
  return 'default';
}

/**
 * Resolve the "scenario outcome" a human cares about, decoupled from
 * the raw rule-side verdict.
 *
 * A negative-path scenario like ``invalid_credentials`` expects
 * ``verdict=failure`` by design (login wall must persist), and
 * surfacing "failure" prominently in the UI makes it look like the
 * scenario regressed when it actually passed. The rubric already
 * computes this reconciliation in ``scorecard.verdict_check.matches_expectation``.
 *
 * Returns:
 *   - 'success'  — scenario matched its declared expectation
 *   - 'failure'  — scenario deviated from expectation
 *   - 'partial'  — rule verdict is partial_success and no scenario
 *                  reconciliation is available
 *   - 'uncertain' — rule verdict is uncertain / unknown
 *   - null       — no verdict and no scenario signal (e.g. run failed
 *                  before any evaluation ran)
 */
export type EffectiveStatus = 'success' | 'failure' | 'partial' | 'uncertain' | null;

export function effectiveStatus(ctx: {
  verdict?: string | null;
  scenarioMatched?: boolean | null;
}): EffectiveStatus {
  if (ctx.scenarioMatched === true) return 'success';
  if (ctx.scenarioMatched === false) return 'failure';
  const v = ctx.verdict;
  if (v === 'success') return 'success';
  if (v === 'failure') return 'failure';
  if (v === 'partial_success') return 'partial';
  if (v === 'uncertain') return 'uncertain';
  return null;
}

export function effectiveStatusColor(s: EffectiveStatus): string {
  if (s === 'success') return 'green';
  if (s === 'failure') return 'red';
  if (s === 'partial') return 'orange';
  return 'default';
}

/**
 * Color for the supervisor's self-reported confidence (high / medium
 * / low). Indicates certainty, not outcome — ``high`` doesn't mean
 * "pass".
 */
export function confidenceColor(c: string | null | undefined): string {
  if (!c) return 'default';
  const v = c.toLowerCase();
  if (v === 'high') return 'blue';
  if (v === 'medium') return 'cyan';
  if (v === 'low') return 'orange';
  return 'default';
}

/**
 * Translate analyzer bucket names (``fillable`` / ``toggle`` / ...)
 * into the operator's UI language via i18n. Falls back to the raw
 * key when an i18n entry is missing so new buckets surface legibly
 * (as the raw key) instead of empty.
 */
export function bucketLabel(name: string): string {
  const key = `autonomous.count${name.charAt(0).toUpperCase()}${name.slice(1)}`;
  const t = i18n.global.t;
  const translated = t(key);
  return translated === key ? name : translated;
}

/**
 * Group the analyzer's elements by visible-bucket into an ordered
 * dict for rendering. Empty buckets are omitted so the UI doesn't
 * show "toggle (0):" headers on pages that have none.
 *
 * Accepts any analysis-shaped payload (both the live workbench's
 * PageAnalysis and the detail page's stored copy).
 */
const _VISIBLE_BUCKETS = [
  'fillable',
  'submit',
  'clickable',
  'navigation',
  'toggle',
  'select',
  'other',
] as const;

export function groupElementsByBucket(
  analysis: Record<string, unknown> | null | undefined,
): Record<string, unknown[]> {
  if (!analysis) return {};
  const g: Record<string, unknown[]> = {};
  for (const cat of _VISIBLE_BUCKETS) {
    const arr = (analysis as Record<string, unknown>)[cat];
    if (Array.isArray(arr) && arr.length > 0) g[cat] = arr;
  }
  return g;
}
