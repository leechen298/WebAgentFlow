import { describe, expect, it, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import AutonomousUseCasesPage from '@/pages/AutonomousUseCasesPage.vue';

const { push, listSpecs, streamAutonomousRun } = vi.hoisted(() => ({
  push: vi.fn(),
  listSpecs: vi.fn(),
  streamAutonomousRun: vi.fn(),
}));

vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
}));

vi.mock('@/api/exploration', () => ({
  listSpecs,
}));

vi.mock('@/api/autonomousStream', () => ({
  streamAutonomousRun,
}));

const stubs = {
  'a-card': {
    props: ['title', 'bordered', 'size'],
    template: '<section><header><slot name="title">{{ title }}</slot></header><slot name="extra" /><slot /></section>',
  },
  'a-tag': { props: ['size', 'color'], template: '<span><slot /></span>' },
  'a-button': {
    props: ['loading', 'size', 'type', 'disabled', 'danger'],
    emits: ['click'],
    template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot /><slot name="icon" /></button>',
  },
  'a-table': {
    props: ['columns', 'dataSource', 'pagination', 'size', 'rowKey'],
    template: '<table><slot name="bodyCell" v-bind="{ column: (columns||[])[0], record: (dataSource||[])[0] }" /></table>',
  },
  'a-space': { props: ['wrap', 'size'], template: '<span><slot /></span>' },
  'a-spin': { props: ['spinning'], template: '<div><slot /></div>' },
  'a-alert': {
    props: ['type', 'message', 'showIcon', 'closable'],
    emits: ['close'],
    template: '<div class="alert"><span class="alert-msg">{{ message }}</span><slot /></div>',
  },
  'a-tooltip': { props: ['title'], template: '<span><slot /></span>' },
  'a-empty': { props: ['description'], template: '<div class="empty">{{ description }}</div>' },
  'a-checkbox': {
    props: ['checked', 'disabled'],
    emits: ['change'],
    template: '<input type="checkbox" :checked="checked" :disabled="disabled" @change="$emit(\'change\')" />',
  },
  'reload-outlined': { template: '<i />' },
  'caret-right-outlined': { template: '<i />' },
  'pause-circle-outlined': { template: '<i />' },
};

function mockSpecs(): Array<{
  spec_id: string;
  page_id: string;
  url_pattern: string;
  description: string;
  scenarios: Array<{
    key: string;
    description: string;
    inputs: Record<string, string>;
    selections: Record<string, string>;
    expected_verdict?: string | null;
    expected_verdict_not?: string | null;
  }>;
}> {
  return [
    {
      spec_id: 'login',
      page_id: 'login',
      url_pattern: '/entry',
      description: 'Login page spec',
      scenarios: [
        {
          key: 'valid_credentials',
          description: 'Valid login',
          inputs: { username: 'admin', password: 'secret' },
          selections: {},
          expected_verdict: 'success',
        },
        {
          key: 'invalid_credentials',
          description: 'Invalid login',
          inputs: { username: 'bad', password: 'wrong' },
          selections: {},
          expected_verdict_not: 'success',
        },
      ],
    },
    {
      spec_id: 'users',
      page_id: 'users',
      url_pattern: '',
      description: 'Users page spec',
      scenarios: [
        {
          key: 'filter_by_name',
          description: 'Filter by name',
          inputs: { search: 'Alice' },
          selections: { status: 'active' },
        },
      ],
    },
  ];
}

