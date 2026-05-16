<template>
  <main class="basic-fixture-page" :data-testid="`fixture-${fixtureId}`">
    <header class="fixture-header">
      <router-link
        class="back-link"
        to="/runtime-observation/basic"
        data-testid="basic-fixture-back"
      >
        {{ t('runtimeFixtures.back') }}
      </router-link>
      <h1 data-testid="basic-fixture-heading">{{ heading }}</h1>
    </header>

    <!-- Login -->
    <section v-if="fixtureId === 'basic-login'" class="fixture-body">
      <div class="field">
        <label>{{ t('runtimeFixtures.login.username') }}</label>
        <input v-model="login.username" type="text" data-testid="basic-fixture-input-username" />
      </div>
      <div class="field">
        <label>{{ t('runtimeFixtures.login.password') }}</label>
        <input v-model="login.password" type="password" data-testid="basic-fixture-input-password" />
      </div>
      <button
        class="btn btn-primary"
        data-testid="basic-fixture-trigger"
        :disabled="login.submitting"
        @click="onLoginSubmit"
      >
        {{ login.submitting ? t('runtimeFixtures.login.submitting') : t('runtimeFixtures.login.submit') }}
      </button>
    </section>

    <!-- Register -->
    <section v-if="fixtureId === 'basic-register'" class="fixture-body">
      <div class="field">
        <label>{{ t('runtimeFixtures.register.username') }}</label>
        <input v-model="register.username" type="text" data-testid="basic-fixture-input-username" />
      </div>
      <div class="field">
        <label>{{ t('runtimeFixtures.register.email') }}</label>
        <input v-model="register.email" type="email" data-testid="basic-fixture-input-email" />
      </div>
      <div class="field">
        <label>{{ t('runtimeFixtures.register.password') }}</label>
        <input v-model="register.password" type="password" data-testid="basic-fixture-input-password" />
      </div>
      <button
        class="btn btn-primary"
        data-testid="basic-fixture-trigger"
        :disabled="register.submitting"
        @click="onRegisterSubmit"
      >
        {{ register.submitting ? t('runtimeFixtures.register.submitting') : t('runtimeFixtures.register.submit') }}
      </button>
    </section>

    <!-- SMS Login -->
    <section v-if="fixtureId === 'basic-sms-login'" class="fixture-body">
      <div class="field">
        <label>{{ t('runtimeFixtures.smsLogin.phone') }}</label>
        <input v-model="smsLogin.phone" type="tel" data-testid="basic-fixture-input-phone" />
      </div>
      <div class="field">
        <label>{{ t('runtimeFixtures.smsLogin.code') }}</label>
        <input v-model="smsLogin.code" type="text" data-testid="basic-fixture-input-code" />
      </div>
      <div class="action-row">
        <button
          class="btn btn-secondary"
          data-testid="basic-fixture-trigger-secondary"
          :disabled="smsLogin.countdown > 0 || smsLogin.submitting"
          @click="onRequestCode"
        >
          {{ smsLogin.countdown > 0 ? t('runtimeFixtures.smsLogin.countdown', { n: smsLogin.countdown }) : t('runtimeFixtures.smsLogin.requestCode') }}
        </button>
        <button
          class="btn btn-primary"
          data-testid="basic-fixture-trigger"
          :disabled="smsLogin.submitting"
          @click="onSmsLoginSubmit"
        >
          {{ smsLogin.submitting ? t('runtimeFixtures.smsLogin.submitting') : t('runtimeFixtures.smsLogin.submit') }}
        </button>
      </div>
    </section>

    <!-- Search -->
    <section v-if="fixtureId === 'basic-search'" class="fixture-body">
      <div class="field inline">
        <input v-model="search.query" type="text" data-testid="basic-fixture-input-query" />
        <button
          class="btn btn-primary"
          data-testid="basic-fixture-trigger"
          :disabled="search.loading"
          @click="onSearch"
        >
          {{ t('runtimeFixtures.search.submit') }}
        </button>
      </div>
      <div v-if="search.loading" class="loading" data-testid="basic-fixture-loading">{{ t('runtimeFixtures.search.loading') }}</div>
      <ul v-else-if="search.results.length" class="result-list" data-testid="basic-fixture-list">
        <li v-for="(item, idx) in search.results" :key="idx">{{ item }}</li>
      </ul>
      <div v-else-if="search.searched" class="empty" data-testid="basic-fixture-empty">
        {{ t('runtimeFixtures.search.emptyResult') }}
      </div>
    </section>

    <!-- Detail -->
    <section v-if="fixtureId === 'basic-detail'" class="fixture-body">
      <div v-if="detail.loading" class="loading" data-testid="basic-fixture-loading">{{ t('runtimeFixtures.detail.loading') }}</div>
      <div v-else-if="detail.notFound" class="empty" data-testid="basic-fixture-empty">
        {{ t('runtimeFixtures.detail.notFound') }}
      </div>
      <div v-else class="detail-card" data-testid="basic-fixture-detail-card">
        <p>{{ t('runtimeFixtures.detail.description') }}</p>
        <p><strong>ID:</strong> {{ detail.id }}</p>
        <p><strong>Name:</strong> {{ detail.name }}</p>
      </div>
      <div class="action-row">
        <button
          class="btn btn-primary"
          data-testid="basic-fixture-trigger"
          :disabled="detail.loading"
          @click="onDetailRefresh"
        >
          {{ t('runtimeFixtures.detail.refresh') }}
        </button>
        <button
          class="btn btn-secondary"
          data-testid="basic-fixture-trigger-secondary"
          :disabled="detail.loading"
          @click="onDetailLoadMissing"
        >
          {{ t('runtimeFixtures.detail.loadMissing') }}
        </button>
      </div>
    </section>

    <!-- Settings -->
    <section v-if="fixtureId === 'basic-settings'" class="fixture-body">
      <label class="toggle-row">
        <input v-model="settings.enabled" type="checkbox" data-testid="basic-fixture-toggle" />
        <span>{{ t('runtimeFixtures.settings.enableNotifications') }}</span>
      </label>
      <button
        class="btn btn-primary"
        data-testid="basic-fixture-trigger"
        :disabled="settings.saving"
        @click="onSettingsSave"
      >
        {{ settings.saving ? t('runtimeFixtures.settings.saving') : t('runtimeFixtures.settings.save') }}
      </button>
    </section>

    <!-- Confirm -->
    <section v-if="fixtureId === 'basic-confirm'" class="fixture-body">
      <p>{{ t('runtimeFixtures.confirm.description') }}</p>
      <button
        class="btn btn-primary"
        data-testid="basic-fixture-trigger"
        @click="onOpenConfirm"
      >
        {{ t('runtimeFixtures.confirm.openConfirm') }}
      </button>

      <div v-if="confirm.show" class="confirm-surface" data-testid="basic-fixture-confirm-surface">
        <p>{{ t('runtimeFixtures.confirm.description') }}</p>
        <div class="action-row">
          <button class="btn btn-secondary" data-testid="basic-fixture-trigger-cancel" @click="onCancelConfirm">
            {{ t('runtimeFixtures.confirm.cancel') }}
          </button>
          <button class="btn btn-primary" data-testid="basic-fixture-trigger-primary" @click="onConfirmAction">
            {{ t('runtimeFixtures.confirm.confirm') }}
          </button>
        </div>
      </div>
    </section>

    <!-- Shared result/status region -->
    <section class="shared-footer">
      <div
        class="result-region"
        data-testid="basic-fixture-result"
        :class="{ visible: resultVisible }"
      >
        {{ resultText }}
      </div>
      <div class="status-row">
        <span class="status-label" data-testid="basic-fixture-status">{{ statusLabel }}</span>
        <button class="btn btn-secondary" data-testid="basic-fixture-reset" @click="reset">
          {{ t('runtimeFixtures.reset') }}
        </button>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';

