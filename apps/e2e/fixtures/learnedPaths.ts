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
  target_url: string;
  mismatch_url?: string;
  expected_final_url_contains?: string;
}

export interface ReplayFixtureFile {
  generated_at: string;
  provider: {
    kind: string;
    name?: string;
  };
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
        'Generate it from the external Fixture-Site provider first. ' +
        `Original error: ${(error as Error).message}`,
    );
  }
}
