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
