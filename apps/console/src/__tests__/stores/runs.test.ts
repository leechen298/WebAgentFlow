import { describe, it, expect, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useRunsStore } from '@/stores/runs';
import * as runsApi from '@/api/runs';
import type { Run } from '@web-agent-flow/shared-types';

// Mock the API
vi.mock('@/api/runs');

const mockRun: Run = {
  id: 'run-123',
  name: 'Test Run',
  status: 'pending',
  recording_id: 'rec-123',
  skill_id: 'skill-123',
  config: {},
  result: null,
  started_at: null,
  completed_at: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

describe('Runs Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('should initialize with default state', () => {
    const store = useRunsStore();
    expect(store.runs).toEqual([]);
    expect(store.currentRun).toBeNull();
    expect(store.loading).toBe(false);
    expect(store.loadingList).toBe(false);
    expect(store.error).toBeNull();
    expect(store.hasRuns).toBe(false);
  });

  it('should fetch runs successfully', async () => {
    const store = useRunsStore();
    const mockGetRunsList = vi.mocked(runsApi.getRunsList);
    mockGetRunsList.mockResolvedValue([mockRun]);

    await store.fetchRuns();

    expect(store.runs).toEqual([mockRun]);
    expect(store.hasRuns).toBe(true);
  });

  it('should fetch a single run', async () => {
    const store = useRunsStore();
    const mockGetRunById = vi.mocked(runsApi.getRunById);
    mockGetRunById.mockResolvedValue(mockRun);

    await store.fetchRun('run-123');

    expect(store.currentRun).toEqual(mockRun);
  });

  it('should create a run and add to list', async () => {
    const store = useRunsStore();
    const mockCreateRun = vi.mocked(runsApi.createRun);
    const newRun = { ...mockRun, id: 'new-123' };
    mockCreateRun.mockResolvedValue(newRun);

    const result = await store.createRun({
      name: 'New Run',
      recording_id: 'rec-123',
      skill_id: 'skill-123',
      config: {},
    });

    expect(result).toEqual(newRun);
    expect(store.runs.length).toBe(1);
    expect(store.runs[0].id).toBe('new-123');
  });

  it('should update a run', async () => {
    const store = useRunsStore();
    const mockUpdateRun = vi.mocked(runsApi.updateRun);
    const updated = { ...mockRun, status: 'running' };
    mockUpdateRun.mockResolvedValue(updated);

    store.runs = [mockRun];

    const result = await store.updateRun('run-123', { status: 'running' });

    expect(result).toEqual(updated);
    expect(store.runs[0].status).toBe('running');
  });

  it('should delete a run', async () => {
    const store = useRunsStore();
    const mockDeleteRun = vi.mocked(runsApi.deleteRun);
    mockDeleteRun.mockResolvedValue({ run_id: 'run-123' });

    store.runs = [mockRun];

    await store.deleteRun('run-123');

    expect(store.runs).toEqual([]);
  });

  it('should clear current run', () => {
    const store = useRunsStore();
    store.currentRun = mockRun;
    store.error = 'Some error';

    store.clearCurrent();

    expect(store.currentRun).toBeNull();
    expect(store.error).toBeNull();
  });
});
