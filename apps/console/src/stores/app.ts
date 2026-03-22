import { defineStore } from 'pinia';
import { ref } from 'vue';
import { getHealth } from '@/api';
import type { HealthStatus } from '@/api';

export const useAppStore = defineStore('app', () => {
  const apiConnected = ref(false);
  const loading = ref(false);
  const error = ref<string | null>(null);

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
    checkApiHealth
  };
});
