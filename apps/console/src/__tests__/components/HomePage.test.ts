import { beforeEach, describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { flushPromises } from '@vue/test-utils';
import HomePage from '@/pages/HomePage.vue';
import { message } from 'ant-design-vue';

const push = vi.fn();
const checkApiHealth = vi.fn();
const fetchRecordings = vi.fn();
const fetchSkills = vi.fn();
const fetchRuns = vi.fn();

const appStore = {
  apiConnected: true,
  loading: false,
  checkApiHealth,
};

const recordingsStore = {
  recordings: [{ id: 'r1' }],
  loadingList: false,
  fetchRecordings,
};

const skillsStore = {
  skills: [{ id: 's1' }, { id: 's2' }],
  loadingList: false,
  fetchSkills,
};

const runsStore = {
  runs: [{ id: 'run1' }, { id: 'run2' }, { id: 'run3' }],
  loadingList: false,
  fetchRuns,
};

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push,
  }),
}));

vi.mock('@/stores', () => ({
  useAppStore: () => appStore,
  useRecordingsStore: () => recordingsStore,
  useSkillsStore: () => skillsStore,
  useRunsStore: () => runsStore,
}));

describe('HomePage', () => {
  beforeEach(() => {
    push.mockReset();
    checkApiHealth.mockReset().mockResolvedValue(undefined);
    fetchRecordings.mockReset().mockResolvedValue(undefined);
    fetchSkills.mockReset().mockResolvedValue(undefined);
    fetchRuns.mockReset().mockResolvedValue(undefined);
    appStore.apiConnected = true;
    appStore.loading = false;
  });

  it('renders, loads dashboard data, and exposes the expected counts', async () => {
    const wrapper = mount(HomePage);
    await flushPromises();

    expect(wrapper.exists()).toBe(true);
    expect(checkApiHealth).toHaveBeenCalled();
    expect(fetchRecordings).toHaveBeenCalled();
    expect(fetchSkills).toHaveBeenCalled();
    expect(fetchRuns).toHaveBeenCalled();

    const vm = wrapper.vm.$.setupState;
    expect(vm.recordingsCount).toBe(1);
    expect(vm.skillsCount).toBe(2);
    expect(vm.runsCount).toBe(3);
    expect(vm.apiStatusType).toBe('success');
    expect(vm.apiStatusMessage).toBeTruthy();
    expect(message.success).toHaveBeenCalled();
  });

  it('handles refresh failures and route navigation actions', async () => {
    checkApiHealth.mockRejectedValueOnce(new Error('boom'));
    appStore.apiConnected = false;
    appStore.loading = true;

    const wrapper = mount(HomePage);
    const vm = wrapper.vm.$.setupState;

    expect(vm.apiStatusType).toBe('info');
    await flushPromises();
    expect(message.error).toHaveBeenCalled();

    vm.goToRecordings();
    vm.goToSkills();
    vm.goToRuns();

    expect(push).toHaveBeenNthCalledWith(1, '/recordings');
    expect(push).toHaveBeenNthCalledWith(2, '/skills');
    expect(push).toHaveBeenNthCalledWith(3, '/runs');
  });

  it('treats list fetch failures as non-fatal during refresh', async () => {
    fetchRecordings.mockRejectedValueOnce(new Error('ignore'));
    fetchSkills.mockRejectedValueOnce(new Error('ignore'));
    fetchRuns.mockRejectedValueOnce(new Error('ignore'));

    const wrapper = mount(HomePage);
    const vm = wrapper.vm.$.setupState;
    await flushPromises();

    message.success = vi.fn();
    await vm.refreshData();

    expect(checkApiHealth).toHaveBeenCalledTimes(2);
    expect(fetchRecordings).toHaveBeenCalledTimes(2);
    expect(fetchSkills).toHaveBeenCalledTimes(2);
    expect(fetchRuns).toHaveBeenCalledTimes(2);
    expect(message.success).toHaveBeenCalled();
  });
});
