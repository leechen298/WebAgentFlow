import { expect, test, type APIRequestContext } from '@playwright/test';

import { apiUrl, validationUrl } from '../../fixtures/config';
import { loadReplayFixtures, type ReplayFixture, type ReplayFixtureFile } from '../../fixtures/learnedPaths';

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
  previous_status: string;
  next_status: string;
  command_kind: string;
  user_response: string;
  events_appended: string[];
  allowed: boolean;
  error: string | null;
  replay_result: ConversationReplaySummary | null;
}

interface ConversationMessage {
  role: string;
  content: string;
  metadata: Record<string, unknown>;
}

interface ConversationEvent {
  type: string;
  payload: Record<string, unknown>;
}

let seeded: ReplayFixtureFile;

test.beforeAll(async () => {
  seeded = await loadReplayFixtures();
});

async function postEnvelope<T>(
  request: APIRequestContext,
  path: string,
  data: Record<string, unknown>,
): Promise<T> {
  const response = await request.post(apiUrl(path), { data });
  const text = await response.text();

  expect(response.status(), `${path} returned ${response.status()}: ${text}`).toBe(200);

  const body = JSON.parse(text) as ApiEnvelope<T>;
  expect(body.code).toBe(0);
  return body.data;
}

async function getEnvelope<T>(request: APIRequestContext, path: string): Promise<T> {
  const response = await request.get(apiUrl(path));
  const text = await response.text();

  expect(response.status(), `${path} returned ${response.status()}: ${text}`).toBe(200);

  const body = JSON.parse(text) as ApiEnvelope<T>;
  expect(body.code).toBe(0);
  return body.data;
}

async function createSession(request: APIRequestContext): Promise<ConversationSession> {
  const session = await postEnvelope<ConversationSession>(request, '/conversation/sessions', {});
  expect(session.status).toBe('idle');
  return session;
}

async function dispatch(
  request: APIRequestContext,
  sessionId: string,
  input: string,
): Promise<ConversationDispatchResponse> {
  return postEnvelope<ConversationDispatchResponse>(
    request,
    `/conversation/sessions/${sessionId}/dispatch`,
    { input },
  );
}

async function appendEvent(
  request: APIRequestContext,
  sessionId: string,
  type: string,
  payload: Record<string, unknown>,
): Promise<ConversationEvent> {
  return postEnvelope<ConversationEvent>(request, `/conversation/sessions/${sessionId}/events`, {
    type,
    payload,
  });
}

async function listEvents(
  request: APIRequestContext,
  sessionId: string,
): Promise<ConversationEvent[]> {
  return getEnvelope<ConversationEvent[]>(request, `/conversation/sessions/${sessionId}/events`);
}

async function listTranscript(
  request: APIRequestContext,
  sessionId: string,
): Promise<ConversationMessage[]> {
  return getEnvelope<ConversationMessage[]>(
    request,
    `/conversation/sessions/${sessionId}/transcript`,
  );
}

async function enterNaturalPlanConfirmed(request: APIRequestContext): Promise<ConversationSession> {
  const session = await createSession(request);
  const preview = await dispatch(request, session.id, 'e2e replay happy users');
  expect(preview.next_status).toBe('awaiting_confirmation');
  expect(preview.allowed).toBe(true);

  const confirm = await dispatch(request, session.id, 'confirm');
  expect(confirm.next_status).toBe('plan_confirmed');
  expect(confirm.allowed).toBe(true);

  return session;
}

async function enterSeededExecutionContext(
  request: APIRequestContext,
  fixture: ReplayFixture,
  targetUrl: string,
): Promise<ConversationSession> {
  const session = await enterNaturalPlanConfirmed(request);

  await appendEvent(request, session.id, 'plan_preview_proposed', {
    task_intent_raw_text: `seeded 11.1.7 reporter context for ${fixture.scenario}`,
    candidate_count: 1,
    planning_status: 'proposed',
    confirmation_required: true,
    selected_path_id: fixture.id,
    selected_purpose: fixture.purpose,
    target_url: targetUrl,
    route_summary: `Seeded confirmed execution context for ${fixture.scenario}`,
    route_steps: [{ order: 0, learned_path_id: fixture.id }],
    warnings: [],
    risk_hints: [],
    confirmation_requirements: [],
  });
  await appendEvent(request, session.id, 'plan_confirmed', {
    decision: 'confirm',
    selected_path_id: fixture.id,
    selected_purpose: fixture.purpose,
    replay_executed: false,
  });

  return session;
}

