import apiClient from './client';
import type { Recording, RecordingCreate, RecordingUpdate, DeleteResponse, NormalizedRecording, CursorPage } from '@web-agent-flow/shared-types';

export async function getRecordingsList(params?: { limit?: number; cursor?: string }): Promise<CursorPage<Recording>> {
  return await apiClient.get('/recordings/list', { params }) as unknown as CursorPage<Recording>;
}

export async function getRecordingById(recordingId: string): Promise<Recording> {
  return await apiClient.get('/recordings/get', {
    params: { recording_id: recordingId }
  }) as unknown as Recording;
}

export async function createRecording(payload: RecordingCreate): Promise<Recording> {
  return await apiClient.post('/recordings/create', payload) as unknown as Recording;
}

export async function updateRecording(recordingId: string, updateData: RecordingUpdate): Promise<Recording> {
  return await apiClient.post('/recordings/update', {
    recording_id: recordingId,
    update_data: updateData
  }) as unknown as Recording;
}

export async function deleteRecording(recordingId: string): Promise<DeleteResponse> {
  return await apiClient.post('/recordings/delete', {
    recording_id: recordingId
  }) as unknown as DeleteResponse;
}

export async function getNormalizedRecording(recordingId: string): Promise<NormalizedRecording> {
  return await apiClient.get('/recordings/get_normalized', {
    params: { recording_id: recordingId }
  }) as unknown as NormalizedRecording;
}
