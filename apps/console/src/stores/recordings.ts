import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import {
  getRecordingsList,
  getRecordingById,
  createRecording as apiCreateRecording,
  updateRecording as apiUpdateRecording,
  deleteRecording as apiDeleteRecording
} from '@/api';
import type { Recording, RecordingCreate, RecordingUpdate } from '@web-agent-flow/shared-types';

export const useRecordingsStore = defineStore('recordings', () => {
  // State
  const recordings = ref<Recording[]>([]);
  const currentRecording = ref<Recording | null>(null);
  const loading = ref(false);
  const loadingList = ref(false);
  const error = ref<string | null>(null);

  // Pagination state
  const hasNext = ref(false);
  const nextCursor = ref<string | null>(null);
  const cursorStack = ref<string[]>([]);
  const hasPrev = computed(() => cursorStack.value.length > 0);

  // Getters
  const hasRecordings = computed(() => recordings.value.length > 0);

  // Actions
  async function fetchRecordings(cursor?: string): Promise<void> {
    loadingList.value = true;
    error.value = null;
    try {
      const page = await getRecordingsList({ cursor });
      recordings.value = page.items;
      hasNext.value = page.has_next;
      nextCursor.value = page.next_cursor;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch recordings';
      throw e;
    } finally {
      loadingList.value = false;
    }
  }

  async function fetchNextPage(): Promise<void> {
    if (!hasNext.value || !nextCursor.value) return;
    cursorStack.value.push(nextCursor.value);
    await fetchRecordings(nextCursor.value);
  }

  async function fetchPrevPage(): Promise<void> {
    if (cursorStack.value.length === 0) return;
    cursorStack.value.pop();
    const prevCursor = cursorStack.value.length > 0 ? cursorStack.value[cursorStack.value.length - 1] : undefined;
    await fetchRecordings(prevCursor);
  }

  async function fetchFirstPage(): Promise<void> {
    cursorStack.value = [];
    await fetchRecordings();
  }

  async function fetchRecording(id: string): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      currentRecording.value = await getRecordingById(id);
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch recording';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function createRecording(payload: RecordingCreate): Promise<Recording> {
    loading.value = true;
    error.value = null;
    try {
      const newRecording = await apiCreateRecording(payload);
      recordings.value.push(newRecording);
      return newRecording;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create recording';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function updateRecording(id: string, payload: RecordingUpdate): Promise<Recording> {
    loading.value = true;
    error.value = null;
    try {
      const updated = await apiUpdateRecording(id, payload);
      const index = recordings.value.findIndex(r => r.id === id);
      if (index !== -1) {
        recordings.value[index] = updated;
      }
      if (currentRecording.value?.id === id) {
        currentRecording.value = updated;
      }
      return updated;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update recording';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function deleteRecording(id: string): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      await apiDeleteRecording(id);
      recordings.value = recordings.value.filter(r => r.id !== id);
      if (currentRecording.value?.id === id) {
        currentRecording.value = null;
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete recording';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  function clearCurrent(): void {
    currentRecording.value = null;
    error.value = null;
  }

  return {
    // State
    recordings,
    currentRecording,
    loading,
    loadingList,
    error,
    // Pagination
    hasNext,
    hasPrev,
    // Getters
    hasRecordings,
    // Actions
    fetchRecordings,
    fetchNextPage,
    fetchPrevPage,
    fetchFirstPage,
    fetchRecording,
    createRecording,
    updateRecording,
    deleteRecording,
    clearCurrent
  };
});
