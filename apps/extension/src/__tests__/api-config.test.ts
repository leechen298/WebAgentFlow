import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getApiConfig, setApiConfig } from '../utils/config';

const storageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
};

vi.stubGlobal('storage', storageMock);

describe('extension API config', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns stored config when present', async () => {
    storageMock.getItem.mockResolvedValueOnce({ baseURL: 'https://api.example.com', timeout: 1234 });
    await expect(getApiConfig()).resolves.toEqual({ baseURL: 'https://api.example.com', timeout: 1234 });
  });

  it('falls back to defaults when storage is empty or throws', async () => {
    storageMock.getItem.mockResolvedValueOnce(null);
    await expect(getApiConfig()).resolves.toEqual({ baseURL: 'http://localhost:8001', timeout: 30000 });

    storageMock.getItem.mockRejectedValueOnce(new Error('storage unavailable'));
    await expect(getApiConfig()).resolves.toEqual({ baseURL: 'http://localhost:8001', timeout: 30000 });
  });

  it('merges and persists updated config values', async () => {
    storageMock.getItem.mockResolvedValueOnce({ baseURL: 'https://api.example.com', timeout: 1234 });

    await setApiConfig({ timeout: 9999 });

    expect(storageMock.setItem).toHaveBeenCalledWith(
      'local:webagentflow:api:config',
      { baseURL: 'https://api.example.com', timeout: 9999 },
    );
  });
});
