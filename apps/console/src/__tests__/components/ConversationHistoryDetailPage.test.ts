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
  'a-tab-pane': { props: ['tab'], template: '<div><span>{{ tab }}</span><slot /></div>' },
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
  messages: {
    en: { conversationHistory: { tabTranscript: 'Transcript', tabEvents: 'Events', tabRawJson: 'Raw JSON' } },
    zh: {
      common: { id: 'ID', createdAt: '创建时间', updatedAt: '更新时间' },
      error: { notFound: 'not found' },
      conversationHistory: {
        detailPageTitle: '会话详情',
        sessionInfo: '会话信息',
        colStatus: '状态',
        colMode: '模式',
        messageCount: '消息数',
        eventCount: '事件数',
        tabDebugTimeline: '运行轨迹',
        tabTranscript: '对话记录',
        tabEvents: '事件',
        tabLearnedActions: 'Learned Actions',
        tabEvidence: 'Replay / Learning Evidence',
        tabRawJson: 'Raw JSON',
        copyRawJson: '复制 Raw JSON',
        copiedRawJson: 'Raw JSON 已复制到剪贴板',
        loadFailed: '加载会话历史失败',
        timelineDetails: '脱敏详情',
        timelineEmpty: '还没有可解释的运行轨迹。请查看事件或 Raw JSON。',
        timelineStatus: {
          info: '信息',
          waiting: '等待',
          running: '运行中',
          success: '完成',
          warning: '需复核',
          error: '错误',
          cancelled: '已取消',
        },
      },
    },
  },
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
      debug_timeline: [
        {
          id: 'timeline-1',
          kind: 'user_message',
          title: '用户输入需求',
          summary: 'hello',
          status: 'info',
          created_at: '2026-05-17T10:01:00Z',
          source: 'message',
          message_id: 'm1',
          event_id: null,
          trace_id: null,
          related_event_ids: [],
          related_trace_ids: [],
          details: { role: 'user', content: 'hello' },
        },
      ],
      raw: { session: {}, messages: [], events: [] },
    });

    const wrapper = mount(ConversationHistoryDetailPage, {
      global: { plugins: [i18n], stubs },
    });

    await flushPromises();
    expect(getConversationHistory).toHaveBeenCalledWith('s1');
    expect(wrapper.text()).toContain('s1');
    expect(wrapper.text()).toContain('运行轨迹');
    expect(wrapper.text()).toContain('用户输入需求');
    expect(wrapper.text()).toContain('hello');
    expect(wrapper.text()).toContain('信息');
    expect(wrapper.text()).toContain('对话记录');
    expect(wrapper.text()).toContain('事件');
    expect(wrapper.text()).toContain('Raw JSON');
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
      debug_timeline: [
        {
          id: 'timeline-trace',
          kind: 'llm_trace',
          title: 'LLM 调用完成',
          summary: 'fake-provider / fake-model / req-1',
          status: 'info',
          created_at: '2026-05-17T10:02:00Z',
          source: 'trace',
          message_id: null,
          event_id: 'event-1',
          trace_id: 'trace-1',
          related_event_ids: [],
          related_trace_ids: [],
          details: { provider: 'fake-provider', model: 'fake-model', request_id: 'req-1' },
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

  it('renders readable learning run outcome summaries', async () => {
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
      messages: [],
      events: [],
      learned_actions: [],
      learning_runs: [
        {
          source_event_id: 'event-learning',
          source_event_type: 'chat_learning_completed',
          run_id: 'run-1',
          run_ids: ['run-1', 'run-2'],
          learned_path_id: 'path-1',
          learned_path_ids: ['path-1'],
          status: 'learned',
          learning_outcome: 'partial_success',
          discovery_batch_id: 'batch-1',
          passed_capabilities: [{ capability_id: 'cap-email', label: '邮箱' }],
          failed_capabilities: [{ scenario_id: 'scenario-status', human_label: '状态' }],
          unverified_capabilities: [{ scenario_id: 'scenario-region', label: '地区' }],
          unsupported_capabilities: [{ capability_id: 'cap-cascader', label: '级联地区' }],
          evidence_warnings: ['supervisor confidence low'],
          summary: '学习部分完成',
          raw: { learning_outcome: 'partial_success' },
        },
      ],
      replay_summaries: [],
      llm_traces: [],
      debug_timeline: [],
      raw: { session: {}, messages: [], events: [] },
    });

    const wrapper = mount(ConversationHistoryDetailPage, {
      global: { plugins: [i18n], stubs },
    });

    await flushPromises();
    const text = wrapper.text();
    expect(text).toContain('outcome: partial_success');
    expect(text).toContain('batch: batch-1');
    expect(text).toContain('run: run-1');
    expect(text).toContain('path: path-1');
    expect(text).toContain('passed 1');
    expect(text).toContain('failed 1');
    expect(text).toContain('unverified 1');
    expect(text).toContain('unsupported 1');
    expect(text).toContain('邮箱');
    expect(text).toContain('状态');
    expect(text).toContain('地区');
    expect(text).toContain('级联地区');
    expect(text).toContain('supervisor confidence low');
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
