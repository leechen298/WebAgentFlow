import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import HomePage from '@/pages/HomePage.vue';

const push = vi.fn();

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push,
  }),
}));

vi.mock('@/stores', () => ({
  useAppStore: () => ({
    apiConnected: true,
    loading: false,
    checkApiHealth: vi.fn(),
  }),
  useRecordingsStore: () => ({
    recordings: [],
    loadingList: false,
  }),
  useSkillsStore: () => ({
    skills: [],
    loadingList: false,
  }),
  useRunsStore: () => ({
    runs: [],
    loadingList: false,
  }),
}));

describe('HomePage', () => {
  it('should have basic structure', () => {
    const wrapper = mount(HomePage, {
      global: {
        stubs: {
          'router-view': true,
          'a-row': true,
          'a-col': true,
          'a-card': true,
          'a-alert': true,
          'a-statistic': true,
          'a-space': true,
          'a-button': true,
        },
      },
    });

    expect(wrapper.exists()).toBe(true);
  });
});
