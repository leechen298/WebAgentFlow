import { defineConfig } from 'wxt';

export default defineConfig({
  modules: ['@wxt-dev/module-vue'],
  manifest: {
    name: 'WebAgentFlow Recorder',
    description: 'Chrome extension scaffold for WebAgentFlow recording.',
    default_locale: 'en',
    permissions: ['storage', 'activeTab', 'scripting'],
    host_permissions: ['<all_urls>'],
  },
});
