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
 * Color for a public verdict tag (self-assessment or supervisor).
 *
 * Spec-driven API payloads expose scenario-relative verdicts: a matched
 * negative-path scenario is `success`. Anything outside the known
 * vocabulary falls through to neutral so stale / legacy verdict strings
 * do not get coloured as pass/fail.
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
 * Resolve the "scenario outcome" a human cares about.
 *
 * Prefers the authoritative ``scorecard.pass_gate.status`` computed
 * by the backend — 'pass' / 'fail' / 'unverified'. See
 * apps/api/app/schemas/page_verification.py::PassGate for the product
 * rationale: the gate is strict on purpose so the UI doesn't accumulate
 * "sort-of passed" runs that mask regressions.
 *
 * Legacy inputs without a pass_gate (ad-hoc runs, older persisted
 * rows, workbench SSE before the comparator finishes) fall back to
 * verdict / scenarioMatched logic — that way the status surface is
 * coherent across mid-run states.
 *
 * Returns:
 *   - 'success'     — pass_gate.status === 'pass'
 *   - 'failure'     — pass_gate.status === 'fail', OR legacy
 *                     scenarioMatched=false / verdict=failure
 *   - 'unverified'  — pass_gate.status === 'unverified' (LLM fallback
 *                     or low / medium confidence or partial agreement)
 *   - 'partial'     — legacy verdict=partial_success without a gate
 *   - 'uncertain'   — legacy verdict=uncertain without a gate
 *   - null          — no data (e.g. run failed before evaluation)
 */
export type EffectiveStatus =
  | 'success'
  | 'failure'
  | 'unverified'
  | 'partial'
  | 'uncertain'
  | null;

export function effectiveStatus(ctx: {
  verdict?: string | null;
  scenarioMatched?: boolean | null;
  passGateStatus?: string | null;
}): EffectiveStatus {
  // Authoritative: the backend-computed pass gate drives the UI when
  // it's available.
  const g = ctx.passGateStatus;
  if (g === 'pass') return 'success';
  if (g === 'fail') return 'failure';
  if (g === 'unverified') return 'unverified';

  // Legacy / pre-gate fallback — preserve the earlier scenario-
  // matched-first logic for rows persisted before pass_gate shipped
  // and for mid-stream SSE states.
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
  // unverified + partial both use orange — they're "not a clean pass"
  // signals and the operator should dig in before trusting them.
  if (s === 'unverified') return 'orange';
  if (s === 'partial') return 'orange';
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
