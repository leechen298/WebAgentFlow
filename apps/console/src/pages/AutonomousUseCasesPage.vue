<template>
  <div class="use-cases-page">
    <a-card :title="$t('autonomousUseCases.title')" :bordered="false">
      <template #extra>
        <a-space>
          <a-button size="small" @click="loadSpecs" :disabled="isRunning">
            <template #icon><reload-outlined /></template>
            {{ $t('autonomousUseCases.refresh') }}
          </a-button>
          <a-button type="primary" size="small" @click="goToWorkbench">
            {{ $t('autonomousUseCases.openWorkbench') }}
          </a-button>
        </a-space>
      </template>

      <p class="subtitle">{{ $t('autonomousUseCases.subtitle') }}</p>

      <a-alert
        v-if="errorMessage"
        type="error"
        :message="errorMessage"
        show-icon
        closable
        style="margin-bottom: 16px"
        @close="errorMessage = ''"
      />

      <!-- Batch toolbar -->
      <div v-if="specs.length > 0" class="batch-toolbar">
        <a-space>
          <span class="selection-count">
            {{ $t('autonomousUseCases.selectedCount', { n: selectedKeys.size }) }}
            /
            {{ $t('autonomousUseCases.runnableCount', { n: runnableScenarios.length }) }}
          </span>
          <a-button size="small" @click="selectAllRunnable" :disabled="isRunning">
            {{ $t('autonomousUseCases.selectAllRunnable') }}
          </a-button>
          <a-button size="small" @click="clearSelection" :disabled="isRunning || selectedKeys.size === 0">
            {{ $t('autonomousUseCases.clearSelection') }}
          </a-button>
          <a-tooltip
            v-if="selectedKeys.size === 0"
            :title="$t('autonomousUseCases.selectFirst')"
          >
            <a-button
              type="primary"
              size="small"
              disabled
            >
              <template #icon><caret-right-outlined /></template>
              {{ $t('autonomousUseCases.runSelected') }}
            </a-button>
          </a-tooltip>
          <a-button
            v-else
            type="primary"
            size="small"
            :disabled="isRunning"
            @click="startBatchRun"
          >
            <template #icon><caret-right-outlined /></template>
            {{ $t('autonomousUseCases.runSelected') }}
          </a-button>
          <a-button
            v-if="isRunning"
            type="primary"
            danger
            size="small"
            @click="abortRunning"
          >
            <template #icon><pause-circle-outlined /></template>
            {{ $t('autonomousUseCases.abortRunning') }}
          </a-button>
        </a-space>
        <div v-if="isRunning || hasCompletedTasks" class="batch-summary">
          <a-space wrap size="small">
            <a-tag v-if="runningCount > 0" color="processing" size="small">
              {{ $t('autonomousUseCases.statusRunning') }}: {{ runningCount }}
            </a-tag>
            <a-tag v-if="queuedCount > 0" size="small">
              {{ $t('autonomousUseCases.statusQueued') }}: {{ queuedCount }}
            </a-tag>
            <a-tag v-if="completedCount > 0" color="success" size="small">
              {{ $t('autonomousUseCases.statusCompleted') }}: {{ completedCount }}
            </a-tag>
            <a-tag v-if="failedCount > 0" color="error" size="small">
              {{ $t('autonomousUseCases.statusFailed') }}: {{ failedCount }}
            </a-tag>
            <a-tag v-if="abortedCount > 0" color="warning" size="small">
              {{ $t('autonomousUseCases.statusAborted') }}: {{ abortedCount }}
            </a-tag>
          </a-space>
        </div>
      </div>

      <a-spin :spinning="loading">
        <a-empty v-if="!loading && specs.length === 0" :description="$t('autonomousUseCases.empty')" />

        <div v-else class="spec-list">
          <a-card
            v-for="spec in specs"
            :key="spec.spec_id"
            size="small"
            class="spec-card"
            :title="spec.description || spec.spec_id"
          >
            <div class="spec-meta">
              <div>
                <strong>{{ $t('autonomousUseCases.specId') }}:</strong>
                <a-tag size="small">{{ spec.spec_id }}</a-tag>
              </div>
              <div v-if="spec.url_pattern">
                <strong>{{ $t('autonomousUseCases.urlPattern') }}:</strong>
                <code>{{ spec.url_pattern }}</code>
              </div>
            </div>

            <a-table
              :columns="scenarioColumns"
              :data-source="spec.scenarios"
              :pagination="false"
              size="small"
              row-key="key"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'checkbox'">
                  <a-tooltip
                    v-if="!spec.url_pattern"
                    :title="$t('autonomousUseCases.notRunnable')"
                  >
                    <a-checkbox :checked="false" disabled />
                  </a-tooltip>
                  <a-checkbox
                    v-else
                    :checked="isSelected(spec.spec_id, record.key)"
                    :disabled="isRunning"
                    @change="toggleSelect(spec.spec_id, record.key)"
                  />
                </template>
                <template v-if="column.key === 'key'">
                  <a-tag size="small">{{ record.key }}</a-tag>
                </template>
                <template v-if="column.key === 'description'">
                  {{ record.description }}
                </template>
                <template v-if="column.key === 'inputs'">
                  <span v-if="Object.keys(record.inputs || {}).length === 0">—</span>
                  <a-space v-else wrap size="small">
                    <a-tag
                      v-for="(val, k) in record.inputs"
                      :key="k"
                      size="small"
                    >
                      {{ k }}={{ val }}
                    </a-tag>
                  </a-space>
                </template>
                <template v-if="column.key === 'selections'">
                  <span v-if="Object.keys(record.selections || {}).length === 0">—</span>
                  <a-space v-else wrap size="small">
                    <a-tag
                      v-for="(val, k) in record.selections"
                      :key="k"
                      size="small"
                    >
                      {{ k }}={{ val }}
                    </a-tag>
                  </a-space>
                </template>
                <template v-if="column.key === 'expected'">
                  <span v-if="record.expected_verdict">{{ record.expected_verdict }}</span>
                  <span v-else-if="record.expected_verdict_not">
                    not {{ record.expected_verdict_not }}
                  </span>
                  <span v-else>—</span>
                </template>
                <template v-if="column.key === 'batchStatus'">
                  <span v-if="!getTaskStatus(spec.spec_id, record.key)">—</span>
                  <a-tag
                    v-else
                    :color="statusTagColor(getTaskStatus(spec.spec_id, record.key)!)"
                    size="small"
                  >
                    {{ statusLabel(getTaskStatus(spec.spec_id, record.key)!) }}
                    <span
                      v-if="getTaskError(spec.spec_id, record.key)"
                      class="task-error"
                    >: {{ getTaskError(spec.spec_id, record.key) }}</span>
                  </a-tag>
                </template>
                <template v-if="column.key === 'action'">
                  <a-tooltip
                    v-if="!spec.url_pattern"
                    :title="$t('autonomousUseCases.noUrlPattern')"
                  >
                    <a-button size="small" disabled>
                      {{ $t('autonomousUseCases.runInWorkbench') }}
                    </a-button>
                  </a-tooltip>
                  <a-button
                    v-else
                    type="primary"
                    size="small"
                    :disabled="isRunning"
                    @click="runInWorkbench(spec, record)"
                  >
                    {{ $t('autonomousUseCases.runInWorkbench') }}
                  </a-button>
                </template>
              </template>
            </a-table>
          </a-card>
        </div>
      </a-spin>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { ReloadOutlined, CaretRightOutlined, PauseCircleOutlined } from '@ant-design/icons-vue';
