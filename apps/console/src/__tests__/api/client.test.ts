import { beforeEach, describe, expect, it, vi } from 'vitest';

type Handler<T = unknown> = (value: T) => unknown;

describe('api/client', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
    localStorage.clear();
  });

  it('resolves direct and proxy api config from env', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://api.example');
    vi.stubEnv('VITE_USE_DEV_PROXY', 'false');
    vi.doMock('axios', () => ({
      default: {
        create: () => ({
          interceptors: {
            request: { use: vi.fn() },
            response: { use: vi.fn() },
          },
        }),
      },
      create: () => ({
        interceptors: {
          request: { use: vi.fn() },
          response: { use: vi.fn() },
        },
      }),
    }));

    const mod = await import('@/api/client');
    expect(mod.resolveApiConfig()).toEqual({
      mode: 'direct',
      baseURL: 'http://api.example',
      useDevProxy: false,
      configuredApiBaseUrl: 'http://api.example',
    });

    vi.resetModules();
    vi.stubEnv('VITE_API_BASE_URL', 'http://ignored.example');
    vi.stubEnv('VITE_USE_DEV_PROXY', 'true');
    vi.doMock('axios', () => ({
      default: {
        create: () => ({
          interceptors: {
            request: { use: vi.fn() },
            response: { use: vi.fn() },
          },
        }),
      },
      create: () => ({
        interceptors: {
          request: { use: vi.fn() },
          response: { use: vi.fn() },
        },
      }),
    }));

    const proxyMod = await import('@/api/client');
    expect(proxyMod.resolveApiConfig()).toEqual({
      mode: 'proxy',
      baseURL: '/api',
      useDevProxy: true,
      configuredApiBaseUrl: 'http://ignored.example',
    });
  });

  it('throws when api config is missing', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '');
    vi.stubEnv('VITE_USE_DEV_PROXY', 'false');
    vi.doMock('axios', () => ({
      default: {
        create: () => ({
          interceptors: {
            request: { use: vi.fn() },
            response: { use: vi.fn() },
          },
        }),
      },
      create: () => ({
        interceptors: {
          request: { use: vi.fn() },
          response: { use: vi.fn() },
        },
      }),
    }));

    await expect(import('@/api/client')).rejects.toThrow(/VITE_API_BASE_URL/);
  });

  it('registers request and response interceptors that normalize payloads and errors', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://api.example');
    vi.stubEnv('VITE_USE_DEV_PROXY', 'false');

    let requestFulfilled: Handler | undefined;
    let requestRejected: Handler | undefined;
    let responseFulfilled: Handler | undefined;
    let responseRejected: Handler | undefined;

    const create = vi.fn(() => ({
      interceptors: {
        request: {
          use: vi.fn((ok: Handler, fail: Handler) => {
            requestFulfilled = ok;
            requestRejected = fail;
          }),
        },
        response: {
          use: vi.fn((ok: Handler, fail: Handler) => {
            responseFulfilled = ok;
            responseRejected = fail;
          }),
        },
      },
    }));

    vi.doMock('axios', () => ({
      default: { create },
      create,
    }));
    vi.doMock('@/i18n', () => ({
      default: {
        global: {
          t: (key: string, params?: Record<string, unknown>) =>
            params?.status ? `${key}:${params.status}` : key,
        },
      },
    }));

    await import('@/api/client');
    expect(create).toHaveBeenCalled();
    expect(requestFulfilled).toBeTypeOf('function');
    expect(responseFulfilled).toBeTypeOf('function');
    expect(responseRejected).toBeTypeOf('function');
    expect(requestRejected).toBeTypeOf('function');

    localStorage.setItem('locale', 'zh-CN');
    const config = { headers: {} as Record<string, string> };
    expect(requestFulfilled?.(config)).toEqual({
      headers: { 'X-Locale': 'zh-CN' },
    });

    const transportError = new Error('transport');
    await expect(requestRejected?.(transportError)).rejects.toBe(transportError);

    expect(responseFulfilled?.({ data: { code: 0, msg: 'ok', data: { id: 1 } } })).toEqual({ id: 1 });
    await expect(responseFulfilled?.({ data: { code: 7, msg: 'bad', data: null } })).rejects.toMatchObject({
      message: 'bad',
      code: 7,
    });

    await expect(
      responseRejected?.({ response: { status: 404, data: {} } }),
    ).rejects.toMatchObject({ message: 'error.notFound' });

    await expect(
      responseRejected?.({ response: { status: 500, data: { msg: 'boom' } } }),
    ).rejects.toMatchObject({ message: 'boom' });

    await expect(
      responseRejected?.({ response: { status: 418, data: {} } }),
    ).rejects.toMatchObject({ message: 'error.httpError:418' });

    await expect(
      responseRejected?.({ request: {} }),
    ).rejects.toMatchObject({ message: 'error.noResponse' });

    await expect(
      responseRejected?.({}),
    ).rejects.toMatchObject({ message: 'error.network' });
  });
});
