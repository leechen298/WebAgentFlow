import { beforeEach, describe, expect, it, vi } from 'vitest';
import { generateRecordingName, prepareRecordingData, submitRecording } from '../recorder/submit';

const { post } = vi.hoisted(() => ({
  post: vi.fn(),
}));

vi.mock('../utils/api', () => ({
  createApiClient: vi.fn().mockResolvedValue({ post }),
}));

describe('recording submission helpers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('prepares recording payload with metadata and optional sections', () => {
    const payload = prepareRecordingData({
      name: 'Test Recording',
      events: [{ id: 'e0', type: 'click', timestamp: 1, url: 'https://example.com' }],
      initialUrl: 'https://example.com',
      initialTitle: 'Example',
      startTime: 100,
      initialState: { pageUrl: 'https://example.com', pageTitle: 'Example', capturedAt: 101, stateTree: [] },
      domMutations: [{ type: 'attributes' } as never],
    });

    expect(payload).toMatchObject({
      name: 'Test Recording',
      status: 'completed',
      source: 'extension',
      events: [{ id: 'e0' }],
    });
    expect(payload.meta).toMatchObject({
      initialUrl: 'https://example.com',
      initialTitle: 'Example',
      eventCount: 1,
    });
  });

  it('submits payload through the API client', async () => {
    post.mockResolvedValueOnce({ id: 'rec-1' });

    await expect(
      submitRecording({
        name: 'Test Recording',
        events: [],
        initialUrl: null,
        initialTitle: null,
        startTime: null,
      }),
    ).resolves.toEqual({ id: 'rec-1' });

    expect(post).toHaveBeenCalledWith('/recordings/create', expect.objectContaining({ name: 'Test Recording' }));
  });

  it('rethrows submission failures', async () => {
    post.mockRejectedValueOnce(new Error('boom'));

    await expect(
      submitRecording({
        name: 'Broken Recording',
        events: [],
        initialUrl: null,
        initialTitle: null,
        startTime: null,
      }),
    ).rejects.toThrow('boom');
  });

  it('generates readable recording names with and without a valid url', () => {
    expect(generateRecordingName('https://example.com/page')).toContain('example.com');
    expect(generateRecordingName('not a url')).toMatch(/^Recording /);
  });
});
