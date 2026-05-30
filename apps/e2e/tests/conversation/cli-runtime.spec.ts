import { execFile } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

import { expect, test } from '@playwright/test';

import { apiBaseUrl } from '../../fixtures/config';
import { loadReplayFixtures, type ReplayFixtureFile } from '../../fixtures/learnedPaths';

const execFileAsync = promisify(execFile);

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '../../../..');
const wagentBin = process.env.E2E_WAGENT_BIN ?? path.resolve(repoRoot, '.venv/bin/wagent');

interface ConversationSession {
  id: string;
  status: string;
}

interface ConversationReplaySummary {
  learned_path_id: string;
  url: string;
  replay_status: string;
  drift_status: string;
  step_count: number;
  error: string | null;
}

interface ConversationDispatchResponse {
  session_id: string;
  next_status: string;
  command_kind: string;
  allowed: boolean;
  error: string | null;
  replay_result: ConversationReplaySummary | null;
}

interface ConversationMessage {
  role: string;
  content: string;
}

interface ConversationEvent {
  type: string;
  payload: Record<string, unknown>;
}

let seeded: ReplayFixtureFile;

test.beforeAll(async () => {
  seeded = await loadReplayFixtures();
});

test.skip(!existsSync(wagentBin), `Missing wagent binary at ${wagentBin}`);

async function runWagentJson<T>(args: string[]): Promise<T> {
  const { stdout, stderr } = await execFileAsync(wagentBin, args, {
    cwd: repoRoot,
    env: {
      ...process.env,
      WBAF_API_BASE: apiBaseUrl,
    },
    timeout: 30_000,
    maxBuffer: 1024 * 1024,
  });

  expect(stderr.trim()).toBe('');
  return JSON.parse(stdout) as T;
}

test.describe('wagent conversation CLI E2E', () => {
  test('drives explicit replay through the runtime CLI', async () => {
    const session = await runWagentJson<ConversationSession>([
      'conversation',
      'start',
    ]);
    expect(session.status).toBe('idle');
    expect(session.id).toBeTruthy();

    const fixture = seeded.fixtures.happy;
    const targetUrl = fixture.target_url;
    const command = `/replay ${fixture.id} ${targetUrl}`;

    const dispatch = await runWagentJson<ConversationDispatchResponse>([
      'conversation',
      'send',
      session.id,
      '--content',
      command,
    ]);

    expect(dispatch).toMatchObject({
      session_id: session.id,
      command_kind: 'replay',
      allowed: true,
      next_status: 'completed',
      error: null,
    });
    expect(dispatch.replay_result).toMatchObject({
      learned_path_id: fixture.id,
      url: targetUrl,
      replay_status: 'succeeded',
      drift_status: 'none',
      error: null,
    });
    expect(dispatch.replay_result?.step_count).toBeGreaterThan(0);

    const status = await runWagentJson<ConversationSession>([
      'conversation',
      'status',
      session.id,
    ]);
    expect(status.status).toBe('completed');

    const transcript = await runWagentJson<ConversationMessage[]>([
      'conversation',
      'transcript',
      session.id,
    ]);
    expect(transcript).toHaveLength(1);
    expect(transcript[0]).toMatchObject({
      role: 'user',
      content: command,
    });

    const events = await runWagentJson<ConversationEvent[]>([
      'conversation',
      'events',
      session.id,
      '--limit',
      '20',
    ]);
    const eventTypes = events.map((event) => event.type);

    expect(eventTypes).toContain('command_parsed');
    expect(eventTypes).toContain('state_changed');
    expect(eventTypes).toContain('replay_completed');
    expect(eventTypes).not.toContain('replay_failed');
  });
});
