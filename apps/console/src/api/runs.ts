import apiClient from './client';
import type { Run, RunCreate, RunUpdate, DeleteResponse, CursorPage } from '@web-agent-flow/shared-types';

export async function getRunsList(params?: { limit?: number; cursor?: string }): Promise<CursorPage<Run>> {
  return await apiClient.get('/runs/list', { params }) as unknown as CursorPage<Run>;
}

export async function getRunById(runId: string): Promise<Run> {
  return await apiClient.get('/runs/get', {
    params: { run_id: runId }
  }) as unknown as Run;
}

export async function createRun(payload: RunCreate): Promise<Run> {
  return await apiClient.post('/runs/create', payload) as unknown as Run;
}

export async function updateRun(runId: string, updateData: RunUpdate): Promise<Run> {
  return await apiClient.post('/runs/update', {
    run_id: runId,
    update_data: updateData
  }) as unknown as Run;
}

export async function deleteRun(runId: string): Promise<DeleteResponse> {
  return await apiClient.post('/runs/delete', {
    run_id: runId
  }) as unknown as DeleteResponse;
}
