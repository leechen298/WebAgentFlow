import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';

const api = vi.hoisted(() => ({
  getRecordingsList: vi.fn(),
  getRecordingById: vi.fn(),
  createRecording: vi.fn(),
  updateRecording: vi.fn(),
  deleteRecording: vi.fn(),
  getSkillsList: vi.fn(),
  getSkillById: vi.fn(),
  createSkill: vi.fn(),
  updateSkill: vi.fn(),
  deleteSkill: vi.fn(),
  getRunsList: vi.fn(),
  getRunById: vi.fn(),
  createRun: vi.fn(),
  updateRun: vi.fn(),
  deleteRun: vi.fn(),
}));

vi.mock('@/api', () => api);

describe('resource stores', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('covers recordings store list, paging, CRUD, and errors', async () => {
    const { useRecordingsStore } = await import('@/stores/recordings');
    const store = useRecordingsStore();
    const rec = { id: 'rec-1', name: 'Recording 1' } as any;

    api.getRecordingsList
      .mockResolvedValueOnce({ items: [rec], has_next: true, next_cursor: 'c2' })
      .mockResolvedValueOnce({ items: [rec], has_next: false, next_cursor: null })
      .mockResolvedValueOnce({ items: [rec], has_next: false, next_cursor: null });
    api.getRecordingById.mockResolvedValue(rec);
    api.createRecording.mockResolvedValue(rec);
    api.updateRecording.mockResolvedValue({ ...rec, name: 'Updated' });

    expect(store.hasPrev).toBe(false);
    expect(store.hasRecordings).toBe(false);

    await store.fetchFirstPage();
    expect(store.recordings).toHaveLength(1);
    expect(store.hasNext).toBe(true);
    expect(store.hasRecordings).toBe(true);

    await store.fetchNextPage();
    expect(store.hasPrev).toBe(true);
    await store.fetchPrevPage();
    expect(api.getRecordingsList).toHaveBeenCalledTimes(3);

    await store.fetchRecording('rec-1');
    expect(store.currentRecording?.id).toBe('rec-1');

    await store.createRecording({ name: 'new' } as any);
    expect(store.recordings).toHaveLength(2);

    await store.updateRecording('rec-1', { name: 'Updated' } as any);
    expect(store.currentRecording?.name).toBe('Updated');

    await store.deleteRecording('rec-1');
    expect(store.currentRecording).toBeNull();

    store.clearCurrent();
    expect(store.error).toBeNull();

    api.getRecordingsList.mockRejectedValueOnce(new Error('list failed'));
    await expect(store.fetchRecordings()).rejects.toThrow('list failed');
    expect(store.error).toBe('list failed');

    api.getRecordingById.mockRejectedValueOnce(new Error('get failed'));
    await expect(store.fetchRecording('bad')).rejects.toThrow('get failed');
    expect(store.error).toBe('get failed');

    api.createRecording.mockRejectedValueOnce(new Error('create failed'));
    await expect(store.createRecording({} as any)).rejects.toThrow('create failed');

    api.updateRecording.mockRejectedValueOnce(new Error('update failed'));
    await expect(store.updateRecording('x', {} as any)).rejects.toThrow('update failed');

    api.deleteRecording.mockRejectedValueOnce(new Error('delete failed'));
    await expect(store.deleteRecording('x')).rejects.toThrow('delete failed');
  });

  it('covers skills store list, paging, CRUD, and errors', async () => {
    const { useSkillsStore } = await import('@/stores/skills');
    const store = useSkillsStore();
    const skill = { id: 'skill-1', name: 'Skill 1' } as any;

    api.getSkillsList
      .mockResolvedValueOnce({ items: [skill], has_next: true, next_cursor: 'c2' })
      .mockResolvedValueOnce({ items: [skill], has_next: false, next_cursor: null })
      .mockResolvedValueOnce({ items: [skill], has_next: false, next_cursor: null });
    api.getSkillById.mockResolvedValue(skill);
    api.createSkill.mockResolvedValue(skill);
    api.updateSkill.mockResolvedValue({ ...skill, name: 'Updated Skill' });

    await store.fetchFirstPage();
    await store.fetchNextPage();
    await store.fetchPrevPage();
    await store.fetchSkill('skill-1');
    expect(store.currentSkill?.id).toBe('skill-1');

    await store.createSkill({} as any);
    await store.updateSkill('skill-1', {} as any);
    expect(store.currentSkill?.name).toBe('Updated Skill');
    await store.deleteSkill('skill-1');
    expect(store.currentSkill).toBeNull();
    store.clearCurrent();

    api.getSkillsList.mockRejectedValueOnce(new Error('list failed'));
    await expect(store.fetchSkills()).rejects.toThrow('list failed');
    api.getSkillById.mockRejectedValueOnce(new Error('get failed'));
    await expect(store.fetchSkill('bad')).rejects.toThrow('get failed');
    api.createSkill.mockRejectedValueOnce(new Error('create failed'));
    await expect(store.createSkill({} as any)).rejects.toThrow('create failed');
    api.updateSkill.mockRejectedValueOnce(new Error('update failed'));
    await expect(store.updateSkill('x', {} as any)).rejects.toThrow('update failed');
    api.deleteSkill.mockRejectedValueOnce(new Error('delete failed'));
    await expect(store.deleteSkill('x')).rejects.toThrow('delete failed');
  });

  it('covers runs store list, paging, CRUD, and errors', async () => {
    const { useRunsStore } = await import('@/stores/runs');
    const store = useRunsStore();
    const run = { id: 'run-1', status: 'pending' } as any;

    api.getRunsList
      .mockResolvedValueOnce({ items: [run], has_next: true, next_cursor: 'c2' })
      .mockResolvedValueOnce({ items: [run], has_next: false, next_cursor: null })
      .mockResolvedValueOnce({ items: [run], has_next: false, next_cursor: null });
    api.getRunById.mockResolvedValue(run);
    api.createRun.mockResolvedValue(run);
    api.updateRun.mockResolvedValue({ ...run, status: 'succeeded' });

    await store.fetchFirstPage();
    await store.fetchNextPage();
    await store.fetchPrevPage();
    await store.fetchRun('run-1');
    expect(store.currentRun?.id).toBe('run-1');

    await store.createRun({} as any);
    await store.updateRun('run-1', {} as any);
    expect(store.currentRun?.status).toBe('succeeded');
    await store.deleteRun('run-1');
    expect(store.currentRun).toBeNull();
    store.clearCurrent();

    api.getRunsList.mockRejectedValueOnce(new Error('list failed'));
    await expect(store.fetchRuns()).rejects.toThrow('list failed');
    api.getRunById.mockRejectedValueOnce(new Error('get failed'));
    await expect(store.fetchRun('bad')).rejects.toThrow('get failed');
    api.createRun.mockRejectedValueOnce(new Error('create failed'));
    await expect(store.createRun({} as any)).rejects.toThrow('create failed');
    api.updateRun.mockRejectedValueOnce(new Error('update failed'));
    await expect(store.updateRun('x', {} as any)).rejects.toThrow('update failed');
    api.deleteRun.mockRejectedValueOnce(new Error('delete failed'));
    await expect(store.deleteRun('x')).rejects.toThrow('delete failed');
  });
});