import { listSpecs, type SpecSummary, type SpecScenarioSummary } from '@/api/exploration';
import {
  streamAutonomousRun,
  type AutonomousStreamPayload,
} from '@/api/autonomousStream';

const CONCURRENCY_LIMIT = 3;

const { t } = useI18n();
const router = useRouter();

const loading = ref(false);
const errorMessage = ref('');
const specs = ref<SpecSummary[]>([]);
const selectedKeys = ref<Set<string>>(new Set());

interface BatchTask {
  specId: string;
  scenarioKey: string;
  description: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'aborted';
  error?: string;
  runId?: string;
  abort: (() => void) | null;
}

const batchTasks = ref<Record<string, BatchTask>>({});

const validationOrigin =
  import.meta.env.VITE_VALIDATION_SITE_ORIGIN || 'http://localhost:5175';

// ─── Computed ──────────────────────────────────────────────

const runnableScenarios = computed(() => {
  const result: { spec: SpecSummary; scenario: SpecScenarioSummary; key: string }[] = [];
  for (const spec of specs.value) {
    if (!spec.url_pattern) continue;
    for (const scenario of spec.scenarios) {
      result.push({ spec, scenario, key: `${spec.spec_id}::${scenario.key}` });
    }
  }
  return result;
});

const isRunning = computed(() =>
  Object.values(batchTasks.value).some(
    (t) => t.status === 'queued' || t.status === 'running',
  ),
);

