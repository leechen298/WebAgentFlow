<template>
  <a-select
    :value="appStore.locale"
    size="small"
    style="width: 100px"
    @change="handleChange"
  >
    <a-select-option value="en">English</a-select-option>
    <a-select-option value="zh">中文</a-select-option>
  </a-select>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { useAppStore } from '@/stores';
import type { SupportedLocale } from '@/i18n';

const appStore = useAppStore();
const { locale: i18nLocale } = useI18n();

function handleChange(value: SupportedLocale) {
  appStore.setLocale(value);
  i18nLocale.value = value;
}
</script>
