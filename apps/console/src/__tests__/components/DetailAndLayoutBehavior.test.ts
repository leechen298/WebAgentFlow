import { beforeEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';
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

    Object.defineProperty(window, 'innerWidth', { value: 1200, writable: true });
    layoutVm.handleResize();
    expect(layoutVm.collapsed).toBe(false);

    layoutVm.handleMenuClick({ key: '/recordings' });
    expect(push).toHaveBeenCalledWith('/recordings');

    const locale = mount(LocaleSwitcher);
    const localeVm = getSetupState(locale);
    localeVm.handleChange('zh');
    expect(setLocale).toHaveBeenCalledWith('zh');
  });
});
