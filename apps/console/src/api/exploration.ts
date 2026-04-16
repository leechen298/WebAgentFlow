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
  return (await apiClient.post('/exploration/run', params)) as unknown as RunExplorationResponse;
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
