import { beforeEach, describe, it, expect, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';

const listLearnedPaths = vi.fn();
const getLearnedPath = vi.fn();
const patchLearnedPathTrust = vi.fn();
const mockPush = vi.fn();

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: {} }),
  useRouter: () => ({ push: mockPush }),
}));

vi.mock('@/api/exploration', () => ({
  listLearnedPaths,
  getLearnedPath,
  patchLearnedPathTrust,
}));

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
      '<div><template v-for="rec in dataSource" :key="rec[rowKey]"><div v-for="col in columns" :key="col.key" class="cell"><slot name="bodyCell" :column="col" :record="rec" /></div></template><slot name="emptyText" /></div>',
  },
  'a-tag': {
    props: ['color'],
    template: '<span class="tag" :data-color="color"><slot /></span>',
  },
  'a-spin': { props: ['size', 'spinning'], template: '<span><slot /></span>' },
  'a-empty': { props: ['description'], template: '<div class="empty" />' },
  'a-popconfirm': {
    emits: ['confirm'],
    template: '<div @click="$emit(\'confirm\')"><slot /></div>',
  },
  'a-select': {
    props: ['value', 'options', 'size'],
    emits: ['update:value', 'change'],
    template:
      '<select :value="value" @change="$emit(\'update:value\', $event.target.value); $emit(\'change\', $event.target.value)"><option v-for="opt in options" :value="opt.value">{{ opt.label }}</option></select>',
  },
  'a-drawer': {
    props: ['open', 'title', 'width'],
    emits: ['update:open'],
    template: '<div v-if="open"><slot /></div>',
  },
  'a-alert': {
    props: ['type', 'showIcon', 'message', 'description'],
    template: '<div class="alert"><slot /></div>',
  },
  'a-descriptions': {
    props: ['column', 'size', 'bordered'],
    template: '<div><slot /></div>',
  },
  'a-descriptions-item': {
    props: ['label', 'span'],
    template: '<div class="desc-item" :data-label="label"><slot /></div>',
  },
  'a-timeline': { template: '<div class="timeline"><slot /></div>' },
  'a-timeline-item': { template: '<div class="timeline-item"><slot /></div>' },
  'router-link': {
    props: ['to'],
    template: '<a :href="to" class="router-link"><slot /></a>',
  },
};

function makePath(overrides: Record<string, unknown> = {}) {
  return {
    id: 'path-001',
    scenario: 'valid_credentials',
    page_template: 'login',
    trust: 'provisional' as const,
    hit_count: 3,
    source_run_id: 'run-001',
    created_at: '2026-05-01T10:00:00Z',
    updated_at: '2026-05-01T10:00:00Z',
    ...overrides,
  };
}

async function loadPage() {
  const mod = await import('@/pages/LearnedPathCatalogPage.vue');
  return mount(mod.default, { global: { stubs } });
}