function indexOfEvent(
  events: ConversationEvent[],
  type: string,
  predicate: (event: ConversationEvent) => boolean = () => true,
): number {
  return events.findIndex((event) => event.type === type && predicate(event));
}

function indexOfEventAfter(
  events: ConversationEvent[],
  startIndex: number,
  type: string,
  predicate: (event: ConversationEvent) => boolean = () => true,
): number {
  const offset = events
    .slice(startIndex + 1)
    .findIndex((event) => event.type === type && predicate(event));
  return offset < 0 ? -1 : startIndex + 1 + offset;
}

function latestAgentMessage(messages: ConversationMessage[]): ConversationMessage | undefined {
  return [...messages].reverse().find((message) => message.role === 'agent');
}

function expectNoForbiddenReporterPayload(payload: Record<string, unknown>): void {
  const forbiddenKeys = [
    'raw_html',
    'html',
    'dom_html',
    'screenshot',
    'screenshot_payload',
    'screenshot_base64',
    'llm_output',
    'supervisor_output',
    'autonomous_run_id',
    'run_id',
    'user_id',
    'account_id',
    'tenant_id',
    'task_succeeded',
    'success_assertion',
    'verified_success',
  ];

  const stack: unknown[] = [payload];
  while (stack.length > 0) {
    const value = stack.pop();
    if (!value || typeof value !== 'object') {
      continue;
    }

    for (const [key, nested] of Object.entries(value as Record<string, unknown>)) {
      expect(forbiddenKeys).not.toContain(key);
      if (nested && typeof nested === 'object') {
        stack.push(nested);
      }
    }
  }
}

