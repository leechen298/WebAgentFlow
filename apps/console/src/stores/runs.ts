import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import {
  getRunsList,
  getRunById,
  createRun as apiCreateRun,
  updateRun as apiUpdateRun,
  deleteRun as apiDeleteRun
} from '@/api';
import type { Run, RunCreate, RunUpdate } from '@web-agent-flow/shared-types';

export const useRunsStore = defineStore('runs', () => {
  // State
  const runs = ref<Run[]>([]);
  const currentRun = ref<Run | null>(null);
  const loading = ref(false);
  const loadingList = ref(false);
  const error = ref<string | null>(null);

  // Getters
  const hasRuns = computed(() => runs.value.length > 0);

  // Actions
  async function fetchRuns(): Promise<void> {
    loadingList.value = true;
    error.value = null;
    try {
      runs.value = await getRunsList();
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch runs';
      throw e;
    } finally {
      loadingList.value = false;
    }
  }

  async function fetchRun(id: string): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      currentRun.value = await getRunById(id);
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch run';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function createRun(payload: RunCreate): Promise<Run> {
    loading.value = true;
    error.value = null;
    try {
      const newRun = await apiCreateRun(payload);
      runs.value.push(newRun);
      return newRun;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create run';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function updateRun(id: string, payload: RunUpdate): Promise<Run> {
    loading.value = true;
    error.value = null;
    try {
      const updated = await apiUpdateRun(id, payload);
      const index = runs.value.findIndex(r => r.id === id);
      if (index !== -1) {
        runs.value[index] = updated;
      }
      if (currentRun.value?.id === id) {
        currentRun.value = updated;
      }
      return updated;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update run';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function deleteRun(id: string): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      await apiDeleteRun(id);
      runs.value = runs.value.filter(r => r.id !== id);
      if (currentRun.value?.id === id) {
        currentRun.value = null;
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete run';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  function clearCurrent(): void {
    currentRun.value = null;
    error.value = null;
  }

  return {
    // State
    runs,
    currentRun,
    loading,
    loadingList,
    error,
    // Getters
    hasRuns,
    // Actions
    fetchRuns,
    fetchRun,
    createRun,
    updateRun,
    deleteRun,
    clearCurrent
  };
});
