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
  containerType: 'form-item' | 'table-row' | 'list-item' | 'section' | 'unknown';
  /** Visible label text of the form field (trailing colons/asterisks stripped) */
  fieldLabel?: string;
  /** Hierarchical label path such as "奖品信息 / 奖品配置" */
  fieldPath?: string;
  /** Nearest higher-level section title such as "奖品信息" */
  sectionLabel?: string;
  /** Repeated item / row label such as "任务1：浏览服务号" */
  itemLabel?: string;
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
// Initial State types (Task Pack 6.5 / 7)
// ---------------------------------------------------------------------------

/** A snapshot of one form field's state at recording start (flat format, legacy). */
export interface InitialFieldSnapshot {
  /** Visible label text (e.g. "发放时间") */
  fieldLabel?: string;
  /** Hierarchical label path such as "奖品信息 / 奖品配置" */
  fieldPath?: string;
  /** Nearest higher-level section title such as "奖品信息" */
  sectionLabel?: string;
  /** Validation prop name from framework (e.g. "awardTiming") */
  fieldProp?: string;
  /** Detected field type: text | number | select | checkbox | radio | richtext | textarea | date-range | custom */
  fieldType?: string;
  /** Whether the field is marked as required */
  required?: boolean;
  /** Number of rows/items for table/list-like structures */
  itemCount?: number;
  /** Current visible value at recording start (before any user interaction) */
  defaultValueText?: string;
  /** Placeholder text (when no value present) */
  placeholder?: string;
  /** Initial HTML content for richtext editors */
  defaultValueHtml?: string;
}

/**
 * A node in the initial state AST tree.
 *
 * type values:
 *   - 'section'  — heading-based or ARIA-labeled section container
 *   - 'group'    — complex form-item with nested children
 *   - Leaf types — 'input', 'select', 'table', 'button', 'checkbox', 'radio',
 *                  'richtext', 'textarea', 'date', 'number', 'switch', 'slider',
 *                  'rate', 'upload', 'cascader', 'transfer', 'code-editor',
 *                  'color', 'autocomplete', 'list', 'custom', etc.
 */
export interface StateNode {
  /** Node type */
  type: string;
  /** Visible label text */
  label?: string;
  /** CSS selector path for locating this element on the page */
  selector?: string;
  /** Current value at snapshot time */
  value?: string;
  /** Placeholder text */
  placeholder?: string;
  /** Whether field is required */
  required?: boolean;
  /** Validation prop name from framework */
  fieldProp?: string;
  /** Row/item count for tables/lists */
  itemCount?: number;
  /** Table column headers */
  headers?: string[];
  /** Table row data (max ~20 rows, each row is array of cell text values) */
  rows?: string[][];
  /** Rich text HTML content */
  htmlContent?: string;
  /** Child nodes (for section, group, and container types) */
  children?: StateNode[];
}

/** Page initial state snapshot captured at recording start. */
export interface PageInitialState {
  /** Unix timestamp (ms) when the snapshot was taken */
  capturedAt: number;
  /** URL of the page at snapshot time */
  pageUrl: string;
  /** document.title at snapshot time */
  pageTitle: string;
  /** AST tree of page state (preferred format) */
  stateTree?: StateNode[];
  /** Flat form field snapshots (legacy format, kept for backward compat) */
  fields?: InitialFieldSnapshot[];
  /** Simplified HTML snapshot of the main content area (~30-80KB) */
  htmlSnapshot?: string;
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
