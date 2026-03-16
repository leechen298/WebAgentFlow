<template>
  <n-layout has-sider class="shell">
    <n-layout-sider bordered collapse-mode="width" :collapsed-width="72" :width="240" show-trigger>
      <div class="brand">
        <span class="brand-mark">WF</span>
        <div class="brand-copy">
          <strong>WebAgentFlow</strong>
          <span>Task Pack 1</span>
        </div>
      </div>
      <n-menu :options="menuOptions" :value="selectedKey" @update:value="handleSelect" />
    </n-layout-sider>

    <n-layout>
      <n-layout-header bordered class="header">
        <div>
          <div class="eyebrow">Engineering Foundation</div>
          <h1>{{ pageTitle }}</h1>
        </div>
        <n-tag type="info" round>Monorepo Skeleton</n-tag>
      </n-layout-header>
      <n-layout-content content-style="padding: 24px">
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { computed, h } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import type { MenuOption } from 'naive-ui';
import { NLayout, NLayoutContent, NLayoutHeader, NLayoutSider, NMenu, NTag } from 'naive-ui';

const route = useRoute();
const router = useRouter();

const menuOptions: MenuOption[] = [
  { key: '/', label: () => h('span', 'Overview') },
  { key: '/recordings', label: () => h('span', 'Recordings') },
  { key: '/skills', label: () => h('span', 'Skills') },
  { key: '/runs', label: () => h('span', 'Runs') },
];

const selectedKey = computed(() => String(route.meta.menuKey ?? route.path));
const pageTitle = computed(() => String(route.meta.title ?? 'WebAgentFlow Console'));

function handleSelect(key: string) {
  void router.push(key);
}
</script>

<style scoped>
.shell {
  min-height: 100vh;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 18px;
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
}

.brand-copy {
  display: flex;
  flex-direction: column;
}

.brand-copy span {
  font-size: 12px;
  color: #5b6475;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(10px);
}

.eyebrow {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #5b6475;
}

h1 {
  margin: 4px 0 0;
  font-size: 26px;
}
</style>
