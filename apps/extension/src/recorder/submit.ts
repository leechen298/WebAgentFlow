import type {
  Recording,
  RecordingCreate,
  RecordingMeta,
  RecordingEvent,
  PageInitialState,
} from '@web-agent-flow/shared-types';
import { createApiClient } from '../utils/api';

export interface SubmitRecordingOptions {
  name: string;
  events: RecordingEvent[];
  initialUrl: string | null;
  initialTitle: string | null;
  startTime: number | null;
  /** Page initial state snapshot (Task Pack 6.5) */
  initialState?: PageInitialState | null;
}

/**
 * Prepare recording data for submission
 */
export function prepareRecordingData(
  options: SubmitRecordingOptions,
): RecordingCreate {
  const now = Date.now();
  const meta: RecordingMeta = {
    initialUrl: options.initialUrl || '',
    initialTitle: options.initialTitle,
    startTime: options.startTime || now,
    endTime: now,
    eventCount: options.events.length,
    ...(options.initialState ? { initialState: options.initialState } : {}),
  };

  return {
    name: options.name,
    status: 'completed',
    source: 'extension',
    events: options.events,
    meta: meta as Record<string, unknown>,
  };
}

/**
 * Submit a recording to the backend API
 */
export async function submitRecording(
  options: SubmitRecordingOptions,
): Promise<Recording> {
  const client = await createApiClient();
  const payload = prepareRecordingData(options);

  try {
    const response = await client.post<Recording>('/recordings/create', payload);
    return response;
  } catch (error) {
    console.error('Failed to submit recording:', error);
    throw error;
  }
}

/**
 * Generate a default recording name based on the current time
 */
export function generateRecordingName(initialUrl?: string | null): string {
  const now = new Date();
  const timeStr = now.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
  });
  const dateStr = now.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });

  let name = `Recording ${dateStr} ${timeStr}`;

  // Add domain from initial URL if available
  if (initialUrl) {
    try {
      const url = new URL(initialUrl);
      name += ` - ${url.hostname}`;
    } catch {
      // Ignore invalid URLs
    }
  }

  return name;
}