describe('AutonomousUseCasesPage', () => {
  beforeEach(() => {
    listSpecs.mockReset();
    push.mockReset();
    streamAutonomousRun.mockReset();
  });

  // ── Existing tests (deep link not regressed) ──────────────

  it('loads and renders specs on mount', async () => {
    listSpecs.mockResolvedValue(mockSpecs());
    const wrapper = mount(AutonomousUseCasesPage, { global: { stubs } });
    await flushPromises();

    expect(listSpecs).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain('Login page spec');
    expect(wrapper.text()).toContain('Users page spec');
    expect(wrapper.text()).toContain('login');
    expect(wrapper.text()).toContain('users');
  });

  it('shows empty state when no specs returned', async () => {
    listSpecs.mockResolvedValue([]);
    const wrapper = mount(AutonomousUseCasesPage, { global: { stubs } });
    await flushPromises();

    expect(wrapper.text()).toContain('No use cases available');
  });

  it('shows error alert when listSpecs fails', async () => {
    listSpecs.mockRejectedValue(new Error('network down'));
    const wrapper = mount(AutonomousUseCasesPage, { global: { stubs } });
    await flushPromises();

    expect(wrapper.text()).toContain('network down');
  });

  it('deep links to workbench with correct query params', async () => {
    listSpecs.mockResolvedValue(mockSpecs());
    const wrapper = mount(AutonomousUseCasesPage, { global: { stubs } });
    await flushPromises();

    const vm = wrapper.vm as unknown as {
      runInWorkbench: (
        spec: ReturnType<typeof mockSpecs>[number],
        scenario: ReturnType<typeof mockSpecs>[number]['scenarios'][number],
      ) => void;
    };
    const specs = mockSpecs();
    vm.runInWorkbench(specs[0], specs[0].scenarios[0]);

    expect(push).toHaveBeenCalledTimes(1);
    const calledWith = push.mock.calls[0][0] as string;
    expect(calledWith).toContain('/exploration/autonomous?');
    expect(calledWith).toContain('url=');
    expect(calledWith).toContain('spec_id=login');
    expect(calledWith).toContain('scenario=valid_credentials');
    expect(calledWith).toContain('goal=');
  });

  // ── Selection tests ───────────────────────────────────────

  it('select all runnable only selects scenarios with url_pattern', async () => {
    listSpecs.mockResolvedValue(mockSpecs());
    const wrapper = mount(AutonomousUseCasesPage, { global: { stubs } });
    await flushPromises();

    const vm = wrapper.vm as unknown as {
      selectAllRunnable: () => void;
      selectedKeys: Set<string>;
      runnableScenarios: Array<{ key: string }>;
    };

    expect(vm.selectedKeys.size).toBe(0);

    vm.selectAllRunnable();

    // login has 2 scenarios both runnable; users has 0 (no url_pattern)
    expect(vm.selectedKeys.size).toBe(2);
    expect(vm.selectedKeys.has('login::valid_credentials')).toBe(true);
    expect(vm.selectedKeys.has('login::invalid_credentials')).toBe(true);
    // users scenario should NOT be selected
    expect(vm.selectedKeys.has('users::filter_by_name')).toBe(false);
  });

  it('clear selection empties selected keys', async () => {
    listSpecs.mockResolvedValue(mockSpecs());
    const wrapper = mount(AutonomousUseCasesPage, { global: { stubs } });
    await flushPromises();

    const vm = wrapper.vm as unknown as {
      selectAllRunnable: () => void;
      clearSelection: () => void;
      selectedKeys: Set<string>;
    };

    vm.selectAllRunnable();
    expect(vm.selectedKeys.size).toBe(2);

    vm.clearSelection();
    expect(vm.selectedKeys.size).toBe(0);
  });

  // ── Batch run tests ───────────────────────────────────────

  it('batch run payload contains url, goal, fill_values, toggle_values, spec_id, scenario, headless=true', async () => {
    listSpecs.mockResolvedValue(mockSpecs());
    // streamAutonomousRun returns a no-op abort
    streamAutonomousRun.mockReturnValue(vi.fn());

    const wrapper = mount(AutonomousUseCasesPage, { global: { stubs } });
    await flushPromises();

    const vm = wrapper.vm as unknown as {
      toggleSelect: (specId: string, scenarioKey: string) => void;
      startBatchRun: () => void;
    };

    // Select only login::valid_credentials
    vm.toggleSelect('login', 'valid_credentials');
    vm.startBatchRun();

    expect(streamAutonomousRun).toHaveBeenCalledTimes(1);
    const payload = streamAutonomousRun.mock.calls[0][0];
    expect(payload.url).toContain('/entry');
    expect(payload.goal).toBe('Valid login');
    expect(payload.fill_values).toEqual({ username: 'admin', password: 'secret' });
    expect(payload.toggle_values).toBeUndefined();
    expect(payload.headless).toBe(true);
    expect(payload.spec_id).toBe('login');
    expect(payload.scenario).toBe('valid_credentials');
  });

  it('concurrency is capped at 3 running tasks', async () => {
    listSpecs.mockResolvedValue([
      {
        spec_id: 'multi',
        page_id: 'multi',
        url_pattern: '/multi',
        description: 'Multi',
        scenarios: [
          { key: 's1', description: 'S1', inputs: {}, selections: {} },
          { key: 's2', description: 'S2', inputs: {}, selections: {} },
          { key: 's3', description: 'S3', inputs: {}, selections: {} },
          { key: 's4', description: 'S4', inputs: {}, selections: {} },
          { key: 's5', description: 'S5', inputs: {}, selections: {} },
        ],
      },
    ]);

    // streamAutonomousRun returns no-op abort; never calls onDone synchronously
    streamAutonomousRun.mockReturnValue(vi.fn());

    const wrapper = mount(AutonomousUseCasesPage, { global: { stubs } });
    await flushPromises();

    const vm = wrapper.vm as unknown as {
      selectAllRunnable: () => void;
      startBatchRun: () => void;
      batchTasks: Record<string, { status: string }>;
    };

    vm.selectAllRunnable(); // selects all 5
    vm.startBatchRun();

    expect(streamAutonomousRun).toHaveBeenCalledTimes(3);

    // 3 running, 2 queued
    const running = Object.values(vm.batchTasks).filter(
      (t) => t.status === 'running',
    ).length;
    const queued = Object.values(vm.batchTasks).filter(
      (t) => t.status === 'queued',
    ).length;
    expect(running).toBe(3);
    expect(queued).toBe(2);
  });

  it('marks task as failed on run_failed SSE event instead of completed', async () => {
    listSpecs.mockResolvedValue([
      {
        spec_id: 'flaky',
        page_id: 'flaky',
        url_pattern: '/flaky',
        description: 'Flaky',
        scenarios: [
          { key: 's1', description: 'S1', inputs: {}, selections: {} },
        ],
      },
    ]);

    let capturedHandlers: {
      onEvent: (evt: { event: string; data: unknown }) => void;
      onDone: () => void;
    } | null = null;

    streamAutonomousRun.mockImplementation(
      (_payload: unknown, handlers: typeof capturedHandlers) => {
        capturedHandlers = handlers;
        return vi.fn();
      },
    );

    const wrapper = mount(AutonomousUseCasesPage, { global: { stubs } });
    await flushPromises();

    const vm = wrapper.vm as unknown as {
      selectAllRunnable: () => void;
      startBatchRun: () => void;
      batchTasks: Record<string, { status: string; error?: string }>;
    };

    vm.selectAllRunnable();
    vm.startBatchRun();

    expect(streamAutonomousRun).toHaveBeenCalledTimes(1);
    expect(capturedHandlers).not.toBeNull();

    // Simulate run_failed SSE event
    capturedHandlers!.onEvent({
      event: 'run_failed',
      data: { error: 'page crashed' },
    });

    // Status should be failed, NOT completed
    expect(vm.batchTasks['flaky::s1'].status).toBe('failed');
    expect(vm.batchTasks['flaky::s1'].error).toBe('page crashed');

    // Now simulate onDone — should NOT flip failed back to completed
    capturedHandlers!.onDone();

    expect(vm.batchTasks['flaky::s1'].status).toBe('failed');
  });

  // ── deep link regression guard ────────────────────────────

  it('deep link still works after batch run state changes', async () => {
    listSpecs.mockResolvedValue(mockSpecs());
    streamAutonomousRun.mockReturnValue(vi.fn());

    const wrapper = mount(AutonomousUseCasesPage, { global: { stubs } });
    await flushPromises();

    const vm = wrapper.vm as unknown as {
      toggleSelect: (specId: string, scenarioKey: string) => void;
      startBatchRun: () => void;
      runInWorkbench: (
        spec: ReturnType<typeof mockSpecs>[number],
        scenario: ReturnType<typeof mockSpecs>[number]['scenarios'][number],
      ) => void;
    };

    // Run batch first to mutate internal state
    vm.toggleSelect('login', 'valid_credentials');
    vm.startBatchRun();

    // Deep link should still work independently
    push.mockClear();
    const specs = mockSpecs();
    vm.runInWorkbench(specs[0], specs[0].scenarios[0]);

    expect(push).toHaveBeenCalledTimes(1);
    const calledWith = push.mock.calls[0][0] as string;
    expect(calledWith).toContain('/exploration/autonomous?');
    expect(calledWith).toContain('spec_id=login');
    expect(calledWith).toContain('scenario=valid_credentials');
  });
});
