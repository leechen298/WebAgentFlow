<template>
  <div class="fixture-inner">
    <div class="form-card">
      <div class="field">
        <label>{{ t('runtimeFixtures.register.username') }}</label>
        <input v-model="username" type="text" data-testid="basic-register-username" :disabled="submitting" />
      </div>
      <div class="field">
        <label>{{ t('runtimeFixtures.register.email') }}</label>
        <input v-model="email" type="email" data-testid="basic-register-email" :disabled="submitting" />
      </div>
      <div class="field">
        <label>{{ t('runtimeFixtures.register.password') }}</label>
        <input v-model="password" type="password" data-testid="basic-register-password" :disabled="submitting" />
      </div>
      <div class="field">
        <label>{{ t('runtimeFixtures.register.confirmPassword') }}</label>
        <input v-model="confirmPassword" type="password" data-testid="basic-register-confirm-password" :disabled="submitting" />
      </div>
      <label class="checkbox-row">
        <input v-model="terms" type="checkbox" data-testid="basic-register-terms" />
        <span>{{ t('runtimeFixtures.register.termsLabel') }}</span>
      </label>

      <div v-if="alert" class="alert error" data-testid="basic-register-alert">
        {{ alert }}
      </div>

      <div v-if="successPanel" class="success-panel" data-testid="basic-register-success-panel">
        <p><strong>{{ t('runtimeFixtures.register.accountCreated') }}</strong></p>
        <p>{{ t('runtimeFixtures.register.username') }}: {{ username }}</p>
        <p>{{ t('runtimeFixtures.register.email') }}: {{ email }}</p>
      </div>

      <button
        class="btn btn-primary"
        data-testid="basic-fixture-primary-trigger"
        :disabled="submitting"
        @click="onSubmit"
      >
        {{ submitting ? t('runtimeFixtures.register.submitting') : t('runtimeFixtures.register.submit') }}
      </button>
    </div>

    <div class="secondary-actions">
      <span data-testid="basic-fixture-secondary-trigger">
        <a href="#" data-testid="basic-register-sign-in" @click.prevent="onSignIn">{{ t('runtimeFixtures.register.signIn') }}</a>
      </span>
      <a href="#" data-testid="basic-register-terms-link" @click.prevent="onTerms">{{ t('runtimeFixtures.register.viewTerms') }}</a>
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
const email = ref('');
const password = ref('');
const confirmPassword = ref('');
const terms = ref(false);
const submitting = ref(false);
const alert = ref('');
const successPanel = ref(false);
const hint = ref('');

function reset() {
  clearAll();
  username.value = '';
  email.value = '';
  password.value = '';
  confirmPassword.value = '';
  terms.value = false;
  submitting.value = false;
  alert.value = '';
  successPanel.value = false;
  hint.value = '';
  emit('update:status', 'idle');
  emit('update:result', '');
}

function onSubmit() {
  clearAll();
  hint.value = '';
  alert.value = '';
  successPanel.value = false;

  if (!username.value.trim() || !email.value.trim() || !password.value.trim() || !confirmPassword.value.trim()) {
    alert.value = t('runtimeFixtures.register.requiredError');
    emit('update:status', 'error');
    emit('update:result', alert.value);
    return;
  }

  const emailValid = /^\S+@\S+\.\S+$/.test(email.value);
  if (!emailValid) {
    alert.value = t('runtimeFixtures.register.emailError');
    emit('update:status', 'error');
    emit('update:result', alert.value);
    return;
  }

  if (password.value !== confirmPassword.value) {
    alert.value = t('runtimeFixtures.register.mismatchError');
    emit('update:status', 'error');
    emit('update:result', alert.value);
    return;
  }

  if (!terms.value) {
    alert.value = t('runtimeFixtures.register.termsError');
    emit('update:status', 'error');
    emit('update:result', alert.value);
    return;
  }

  if (username.value.trim() === 'taken-user') {
    alert.value = t('runtimeFixtures.register.takenError');
    emit('update:status', 'error');
    emit('update:result', alert.value);
    return;
  }

  submitting.value = true;
  emit('update:status', 'loading');
  emit('update:result', '');

  setDelay(500, () => {
    submitting.value = false;
    successPanel.value = true;
    emit('update:status', 'success');
    emit('update:result', t('runtimeFixtures.register.successMessage'));
  });
}

function onSignIn() {
  hint.value = t('runtimeFixtures.register.signInHint');
}

function onTerms() {
  hint.value = t('runtimeFixtures.register.termsHint');
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

.field input[type='text'],
.field input[type='email'],
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
