<template>
  <a-layout style="min-height: 100vh">
    <a-layout-sider v-model:collapsed="collapsed" collapsible width="240">
      <div class="brand">
        <span class="brand-mark">WF</span>
        <div v-if="!collapsed" class="brand-copy">
          <strong>WebAgentFlow</strong>
          <span>v0.1</span>
        </div>
      </div>
      <a-menu
        v-model:selectedKeys="selectedKeys"
        mode="inline"
        theme="dark"
        @click="handleMenuClick"
      >
        <a-menu-item key="/">
          <dashboard-outlined />
          <span>{{ $t('nav.overview') }}</span>
        </a-menu-item>
        <a-menu-item key="/exploration/autonomous">
          <thunderbolt-outlined />
          <span>{{ $t('nav.autonomousExploration') }}</span>
        </a-menu-item>
        <a-menu-item key="/exploration/autonomous/history">
          <history-outlined />
          <span>{{ $t('nav.autonomousHistory') }}</span>
        </a-menu-item>
      </a-menu>
    </a-layout-sider>

    <a-layout>
      <a-layout-header style="background: #fff; padding: 0 24px; border-bottom: 1px solid #f0f0f0">
        <div class="header-left">
          <div class="eyebrow">{{ $t('header.eyebrow') }}</div>
          <h1>{{ pageTitle }}</h1>
        </div>
        <div class="header-right">
          <LocaleSwitcher />
          <a-badge :status="apiStatus" :text="apiStatusText" />
        </div>
      </a-layout-header>
      <a-layout-content style="padding: 24px; background: #f0f2f5">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import {
  DashboardOutlined,
  HistoryOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons-vue';
import { useAppStore } from '@/stores';
import LocaleSwitcher from '@/components/LocaleSwitcher.vue';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const appStore = useAppStore();

const collapsed = ref(false);
const selectedKeys = ref<string[]>([String(route.meta.menuKey ?? route.path)]);

const BREAKPOINT = 768;

const pageTitle = computed(() => {
  const key = String(route.meta.titleKey ?? '');
  return key ? t(key) : 'WebAgentFlow Console';
});

const apiStatus = computed(() => {
  if (appStore.loading) return 'processing';
  return appStore.apiConnected ? 'success' : 'error';
});

const apiStatusText = computed(() => {
  if (appStore.loading) return t('status.checking');
  return appStore.apiConnected ? t('status.apiConnected') : t('status.apiDisconnected');
});

function handleMenuClick({ key }: { key: string }) {
  void router.push(key);
}

function handleResize() {
  collapsed.value = window.innerWidth < BREAKPOINT;
}

onMounted(() => {
  handleResize();
  window.addEventListener('resize', handleResize);
  void appStore.checkApiHealth();
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 18px;
  height: 64px;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  background: linear-gradient(135deg, #102a43, #1f7a8c);
  color: #f8fbff;
  font-weight: 700;
  flex-shrink: 0;
}

.brand-copy {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.brand-copy strong {
  color: #fff;
  font-size: 15px;
}

.brand-copy span {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
}

:deep(.ant-layout-sider-collapsed .brand-copy) {
  display: none;
}

:deep(.ant-layout-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: auto;
  padding: 18px 24px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left {
  display: flex;
  flex-direction: column;
}

.eyebrow {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #8c8c8c;
}

h1 {
  margin: 4px 0 0;
  font-size: 26px;
  color: #262626;
}
</style>
