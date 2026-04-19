import { createI18n } from 'vue-i18n';
import en from './locales/en';
import zh from './locales/zh';
import ja from './locales/ja';

const SUPPORTED_LOCALES = ['en', 'zh', 'ja'] as const;
export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number];

export const LOCALE_LABELS: Record<SupportedLocale, string> = {
  en: 'English',
  zh: '中文',
  ja: '日本語',
};

function normalizeLocale(raw: string): SupportedLocale {
  const short = raw.split('-')[0].split('_')[0].toLowerCase();
  return SUPPORTED_LOCALES.includes(short as SupportedLocale)
    ? (short as SupportedLocale)
    : 'en';
}

function detectLocale(): SupportedLocale {
  // Playwright-driven autonomous runs will see an empty localStorage
  // and fall back to navigator.language, which in headless Chromium is
  // en-US — this keeps specs that assert on English DOM content stable
  // regardless of what human locale the operator has set in their
  // real browser.
  const stored = typeof localStorage !== 'undefined'
    ? localStorage.getItem('validation_locale')
    : null;
  if (stored) return normalizeLocale(stored);
  if (typeof navigator !== 'undefined') return normalizeLocale(navigator.language);
  return 'en';
}

const i18n = createI18n({
  legacy: false,
  locale: detectLocale(),
  fallbackLocale: 'en',
  messages: { en, zh, ja },
});

export { SUPPORTED_LOCALES };
export default i18n;
