import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createApiClient } from '../utils/api';

const { useResponse, axiosCreate } = vi.hoisted(() => {
  const useResponse = vi.fn();
  const axiosCreate = vi.fn(() => ({
    interceptors: { response: { use: useResponse } },
  }));
  return { useResponse, axiosCreate };
});

vi.mock('axios', () => ({
  default: { create: axiosCreate },
}));

vi.mock('../utils/config', () => ({
  getApiConfig: vi.fn().mockResolvedValue({ baseURL: 'https://api.example.com', timeout: 4321 }),
}));

describe('extension API client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates an axios client with the configured base url and timeout', async () => {
    const client = await createApiClient();

    expect(client).toBeDefined();
    expect(axiosCreate).toHaveBeenCalledWith({
      baseURL: 'https://api.example.com',
      timeout: 4321,
      headers: { 'Content-Type': 'application/json' },
    });
    expect(useResponse).toHaveBeenCalledOnce();
  });

  it('unwraps successful envelope responses', async () => {
    await createApiClient();
    const onSuccess = useResponse.mock.calls[0][0];

    expect(onSuccess({ data: { code: 0, data: { ok: true } } })).toEqual({ ok: true });
    await expect(onSuccess({ data: { code: 400, msg: 'Bad business' } })).rejects.toThrow('Bad business');
  });

  it('maps HTTP and request failures to readable errors', async () => {
    await createApiClient();
    const onError = useResponse.mock.calls[0][1];

    await expect(onError({ response: { status: 404, data: {} } })).rejects.toThrow('Resource not found');
    await expect(onError({ response: { status: 500, data: { msg: 'server exploded' } } })).rejects.toThrow('server exploded');
    await expect(onError({ request: {} })).rejects.toThrow('No response from server');
  });
});
