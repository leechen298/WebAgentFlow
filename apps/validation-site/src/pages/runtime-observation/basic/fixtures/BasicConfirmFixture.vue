<template>
  <div class="fixture-inner">
    <div class="summary-card" data-testid="basic-confirm-summary">
      <h3>{{ t('runtimeFixtures.confirm.actionTitle') }}</h3>
      <p>{{ t('runtimeFixtures.confirm.actionDescription') }}</p>
      <div class="summary-meta">
        <div><strong>{{ t('runtimeFixtures.confirm.object') }}</strong> {{ objectName }}</div>
        <div><strong>{{ t('runtimeFixtures.confirm.risk') }}</strong> {{ riskLevel }}</div>
      </div>
    </div>

    <div class="action-row">
      <button
        class="btn btn-primary"
        data-testid="basic-fixture-primary-trigger"
        :disabled="pending || success"
        @click="onOpenConfirm"
      >
        {{ t('runtimeFixtures.confirm.primaryAction') }}
      </button>
      <button
        class="btn btn-secondary"
        data-testid="basic-fixture-secondary-trigger"
        @click="onViewDetails"
      >
        {{ t('runtimeFixtures.confirm.viewDetails') }}
      </button>
    </div>

    <div v-if="confirmSurface" class="confirm-surface" data-testid="basic-confirm-surface">
      <p>{{ t('runtimeFixtures.confirm.confirmMessage') }}</p>
      <div class="action-row">
        <button
          class="btn btn-secondary"
          data-testid="basic-confirm-cancel"
          :disabled="pending"
          @click="onCancel"
        >
          {{ t('runtimeFixtures.confirm.cancel') }}
        </button>
        <button
          class="btn btn-primary"
          data-testid="basic-confirm-confirm"
          :disabled="pending"
          @click="onConfirm"
        >
          {{ pending ? t('runtimeFixtures.confirm.pending') : t('runtimeFixtures.confirm.confirm') }}
        </button>
      </div>
    </div>

    <div v-if="pending" class="pending-panel" data-testid="basic-confirm-pending">
      {{ t('runtimeFixtures.confirm.pendingMessage') }}
    </div>

    <div v-if="success" class="success-panel" data-testid="basic-confirm-success">
      {{ t('runtimeFixtures.confirm.confirmed') }}
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

const objectName = ref('Report Q2-2026');
const riskLevel = ref('medium');
const confirmSurface = ref(false);
const pending = ref(false);
const success = ref(false);
const hint = ref('');

function reset() {
  clearAll();
  confirmSurface.value = false;
  pending.value = false;
  success.value = false;
  hint.value = '';
  emit('update:status', 'idle');
  emit('update:result', '');
}

function onOpenConfirm() {
  clearAll();
  hint.value = '';
  confirmSurface.value = true;
  pending.value = false;
  success.value = false;
  emit('update:status', 'idle');
  emit('update:result', '');
}

function onCancel() {
  clearAll();
  confirmSurface.value = false;
  pending.value = false;
  success.value = false;
  emit('update:status', 'idle');
  emit('update:result', t('runtimeFixtures.confirm.cancelled'));
}

function onConfirm() {
  clearAll();
  confirmSurface.value = false;
  pending.value = true;
  success.value = false;
  emit('update:status', 'loading');
  emit('update:result', '');

  setDelay(500, () => {
    pending.value = false;
    success.value = true;
    emit('update:status', 'success');
    emit('update:result', t('runtimeFixtures.confirm.confirmed'));
  });
}

function onViewDetails() {
  hint.value = t('runtimeFixtures.confirm.detailsHint');
}
</script>

<style scoped>
.fixture-inner {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-card {
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f9fafb;
}

.summary-card h3 {
  margin: 0 0 8px;
  font-size: 15px;
}

.summary-card p {
  margin: 0 0 10px;
  font-size: 13px;
  color: #4b5563;
}

.summary-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #374151;
}

.action-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.confirm-surface {
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.confirm-surface p {
  margin: 0 0 12px;
  font-size: 14px;
  color: #374151;
}

.pending-panel {
  padding: 12px;
  border-radius: 6px;
  background: #eff6ff;
  color: #1e40af;
  font-size: 13px;
}

.success-panel {
  padding: 12px;
  border-radius: 6px;
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
  font-size: 13px;
}

.hint-surface {
  padding: 10px 12px;
  border-radius: 6px;
  background: #eff6ff;
  color: #1e40af;
  font-size: 13px;
}
</style>
