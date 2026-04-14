// Cursor pagination
export interface CursorPage<T> {
  items: T[];
  has_next: boolean;
  next_cursor: string | null;
}

// Recording types
export type RecordingStatus = 'draft' | 'completed' | 'archived';

// Recording Event Types
export type RecordingEventType = 'navigate' | 'click' | 'input' | 'change' | 'richtext-input';

// ---------------------------------------------------------------------------
// AST Match — associates a recording event with the AST node it acted on.
//
// At capture time the content script tries to locate the event target in the
// current Semantic State Tree (stateTree). The result is stored on the event
// so downstream consumers can correlate events with page structure.
// ---------------------------------------------------------------------------

/**
 * How confidently the event target was matched to an AST node.
 *
 * Current matching semantics (produced by AstIndex.matchElement):
 *   - `exact`    — the event target element directly matches an AST leaf node's CSS selector
 *   - `ancestor` — the event target is a descendant of an element matching an AST leaf node
 *   - `none`     — no match found; fallback context (ancestorChain, areaLabel) is provided
 */
export type AstMatchConfidence = 'exact' | 'ancestor' | 'none';

/**
 * Association between a recording event and a node in the Semantic State Tree.
 */
export interface AstMatch {
  /** Confidence level of the match */
  confidence: AstMatchConfidence;
  /** AST node ID (sequential, assigned during tree building) */
  nodeId?: string;
  /** Dot-separated path in the tree, e.g. "0.2.1" (root index . child index ...) */
  nodePath?: string;
  /** The matched node's type (e.g. 'input', 'button', 'select', 'section') */
  nodeType?: string;
  /** The matched node's label */
  nodeLabel?: string;
  /** The matched node's selector (if it's a leaf node) */
  nodeSelector?: string;
  /** Fallback: summary of ancestor chain when no AST match (tag > tag > tag) */
  ancestorChain?: string;
  /** Fallback: nearest identifiable section/card/form heading */
  areaLabel?: string;
}

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
  /** Unique event identifier (monotonic counter per recording session) */
  id: string;
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
  /** Association with the Semantic State Tree node this event acted on */
  astMatch?: AstMatch;
}

// ---------------------------------------------------------------------------
// Initial State types (Task Pack 6.5 / 6.6)
//
// Three-layer architecture:
//   1. Semantic State Tree (stateTree) — primary structure expressing page
//      semantic blocks, key values, actions, and hierarchy. This is the main
//      input for downstream consumers (normalization, skill draft, LLM).
//   2. Leaf-level local HTML (localHtml on StateNode) — small HTML snippets
//      on complex leaf nodes where semantic extraction alone is insufficient
//      (richtext, custom components). Fallback facts layer.
//   3. Raw HTML Snapshot (rawHtmlSnapshot) — full simplified page snapshot
//      for debug, tracing, and offline re-analysis. NOT used in the primary
//      analysis pipeline.
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
 *   - 'table'    — may have flat rows[][] (simple) or children[] (complex cells)
 *   - Leaf types — 'input', 'select', 'button', 'link', 'checkbox',
 *                  'radio', 'richtext', 'textarea', 'date', 'number', 'switch',
 *                  'slider', 'rate', 'upload', 'cascader', 'transfer',
 *                  'code-editor', 'color', 'autocomplete', 'list', 'custom', etc.
 */
export interface TableCellNode {
  /** Cell type: text | image | button | button-group | input | input-number | custom | empty | cell */
  type: string;
  /** Optional cell label */
  label?: string;
  /** Selector for the cell root or primary control */
  selector?: string;
  /** Plain text content */
  text?: string;
  /** Image source for image cells */
  src?: string;
  /** Structured control value */
  value?: string;
  /** Placeholder for embedded controls */
  placeholder?: string;
  /** Child action nodes for button/button-group cells */
  actions?: StateNode[];
  /** Structured child nodes preserved from the cell DOM */
  children?: StateNode[];
  /** Explicit visibility flag when hidden */
  visible?: boolean;
  /** Key CSS visibility state affecting interaction */
  cssState?: string;
  /** Local HTML fallback for complex cells */
  localHtml?: string;
}