describe('LearnedPathCatalogPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listLearnedPaths.mockResolvedValue({
      items: [makePath()],
      has_next: false,
      next_cursor: null,
    });
  });

  it('calls listLearnedPaths on mount', async () => {
    await loadPage();
    await flushPromises();
    expect(listLearnedPaths).toHaveBeenCalledWith({
      limit: 20,
      cursor: null,
      trust: null,
    });
  });

  it('renders scenario / page_template / trust / hit_count when data exists', async () => {
    const wrapper = await loadPage();
    await flushPromises();
    const html = wrapper.html();
    expect(html).toContain('valid_credentials');
    expect(html).toContain('login');
    expect(html).toContain('3');
  });

  it('renders empty state when no paths', async () => {
    listLearnedPaths.mockResolvedValue({
      items: [],
      has_next: false,
      next_cursor: null,
    });
    const wrapper = await loadPage();
    await flushPromises();
    expect(wrapper.find('.empty').exists()).toBe(true);
  });

  it('shows error alert on drawer load failure', async () => {
    getLearnedPath.mockRejectedValue(new Error('boom'));
    const wrapper = await loadPage();
    await flushPromises();

    const viewBtn = wrapper.findAll('button').find((b) => b.text().includes('View') || b.text().includes('view'));
    expect(viewBtn).toBeTruthy();
    if (viewBtn) {
      await viewBtn.trigger('click');
      await flushPromises();
      expect(wrapper.find('.alert').exists()).toBe(true);
    }
  });

  it('re-fetches with trust filter when select changes', async () => {
    const wrapper = await loadPage();
    await flushPromises();
    vi.clearAllMocks();

    const select = wrapper.find('select');
    expect(select.exists()).toBe(true);
    await select.setValue('confirmed');
    await flushPromises();

    expect(listLearnedPaths).toHaveBeenCalledWith(
      expect.objectContaining({ trust: 'confirmed' }),
    );
  });

  it('renders clickable source run link when source_run_id exists', async () => {
    const wrapper = await loadPage();
    await flushPromises();
    const link = wrapper.find('.router-link');
    expect(link.exists()).toBe(true);
    expect(link.attributes('href')).toBe('/exploration/autonomous/history/run-001');
  });

  it('does not render clickable link when source_run_id is absent', async () => {
    listLearnedPaths.mockResolvedValue({
      items: [makePath({ source_run_id: null })],
      has_next: false,
      next_cursor: null,
    });
    const wrapper = await loadPage();
    await flushPromises();
    expect(wrapper.find('.router-link').exists()).toBe(false);
  });

  it('opens actions drawer and displays actions on viewActions click', async () => {
    getLearnedPath.mockResolvedValue({
      ...makePath(),
      actions: [{ type: 'fill', target: 'username', value: 'admin' }],
    });
    const wrapper = await loadPage();
    await flushPromises();

    const viewBtn = wrapper.findAll('button').find((b) => b.text().includes('View') || b.text().includes('view'));
    expect(viewBtn).toBeTruthy();
    if (viewBtn) {
      await viewBtn.trigger('click');
      await flushPromises();
      expect(getLearnedPath).toHaveBeenCalledWith('path-001');
      expect(wrapper.find('.timeline').exists()).toBe(true);
    }
  });

  it('shows empty state when actions are empty', async () => {
    getLearnedPath.mockResolvedValue({
      ...makePath(),
      actions: [],
    });
    const wrapper = await loadPage();
    await flushPromises();

    const viewBtn = wrapper.findAll('button').find((b) => b.text().includes('View') || b.text().includes('view'));
    if (viewBtn) {
      await viewBtn.trigger('click');
      await flushPromises();
      expect(wrapper.find('.empty').exists()).toBe(true);
    }
  });

  it('calls patchLearnedPathTrust with confirmed on confirm click', async () => {
    patchLearnedPathTrust.mockResolvedValue(makePath({ trust: 'confirmed' }));
    const wrapper = await loadPage();
    await flushPromises();

    // Find confirm button (primary type, text includes confirm/确认)
    const buttons = wrapper.findAll('button');
    const confirmBtn = buttons.find((b) =>
      b.text().toLowerCase().includes('confirm') || b.text().includes('确认'),
    );
    expect(confirmBtn).toBeTruthy();
    if (confirmBtn) {
      await confirmBtn.trigger('click');
      await flushPromises();
      expect(patchLearnedPathTrust).toHaveBeenCalledWith('path-001', { status: 'confirmed' });
    }
  });

  it('calls patchLearnedPathTrust with flaky on mark flaky click', async () => {
    patchLearnedPathTrust.mockResolvedValue(makePath({ trust: 'flaky' }));
    const wrapper = await loadPage();
    await flushPromises();

    const buttons = wrapper.findAll('button');
    const flakyBtn = buttons.find((b) =>
      b.text().toLowerCase().includes('flaky') || b.text().includes('不稳定'),
    );
    expect(flakyBtn).toBeTruthy();
    if (flakyBtn) {
      await flakyBtn.trigger('click');
      await flushPromises();
      expect(patchLearnedPathTrust).toHaveBeenCalledWith('path-001', { status: 'flaky' });
    }
  });

  it('calls patchLearnedPathTrust with deprecated on deprecate click', async () => {
    patchLearnedPathTrust.mockResolvedValue(makePath({ trust: 'deprecated' }));
    const wrapper = await loadPage();
    await flushPromises();

    const buttons = wrapper.findAll('button');
    const depBtn = buttons.find((b) =>
      b.text().toLowerCase().includes('deprecat') || b.text().includes('废弃'),
    );
    expect(depBtn).toBeTruthy();
    if (depBtn) {
      await depBtn.trigger('click');
      await flushPromises();
      expect(patchLearnedPathTrust).toHaveBeenCalledWith('path-001', { status: 'deprecated' });
    }
  });

  it('does not trigger patch when trust already matches target status', async () => {
    listLearnedPaths.mockResolvedValue({
      items: [makePath({ trust: 'confirmed' })],
      has_next: false,
      next_cursor: null,
    });
    const wrapper = await loadPage();
    await flushPromises();

    const buttons = wrapper.findAll('button');
    const confirmBtn = buttons.find((b) =>
      b.text().toLowerCase().includes('confirm') || b.text().includes('确认'),
    );
    // Button should be disabled
    expect(confirmBtn?.attributes('disabled')).toBe('');
  });
});
