<template>
  <div>
    <a-page-header :title="$t('exploration.title')" :sub-title="$t('exploration.subtitle')" />

    <!-- ① Task Configuration -->
    <a-card :title="$t('exploration.taskConfig')" :bordered="false" style="margin-top: 16px">
      <a-form layout="inline" @finish="handleRun">
        <a-form-item :label="$t('exploration.selectTask')">
          <a-select
            v-model:value="selectedTaskId"
            style="width: 280px"
            :placeholder="$t('exploration.selectTaskPlaceholder')"
            :loading="tasksLoading"
            @change="handleTaskChange"
          >
            <a-select-option v-for="t in tasks" :key="t.id" :value="t.id">
              {{ t.name }} ({{ t.step_count }} steps)
            </a-select-option>
          </a-select>
        </a-form-item>

        <!-- Dynamic variables -->
        <a-form-item
          v-for="(val, key) in editableVariables"
          :key="key"
          :label="String(key)"
        >
          <a-input
            v-model:value="editableVariables[key]"
            style="width: 200px"
          />
        </a-form-item>

        <a-form-item :label="$t('exploration.maxSteps')">
          <a-input-number
            v-model:value="maxSteps"
            :min="1"
            :max="20"
            :placeholder="$t('exploration.allSteps')"
            allow-clear
            style="width: 100px"
          />
        </a-form-item>

        <a-form-item>
          <a-space>
            <a-button
              type="primary"
              html-type="submit"
              :loading="running"
              :disabled="!selectedTaskId"
            >
              {{ $t('exploration.start') }}
            </a-button>
            <a-button v-if="running" danger @click="handleStop">
              {{ $t('exploration.stop') }}
            </a-button>
          </a-space>
        </a-form-item>
      </a-form>

      <a-alert type="info" show-icon style="margin-top: 16px">
        <template #message>{{ $t('exploration.runAllStepsHint') }}</template>
        <template #description>
          <a-descriptions :column="1" size="small">
            <a-descriptions-item :label="$t('exploration.currentTask')">
              {{ selectedTask?.name || '—' }}
            </a-descriptions-item>
            <a-descriptions-item :label="$t('exploration.taskUrl')">
              {{ selectedTask?.target_url || '—' }}
            </a-descriptions-item>
            <a-descriptions-item :label="$t('exploration.currentVariables')">
              {{ variableSummary }}
            </a-descriptions-item>
            <a-descriptions-item :label="$t('exploration.currentStatus')">
              {{ currentStatusLabel }}
            </a-descriptions-item>
          </a-descriptions>
        </template>
      </a-alert>
    </a-card>

    <!-- Error -->
    <a-alert
      v-if="error"
      :message="$t('exploration.error')"
      :description="error"
      type="error"
      show-icon
      closable
      style="margin-top: 16px"
      @close="error = null"
    />

    <!-- Main content: execution + page state side by side -->
    <a-row v-if="result" :gutter="16" style="margin-top: 16px">
      <!-- ② Execution Timeline -->
      <a-col :span="16">
        <a-card :title="$t('exploration.executionTimeline')" :bordered="false">
          <!-- Overall result banner -->
          <a-alert
            :message="result.success ? $t('exploration.taskSucceeded') : $t('exploration.taskFailed')"
            :type="result.success ? 'success' : 'error'"
            show-icon
            style="margin-bottom: 16px"
          >
            <template #description>
              {{ result.total_steps }} steps, {{ result.elapsed_ms }}ms
              <span v-if="result.final_url"> — {{ result.final_url }}</span>
            </template>
          </a-alert>

          <a-alert
            :message="$t('exploration.resultSummary')"
            :description="result.summary"
            type="info"
            show-icon
            style="margin-bottom: 16px"
          />

          <!-- Step timeline -->
          <a-timeline>
            <a-timeline-item
              v-for="step in result.steps"
              :key="step.step_index"
              :color="stepColor(step)"
            >
              <div class="step-header">
                <a-tag :color="stepColor(step)">
                  Step {{ step.step_index }}
                </a-tag>
                <strong>{{ step.intent }}</strong>
                <a-tag>{{ step.action_type }}</a-tag>
                <span v-if="step.value" class="step-value">"{{ step.value }}"</span>
              </div>

              <div class="step-detail">
                <!-- Execution result -->
                <div v-if="step.execution_result" class="step-section">
                  <a-tag :color="step.execution_result.ok ? 'green' : 'red'">
                    {{ step.execution_result.ok ? 'OK' : 'FAILED' }}
                  </a-tag>
                  <span v-if="step.execution_result.error" class="step-error">
                    {{ step.execution_result.error }}
                  </span>
                  <span v-if="step.target_summary" class="step-target">
                    → {{ step.target_summary }}
                  </span>
                </div>

                <!-- Observation summary -->
                <div v-if="step.observation" class="step-section">
                  <a-space :size="4">
                    <a-tag v-if="step.observation.url_changed" color="blue">URL changed</a-tag>
                    <a-tag v-if="step.observation.title_changed" color="blue">Title changed</a-tag>
                    <a-tag v-if="step.observation.html_changed" color="blue">HTML changed</a-tag>
                    <span v-if="step.observation.url" class="step-url">{{ step.observation.url }}</span>
                  </a-space>
                </div>

                <!-- Success evaluation -->
                <div v-if="step.success_evaluation" class="step-section">
                  <a-tag :color="evalColor(step.success_evaluation)">
                    {{ step.success_evaluation.satisfied ? 'SATISFIED' : 'NOT SATISFIED' }}
                    ({{ step.success_evaluation.confidence }})
                  </a-tag>
                  <a-tag
                    v-for="cond in step.success_evaluation.matched_conditions"
                    :key="cond"
                    color="green"
                    size="small"
                  >
                    ✓ {{ cond }}
                  </a-tag>
                  <a-tag
                    v-for="cond in step.success_evaluation.failed_conditions"
                    :key="cond"
                    color="red"
                    size="small"
                  >
                    ✗ {{ cond }}
                  </a-tag>
                  <div v-if="step.success_evaluation.uncertain_reason" class="step-uncertain">
                    {{ step.success_evaluation.uncertain_reason }}
                  </div>
                </div>

                <!-- Agent note -->
                <div v-if="step.agent_note" class="step-note">
                  {{ step.agent_note }}
                </div>

                <!-- Raw JSON collapse -->
                <a-collapse :bordered="false" size="small" style="margin-top: 8px">
                  <a-collapse-panel v-if="step.execution_result" header="Raw ExecutionResult" :key="`exec-${step.step_index}`">
                    <pre class="raw-json">{{ JSON.stringify(step.execution_result, null, 2) }}</pre>
                  </a-collapse-panel>
                  <a-collapse-panel v-if="step.observation" header="Raw Observation" :key="`obs-${step.step_index}`">
                    <pre class="raw-json">{{ JSON.stringify(step.observation, null, 2) }}</pre>
                  </a-collapse-panel>
                </a-collapse>
              </div>
            </a-timeline-item>
          </a-timeline>
        </a-card>
      </a-col>

      <!-- ③ Page State + Supervisor -->
      <a-col :span="8">
        <!-- Screenshot -->
        <a-card :title="$t('exploration.pageState')" :bordered="false">
          <div v-if="selectedScreenshot" class="screenshot-container">
            <a-image
              :src="selectedScreenshot"
              class="screenshot-img"
              :preview="{ mask: $t('exploration.clickToZoom') }"
            />
          </div>
          <a-empty v-else :description="$t('exploration.noScreenshot')" />

          <a-descriptions :column="1" size="small" style="margin-top: 12px">
            <a-descriptions-item label="URL">
              {{ result.final_url || '—' }}
            </a-descriptions-item>
            <a-descriptions-item label="Title">
              {{ result.final_title || '—' }}
            </a-descriptions-item>
          </a-descriptions>

          <!-- Per-step screenshot selector -->
          <div v-if="stepScreenshots.length > 0" style="margin-top: 12px">
            <span style="font-size: 12px; color: #8c8c8c">{{ $t('exploration.stepScreenshots') }}</span>
            <a-radio-group
              v-model:value="selectedScreenshotIndex"
              button-style="solid"
              size="small"
              style="margin-top: 4px"
            >
              <a-radio-button
                v-for="(ss, idx) in stepScreenshots"
                :key="idx"
                :value="idx"
              >
                {{ ss.label }}
              </a-radio-button>
            </a-radio-group>
          </div>
        </a-card>

        <!-- Supervisor Assessment -->
        <a-card
          v-if="result.supervisor"
          :title="$t('exploration.supervisorAssessment')"
          :bordered="false"
          style="margin-top: 16px"
        >
          <a-tag :color="verdictColor(result.supervisor.verdict)" style="font-size: 14px; padding: 4px 12px">
            {{ result.supervisor.verdict.toUpperCase() }}
          </a-tag>
          <a-tag>{{ result.supervisor.confidence }}</a-tag>

          <p style="margin-top: 12px">{{ result.supervisor.summary }}</p>

          <!-- Anomalies -->
          <div v-if="result.supervisor.anomalies.length > 0" style="margin-top: 8px">
            <strong>{{ $t('exploration.anomalies') }}</strong>
            <ul style="margin: 4px 0; padding-left: 20px">
              <li v-for="(a, i) in result.supervisor.anomalies" :key="i">{{ a }}</li>
            </ul>
          </div>

          <!-- Suggestions -->
          <div v-if="result.supervisor.suggestions.length > 0" style="margin-top: 8px">
            <strong>{{ $t('exploration.suggestions') }}</strong>
            <ul style="margin: 4px 0; padding-left: 20px">
              <li v-for="(s, i) in result.supervisor.suggestions" :key="i">{{ s }}</li>
            </ul>
          </div>

          <!-- Per-step assessments -->
          <a-collapse :bordered="false" size="small" style="margin-top: 8px">
            <a-collapse-panel :header="$t('exploration.perStepAssessment')">
              <div v-for="sa in result.supervisor.step_assessments" :key="sa.step_index" style="margin-bottom: 4px">
                <a-tag :color="sa.status === 'ok' ? 'green' : sa.status === 'failed' ? 'red' : 'orange'" size="small">
                  Step {{ sa.step_index }}: {{ sa.status }}
                </a-tag>
                {{ sa.note }}
              </div>
            </a-collapse-panel>
          </a-collapse>
        </a-card>
      </a-col>
    </a-row>

    <!-- ④ User Verdict -->
    <a-card
      v-if="result"
      :title="$t('exploration.userVerdict')"
      :bordered="false"
      style="margin-top: 16px"
    >
      <a-space>
        <a-button type="primary" @click="handleApprove">
          {{ $t('exploration.approvePath') }}
        </a-button>
        <a-button danger @click="handleReject">
          {{ $t('exploration.rejectPath') }}
        </a-button>
        <a-button @click="handleRerun">
          {{ $t('exploration.rerun') }}
        </a-button>
      </a-space>
      <a-input
        v-model:value="verdictNote"
        :placeholder="$t('exploration.notePlaceholder')"
        style="margin-top: 12px; max-width: 600px"
      />
      <div class="verdict-placeholder">
        {{ $t('exploration.placeholderNotice') }}
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import { useI18n } from 'vue-i18n';
import {
  listTasks,
  runExploration,
  approveRun,
  rejectRun,
  type TaskListItem,
  type RunExplorationResponse,
  type ExplorationStepData,
} from '@/api/exploration';
import { resolveApiConfig } from '@/api/client';

