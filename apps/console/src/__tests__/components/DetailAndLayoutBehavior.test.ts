import { beforeEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { message } from 'ant-design-vue';
import MainLayout from '@/layouts/MainLayout.vue';
import LocaleSwitcher from '@/components/LocaleSwitcher.vue';
import SkillDetailPage from '@/pages/SkillDetailPage.vue';
import RunDetailPage from '@/pages/RunDetailPage.vue';

const push = vi.fn();
const checkApiHealth = vi.fn().mockResolvedValue(undefined);
const setLocale = vi.fn();

const skill = {
  id: 'skill-1',
  name: 'Skill 1',
  version: '1.0.0',
  status: 'published',
  recording_id: 'rec-1',
  description: 'desc',
  definition: {},
  created_at: '2026-04-16T00:00:00Z',
  updated_at: '2026-04-16T00:00:00Z',
};

const run = {
  id: 'run-1',
  skill_id: 'skill-1',
  status: 'succeeded',
  started_at: '2026-04-16T00:00:00Z',
  finished_at: '2026-04-16T00:01:00Z',
  input_payload: {},
  result_payload: {},
  logs: [],
  created_at: '2026-04-16T00:00:00Z',
};

const appStore = {
  apiConnected: true,
  loading: false,
  locale: 'en',
  setLocale,
  checkApiHealth,
};

const skillsStore = {
  currentSkill: skill,
  loading: false,
  error: null,
  fetchSkill: vi.fn().mockResolvedValue(undefined),
  updateSkill: vi.fn().mockResolvedValue(skill),
  deleteSkill: vi.fn().mockResolvedValue(undefined),
  clearCurrent: vi.fn(),
};

const runsStore = {
  currentRun: run,
  loading: false,
  error: null,
  fetchRun: vi.fn().mockResolvedValue(undefined),
  updateRun: vi.fn().mockResolvedValue(run),
  deleteRun: vi.fn().mockResolvedValue(undefined),
  clearCurrent: vi.fn(),
};

vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
  useRoute: () => ({ path: '/skills', meta: { menuKey: '/skills', titleKey: 'nav.skills' }, params: { id: 'skill-1' } }),
}));

vi.mock('@/stores', () => ({
  useAppStore: () => appStore,
  useSkillsStore: () => skillsStore,
  useRunsStore: () => runsStore,
}));

function getSetupState(wrapper: ReturnType<typeof mount>) {
  return (wrapper.vm as any).$?.setupState ?? wrapper.vm;
}

