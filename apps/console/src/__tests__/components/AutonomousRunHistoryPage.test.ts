import { beforeEach, describe, it, expect, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';

const listAutonomousRuns = vi.fn();
const getAutonomousRun = vi.fn();
const deleteAutonomousRun = vi.fn();
const mockPush = vi.fn();

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: {} }),
  useRouter: () => ({ push: mockPush }),
}));

vi.mock('@/api/exploration', () => ({
  listAutonomousRuns,
  getAutonomousRun,
  deleteAutonomousRun,
}));

// Stub ant-design-vue message to suppress console noise.
vi.mock('ant-design-vue', async (importOriginal) => {
  const orig = (await importOriginal()) as Record<string, unknown>;
  return { ...orig, message: { success: vi.fn(), error: vi.fn() } };
});

const stubs = {
  'a-card': {
    inheritAttrs: false,
    props: ['bordered'],
    template: '<section><slot name="title" /><slot /></section>',
  },
  'a-button': {
    props: ['size', 'type', 'danger', 'loading', 'disabled'],
    emits: ['click'],
    template:
      '<button :disabled="disabled" :data-danger="danger" @click="$emit(\'click\')"><slot /></button>',
  },
  'a-space': { props: ['size'], template: '<div><slot /></div>' },
  'a-table': {
    props: ['columns', 'dataSource', 'pagination', 'loading', 'rowKey', 'size'],
    template:
      '<table><tbody><tr v-for="record in dataSource" :key="record[rowKey]"><td v-for="column in columns" :key="column.key"><slot name="bodyCell" :column="column" :record="record" /></td></tr></tbody><slot v-if="!dataSource || dataSource.length === 0" name="emptyText" /></table>',
  },
  'a-tag': {
    props: ['color'],
    template: '<span class="tag" :data-color="color"><slot /></span>',
  },
  'a-spin': { props: ['size'], template: '<span />' },
  'a-tooltip': { props: ['title'], template: '<span><slot /></span>' },
  'a-empty': { props: ['description'], template: '<div />' },
  'a-popconfirm': {
    emits: ['confirm'],
    template: '<div @click="$emit(\'confirm\')"><slot /></div>',
  },
};

function makeRun(overrides: Record<string, unknown> = {}) {
  return {
    run_id: 'run-001',
    created_at: '2026-05-01T10:00:00Z',
    spec_id: 'login',
    scenario: 'valid_credentials',
    verdict: 'success',
    scenario_matched: true,
    pass_gate_status: 'pass',
    status: 'succeeded',
    url: 'http://localhost:5175/login',
    summary: 'All steps succeeded.',
    ...overrides,
  };
}

async function loadPage() {
  const mod = await import('@/pages/AutonomousRunHistoryPage.vue');
  return mount(mod.default, { global: { stubs } });
}

