import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getHealth, type HealthStatus } from '@/api/health';

const { get } = vi.hoisted(() => ({
  get: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  default: { get },
}));

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

  it('fetches health status from the backend', async () => {
    get.mockResolvedValueOnce({ status: 'ok', database: 'ok' });

    await expect(getHealth()).resolves.toEqual({ status: 'ok', database: 'ok' });
    expect(get).toHaveBeenCalledWith('/health');
  });
});