const _apiBase = resolveApiConfig().baseURL;

const { t: $t } = useI18n();

// ─── State ───────────────────────────────────────────────────

const tasks = ref<TaskListItem[]>([]);
const tasksLoading = ref(false);
const selectedTaskId = ref<string | null>(null);
const editableVariables = reactive<Record<string, string>>({});
const maxSteps = ref<number | null>(null);

const running = ref(false);
const result = ref<RunExplorationResponse | null>(null);
const error = ref<string | null>(null);
const verdictNote = ref('');

const selectedScreenshotIndex = ref(0);

// ─── Computed ────────────────────────────────────────────────

const selectedTask = computed(() =>
  tasks.value.find(task => task.id === selectedTaskId.value) ?? null,
);

const variableSummary = computed(() => {
  const pairs = Object.entries(editableVariables);
  if (pairs.length === 0) return '—';
  return pairs.map(([key, value]) => `${key}=${value}`).join(', ');
});

const currentStatusLabel = computed(() => {
  if (running.value) return $t('exploration.runningStatus');
  if (result.value) return $t('exploration.finishedStatus');
  return $t('exploration.idleStatus');
});

interface StepScreenshot {
  label: string;
  src: string;
}

/** Prepend API base so the browser can load screenshot images. */
function screenshotUrl(ref: string | null | undefined): string | null {
  if (!ref) return null;
  return `${_apiBase}${ref}`;
}

