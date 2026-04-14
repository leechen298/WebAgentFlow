<template>
  <main class="popup">
    <div class="header">
      <div class="badge" :class="{ 'badge-recording': state.isRecording }">
        {{ state.isRecording ? msg('badgeRecording') : msg('badgeReady') }}
      </div>
      <h1>WebAgentFlow</h1>
    </div>

    <!-- Status Section -->
    <div class="status-section">
      <div class="status-item">
        <span class="status-label">{{ msg('statusLabel') }}</span>
        <span class="status-value" :class="{ 'recording': state.isRecording }">
          {{ state.isRecording ? msg('statusRecording') : msg('statusReady') }}
        </span>
      </div>
      <div class="status-item">
        <span class="status-label">{{ msg('eventsLabel') }}</span>
        <span class="status-value">{{ state.events.length }}</span>
      </div>
    </div>

    <!-- Recording Name Input -->
    <div class="input-section" v-if="!state.isRecording && state.events.length > 0">
      <label for="recording-name">{{ msg('recordingNameLabel') }}</label>
      <input
        id="recording-name"
        v-model="recordingName"
        type="text"
        :placeholder="msg('recordingNamePlaceholder')"
        class="name-input"
      />
    </div>

    <!-- Control Buttons -->
    <div class="controls">
      <button
        v-if="!state.isRecording"
        class="btn btn-primary"
        @click="handleStart"
        :disabled="isLoading"
      >
        {{ isLoading ? msg('btnStarting') : msg('btnStartRecording') }}
      </button>

      <button
        v-else
        class="btn btn-danger"
        @click="handleStop"
        :disabled="isLoading"
      >
        {{ isLoading ? msg('btnStopping') : msg('btnStopRecording') }}
      </button>

      <div class="secondary-controls" v-if="!state.isRecording">
        <button
          class="btn btn-secondary"
          @click="handleClear"
          :disabled="state.events.length === 0 || isLoading"
        >
          {{ msg('btnClear') }}
        </button>

        <button
          class="btn btn-success"
          @click="handleSubmit"
          :disabled="state.events.length === 0 || isLoading"
        >
          {{ isSubmitting ? msg('btnSubmitting') : msg('btnSubmit') }}
        </button>
      </div>
    </div>

    <!-- Messages -->
    <div v-if="message" class="message" :class="messageType">
      {{ message }}
    </div>

    <!-- Event Preview (first few events) -->
    <div v-if="state.events.length > 0 && !state.isRecording" class="events-preview">
      <h3>{{ msg('eventsPreviewTitle', [String(state.events.length)]) }}</h3>
      <div class="event-list">
        <div v-for="(event, index) in previewEvents" :key="index" class="event-item">
          <span class="event-type">{{ event.type }}</span>
          <span class="event-url" :title="event.url">
            {{ formatUrl(event.url) }}
          </span>
        </div>
        <div v-if="state.events.length > 5" class="event-more">
          {{ msg('eventsMore', [String(state.events.length - 5)]) }}
        </div>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import type { RecorderState } from '../../src/recorder/state';
import { submitRecording, generateRecordingName } from '../../src/recorder/submit';

// State
const state = ref<RecorderState>({
  isRecording: false,
  events: [],
  startTime: null,
  initialUrl: null,
  initialTitle: null,
  initialState: null,
});

const isLoading = ref(false);
const isSubmitting = ref(false);
const recordingName = ref('');
const message = ref('');
const messageType = ref<'success' | 'error' | 'info'>('info');

// i18n helper
const msg = (key: string, substitutions?: string | string[]) =>
  browser.i18n.getMessage(key, substitutions) || key;

// Computed
const previewEvents = computed(() => state.value.events.slice(0, 5));

// Methods
function showMessage(text: string, type: 'success' | 'error' | 'info' = 'info') {
  message.value = text;
  messageType.value = type;
  setTimeout(() => {
    if (message.value === text) {
      message.value = '';
    }
  }, 5000);
}

function formatUrl(url: string): string {
  try {
    const u = new URL(url);
    return u.hostname + u.pathname.slice(0, 30);
  } catch {
    return url.slice(0, 40);
  }
}

async function fetchState() {
  try {
    const response = await browser.runtime.sendMessage({ type: 'GET_STATE' });
    if (response.success) {
      state.value = response.state;
      if (!recordingName.value && state.value.events.length > 0) {
        recordingName.value = generateRecordingName(state.value.initialUrl);
      }
    }
  } catch (error) {
    console.error('Failed to fetch state:', error);
  }
}

async function handleStart() {
  isLoading.value = true;
  message.value = '';

  try {
    const response = await browser.runtime.sendMessage({ type: 'START_RECORDING' });
    if (response.success) {
      state.value = response.state;
      recordingName.value = '';
      showMessage(msg('msgRecordingStarted'), 'success');
    } else {
      showMessage(response.error || msg('msgFailedToStart'), 'error');
    }
  } catch (error) {
    showMessage(msg('msgError', [String(error)]), 'error');
  } finally {
    isLoading.value = false;
  }
}

