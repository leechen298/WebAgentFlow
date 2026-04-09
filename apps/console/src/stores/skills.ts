import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import {
  getSkillsList,
  getSkillById,
  createSkill as apiCreateSkill,
  updateSkill as apiUpdateSkill,
  deleteSkill as apiDeleteSkill
} from '@/api';
import type { Skill, SkillCreate, SkillUpdate } from '@web-agent-flow/shared-types';

export const useSkillsStore = defineStore('skills', () => {
  // State
  const skills = ref<Skill[]>([]);
  const currentSkill = ref<Skill | null>(null);
  const loading = ref(false);
  const loadingList = ref(false);
  const error = ref<string | null>(null);

  // Pagination state
  const hasNext = ref(false);
  const nextCursor = ref<string | null>(null);
  const cursorStack = ref<string[]>([]);
  const hasPrev = computed(() => cursorStack.value.length > 0);

  // Getters
  const hasSkills = computed(() => skills.value.length > 0);

  // Actions
  async function fetchSkills(cursor?: string): Promise<void> {
    loadingList.value = true;
    error.value = null;
    try {
      const page = await getSkillsList({ cursor });
      skills.value = page.items;
      hasNext.value = page.has_next;
      nextCursor.value = page.next_cursor;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch skills';
      throw e;
    } finally {
      loadingList.value = false;
    }
  }

  async function fetchNextPage(): Promise<void> {
    if (!hasNext.value || !nextCursor.value) return;
    cursorStack.value.push(nextCursor.value);
    await fetchSkills(nextCursor.value);
  }

  async function fetchPrevPage(): Promise<void> {
    if (cursorStack.value.length === 0) return;
    cursorStack.value.pop();
    const prevCursor = cursorStack.value.length > 0 ? cursorStack.value[cursorStack.value.length - 1] : undefined;
    await fetchSkills(prevCursor);
  }

  async function fetchFirstPage(): Promise<void> {
    cursorStack.value = [];
    await fetchSkills();
  }

  async function fetchSkill(id: string): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      currentSkill.value = await getSkillById(id);
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch skill';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function createSkill(payload: SkillCreate): Promise<Skill> {
    loading.value = true;
    error.value = null;
    try {
      const newSkill = await apiCreateSkill(payload);
      skills.value.push(newSkill);
      return newSkill;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create skill';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function updateSkill(id: string, payload: SkillUpdate): Promise<Skill> {
    loading.value = true;
    error.value = null;
    try {
      const updated = await apiUpdateSkill(id, payload);
      const index = skills.value.findIndex(s => s.id === id);
      if (index !== -1) {
        skills.value[index] = updated;
      }
      if (currentSkill.value?.id === id) {
        currentSkill.value = updated;
      }
      return updated;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update skill';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function deleteSkill(id: string): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      await apiDeleteSkill(id);
      skills.value = skills.value.filter(s => s.id !== id);
      if (currentSkill.value?.id === id) {
        currentSkill.value = null;
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete skill';
      throw e;
    } finally {
      loading.value = false;
    }
  }

  function clearCurrent(): void {
    currentSkill.value = null;
    error.value = null;
  }

  return {
    // State
    skills,
    currentSkill,
    loading,
    loadingList,
    error,
    // Pagination
    hasNext,
    hasPrev,
    // Getters
    hasSkills,
    // Actions
    fetchSkills,
    fetchNextPage,
    fetchPrevPage,
    fetchFirstPage,
    fetchSkill,
    createSkill,
    updateSkill,
    deleteSkill,
    clearCurrent
  };
});
