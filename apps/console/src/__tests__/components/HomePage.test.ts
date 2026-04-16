import { beforeEach, describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { flushPromises } from '@vue/test-utils';
import { message } from 'ant-design-vue';

const push = vi.fn();
const checkApiHealth = vi.fn();
const fetchRecordings = vi.fn();
const fetchSkills = vi.fn();
const fetchRuns = vi.fn();
const resolveApiConfig = vi.hoisted(() => vi.fn());

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

vi.mock('@/api/client', () => ({
  resolveApiConfig,
}));

const renderStubs = {
  'a-row': { template: '<div><slot /></div>' },
  'a-col': { template: '<div><slot /></div>' },
  'a-card': { props: ['title'], template: '<section>{{ title }}<slot /></section>' },
  'a-space': { template: '<div><slot /></div>' },
  'a-alert': { props: ['message', 'type'], template: '<div>{{ type }}:{{ message }}</div>' },
  'a-statistic': { props: ['title', 'value', 'loading'], template: '<div>{{ title }}={{ value }}<slot name="prefix" /></div>' },
  'a-button': { props: ['loading'], emits: ['click'], template: '<button @click="$emit(\'click\')"><slot /><slot name="icon" /></button>' },
  'a-descriptions': { template: '<div><slot /></div>' },
  'a-descriptions-item': { props: ['label'], template: '<div>{{ label }}<slot /></div>' },
  'a-tag': { template: '<span><slot /></span>' },
  'a-divider': { template: '<hr />' },
  'video-camera-outlined': { template: '<i />' },
  'tool-outlined': { template: '<i />' },
  'play-circle-outlined': { template: '<i />' },
  'sync-outlined': { template: '<i />' },
  'plus-outlined': { template: '<i />' },
  'info-circle-outlined': { template: '<i />' },
};

async function loadHomePage() {
  const mod = await import('@/pages/HomePage.vue');
  return mod.default;
}

describe('HomePage', () => {
  beforeEach(() => {
    vi.resetModules();
    push.mockReset();
    checkApiHealth.mockReset().mockResolvedValue(undefined);
    fetchRecordings.mockReset().mockResolvedValue(undefined);
    fetchSkills.mockReset().mockResolvedValue(undefined);
    fetchRuns.mockReset().mockResolvedValue(undefined);
    resolveApiConfig.mockReset().mockReturnValue({
      mode: 'direct',
      useDevProxy: false,
      baseURL: 'http://127.0.0.1:8001',
      configuredApiBaseUrl: 'http://127.0.0.1:8001',
    });
    appStore.apiConnected = true;
    appStore.loading = false;
  });

  it('renders, loads dashboard data, and exposes the expected counts', async () => {
    const HomePage = await loadHomePage();
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
    const HomePage = await loadHomePage();
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
    const HomePage = await loadHomePage();
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

  it('exposes unreachable API status and resets loading after refresh', async () => {
    const HomePage = await loadHomePage();
    appStore.apiConnected = false;
    appStore.loading = false;

    const wrapper = mount(HomePage);
    const vm = wrapper.vm.$.setupState;
    await flushPromises();

    expect(vm.apiStatusType).toBe('error');
    expect(vm.apiStatusMessage).toBeTruthy();

    vm.loading = true;
    await vm.refreshData();
    expect(vm.loading).toBe(false);
  });

  it('renders the dashboard cards, debug panel, and quick actions in direct mode', async () => {
    const HomePage = await loadHomePage();
    const wrapper = mount(HomePage, { global: { stubs: renderStubs } });
    await flushPromises();

    expect(wrapper.text()).toContain('http://127.0.0.1:8001');
    expect(wrapper.text()).toContain('1');
    expect(wrapper.text()).toContain('2');
    expect(wrapper.text()).toContain('3');

    const buttons = wrapper.findAll('button');
    expect(buttons).toHaveLength(4);

    await buttons[1].trigger('click');
    await buttons[2].trigger('click');
    await buttons[3].trigger('click');

    expect(push).toHaveBeenNthCalledWith(1, '/recordings');
    expect(push).toHaveBeenNthCalledWith(2, '/skills');
    expect(push).toHaveBeenNthCalledWith(3, '/runs');
  });

  it('renders the proxy branch and refresh button through the template', async () => {
    resolveApiConfig.mockReturnValueOnce({
      mode: 'proxy',
      useDevProxy: true,
      baseURL: '/api',
      configuredApiBaseUrl: '',
    });
    const HomePage = await loadHomePage();
    const wrapper = mount(HomePage, { global: { stubs: renderStubs } });
    await flushPromises();

    expect(wrapper.text()).toContain('/api');
    expect(wrapper.text()).not.toContain('http://127.0.0.1:8001');

    await wrapper.find('button').trigger('click');
    expect(checkApiHealth).toHaveBeenCalledTimes(2);
    expect(fetchRecordings).toHaveBeenCalledTimes(2);
  });
});