const hasCompletedTasks = computed(() =>
  Object.values(batchTasks.value).some(
    (t) => t.status === 'completed' || t.status === 'failed',
  ),
);

const runningCount = computed(() =>
  Object.values(batchTasks.value).filter((t) => t.status === 'running').length,
);
const queuedCount = computed(() =>
  Object.values(batchTasks.value).filter((t) => t.status === 'queued').length,
);
const completedCount = computed(() =>
  Object.values(batchTasks.value).filter((t) => t.status === 'completed').length,
);
const failedCount = computed(() =>
  Object.values(batchTasks.value).filter((t) => t.status === 'failed').length,
);
const abortedCount = computed(() =>
  Object.values(batchTasks.value).filter((t) => t.status === 'aborted').length,
);

const scenarioColumns = computed(() => [
  { title: '', key: 'checkbox', width: 40 },
  { title: t('autonomousUseCases.scenario'), key: 'key', width: 160 },
  { title: t('common.description'), key: 'description' },
  { title: t('autonomousUseCases.inputs'), key: 'inputs', width: 200 },
  { title: t('autonomousUseCases.selections'), key: 'selections', width: 160 },
  { title: t('autonomousUseCases.expected'), key: 'expected', width: 120 },
  { title: t('autonomousUseCases.batchStatus'), key: 'batchStatus', width: 120 },
  { title: t('common.actions'), key: 'action', width: 140 },
]);

// ─── Selection ──────────────────────────────────────────────

function batchKey(specId: string, scenarioKey: string): string {
  return `${specId}::${scenarioKey}`;
}

function isSelected(specId: string, scenarioKey: string): boolean {
  return selectedKeys.value.has(batchKey(specId, scenarioKey));
}

function toggleSelect(specId: string, scenarioKey: string): void {
  const key = batchKey(specId, scenarioKey);
  const next = new Set(selectedKeys.value);
  if (next.has(key)) next.delete(key);
  else next.add(key);
  selectedKeys.value = next;
}

function selectAllRunnable(): void {
  const keys = new Set<string>();
  for (const item of runnableScenarios.value) {
    keys.add(item.key);
  }
  selectedKeys.value = keys;
}

function clearSelection(): void {
  selectedKeys.value = new Set();
}

// ─── Spec loading ───────────────────────────────────────────

async function loadSpecs(): Promise<void> {
  loading.value = true;
  errorMessage.value = '';
  try {
    specs.value = await listSpecs();
  } catch (err) {
    errorMessage.value = t('autonomousUseCases.loadFailed') + ': ' + (err as Error).message;
  } finally {
    loading.value = false;
  }
}

// ─── Deep link to workbench ─────────────────────────────────

function workbenchQuery(spec: SpecSummary, scenarioKey: string, description: string): string {
  const params = new URLSearchParams();
  params.set('url', `${validationOrigin}${spec.url_pattern}`);
  params.set('spec_id', spec.spec_id);
  params.set('scenario', scenarioKey);
  if (description || spec.description) {
    params.set('goal', description || spec.description);
  }
  return `/exploration/autonomous?${params.toString()}`;
}

function runInWorkbench(spec: SpecSummary, scenario: SpecScenarioSummary): void {
  void router.push(workbenchQuery(spec, scenario.key, scenario.description));
}

function goToWorkbench(): void {
  void router.push('/exploration/autonomous');
}

// ─── Batch run ──────────────────────────────────────────────

function batchPayload(spec: SpecSummary, scenario: SpecScenarioSummary): AutonomousStreamPayload {
  return {
    url: `${validationOrigin}${spec.url_pattern}`,
    goal: scenario.description || spec.description || undefined,
    fill_values:
      Object.keys(scenario.inputs ?? {}).length > 0 ? scenario.inputs : undefined,
    toggle_values:
      Object.keys(scenario.selections ?? {}).length > 0
        ? scenario.selections
        : undefined,
    headless: true,
    spec_id: spec.spec_id,
    scenario: scenario.key,
  };
}

function startBatchRun(): void {
  const tasks: Record<string, BatchTask> = {};
  for (const key of selectedKeys.value) {
    const [specId, scenarioKey] = key.split('::', 2);
    const spec = specs.value.find((s) => s.spec_id === specId);
    if (!spec || !spec.url_pattern) continue;
    const scenario = spec.scenarios.find((s) => s.key === scenarioKey);
    if (!scenario) continue;
    tasks[key] = {
      specId,
      scenarioKey,
      description: scenario.description,
      status: 'queued',
      abort: null,
    };
  }
  batchTasks.value = tasks;
  processQueue();
}

