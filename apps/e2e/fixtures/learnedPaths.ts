import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

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
