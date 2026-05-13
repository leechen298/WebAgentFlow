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
  const body = (await response.json()) as ApiEnvelope<T>;

  expect(response.status()).toBe(200);
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

async function enterNaturalPlanConfirmed(
  request: APIRequestContext,
): Promise<{ session: ConversationSession; previewInput: string; selectedPathId: string }> {
  const session = await createSession(request);
  const previewInput = 'e2e replay happy users';
  const preview = await dispatch(request, session.id, previewInput);
  expect(preview.next_status).toBe('awaiting_confirmation');
  expect(preview.allowed).toBe(true);

  const previewEvents = await listEvents(request, session.id);
  const naturalPreview = [...previewEvents]
    .reverse()
    .find((event) => event.type === 'plan_preview_proposed');
  expect(naturalPreview).toBeTruthy();
  const selectedPathId = String(naturalPreview?.payload.selected_path_id ?? '');
  expect(selectedPathId).toBeTruthy();

  const confirm = await dispatch(request, session.id, 'confirm');
  expect(confirm.next_status).toBe('plan_confirmed');
  expect(confirm.allowed).toBe(true);

  return { session, previewInput, selectedPathId };
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

function expectNoExecutionOrReplayEvents(events: ConversationEvent[]): void {
  const eventTypes = events.map((event) => event.type);
  expect(eventTypes).not.toContain('plan_execution_started');
  expect(eventTypes).not.toContain('plan_execution_completed');
  expect(eventTypes).not.toContain('replay_completed');
}

test.describe('Conversation 11.1.6 task execution E2E', () => {
  test('E2E-11-1-6-001A seeded confirmed execution context executes replay', async ({
    request,
  }) => {
    const { session } = await enterNaturalPlanConfirmed(request);
    const fixture = seeded.fixtures.happy;
    const targetUrl = validationUrl('/users');

    await appendEvent(request, session.id, 'plan_preview_proposed', {
      task_intent_raw_text: 'seeded confirmed execution context',
      candidate_count: 1,
      planning_status: 'proposed',
      confirmation_required: true,
      selected_path_id: fixture.id,
      selected_purpose: fixture.purpose,
      target_url: targetUrl,
      route_summary: 'Seeded confirmed execution context for 11.1.6 E2E',
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

    const execute = await dispatch(request, session.id, 'execute');
    expect(execute).toMatchObject({
      session_id: session.id,
      next_status: 'execution_finished',
      command_kind: 'free_text',
      allowed: true,
      error: null,
    });
    expect(execute.user_response.toLowerCase()).toContain('could not verify');
    expect(execute.replay_result).toMatchObject({
      learned_path_id: fixture.id,
      url: targetUrl,
      replay_status: 'succeeded',
      drift_status: 'none',
      error: null,
    });
    expect(execute.replay_result?.step_count).toBeGreaterThan(0);

    const events = await listEvents(request, session.id);
    const supplementalPreviewIndex = indexOfEvent(
      events,
      'plan_preview_proposed',
      (event) => event.payload.selected_path_id === fixture.id && event.payload.target_url === targetUrl,
    );
    const supplementalConfirmIndex = indexOfEventAfter(
      events,
      supplementalPreviewIndex,
      'plan_confirmed',
      (event) => event.payload.selected_path_id === fixture.id,
    );
    const commandIndex = indexOfEventAfter(
      events,
      supplementalConfirmIndex,
      'command_parsed',
      (event) => event.payload.raw === 'execute' && event.payload.gate === 'plan_confirmed',
    );
    const executingIndex = indexOfEventAfter(
      events,
      commandIndex,
      'state_changed',
      (event) => event.payload.from === 'plan_confirmed' && event.payload.to === 'executing',
    );
    const startedIndex = indexOfEventAfter(events, executingIndex, 'plan_execution_started');
    const completedIndex = indexOfEventAfter(events, startedIndex, 'plan_execution_completed');
    const reportedIndex = indexOfEventAfter(events, completedIndex, 'task_result_reported');
    const finishedIndex = indexOfEventAfter(
      events,
      reportedIndex,
      'state_changed',
      (event) => event.payload.from === 'executing' && event.payload.to === 'execution_finished',
    );

    expect(supplementalPreviewIndex).toBeGreaterThanOrEqual(0);
    expect(supplementalConfirmIndex).toBeGreaterThan(supplementalPreviewIndex);
    expect(commandIndex).toBeGreaterThan(supplementalConfirmIndex);
    expect(executingIndex).toBeGreaterThan(commandIndex);
    expect(startedIndex).toBeGreaterThan(executingIndex);
    expect(completedIndex).toBeGreaterThan(startedIndex);
    expect(reportedIndex).toBeGreaterThan(completedIndex);
    expect(finishedIndex).toBeGreaterThan(reportedIndex);

    const completed = events[completedIndex];
    expect(completed.payload).toMatchObject({
      learned_path_id: fixture.id,
      target_url: targetUrl,
      replay_status: 'succeeded',
      no_result_verification: true,
      task_verified: false,
      no_autonomous: true,
    });

    const reported = events[reportedIndex];
    expect(reported.payload).toMatchObject({
      learned_path_id: fixture.id,
      verification_outcome: 'uncertain',
      task_verified: false,
      needs_review: true,
      no_recovery: true,
      no_autonomous: true,
      no_llm: true,
    });
    expect(String(reported.payload.evidence_summary ?? '')).toContain('Replay status: succeeded');
    expect(String(reported.payload.missing_evidence_summary ?? '')).toContain(
      'no explicit postcondition evidence',
    );
    // Structured payload fields (follow-up fix)
    expect(reported.payload.execution_status).toBe('completed');
    expect(reported.payload.replay_status).toBe('succeeded');
    expect(reported.payload.drift_status).toBe('none');

    const transcript = await listTranscript(request, session.id);
    const finalAgentMessage = [...transcript]
      .reverse()
      .find((message) => message.role === 'agent');
    expect(finalAgentMessage?.content.toLowerCase()).toContain('could not verify');
    expect(finalAgentMessage?.metadata).toMatchObject({
      source: 'execution_gate',
      status: 'completed',
      verification_outcome: 'uncertain',
      needs_review: true,
    });
  });

  test('E2E-11-1-6-001B natural planning flow blocks execution without target_url', async ({
    request,
  }) => {
    const { session } = await enterNaturalPlanConfirmed(request);

    const execute = await dispatch(request, session.id, 'execute');
    expect(execute.next_status).toBe('plan_confirmed');
    expect(execute.allowed).toBe(false);
    expect(execute.replay_result).toBeNull();
    expect(execute.user_response.toLowerCase()).toMatch(
      /blocked|could not run|required evidence/,
    );

    const events = await listEvents(request, session.id);
    const eventTypes = events.map((event) => event.type);
    expect(eventTypes).toContain('plan_execution_blocked');
    expect(eventTypes).toContain('task_result_reported');
    expect(eventTypes).not.toContain('plan_execution_started');
    expect(eventTypes).not.toContain('plan_execution_completed');
    expect(eventTypes).not.toContain('replay_completed');

    const blocked = events.find((event) => event.type === 'plan_execution_blocked');
    expect(blocked?.payload).toMatchObject({
      reason: 'missing_execution_context',
      no_result_verification: true,
      no_autonomous: true,
    });
    expect(blocked?.payload.missing_fields).toContain('target_url');

    const reported = events.find((event) => event.type === 'task_result_reported');
    expect(reported?.payload).toMatchObject({
      verification_outcome: 'blocked',
      task_verified: false,
      needs_review: false,
      no_recovery: true,
      no_autonomous: true,
      no_llm: true,
    });
    // Structured payload fields (follow-up fix)
    expect(reported?.payload.execution_status).toBe('blocked');
    expect(reported?.payload.replay_status).toBeNull();
    expect(reported?.payload.drift_status).toBeNull();

    const transcript = await listTranscript(request, session.id);
    const finalAgentMessage = [...transcript]
      .reverse()
      .find((message) => message.role === 'agent');
    expect(finalAgentMessage?.content.toLowerCase()).toMatch(
      /blocked|could not run|required evidence/,
    );
    expect(finalAgentMessage?.metadata).toMatchObject({
      source: 'execution_gate',
      status: 'blocked',
      verification_outcome: 'blocked',
      needs_review: false,
    });
  });

  test('E2E-11-1-6-002 explicit replay cannot bypass pending or confirmed plan flow', async ({
    request,
  }) => {
    const fixture = seeded.fixtures.happy;
    const replayCommand = `/replay ${fixture.id} ${validationUrl('/users')}`;

    const pendingSession = await createSession(request);
    const pendingPreview = await dispatch(request, pendingSession.id, 'e2e replay happy users');
    expect(pendingPreview.next_status).toBe('awaiting_confirmation');

    const pendingReplay = await dispatch(request, pendingSession.id, replayCommand);
    expect(pendingReplay.next_status).toBe('awaiting_confirmation');
    expect(pendingReplay.allowed).toBe(false);
    expect(pendingReplay.replay_result).toBeNull();
    expect(pendingReplay.user_response).toContain('awaiting confirmation');

    const pendingEvents = await listEvents(request, pendingSession.id);
    expect(pendingEvents.map((event) => event.type)).toContain(
      'explicit_replay_blocked_by_pending_confirmation',
    );
    expectNoExecutionOrReplayEvents(pendingEvents);

    const { session: confirmedSession } = await enterNaturalPlanConfirmed(request);
    const confirmedReplay = await dispatch(request, confirmedSession.id, replayCommand);
    expect(confirmedReplay.next_status).toBe('plan_confirmed');
    expect(confirmedReplay.allowed).toBe(false);
    expect(confirmedReplay.replay_result).toBeNull();
    expect(confirmedReplay.error).toContain('Replay is not allowed from plan_confirmed');

    const confirmedEvents = await listEvents(request, confirmedSession.id);
    expectNoExecutionOrReplayEvents(confirmedEvents);
  });
});
