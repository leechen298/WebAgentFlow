/**
 * Frontend client for the autonomous-exploration HTTP API.
 *
 * Only the autonomous surface is covered here — /exploration/specs (spec
 * metadata for workbench prefill) and /exploration/autonomous-runs/*
 * (persisted run history + detail). The one-shot run stream lives in
 * ./autonomousStream.ts.
 */

import apiClient from './client';

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
  /**
   * Authoritative outcome gate; null for pre-gate historical rows.
   * The detail page uses this to explain *why* a run didn't sink into
   * a LearnedPath: `pass` but no learned_path_id = ingest hook failed
   * or predates the hook; `fail` / `unverified` = not a pass, expected
   * to be absent.
   */
  pass_gate_status?: 'pass' | 'fail' | 'unverified' | null;
  /**
   * LearnedPath auto-sunk from this run's `pass_gate = pass` outcome,
   * if any. Null means the run wasn't a clean pass or pre-dates the
   * ingest hook.
   */
  learned_path_id?: string | null;
  learned_path_trust?: LearnedPathTrust | null;
}

// ─── LearnedPath ────────────────────────────────────────────

export type LearnedPathTrust =
  | 'provisional'
  | 'confirmed'
  | 'flaky'
  | 'deprecated';

export type LearnedPathPatchStatus = 'confirmed' | 'deprecated' | 'flaky';

export interface LearnedPathSummary {
  id: string;
  page_template: string;
  query_signature: Record<string, string>;
  dom_fingerprint: string;
  scenario: string;
  provenance: string;
  trust: LearnedPathTrust;
  trust_reason: string | null;
  trust_updated_at: string | null;
  hit_count: number;
  source_run_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface LearnedPathDetail extends LearnedPathSummary {
  actions: Array<Record<string, unknown>>;
}

export interface LearnedPathListPage {
  items: LearnedPathSummary[];
  has_next: boolean;
  next_cursor: string | null;
}

export async function listLearnedPaths(params: {
  limit?: number;
  cursor?: string | null;
  page_template?: string | null;
  scenario?: string | null;
  trust?: LearnedPathTrust | null;
} = {}): Promise<LearnedPathListPage> {
  return (await apiClient.get('/exploration/learned-paths', {
    params: {
      limit: params.limit ?? 20,
      cursor: params.cursor ?? undefined,
      page_template: params.page_template ?? undefined,
      scenario: params.scenario ?? undefined,
      trust: params.trust ?? undefined,
    },
  })) as unknown as LearnedPathListPage;
}

export async function getLearnedPath(pathId: string): Promise<LearnedPathDetail> {
  return (await apiClient.get(
    `/exploration/learned-paths/${pathId}`,
  )) as unknown as LearnedPathDetail;
}

export async function patchLearnedPathTrust(
  pathId: string,
  payload: { status: LearnedPathPatchStatus; reason?: string | null },
): Promise<LearnedPathDetail> {
  return (await apiClient.patch(
    `/exploration/learned-paths/${pathId}/trust`,
    payload,
  )) as unknown as LearnedPathDetail;
}

export async function listAutonomousRuns(params: {
  limit?: number;
  cursor?: string | null;
  spec_id?: string | null;
  scenario?: string | null;
} = {}): Promise<AutonomousRunListPage> {
  return (await apiClient.get('/exploration/autonomous-runs', {
    params: {
      limit: params.limit ?? 20,
      cursor: params.cursor ?? undefined,
      spec_id: params.spec_id ?? undefined,
      scenario: params.scenario ?? undefined,
    },
  })) as unknown as AutonomousRunListPage;
}

export async function getAutonomousRun(runId: string): Promise<AutonomousRunDetail> {
  return (await apiClient.get(
    `/exploration/autonomous-runs/${runId}`,
  )) as unknown as AutonomousRunDetail;
}

export interface AutonomousRunDeleteResult {
  run_id: string;
  deleted: boolean;
  deleted_learned_path_ids: string[];
}

export async function deleteAutonomousRun(runId: string): Promise<AutonomousRunDeleteResult> {
  return (await apiClient.delete(
    `/exploration/autonomous-runs/${runId}`,
  )) as unknown as AutonomousRunDeleteResult;
}
