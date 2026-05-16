<template>
  <div class="fixture-inner">
    <div class="form-card">
      <div class="field">
        <label>{{ t('runtimeFixtures.smsLogin.phone') }}</label>
        <input v-model="phone" type="tel" data-testid="basic-sms-phone" :disabled="submitting" />
      </div>
      <div class="action-row">
        <button
          class="btn btn-secondary"
          data-testid="basic-sms-request-code"
          :disabled="countdown > 0 || submitting"
          @click="onRequestCode"
        >
          {{ countdown > 0 ? t('runtimeFixtures.smsLogin.countdown', { n: countdown }) : t('runtimeFixtures.smsLogin.requestCode') }}
        </button>
        <span v-if="countdown > 0" class="countdown-status" data-testid="basic-sms-countdown">
          {{ t('runtimeFixtures.smsLogin.countdown', { n: countdown }) }}
        </span>
      </div>
      <div class="field">
        <label>{{ t('runtimeFixtures.smsLogin.code') }}</label>
        <input v-model="code" type="text" data-testid="basic-sms-code" :disabled="submitting" />
      </div>

      <div v-if="alert" class="alert error" data-testid="basic-sms-alert">
        {{ alert }}
      </div>

      <div v-if="successPanel" class="success-panel" data-testid="basic-sms-success-panel">
        <p>{{ t('runtimeFixtures.smsLogin.successMessage') }}</p>
        <p>{{ t('runtimeFixtures.smsLogin.maskedPhone', { phone: maskedPhone }) }}</p>
      </div>

      <button
        class="btn btn-primary"
        data-testid="basic-fixture-primary-trigger"
        :disabled="submitting"
        @click="onSubmit"
      >
        {{ submitting ? t('runtimeFixtures.smsLogin.submitting') : t('runtimeFixtures.smsLogin.submit') }}
      </button>
    </div>

    <div class="secondary-actions">
      <span data-testid="basic-fixture-secondary-trigger">
        <a href="#" data-testid="basic-sms-password-login" @click.prevent="onPasswordLogin">{{ t('runtimeFixtures.smsLogin.passwordLogin') }}</a>
      </span>
      <a href="#" data-testid="basic-sms-support" @click.prevent="onSupport">{{ t('runtimeFixtures.smsLogin.support') }}</a>
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
const { setDelay, setCountdown, clearAll } = useFixtureTimer();

const phone = ref('');
const code = ref('');
const countdown = ref(0);
const submitting = ref(false);
const alert = ref('');
const successPanel = ref(false);
const hint = ref('');

const maskedPhone = computed(() => {
  const p = phone.value.trim();
  if (p.length <= 4) return p;
  return p.slice(0, 3) + '****' + p.slice(-4);
});

function reset() {
  clearAll();
  phone.value = '';
  code.value = '';
  countdown.value = 0;
  submitting.value = false;
  alert.value = '';
  successPanel.value = false;
  hint.value = '';
  emit('update:status', 'idle');
  emit('update:result', '');
}

function isValidPhone(value: string) {
  return /^1[3-9]\d{9}$/.test(value.trim());
}

function onRequestCode() {
  clearAll();
  hint.value = '';
  alert.value = '';
  successPanel.value = false;

  if (!phone.value.trim()) {
    alert.value = t('runtimeFixtures.smsLogin.phoneRequired');
    emit('update:status', 'error');
    emit('update:result', alert.value);
    return;
  }

  if (!isValidPhone(phone.value)) {
    alert.value = t('runtimeFixtures.smsLogin.phoneInvalid');
    emit('update:status', 'error');
    emit('update:result', alert.value);
    return;
  }

  setCountdown(
    3,
    (n) => { countdown.value = n; },
    () => { countdown.value = 0; },
  );
}

function onSubmit() {
  hint.value = '';
  alert.value = '';
  successPanel.value = false;

  if (!phone.value.trim()) {
    alert.value = t('runtimeFixtures.smsLogin.phoneRequired');
    emit('update:status', 'error');
    emit('update:result', alert.value);
    return;
  }
  if (!isValidPhone(phone.value)) {
    alert.value = t('runtimeFixtures.smsLogin.phoneInvalid');
    emit('update:status', 'error');
    emit('update:result', alert.value);
    return;
  }
  if (!code.value.trim()) {
    alert.value = t('runtimeFixtures.smsLogin.codeRequired');
    emit('update:status', 'error');
    emit('update:result', alert.value);
    return;
  }
  if (code.value.trim() !== '123456') {
    alert.value = t('runtimeFixtures.smsLogin.codeInvalid');
    emit('update:status', 'error');
    emit('update:result', alert.value);
    return;
  }

  countdown.value = 0;
  submitting.value = true;
  emit('update:status', 'loading');
  emit('update:result', '');

  setDelay(500, () => {
    submitting.value = false;
    successPanel.value = true;
    emit('update:status', 'success');
    emit('update:result', t('runtimeFixtures.smsLogin.successMessage'));
  });
}

function onPasswordLogin() {
  hint.value = t('runtimeFixtures.smsLogin.passwordLoginHint');
}

function onSupport() {
  hint.value = t('runtimeFixtures.smsLogin.supportHint');
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

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.field input[type='tel'],
.field input[type='text'] {
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.countdown-status {
  font-size: 13px;
  color: #6b7280;
}

.alert {
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
}

.alert.error {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}

.success-panel {
  padding: 14px;
  border-radius: 6px;
  background: #ecfdf5;
  color: #065f46;
  border: 1px solid #a7f3d0;
  font-size: 13px;
}

.success-panel p {
  margin: 0 0 6px;
}

.secondary-actions {
  display: flex;
  gap: 16px;
  font-size: 13px;
}

.secondary-actions a {
  color: #2563eb;
  text-decoration: none;
}

.secondary-actions a:hover {
  text-decoration: underline;
}

.hint-surface {
  padding: 10px 12px;
  border-radius: 6px;
  background: #eff6ff;
  color: #1e40af;
  font-size: 13px;
}
</style>
