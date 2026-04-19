<template>
  <a-dropdown trigger="click" placement="bottomRight">
    <button class="lang-btn" type="button">
      <span class="lang-globe">🌐</span>
      <span>{{ currentLabel }}</span>
    </button>
    <template #overlay>
      <a-menu :selected-keys="[String(locale)]" @click="onPick">
        <a-menu-item
          v-for="loc in SUPPORTED_LOCALES"
          :key="loc"
        >
          {{ LOCALE_LABELS[loc] }}
        </a-menu-item>
      </a-menu>
    </template>
  </a-dropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { SUPPORTED_LOCALES, LOCALE_LABELS, type SupportedLocale } from '../i18n';

const { locale } = useI18n();

const currentLabel = computed(() => LOCALE_LABELS[locale.value as SupportedLocale] ?? locale.value);

function onPick(info: { key: string }) {
  const next = info.key as SupportedLocale;
  locale.value = next;
  try {
    localStorage.setItem('validation_locale', next);
  } catch {
    // Storage may be unavailable (e.g. private mode). The in-memory
    // switch still works for the rest of the session.
  }
}
</script>

<style scoped>
.lang-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 13px;
  color: #1f2937;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  transition: background 0.15s, border-color 0.15s;
}
.lang-btn:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}
.lang-globe {
  font-size: 14px;
  line-height: 1;
}
</style>
