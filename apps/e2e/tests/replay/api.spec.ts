import { expect, test, type APIRequestContext } from '@playwright/test';

import { apiUrl, validationUrl } from '../../fixtures/config';
import {
  loadReplayFixtures,
  type ReplayFixtureFile,
  type ReplayFixtureName,
} from '../../fixtures/learnedPaths';

interface ApiEnvelope<T> {
  code: number;
  msg: string;
  data: T;
}

interface ReplayResult {
  status: string;
  drift_status: string;
  drift_reasons: string[];
  warnings: string[];
  steps: unknown[];
  final_url: string | null;
  final_title: string | null;
}

let seeded: ReplayFixtureFile;

test.beforeAll(async () => {
  seeded = await loadReplayFixtures();
});

async function replay(
  request: APIRequestContext,
  name: ReplayFixtureName,
  url: string = validationUrl('/users'),
): Promise<{ status: number; body: ApiEnvelope<ReplayResult> }> {
  const fixture = seeded.fixtures[name];
  const response = await request.post(apiUrl(`/exploration/learned-paths/${fixture.id}/replay`), {
    data: { url },
  });
  const body = (await response.json()) as ApiEnvelope<ReplayResult>;
  return { status: response.status(), body };
}

test.describe('LearnedPath replay API E2E', () => {
  test('happy path succeeds with no drift', async ({ request }) => {
    const { status, body } = await replay(request, 'happy');

    expect(status).toBe(200);
    expect(body.code).toBe(0);
    expect(body.data.status).toBe('succeeded');
    expect(body.data.drift_status).toBe('none');
    expect(body.data.steps.length).toBeGreaterThan(0);
  });

  test('observational path reports observed with no steps', async ({ request }) => {
    const { status, body } = await replay(request, 'observational');

    expect(status).toBe(200);
    expect(body.code).toBe(0);
    expect(body.data.status).toBe('observed');
    expect(body.data.steps).toEqual([]);
  });

  test('page mismatch blocks replay', async ({ request }) => {
    const { status, body } = await replay(request, 'pageMismatch', validationUrl('/login'));

    expect(status).toBe(200);
    expect(body.code).toBe(0);
    expect(body.data.status).toBe('drifted');
    expect(body.data.drift_status).toBe('page_mismatch');
  });

  test('target missing blocks replay', async ({ request }) => {
    const { status, body } = await replay(request, 'targetMissing');

    expect(status).toBe(200);
    expect(body.code).toBe(0);
    expect(body.data.status).toBe('drifted');
    expect(body.data.drift_status).toBe('target_missing');
  });

  test('unsupported action reports unsupported action drift', async ({ request }) => {
    const { status, body } = await replay(request, 'unsupportedAction');

    expect(status).toBe(200);
    expect(body.code).toBe(0);
    expect(body.data.status).toBe('unsupported');
    expect(body.data.drift_status).toBe('unsupported_action');
  });

  test('flaky path replays with trust warning', async ({ request }) => {
    const { status, body } = await replay(request, 'flaky');

    expect(status).toBe(200);
    expect(body.code).toBe(0);
    expect(body.data.warnings.join(' ')).toContain('flaky');
  });

  test('deprecated path returns 422', async ({ request }) => {
    const { status, body } = await replay(request, 'deprecated');

    expect(status).toBe(422);
    expect(body.code).toBe(422);
  });

  test('signature changed remains executable when targets still match', async ({ request }) => {
    const { status, body } = await replay(request, 'signatureChanged');

    expect(status).toBe(200);
    expect(body.code).toBe(0);
    expect(['succeeded', 'observed']).toContain(body.data.status);
    expect(body.data.drift_status).toBe('signature_changed');
    expect(body.data.warnings.length).toBeGreaterThan(0);
  });
});
