import { createI18n } from 'vue-i18n'
import en from './locales/en'
import zh from './locales/zh'
import ja from './locales/ja'

const SUPPORTED_LOCALES = ['en', 'zh', 'ja'] as const
type SupportedLocale = (typeof SUPPORTED_LOCALES)[number]

function normalizeLocale(raw: string): SupportedLocale {
  const short = raw.split('-')[0].split('_')[0].toLowerCase()
  return SUPPORTED_LOCALES.includes(short as SupportedLocale)
    ? (short as SupportedLocale)
    : 'en'
}

function detectLocale(): SupportedLocale {
  const stored = localStorage.getItem('locale')
  if (stored) return normalizeLocale(stored)
  return normalizeLocale(navigator.language)
}

const i18n = createI18n({
  legacy: false,
  locale: detectLocale(),
  fallbackLocale: 'en',
  messages: { en, zh, ja },
})

export { normalizeLocale, SUPPORTED_LOCALES }
export type { SupportedLocale }
export default i18n
