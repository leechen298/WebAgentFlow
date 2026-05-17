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
      raw: { session: {}, messages: [], events: [] },
    });

    const wrapper = mount(ConversationHistoryDetailPage, {
      global: { plugins: [i18n], stubs },
    });

    await flushPromises();
    expect(getConversationHistory).toHaveBeenCalledWith('s1');
    expect(wrapper.text()).toContain('s1');
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