describe('detail pages and layout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(window, 'innerWidth', { value: 640, writable: true });
  });

  it('covers SkillDetailPage edit/save/delete/back flow', async () => {
    const wrapper = mount(SkillDetailPage);
    const vm = getSetupState(wrapper);
    vm.formRef = { validate: vi.fn().mockResolvedValue(undefined) };

    vm.showEditModal();
    expect(vm.editModalOpen).toBe(true);
    vm.formData.definitionStr = '{';
    expect(vm.validateJson()).toBe(false);
    vm.formData.definitionStr = '{}';
    await vm.handleSave();
    expect(skillsStore.updateSkill).toHaveBeenCalledWith('skill-1', expect.objectContaining({ name: 'Skill 1' }));

    await vm.handleDelete();
    expect(skillsStore.deleteSkill).toHaveBeenCalledWith('skill-1');
    expect(push).toHaveBeenCalledWith('/skills');

    vm.goBack();
    expect(push).toHaveBeenCalledWith('/skills');
  });

  it('covers RunDetailPage edit/save/delete/back flow', async () => {
    const wrapper = mount(RunDetailPage);
    const vm = getSetupState(wrapper);
    vm.formRef = { validate: vi.fn().mockResolvedValue(undefined) };

    vm.showEditModal();
    expect(vm.editModalOpen).toBe(true);
    vm.formData.logsStr = '[';
    expect(vm.validateJson('logs')).toBe(false);
    vm.formData.logsStr = '[]';
    await vm.handleSave();
    expect(runsStore.updateRun).toHaveBeenCalledWith('skill-1', expect.any(Object));

    await vm.handleDelete();
    expect(runsStore.deleteRun).toHaveBeenCalledWith('skill-1');
    expect(push).toHaveBeenCalledWith('/runs');

    vm.goBack();
    expect(push).toHaveBeenCalledWith('/runs');
  });

  it('covers MainLayout responsive/menu behavior and locale switching', async () => {
    const layout = mount(MainLayout);
    const layoutVm = getSetupState(layout);

    expect(checkApiHealth).toHaveBeenCalled();
    expect(layoutVm.collapsed).toBe(true);
    expect(layoutVm.selectedKeys).toEqual(['/skills']);
    expect(layoutVm.pageTitle).toBeTruthy();
    expect(layoutVm.apiStatus).toBe('success');
    expect(layoutVm.apiStatusText).toBeTruthy();

    Object.defineProperty(window, 'innerWidth', { value: 1200, writable: true });
    layoutVm.handleResize();
    expect(layoutVm.collapsed).toBe(false);

    layoutVm.handleMenuClick({ key: '/recordings' });
    expect(push).toHaveBeenCalledWith('/recordings');

    const locale = mount(LocaleSwitcher);
    const localeVm = getSetupState(locale);
    localeVm.handleChange('zh');
    expect(setLocale).toHaveBeenCalledWith('zh');
    expect(localeVm.appStore.locale).toBe('en');
  });

  it('covers MainLayout fallback title, loading/error api states, and unmount cleanup', async () => {
    vi.resetModules();
    vi.doMock('vue-router', () => ({
      useRouter: () => ({ push }),
      useRoute: () => ({ path: '/unknown', meta: {}, params: { id: 'run-1' } }),
    }));
    vi.doMock('@/stores', () => ({
      useAppStore: () => ({ ...appStore, apiConnected: false, loading: true }),
      useSkillsStore: () => skillsStore,
      useRunsStore: () => runsStore,
    }));

    const removeSpy = vi.spyOn(window, 'removeEventListener');
    const { default: FreshMainLayout } = await import('@/layouts/MainLayout.vue');
    const wrapper = mount(FreshMainLayout);
    const vm = getSetupState(wrapper);

    expect(vm.pageTitle).toBe('WebAgentFlow Console');
    expect(vm.apiStatus).toBe('processing');
    expect(vm.apiStatusText).toBeTruthy();

    wrapper.unmount();
    expect(removeSpy).toHaveBeenCalledWith('resize', vm.handleResize);
    removeSpy.mockRestore();
  });

  it('covers SkillDetailPage helper and error branches', async () => {
    const wrapper = mount(SkillDetailPage);
    const vm = getSetupState(wrapper);

    expect(vm.getStatusColor('draft')).toBe('default');
    expect(vm.getStatusColor('other')).toBe('default');
    expect(typeof vm.formatDate('2026-04-16T00:00:00Z')).toBe('string');
    expect(vm.rules.name[0].message).toBeTruthy();
    expect(vm.error).toBeNull();

    skillsStore.fetchSkill.mockRejectedValueOnce(new Error('load failed'));
    await vm.fetchSkill();
    expect(message.error).toHaveBeenCalled();

    vm.editModalOpen = false;
    skillsStore.currentSkill = null as any;
    vm.showEditModal();
    expect(vm.editModalOpen).toBe(false);
    skillsStore.currentSkill = skill as any;

    vm.formRef = { validate: vi.fn().mockRejectedValue(new Error('invalid')) };
    await vm.handleSave();
    expect(message.error).toHaveBeenCalled();

    skillsStore.deleteSkill.mockRejectedValueOnce(new Error('delete failed'));
    await vm.handleDelete();
    expect(message.error).toHaveBeenCalled();
  });

  it('covers RunDetailPage helper and error branches', async () => {
    const wrapper = mount(RunDetailPage);
    const vm = getSetupState(wrapper);

    expect(vm.getStatusColor('queued')).toBe('blue');
    expect(vm.getStatusColor('other')).toBe('default');
    expect(typeof vm.formatDate('2026-04-16T00:00:00Z')).toBe('string');
    expect(vm.rules.skill_id[0].message).toBeTruthy();
    expect(vm.validateJson('input_payload')).toBe(true);
    expect(vm.validateJson('result_payload')).toBe(true);
    expect(vm.error).toBeNull();

    runsStore.fetchRun.mockRejectedValueOnce(new Error('load failed'));
    await vm.fetchRun();
    expect(message.error).toHaveBeenCalled();

    vm.editModalOpen = false;
    runsStore.currentRun = null as any;
    vm.showEditModal();
    expect(vm.editModalOpen).toBe(false);
    runsStore.currentRun = run as any;

    vm.formRef = { validate: vi.fn().mockRejectedValue(new Error('invalid')) };
    await vm.handleSave();
    expect(message.error).toHaveBeenCalled();

    runsStore.deleteRun.mockRejectedValueOnce(new Error('delete failed'));
    await vm.handleDelete();
    expect(message.error).toHaveBeenCalled();
  });
});
