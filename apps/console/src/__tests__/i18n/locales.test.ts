import { describe, expect, it } from 'vitest';
import en from '@/i18n/locales/en';
import zh from '@/i18n/locales/zh';
import ja from '@/i18n/locales/ja';

describe('locale bundles', () => {
  it('load all locale dictionaries with the expected top-level sections', () => {
    for (const locale of [en, zh, ja]) {
      expect(locale).toHaveProperty('nav');
      expect(locale).toHaveProperty('common');
      expect(locale).toHaveProperty('home');
      expect(locale).toHaveProperty('recordings');
      expect(locale).toHaveProperty('skills');
      expect(locale).toHaveProperty('runs');
      expect(locale).toHaveProperty('exploration');
      expect(locale).toHaveProperty('learning');
    }
  });

  it('keeps critical navigation and action keys aligned across locales', () => {
    expect(zh.nav.recordings).toBeTruthy();
    expect(ja.nav.recordings).toBeTruthy();
    expect(en.common.save).toBeTruthy();
    expect(zh.common.save).toBeTruthy();
    expect(ja.common.save).toBeTruthy();
  });
});
