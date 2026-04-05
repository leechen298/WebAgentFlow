// Recording types
export type RecordingStatus = 'draft' | 'completed' | 'archived';

// Recording Event Types
export type RecordingEventType = 'navigate' | 'click' | 'input' | 'change' | 'richtext-input';

export interface FrameInfo {
  isIframe: boolean;
  frameUrl: string;
}

export interface RecordingEventTarget {
  tag: string;
  text?: string;
  selector?: string;
  label?: string;
  name?: string;
  id?: string;
  // Richer context (Task Pack 5)
  placeholder?: string;
  className?: string;
  role?: string;
  nearbyText?: string;
  // Rich text flag (Task Pack 5 RT)
  isRichText?: boolean;
}

/**
 * Semantic context of the form field that contains the event target.
 * Extracted by walking up the DOM to the nearest recognizable form-item container.
 */
export interface FieldContext {
  /** Type of the closest recognized container */
  containerType: 'form-item' | 'unknown';
  /** Visible label text of the form field (trailing colons/asterisks stripped) */
  fieldLabel?: string;
  /** Current value(s) visible in the field at event time (tags, input value, etc.) */
  fieldValueText?: string;
  /** Whether the field is marked as required */
  fieldRequired?: boolean;
  /** Validation prop name — e.g. "cityCodes" from Element UI prop="cityCodes" */
  fieldProp?: string;
  /** Inline error or hint message text */
  fieldHintText?: string;
}

export interface RecordingEvent {
  type: RecordingEventType;
  timestamp: number;
  url: string;
  title?: string;
  target?: RecordingEventTarget;
  value?: string | null;
  // Frame context (Task Pack 5)
  frameInfo?: FrameInfo;
  // Rich text HTML snapshot — truncated, only present for richtext-input events
  htmlContent?: string;
  // Form field semantic context extracted from DOM at event time (Task Pack 5.5)
  fieldContext?: FieldContext;
}

// ---------------------------------------------------------------------------
// Initial State types (Task Pack 6.5)
// ---------------------------------------------------------------------------

/** A snapshot of one form field's state at recording start. */
export interface InitialFieldSnapshot {
  /** Visible label text (e.g. "发放时间") */
  fieldLabel?: string;
  /** Validation prop name from framework (e.g. "awardTiming") */
  fieldProp?: string;
  /** Detected field type: text | number | select | checkbox | radio | richtext | textarea | date-range | custom */
  fieldType?: string;
  /** Whether the field is marked as required */
  required?: boolean;
  /** Current visible value at recording start (before any user interaction) */
  defaultValueText?: string;
  /** Placeholder text (when no value present) */
  placeholder?: string;
  /** Initial HTML content for richtext editors */
  defaultValueHtml?: string;
}

/** Page initial state snapshot captured at recording start. */
export interface PageInitialState {
  /** Unix timestamp (ms) when the snapshot was taken */
  capturedAt: number;
  /** URL of the page at snapshot time */
  pageUrl: string;
  /** document.title at snapshot time */
  pageTitle: string;
  /** All form field snapshots found on the page */
  fields: InitialFieldSnapshot[];
}

// Recording Meta
export interface RecordingMeta {
  initialUrl: string;
  initialTitle?: string;
  startTime: number;
  endTime?: number;
  eventCount: number;
  /** Page initial state captured at recording start (Task Pack 6.5) */
  initialState?: PageInitialState;
}

export interface Recording {
  id: string;
  name: string;
  status: RecordingStatus;
  source: string;
  events: Array<Record<string, unknown>>;
  meta: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface RecordingCreate {
  name: string;
  status?: RecordingStatus;
  source: string;
  events?: Array<Record<string, unknown>>;
  meta?: Record<string, unknown> | null;
}

export interface RecordingUpdate {
  name?: string;
  status?: RecordingStatus;
  source?: string;
  events?: Array<Record<string, unknown>>;
  meta?: Record<string, unknown> | null;
}

// ---------------------------------------------------------------------------
// Normalized Recording types (Task Pack 6)
// ---------------------------------------------------------------------------

export interface NormalizedStep {
  action_type: string;
  timestamp: number;
  url: string;
  page_title?: string | null;
  field_label?: string | null;
  field_prop?: string | null;
  field_required?: boolean | null;
  value?: string | null;
  button_text?: string | null;
  in_iframe: boolean;
  frame_url?: string | null;
  is_richtext: boolean;
  html_content?: string | null;
  raw_event_indices: number[];
}

export interface NormalizedSegment {
  index: number;
  type: string;
  title: string;
  steps: NormalizedStep[];
}

export interface NormalizationSummary {
  event_count_raw: number;
  event_count_normalized: number;
  page_count: number;
  segment_count: number;
  contains_iframe: boolean;
  contains_richtext: boolean;
}

export interface NormalizedRecording {
  recording_id: string;
  summary: NormalizationSummary;
  segments: NormalizedSegment[];
  key_actions: NormalizedStep[];
  /** Initial page state captured at recording start (Task Pack 6.5) */
  initial_state?: PageInitialState | null;
}

// Skill types
export type SkillStatus = 'draft' | 'published' | 'archived';

export interface Skill {
  id: string;
  name: string;
  version: string;
  status: SkillStatus;
  recording_id: string | null;
  definition: Record<string, unknown>;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface SkillCreate {
  name: string;
  version?: string;
  status?: SkillStatus;
  recording_id?: string | null;
  definition?: Record<string, unknown>;
  description?: string | null;
}

export interface SkillUpdate {
  name?: string;
  version?: string;
  status?: SkillStatus;
  recording_id?: string | null;
  definition?: Record<string, unknown>;
  description?: string | null;
}

// Run types
export type RunStatus = 'pending' | 'queued' | 'running' | 'succeeded' | 'failed';

export interface Run {
  id: string;
  skill_id: string;
  status: RunStatus;
  input_payload: Record<string, unknown> | Array<unknown>;
  result_payload: Record<string, unknown> | Array<unknown> | null;
  logs: Array<Record<string, unknown>> | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RunCreate {
  skill_id: string;
  status?: RunStatus;
  input_payload: Record<string, unknown> | Array<unknown>;
  result_payload?: Record<string, unknown> | Array<unknown> | null;
  logs?: Array<Record<string, unknown>> | null;
  started_at?: string | null;
  finished_at?: string | null;
}

export interface RunUpdate {
  skill_id?: string;
  status?: RunStatus;
  input_payload?: Record<string, unknown> | Array<unknown>;
  result_payload?: Record<string, unknown> | Array<unknown> | null;
  logs?: Array<Record<string, unknown>> | null;
  started_at?: string | null;
  finished_at?: string | null;
}

// API Response envelope
export interface ApiResponse<T> {
  code: number;
  msg: string;
  data: T;
}

export interface ApiErrorResponse {
  code: number;
  msg: string;
  data: Record<string, unknown> | Array<unknown> | null;
}

// Delete response
export interface DeleteResponse {
  recording_id?: string;
  skill_id?: string;
  run_id?: string;
}