export type TableRowValue = string | TableCellNode;

export interface StateNode {
  /** Unique node ID assigned during tree building (e.g. "n0", "n1", ...) */
  astNodeId?: string;
  /** Node type */
  type: string;
  /** Visible label text */
  label?: string;
  /** Semantic block classification for section/group nodes (e.g. 'form-section', 'card-block', 'toolbar') */
  blockType?: string;
  /** Short summary of the block content (for non-field nodes) */
  summaryText?: string;
  /** Action button labels found inside this block */
  actions?: string[];
  /** CSS selector for locating this element (leaf/actionable nodes only, omitted on containers) */
  selector?: string;
  /** Link target URL (for navigation links) */
  href?: string;
  /** Whether this item is currently active/selected (e.g. active menu item) */
  active?: boolean;
  /** Explicit visibility flag for hidden nodes; omitted for visible nodes */
  visible?: boolean;
  /** Key CSS visibility state affecting interaction (e.g. 'display:none', 'visibility:hidden').
   *  display:none = not rendered, not clickable. visibility:hidden = rendered, occupies space, still clickable.
   *  Omitted when the element is normally visible. */
  cssState?: string;
  /** Current value at snapshot time */
  value?: string;
  /** Available options for select/radio/checkbox fields (label + selected state) */
  options?: { label: string; selected?: boolean }[];
  /** Placeholder text */
  placeholder?: string;
  /** Hint, tip, or description text associated with a form field */
  hint?: string;
  /** Help text associated with the node */
  helpText?: string;
  /** Tip texts associated with the node */
  tips?: string[];
  /** Longer descriptive text associated with the node */
  description?: string;
  /** Status text associated with the node */
  statusText?: string;
  /** Whether field is required */
  required?: boolean;
  /** Validation prop name from framework */
  fieldProp?: string;
  /** Row/item count for tables/lists */
  itemCount?: number;
  /** Table column headers */
  headers?: string[];
  /** Table row data; parsers may emit legacy strings or structured cell objects */
  rows?: TableRowValue[][];
  /** Tip / description nodes that belong to the table footer area */
  footerTips?: StateNode[];
  /**
   * Leaf-level local HTML snippet — fallback facts layer for complex nodes
   * where semantic extraction alone is insufficient (richtext content,
   * custom components with complex display). Max ~500 chars.
   */
  localHtml?: string;
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
  /** Visible main heading extracted from the page content (h1/h2/page-header) */
  pageHeading?: string;
  /** Primary CTA button labels found on the page (e.g. ["保存", "取消"]) */
  primaryActions?: string[];
  /** Semantic state tree — primary structure (see 3-layer doc above) */
  stateTree?: StateNode[];
  /** Flat form field snapshots (legacy format, kept for backward compat) */
  fields?: InitialFieldSnapshot[];
  /**
   * Raw HTML snapshot of the main content area (~30-80KB).
   * Debug/fallback layer only — NOT used in the primary analysis pipeline.
   * Kept for tracing, offline re-analysis, and regression debugging.
   */
  rawHtmlSnapshot?: string;
}

// ---------------------------------------------------------------------------
// DOM Mutation types — captures page DOM changes during recording.
//
// The mutation tracker observes MutationObserver events on both the top-level
// document and same-origin iframe documents. Each batch of DOM mutations is
// coalesced into DomMutationRecord entries with AST node association.
// ---------------------------------------------------------------------------

/** Type of DOM mutation observed */
export type DomMutationType = 'childList' | 'attributes' | 'characterData';

/** Summary of an added or removed DOM node (childList mutations) */
export interface MutationNodeSummary {
  tag: string;
  id?: string;
  className?: string;
  /** Truncated text content (max 200 chars) */
  text?: string;
  /** Number of child elements in the added/removed subtree */
  childCount?: number;
}

/** Details specific to each mutation type, stored in the `detail` field */
export interface ChildListDetail {
  type: 'childList';
  addedNodes: MutationNodeSummary[];
  removedNodes: MutationNodeSummary[];
}

export interface AttributeDetail {
  type: 'attributes';
  attributeName: string;
  oldValue: string | null;
  newValue: string | null;
}

