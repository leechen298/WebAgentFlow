import type { RecordingEvent, PageInitialState } from '@web-agent-flow/shared-types';

export interface InitialStateSourceInfo {
  frameId: number | null;
  senderUrl: string | null;
  score: number;
}

export interface RecorderState {
  isRecording: boolean;
  events: RecordingEvent[];
  startTime: number | null;
  initialUrl: string | null;
  initialTitle: string | null;
  /** Page initial state snapshot captured at recording start (Task Pack 6.5) */
  initialState: PageInitialState | null;
  /** Internal source metadata for choosing the best initial-state candidate. */
  initialStateSource?: InitialStateSourceInfo | null;
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
    initialState: null,
    initialStateSource: null,
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
    initialState: null,
    initialStateSource: null,
  };
}

/**
 * Message-level source info used to rank competing initial-state snapshots.
 */
export interface InitialStateCandidateSource {
  frameId?: number | null;
  senderUrl?: string | null;
}

function hasUsableUrl(url?: string | null): boolean {
  if (!url) return false;
  const trimmed = url.trim();
  return trimmed.length > 0 && trimmed !== 'about:blank';
}

function hasMeaningfulFieldData(initialState: PageInitialState): boolean {
  return initialState.fields.some(
    (field) =>
      Boolean(field.defaultValueText?.trim()) ||
      Boolean(field.defaultValueHtml?.trim()) ||
      Boolean(field.placeholder?.trim()),
  );
}

function computeInitialStateScore(
  initialState: PageInitialState,
  source?: InitialStateCandidateSource,
): number {
  let score = 0;

  score += initialState.fields.length * 100;

  if (hasMeaningfulFieldData(initialState)) score += 40;
  if (initialState.fields.some((field) => field.required)) score += 10;

  if (hasUsableUrl(initialState.pageUrl)) {
    score += 80;
  } else {
    score -= 400;
  }

  if (initialState.pageTitle?.trim()) {
    score += 20;
  } else {
    score -= 20;
  }

  if (source?.senderUrl && source.senderUrl === initialState.pageUrl) {
    score += 20;
  }

  // In iframe scenes, the business form is often inside a child frame. This is
  // only a mild bonus so top-level pages still win when they clearly have
  // better field data.
  if ((source?.frameId ?? 0) > 0 && initialState.fields.length > 0) {
    score += 15;
  }

  return score;
}

function shouldReplaceInitialState(
  currentState: RecorderState,
  incoming: PageInitialState,
  incomingSource: InitialStateCandidateSource,
): boolean {
  if (!currentState.initialState) return true;

  const currentScore = currentState.initialStateSource?.score ??
    computeInitialStateScore(currentState.initialState, currentState.initialStateSource ?? undefined);
  const incomingScore = computeInitialStateScore(incoming, incomingSource);

  if (incomingScore !== currentScore) {
    return incomingScore > currentScore;
  }

  if (incoming.fields.length !== currentState.initialState.fields.length) {
    return incoming.fields.length > currentState.initialState.fields.length;
  }

  return incoming.capturedAt >= currentState.initialState.capturedAt;
}

/**
 * Store the best initial page state snapshot in the recorder state.
 */
export function setInitialState(
  state: RecorderState,
  initialState: PageInitialState,
  source?: InitialStateCandidateSource,
): RecorderState {
  if (!shouldReplaceInitialState(state, initialState, source ?? {})) {
    return state;
  }

  const nextState: RecorderState = {
    ...state,
    initialState,
    initialStateSource: {
      frameId: source?.frameId ?? null,
      senderUrl: source?.senderUrl ?? null,
      score: computeInitialStateScore(initialState, source),
    },
  };

  // If recording started too early on about:blank or an empty shell page, let a
  // better initial-state candidate repair the visible recording metadata too.
  if (!hasUsableUrl(nextState.initialUrl) && hasUsableUrl(initialState.pageUrl)) {
    nextState.initialUrl = initialState.pageUrl;
  }
  if (!nextState.initialTitle?.trim() && initialState.pageTitle?.trim()) {
    nextState.initialTitle = initialState.pageTitle;
  }

  return nextState;
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
