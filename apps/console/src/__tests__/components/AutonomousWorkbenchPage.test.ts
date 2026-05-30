import { describe, expect, it, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import AutonomousWorkbenchPage from '@/pages/AutonomousWorkbenchPage.vue';

const { push, listSpecs, streamAutonomousRun, messageSuccess, messageError, messageWarning } =
  vi.hoisted(() => ({
    push: vi.fn(),
    listSpecs: vi.fn(),
    streamAutonomousRun: vi.fn(),
    messageSuccess: vi.fn(),
    messageError: vi.fn(),
    messageWarning: vi.fn(),
  }));

vi.mock('vue-router', () => ({
  useRoute: () => ({
    query: {},
    path: '/exploration/autonomous',
  }),
  useRouter: () => ({ push }),
}));

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string, vars?: Record<string, unknown>) => {
      if (vars) return `${key}:${JSON.stringify(vars)}`;
      return key;
    },
    locale: { value: 'en' },
  }),
}));

vi.mock('ant-design-vue', () => ({
  message: { success: messageSuccess, error: messageError, warning: messageWarning },
}));

vi.mock('@/api/exploration', () => ({
  listSpecs,
}));

vi.mock('@/api/autonomousStream', () => ({
  streamAutonomousRun,
}));

const stubs = {
  'a-card': {
    props: ['title', 'bordered'],
    template: '<section><header>{{ title }}</header><slot name="extra" /><slot /></section>',
  },
  'a-form': { template: '<form><slot /></form>' },
  'a-form-item': { props: ['label', 'required'], template: '<div><label>{{ label }}</label><slot /></div>' },
  'a-row': { props: ['gutter'], template: '<div class="row"><slot /></div>' },
  'a-col': { props: ['xs', 'md'], template: '<div class="col"><slot /></div>' },
  'a-input': {
    props: ['value', 'placeholder', 'allowClear', 'disabled', 'addonBefore'],
    emits: ['update:value'],
    template: '<input :value="value" :placeholder="placeholder" @input="$emit(\'update:value\', $event.target.value)" />',
  },
  'a-select': {
    props: ['value', 'options', 'placeholder', 'allowClear'],
    emits: ['update:value', 'change'],
    template: '<select :value="value" @change="$emit(\'update:value\', $event.target.value)"><option v-for="o in (options||[])" :key="o.value" :value="o.value">{{ o.label }}</option></select>',
  },
  'a-button': {
    props: ['type', 'loading', 'disabled', 'danger', 'size', 'block'],
    emits: ['click'],
    template: '<button :disabled="disabled" @click="$emit(\'click\')"><slot /></button>',
  },
  'a-alert': {
    props: ['type', 'showIcon', 'message', 'description', 'closable'],
    template: '<div class="alert"><span class="alert-msg">{{ message }}</span></div>',
  },
  'a-tag': { props: ['color'], template: '<span class="tag"><slot /></span>' },
  'a-space': { props: ['wrap', 'size'], template: '<span><slot /></span>' },
  'a-divider': { template: '<hr />' },
  'a-tooltip': { props: ['title'], template: '<span><slot /></span>' },
  'a-table': {
    props: ['columns', 'dataSource', 'pagination', 'size', 'rowKey'],
    template: '<table />',
  },
  'a-collapse': { template: '<div><slot /></div>' },
  'a-collapse-panel': { props: ['key', 'header'], template: '<div>{{ header }}<slot /></div>' },
  'a-progress': { props: ['percent', 'status', 'size'], template: '<div />' },
  'a-spin': { props: ['spinning', 'size'], template: '<div><slot /></div>' },
  'a-empty': { props: ['description'], template: '<div />' },
  'page-analysis-block': { props: ['analysis', 'steps'], template: '<div />' },
  'step-timeline-block': { props: ['steps'], template: '<div />' },
  'verification-block': {
    props: ['selfAssessment', 'supervisor', 'scorecard', 'isRunning'],
    template: '<div />',
  },
  'plus-outlined': { template: '<i />' },
  'delete-outlined': { template: '<i />' },
  'reload-outlined': { template: '<i />' },
  'play-circle-outlined': { template: '<i />' },
  'bulb-outlined': { template: '<i />' },
  'check-circle-outlined': { template: '<i />' },
  'exclamation-circle-outlined': { template: '<i />' },
  'info-circle-outlined': { template: '<i />' },
  'link-outlined': { template: '<i />' },
  'copy-outlined': { template: '<i />' },
};

function mockSpecs() {
  return [
    {
      spec_id: 'login',
      page_id: 'login',
      url_pattern: '/entry',
      description: 'Login page',
      scenarios: [
        {
          key: 'valid_credentials',
          description: 'Valid login',
          inputs: { username: 'admin', password: 'secret' },
          selections: {},
        },
      ],
    },
  ];
}

describe('AutonomousWorkbenchPage', () => {
  beforeEach(() => {
    listSpecs.mockReset();
    streamAutonomousRun.mockReset();
    push.mockReset();
    messageSuccess.mockReset();
    messageError.mockReset();
    messageWarning.mockReset();
  });

  it('renders the config card on mount', async () => {
    listSpecs.mockResolvedValue(mockSpecs());
    const wrapper = mount(AutonomousWorkbenchPage, { global: { stubs } });
    await flushPromises();

    expect(wrapper.find('.config-card').exists()).toBe(true);
    // Actual rendered text from real i18n translations
    expect(wrapper.text()).toContain('Run configuration');
  });

  it('loads specs on mount', async () => {
    listSpecs.mockResolvedValue(mockSpecs());
    mount(AutonomousWorkbenchPage, { global: { stubs } });
    await flushPromises();

    expect(listSpecs).toHaveBeenCalledTimes(1);
  });

  it('renders form inputs for URL and goal', async () => {
    listSpecs.mockResolvedValue(mockSpecs());
    const wrapper = mount(AutonomousWorkbenchPage, { global: { stubs } });
    await flushPromises();

    expect(wrapper.text()).toContain('URL');
    expect(wrapper.text()).toContain('Goal');
  });

  it('shows spec matched alert when URL matches a spec', async () => {
    listSpecs.mockResolvedValue(mockSpecs());
    const wrapper = mount(AutonomousWorkbenchPage, { global: { stubs } });
    await flushPromises();

    const vm = wrapper.vm as unknown as { form: { url: string } };
    vm.form.url = '/entry';
    await flushPromises();

    expect(wrapper.text()).toContain('Spec matched');
  });

  it('shows no-match warning when URL does not match any spec', async () => {
    listSpecs.mockResolvedValue(mockSpecs());
    const wrapper = mount(AutonomousWorkbenchPage, { global: { stubs } });
    await flushPromises();

    const vm = wrapper.vm as unknown as { form: { url: string } };
    vm.form.url = '/nonexistent';
    await flushPromises();

    expect(wrapper.text()).toContain('No spec matches this URL');
  });

  it('shows error when listSpecs fails', async () => {
    listSpecs.mockRejectedValue(new Error('network down'));
    const wrapper = mount(AutonomousWorkbenchPage, { global: { stubs } });
    await flushPromises();

    expect(messageWarning).toHaveBeenCalled();
  });
});
