import { beforeEach, describe, it, expect, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';

const getAutonomousRun = vi.fn();
const patchLearnedPathTrust = vi.fn();
const patchRunReview = vi.fn();

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { run_id: 'run-1' } }),
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock('@/api/exploration', () => ({
  getAutonomousRun,
  patchLearnedPathTrust,
  patchRunReview,
}));

// The LearnedPath block sits below the existing Page/Step/Verification
// blocks. Stub them out so the test focuses on the LearnedPath logic
// without dragging in their setup.
vi.mock('@/components/autonomous/PageAnalysisBlock.vue', () => ({
  default: { name: 'PageAnalysisBlock', template: '<div />' },
}));
vi.mock('@/components/autonomous/StepTimelineBlock.vue', () => ({
  default: { name: 'StepTimelineBlock', template: '<div />' },
}));
vi.mock('@/components/autonomous/VerificationBlock.vue', () => ({
  default: { name: 'VerificationBlock', template: '<div />' },
}));

const stubs = {
  'a-page-header': {
    props: ['title'],
    template: '<header><slot /><slot name="extra" /></header>',
  },
  'a-spin': {
    props: ['spinning'],
    template: '<div><slot /></div>',
  },
  'a-card': {
    inheritAttrs: false,
    props: ['title', 'bordered'],
    template:
      '<section :class="$attrs.class"><header>{{ title }}</header><slot name="extra" /><slot /></section>',
  },
  'a-descriptions': { template: '<dl><slot /></dl>' },
  'a-descriptions-item': {
    props: ['label', 'span'],
    template: '<div><dt>{{ label }}</dt><dd><slot /></dd></div>',
  },
  'a-collapse': { template: '<div><slot /></div>' },
  'a-collapse-panel': {
    props: ['key', 'header'],
    template: '<div>{{ header }}<slot /></div>',
  },
  'a-tag': {
    props: ['color'],
    template: '<span class="tag" :data-color="color"><slot /></span>',
  },
  'a-button': {
    props: ['type', 'disabled', 'loading', 'danger'],
    emits: ['click'],
    template:
      '<button :disabled="disabled" :data-loading="loading || false" :data-danger="danger || false" @click="$emit(\'click\')"><slot /></button>',
  },
  'a-space': { template: '<div><slot /></div>' },
  'a-alert': { props: ['type', 'message', 'description'], template: '<div />' },
  // Treat popconfirm as a transparent wrapper that fires @confirm
  // immediately when the inner button is clicked. The real component
  // adds a confirmation popup; for test purposes we trust the library
  // and exercise the confirmed-path callback directly.
  'a-popconfirm': {
    emits: ['confirm'],
    template:
      '<div class="popconfirm" @click="$emit(\'confirm\')"><slot /></div>',
  },
};

async function loadDetailPage() {
  const mod = await import('@/pages/AutonomousRunDetailPage.vue');
  return mod.default;
}

function buildDetail(overrides: Record<string, unknown> = {}) {
  return {
    run_id: 'run-1',
    created_at: '2026-04-25T10:00:00Z',
    updated_at: '2026-04-25T10:00:00Z',
    status: 'completed',
    strategy: { url: 'https://example.com/users', headless: true },
    summary: '',
    result: {
      page_analysis: { url: 'https://example.com/users', title: 'Users' },
      steps: [],
      verdict: 'success',
      verification: { scorecard: { pass_gate: { status: 'pass' } } },
    },
    pass_gate_status: 'pass',
    operator_review_status: 'unreviewed',
    operator_review_note: null,
    operator_reviewed_at: null,
    learned_path_id: 'lp-1',
    learned_path_trust: 'provisional',
    learned_path: {
      id: 'lp-1',
      trust: 'provisional',
      source_run_id: 'run-1',
      hit_count: 1,
      relation: 'source',
    },
    ...overrides,
  };
}