async function handleStop() {
  isLoading.value = true;
  message.value = '';

  try {
    const response = await browser.runtime.sendMessage({ type: 'STOP_RECORDING' });
    if (response.success) {
      state.value = response.state;
      recordingName.value = generateRecordingName(state.value.initialUrl);
      showMessage(msg('msgRecordingStopped', [String(state.value.events.length)]), 'success');
    } else {
      showMessage(response.error || msg('msgFailedToStop'), 'error');
    }
  } catch (error) {
    showMessage(msg('msgError', [String(error)]), 'error');
  } finally {
    isLoading.value = false;
  }
}

async function handleClear() {
  isLoading.value = true;
  message.value = '';

  try {
    const response = await browser.runtime.sendMessage({ type: 'CLEAR_RECORDING' });
    if (response.success) {
      state.value = response.state;
      recordingName.value = '';
      showMessage(msg('msgRecordingCleared'), 'info');
    } else {
      showMessage(response.error || msg('msgFailedToClear'), 'error');
    }
  } catch (error) {
    showMessage(msg('msgError', [String(error)]), 'error');
  } finally {
    isLoading.value = false;
  }
}

async function handleSubmit() {
  if (!recordingName.value.trim()) {
    showMessage(msg('msgEnterName'), 'error');
    return;
  }

  isSubmitting.value = true;
  message.value = '';

  try {
    const result = await submitRecording({
      name: recordingName.value.trim(),
      events: state.value.events,
      initialUrl: state.value.initialUrl,
      initialTitle: state.value.initialTitle,
      startTime: state.value.startTime,
      initialState: state.value.initialState,
    });

    showMessage(msg('msgSubmitSuccess', [result.name]), 'success');

    // Clear after successful submit
    setTimeout(async () => {
      const response = await browser.runtime.sendMessage({ type: 'CLEAR_RECORDING' });
      if (response.success) {
        state.value = response.state;
        recordingName.value = '';
      }
    }, 1500);
  } catch (error) {
    showMessage(msg('msgSubmitFailed', [String(error)]), 'error');
  } finally {
    isSubmitting.value = false;
  }
}

// Lifecycle
onMounted(() => {
  fetchState();

  // Poll for state updates
  const interval = setInterval(() => {
    fetchState();
  }, 1000);

  // Cleanup on unmount
  window.addEventListener('beforeunload', () => {
    clearInterval(interval);
  });
});
</script>

<style scoped>
.popup {
  width: 360px;
  min-height: 300px;
  padding: 20px;
  background:
    radial-gradient(circle at top, rgba(31, 122, 140, 0.18), transparent 45%),
    linear-gradient(180deg, #fffef8 0%, #edf4f4 100%);
  color: #102a43;
  font-family: 'IBM Plex Sans', 'Segoe UI', system-ui, sans-serif;
}

.header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.badge {
  display: inline-flex;
  padding: 4px 10px;
  border-radius: 999px;
  background: #d8eef0;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.badge-recording {
  background: #ff4444;
  color: white;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

h1 {
  margin: 0;
  font-size: 20px;
}

.status-section {
  display: flex;
  gap: 20px;
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 8px;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-label {
  font-size: 12px;
  color: #627d98;
}

.status-value {
  font-size: 16px;
  font-weight: 600;
}

.status-value.recording {
  color: #ff4444;
}

.input-section {
  margin-bottom: 16px;
}

.input-section label {
  display: block;
  font-size: 12px;
  color: #627d98;
  margin-bottom: 4px;
}

.name-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #9fb3c8;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}

.name-input:focus {
  outline: none;
  border-color: #1f7a8c;
  box-shadow: 0 0 0 2px rgba(31, 122, 140, 0.2);
}

.controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.secondary-controls {
  display: flex;
  gap: 12px;
}

.btn {
  flex: 1;
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #1f7a8c;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #175d6b;
}

.btn-danger {
  background: #ff4444;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #cc3333;
}

.btn-secondary {
  background: #9fb3c8;
  color: #102a43;
}

.btn-secondary:hover:not(:disabled) {
  background: #829ab1;
}

.btn-success {
  background: #27ae60;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #1e8449;
}

.message {
  margin-top: 16px;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
}

.message.success {
  background: rgba(39, 174, 96, 0.1);
  color: #1e8449;
}

.message.error {
  background: rgba(255, 68, 68, 0.1);
  color: #cc3333;
}

.message.info {
  background: rgba(31, 122, 140, 0.1);
  color: #175d6b;
}

.events-preview {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(159, 179, 200, 0.3);
}

.events-preview h3 {
  margin: 0 0 8px;
  font-size: 13px;
  color: #627d98;
}

.event-list {
  background: rgba(255, 255, 255, 0.5);
  border-radius: 6px;
  overflow: hidden;
}

.event-item {
  display: flex;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(159, 179, 200, 0.2);
  font-size: 12px;
}

.event-item:last-child {
  border-bottom: none;
}

.event-type {
  font-weight: 600;
  color: #1f7a8c;
  min-width: 60px;
}

.event-url {
  color: #627d98;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.event-more {
  padding: 8px 12px;
  font-size: 12px;
  color: #9fb3c8;
  text-align: center;
}
</style>