test.describe('Conversation 11.1.7 task result reporter E2E', () => {
  test('E2E-11-1-7-001 successful replay reports uncertain, not task succeeded', async ({
    request,
  }) => {
    const fixture = seeded.fixtures.happy;
    const targetUrl = validationUrl('/users');
    const session = await enterSeededExecutionContext(request, fixture, targetUrl);

    const execute = await dispatch(request, session.id, 'execute');
    expect(execute).toMatchObject({
      next_status: 'execution_finished',
      allowed: true,
      error: null,
    });
    expect(execute.user_response.toLowerCase()).toContain('could not verify');
    expect(execute.user_response.toLowerCase()).not.toContain('task succeeded');
    expect(execute.user_response.toLowerCase()).not.toContain('verified');
    expect(execute.replay_result).toMatchObject({
      learned_path_id: fixture.id,
      url: targetUrl,
      replay_status: 'succeeded',
      drift_status: 'none',
      error: null,
    });

    const events = await listEvents(request, session.id);
    const startedIndex = indexOfEvent(events, 'plan_execution_started');
    const completedIndex = indexOfEventAfter(events, startedIndex, 'plan_execution_completed');
    const reportedIndex = indexOfEventAfter(events, completedIndex, 'task_result_reported');

    expect(startedIndex).toBeGreaterThanOrEqual(0);
    expect(completedIndex).toBeGreaterThan(startedIndex);
    expect(reportedIndex).toBeGreaterThan(completedIndex);

    const reported = events[reportedIndex];
    expect(reported.payload).toMatchObject({
      learned_path_id: fixture.id,
      verification_outcome: 'uncertain',
      task_verified: false,
      needs_review: true,
      no_recovery: true,
      no_autonomous: true,
      no_llm: true,
      execution_status: 'completed',
      replay_status: 'succeeded',
      drift_status: 'none',
      error_summary: null,
    });
    expect(String(reported.payload.final_url ?? '')).toContain('/users?name=alice');
    expect(String(reported.payload.evidence_summary ?? '')).toContain('Replay status: succeeded');
    expect(String(reported.payload.missing_evidence_summary ?? '')).toContain(
      'no explicit postcondition evidence',
    );
    expectNoForbiddenReporterPayload(reported.payload);

    const transcript = await listTranscript(request, session.id);
    const finalMessage = latestAgentMessage(transcript);
    expect(finalMessage?.content.toLowerCase()).toContain('could not verify');
    expect(finalMessage?.content.toLowerCase()).not.toContain('task succeeded');
    expect(finalMessage?.metadata).toMatchObject({
      source: 'execution_gate',
      status: 'completed',
      verification_outcome: 'uncertain',
      needs_review: true,
    });
  });

  test('E2E-11-1-7-002 failed replay reports failed and no recovery', async ({
    request,
  }) => {
    const fixture = seeded.fixtures.targetMissing;
    const targetUrl = validationUrl('/users');
    const session = await enterSeededExecutionContext(request, fixture, targetUrl);

    const execute = await dispatch(request, session.id, 'execute');
    expect(execute).toMatchObject({
      next_status: 'execution_failed',
      allowed: true,
      error: null,
    });
    expect(execute.user_response.toLowerCase()).toContain('failed');
    expect(execute.user_response.toLowerCase()).toContain('no recovery was attempted');
    expect(execute.user_response.toLowerCase()).not.toContain('task succeeded');
    expect(execute.replay_result).toMatchObject({
      learned_path_id: fixture.id,
      url: targetUrl,
      replay_status: 'drifted',
      drift_status: 'target_missing',
    });

    const events = await listEvents(request, session.id);
    const startedIndex = indexOfEvent(events, 'plan_execution_started');
    const failedIndex = indexOfEventAfter(events, startedIndex, 'plan_execution_failed');
    const reportedIndex = indexOfEventAfter(events, failedIndex, 'task_result_reported');

    expect(startedIndex).toBeGreaterThanOrEqual(0);
    expect(failedIndex).toBeGreaterThan(startedIndex);
    expect(reportedIndex).toBeGreaterThan(failedIndex);

    const reported = events[reportedIndex];
    expect(reported.payload).toMatchObject({
      learned_path_id: fixture.id,
      verification_outcome: 'failed',
      task_verified: false,
      needs_review: false,
      no_recovery: true,
      no_autonomous: true,
      no_llm: true,
      execution_status: 'failed',
      replay_status: 'drifted',
      drift_status: 'target_missing',
      final_url: targetUrl,
    });
    expect(String(reported.payload.missing_evidence_summary ?? '')).toContain(
      'Replay did not complete successfully',
    );
    expectNoForbiddenReporterPayload(reported.payload);

    const transcript = await listTranscript(request, session.id);
    const finalMessage = latestAgentMessage(transcript);
    expect(finalMessage?.content.toLowerCase()).toContain('failed');
    expect(finalMessage?.content.toLowerCase()).toContain('no recovery was attempted');
    expect(finalMessage?.content.toLowerCase()).not.toContain('task succeeded');
    expect(finalMessage?.metadata).toMatchObject({
      source: 'execution_gate',
      status: 'failed',
      verification_outcome: 'failed',
      needs_review: false,
    });
  });

  test('E2E-11-1-7-003 blocked execution reports blocked', async ({ request }) => {
    const session = await enterNaturalPlanConfirmed(request);

    const execute = await dispatch(request, session.id, 'execute');
    expect(execute.next_status).toBe('plan_confirmed');
    expect(execute.allowed).toBe(false);
    expect(execute.replay_result).toBeNull();
    expect(execute.user_response.toLowerCase()).toMatch(
      /blocked|could not run|required evidence/,
    );

    const events = await listEvents(request, session.id);
    const blockedIndex = indexOfEvent(events, 'plan_execution_blocked');
    const reportedIndex = indexOfEventAfter(events, blockedIndex, 'task_result_reported');

    expect(blockedIndex).toBeGreaterThanOrEqual(0);
    expect(reportedIndex).toBeGreaterThan(blockedIndex);
    expect(events.map((event) => event.type)).not.toContain('plan_execution_started');
    expect(events.map((event) => event.type)).not.toContain('plan_execution_completed');
    expect(events.map((event) => event.type)).not.toContain('plan_execution_failed');
    expect(events.map((event) => event.type)).not.toContain('replay_completed');
    expect(events.map((event) => event.type)).not.toContain('replay_failed');

    const reported = events[reportedIndex];
    expect(reported.payload).toMatchObject({
      verification_outcome: 'blocked',
      task_verified: false,
      needs_review: false,
      no_recovery: true,
      no_autonomous: true,
      no_llm: true,
      execution_status: 'blocked',
      replay_status: null,
      drift_status: null,
      error_summary: null,
      final_url: null,
      final_title: null,
    });
    expectNoForbiddenReporterPayload(reported.payload);

    const transcript = await listTranscript(request, session.id);
    const finalMessage = latestAgentMessage(transcript);
    expect(finalMessage?.content.toLowerCase()).toMatch(
      /blocked|could not run|required evidence/,
    );
    expect(finalMessage?.metadata).toMatchObject({
      source: 'execution_gate',
      status: 'blocked',
      verification_outcome: 'blocked',
      needs_review: false,
    });
  });
});
