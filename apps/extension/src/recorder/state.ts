import type { RecordingEvent } from '@web-agent-flow/shared-types';

export interface RecorderState {
  isRecording: boolean;
  events: RecordingEvent[];
  startTime: number | null;
  initialUrl: string | null;
  initialTitle: string | null;
}

const STORAGE_KEY = 'local:webagentflow:recorder:state';

/**
 * Create initial recorder state
 */
export function createInitialState(): RecorderState {
  return {
    isRecording: false,
    events: [],
    startTime: null,
    initialUrl: null,
    initialTitle: null,
  };
}

/**
 * Save recorder state to extension storage
 */
export async function saveState(state: RecorderState): Promise<void> {
  await storage.setItem(STORAGE_KEY, state);
}

/**
 * Load recorder state from extension storage
 */
export async function loadState(): Promise<RecorderState> {
  const stored = await storage.getItem<RecorderState>(STORAGE_KEY);
  return stored || createInitialState();
}

/**
 * Clear recorder state from storage
 */
export async function clearState(): Promise<void> {
  await storage.removeItem(STORAGE_KEY);
}

/**
 * Start recording - resets state and marks as recording
 */
export function startRecording(
  state: RecorderState,
  url: string,
  title?: string,
): RecorderState {
  return {
    isRecording: true,
    events: [],
    startTime: Date.now(),
    initialUrl: url,
    initialTitle: title,
  };
}

/**
 * Stop recording - marks as not recording
 */
export function stopRecording(state: RecorderState): RecorderState {
  return {
    ...state,
    isRecording: false,
  };
}

/**
 * Add an event to the recorder state
 */
export function addEvent(state: RecorderState, event: RecordingEvent): RecorderState {
  if (!state.isRecording) {
    return state;
  }
  return {
    ...state,
    events: [...state.events, event],
  };
}

/**
 * Clear all events from the recorder state
 */
export function clearEvents(state: RecorderState): RecorderState {
  return {
    ...state,
    events: [],
  };
}
