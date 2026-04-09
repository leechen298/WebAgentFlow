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

  // Pagination state
  const hasNext = ref(false);
  const nextCursor = ref<string | null>(null);
  const cursorStack = ref<string[]>([]);
  const hasPrev = computed(() => cursorStack.value.length > 0);

  // Getters
  const hasRuns = computed(() => runs.value.length > 0);

  // Actions
  async function fetchRuns(cursor?: string): Promise<void> {
    loadingList.value = true;
    error.value = null;
    try {
      const page = await getRunsList({ cursor });
      runs.value = page.items;
      hasNext.value = page.has_next;
      nextCursor.value = page.next_cursor;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch runs';
      throw e;
    } finally {
      loadingList.value = false;
    }
  }

  async function fetchNextPage(): Promise<void> {
    if (!hasNext.value || !nextCursor.value) return;
    cursorStack.value.push(nextCursor.value);
    await fetchRuns(nextCursor.value);
  }

  async function fetchPrevPage(): Promise<void> {
    if (cursorStack.value.length === 0) return;
    cursorStack.value.pop();
    const prevCursor = cursorStack.value.length > 0 ? cursorStack.value[cursorStack.value.length - 1] : undefined;
    await fetchRuns(prevCursor);
  }

  async function fetchFirstPage(): Promise<void> {
    cursorStack.value = [];
    await fetchRuns();
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
    // Pagination
    hasNext,
    hasPrev,
    // Getters
    hasRuns,
    // Actions
    fetchRuns,
    fetchNextPage,
    fetchPrevPage,
    fetchFirstPage,
    fetchRun,
    createRun,
    updateRun,
    deleteRun,
    clearCurrent
  };
});
