/**
 * Minimal SSE client for the /exploration/autonomous-runs/stream endpoint.
 *
 * The native EventSource API only supports GET. Since our endpoint is POST
 * with a JSON payload, we use fetch + a ReadableStream reader and parse
 * the SSE wire format manually.
 *
 * Usage:
 *   const stop = streamAutonomousRun({...payload}, { onEvent, onError, onDone });
 *   // stop() aborts the connection
 */

import { resolveApiConfig } from './client';

export interface AutonomousStreamPayload {
  url: string;
  goal?: string;
  fill_value?: string;
  fill_values?: Record<string, string>;
  /** Native toggle (radio/checkbox) selections keyed by group's
   * semantic role (e.g. 'status') -> option value (e.g. 'active'). */
  toggle_values?: Record<string, string>;
  headless?: boolean;
  spec_id?: string | null;
  scenario?: string | null;
  /**
   * UI locale passed through so the project-internal Supervisor Agent
   * (the LLM part) responds in the user's language. Expected values:
   * "en" | "zh" | "ja" (or any BCP-47 code — backend uses it verbatim).
   */
  language?: string;
}

export interface StreamEvent {
  event: string;
  data: unknown;
}

export interface StreamHandlers {
  onEvent: (evt: StreamEvent) => void;
  onError?: (err: Error) => void;
  onDone?: () => void;
}

/**
 * Starts the SSE stream and returns a function to abort it.
 */
export function streamAutonomousRun(
  payload: AutonomousStreamPayload,
  handlers: StreamHandlers,
): () => void {
  const controller = new AbortController();
  const { baseURL } = resolveApiConfig();
  const url = `${baseURL}/exploration/autonomous-runs/stream`;

  (async () => {
    try {
      const res = await fetch(url, {
        method: 'POST',
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const body = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status}: ${body.slice(0, 200)}`);
      }
      if (!res.body) {
        throw new Error('Response has no body');
      }

      const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += value;

        // SSE events are separated by a blank line (\n\n).
        let idx: number;
        // eslint-disable-next-line no-cond-assign
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const rawEvent = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const parsed = parseSseBlock(rawEvent);
          if (parsed) handlers.onEvent(parsed);
        }
      }

      // Flush any trailing event.
      if (buffer.trim()) {
        const parsed = parseSseBlock(buffer);
        if (parsed) handlers.onEvent(parsed);
      }

      handlers.onDone?.();
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        handlers.onDone?.();
        return;
      }
      handlers.onError?.(err as Error);
    }
  })();

  return () => controller.abort();
}

function parseSseBlock(block: string): StreamEvent | null {
  const lines = block.split('\n');
  let eventType = 'message';
  const dataLines: string[] = [];
  for (const line of lines) {
    if (line.startsWith(':')) continue; // comment / keepalive
    if (line.startsWith('event:')) eventType = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''));
  }
  if (dataLines.length === 0) return null;
  const dataRaw = dataLines.join('\n');
  let data: unknown = dataRaw;
  try {
    data = JSON.parse(dataRaw);
  } catch {
    /* keep raw string if not JSON */
  }
  return { event: eventType, data };
}