describe('AutonomousRunDetailPage · Run review block', () => {
  beforeEach(() => {
    vi.resetModules();
    getAutonomousRun.mockReset();
    patchRunReview.mockReset();
  });

  it('renders run review status tag and action buttons', async () => {
    getAutonomousRun.mockResolvedValueOnce(buildDetail());

    const Page = await loadDetailPage();
    const wrapper = mount(Page, { global: { stubs } });
    await flushPromises();

    const tag = wrapper.find('.run-review-card .tag');
    expect(tag.attributes('data-color')).toBe('default');
    const buttons = wrapper.findAll('button');
    const labels = buttons.map((b) => b.text());
    expect(labels.some((t) => /Accept this run/i.test(t))).toBe(true);
    expect(labels.some((t) => /Reject this run/i.test(t))).toBe(true);
  });

  it('accepts run and updates review tag', async () => {
    getAutonomousRun.mockResolvedValueOnce(buildDetail());
    patchRunReview.mockResolvedValueOnce({
      run_id: 'run-1',
      operator_review_status: 'accepted',
      operator_review_note: null,
      operator_reviewed_at: '2026-04-25T11:00:00Z',
      learned_path: buildDetail().learned_path,
    });

    const Page = await loadDetailPage();
    const wrapper = mount(Page, { global: { stubs } });
    await flushPromises();

    const vm = (wrapper.vm as unknown as {
      $: { setupState: { onAcceptRun: () => void } };
    }).$.setupState;
    vm.onAcceptRun();
    await flushPromises();

    expect(patchRunReview).toHaveBeenCalledWith('run-1', {
      status: 'accepted',
    });
    expect(
      wrapper.find('.run-review-card .tag').attributes('data-color'),
    ).toBe('green');
  });

  it('rejects run and updates review tag', async () => {
    getAutonomousRun.mockResolvedValueOnce(buildDetail());
    patchRunReview.mockResolvedValueOnce({
      run_id: 'run-1',
      operator_review_status: 'rejected',
      operator_review_note: 'wrong path',
      operator_reviewed_at: '2026-04-25T11:00:00Z',
      learned_path: buildDetail().learned_path,
    });

    const Page = await loadDetailPage();
    const wrapper = mount(Page, { global: { stubs } });
    await flushPromises();

    const vm = (wrapper.vm as unknown as {
      $: { setupState: { onRejectRun: () => void } };
    }).$.setupState;
    vm.onRejectRun();
    await flushPromises();

    expect(patchRunReview).toHaveBeenCalledWith('run-1', {
      status: 'rejected',
    });
    expect(
      wrapper.find('.run-review-card .tag').attributes('data-color'),
    ).toBe('red');
  });

  it('disables Accept when already accepted', async () => {
    getAutonomousRun.mockResolvedValueOnce(
      buildDetail({ operator_review_status: 'accepted' }),
    );

    const Page = await loadDetailPage();
    const wrapper = mount(Page, { global: { stubs } });
    await flushPromises();

    const buttons = wrapper.findAll('button');
    const acceptBtn = buttons.find((b) =>
      /Accept this run/i.test(b.text()),
    );
    const rejectBtn = buttons.find((b) =>
      /Reject this run/i.test(b.text()),
    );
    expect(acceptBtn?.attributes('disabled')).toBeDefined();
    expect(rejectBtn?.attributes('disabled')).toBeUndefined();
  });

  it('disables Reject when already rejected', async () => {
    getAutonomousRun.mockResolvedValueOnce(
      buildDetail({ operator_review_status: 'rejected' }),
    );

    const Page = await loadDetailPage();
    const wrapper = mount(Page, { global: { stubs } });
    await flushPromises();

    const buttons = wrapper.findAll('button');
    const acceptBtn = buttons.find((b) =>
      /Accept this run/i.test(b.text()),
    );
    const rejectBtn = buttons.find((b) =>
      /Reject this run/i.test(b.text()),
    );
    expect(acceptBtn?.attributes('disabled')).toBeUndefined();
    expect(rejectBtn?.attributes('disabled')).toBeDefined();
  });
});

