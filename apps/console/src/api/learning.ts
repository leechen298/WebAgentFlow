import apiClient from './client';

export interface InferCandidatesParams {
  recording_id: string;
  run_id?: string | null;
  score_threshold?: number;
  max_candidates?: number;
}

export interface CandidateEvidence {
  tag?: string;
  class_hints?: string[];
  role?: string;
  aria?: Record<string, string>;
  component_lib?: string;
  text_intent?: string;
  icon_intent?: string[];
  mutation_linkage?: boolean;
}

export interface CandidateElement {
  element_key: string;
  inferred_actions: string[];
  score: number;
  evidence: CandidateEvidence;
  priority: number;
}

export interface InteractionHint {
  element_key: string;
  action: string;
  reason: string;
  expected_effect: string | null;
  priority: number;
}

export interface InferCandidatesResult {
  recording_id: string;
  candidate_count: number;
  hint_count: number;
  candidate_elements: CandidateElement[];
  interaction_hints: InteractionHint[];
  written_to_run: string | null;
}

export async function inferCandidates(
  params: InferCandidatesParams,
): Promise<InferCandidatesResult> {
  return (await apiClient.post(
    '/learning/runs/infer-candidates',
    params,
  )) as unknown as InferCandidatesResult;
}
