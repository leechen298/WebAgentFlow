import { describe, it, expect } from 'vitest';

describe('API Client', () => {
  it('should have API client exported', async () => {
    const api = await import('@/api/client');
    expect(api.default).toBeDefined();
    expect(api.resolveApiConfig).toBeDefined();
  });
});
