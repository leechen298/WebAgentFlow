import { config } from '@vue/test-utils';
import { vi } from 'vitest';
import i18n from '@/i18n';

// Mock import.meta.env
vi.stubGlobal('import.meta', {
  env: {
    VITE_API_BASE_URL: 'http://localhost:8001',
    VITE_USE_DEV_PROXY: 'false',
    DEV: true,
    PROD: false,
  },
});

// Mock Ant Design Vue components
config.global.stubs = {
  'a-row': true,
  'a-col': true,
  'a-card': true,
  'a-space': true,
  'a-alert': true,
  'a-statistic': true,
  'a-button': true,
  'a-tag': true,
  'a-descriptions': true,
  'a-descriptions-item': true,
  'a-divider': true,
  'a-layout': true,
  'a-layout-sider': true,
  'a-layout-content': true,
  'a-layout-header': true,
  'a-menu': true,
  'a-menu-item': true,
  'a-table': true,
  'a-tabs': true,
  'a-tab-pane': true,
  'a-input': true,
  'a-input-search': true,
  'a-input-number': true,
  'a-modal': true,
  'a-form': true,
  'a-form-item': true,
  'a-select': true,
  'a-select-option': true,
  'a-date-picker': true,
  'a-textarea': true,
  'a-popconfirm': true,
  'a-empty': true,
  'a-spin': true,
  'a-result': true,
  'a-page-header': true,
  'a-collapse': true,
  'a-collapse-panel': true,
  'a-timeline': true,
  'a-timeline-item': true,
  'a-radio-group': true,
  'a-radio-button': true,
  'a-input-number-group': true,
  'a-tooltip': true,
  'a-checkbox': true,
};

config.global.plugins = [i18n];

// Mock message from ant-design-vue
vi.mock('ant-design-vue', async () => {
  const actual = await vi.importActual('ant-design-vue');
  return {
    ...actual,
    message: {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    },
  };
});