const props = defineProps<{ fixtureId: string }>();
const { t } = useI18n();

// ---- Shared state ----
const status = ref<'idle' | 'loading' | 'success' | 'error'>('idle');
const resultText = ref('');
let timer: ReturnType<typeof setTimeout> | null = null;
let interval: ReturnType<typeof setInterval> | null = null;

function clearTimers() {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
  if (interval) {
    clearInterval(interval);
    interval = null;
  }
}

onUnmounted(clearTimers);

const heading = computed(() => {
  switch (props.fixtureId) {
    case 'basic-login':
      return t('runtimeFixtures.login.heading');
    case 'basic-register':
      return t('runtimeFixtures.register.heading');
    case 'basic-sms-login':
      return t('runtimeFixtures.smsLogin.heading');
    case 'basic-search':
      return t('runtimeFixtures.search.heading');
    case 'basic-detail':
      return t('runtimeFixtures.detail.heading');
    case 'basic-settings':
      return t('runtimeFixtures.settings.heading');
    case 'basic-confirm':
      return t('runtimeFixtures.confirm.heading');
    default:
      return props.fixtureId;
  }
});

const statusLabel = computed(() => {
  switch (status.value) {
    case 'idle':
      return t('runtimeFixtures.status.idle');
    case 'loading':
      return t('runtimeFixtures.status.loading');
    case 'success':
      return t('runtimeFixtures.status.success');
    case 'error':
      return t('runtimeFixtures.status.error');
    default:
      return status.value;
  }
});

