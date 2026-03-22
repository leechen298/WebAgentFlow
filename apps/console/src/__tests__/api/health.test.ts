import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { HealthStatus } from '@/api/health';

describe('Health API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should export HealthStatus interface', () => {
    const health: HealthStatus = {
      status: 'ok',
      database: 'ok',
    };
    expect(health.status).toBe('ok');
    expect(health.database).toBe('ok');
  });
});
