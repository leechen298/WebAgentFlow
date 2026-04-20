import { beforeEach, describe, it, expect, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { message } from 'ant-design-vue';

const push = vi.fn();
const listAutonomousRuns = vi.fn();

vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
}));

vi.mock('@/api/exploration', () => ({
  listAutonomousRuns,
}));

const stubs = {
  'a-row': { template: '<div><slot /></div>' },
  'a-col': { template: '<div><slot /></div>' },
  'a-card': {
    props: ['title', 'bordered', 'hoverable'],
    emits: ['click'],
    template: '<section @click="$emit(\'click\')"><header>{{ title }}</header><slot name="extra" /><slot /></section>',
  },
  'a-tag': { props: ['color'], template: '<span><slot /></span>' },
  'a-button': {
    props: ['loading', 'size', 'type'],
    emits: ['click'],
    template: '<button @click="$emit(\'click\')"><slot /><slot name="icon" /></button>',
  },
  'a-empty': { props: ['description'], template: '<div class="empty">{{ description }}</div>' },
  'a-list': {
    props: ['dataSource', 'loading'],
    template: '<ul><template v-for="item in dataSource" :key="item.run_id"><slot name="renderItem" :item="item" /></template></ul>',
  },
  'a-list-item': {
    emits: ['click'],
    template: '<li @click="$emit(\'click\')"><slot /></li>',
  },
  'thunderbolt-outlined': { template: '<i />' },
  'history-outlined': { template: '<i />' },
  'sync-outlined': { template: '<i />' },
};

async function loadHomePage() {
  const mod = await import('@/pages/HomePage.vue');
  return mod.default;
}

describe('HomePage', () => {
  beforeEach(() => {
    vi.resetModules();
    push.mockReset();
    listAutonomousRuns.mockReset();
  });

  it('loads recent runs on mount and renders entry cards', async () => {
    listAutonomousRuns.mockResolvedValueOnce({
      items: [
        {
          run_id: 'r1',
          created_at: '2026-04-20T10:00:00Z',
          spec_id: 'login',
          scenario: 'valid_credentials',
          verdict: 'success',
          scenario_matched: true,
          pass_gate_status: 'pass',
          status: 'completed',
        },
      ],
      has_next: false,
      next_cursor: null,
    });

    const HomePage = await loadHomePage();
    const wrapper = mount(HomePage, { global: { stubs } });
    await flushPromises();

    expect(listAutonomousRuns).toHaveBeenCalledWith({ limit: 5 });
    expect(wrapper.text()).toContain('WebAgentFlow');
    expect(wrapper.text()).toContain('login');
    expect(wrapper.text()).toContain('valid_credentials');
  });

  it('navigates on entry-card clicks', async () => {
    listAutonomousRuns.mockResolvedValueOnce({ items: [], has_next: false, next_cursor: null });
    const HomePage = await loadHomePage();
    const wrapper = mount(HomePage, { global: { stubs } });
    await flushPromises();

    const vm = (wrapper.vm as unknown as {
      $: { setupState: {
        goWorkbench: () => void;
        goHistory: () => void;
        openRun: (item: { run_id: string }) => void;
      } };
    }).$.setupState;
    vm.goWorkbench();
    vm.goHistory();
    vm.openRun({ run_id: 'abc' });

    expect(push).toHaveBeenNthCalledWith(1, '/exploration/autonomous');
    expect(push).toHaveBeenNthCalledWith(2, '/exploration/autonomous/history');
    expect(push).toHaveBeenNthCalledWith(3, '/exploration/autonomous/history/abc');
  });

  it('shows an error toast when recent-runs fetch fails', async () => {
    listAutonomousRuns.mockRejectedValueOnce(new Error('boom'));
    const err = vi.spyOn(message, 'error').mockImplementation(() => ({}) as any);

    const HomePage = await loadHomePage();
    mount(HomePage, { global: { stubs } });
    await flushPromises();

    expect(err).toHaveBeenCalled();
    err.mockRestore();
  });

  it('can be refreshed via defineExpose', async () => {
    listAutonomousRuns.mockResolvedValue({ items: [], has_next: false, next_cursor: null });
    const HomePage = await loadHomePage();
    const wrapper = mount(HomePage, { global: { stubs } });
    await flushPromises();

    await (wrapper.vm as unknown as { refresh: () => Promise<void> }).refresh();
    expect(listAutonomousRuns).toHaveBeenCalledTimes(2);
  });
});
