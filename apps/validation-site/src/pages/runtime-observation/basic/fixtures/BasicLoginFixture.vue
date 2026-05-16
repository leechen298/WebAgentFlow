<template>
  <div class="fixture-inner">
    <div class="brand" data-testid="basic-login-brand">WebAgentFlow Business Portal</div>

    <div class="form-card">
      <div class="field">
        <label>{{ t('runtimeFixtures.login.username') }}</label>
        <input
          v-model="username"
          type="text"
          data-testid="basic-login-username"
          :disabled="submitting"
        />
      </div>
      <div class="field">
        <label>{{ t('runtimeFixtures.login.password') }}</label>
        <input
          v-model="password"
          type="password"
          data-testid="basic-login-password"
          :disabled="submitting"
        />
      </div>
      <label class="checkbox-row">
        <input v-model="rememberMe" type="checkbox" data-testid="basic-login-remember-me" />
        <span>{{ t('runtimeFixtures.login.rememberMe') }}</span>
      </label>

      <div v-if="alert" class="alert" data-testid="basic-login-alert" :class="alert.type">
        {{ alert.message }}
      </div>

      <div v-if="successPanel" class="success-panel" data-testid="basic-login-success-panel">
        <p><strong>{{ t('runtimeFixtures.login.signedInAs') }}</strong> {{ username }}</p>
        <p v-if="rememberMe">{{ t('runtimeFixtures.login.rememberMeOn') }}</p>
        <p>{{ t('runtimeFixtures.login.sessionReady') }}</p>
      </div>

      <button
        class="btn btn-primary"
        data-testid="basic-fixture-primary-trigger"
        :disabled="submitting"
        @click="onSubmit"
      >
        {{ submitting ? t('runtimeFixtures.login.submitting') : t('runtimeFixtures.login.submit') }}
      </button>
    </div>

    <div class="secondary-actions">
      <span data-testid="basic-fixture-secondary-trigger">
        <a href="#" data-testid="basic-login-forgot-password" @click.prevent="onForgot">
          {{ t('runtimeFixtures.login.forgotPassword') }}
        </a>
      </span>
      <a href="#" data-testid="basic-login-contact-admin" @click.prevent="onContact">
        {{ t('runtimeFixtures.login.contactAdmin') }}
      </a>
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

const username = ref('');
const password = ref('');
const rememberMe = ref(false);
const submitting = ref(false);
const alert = ref<{ type: 'error'; message: string } | null>(null);
const successPanel = ref(false);
const hint = ref('');

function reset() {
  clearAll();
  username.value = '';
  password.value = '';
  rememberMe.value = false;
  submitting.value = false;
  alert.value = null;
  successPanel.value = false;
  hint.value = '';
  emit('update:status', 'idle');
  emit('update:result', '');
}

function onSubmit() {
  clearAll();
  hint.value = '';
  alert.value = null;
  successPanel.value = false;

  if (!username.value.trim() || !password.value.trim()) {
    alert.value = { type: 'error', message: t('runtimeFixtures.login.requiredError') };
    emit('update:status', 'error');
    emit('update:result', t('runtimeFixtures.login.requiredError'));
    return;
  }

  if (username.value.trim() !== 'demo.operator' || password.value.trim() !== 'correct-password') {
    alert.value = { type: 'error', message: t('runtimeFixtures.login.invalidCredentials') };
    emit('update:status', 'error');
    emit('update:result', t('runtimeFixtures.login.invalidCredentials'));
    return;
  }

  submitting.value = true;
  emit('update:status', 'loading');
  emit('update:result', '');

  setDelay(500, () => {
    submitting.value = false;
    successPanel.value = true;
    emit('update:status', 'success');
    emit('update:result', t('runtimeFixtures.login.successMessage'));
  });
}

function onForgot() {
  hint.value = t('runtimeFixtures.login.forgotHint');
}

function onContact() {
  hint.value = t('runtimeFixtures.login.contactHint');
}
</script>

<style scoped>
.fixture-inner {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.brand {
  font-size: 18px;
  font-weight: 700;
  color: #1e3a8a;
  margin-bottom: 4px;
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

.field input[type='text'],
.field input[type='password'] {
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}

.checkbox-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
}

.checkbox-row input[type='checkbox'] {
  width: 16px;
  height: 16px;
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
