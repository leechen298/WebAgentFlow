import { beforeEach, describe, it, expect, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';

const getAutonomousRun = vi.fn();
const patchLearnedPathTrust = vi.fn();

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { run_id: 'run-1' } }),
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock('@/api/exploration', () => ({
  getAutonomousRun,
  patchLearnedPathTrust,
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
    learned_path_id: 'lp-1',
    learned_path_trust: 'provisional',
    ...overrides,
  };
}

describe('AutonomousRunDetailPage · LearnedPath block', () => {
  beforeEach(() => {
    vi.resetModules();
    getAutonomousRun.mockReset();
    patchLearnedPathTrust.mockReset();
  });

  it('renders the trust tag and both action buttons when ingested', async () => {
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
    expect(labels.some((t) => /Confirm|确认|確認/.test(t))).toBe(true);
    expect(labels.some((t) => /Mark wrong|标记错误|誤りとして報告/.test(t))).toBe(
      true,
    );
  });

  it('Confirm button promotes trust and refreshes the tag', async () => {
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
    // onConfirm handler.
    const vm = (wrapper.vm as unknown as {
      $: { setupState: { onConfirm: () => void } };
    }).$.setupState;
    vm.onConfirm();
    await flushPromises();

    expect(patchLearnedPathTrust).toHaveBeenCalledWith('lp-1', {
      status: 'confirmed',
    });
    // Trust tag should now reflect the new state.
    expect(
      wrapper.find('.learned-path-card .tag').attributes('data-color'),
    ).toBe('green');
  });

  it('Mark-wrong button deprecates trust', async () => {
    getAutonomousRun.mockResolvedValueOnce(buildDetail());
    patchLearnedPathTrust.mockResolvedValueOnce({
      id: 'lp-1',
      trust: 'deprecated',
    });

    const Page = await loadDetailPage();
    const wrapper = mount(Page, { global: { stubs } });
    await flushPromises();

    const vm = (wrapper.vm as unknown as {
      $: { setupState: { onMarkWrong: () => void } };
    }).$.setupState;
    vm.onMarkWrong();
    await flushPromises();

    expect(patchLearnedPathTrust).toHaveBeenCalledWith('lp-1', {
      status: 'deprecated',
    });
    expect(
      wrapper.find('.learned-path-card .tag').attributes('data-color'),
    ).toBe('red');
  });

  it('disables Confirm when trust is already confirmed', async () => {
    getAutonomousRun.mockResolvedValueOnce(
      buildDetail({ learned_path_trust: 'confirmed' }),
    );

    const Page = await loadDetailPage();
    const wrapper = mount(Page, { global: { stubs } });
    await flushPromises();

    const buttons = wrapper.findAll('button');
    const confirmBtn = buttons.find((b) =>
      /Confirm|确认|確認/.test(b.text()),
    );
    const markWrongBtn = buttons.find((b) =>
      /Mark wrong|标记错误|誤りとして報告/.test(b.text()),
    );
    expect(confirmBtn?.attributes('disabled')).toBeDefined();
    expect(markWrongBtn?.attributes('disabled')).toBeUndefined();
  });

  it('disables Mark-wrong when trust is already deprecated', async () => {
    getAutonomousRun.mockResolvedValueOnce(
      buildDetail({ learned_path_trust: 'deprecated' }),
    );

    const Page = await loadDetailPage();
    const wrapper = mount(Page, { global: { stubs } });
    await flushPromises();

    const buttons = wrapper.findAll('button');
    const confirmBtn = buttons.find((b) =>
      /Confirm|确认|確認/.test(b.text()),
    );
    const markWrongBtn = buttons.find((b) =>
      /Mark wrong|标记错误|誤りとして報告/.test(b.text()),
    );
    expect(confirmBtn?.attributes('disabled')).toBeUndefined();
    expect(markWrongBtn?.attributes('disabled')).toBeDefined();
  });

  it('shows the "pass but missing" copy when gate=pass and no learned_path', async () => {
    getAutonomousRun.mockResolvedValueOnce(
      buildDetail({
        learned_path_id: null,
        learned_path_trust: null,
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
        pass_gate_status: 'fail',
      }),
    );

    const Page = await loadDetailPage();
    const wrapper = mount(Page, { global: { stubs } });
    await flushPromises();

    expect(wrapper.text()).toMatch(/pass_gate/i);
  });
});
