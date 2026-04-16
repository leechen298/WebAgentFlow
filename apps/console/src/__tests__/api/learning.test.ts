import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  inferCandidates,
  listFeedbackByRecording,
  upsertFeedback,
} from '@/api/learning';

const { get, post } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  default: { get, post },
}));

describe('Learning API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('posts candidate inference requests', async () => {
    post.mockResolvedValueOnce({ candidate_count: 1 });

    await expect(
      inferCandidates({ recording_id: 'rec-1', score_threshold: 0.5, max_candidates: 10 }),
    ).resolves.toEqual({ candidate_count: 1 });

    expect(post).toHaveBeenCalledWith('/learning/runs/infer-candidates', {
      recording_id: 'rec-1',
      score_threshold: 0.5,
      max_candidates: 10,
    });
  });

  it('posts feedback upserts', async () => {
    post.mockResolvedValueOnce({ id: 'fb-1' });

    await expect(
      upsertFeedback({ recording_id: 'rec-1', element_key: 'button:submit', judgment: 'reasonable' }),
    ).resolves.toEqual({ id: 'fb-1' });

    expect(post).toHaveBeenCalledWith('/learning/feedback/upsert', {
      recording_id: 'rec-1',
      element_key: 'button:submit',
      judgment: 'reasonable',
    });
  });

  it('queries feedback with and without run id', async () => {
    get.mockResolvedValueOnce([{ id: 'fb-1' }]);
    await expect(listFeedbackByRecording('rec-1')).resolves.toEqual([{ id: 'fb-1' }]);
    expect(get).toHaveBeenCalledWith('/learning/feedback/list-by-recording', {
      params: { recording_id: 'rec-1' },
    });

    get.mockResolvedValueOnce([{ id: 'fb-2' }]);
    await expect(listFeedbackByRecording('rec-1', 'run-1')).resolves.toEqual([{ id: 'fb-2' }]);
    expect(get).toHaveBeenLastCalledWith('/learning/feedback/list-by-recording', {
      params: { recording_id: 'rec-1', run_id: 'run-1' },
    });
  });
});
