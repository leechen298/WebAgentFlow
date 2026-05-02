import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  listLearnedPaths,
  getLearnedPath,
  patchLearnedPathTrust,
  type LearnedPathDetail,
  type LearnedPathListPage,
} from '@/api/exploration';

const { get, patch } = vi.hoisted(() => ({
  get: vi.fn(),
  patch: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  default: { get, patch },
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
