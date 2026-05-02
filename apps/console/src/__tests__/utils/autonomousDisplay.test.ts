import { describe, it, expect } from 'vitest';
import {
  effectiveStatus,
  effectiveStatusColor,
  verdictColor,
  toScreenshotUrl,
  stepColor,
  bucketLabel,
  groupElementsByBucket,
} from '@/utils/autonomousDisplay';

describe('autonomousDisplay effectiveStatus', () => {
  // Legacy fallback: old persisted rows may still carry a mechanical
  // failure verdict for negative-path scenarios. New API payloads
  // rewrite public verdicts to scenario-relative values, but the helper
  // keeps older rows readable.

  it('scenario matched=true overrides a failure verdict', () => {
    expect(
      effectiveStatus({ verdict: 'failure', scenarioMatched: true }),
    ).toBe('success');
  });

  it('scenario matched=true overrides partial_success', () => {
    expect(
      effectiveStatus({ verdict: 'partial_success', scenarioMatched: true }),
    ).toBe('success');
  });

  it('scenario matched=false flips even a success verdict to failure', () => {
    // If the rubric disagrees with the raw verdict (rare — e.g. the
    // run reported success but violated must_not_transition_to), the
    // mismatch is the authoritative signal.
    expect(
      effectiveStatus({ verdict: 'success', scenarioMatched: false }),
    ).toBe('failure');
  });

  it('falls back to raw verdict when scenario_matched is null', () => {
    // Ad-hoc runs (no spec) don't carry a verdict_check block.
    expect(
      effectiveStatus({ verdict: 'success', scenarioMatched: null }),
    ).toBe('success');
    expect(
      effectiveStatus({ verdict: 'failure', scenarioMatched: null }),
    ).toBe('failure');
    expect(
      effectiveStatus({ verdict: 'partial_success', scenarioMatched: null }),
    ).toBe('partial');
    expect(
      effectiveStatus({ verdict: 'uncertain', scenarioMatched: null }),
    ).toBe('uncertain');
  });

  it('returns null when neither verdict nor scenario_matched is known', () => {
    expect(effectiveStatus({})).toBe(null);
    expect(effectiveStatus({ verdict: null })).toBe(null);
  });

  it('color mapping matches the rubric outcome, not the raw verdict', () => {
    // A run with verdict=failure but matched scenario must get
    // green, not red — that's the whole point of the helper.
    expect(
      effectiveStatusColor(effectiveStatus({ verdict: 'failure', scenarioMatched: true })),
    ).toBe('green');
    expect(
      effectiveStatusColor(effectiveStatus({ verdict: 'success', scenarioMatched: false })),
    ).toBe('red');
    expect(effectiveStatusColor('partial')).toBe('orange');
    expect(effectiveStatusColor('uncertain')).toBe('default');
    expect(effectiveStatusColor(null)).toBe('default');
  });
});

describe('autonomousDisplay verdictColor (unchanged legacy mapping)', () => {
  // Still exported + used by verdict tags. Spec-driven payloads should
  // already be scenario-relative; legacy / ad-hoc payloads may still use
  // the older mechanical vocabulary.
  it('maps the shared OutcomeVerdict vocabulary', () => {
    expect(verdictColor('success')).toBe('green');
    expect(verdictColor('failure')).toBe('red');
    expect(verdictColor('partial_success')).toBe('orange');
    expect(verdictColor('uncertain')).toBe('default');
    expect(verdictColor(null)).toBe('default');
    expect(verdictColor('legacy_other')).toBe('default');
  });
});

describe('passGateStatus path in effectiveStatus', () => {
  it('pass gate returns success', () => {
    expect(effectiveStatus({ passGateStatus: 'pass' })).toBe('success');
  });

  it('fail gate returns failure', () => {
    expect(effectiveStatus({ passGateStatus: 'fail' })).toBe('failure');
  });

  it('unverified gate returns unverified', () => {
    expect(effectiveStatus({ passGateStatus: 'unverified' })).toBe('unverified');
  });

  it('pass gate overrides mismatched scenarioMatched', () => {
    expect(effectiveStatus({ passGateStatus: 'pass', scenarioMatched: false, verdict: 'failure' })).toBe('success');
  });
});

describe('toScreenshotUrl', () => {
  it('returns empty string for null/undefined/empty', () => {
    expect(toScreenshotUrl(null)).toBe('');
    expect(toScreenshotUrl(undefined)).toBe('');
    expect(toScreenshotUrl('')).toBe('');
  });

  it('passes through http URLs unchanged', () => {
    expect(toScreenshotUrl('http://cdn/img.png')).toBe('http://cdn/img.png');
    expect(toScreenshotUrl('https://cdn/img.png')).toBe('https://cdn/img.png');
  });

  it('prepends API base for relative refs', () => {
    const result = toScreenshotUrl('/exploration/screenshots/x.png');
    expect(result).toContain('/exploration/screenshots/x.png');
    expect(result).not.toEqual('/exploration/screenshots/x.png');
  });
});

describe('stepColor', () => {
  it('green for ok=true', () => {
    expect(stepColor({ ok: true })).toBe('green');
  });

  it('red for ok=false', () => {
    expect(stepColor({ ok: false })).toBe('red');
  });

  it('blue for ok=null/undefined', () => {
    expect(stepColor({ ok: null })).toBe('blue');
    expect(stepColor({})).toBe('blue');
  });
});

describe('bucketLabel', () => {
  it('returns translated label for known buckets', () => {
    // "fillable" → "autonomous.countFillable" which should be in en.ts
    const label = bucketLabel('fillable');
    expect(typeof label).toBe('string');
    expect(label.length).toBeGreaterThan(0);
  });

  it('falls back to raw key for unknown buckets', () => {
    expect(bucketLabel('nonexistent_bucket_xyz')).toBe('nonexistent_bucket_xyz');
  });
});

describe('groupElementsByBucket', () => {
  it('returns empty object for null/undefined analysis', () => {
    expect(groupElementsByBucket(null)).toEqual({});
    expect(groupElementsByBucket(undefined)).toEqual({});
  });

  it('groups elements by visible buckets, omitting empty ones', () => {
    const analysis = {
      fillable: [{ id: 'a' }, { id: 'b' }],
      toggle: [{ id: 'c' }],
      submit: [],
      other: [],
      hidden_category: [{ id: 'x' }],
    };
    const grouped = groupElementsByBucket(analysis);
    expect(Object.keys(grouped)).toEqual(['fillable', 'toggle']);
    expect(grouped.fillable).toHaveLength(2);
    expect(grouped.toggle).toHaveLength(1);
    // hidden_category is not in _VISIBLE_BUCKETS
    expect(grouped.hidden_category).toBeUndefined();
  });

  it('preserves bucket order', () => {
    const analysis = {
      other: [{ id: 'o' }],
      fillable: [{ id: 'f' }],
      navigation: [{ id: 'n' }],
    };
    const grouped = groupElementsByBucket(analysis);
    expect(Object.keys(grouped)).toEqual(['fillable', 'navigation', 'other']);
  });
});
