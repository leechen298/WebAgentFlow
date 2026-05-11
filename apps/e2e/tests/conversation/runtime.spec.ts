import { expect, test, type APIRequestContext } from '@playwright/test';

import { apiUrl, validationUrl } from '../../fixtures/config';
import { loadReplayFixtures, type ReplayFixtureFile } from '../../fixtures/learnedPaths';

interface ApiEnvelope<T> {
  code: number;
  msg: string;
  data: T;
}

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

async function createSession(request: APIRequestContext): Promise<ConversationSession> {
  const response = await request.post(apiUrl('/conversation/sessions'), {
    data: {},
  });
  const body = (await response.json()) as ApiEnvelope<ConversationSession>;

  expect(response.status()).toBe(200);
  expect(body.code).toBe(0);
  expect(body.data.status).toBe('idle');

  return body.data;
}

test.describe('Conversation runtime E2E', () => {
  test('dispatches explicit replay and records transcript and events', async ({ request }) => {
    const session = await createSession(request);
    const fixture = seeded.fixtures.happy;
    const targetUrl = validationUrl('/users');
    const command = `/replay ${fixture.id} ${targetUrl}`;

    const dispatchResponse = await request.post(
      apiUrl(`/conversation/sessions/${session.id}/dispatch`),
      { data: { input: command } },
    );
    const dispatchBody =
      (await dispatchResponse.json()) as ApiEnvelope<ConversationDispatchResponse>;

    expect(dispatchResponse.status()).toBe(200);
    expect(dispatchBody.code).toBe(0);
    expect(dispatchBody.data.session_id).toBe(session.id);
    expect(dispatchBody.data.command_kind).toBe('replay');
    expect(dispatchBody.data.allowed).toBe(true);
    expect(dispatchBody.data.next_status).toBe('completed');
    expect(dispatchBody.data.error).toBeNull();
    expect(dispatchBody.data.replay_result).toMatchObject({
      learned_path_id: fixture.id,
      url: targetUrl,
      replay_status: 'succeeded',
      drift_status: 'none',
      error: null,
    });
    expect(dispatchBody.data.replay_result?.step_count).toBeGreaterThan(0);

    const sessionResponse = await request.get(apiUrl(`/conversation/sessions/${session.id}`));
    const sessionBody = (await sessionResponse.json()) as ApiEnvelope<ConversationSession>;
    expect(sessionResponse.status()).toBe(200);
    expect(sessionBody.data.status).toBe('completed');

    const transcriptResponse = await request.get(
      apiUrl(`/conversation/sessions/${session.id}/transcript`),
    );
    const transcriptBody =
      (await transcriptResponse.json()) as ApiEnvelope<ConversationMessage[]>;
    expect(transcriptResponse.status()).toBe(200);
    expect(transcriptBody.data).toHaveLength(1);
    expect(transcriptBody.data[0]).toMatchObject({
      role: 'user',
      content: command,
    });

    const eventsResponse = await request.get(apiUrl(`/conversation/sessions/${session.id}/events`));
    const eventsBody = (await eventsResponse.json()) as ApiEnvelope<ConversationEvent[]>;
    expect(eventsResponse.status()).toBe(200);

    const eventTypes = eventsBody.data.map((event) => event.type);
    expect(eventTypes).toContain('command_parsed');
    expect(eventTypes).toContain('state_changed');
    expect(eventTypes).toContain('replay_completed');
    expect(eventTypes).not.toContain('replay_failed');

    const replayCompleted = eventsBody.data.find((event) => event.type === 'replay_completed');
    expect(replayCompleted?.payload).toMatchObject({
      learned_path_id: fixture.id,
      replay_status: 'succeeded',
      drift_status: 'none',
    });
  });
});
