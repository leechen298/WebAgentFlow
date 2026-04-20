import apiClient from './client';

// ─── Task definition types ───────────────────────────────────

export interface TaskListItem {
  id: string;
  name: string;
  description: string;
  target_url: string;
  step_count: number;
  source: string;
  variables: Record<string, unknown>;
}

export interface TaskStepHint {
  role?: string | null;
  name?: string | null;
  tag?: string | null;
  selector?: string | null;
  text?: string | null;
  placeholder?: string | null;
}

export interface TaskStepSuccessCriteria {
  conditions: Array<{
    type: string;
    value?: string | null;
    value_from?: string | null;
    required: boolean;
  }>;
}

export interface TaskStep {
  intent: string;
  action_type: string;
  target_hint?: TaskStepHint | null;
  value?: string | null;
  value_from?: string | null;
  success_criteria?: TaskStepSuccessCriteria | null;
}

export interface TaskDefinition {
  id: string;
  name: string;
  description: string;
  target_url: string;
  variables: Record<string, unknown>;
  steps: TaskStep[];
  global_success_criteria?: TaskStepSuccessCriteria | null;
  source: string;
  provenance: string;
  revision: number;
}

// ─── Exploration run types ───────────────────────────────────

export interface SupervisorAssessment {
  verdict: string;
  confidence: string;
  summary: string;
  step_assessments: Array<{
    step_index: number;
    status: string;
    note: string;
  }>;
  anomalies: string[];
  suggestions: string[];
  should_save_path: boolean;
}

export interface ExplorationStepData {
  step_index: number;
  intent: string;
  action_type: string;
  target_summary: string;
  value?: string | null;
  timestamp_ms: number;
  agent_note?: string | null;
  execution_result?: Record<string, unknown> | null;
  observation?: Record<string, unknown> | null;
  success_evaluation?: {
    satisfied: boolean;
    strength: string;
    confidence: string;
    matched_conditions: string[];
    failed_conditions: string[];
    evidence: Record<string, unknown>;
    uncertain_reason?: string | null;
  } | null;
}

export interface RunExplorationResponse {
  success: boolean;
  total_steps: number;
  final_url: string;
  final_title: string;
  elapsed_ms: number | null;
  summary: string;
  final_screenshot_ref?: string | null;
  steps: ExplorationStepData[];
  supervisor?: SupervisorAssessment | null;
}

export interface RunExplorationParams {
  task_id: string;
  variables?: Record<string, unknown>;
  headless?: boolean;
  max_steps?: number | null;
}

// ─── API functions ───────────────────────────────────────────

export async function listTasks(): Promise<TaskListItem[]> {
  return (await apiClient.get('/exploration/tasks')) as unknown as TaskListItem[];
}

export async function getTask(taskId: string): Promise<TaskDefinition> {
  return (await apiClient.get(`/exploration/tasks/${taskId}`)) as unknown as TaskDefinition;
}

export async function runExploration(
  params: RunExplorationParams,
): Promise<RunExplorationResponse> {
  // Exploration is synchronous and blocking — may take minutes.
  return (await apiClient.post('/exploration/run', params, {
    timeout: 300_000,
  })) as unknown as RunExplorationResponse;
}

export async function approveRun(runId: string, note?: string): Promise<Record<string, string>> {
  return (await apiClient.post(
    `/exploration/runs/${runId}/approve`,
    { run_id: runId, note: note ?? '' },
  )) as unknown as Record<string, string>;
}

export async function rejectRun(runId: string, note?: string): Promise<Record<string, string>> {
  return (await apiClient.post(
    `/exploration/runs/${runId}/reject`,
    { run_id: runId, note: note ?? '' },
  )) as unknown as Record<string, string>;
}

// ─── Page verification specs ─────────────────────────────────

export interface SpecScenarioSummary {
  key: string;
  description: string;
  inputs: Record<string, string>;
  selections: Record<string, string>;
  expected_verdict?: string | null;
  expected_verdict_not?: string | null;
}

export interface SpecSummary {
  spec_id: string;
  page_id: string;
  url_pattern: string;
  description: string;
  scenarios: SpecScenarioSummary[];
}

export async function listSpecs(): Promise<SpecSummary[]> {
  return (await apiClient.get('/exploration/specs')) as unknown as SpecSummary[];
}

export async function getSpec(specId: string): Promise<SpecSummary> {
  return (await apiClient.get(`/exploration/specs/${specId}`)) as unknown as SpecSummary;
}

// ─── Persisted autonomous runs ───────────────────────────────

export interface AutonomousRunSummary {
  run_id: string;
  created_at: string;
  spec_id?: string | null;
  scenario?: string | null;
  verdict?: string | null;
  /**
   * True when the scenario's rubric accepted this run (positive-path
   * scenarios match on `verdict=success`; negative-path scenarios
   * like invalid_credentials match on the expected failure signals).
   * Null for ad-hoc / pre-feature runs that don't have verdict_check.
   */
  scenario_matched?: boolean | null;
  /**
   * Authoritative pass/fail/unverified status — the strict gate the
   * UI reads as the primary outcome. Null for pre-gate persisted rows
   * (the list falls back to scenario_matched in that case).
   */
  pass_gate_status?: 'pass' | 'fail' | 'unverified' | null;
  status: string;
  url?: string | null;
  summary?: string | null;
}

export interface AutonomousRunListPage {
  items: AutonomousRunSummary[];
  has_next: boolean;
  next_cursor: string | null;
}

export interface AutonomousRunDetail {
  run_id: string;
  created_at: string;
  updated_at: string;
  status: string;
  strategy: Record<string, unknown>;
  summary: string | null;
  result: Record<string, unknown> | null;
}

export async function listAutonomousRuns(params: {
  limit?: number;
  cursor?: string | null;
  spec_id?: string | null;
  scenario?: string | null;
} = {}): Promise<AutonomousRunListPage> {
  return (await apiClient.get('/exploration/autonomous-runs/list', {
    params: {
      limit: params.limit ?? 20,
      cursor: params.cursor ?? undefined,
      spec_id: params.spec_id ?? undefined,
      scenario: params.scenario ?? undefined,
    },
  })) as unknown as AutonomousRunListPage;
}

export async function getAutonomousRun(runId: string): Promise<AutonomousRunDetail> {
  return (await apiClient.get('/exploration/autonomous-runs/get', {
    params: { run_id: runId },
  })) as unknown as AutonomousRunDetail;
}
