import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import type { APIRequestContext } from '@playwright/test';

import { apiUrl } from './config';

export type ReplayFixtureName =
  | 'happy'
  | 'observational'
  | 'pageMismatch'
  | 'targetMissing'
  | 'unsupportedAction'
  | 'flaky'
  | 'deprecated'
  | 'signatureChanged';

export interface ReplayFixture {
  id: string;
  scenario: string;
  trust: string;
  purpose: string;
}

export interface ReplayFixtureFile {
  generated_at: string;
  validation_base_url: string;
  fixtures: Record<ReplayFixtureName, ReplayFixture>;
}

export interface LearnedPathSummary {
  id: string;
  page_template: string;
  scenario: string;
  trust: string;
}

const here = path.dirname(fileURLToPath(import.meta.url));
const fixtureFile = path.resolve(here, '../.tmp/replay-fixtures.json');

export async function loadReplayFixtures(): Promise<ReplayFixtureFile> {
  try {
    const raw = await readFile(fixtureFile, 'utf8');
    return JSON.parse(raw) as ReplayFixtureFile;
  } catch (error) {
    throw new Error(
      `Missing E2E replay fixtures at ${fixtureFile}. ` +
        'Run `.venv/bin/python apps/e2e/scripts/seed-replay-fixtures.py` first. ' +
        `Original error: ${(error as Error).message}`,
    );
  }
}

export async function fetchSeededLearnedPathByScenario(
  request: APIRequestContext,
  scenario: string,
): Promise<LearnedPathSummary> {
  const response = await request.get(apiUrl('/exploration/learned-paths'), {
    params: { scenario, limit: '1' },
  });
  if (!response.ok()) {
    throw new Error(
      `Failed to fetch LearnedPath scenario=${scenario}: ` +
        `${response.status()} ${await response.text()}`,
    );
  }

  const body = (await response.json()) as {
    code: number;
    data?: { items?: LearnedPathSummary[] };
  };
  const item = body.data?.items?.[0];
  if (!item) {
    throw new Error(`Seeded LearnedPath not found for scenario=${scenario}`);
  }
  return item;
}
