import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

vi.mock('@/api/client', () => ({
  resolveApiConfig: () => ({ baseURL: 'http://test.api' }),
}));

function buildSsePayload(events: string): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(events));
      controller.close();
    },
  });
}

/**
 * Polyfill TextDecoderStream for jsdom — decodes Uint8Array → string chunks.
 */
class PolyfillTextDecoderStream {
  readable: ReadableStream<string>;
  writable: WritableStream<Uint8Array>;
  constructor() {
    const decoder = new TextDecoder();
    const ts = new TransformStream<Uint8Array, string>({
      transform(chunk, controller) {
        controller.enqueue(decoder.decode(chunk, { stream: true }));
      },
      flush(controller) {
        const remaining = decoder.decode();
        if (remaining) controller.enqueue(remaining);
      },
    });
    this.readable = ts.readable;
    this.writable = ts.writable;
  }
}

describe('autonomousStream', () => {
  let origFetch: typeof globalThis.fetch;
  let origTDS: typeof globalThis.TextDecoderStream;

  beforeEach(() => {
    origFetch = globalThis.fetch;
    origTDS = globalThis.TextDecoderStream;
    // @ts-expect-error — jsdom lacks TextDecoderStream
    globalThis.TextDecoderStream = PolyfillTextDecoderStream;
  });

  afterEach(() => {
    globalThis.fetch = origFetch;
    globalThis.TextDecoderStream = origTDS;
  });

  it('dispatches parsed SSE events to onEvent', async () => {
    const sseData = 'event: step\ndata: {"index":0}\n\nevent: done\ndata: {"ok":true}\n\n';
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: buildSsePayload(sseData),
    });

    const { streamAutonomousRun } = await import('@/api/autonomousStream');
    const events: Array<{ event: string; data: unknown }> = [];

    await new Promise<void>((resolve) => {
      streamAutonomousRun(
        { url: 'http://x' },
        {
          onEvent: (evt) => events.push(evt),
          onDone: resolve,
        },
      );
    });

    expect(events).toHaveLength(2);
    expect(events[0]).toEqual({ event: 'step', data: { index: 0 } });
    expect(events[1]).toEqual({ event: 'done', data: { ok: true } });
  });

  it('defaults event type to "message" when no event: line', async () => {
    const sseData = 'data: "hello"\n\n';
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: buildSsePayload(sseData),
    });

    const { streamAutonomousRun } = await import('@/api/autonomousStream');
    const events: Array<{ event: string; data: unknown }> = [];

    await new Promise<void>((resolve) => {
      streamAutonomousRun(
        { url: 'http://x' },
        {
          onEvent: (evt) => events.push(evt),
          onDone: resolve,
        },
      );
    });

    expect(events[0].event).toBe('message');
    expect(events[0].data).toBe('hello');
  });

  it('keeps raw string when data is not valid JSON', async () => {
    const sseData = 'data: not-json\n\n';
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: buildSsePayload(sseData),
    });

    const { streamAutonomousRun } = await import('@/api/autonomousStream');
    const events: Array<{ event: string; data: unknown }> = [];

    await new Promise<void>((resolve) => {
      streamAutonomousRun(
        { url: 'http://x' },
        {
          onEvent: (evt) => events.push(evt),
          onDone: resolve,
        },
      );
    });

    expect(events[0].data).toBe('not-json');
  });

  it('skips comment lines starting with colon', async () => {
    const sseData = ': keepalive\ndata: "real"\n\n';
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: buildSsePayload(sseData),
    });

    const { streamAutonomousRun } = await import('@/api/autonomousStream');
    const events: Array<{ event: string; data: unknown }> = [];

    await new Promise<void>((resolve) => {
      streamAutonomousRun(
        { url: 'http://x' },
        {
          onEvent: (evt) => events.push(evt),
          onDone: resolve,
        },
      );
    });

    expect(events).toHaveLength(1);
    expect(events[0].data).toBe('real');
  });

  it('calls onError when fetch returns non-ok status', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: vi.fn().mockResolvedValue('Internal Server Error'),
    });

    const { streamAutonomousRun } = await import('@/api/autonomousStream');
    const errors: Error[] = [];

    await new Promise<void>((resolve) => {
      streamAutonomousRun(
        { url: 'http://x' },
        {
          onEvent: vi.fn(),
          onError: (err) => {
            errors.push(err);
            resolve();
          },
        },
      );
    });

    expect(errors).toHaveLength(1);
    expect(errors[0].message).toContain('HTTP 500');
  });

  it('calls onError when response has no body', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: null,
    });

    const { streamAutonomousRun } = await import('@/api/autonomousStream');
    const errors: Error[] = [];

    await new Promise<void>((resolve) => {
      streamAutonomousRun(
        { url: 'http://x' },
        {
          onEvent: vi.fn(),
          onError: (err) => {
            errors.push(err);
            resolve();
          },
        },
      );
    });

    expect(errors).toHaveLength(1);
    expect(errors[0].message).toContain('no body');
  });

  it('aborts the fetch signal and calls onDone when stop is called', async () => {
    let capturedSignal: AbortSignal | undefined;
    globalThis.fetch = vi.fn((_url: string | URL | Request, init?: RequestInit) => {
      capturedSignal = init?.signal ?? undefined;
      return new Promise((_resolve, reject) => {
        capturedSignal?.addEventListener('abort', () => {
          reject(new DOMException('aborted', 'AbortError'));
        });
      });
    }) as typeof globalThis.fetch;

    const { streamAutonomousRun } = await import('@/api/autonomousStream');
    const done = new Promise<void>((resolve) => {
      const stop = streamAutonomousRun(
        { url: 'http://x' },
        {
          onEvent: vi.fn(),
          onDone: resolve,
        },
      );

      expect(capturedSignal).toBeInstanceOf(AbortSignal);
      expect(capturedSignal?.aborted).toBe(false);

      stop();

      expect(capturedSignal?.aborted).toBe(true);
    });

    await done;
  });

  it('calls onError for non-abort fetch errors', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError('Network fail'));

    const { streamAutonomousRun } = await import('@/api/autonomousStream');
    const errors: Error[] = [];

    await new Promise<void>((resolve) => {
      streamAutonomousRun(
        { url: 'http://x' },
        {
          onEvent: vi.fn(),
          onError: (err) => {
            errors.push(err);
            resolve();
          },
        },
      );
    });

    expect(errors).toHaveLength(1);
    expect(errors[0].message).toBe('Network fail');
  });

  it('handles multi-line data fields', async () => {
    const sseData = 'data: line1\ndata: line2\n\n';
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: buildSsePayload(sseData),
    });

    const { streamAutonomousRun } = await import('@/api/autonomousStream');
    const events: Array<{ event: string; data: unknown }> = [];

    await new Promise<void>((resolve) => {
      streamAutonomousRun(
        { url: 'http://x' },
        {
          onEvent: (evt) => events.push(evt),
          onDone: resolve,
        },
      );
    });

    // Multi-line data joins with \n
    expect(events[0].data).toBe('line1\nline2');
  });

  it('sends POST with correct headers and body', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: buildSsePayload('data: "ok"\n\n'),
    });

    const { streamAutonomousRun } = await import('@/api/autonomousStream');

    await new Promise<void>((resolve) => {
      streamAutonomousRun(
        { url: 'http://target/', goal: 'test', spec_id: 'login' },
        { onEvent: vi.fn(), onDone: resolve },
      );
    });

    const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(call[0]).toBe('http://test.api/exploration/autonomous-runs/stream');
    expect(call[1].method).toBe('POST');
    expect(call[1].headers['Content-Type']).toBe('application/json');
    expect(call[1].headers['Accept']).toBe('text/event-stream');
    const body = JSON.parse(call[1].body);
    expect(body.url).toBe('http://target/');
    expect(body.spec_id).toBe('login');
  });
});
