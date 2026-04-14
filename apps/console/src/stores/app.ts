import { defineStore } from 'pinia';
import { ref } from 'vue';
import { getHealth } from '@/api';
import { normalizeLocale } from '@/i18n';
import type { SupportedLocale } from '@/i18n';

export const useAppStore = defineStore('app', () => {
  const apiConnected = ref(false);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const stored = localStorage.getItem('locale');
  const locale = ref<SupportedLocale>(
    stored ? normalizeLocale(stored) : normalizeLocale(navigator.language),
  );

  function setLocale(newLocale: SupportedLocale) {
    locale.value = newLocale;
    localStorage.setItem('locale', newLocale);
  }

  async function checkApiHealth(): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      const health = await getHealth();
      apiConnected.value = health.status === 'ok';
    } catch {
      apiConnected.value = false;
    } finally {
      loading.value = false;
    }
  }

  return {
    apiConnected,
    loading,
    error,
    locale,
    setLocale,
    checkApiHealth,
  };
});