const resultVisible = computed(() => resultText.value !== '');

function reset() {
  clearTimers();
  status.value = 'idle';
  resultText.value = '';

  // login
  login.value.username = '';
  login.value.password = '';
  login.value.submitting = false;

  // register
  register.value.username = '';
  register.value.email = '';
  register.value.password = '';
  register.value.submitting = false;

  // sms-login
  smsLogin.value.phone = '';
  smsLogin.value.code = '';
  smsLogin.value.countdown = 0;
  smsLogin.value.submitting = false;

  // search
  search.value.query = '';
  search.value.results = [];
  search.value.searched = false;
  search.value.loading = false;

  // detail
  detail.value.loading = false;
  detail.value.notFound = false;
  detail.value.id = 'item-001';
  detail.value.name = 'Sample Item';

  // settings
  settings.value.enabled = false;
  settings.value.saving = false;

  // confirm
  confirm.value.show = false;
}

// ---- Login ----
const login = ref({
  username: '',
  password: '',
  submitting: false,
});

function onLoginSubmit() {
  clearTimers();
  if (!login.value.username.trim() || !login.value.password.trim()) {
    status.value = 'error';
    resultText.value = t('runtimeFixtures.login.validationError');
    return;
  }
  login.value.submitting = true;
  status.value = 'loading';
  resultText.value = '';
  timer = setTimeout(() => {
    login.value.submitting = false;
    status.value = 'success';
    resultText.value = t('runtimeFixtures.login.successMessage');
    timer = null;
  }, 500);
}

// ---- Register ----
const register = ref({
  username: '',
  email: '',
  password: '',
  submitting: false,
});

function onRegisterSubmit() {
  clearTimers();
  const emailValid = /^\S+@\S+\.\S+$/.test(register.value.email);
  if (!register.value.username.trim() || !emailValid || !register.value.password.trim()) {
    status.value = 'error';
    resultText.value = t('runtimeFixtures.register.validationError');
    return;
  }
  register.value.submitting = true;
  status.value = 'loading';
  resultText.value = '';
  timer = setTimeout(() => {
    register.value.submitting = false;
    status.value = 'success';
    resultText.value = t('runtimeFixtures.register.successMessage');
    timer = null;
  }, 500);
}

// ---- SMS Login ----
const smsLogin = ref({
  phone: '',
  code: '',
  countdown: 0,
  submitting: false,
});

function onRequestCode() {
  clearTimers();
  if (!smsLogin.value.phone.trim()) {
    status.value = 'error';
    resultText.value = t('runtimeFixtures.smsLogin.validationError');
    return;
  }
  smsLogin.value.countdown = 3;
  status.value = 'loading';
  resultText.value = '';
  interval = setInterval(() => {
    smsLogin.value.countdown -= 1;
    if (smsLogin.value.countdown <= 0) {
      if (interval) clearInterval(interval);
      interval = null;
      status.value = 'idle';
    }
  }, 1000);
}

function onSmsLoginSubmit() {
  clearTimers();
  if (!smsLogin.value.phone.trim() || !smsLogin.value.code.trim()) {
    status.value = 'error';
    resultText.value = t('runtimeFixtures.smsLogin.validationError');
    return;
  }
  smsLogin.value.submitting = true;
  status.value = 'loading';
  resultText.value = '';
  timer = setTimeout(() => {
    smsLogin.value.submitting = false;
    status.value = 'success';
    resultText.value = t('runtimeFixtures.smsLogin.successMessage');
    timer = null;
  }, 500);
}

// ---- Search ----
const search = ref({
  query: '',
  results: [] as string[],
  searched: false,
  loading: false,
});

