import { describe, expect, it } from 'vitest';

describe('API index exports', () => {
  it('re-exports the expected API helpers', async () => {
    const api = await import('@/api');

    expect(api.apiClient).toBeDefined();
    expect(api.getHealth).toBeDefined();
    expect(api.getRecordingsList).toBeDefined();
    expect(api.createSkill).toBeDefined();
    expect(api.createRun).toBeDefined();
    expect(api.inferCandidates).toBeDefined();
  });
});
