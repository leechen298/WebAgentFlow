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

    <section class="fixture-body">
      <component
        :is="fixtureComponent"
        v-if="fixtureComponent"
        :key="fixtureId"
        ref="fixtureRef"
        @update:status="status = $event"
        @update:result="resultText = $event"
      />
      <div v-else class="empty">Unknown fixture: {{ fixtureId }}</div>
    </section>

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
        <button class="btn btn-secondary" data-testid="basic-fixture-reset" @click="onReset">
          {{ t('runtimeFixtures.reset') }}
        </button>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import BasicLoginFixture from './fixtures/BasicLoginFixture.vue';
import BasicRegisterFixture from './fixtures/BasicRegisterFixture.vue';
import BasicSmsLoginFixture from './fixtures/BasicSmsLoginFixture.vue';
import BasicSearchFixture from './fixtures/BasicSearchFixture.vue';
import BasicDetailFixture from './fixtures/BasicDetailFixture.vue';
import BasicSettingsFixture from './fixtures/BasicSettingsFixture.vue';
import BasicConfirmFixture from './fixtures/BasicConfirmFixture.vue';

const props = defineProps<{ fixtureId: string }>();
const { t } = useI18n();

const fixtureRef = ref();
const status = ref<'idle' | 'loading' | 'success' | 'error'>('idle');
const resultText = ref('');

const fixtureComponent = computed(() => {
  switch (props.fixtureId) {
    case 'basic-login':
      return BasicLoginFixture;
    case 'basic-register':
      return BasicRegisterFixture;
    case 'basic-sms-login':
      return BasicSmsLoginFixture;
    case 'basic-search':
      return BasicSearchFixture;
    case 'basic-detail':
      return BasicDetailFixture;
    case 'basic-settings':
      return BasicSettingsFixture;
    case 'basic-confirm':
      return BasicConfirmFixture;
    default:
      return null;
  }
});

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

watch(() => props.fixtureId, () => {
  onReset();
});

function onReset() {
  status.value = 'idle';
  resultText.value = '';
  fixtureRef.value?.reset();
}
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

.empty {
  padding: 12px;
  border-radius: 6px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 13px;
}
</style>
