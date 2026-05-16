<template>
  <div class="fixture-inner">
    <div class="form-card">
      <div class="control-row">
        <label class="toggle-row">
          <input v-model="notifications" type="checkbox" data-testid="basic-settings-notifications" />
          <span>{{ t('runtimeFixtures.settings.enableNotifications') }}</span>
        </label>
        <span v-if="dirty" class="dirty-badge" data-testid="basic-settings-dirty-state">{{ t('runtimeFixtures.settings.dirty') }}</span>
      </div>

      <div class="control-row">
        <label>{{ t('runtimeFixtures.settings.digestFrequency') }}</label>
        <div class="radio-row" data-testid="basic-settings-frequency">
          <label>
            <input v-model="frequency" type="radio" value="daily" data-testid="basic-settings-frequency-daily" />
            {{ t('runtimeFixtures.settings.daily') }}
          </label>
          <label>
            <input v-model="frequency" type="radio" value="weekly" data-testid="basic-settings-frequency-weekly" />
            {{ t('runtimeFixtures.settings.weekly') }}
          </label>
          <label>
            <input v-model="frequency" type="radio" value="never" data-testid="basic-settings-frequency-never" />
            {{ t('runtimeFixtures.settings.never') }}
          </label>
        </div>
      </div>

      <div class="control-row">
        <label class="toggle-row">
          <input v-model="quietHours" type="checkbox" data-testid="basic-settings-quiet-hours" />
          <span>{{ t('runtimeFixtures.settings.quietHours') }}</span>
        </label>
      </div>

      <div v-if="warning" class="alert warning" data-testid="basic-settings-warning">
        {{ warning }}
      </div>

      <div v-if="saved" class="success-panel" data-testid="basic-settings-saved">
        {{ t('runtimeFixtures.settings.saved') }}
      </div>

      <div class="action-row">
        <button
          class="btn btn-primary"
          data-testid="basic-fixture-primary-trigger"
          :disabled="!dirty || saving"
          @click="onSave"
        >
          {{ saving ? t('runtimeFixtures.settings.saving') : t('runtimeFixtures.settings.save') }}
        </button>
      </div>
    </div>

    <div class="distractor-row" data-testid="basic-fixture-secondary-trigger">
      <button class="btn btn-secondary" data-testid="basic-settings-preview" @click="onPreview">
        {{ t('runtimeFixtures.settings.preview') }}
      </button>
    </div>

    <div v-if="hint" class="hint-surface">{{ hint }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useFixtureTimer } from '../useFixtureTimer';

const emit = defineEmits<{
  (e: 'update:status', v: 'idle' | 'loading' | 'success' | 'error'): void;
  (e: 'update:result', v: string): void;
}>();

defineExpose({ reset });

const { t } = useI18n();
const { setDelay, clearAll } = useFixtureTimer();

const notifications = ref(true);
const frequency = ref('daily');
const quietHours = ref(false);
const saving = ref(false);
const saved = ref(false);
const hint = ref('');

const INITIAL_VALUES = { notifications: true, frequency: 'daily', quietHours: false };
const savedBaseline = ref({ ...INITIAL_VALUES });

const dirty = computed(() => {
  return notifications.value !== savedBaseline.value.notifications
    || frequency.value !== savedBaseline.value.frequency
    || quietHours.value !== savedBaseline.value.quietHours;
});

const warning = computed(() => {
  if (!notifications.value && frequency.value === 'daily') {
    return t('runtimeFixtures.settings.warningNotificationsOff');
  }
  if (quietHours.value && !notifications.value) {
    return t('runtimeFixtures.settings.warningQuietHours');
  }
  return '';
});

function reset() {
  clearAll();
  notifications.value = INITIAL_VALUES.notifications;
  frequency.value = INITIAL_VALUES.frequency;
  quietHours.value = INITIAL_VALUES.quietHours;
  savedBaseline.value = { ...INITIAL_VALUES };
  saving.value = false;
  saved.value = false;
  hint.value = '';
  emit('update:status', 'idle');
  emit('update:result', '');
}

function onSave() {
  clearAll();
  hint.value = '';
  saved.value = false;
  saving.value = true;
  emit('update:status', 'loading');
  emit('update:result', '');

  setDelay(500, () => {
    saving.value = false;
    saved.value = true;
    savedBaseline.value = {
      notifications: notifications.value,
      frequency: frequency.value,
      quietHours: quietHours.value,
    };
    emit('update:status', 'success');
    emit('update:result', t('runtimeFixtures.settings.saved'));
  });
}

function onPreview() {
  hint.value = t('runtimeFixtures.settings.previewHint');
}
</script>

<style scoped>
.fixture-inner {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.control-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toggle-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: #374151;
  cursor: pointer;
}

.toggle-row input[type='checkbox'] {
  width: 18px;
  height: 18px;
}

.radio-row {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #374151;
}

.radio-row label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.dirty-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  background: #fef3c7;
  color: #92400e;
  text-transform: uppercase;
}

.alert {
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
}

.alert.warning {
  background: #fffbeb;
  color: #b45309;
  border: 1px solid #fcd34d;
}

.success-panel {
  padding: 10px 12px;
  border-radius: 6px;
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
  font-size: 13px;
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