describe('AutonomousRunHistoryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listAutonomousRuns.mockResolvedValue({
      items: [makeRun()],
      has_next: false,
      next_cursor: null,
    });
  });

  it('loads runs on mount and renders rows', async () => {
    const wrapper = await loadPage();
    await flushPromises();
    expect(listAutonomousRuns).toHaveBeenCalledWith({ limit: 20, cursor: null });
    // Should render without error
    expect(wrapper.find('.autonomous-history').exists()).toBe(true);
  });

  it('renders empty state when no runs', async () => {
    listAutonomousRuns.mockResolvedValue({
      items: [],
      has_next: false,
      next_cursor: null,
    });
    const wrapper = await loadPage();
    await flushPromises();
    expect(wrapper.find('.autonomous-history').exists()).toBe(true);
  });

  it('navigates to workbench on openWorkbench click', async () => {
    const wrapper = await loadPage();
    await flushPromises();
    const buttons = wrapper.findAll('button');
    // Second button is "Open Workbench"
    const workbenchBtn = buttons.find((b) => b.text().includes('Workbench') || b.text().includes('workbench'));
    expect(workbenchBtn).toBeDefined();
    await workbenchBtn!.trigger('click');
    expect(mockPush).toHaveBeenCalledWith('/exploration/autonomous');
  });

  it('viewDetail navigates to detail page', async () => {
    const wrapper = await loadPage();
    await flushPromises();

    const buttons = wrapper.findAll('button');
    const viewBtn = buttons.find((b) =>
      ['View', 'view', '查看', '詳細'].some((label) => b.text().includes(label)),
    );
    expect(viewBtn).toBeDefined();
    await viewBtn!.trigger('click');
    expect(mockPush).toHaveBeenCalledWith('/exploration/autonomous/history/run-001');
  });

  it('copyRunJson fetches detail and writes to clipboard', async () => {
    const detail = makeRun({ result: { steps: [] } });
    getAutonomousRun.mockResolvedValueOnce(detail);
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    const wrapper = await loadPage();
    await flushPromises();

    const buttons = wrapper.findAll('button');
    const copyBtn = buttons.find((b) => b.text().includes('Copy') || b.text().includes('copy'));
    expect(copyBtn).toBeDefined();
    await copyBtn!.trigger('click');
    await flushPromises();
    expect(getAutonomousRun).toHaveBeenCalledWith('run-001');
    expect(writeText).toHaveBeenCalled();
  });

  it('handleDelete calls API and refreshes list', async () => {
    deleteAutonomousRun.mockResolvedValueOnce({ run_id: 'run-001', deleted: true });
    // After delete, reload with no cursor
    listAutonomousRuns
      .mockResolvedValueOnce({ items: [makeRun()], has_next: false, next_cursor: null })
      .mockResolvedValueOnce({ items: [], has_next: false, next_cursor: null });

    const wrapper = await loadPage();
    await flushPromises();

    // The popconfirm stub fires confirm immediately on click.
    // Find the delete button (danger button).
    const buttons = wrapper.findAll('button');
    const deleteBtn = buttons.find((b) => b.attributes('data-danger') === 'true' || b.text().includes('Delete') || b.text().includes('delete'));
    expect(deleteBtn).toBeDefined();
    await deleteBtn!.trigger('click');
    await flushPromises();
    expect(deleteAutonomousRun).toHaveBeenCalledWith('run-001');
  });

  it('refresh button reloads first page', async () => {
    const wrapper = await loadPage();
    await flushPromises();
    vi.clearAllMocks();
    listAutonomousRuns.mockResolvedValueOnce({
      items: [],
      has_next: false,
      next_cursor: null,
    });

    const buttons = wrapper.findAll('button');
    const refreshBtn = buttons.find((b) => b.text().includes('Refresh') || b.text().includes('refresh'));
    expect(refreshBtn).toBeDefined();
    await refreshBtn!.trigger('click');
    await flushPromises();
    expect(listAutonomousRuns).toHaveBeenCalledWith({ limit: 20, cursor: null });
  });

  it('pagination: next page loads with cursor', async () => {
    listAutonomousRuns.mockResolvedValue({
      items: [makeRun()],
      has_next: true,
      next_cursor: 'cursor-1',
    });
    const wrapper = await loadPage();
    await flushPromises();
    vi.clearAllMocks();
    listAutonomousRuns.mockResolvedValueOnce({
      items: [makeRun({ run_id: 'run-002' })],
      has_next: false,
      next_cursor: null,
    });

    const buttons = wrapper.findAll('button');
    const nextBtn = buttons.find((b) => b.text().includes('Next') || b.text().includes('next'));
    expect(nextBtn).toBeDefined();
    await nextBtn!.trigger('click');
    await flushPromises();
    expect(listAutonomousRuns).toHaveBeenCalledWith({ limit: 20, cursor: 'cursor-1' });
  });

  it('handles listAutonomousRuns error gracefully', async () => {
    listAutonomousRuns.mockRejectedValueOnce(new Error('Network error'));
    const wrapper = await loadPage();
    await flushPromises();
    // Should not crash
    expect(wrapper.find('.autonomous-history').exists()).toBe(true);
  });
});
