import { describe, it, expect, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useAppStore } from '@/stores/app';
import * as healthApi from '@/api/health';

// Mock the API
vi.mock('@/api/health');

describe('App Store', () => {
  beforeEach(() => {
    // Create a fresh pinia instance and make it active
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('should initialize with default state', () => {
    const store = useAppStore();
    expect(store.apiConnected).toBe(false);
    expect(store.loading).toBe(false);
    expect(store.error).toBeNull();
  });

  it('should check API health successfully', async () => {
    const store = useAppStore();
    const mockGetHealth = vi.mocked(healthApi.getHealth);
    mockGetHealth.mockResolvedValue({ status: 'ok', database: 'ok' });

    await store.checkApiHealth();

    expect(mockGetHealth).toHaveBeenCalled();
    expect(store.apiConnected).toBe(true);
    expect(store.loading).toBe(false);
  });

  it('should handle API health check failure', async () => {
    const store = useAppStore();
    const mockGetHealth = vi.mocked(healthApi.getHealth);
    mockGetHealth.mockRejectedValue(new Error('Network error'));

    await store.checkApiHealth();

    expect(mockGetHealth).toHaveBeenCalled();
    expect(store.apiConnected).toBe(false);
    expect(store.loading).toBe(false);
  });

  it('should set loading state during health check', async () => {
    const store = useAppStore();
    const mockGetHealth = vi.mocked(healthApi.getHealth);

    let resolvePromise: (value: healthApi.HealthStatus) => void;
    const promise = new Promise<healthApi.HealthStatus>((resolve) => {
      resolvePromise = resolve;
    });
    mockGetHealth.mockReturnValue(promise);

    const healthCheck = store.checkApiHealth();
    expect(store.loading).toBe(true);

    resolvePromise!({ status: 'ok', database: 'ok' });
    await healthCheck;

    expect(store.loading).toBe(false);
  });
});
