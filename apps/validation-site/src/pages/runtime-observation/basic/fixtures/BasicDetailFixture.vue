<template>
  <div class="fixture-inner">
    <div v-if="loading" class="loading" data-testid="basic-detail-loading">
      {{ t('runtimeFixtures.detail.loading') }}
    </div>

    <div v-else-if="notFound" class="not-found" data-testid="basic-detail-not-found">
      <p><strong>{{ t('runtimeFixtures.detail.notFound') }}</strong></p>
      <p>{{ t('runtimeFixtures.detail.notFoundHint') }}</p>
    </div>

    <div v-else class="detail-card" data-testid="basic-detail-summary-card">
      <div class="detail-header">
        <h3>{{ record.name }}</h3>
        <span class="badge" :class="record.status">{{ record.status }}</span>
      </div>
      <div class="detail-grid">
        <div><strong>ID</strong> {{ record.id }}</div>
        <div><strong>{{ t('runtimeFixtures.detail.owner') }}</strong> {{ record.owner }}</div>
        <div><strong>{{ t('runtimeFixtures.detail.lastUpdated') }}</strong> {{ record.lastUpdated }}</div>
      </div>
      <div class="metadata" data-testid="basic-detail-metadata">
        <h4>{{ t('runtimeFixtures.detail.metadata') }}</h4>
        <div class="detail-grid">
          <div><strong>{{ t('runtimeFixtures.detail.created') }}</strong> {{ record.created }}</div>
          <div><strong>{{ t('runtimeFixtures.detail.category') }}</strong> {{ record.category }}</div>
          <div><strong>{{ t('runtimeFixtures.detail.source') }}</strong> {{ record.source }}</div>
        </div>
      </div>
    </div>

    <div class="action-row">
      <button
        class="btn btn-primary"
        data-testid="basic-fixture-primary-trigger"
        :disabled="loading"
        @click="onRefresh"
      >
        {{ t('runtimeFixtures.detail.refresh') }}
      </button>
      <button
        class="btn btn-secondary"
        data-testid="basic-fixture-secondary-trigger"
        :disabled="loading"
        @click="onLoadMissing"
      >
        {{ t('runtimeFixtures.detail.loadMissing') }}
      </button>
    </div>

    <div class="distractor-row">
      <button class="btn btn-secondary" data-testid="basic-detail-distractor" @click="onCopyId">
        {{ t('runtimeFixtures.detail.copyId') }}
      </button>
    </div>

    <div v-if="hint" class="hint-surface">{{ hint }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useFixtureTimer } from '../useFixtureTimer';

const emit = defineEmits<{
  (e: 'update:status', v: 'idle' | 'loading' | 'success' | 'error'): void;
  (e: 'update:result', v: string): void;
}>();

defineExpose({ reset });

const { t } = useI18n();
const { setDelay, clearAll } = useFixtureTimer();

const INITIAL = {
  id: 'item-001',
  name: 'Sample Item',
  owner: 'alice',
  status: 'active',
  lastUpdated: '2026-05-15',
  created: '2026-01-10',
  category: 'alpha',
  source: 'import',
};

const REFRESHED = {
  id: 'item-002',
  name: 'Refreshed Item',
  owner: 'bob',
  status: 'pending',
  lastUpdated: '2026-05-16',
  created: '2026-02-20',
  category: 'beta',
  source: 'manual',
};

const record = ref({ ...INITIAL });
const loading = ref(false);
const notFound = ref(false);
const hint = ref('');

function reset() {
  clearAll();
  record.value = { ...INITIAL };
  loading.value = false;
  notFound.value = false;
  hint.value = '';
  emit('update:status', 'idle');
  emit('update:result', '');
}

function onRefresh() {
  clearAll();
  hint.value = '';
  notFound.value = false;
  loading.value = true;
  emit('update:status', 'loading');
  emit('update:result', '');

  setDelay(500, () => {
    loading.value = false;
    record.value = { ...REFRESHED };
    emit('update:status', 'success');
    emit('update:result', t('runtimeFixtures.detail.refreshed'));
  });
}

function onLoadMissing() {
  clearAll();
  hint.value = '';
  loading.value = true;
  emit('update:status', 'loading');
  emit('update:result', '');

  setDelay(500, () => {
    loading.value = false;
    notFound.value = true;
    emit('update:status', 'error');
    emit('update:result', t('runtimeFixtures.detail.notFound'));
  });
}

function onCopyId() {
  hint.value = t('runtimeFixtures.detail.copyIdHint', { id: record.value.id });
}
</script>

<style scoped>
.fixture-inner {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.loading,
.not-found {
  padding: 12px;
  border-radius: 6px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 13px;
}

.not-found {
  background: #fef2f2;
  color: #b91c1c;
}

.detail-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.detail-header h3 {
  margin: 0;
  font-size: 16px;
}

.badge {
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  text-transform: lowercase;
}

.badge.active {
  background: #ecfdf5;
  color: #047857;
}

.badge.pending {
  background: #fef3c7;
  color: #92400e;
}

.badge.disabled {
  background: #f3f4f6;
  color: #4b5563;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  font-size: 13px;
  color: #374151;
}

.detail-grid div {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metadata {
  padding-top: 12px;
  border-top: 1px dashed #d1d5db;
}

.metadata h4 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #374151;
}

.action-row,
.distractor-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.hint-surface {
  padding: 10px 12px;
  border-radius: 6px;
  background: #eff6ff;
  color: #1e40af;
  font-size: 13px;
}
</style>
