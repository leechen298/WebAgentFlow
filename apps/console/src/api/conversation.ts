import apiClient from './client';

export interface ConversationSessionSummary {
  id: string;
  status: string;
  current_mode: string | null;
  created_at: string | null;
  updated_at: string | null;
  message_count: number;
  event_count: number;
  last_user_message: string | null;
  last_agent_message: string | null;
  learned_action_count: number;
  learned_actions: Array<Record<string, unknown>>;
}

export interface ConversationHistoryPayload {
  session: {
    id: string;
    status: string;
    current_mode: string | null;
    previous_status: string | null;
    metadata: Record<string, unknown>;
    created_at: string | null;
    updated_at: string | null;
  };
  messages: Array<{
    id: string;
    session_id: string;
    role: string;
    content: string;
    metadata: Record<string, unknown>;
    created_at: string | null;
  }>;
  events: Array<{
    id: string;
    session_id: string;
    type: string;
    payload: Record<string, unknown>;
    created_at: string | null;
  }>;
  learned_actions: Array<Record<string, unknown>>;
  learning_runs: Array<Record<string, unknown>>;
  replay_summaries: Array<Record<string, unknown>>;
  raw: Record<string, unknown>;
}

export interface ListSessionsParams {
  current_mode?: string;
  status?: string;
  updated_from?: string;
  updated_to?: string;
  limit?: number;
}

export async function listConversationSessions(
  params: ListSessionsParams = {}
): Promise<{ items: ConversationSessionSummary[] }> {
  const response = await apiClient.get('/conversation/sessions', { params });
  return response as unknown as { items: ConversationSessionSummary[] };
}

export async function getConversationHistory(
  sessionId: string
): Promise<ConversationHistoryPayload> {
  const response = await apiClient.get(`/conversation/sessions/${sessionId}/history`);
  return response as unknown as ConversationHistoryPayload;
}
