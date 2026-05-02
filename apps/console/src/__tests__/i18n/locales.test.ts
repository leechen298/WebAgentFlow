import { describe, expect, it } from 'vitest';
import en from '@/i18n/locales/en';
import zh from '@/i18n/locales/zh';
import ja from '@/i18n/locales/ja';

function collectLeafPaths(
  value: Record<string, unknown>,
  prefix = '',
  out: string[] = [],
): string[] {
  for (const [key, child] of Object.entries(value)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (child && typeof child === 'object' && !Array.isArray(child)) {
      collectLeafPaths(child as Record<string, unknown>, path, out);
    } else {
      out.push(path);
    }
  }
  return out;
}

function readLeafValues(value: Record<string, unknown>): string[] {
  const leaves: string[] = [];
  for (const path of collectLeafPaths(value)) {
    const resolved = path.split('.').reduce<unknown>((acc, key) => {
      return acc && typeof acc === 'object' ? (acc as Record<string, unknown>)[key] : undefined;
    }, value);
    leaves.push(String(resolved ?? ''));
  }
  return leaves;
}

describe('locale bundles', () => {
  it('load all locale dictionaries with the expected top-level sections', () => {
    for (const locale of [en, zh, ja]) {
      expect(locale).toHaveProperty('nav');
      expect(locale).toHaveProperty('common');
      expect(locale).toHaveProperty('home');
      expect(locale).toHaveProperty('autonomous');
      expect(locale).toHaveProperty('autonomousHistory');
      expect(locale).toHaveProperty('learnedPaths');
    }
  });

  it('keeps critical navigation and action keys aligned across locales', () => {
    expect(zh.nav.overview).toBeTruthy();
    expect(ja.nav.overview).toBeTruthy();
    expect(zh.nav.autonomousExploration).toBeTruthy();
    expect(ja.nav.autonomousExploration).toBeTruthy();
    expect(en.common.save).toBeTruthy();
    expect(zh.common.save).toBeTruthy();
    expect(ja.common.save).toBeTruthy();
  });

  it('keeps the full locale key structure aligned across languages', () => {
    const enPaths = collectLeafPaths(en);
    const zhPaths = collectLeafPaths(zh);
    const jaPaths = collectLeafPaths(ja);

    expect(zhPaths).toEqual(enPaths);
    expect(jaPaths).toEqual(enPaths);
    expect(enPaths.length).toBeGreaterThan(100);
  });

  it('can read every locale leaf value as a non-empty string', () => {
    for (const locale of [en, zh, ja]) {
      const leaves = readLeafValues(locale);
      expect(leaves.length).toBeGreaterThan(100);
      expect(leaves.every((value) => value.length > 0)).toBe(true);
    }
  });
});
