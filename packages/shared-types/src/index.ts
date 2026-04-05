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

// Recording Meta
export interface RecordingMeta {
  initialUrl: string;
  initialTitle?: string;
  startTime: number;
  endTime?: number;
  eventCount: number;
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
