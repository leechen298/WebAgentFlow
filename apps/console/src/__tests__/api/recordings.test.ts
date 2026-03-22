import { describe, it, vi, beforeEach } from 'vitest';

describe('Recordings API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should have recordings API functions exported', async () => {
    const api = await import('@/api/recordings');
    expect(api.getRecordingsList).toBeDefined();
    expect(api.getRecordingById).toBeDefined();
    expect(api.createRecording).toBeDefined();
    expect(api.updateRecording).toBeDefined();
    expect(api.deleteRecording).toBeDefined();
  });
});