function onSearch() {
  clearTimers();
  search.value.loading = true;
  search.value.searched = true;
  search.value.results = [];
  status.value = 'loading';
  resultText.value = '';
  timer = setTimeout(() => {
    search.value.loading = false;
    if (search.value.query.trim().toLowerCase() === 'empty') {
      search.value.results = [];
      status.value = 'idle';
      resultText.value = '';
    } else {
      search.value.results = [
        `${t('runtimeFixtures.search.resultPrefix')} "${search.value.query || t('runtimeFixtures.search.defaultQuery')}"`,
        'Result A',
        'Result B',
      ];
      status.value = 'success';
      resultText.value = `${search.value.results.length} ${t('runtimeFixtures.search.resultCountSuffix')}`;
    }
    timer = null;
  }, 500);
}

// ---- Detail ----
const detail = ref({
  loading: false,
  notFound: false,
  id: 'item-001',
  name: 'Sample Item',
});

function onDetailRefresh() {
  clearTimers();
  detail.value.loading = true;
  detail.value.notFound = false;
  status.value = 'loading';
  resultText.value = '';
  timer = setTimeout(() => {
    detail.value.loading = false;
    detail.value.notFound = false;
    detail.value.id = 'item-002';
    detail.value.name = 'Refreshed Item';
    status.value = 'success';
    resultText.value = t('runtimeFixtures.detail.refreshed');
    timer = null;
  }, 500);
}

function onDetailLoadMissing() {
  clearTimers();
  detail.value.loading = true;
  detail.value.notFound = false;
  status.value = 'loading';
  resultText.value = '';
  timer = setTimeout(() => {
    detail.value.loading = false;
    detail.value.notFound = true;
    status.value = 'error';
    resultText.value = t('runtimeFixtures.detail.notFound');
    timer = null;
  }, 500);
}

// ---- Settings ----
const settings = ref({
  enabled: false,
  saving: false,
});

function onSettingsSave() {
  clearTimers();
  settings.value.saving = true;
  status.value = 'loading';
  resultText.value = '';
  timer = setTimeout(() => {
    settings.value.saving = false;
    status.value = 'success';
    resultText.value = t('runtimeFixtures.settings.saved');
    timer = null;
  }, 500);
}

// ---- Confirm ----
const confirm = ref({
  show: false,
});

function onOpenConfirm() {
  clearTimers();
  confirm.value.show = true;
  status.value = 'idle';
  resultText.value = '';
}

function onCancelConfirm() {
  confirm.value.show = false;
  status.value = 'idle';
  resultText.value = '';
}

function onConfirmAction() {
  confirm.value.show = false;
  status.value = 'success';
  resultText.value = t('runtimeFixtures.confirm.confirmed');
}

watch(
  () => props.fixtureId,
  () => {
    reset();
  },
);
</script>

<style scoped>
.basic-fixture-page {
  min-height: 100vh;
  padding: 40px 24px 64px;
  background: #f5f7fa;
  color: #1f2937;
  max-width: 720px;
  margin: 0 auto;
}

.fixture-header {
  margin-bottom: 24px;
}

.back-link {
  display: inline-flex;
  margin-bottom: 12px;
  color: #2563eb;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

.fixture-header h1 {
  margin: 0;
  font-size: 24px;
}

.fixture-body {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field.inline {
  flex-direction: row;
  align-items: center;
  gap: 10px;
}

.field label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.field input[type='text'],
.field input[type='password'],
.field input[type='email'],
.field input[type='tel'] {
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  min-width: 240px;
}

.btn {
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  align-self: flex-start;
}

.btn-primary {
  background: #2563eb;
  color: #fff;
}

.btn-primary:hover {
  background: #1d4ed8;
}

.btn-primary:disabled {
  background: #93c5fd;
  cursor: not-allowed;
}

.btn-secondary {
  background: #fff;
  color: #2563eb;
  border-color: #bfdbfe;
}

.btn-secondary:hover {
  border-color: #2563eb;
  background: #eff6ff;
}

.btn-secondary:disabled {
  color: #9ca3af;
  border-color: #e5e7eb;
  background: #f9fafb;
  cursor: not-allowed;
}

.action-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.loading,
.empty {
  padding: 12px;
  border-radius: 6px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 13px;
}

.result-list {
  margin: 0;
  padding-left: 18px;
  color: #374151;
  font-size: 13px;
}

.result-list li {
  margin-bottom: 6px;
}

.detail-card p {
  margin: 0 0 8px;
  font-size: 14px;
  color: #374151;
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
  cursor: pointer;
}

.confirm-surface {
  margin-top: 12px;
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

.shared-footer {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.result-region {
  min-height: 22px;
  font-size: 13px;
  color: #374151;
}

.result-region.visible {
  font-weight: 600;
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.status-label {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  color: #6b7280;
}
</style>
