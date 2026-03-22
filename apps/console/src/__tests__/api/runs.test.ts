import { describe, it, vi, beforeEach } from 'vitest';

describe('Runs API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should have runs API functions exported', async () => {
    const api = await import('@/api/runs');
    expect(api.getRunsList).toBeDefined();
    expect(api.getRunById).toBeDefined();
    expect(api.createRun).toBeDefined();
    expect(api.updateRun).toBeDefined();
    expect(api.deleteRun).toBeDefined();
  });
});