export interface CharacterDataDetail {
  type: 'characterData';
  oldValue: string | null;
  newValue: string | null;
}

export type DomMutationDetail = ChildListDetail | AttributeDetail | CharacterDataDetail;

/** A single structured DOM mutation record */
export interface DomMutationRecord {
  /** Unique mutation ID (m0, m1, ... or fm{nonce}_0 for iframes) */
  id: string;
  /** Unix timestamp (ms) when the mutation was observed */
  timestamp: number;
  /** Mutation type */
  mutationType: DomMutationType;
  /** URL of the page/frame where the mutation occurred */
  url: string;
  /** Frame context */
  frameInfo?: FrameInfo;

  // --- Target node info ---
  /** Tag name of the target node */
  targetTag: string;
  /** CSS selector of the target node (best-effort) */
  targetSelector?: string;
  /** Truncated text content of the target node */
  targetText?: string;
  /** ID attribute of the target node */
  targetId?: string;
  /** First class name of the target node */
  targetClassName?: string;

  // --- AST association ---
  /** AST match for this mutation's target element */
  astMatch?: AstMatch;

  // --- Mutation detail ---
  /** Type-specific detail of the change */
  detail: DomMutationDetail;

  // --- Context ---
  /** Nearest identifiable area/section label (heading, card title, etc.) */
  areaLabel?: string;
  /** Extensible metadata for future use */
  meta?: Record<string, unknown>;
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
  /** DOM mutation records captured during recording */
  domMutations?: DomMutationRecord[];
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

// ---------------------------------------------------------------------------
// Operation Step types — correlates user events with subsequent DOM mutations
//
// Phase 5 boundary: The Step layer is a lightweight event → DOM-change
// organizer. It is NOT a causal inference engine, execution decision layer,
// or path template layer. See step_builder.py for the full boundary statement.
//
// Field classification:
//   Agent-core: event_type, event_target_summary, has_changes,
//     mutations.total, mutations.by_type, change_area, summary
//   Debug/context: id, timestamp, end_timestamp, url, frame_info,
//     event_index, event_ast_match, mutation_ids, highlights
// ---------------------------------------------------------------------------

/** Summary of mutations associated with a step */
export interface StepMutationSummary {
  /** [Agent-core] Total number of correlated mutations */
  total: number;
  /** [Agent-core] Breakdown by mutation type */
  by_type: { childList: number; attributes: number; characterData: number };
  /** [Debug] IDs of the correlated mutation records */
  mutation_ids: string[];
  /** [Debug] Human-readable one-line descriptions of the most significant changes */
  highlights: string[];
}

/** A single operation step: one user event + its correlated DOM mutations */
export interface OperationStep {
  // --- Debug / context fields ---
  /** [Debug] Sequential step ID (s0, s1, ...) */
  id: string;
  /** [Debug] Timestamp of the primary event (Unix ms) */
  timestamp: number;
  /** [Debug] End timestamp — latest mutation timestamp, or same as timestamp if no mutations */
  end_timestamp: number;
  /** [Debug] URL where the event occurred */
  url: string;
  /** [Debug] Frame context */
  frame_info?: FrameInfo | null;
  /** [Debug] Index of the primary event in recording.events */
  event_index: number;
  /** [Debug] AST match for the event (if available) */
  event_ast_match?: AstMatch | null;