const stepScreenshots = computed<StepScreenshot[]>(() => {
  if (!result.value) return [];
  const shots: StepScreenshot[] = [];
  for (const step of result.value.steps) {
    const obs = step.observation as Record<string, unknown> | null;
    const exec = step.execution_result as Record<string, unknown> | null;
    const raw = (obs?.screenshot_ref ?? exec?.screenshot_ref) as string | undefined;
    const url = screenshotUrl(raw);
    if (url) {
      shots.push({ label: `Step ${step.step_index}`, src: url });
    }
  }
  const finalUrl = screenshotUrl(result.value.final_screenshot_ref);
  if (finalUrl) {
    shots.push({ label: 'Final', src: finalUrl });
  }
  return shots;
});

const selectedScreenshot = computed(() => {
  if (stepScreenshots.value.length === 0) {
    return screenshotUrl(result.value?.final_screenshot_ref) || null;
  }
  return stepScreenshots.value[selectedScreenshotIndex.value]?.src || null;
});

// ─── Helpers ─────────────────────────────────────────────────

function stepColor(step: ExplorationStepData): string {
  if (step.execution_result && !step.execution_result.ok) return 'red';
  if (step.success_evaluation && !step.success_evaluation.satisfied) {
    return step.success_evaluation.confidence === 'low' ? 'orange' : 'red';
  }
  return 'green';
}

