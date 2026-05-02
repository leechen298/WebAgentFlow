import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  listSpecs,
  getSpec,
  listAutonomousRuns,
  getAutonomousRun,
  patchRunReview,
  deleteAutonomousRun,
  listLearnedPaths,
  getLearnedPath,
  patchLearnedPathTrust,
  type LearnedPathDetail,
  type LearnedPathListPage,
} from '@/api/exploration';

const { get, patch, delete: del } = vi.hoisted(() => ({
  get: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  default: { get, patch, delete: del },
}));

describe('LearnedPath API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('listLearnedPaths forwards filters to the backend', async () => {
    const page: LearnedPathListPage = {
      items: [],
      has_next: false,
      next_cursor: null,
    };
    get.mockResolvedValueOnce(page);

    await expect(
      listLearnedPaths({
        limit: 50,
        trust: 'provisional',
        scenario: 'filter_by_status',
      }),
    ).resolves.toEqual(page);

    expect(get).toHaveBeenCalledWith('/exploration/learned-paths', {
      params: {
        limit: 50,
        cursor: undefined,
        page_template: undefined,
        scenario: 'filter_by_status',
        trust: 'provisional',
      },
    });
  });

  it('listLearnedPaths defaults limit to 20', async () => {
    get.mockResolvedValueOnce({ items: [], has_next: false, next_cursor: null });
    await listLearnedPaths();
    expect(get).toHaveBeenCalledWith('/exploration/learned-paths', {
      params: {
        limit: 20,
        cursor: undefined,
        page_template: undefined,
        scenario: undefined,
        trust: undefined,
      },
    });
  });

  it('getLearnedPath hits the detail route', async () => {
    const detail: LearnedPathDetail = {
      id: 'abc',
      page_template: '/users',
      query_signature: {},
      dom_fingerprint: 'x'.repeat(64),
      scenario: 'filter_by_status',
      provenance: 'system',
      trust: 'provisional',
      trust_reason: null,
      trust_updated_at: null,
      hit_count: 1,
      source_run_id: null,
      created_at: '2026-04-24T00:00:00Z',
      updated_at: '2026-04-24T00:00:00Z',
      actions: [],
    };
    get.mockResolvedValueOnce(detail);

    await expect(getLearnedPath('abc')).resolves.toEqual(detail);
    expect(get).toHaveBeenCalledWith('/exploration/learned-paths/abc');
  });

  it('patchLearnedPathTrust PATCHes the trust subresource', async () => {
    const updated = {
      id: 'abc',
      trust: 'confirmed' as const,
    } as LearnedPathDetail;
    patch.mockResolvedValueOnce(updated);

    await expect(
      patchLearnedPathTrust('abc', { status: 'confirmed', reason: 'ok' }),
    ).resolves.toEqual(updated);

    expect(patch).toHaveBeenCalledWith(
      '/exploration/learned-paths/abc/trust',
      { status: 'confirmed', reason: 'ok' },
    );
  });
});

// ─── Spec API ──────────────────────────────────────────────────

describe('Spec API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('listSpecs fetches the spec list', async () => {
    const specs = [{ spec_id: 'login', page_id: 'login', url_pattern: 'http://x/login', description: 'd', scenarios: [] }];
    get.mockResolvedValueOnce(specs);
    await expect(listSpecs()).resolves.toEqual(specs);
    expect(get).toHaveBeenCalledWith('/exploration/specs');
  });

  it('getSpec fetches a single spec by id', async () => {
    const spec = { spec_id: 'login', page_id: 'login', url_pattern: 'http://x/', description: 'd', scenarios: [] };
    get.mockResolvedValueOnce(spec);
    await expect(getSpec('login')).resolves.toEqual(spec);
    expect(get).toHaveBeenCalledWith('/exploration/specs/login');
  });
});

// ─── Autonomous Runs API ───────────────────────────────────────

describe('Autonomous Runs API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('listAutonomousRuns forwards filters', async () => {
    const page = { items: [], has_next: false, next_cursor: null };
    get.mockResolvedValueOnce(page);
    await expect(listAutonomousRuns({ limit: 10, spec_id: 'login', scenario: 'valid' })).resolves.toEqual(page);
    expect(get).toHaveBeenCalledWith('/exploration/autonomous-runs', {
      params: { limit: 10, cursor: undefined, spec_id: 'login', scenario: 'valid' },
    });
  });

  it('listAutonomousRuns defaults limit to 20', async () => {
    get.mockResolvedValueOnce({ items: [], has_next: false, next_cursor: null });
    await listAutonomousRuns();
    expect(get).toHaveBeenCalledWith('/exploration/autonomous-runs', {
      params: { limit: 20, cursor: undefined, spec_id: undefined, scenario: undefined },
    });
  });

  it('getAutonomousRun fetches a single run', async () => {
    const run = { run_id: 'abc', created_at: '', updated_at: '', status: 'done', strategy: {}, summary: null, result: null };
    get.mockResolvedValueOnce(run);
    await expect(getAutonomousRun('abc')).resolves.toEqual(run);
    expect(get).toHaveBeenCalledWith('/exploration/autonomous-runs/abc');
  });

  it('patchRunReview sends review payload', async () => {
    const resp = { run_id: 'abc', operator_review_status: 'accepted', operator_review_note: null, operator_reviewed_at: null, learned_path: null };
    patch.mockResolvedValueOnce(resp);
    await expect(patchRunReview('abc', { status: 'accepted', note: 'good' })).resolves.toEqual(resp);
    expect(patch).toHaveBeenCalledWith('/exploration/autonomous-runs/abc/review', { status: 'accepted', note: 'good' });
  });

  it('deleteAutonomousRun sends DELETE', async () => {
    const resp = { run_id: 'abc', deleted: true, deleted_learned_path_ids: [] };
    del.mockResolvedValueOnce(resp);
    await expect(deleteAutonomousRun('abc')).resolves.toEqual(resp);
    expect(del).toHaveBeenCalledWith('/exploration/autonomous-runs/abc');
  });
});
