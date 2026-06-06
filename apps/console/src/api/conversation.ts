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

export interface ConversationResponseProvenance {
  source_type: 'code' | 'agent' | 'hybrid' | 'unknown' | string;
  producer: {
    type: 'code' | 'agent' | 'unknown' | string;
    id: string;
    display_name: string;
    internal_agent_role: string | null;
  };
  llm_trace_ids: string[];
  generated_from_event_ids: string[];
  fallback: boolean;
}

export interface ConversationHistoryMessage {
  id: string;
  session_id: string;
  role: string;
  content: string;
  metadata: Record<string, unknown>;
  response_provenance?: ConversationResponseProvenance | null;
  created_at: string | null;
}

export interface ConversationLlmTrace {
  trace_id: string;
  purpose: string | null;
  agent_role: string | null;
  provider: string | null;
  model: string | null;
  request_id: string | null;
  prompt_template_id: string | null;
  prompt_hash: string | null;
  schema_name: string | null;
  schema_version: string | null;
  validation: Record<string, unknown>;
  latency_ms: number | null;
  usage: Record<string, unknown>;
  redaction: Record<string, unknown>;
  source_event_id: string | null;
  created_at: string | null;
}

export interface ConversationDebugTimelineItem {
  id: string;
  kind: string;
  title: string;
  summary: string;
  status: 'info' | 'waiting' | 'running' | 'success' | 'warning' | 'error' | 'cancelled' | string;
  created_at: string | null;
  source: 'message' | 'event' | 'trace' | 'derived' | string;
  message_id: string | null;
  event_id: string | null;
  trace_id: string | null;
  related_event_ids: string[];
  related_trace_ids: string[];
  details: Record<string, unknown>;
  raw_ref?: {
    tab: string;
    id: string | null;
  } | null;
}

export interface ConversationLearningRunSummary {
  source_event_id: string;
  source_event_type: string;
  run_id: string | null;
  run_ids: string[];
  learned_path_id: string | null;
  learned_path_ids: string[];
  status: string | null;
  learning_outcome: string | null;
  discovery_batch_id: string | null;
  passed_capabilities: Array<Record<string, unknown>>;
  failed_capabilities: Array<Record<string, unknown>>;
  unverified_capabilities: Array<Record<string, unknown>>;
  unsupported_capabilities: Array<Record<string, unknown>>;
  evidence_warnings: string[];
  summary: string | null;
  raw: Record<string, unknown>;
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
  messages: ConversationHistoryMessage[];
  events: Array<{
    id: string;
    session_id: string;
    type: string;
    payload: Record<string, unknown>;
    created_at: string | null;
  }>;
  learned_actions: Array<Record<string, unknown>>;
  learning_runs: ConversationLearningRunSummary[];
  replay_summaries: Array<Record<string, unknown>>;
  llm_traces: ConversationLlmTrace[];
  debug_timeline: ConversationDebugTimelineItem[];
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
