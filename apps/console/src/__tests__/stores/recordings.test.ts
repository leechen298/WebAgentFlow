import { describe, it, expect, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useRecordingsStore } from '@/stores/recordings';
import * as recordingsApi from '@/api/recordings';
import type { Recording } from '@web-agent-flow/shared-types';

// Mock the API
vi.mock('@/api/recordings');

const mockRecording: Recording = {
  id: 'rec-123',
  name: 'Test Recording',
  source: 'extension',
  status: 'draft',
  events: [],
  meta: {},
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

describe('Recordings Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe('initial state', () => {
    it('should initialize with empty state', () => {
      const store = useRecordingsStore();
      expect(store.recordings).toEqual([]);
      expect(store.currentRecording).toBeNull();
      expect(store.loading).toBe(false);
      expect(store.loadingList).toBe(false);
      expect(store.error).toBeNull();
      expect(store.hasRecordings).toBe(false);
    });
  });

  describe('fetchRecordings', () => {
    it('should fetch recordings and update state', async () => {
      const store = useRecordingsStore();
      const mockGetRecordingsList = vi.mocked(recordingsApi.getRecordingsList);
      mockGetRecordingsList.mockResolvedValue({ items: [mockRecording], has_next: false, next_cursor: null });

      await store.fetchRecordings();

      expect(mockGetRecordingsList).toHaveBeenCalled();
      expect(store.recordings).toEqual([mockRecording]);
      expect(store.hasRecordings).toBe(true);
      expect(store.loadingList).toBe(false);
    });

    it('should handle fetch error', async () => {
      const store = useRecordingsStore();
      const mockGetRecordingsList = vi.mocked(recordingsApi.getRecordingsList);
      mockGetRecordingsList.mockRejectedValue(new Error('Failed to fetch'));

      await expect(store.fetchRecordings()).rejects.toThrow('Failed to fetch');
      expect(store.error).toBe('Failed to fetch');
      expect(store.loadingList).toBe(false);
    });
  });

  describe('fetchRecording', () => {
    it('should fetch a single recording', async () => {
      const store = useRecordingsStore();
      const mockGetRecordingById = vi.mocked(recordingsApi.getRecordingById);
      mockGetRecordingById.mockResolvedValue(mockRecording);

      await store.fetchRecording('rec-123');

      expect(mockGetRecordingById).toHaveBeenCalledWith('rec-123');
      expect(store.currentRecording).toEqual(mockRecording);
      expect(store.loading).toBe(false);
    });
  });

  describe('createRecording', () => {
    it('should create a recording and add to list', async () => {
      const store = useRecordingsStore();
      const mockCreateRecording = vi.mocked(recordingsApi.createRecording);
      const newRecording = { ...mockRecording, id: 'new-123' };
      mockCreateRecording.mockResolvedValue(newRecording);

      const result = await store.createRecording({
        name: 'New Recording',
        source: 'extension',
        events: [],
        meta: {},
      });

      expect(result).toEqual(newRecording);
      expect(store.recordings.length).toBe(1);
      expect(store.recordings[0].id).toBe('new-123');
    });
  });

  describe('updateRecording', () => {
    it('should update recording in list', async () => {
      const store = useRecordingsStore();
      const mockUpdateRecording = vi.mocked(recordingsApi.updateRecording);
      const updated = { ...mockRecording, name: 'Updated' };
      mockUpdateRecording.mockResolvedValue(updated);

      // Pre-populate the store
      store.recordings = [mockRecording];

      const result = await store.updateRecording('rec-123', { name: 'Updated' });

      expect(result).toEqual(updated);
      expect(store.recordings[0].name).toBe('Updated');
    });

    it('should update currentRecording if it matches', async () => {
      const store = useRecordingsStore();
      const mockUpdateRecording = vi.mocked(recordingsApi.updateRecording);
      const updated = { ...mockRecording, name: 'Updated' };
      mockUpdateRecording.mockResolvedValue(updated);

      store.recordings = [mockRecording];
      store.currentRecording = mockRecording;

      await store.updateRecording('rec-123', { name: 'Updated' });

      expect(store.currentRecording?.name).toBe('Updated');
    });
  });

  describe('deleteRecording', () => {
    it('should remove recording from list', async () => {
      const store = useRecordingsStore();
      const mockDeleteRecording = vi.mocked(recordingsApi.deleteRecording);
      mockDeleteRecording.mockResolvedValue({ recording_id: 'rec-123' });

      store.recordings = [mockRecording];

      await store.deleteRecording('rec-123');

      expect(store.recordings).toEqual([]);
    });

    it('should clear currentRecording if it matches', async () => {
      const store = useRecordingsStore();
      const mockDeleteRecording = vi.mocked(recordingsApi.deleteRecording);
      mockDeleteRecording.mockResolvedValue({ recording_id: 'rec-123' });

      store.recordings = [mockRecording];
      store.currentRecording = mockRecording;

      await store.deleteRecording('rec-123');

      expect(store.currentRecording).toBeNull();
    });
  });

  describe('clearCurrent', () => {
    it('should clear currentRecording and error', () => {
      const store = useRecordingsStore();
      store.currentRecording = mockRecording;
      store.error = 'Some error';

      store.clearCurrent();

      expect(store.currentRecording).toBeNull();
      expect(store.error).toBeNull();
    });
  });
});
