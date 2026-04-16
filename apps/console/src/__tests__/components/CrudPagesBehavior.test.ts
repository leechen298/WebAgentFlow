import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { defineComponent } from 'vue';
import { message } from 'ant-design-vue';
import RecordingsPage from '@/pages/RecordingsPage.vue';
import SkillsPage from '@/pages/SkillsPage.vue';
import RunsPage from '@/pages/RunsPage.vue';

const push = vi.fn();

const recording = {
  id: 'rec-1',
  name: 'Recording 1',
  status: 'draft',
  source: 'extension',
  events: [],
  meta: {},
  created_at: '2026-04-16T00:00:00Z',
};

const skill = {
  id: 'skill-1',
  name: 'Skill 1',
  version: '1.0.0',
  status: 'draft',
  recording_id: 'rec-1',
  description: 'desc',
  definition: {},
  created_at: '2026-04-16T00:00:00Z',
  updated_at: '2026-04-16T00:00:00Z',
};

const run = {
  id: 'run-1',
  skill_id: 'skill-1',
  status: 'pending',
  started_at: null,
  finished_at: null,
  input_payload: {},
  result_payload: null,
  logs: null,
  created_at: '2026-04-16T00:00:00Z',
};

const recordingsStore = {
  recordings: [recording],
  loadingList: false,
  loading: false,
  error: null,
  hasPrev: false,
  hasNext: true,
  fetchFirstPage: vi.fn().mockResolvedValue(undefined),
  fetchNextPage: vi.fn().mockResolvedValue(undefined),
  fetchPrevPage: vi.fn().mockResolvedValue(undefined),
  createRecording: vi.fn().mockResolvedValue(recording),
  updateRecording: vi.fn().mockResolvedValue(recording),
  deleteRecording: vi.fn().mockResolvedValue(undefined),
};

const skillsStore = {
  skills: [skill],
  loadingList: false,
  loading: false,
  error: null,
  hasPrev: false,
  hasNext: true,
  fetchFirstPage: vi.fn().mockResolvedValue(undefined),
  fetchNextPage: vi.fn().mockResolvedValue(undefined),
  fetchPrevPage: vi.fn().mockResolvedValue(undefined),
  createSkill: vi.fn().mockResolvedValue(skill),
  updateSkill: vi.fn().mockResolvedValue(skill),
  deleteSkill: vi.fn().mockResolvedValue(undefined),
};

const runsStore = {
  runs: [run],
  loadingList: false,
  loading: false,
  error: null,
  hasPrev: false,
  hasNext: true,
  fetchFirstPage: vi.fn().mockResolvedValue(undefined),
  fetchNextPage: vi.fn().mockResolvedValue(undefined),
  fetchPrevPage: vi.fn().mockResolvedValue(undefined),
  createRun: vi.fn().mockResolvedValue(run),
  updateRun: vi.fn().mockResolvedValue(run),
  deleteRun: vi.fn().mockResolvedValue(undefined),
};

vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
}));

vi.mock('@/stores', () => ({
  useRecordingsStore: () => recordingsStore,
  useSkillsStore: () => skillsStore,
  useRunsStore: () => runsStore,
}));

function getSetupState(wrapper: ReturnType<typeof mount>) {
  return (wrapper.vm as any).$?.setupState ?? wrapper.vm;
}

const TableStub = defineComponent({
  props: ['columns', 'dataSource'],
  template: `
    <div>
      <div v-if="!dataSource || dataSource.length === 0">
        <slot name="emptyText" />
      </div>
      <div v-for="record in (dataSource || [])" :key="record.id">
        <div v-for="column in (columns || [])" :key="column.key">
          <slot name="bodyCell" :column="column" :record="record">
            {{ record[column.dataIndex || column.key] }}
          </slot>
        </div>
      </div>
    </div>
  `,
});

const renderStubs = {
  'a-card': { template: '<section><slot name="title" /><slot /></section>' },
  'a-spin': { template: '<div><slot /></div>' },
  'a-table': TableStub,
  'a-tag': { template: '<span><slot /></span>' },
  'a-space': { template: '<div><slot /></div>' },
  'a-button': { emits: ['click'], template: '<button @click="$emit(\'click\')"><slot /><slot name="icon" /></button>' },
  'a-popconfirm': { emits: ['confirm'], template: '<div><slot /><button class="confirm" @click="$emit(\'confirm\')" /></div>' },
  'a-empty': { props: ['description'], template: '<div>{{ description }}<slot /></div>' },
  'a-modal': { props: ['open', 'title'], template: '<div>{{ title }}<slot v-if="open" /></div>' },
  'a-form': { template: '<form><slot /></form>' },
  'a-row': { template: '<div><slot /></div>' },
  'a-col': { template: '<div><slot /></div>' },
  'a-form-item': { props: ['label'], template: '<label>{{ label }}<slot /></label>' },
  'a-input': { template: '<input />' },
  'a-select': { template: '<select><slot /></select>' },
  'a-select-option': { props: ['value'], template: '<option><slot /></option>' },
  'a-textarea': { props: ['value'], template: '<textarea>{{ value }}</textarea>' },
  'a-date-picker': { template: '<input type="datetime-local" />' },
  'plus-outlined': { template: '<i />' },
};

