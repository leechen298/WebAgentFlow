import { describe, expect, it, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createI18n } from 'vue-i18n';
import ConversationHistoryPage from '@/pages/ConversationHistoryPage.vue';

const { listConversationSessions } = vi.hoisted(() => ({
  listConversationSessions: vi.fn(),
}));

vi.mock('@/api/conversation', () => ({
  listConversationSessions,
}));

vi.mock('ant-design-vue', async (importOriginal) => {
  const orig = (await importOriginal()) as Record<string, unknown>;
  return { ...orig, message: { success: vi.fn(), error: vi.fn() } };
});

const stubs = {
  'a-page-header': { template: '<div><slot /></div>' },
  'a-card': { template: '<section><slot /></section>' },
  'a-space': { template: '<div><slot /></div>' },
  'a-input': { props: ['value'], template: '<input />' },
  'a-input-number': { props: ['value'], template: '<input />' },
  'a-date-picker': { props: ['value'], template: '<input />' },
  'a-button': { emits: ['click'], template: '<button @click="$emit(\'click\')"><slot /></button>' },
  'a-table': {
    props: ['columns', 'dataSource', 'loading', 'rowKey'],
    template: '<table><tbody><tr v-for="record in dataSource" :key="record[rowKey]"><td v-for="column in columns" :key="column.key"><slot name="bodyCell" :column="column" :record="record">{{ record[column.dataIndex] }}</slot></td></tr></tbody></table>',
  },
  'a-empty': { props: ['description'], template: '<div class="empty" />' },
  'a-typography-text': { props: ['copyable'], template: '<span><slot /></span>' },
};

const i18n = createI18n({
  locale: 'zh',
  fallbackLocale: 'en',
  messages: { en: {}, zh: {} },
  legacy: false,
});

describe('ConversationHistoryPage', () => {
  it('loads sessions on mount and renders rows', async () => {
    listConversationSessions.mockResolvedValueOnce({
      items: [
        {
          id: 's1',
          status: 'idle',
          current_mode: 'interactive_chat',
          created_at: '2026-05-17T10:00:00Z',
          updated_at: '2026-05-17T10:05:00Z',
          message_count: 2,
          event_count: 1,
          last_user_message: 'hello',
          last_agent_message: 'hi',
          learned_action_count: 0,
          learned_actions: [],
        },
      ],
    });

    const wrapper = mount(ConversationHistoryPage, {
      global: { plugins: [i18n], stubs },
    });

    await flushPromises();
    expect(listConversationSessions).toHaveBeenCalled();
    expect(wrapper.text()).toContain('s1');
    expect(wrapper.text()).toContain('interactive_chat');
  });

  it('shows empty state when no sessions', async () => {
    listConversationSessions.mockResolvedValueOnce({ items: [] });

    const wrapper = mount(ConversationHistoryPage, {
      global: { plugins: [i18n], stubs },
    });

    await flushPromises();
    expect(listConversationSessions).toHaveBeenCalled();
    expect(wrapper.find('.empty').exists()).toBe(true);
  });
});