describe('AutonomousRunDetailPage · LearnedPath block', () => {
  beforeEach(() => {
    vi.resetModules();
    getAutonomousRun.mockReset();
    patchLearnedPathTrust.mockReset();
    patchRunReview.mockReset();
  });

  it('renders the trust tag and path-level action buttons when ingested', async () => {
    getAutonomousRun.mockResolvedValueOnce(buildDetail());

    const Page = await loadDetailPage();
    const wrapper = mount(Page, { global: { stubs } });
    await flushPromises();

    // Tag should reflect current trust ("provisional" → blue) —
    // scope to the LearnedPath card to avoid the run-status tag.
    const tag = wrapper.find('.learned-path-card .tag');
    expect(tag.attributes('data-color')).toBe('blue');
    // Both action buttons present and enabled at provisional state
    const buttons = wrapper.findAll('button');
    const labels = buttons.map((b) => b.text());
    expect(labels.some((t) => /Confirm path/i.test(t))).toBe(true);
    expect(labels.some((t) => /Deprecate path/i.test(t))).toBe(true);
  });

  it('Confirm path button promotes trust and refreshes the tag', async () => {
    getAutonomousRun.mockResolvedValueOnce(buildDetail());
    patchLearnedPathTrust.mockResolvedValueOnce({
      id: 'lp-1',
      trust: 'confirmed',
    });

    const Page = await loadDetailPage();
    const wrapper = mount(Page, { global: { stubs } });
    await flushPromises();

    // Drive the confirmed path via the component's exposed callback —
    // the popconfirm wrapper is library code, trust it; we test the
    // onConfirmPath handler.
    const vm = (wrapper.vm as unknown as {
      $: { setupState: { onConfirmPath: () => void } };
    }).$.setupState;
    vm.onConfirmPath();
    await flushPromises();

    expect(patchLearnedPathTrust).toHaveBeenCalledWith('lp-1', {
      status: 'confirmed',
    });
    // Trust tag should now reflect the new state.
    expect(
      wrapper.find('.learned-path-card .tag').attributes('data-color'),
    ).toBe('green');
  });

  it('Deprecate path button deprecates trust', async () => {
    getAutonomousRun.mockResolvedValueOnce(buildDetail());
    patchLearnedPathTrust.mockResolvedValueOnce({
      id: 'lp-1',
      trust: 'deprecated',
    });

    const Page = await loadDetailPage();
    const wrapper = mount(Page, { global: { stubs } });
    await flushPromises();

    const vm = (wrapper.vm as unknown as {
      $: { setupState: { onDeprecatePath: () => void } };
    }).$.setupState;
    vm.onDeprecatePath();
    await flushPromises();

    expect(patchLearnedPathTrust).toHaveBeenCalledWith('lp-1', {
      status: 'deprecated',
    });
    expect(
      wrapper.find('.learned-path-card .tag').attributes('data-color'),
    ).toBe('red');
  });

  it('disables Confirm path when trust is already confirmed', async () => {
    getAutonomousRun.mockResolvedValueOnce(
      buildDetail({ learned_path_trust: 'confirmed', learned_path: { ...buildDetail().learned_path, trust: 'confirmed' } }),
    );

    const Page = await loadDetailPage();
    const wrapper = mount(Page, { global: { stubs } });
    await flushPromises();

    const buttons = wrapper.findAll('button');
    const confirmBtn = buttons.find((b) =>
      /Confirm path/i.test(b.text()),
    );
    const markWrongBtn = buttons.find((b) =>
      /Deprecate path/i.test(b.text()),
    );
    expect(confirmBtn?.attributes('disabled')).toBeDefined();
    expect(markWrongBtn?.attributes('disabled')).toBeUndefined();
  });

  it('disables Deprecate path when trust is already deprecated', async () => {
    getAutonomousRun.mockResolvedValueOnce(
      buildDetail({ learned_path_trust: 'deprecated', learned_path: { ...buildDetail().learned_path, trust: 'deprecated' } }),
    );

    const Page = await loadDetailPage();
    const wrapper = mount(Page, { global: { stubs } });
    await flushPromises();

    const buttons = wrapper.findAll('button');
    const confirmBtn = buttons.find((b) =>
      /Confirm path/i.test(b.text()),
    );
    const markWrongBtn = buttons.find((b) =>
      /Deprecate path/i.test(b.text()),
    );
    expect(confirmBtn?.attributes('disabled')).toBeUndefined();
    expect(markWrongBtn?.attributes('disabled')).toBeDefined();
  });

  it('shows the "pass but missing" copy when gate=pass and no learned_path', async () => {
    getAutonomousRun.mockResolvedValueOnce(
      buildDetail({
        learned_path_id: null,
        learned_path_trust: null,
        learned_path: null,
        pass_gate_status: 'pass',
      }),
    );

    const Page = await loadDetailPage();
    const wrapper = mount(Page, { global: { stubs } });
    await flushPromises();

    expect(wrapper.text()).toMatch(/ingest|hook|フック/i);
  });

  it('shows the "not pass" copy when gate=fail', async () => {
    getAutonomousRun.mockResolvedValueOnce(
      buildDetail({
        learned_path_id: null,
        learned_path_trust: null,
        learned_path: null,
        pass_gate_status: 'fail',
      }),
    );

    const Page = await loadDetailPage();
    const wrapper = mount(Page, { global: { stubs } });
    await flushPromises();

    expect(wrapper.text()).toMatch(/pass_gate/i);
  });
});
