import { describe, it, expect } from 'vitest';
import {
  effectiveStatus,
  effectiveStatusColor,
  verdictColor,
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
