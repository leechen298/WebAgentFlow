import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';

vi.mock('ant-design-vue', async (importOriginal) => {
  const orig = (await importOriginal()) as Record<string, unknown>;
  return { ...orig, message: { success: vi.fn(), error: vi.fn() } };
});

const stubs = {
  'a-card': {
    props: ['title', 'bordered', 'size'],
    template: '<section :class="$attrs.class"><header>{{ title }}</header><slot name="extra" /><slot /></section>',
  },
  'a-tag': {
    props: ['color'],
    template: '<span class="tag" :data-color="color"><slot /></span>',
  },
  'a-row': { template: '<div class="row"><slot /></div>' },
  'a-col': { template: '<div class="col"><slot /></div>' },
  'a-empty': { props: ['description'], template: '<div />' },
  'a-spin': { props: ['size'], template: '<span />' },
  'a-progress': { name: 'a-progress', props: ['percent', 'status', 'size'], template: '<div />' },
  'a-collapse': { template: '<div><slot /></div>' },
  'a-collapse-panel': {
    props: ['key', 'header'],
    template: '<div>{{ header }}<slot /></div>',
  },
  'a-button': {
    props: ['size'],
    emits: ['click'],
    template: '<button @click="$emit(\'click\')"><slot /></button>',
  },
};

async function loadComponent() {
  const mod = await import('@/components/autonomous/VerificationBlock.vue');
  return mod.default;
}

function mountBlock(props: Record<string, unknown> = {}) {
  return loadComponent().then((comp) =>
    mount(comp, {
      props: {
        selfAssessment: null,
        supervisor: null,
        scorecard: null,
        isRunning: false,
        ...props,
      },
      global: { stubs },
    }),
  );
}