describe('CRUD page behavior', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('covers RecordingsPage create/edit/validate/delete/navigation flow', async () => {
    const wrapper = mount(RecordingsPage);
    const vm = getSetupState(wrapper);
    vm.formRef = { validate: vi.fn().mockResolvedValue(undefined) };

    vm.showCreateModal();
    expect(vm.modalOpen).toBe(true);
    vm.formData.name = 'Created';
    vm.formData.source = 'web';
    vm.formData.eventsStr = '[]';
    vm.formData.metaStr = '{}';
    await vm.handleSave();
    expect(recordingsStore.createRecording).toHaveBeenCalled();

    vm.editRecording(recording as never);
    expect(vm.isEditing).toBe(true);
    vm.formData.eventsStr = '{';
    expect(vm.validateJson('events')).toBe(false);
    vm.formData.eventsStr = '[]';
    expect(vm.validateJson('events')).toBe(true);

    await vm.deleteRecording('rec-1');
    expect(recordingsStore.deleteRecording).toHaveBeenCalledWith('rec-1');

    vm.viewDetail('rec-1');
    expect(push).toHaveBeenCalledWith('/recordings/rec-1');
  });

  it('covers SkillsPage create/edit/validate/delete/navigation flow', async () => {
    const wrapper = mount(SkillsPage);
    const vm = getSetupState(wrapper);
    vm.formRef = { validate: vi.fn().mockResolvedValue(undefined) };

    vm.showCreateModal();
    vm.formData.name = 'Skill X';
    vm.formData.version = '1.0.0';
    vm.formData.definitionStr = '{}';
    await vm.handleSave();
    expect(skillsStore.createSkill).toHaveBeenCalled();

    vm.editSkill(skill as never);
    expect(vm.isEditing).toBe(true);
    vm.formData.definitionStr = '{';
    expect(vm.validateJson()).toBe(false);
    vm.formData.definitionStr = '{}';
    await vm.handleSave();
    expect(skillsStore.updateSkill).toHaveBeenCalled();

    await vm.deleteSkill('skill-1');
    expect(skillsStore.deleteSkill).toHaveBeenCalledWith('skill-1');

    vm.viewDetail('skill-1');
    expect(push).toHaveBeenCalledWith('/skills/skill-1');
  });

  it('covers RunsPage create/edit/validate/delete/navigation flow', async () => {
    const wrapper = mount(RunsPage);
    const vm = getSetupState(wrapper);
    vm.formRef = { validate: vi.fn().mockResolvedValue(undefined) };

    vm.showCreateModal();
    vm.formData.skill_id = 'skill-1';
    vm.formData.inputPayloadStr = '{}';
    await vm.handleSave();
    expect(runsStore.createRun).toHaveBeenCalled();

    vm.editRun(run as never);
    expect(vm.isEditing).toBe(true);
    vm.formData.logsStr = '[';
    expect(vm.validateJson('logs')).toBe(false);
    vm.formData.logsStr = '[]';
    await vm.handleSave();
    expect(runsStore.updateRun).toHaveBeenCalled();

    await vm.deleteRun('run-1');
    expect(runsStore.deleteRun).toHaveBeenCalledWith('run-1');

    vm.viewDetail('run-1');
    expect(push).toHaveBeenCalledWith('/runs/run-1');
  });

  it('covers RecordingsPage paging, helpers, reset, and error branches', async () => {
    const wrapper = mount(RecordingsPage);
    const vm = getSetupState(wrapper);

    expect(vm.columns).toHaveLength(5);
    expect(vm.getStatusColor('archived')).toBe('orange');
    expect(vm.getStatusColor('weird')).toBe('default');
    expect(typeof vm.formatDate('2026-04-16T00:00:00Z')).toBe('string');
    expect(vm.error).toBeNull();

    await vm.fetchRecordings();
    await vm.goNextPage();
    await vm.goPrevPage();
    await vm.goFirstPage();
    expect(recordingsStore.fetchFirstPage).toHaveBeenCalled();
    expect(recordingsStore.fetchNextPage).toHaveBeenCalled();
    expect(recordingsStore.fetchPrevPage).toHaveBeenCalled();

    vm.formData.name = 'x';
    vm.resetForm();
    expect(vm.formData.name).toBe('');
    expect(vm.validateJson('meta')).toBe(true);

    vm.formRef = { validate: vi.fn().mockRejectedValue(new Error('Validation failed')) };
    await vm.handleSave();
    expect(message.error).not.toHaveBeenCalledWith('Validation failed');

    recordingsStore.fetchNextPage.mockRejectedValueOnce(new Error('next failed'));
    await vm.goNextPage();
    expect(message.error).toHaveBeenCalled();

    recordingsStore.deleteRecording.mockRejectedValueOnce(new Error('delete failed'));
    await vm.deleteRecording('rec-1');
    expect(message.error).toHaveBeenCalled();
  });

  it('covers SkillsPage paging, helpers, reset, and error branches', async () => {
    const wrapper = mount(SkillsPage);
    const vm = getSetupState(wrapper);

    expect(vm.columns).toHaveLength(6);
    expect(vm.getStatusColor('published')).toBe('green');
    expect(vm.getStatusColor('other')).toBe('default');
    expect(typeof vm.formatDate('2026-04-16T00:00:00Z')).toBe('string');
    expect(vm.error).toBeNull();

    await vm.fetchSkills();
    await vm.goNextPage();
    await vm.goPrevPage();
    await vm.goFirstPage();
    expect(skillsStore.fetchFirstPage).toHaveBeenCalled();
    expect(skillsStore.fetchNextPage).toHaveBeenCalled();
    expect(skillsStore.fetchPrevPage).toHaveBeenCalled();

    vm.formData.name = 'changed';
    vm.resetForm();
    expect(vm.formData.version).toBe('1.0.0');
    vm.formData.definitionStr = '';
    expect(vm.validateJson()).toBe(true);

    vm.formRef = { validate: vi.fn().mockRejectedValue(new Error('Validation failed')) };
    await vm.handleSave();
    expect(message.error).not.toHaveBeenCalledWith('Validation failed');

    skillsStore.fetchPrevPage.mockRejectedValueOnce(new Error('prev failed'));
    await vm.goPrevPage();
    expect(message.error).toHaveBeenCalled();

    skillsStore.deleteSkill.mockRejectedValueOnce(new Error('delete failed'));
    await vm.deleteSkill('skill-1');
    expect(message.error).toHaveBeenCalled();
  });

  it('covers RunsPage paging, helpers, reset, and error branches', async () => {
    const wrapper = mount(RunsPage);
    const vm = getSetupState(wrapper);

    expect(vm.columns).toHaveLength(6);
    expect(vm.getStatusColor('running')).toBe('processing');
    expect(vm.getStatusColor('unknown')).toBe('default');
    expect(typeof vm.formatDate('2026-04-16T00:00:00Z')).toBe('string');
    expect(vm.error).toBeNull();

    await vm.fetchRuns();
    await vm.goNextPage();
    await vm.goPrevPage();
    await vm.goFirstPage();
    expect(runsStore.fetchFirstPage).toHaveBeenCalled();
    expect(runsStore.fetchNextPage).toHaveBeenCalled();
    expect(runsStore.fetchPrevPage).toHaveBeenCalled();

    vm.formData.skill_id = 'changed';
    vm.resetForm();
    expect(vm.formData.skill_id).toBe('');
    vm.formData.resultPayloadStr = '';
    expect(vm.validateJson('result_payload')).toBe(true);

    vm.formRef = { validate: vi.fn().mockRejectedValue(new Error('Validation failed')) };
    await vm.handleSave();
    expect(message.error).not.toHaveBeenCalledWith('Validation failed');

    runsStore.fetchFirstPage.mockRejectedValueOnce(new Error('first failed'));
    await vm.goFirstPage();
    expect(message.error).toHaveBeenCalled();

    runsStore.deleteRun.mockRejectedValueOnce(new Error('delete failed'));
    await vm.deleteRun('run-1');
    expect(message.error).toHaveBeenCalled();
  });

  it('renders CRUD table pages, action slots, empty states, and modal branches', async () => {
    const recordingsWrapper = mount(RecordingsPage, { global: { stubs: renderStubs } });
    await flushPromises();
    expect(recordingsWrapper.text()).toContain('Recording 1');
    expect(recordingsWrapper.text()).toContain('draft');
    await recordingsWrapper.findAll('button')[0].trigger('click');
    expect(getSetupState(recordingsWrapper).modalOpen).toBe(true);

    const skillsWrapper = mount(SkillsPage, { global: { stubs: renderStubs } });
    await flushPromises();
    expect(skillsWrapper.text()).toContain('Skill 1');
    expect(skillsWrapper.text()).toContain('draft');
    await skillsWrapper.findAll('button')[1].trigger('click');
    expect(push).toHaveBeenCalledWith('/skills/skill-1');

    const runsWrapper = mount(RunsPage, { global: { stubs: renderStubs } });
    await flushPromises();
    expect(runsWrapper.text()).toContain('skill-1');
    expect(runsWrapper.text()).toContain('pending');
    await runsWrapper.findAll('button')[1].trigger('click');
    expect(push).toHaveBeenCalledWith('/runs/run-1');

    recordingsStore.recordings = [];
    skillsStore.skills = [];
    runsStore.runs = [];

    const emptyRecordings = mount(RecordingsPage, { global: { stubs: renderStubs } });
    const emptySkills = mount(SkillsPage, { global: { stubs: renderStubs } });
    const emptyRuns = mount(RunsPage, { global: { stubs: renderStubs } });

    expect(emptyRecordings.text()).toBeTruthy();
    expect(emptySkills.text()).toBeTruthy();
    expect(emptyRuns.text()).toBeTruthy();

    recordingsStore.recordings = [recording];
    skillsStore.skills = [skill];
    runsStore.runs = [run];
  });
});
