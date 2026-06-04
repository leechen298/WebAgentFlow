import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  listConversationSessions,
  getConversationHistory,
  type ConversationSessionSummary,
  type ConversationHistoryPayload,
} from '@/api/conversation';

const { get } = vi.hoisted(() => ({
  get: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  default: { get },
}));

describe('Conversation API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('listConversationSessions forwards filters', async () => {
    const page = {
      items: [
        {
          id: 's1',
          status: 'idle',
          current_mode: 'interactive_chat',
          created_at: '2026-05-17T10:00:00Z',
          updated_at: '2026-05-17T10:05:00Z',
          message_count: 2,
          event_count: 1,
          last_user_message: null,
          last_agent_message: null,
          learned_action_count: 0,
          learned_actions: [],
        } as unknown as ConversationSessionSummary,
      ],
    };
    get.mockResolvedValueOnce(page);

    await expect(
      listConversationSessions({
        current_mode: 'interactive_chat',
        status: 'idle',
        limit: 20,
      }),
    ).resolves.toEqual(page);

    expect(get).toHaveBeenCalledWith('/conversation/sessions', {
      params: {
        current_mode: 'interactive_chat',
        status: 'idle',
        limit: 20,
      },
    });
  });

  it('listConversationSessions defaults to empty params', async () => {
    get.mockResolvedValueOnce({ items: [] });
    await listConversationSessions();
    expect(get).toHaveBeenCalledWith('/conversation/sessions', {
      params: {},
    });
  });

  it('getConversationHistory hits the detail route', async () => {
    const payload: ConversationHistoryPayload = {
      session: {
        id: 's1',
        status: 'idle',
        current_mode: 'interactive_chat',
        previous_status: null,
        metadata: {},
        created_at: '2026-05-17T10:00:00Z',
        updated_at: '2026-05-17T10:05:00Z',
      },
      messages: [],
      events: [],
      learned_actions: [],
      learning_runs: [],
      replay_summaries: [],
      llm_traces: [],
      debug_timeline: [
        {
          id: 'timeline-1',
          kind: 'user_message',
          title: '用户输入需求',
          summary: 'hello',
          status: 'info',
          created_at: '2026-05-17T10:00:00Z',
          source: 'message',
          message_id: 'm1',
          event_id: null,
          trace_id: null,
          related_event_ids: [],
          related_trace_ids: [],
          details: {},
          raw_ref: { tab: 'transcript', id: 'm1' },
        },
      ],
      raw: {},
    };
    get.mockResolvedValueOnce(payload);

    await expect(getConversationHistory('s1')).resolves.toEqual(payload);
    expect(get).toHaveBeenCalledWith('/conversation/sessions/s1/history');
  });
});