describe('VerificationBlock', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when all props are null', async () => {
    const wrapper = await mountBlock();
    expect(wrapper.find('.verify-card').exists()).toBe(false);
  });

  it('renders card when selfAssessment is provided', async () => {
    const wrapper = await mountBlock({
      selfAssessment: { verdict: 'success', summary: 'All good.' },
    });
    expect(wrapper.find('.verify-card').exists()).toBe(true);
  });

  it('shows pass gate banner with pass status', async () => {
    const wrapper = await mountBlock({
      selfAssessment: { verdict: 'success', summary: 'ok' },
      scorecard: {
        pass_gate: { status: 'pass', reasons: [] },
      },
    });
    const banner = wrapper.find('.pass-gate-banner');
    expect(banner.exists()).toBe(true);
    expect(banner.classes()).toContain('pass-gate-banner-pass');
  });

  it('shows pass gate banner with fail status', async () => {
    const wrapper = await mountBlock({
      selfAssessment: { verdict: 'failure', summary: 'bad' },
      scorecard: {
        pass_gate: { status: 'fail', reasons: ['element missing'] },
      },
    });
    const banner = wrapper.find('.pass-gate-banner');
    expect(banner.exists()).toBe(true);
    expect(banner.classes()).toContain('pass-gate-banner-fail');
    // Reasons should be rendered
    expect(wrapper.findAll('.pass-gate-reasons li')).toHaveLength(1);
  });

  it('shows pass gate banner with unverified status', async () => {
    const wrapper = await mountBlock({
      selfAssessment: { verdict: 'success', summary: 'ok' },
      scorecard: {
        pass_gate: { status: 'unverified', reasons: ['LLM fallback'] },
      },
    });
    const banner = wrapper.find('.pass-gate-banner');
    expect(banner.classes()).toContain('pass-gate-banner-unverified');
  });

  it('shows evaluating banner when isRunning and selfAssessment present but no pass gate', async () => {
    const wrapper = await mountBlock({
      selfAssessment: { verdict: 'success', summary: 'ok' },
      isRunning: true,
    });
    expect(wrapper.find('.pass-gate-banner-loading').exists()).toBe(true);
  });

  it('hides evaluating banner when pass gate is set', async () => {
    const wrapper = await mountBlock({
      selfAssessment: { verdict: 'success', summary: 'ok' },
      isRunning: true,
      scorecard: { pass_gate: { status: 'pass', reasons: [] } },
    });
    expect(wrapper.find('.pass-gate-banner-loading').exists()).toBe(false);
  });

  it('renders supervisor fallback tag', async () => {
    const wrapper = await mountBlock({
      selfAssessment: { verdict: 'success', summary: 'ok' },
      supervisor: {
        verdict: 'success',
        summary: 'ok',
        source: 'fallback',
        error_kind: 'provider_error',
      },
    });
    const tags = wrapper.findAll('.tag');
    const fallbackTag = tags.find((t) => t.text().includes('provider_error') || t.text().includes('Unavailable'));
    expect(fallbackTag).toBeDefined();
  });

  it('renders supervisor partial parse tag', async () => {
    const wrapper = await mountBlock({
      selfAssessment: { verdict: 'success', summary: 'ok' },
      supervisor: {
        verdict: 'success',
        summary: 'ok',
        _supervisor_partial_parse: true,
      },
    });
    const tags = wrapper.findAll('.tag');
    const partialTag = tags.find((t) => t.text().includes('partial') || t.text().includes('Partial'));
    expect(partialTag).toBeDefined();
  });

  it('renders supervisor anomalies and suggestions', async () => {
    const wrapper = await mountBlock({
      selfAssessment: { verdict: 'success', summary: 'ok' },
      supervisor: {
        verdict: 'success',
        summary: 'ok',
        anomalies: ['anomaly 1', 'anomaly 2'],
        suggestions: ['suggestion 1'],
      },
    });
    expect(wrapper.html()).toContain('anomaly 1');
    expect(wrapper.html()).toContain('anomaly 2');
    expect(wrapper.html()).toContain('suggestion 1');
  });

  it('renders scorecard with 5 metrics', async () => {
    const wrapper = await mountBlock({
      selfAssessment: { verdict: 'success', summary: 'ok' },
      scorecard: {
        element_recognition: { score: 1.0 },
        action_coverage: { score: 0.8 },
        verdict_accuracy: { score: 1.0 },
        distraction_avoidance: { score: 1.0 },
        supervisor_agreement: { score: 1.0 },
      },
    });
    // Should render 5 progress bars
    expect(wrapper.findAllComponents({ name: 'a-progress' })).toHaveLength(5);
  });

  it('renders observation atoms when present', async () => {
    const wrapper = await mountBlock({
      selfAssessment: { verdict: 'success', summary: 'ok' },
      supervisor: {
        verdict: 'success',
        summary: 'ok',
        observations: {
          did_navigate: true,
          final_url_path: '/dashboard',
          scenario_goal_observed: true,
        },
      },
    });
    expect(wrapper.html()).toContain('did_navigate');
    expect(wrapper.html()).toContain('scenario_goal_observed');
  });

  it('renders derivation trail', async () => {
    const wrapper = await mountBlock({
      selfAssessment: { verdict: 'success', summary: 'ok' },
      supervisor: {
        verdict: 'success',
        summary: 'ok',
        _supervisor_verdict_derivation: ['rule1: matched', 'rule2: passed'],
      },
    });
    expect(wrapper.html()).toContain('rule1: matched');
    expect(wrapper.html()).toContain('rule2: passed');
  });

  it('renders thinking block when _thinking is present', async () => {
    const wrapper = await mountBlock({
      selfAssessment: { verdict: 'success', summary: 'ok' },
      supervisor: {
        verdict: 'success',
        summary: 'ok',
        _thinking: 'Let me analyze...',
        _model: 'gpt-4',
      },
    });
    expect(wrapper.html()).toContain('Let me analyze...');
    expect(wrapper.html()).toContain('gpt-4');
  });

  it('copyThinking writes to clipboard', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });

    const wrapper = await mountBlock({
      selfAssessment: { verdict: 'success', summary: 'ok' },
      supervisor: {
        verdict: 'success',
        summary: 'ok',
        _thinking: 'trace content',
      },
    });
    const copyBtn = wrapper.find('button');
    await copyBtn.trigger('click');
    await flushPromises();
    expect(writeText).toHaveBeenCalledWith('trace content');
  });

  it('renders final_url and final_title in self-assessment', async () => {
    const wrapper = await mountBlock({
      selfAssessment: {
        verdict: 'success',
        summary: 'ok',
        final_url: 'https://example.invalid/dashboard',
        final_title: 'Dashboard',
      },
    });
    expect(wrapper.html()).toContain('dashboard');
    expect(wrapper.html()).toContain('Dashboard');
  });

  it('does not render verdict tag while evaluating', async () => {
    const wrapper = await mountBlock({
      selfAssessment: { verdict: 'success', summary: 'ok' },
      isRunning: true,
    });
    // When isEvaluating is true, verdict tags are hidden
    const verdictTags = wrapper.findAll('.tag');
    const successTag = verdictTags.find((t) => t.text() === 'success');
    expect(successTag).toBeUndefined();
  });
});
