import { describe, expect, it, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createI18n } from 'vue-i18n';
import ConversationHistoryDetailPage from '@/pages/ConversationHistoryDetailPage.vue';

const { getConversationHistory } = vi.hoisted(() => ({
  getConversationHistory: vi.fn(),
}));

vi.mock('@/api/conversation', () => ({
  getConversationHistory,
}));

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { session_id: 's1' } }),
}));

vi.mock('ant-design-vue', async (importOriginal) => {
  const orig = (await importOriginal()) as Record<string, unknown>;
  return { ...orig, message: { success: vi.fn(), error: vi.fn() } };
});

const stubs = {
  'a-page-header': { template: '<div><slot /></div>' },
  'a-card': { template: '<section><slot /></section>' },
  'a-spin': { props: ['spinning'], template: '<div><slot /></div>' },
  'a-descriptions': { template: '<div><slot /></div>' },
  'a-descriptions-item': { template: '<div><slot /></div>' },
  'a-tabs': { props: ['activeKey'], template: '<div><slot /></div>' },
  'a-tab-pane': { props: ['tab', 'key'], template: '<div><slot /></div>' },
  'a-timeline': { template: '<div><slot /></div>' },
  'a-timeline-item': { template: '<div><slot /></div>' },
  'a-empty': { template: '<div class="empty" />' },
  'a-space': { template: '<div><slot /></div>' },
  'a-button': { emits: ['click'], template: '<button @click="$emit(\'click\')"><slot /></button>' },
  'a-typography-text': { props: ['copyable'], template: '<span><slot /></span>' },
};

const i18n = createI18n({
  locale: 'zh',
  fallbackLocale: 'en',
  messages: { en: {}, zh: {} },
  legacy: false,
});

describe('ConversationHistoryDetailPage', () => {
  it('loads history on mount and renders session info', async () => {
    getConversationHistory.mockResolvedValueOnce({
      session: {
        id: 's1',
        status: 'idle',
        current_mode: 'interactive_chat',
        previous_status: null,
        metadata: {},
        created_at: '2026-05-17T10:00:00Z',
        updated_at: '2026-05-17T10:05:00Z',
      },
      messages: [
        { id: 'm1', session_id: 's1', role: 'user', content: 'hello', metadata: {}, created_at: '2026-05-17T10:01:00Z' },
      ],
      events: [],
      learned_actions: [],
      learning_runs: [],
      replay_summaries: [],
      llm_traces: [],
      raw: { session: {}, messages: [], events: [] },
    });

    const wrapper = mount(ConversationHistoryDetailPage, {
      global: { plugins: [i18n], stubs },
    });

    await flushPromises();
    expect(getConversationHistory).toHaveBeenCalledWith('s1');
    expect(wrapper.text()).toContain('s1');
  });

  it('renders response provenance labels and llm trace summary', async () => {
    getConversationHistory.mockResolvedValueOnce({
      session: {
        id: 's1',
        status: 'idle',
        current_mode: 'interactive_chat',
        previous_status: null,
        metadata: {},
        created_at: '2026-05-17T10:00:00Z',
        updated_at: '2026-05-17T10:05:00Z',
      },
      messages: [
        {
          id: 'm-code',
          session_id: 's1',
          role: 'agent',
          content: 'code reply',
          metadata: {},
          created_at: '2026-05-17T10:01:00Z',
          response_provenance: {
            source_type: 'code',
            producer: {
              type: 'code',
              id: 'interactive_chat_runtime_code',
              display_name: 'Interactive Chat Runtime',
              internal_agent_role: null,
            },
            llm_trace_ids: [],
            generated_from_event_ids: [],
            fallback: false,
          },
        },
        {
          id: 'm-agent',
          session_id: 's1',
          role: 'agent',
          content: 'agent reply',
          metadata: {},
          created_at: '2026-05-17T10:02:00Z',
          response_provenance: {
            source_type: 'agent',
            producer: {
              type: 'agent',
              id: 'conversation_intake_agent',
              display_name: 'Conversation Intake Agent',
              internal_agent_role: 'conversation_intake_agent',
            },
            llm_trace_ids: ['trace-1'],
            generated_from_event_ids: ['event-1'],
            fallback: false,
          },
        },
        {
          id: 'm-hybrid',
          session_id: 's1',
          role: 'agent',
          content: 'hybrid reply',
          metadata: {},
          created_at: '2026-05-17T10:03:00Z',
          response_provenance: {
            source_type: 'hybrid',
            producer: {
              type: 'agent',
              id: 'conversation_intake_agent',
              display_name: 'Conversation Intake Agent',
              internal_agent_role: 'conversation_intake_agent',
            },
            llm_trace_ids: [],
            generated_from_event_ids: [],
            fallback: false,
          },
        },
        {
          id: 'm-unknown',
          session_id: 's1',
          role: 'agent',
          content: 'unknown reply',
          metadata: {},
          created_at: '2026-05-17T10:04:00Z',
          response_provenance: {
            source_type: 'unknown',
            producer: {
              type: 'unknown',
              id: 'unknown',
              display_name: 'Unknown',
              internal_agent_role: null,
            },
            llm_trace_ids: [],
            generated_from_event_ids: [],
            fallback: false,
          },
        },
      ],
      events: [],
      learned_actions: [],
      learning_runs: [],
      replay_summaries: [],
      llm_traces: [
        {
          trace_id: 'trace-1',
          purpose: 'conversation_intake',
          agent_role: 'conversation_intake_agent',
          provider: 'fake-provider',
          model: 'fake-model',
          request_id: 'req-1',
          prompt_template_id: 'conversation_intake_agent.v1',
          prompt_hash: 'hash-1',
          schema_name: 'ConversationIntakeResult',
          schema_version: 'm11.3.4',
          validation: { status: 'ok' },
          latency_ms: 12,
          usage: { prompt: 7, completion: 5, total: 12 },
          redaction: { applied: true },
          source_event_id: 'event-1',
          created_at: '2026-05-17T10:02:00Z',
        },
      ],
      raw: { session: {}, messages: [], events: [], llm_traces: [] },
    });

    const wrapper = mount(ConversationHistoryDetailPage, {
      global: { plugins: [i18n], stubs },
    });

    await flushPromises();
    expect(wrapper.text()).toContain('代码生成');
    expect(wrapper.text()).toContain('Agent 生成');
    expect(wrapper.text()).toContain('混合生成');
    expect(wrapper.text()).toContain('未知来源');
    expect(wrapper.text()).toContain('fake-provider');
    expect(wrapper.text()).toContain('fake-model');
    expect(wrapper.text()).toContain('req-1');
    expect(wrapper.text()).toContain('ConversationIntakeResult');
    expect(wrapper.text()).toContain('12 ms');
    expect(wrapper.text()).toContain('total 12');
    expect(wrapper.text()).toContain('redacted');
  });

  it('shows not found when history load fails', async () => {
    getConversationHistory.mockRejectedValueOnce(new Error('not found'));

    const wrapper = mount(ConversationHistoryDetailPage, {
      global: { plugins: [i18n], stubs },
    });

    await flushPromises();
    expect(getConversationHistory).toHaveBeenCalled();
    expect(wrapper.find('.empty').exists()).toBe(true);
  });
});