  // --- Agent-core fields ---
  /** [Agent-core] The event type (click, input, navigate, etc.) */
  event_type: RecordingEventType;
  /** [Agent-core] Short description of the event target */
  event_target_summary: string;
  /** [Agent-core] Summary of DOM mutations correlated with this event */
  mutations: StepMutationSummary;
  /** [Agent-core] Whether this step produced observable DOM changes */
  has_changes: boolean;
  /** [Agent-core] Primary area where changes occurred (from areaLabel or astMatch) */
  change_area?: string | null;
  /** [Agent-core] Brief human-readable summary: Verb Target → Change */
  summary: string;
}

/** Result of building steps for a recording */
export interface OperationStepResult {
  recording_id: string;
  steps: OperationStep[];
  /** Total events processed */
  event_count: number;
  /** Total mutations processed */
  mutation_count: number;
  /** Number of mutations that were correlated to at least one step */
  mutations_correlated: number;
  /** Number of mutations that were not correlated to any step */
  mutations_uncorrelated: number;
}

// ---------------------------------------------------------------------------
// Agent-ready Step view — stable, minimal projection for Agent consumption
//
// Use this instead of OperationStep when feeding steps to an Agent.
// All fields are part of the stable contract.
// ---------------------------------------------------------------------------

/**
 * Stable, minimal representation of one step for Agent consumption.
 *
 * No-change semantics: has_changes=false does NOT mean the action failed.
 * Check no_change_reason for context. Possible reasons:
 *   - "no_mutations_observed" — no DOM mutations in the time window
 *   - "navigate" — navigation events don't produce same-document mutations
 *
 * Downstream consumers must NOT treat no-change as automatic failure.
 */
export interface AgentStepView {
  /** What event the user performed */
  event_type: RecordingEventType;
  /** Human-readable target description */
  target: string;
  /** Whether DOM changes were observed */
  has_changes: boolean;
  /** Total number of correlated mutations */
  mutation_total: number;
  /** Mutation breakdown by type */
  mutation_types: { childList: number; attributes: number; characterData: number };
  /** Primary area where changes occurred */
  change_area?: string | null;
  /** Structured summary: Verb Target → Change */
  summary: string;
  /** Why no changes were observed (null when has_changes is true) */
  no_change_reason?: string | null;
}

/** Agent-ready projection of an entire recording's steps */
export interface AgentStepListView {
  recording_id: string;
  steps: AgentStepView[];
  step_count: number;
  has_mutations: boolean;
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

// ---------------------------------------------------------------------------
// Autonomous Learning Mode types
//
// Core entities for the learning subsystem: success criteria definition,
// learned execution paths, exploration run records, and inline constraints.
// LearnedConstraint is stored inside LearnedPath.constraints_json (not a
// standalone DB table in v0.1).
// ---------------------------------------------------------------------------

// --- Success Criteria ---

export type SuccessCriteriaCategory =
  | 'submit_success'
  | 'search_success'
  | 'open_success'
  | 'save_success'
  | 'filter_success'
  | 'weak_success_no_error'
  | 'custom';

export type SuccessCriteriaStrength = 'strong' | 'weak';

export type SuccessCriteriaCreatedBy = 'system' | 'user';

export interface SuccessCondition {
  type: string;
  target?: string;
  value?: string;
  description?: string;
}

export interface SuccessCriteria {
  id: string;
  name: string;
  category: SuccessCriteriaCategory;
  strength: SuccessCriteriaStrength;
  description: string | null;
  conditions_json: SuccessCondition[];
  created_by: SuccessCriteriaCreatedBy;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface SuccessCriteriaCreate {
  name: string;
  category?: SuccessCriteriaCategory;
  strength?: SuccessCriteriaStrength;
  description?: string | null;
  conditions_json?: SuccessCondition[];
  created_by?: SuccessCriteriaCreatedBy;
  enabled?: boolean;
}

export interface SuccessCriteriaUpdate {
  name?: string;
  category?: SuccessCriteriaCategory;
  strength?: SuccessCriteriaStrength;
  description?: string | null;
  conditions_json?: SuccessCondition[];
  created_by?: SuccessCriteriaCreatedBy;
  enabled?: boolean;
}

// --- Learned Constraint (inline JSON structure, not a standalone table) ---

export type LearnedConstraintType =
  | 'required'
  | 'format'
  | 'range'
  | 'dependency'
  | 'visibility'
  | 'backend_validation'
  | 'unknown';

export interface LearnedConstraint {
  id?: string;
  field_key?: string;
  type: LearnedConstraintType;
  description: string;
  trigger?: string;
  evidence?: string[];
}

// --- Learned Path ---

export type LearnedPathStatus = 'candidate' | 'approved' | 'rejected';

export interface LearnedPath {
  id: string;
  page_signature: string | null;
  goal_type: string | null;
  success_criteria_id: string | null;
  steps_json: Record<string, unknown>[];
  variable_slots_json: Record<string, unknown>[];
  observed_effects_json: Record<string, unknown>[];
  constraints_json: LearnedConstraint[];
  user_labels_json: string[];
  recommended: boolean;
  confidence: number;
  status: LearnedPathStatus;
  created_at: string;
  updated_at: string;
}

export interface LearnedPathCreate {
  page_signature?: string | null;
  goal_type?: string | null;
  success_criteria_id?: string | null;
  steps_json?: Record<string, unknown>[];
  variable_slots_json?: Record<string, unknown>[];
  observed_effects_json?: Record<string, unknown>[];
  constraints_json?: LearnedConstraint[];
  user_labels_json?: string[];
  recommended?: boolean;
  confidence?: number;
  status?: LearnedPathStatus;
}

export interface LearnedPathUpdate {
  page_signature?: string | null;
  goal_type?: string | null;
  success_criteria_id?: string | null;
  steps_json?: Record<string, unknown>[];
  variable_slots_json?: Record<string, unknown>[];
  observed_effects_json?: Record<string, unknown>[];
  constraints_json?: LearnedConstraint[];
  user_labels_json?: string[];
  recommended?: boolean;
  confidence?: number;
  status?: LearnedPathStatus;
}

// --- Exploration Run ---

export type ExplorationMode = 'form' | 'search' | 'filter' | 'modal';

export type ExplorationRunStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed';

/**
 * A candidate interactive element identified from AST + mutation history.
 * Reserved for Phase 2 "interactive candidate element inference" layer.
 * The inference layer will extract elements likely to be clickable, inputtable,
 * or hoverable, score them by structural/class/aria/mutation signals, and
 * prioritize them for guided exploration instead of blind trial.
 */
export interface CandidateElement {
  /** Element identifier — AST node ID or locator */
  element_key: string;
  /** Inferred possible actions */
  inferred_actions: ('click' | 'input' | 'hover' | 'select' | 'toggle')[];
  /** Interaction likelihood score (0-1) */
  score: number;
  /** Signals that contributed to the score */
  evidence: {
    tag?: string;
    class_hints?: string[];
    role?: string;
    aria?: Record<string, string>;
    mutation_linkage?: boolean;
  };
  /** Exploration priority rank (lower = try first) */
  priority?: number;
}

/**
 * An interaction hint derived from candidate inference.
 * Suggests what to try and why during guided exploration.
 */
export interface InteractionHint {
  /** Target element key */
  element_key: string;
  /** Suggested action */
  action: 'click' | 'input' | 'hover' | 'select' | 'toggle';
  /** Why this interaction is suggested */
  reason: string;
  /** Expected effect based on historical mutations */
  expected_effect?: string;
  /** Priority rank */
  priority?: number;
}

export interface ExplorationRun {
  id: string;
  page_signature: string | null;
  mode: ExplorationMode;
  status: ExplorationRunStatus;
  success_criteria_ids_json: string[];
  strategy_json: Record<string, unknown>;
  summary: string | null;
  result_snapshot_json: Record<string, unknown> | null;
  /** Candidate interactive elements inferred from AST + mutation history */
  candidate_elements_json: CandidateElement[] | null;
  /** Prioritized exploration suggestions */
  interaction_hints_json: InteractionHint[] | null;
  created_at: string;
  updated_at: string;
}

export interface ExplorationRunCreate {
  page_signature?: string | null;
  mode?: ExplorationMode;
  status?: ExplorationRunStatus;
  success_criteria_ids_json?: string[];
  strategy_json?: Record<string, unknown>;
  summary?: string | null;
  result_snapshot_json?: Record<string, unknown> | null;
  candidate_elements_json?: CandidateElement[] | null;
  interaction_hints_json?: InteractionHint[] | null;
}

export interface ExplorationRunUpdate {
  page_signature?: string | null;
  mode?: ExplorationMode;
  status?: ExplorationRunStatus;
  success_criteria_ids_json?: string[];
  strategy_json?: Record<string, unknown>;
  summary?: string | null;
  result_snapshot_json?: Record<string, unknown> | null;
  candidate_elements_json?: CandidateElement[] | null;
  interaction_hints_json?: InteractionHint[] | null;
}
