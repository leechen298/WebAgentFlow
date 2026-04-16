import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import apiClient from '@/api/client';
import {
  listTasks,
  getTask,
  runExploration,
  approveRun,
  rejectRun,
} from '@/api/exploration';
import type { RunExplorationParams } from '@/api/exploration';

describe('Exploration API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should have exploration API functions exported', async () => {
    const api = await import('@/api/exploration');
    expect(api.listTasks).toBeDefined();
    expect(api.getTask).toBeDefined();
    expect(api.runExploration).toBeDefined();
    expect(api.approveRun).toBeDefined();
    expect(api.rejectRun).toBeDefined();
  });

  it('listTasks calls GET /exploration/tasks', async () => {
    const mockData = [{ id: 't1', name: 'Task 1' }];
    vi.mocked(apiClient.get).mockResolvedValue(mockData);

    const result = await listTasks();

    expect(apiClient.get).toHaveBeenCalledTimes(1);
    expect(apiClient.get).toHaveBeenCalledWith('/exploration/tasks');
    expect(result).toEqual(mockData);
  });

  it('getTask passes taskId in URL', async () => {
    const mockTask = { id: 'task-abc', name: 'My Task', steps: [] };
    vi.mocked(apiClient.get).mockResolvedValue(mockTask);

    const result = await getTask('task-abc');

    expect(apiClient.get).toHaveBeenCalledTimes(1);
    expect(apiClient.get).toHaveBeenCalledWith('/exploration/tasks/task-abc');
    expect(result).toEqual(mockTask);
  });

  it('runExploration sends correct payload', async () => {
    const mockResponse = { success: true, total_steps: 3, summary: 'done' };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const params: RunExplorationParams = {
      task_id: 'task-123',
      variables: { username: 'test' },
      headless: true,
      max_steps: 10,
    };

    const result = await runExploration(params);

    expect(apiClient.post).toHaveBeenCalledTimes(1);
    expect(apiClient.post).toHaveBeenCalledWith('/exploration/run', params);
    expect(result).toEqual(mockResponse);
  });

  it('approveRun calls correct endpoint with payload', async () => {
    const mockResponse = { status: 'approved' };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await approveRun('run-001', 'Looks good');

    expect(apiClient.post).toHaveBeenCalledTimes(1);
    expect(apiClient.post).toHaveBeenCalledWith(
      '/exploration/runs/run-001/approve',
      { run_id: 'run-001', note: 'Looks good' },
    );
    expect(result).toEqual(mockResponse);
  });

  it('approveRun defaults note to empty string when omitted', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ status: 'approved' });

    await approveRun('run-002');

    expect(apiClient.post).toHaveBeenCalledWith(
      '/exploration/runs/run-002/approve',
      { run_id: 'run-002', note: '' },
    );
  });

  it('rejectRun calls correct endpoint with payload', async () => {
    const mockResponse = { status: 'rejected' };
    vi.mocked(apiClient.post).mockResolvedValue(mockResponse);

    const result = await rejectRun('run-003', 'Needs fixes');

    expect(apiClient.post).toHaveBeenCalledTimes(1);
    expect(apiClient.post).toHaveBeenCalledWith(
      '/exploration/runs/run-003/reject',
      { run_id: 'run-003', note: 'Needs fixes' },
    );
    expect(result).toEqual(mockResponse);
  });

  it('rejectRun defaults note to empty string when omitted', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ status: 'rejected' });

    await rejectRun('run-004');

    expect(apiClient.post).toHaveBeenCalledWith(
      '/exploration/runs/run-004/reject',
      { run_id: 'run-004', note: '' },
    );
  });
});