function processQueue(): void {
  const running = Object.values(batchTasks.value).filter(
    (t) => t.status === 'running',
  ).length;
  const slots = CONCURRENCY_LIMIT - running;
  if (slots <= 0) return;

  let started = 0;
  for (const [key, task] of Object.entries(batchTasks.value)) {
    if (started >= slots) break;
    if (task.status !== 'queued') continue;

    const [specId, scenarioKey] = key.split('::', 2);
    const spec = specs.value.find((s) => s.spec_id === specId);
    if (!spec) continue;
    const scenario = spec.scenarios.find((s) => s.key === scenarioKey);
    if (!scenario) continue;

    task.status = 'running';
    started++;

    const abort = streamAutonomousRun(batchPayload(spec, scenario), {
      onEvent: (evt) => {
        if (task.status === 'aborted') return;
        if (evt.event === 'run_completed') {
          task.status = 'completed';
          if (
            evt.data &&
            typeof evt.data === 'object' &&
            'run_id' in evt.data
          ) {
            task.runId = (evt.data as Record<string, unknown>).run_id as string;
          }
        } else if (evt.event === 'run_failed') {
          task.status = 'failed';
          const data = evt.data;
          if (data && typeof data === 'object' && 'error' in data) {
            task.error = (data as Record<string, unknown>).error as string;
          } else if (data && typeof data === 'string') {
            task.error = data;
          }
        }
      },
      onError: (err) => {
        if (task.status === 'aborted') return;
        task.status = 'failed';
        task.error = err.message;
        task.abort = null;
        batchTasks.value = { ...batchTasks.value };
        processQueue();
      },
      onDone: () => {
        if (task.status === 'running') {
          task.status = 'completed';
        }
        task.abort = null;
        batchTasks.value = { ...batchTasks.value };
        processQueue();
      },
    });
    task.abort = abort;
  }
  batchTasks.value = { ...batchTasks.value };
}

function abortRunning(): void {
  for (const task of Object.values(batchTasks.value)) {
    if (task.status === 'queued') {
      task.status = 'aborted';
    } else if (task.status === 'running' && task.abort) {
      task.abort();
      task.status = 'aborted';
      task.abort = null;
    }
  }
  batchTasks.value = { ...batchTasks.value };
}

// ─── Batch status helpers ───────────────────────────────────

function getTaskStatus(specId: string, scenarioKey: string): string | null {
  return batchTasks.value[batchKey(specId, scenarioKey)]?.status ?? null;
}

function getTaskError(specId: string, scenarioKey: string): string | undefined {
  return batchTasks.value[batchKey(specId, scenarioKey)]?.error;
}

function statusTagColor(s: string): string {
  switch (s) {
    case 'running':
      return 'processing';
    case 'completed':
      return 'success';
    case 'failed':
      return 'error';
    case 'aborted':
      return 'warning';
    default:
      return 'default';
  }
}

function statusLabel(s: string): string {
  switch (s) {
    case 'queued':
      return t('autonomousUseCases.statusQueued');
    case 'running':
      return t('autonomousUseCases.statusRunning');
    case 'completed':
      return t('autonomousUseCases.statusCompleted');
    case 'failed':
      return t('autonomousUseCases.statusFailed');
    case 'aborted':
      return t('autonomousUseCases.statusAborted');
    default:
      return s;
  }
}

// ─── Lifecycle ──────────────────────────────────────────────

onMounted(() => {
  void loadSpecs();
});

onBeforeUnmount(() => {
  for (const task of Object.values(batchTasks.value)) {
    if (task.status === 'running' && task.abort) {
      task.abort();
    }
  }
});
</script>

<style scoped>
.use-cases-page {
  max-width: 1400px;
  margin: 0 auto;
}
.subtitle {
  color: #8c8c8c;
  margin-bottom: 16px;
}
.batch-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  margin-bottom: 16px;
}
.selection-count {
  font-size: 13px;
  color: #595959;
}
.batch-summary {
  display: flex;
  align-items: center;
}
.task-error {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
  vertical-align: middle;
}
.spec-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.spec-card {
  background: #fff;
}
.spec-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 12px;
  font-size: 13px;
}
.spec-meta code {
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}
</style>