function evalColor(ev: NonNullable<ExplorationStepData['success_evaluation']>): string {
  if (ev.satisfied) return 'green';
  if (ev.confidence === 'low') return 'orange';
  return 'red';
}

function verdictColor(verdict: string): string {
  switch (verdict) {
    case 'success': return 'green';
    case 'partial_success': return 'orange';
    case 'failure': return 'red';
    default: return 'default';
  }
}

// ─── Actions ─────────────────────────────────────────────────

async function loadTasks() {
  tasksLoading.value = true;
  try {
    tasks.value = await listTasks();
  } catch (e) {
    error.value = String(e);
  } finally {
    tasksLoading.value = false;
  }
}

function handleTaskChange(taskId: string) {
  const task = tasks.value.find(t => t.id === taskId);
  // Reset editable variables
  Object.keys(editableVariables).forEach(k => delete editableVariables[k]);
  if (task) {
    Object.entries(task.variables).forEach(([k, v]) => {
      editableVariables[k] = String(v);
    });
  }
}

async function handleRun() {
  if (!selectedTaskId.value) return;
  running.value = true;
  error.value = null;
  result.value = null;
  selectedScreenshotIndex.value = 0;

  try {
    result.value = await runExploration({
      task_id: selectedTaskId.value,
      variables: { ...editableVariables },
      headless: false,
      max_steps: maxSteps.value,
    });
  } catch (e) {
    error.value = String(e);
  } finally {
    running.value = false;
  }
}

function handleStop() {
  // MVP: no real cancellation yet — just a placeholder
  message.info('Stop requested (not yet implemented in MVP)');
}

async function handleApprove() {
  if (!result.value) return;
  try {
    await approveRun('mvp-run', verdictNote.value);
    message.success('Path approved (MVP placeholder)');
  } catch (e) {
    message.error(String(e));
  }
}

async function handleReject() {
  if (!result.value) return;
  try {
    await rejectRun('mvp-run', verdictNote.value);
    message.warning('Path rejected (MVP placeholder)');
  } catch (e) {
    message.error(String(e));
  }
}

function handleRerun() {
  void handleRun();
}

// ─── Lifecycle ───────────────────────────────────────────────

onMounted(() => {
  void loadTasks();
});
</script>

<style scoped>
.step-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.step-detail {
  margin-top: 8px;
  padding-left: 4px;
}

.step-section {
  margin-top: 4px;
}

.step-value {
  color: #1890ff;
  font-style: italic;
}

.step-target {
  color: #8c8c8c;
  font-size: 12px;
}

.step-error {
  color: #ff4d4f;
  font-size: 12px;
}

.step-url {
  color: #8c8c8c;
  font-size: 12px;
  word-break: break-all;
}

.step-uncertain {
  color: #fa8c16;
  font-size: 12px;
  margin-top: 2px;
}

.step-note {
  color: #8c8c8c;
  font-size: 12px;
  font-style: italic;
  margin-top: 4px;
}

.raw-json {
  font-size: 11px;
  max-height: 300px;
  overflow: auto;
  background: #fafafa;
  padding: 8px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-all;
}

.screenshot-container {
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.screenshot-img {
  width: 100%;
  display: block;
}

.verdict-placeholder {
  margin-top: 8px;
  color: #8c8c8c;
  font-size: 12px;
}
</style>
