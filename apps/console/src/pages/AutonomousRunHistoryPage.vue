<template>
  <div class="autonomous-history">
    <a-card :bordered="false">
      <template #title>
        <div class="history-header">
          <span>{{ $t('autonomousHistory.title') }}</span>
          <a-space>
            <a-button size="small" @click="loadFirstPage">
              {{ $t('common.refresh') }}
            </a-button>
            <a-button type="primary" size="small" @click="openWorkbench">
              {{ $t('autonomousHistory.openWorkbench') }}
            </a-button>
          </a-space>
        </div>
      </template>

      <a-table
        :columns="columns"
        :data-source="runs"
        :pagination="false"
        :loading="loading"
        row-key="run_id"
        size="middle"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'created_at'">
            {{ formatDate(record.created_at) }}
          </template>
          <template v-else-if="column.key === 'verdict'">
            <!-- Show the scenario-level outcome as the primary signal.
                 For negative-path scenarios (e.g. invalid_credentials)
                 the raw verdict is "failure" by design — surfacing that
                 as red here made correct runs look broken. Tooltip keeps
                 the raw verdict accessible for debugging. -->
            <a-tooltip
              v-if="record.verdict || record.scenario_matched !== null"
              :title="rowTooltip(record)"
            >
              <a-tag :color="effectiveStatusColor(rowStatus(record))">
                {{ rowStatusLabel(record) }}
              </a-tag>
            </a-tooltip>
            <span v-else class="muted">—</span>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-tag :color="statusColor(record.status)">{{ record.status }}</a-tag>
          </template>
          <template v-else-if="column.key === 'run_id'">
            <code class="run-id">{{ record.run_id.slice(0, 8) }}</code>
          </template>
          <template v-else-if="column.key === 'url'">
            <span class="truncate" :title="record.url || ''">
              {{ record.url || '—' }}
            </span>
          </template>
          <template v-else-if="column.key === 'actions'">
            <a-space size="small">
              <!-- Copy JSON: fetches full run detail and writes it to
                   the clipboard. Use case: paste into Claude Code for
                   analysis. -->
              <a-button
                type="link"
                size="small"
                :loading="copyingRunId === record.run_id"
                @click="copyRunJson(record.run_id)"
              >
                {{ $t('autonomousHistory.copyData') }}
              </a-button>
              <!-- View: navigate to dedicated detail page. -->
              <a-button
                type="link"
                size="small"
                @click="viewDetail(record.run_id)"
              >
                {{ $t('autonomousHistory.viewDetail') }}
              </a-button>
            </a-space>
          </template>
        </template>

        <template #emptyText>
          <a-empty :description="$t('autonomousHistory.empty')" />
        </template>
      </a-table>

      <div v-if="runs.length > 0" class="pagination-bar">
        <a-button size="small" :disabled="cursorStack.length === 0" @click="loadFirstPage">
          {{ $t('common.first') }}
        </a-button>
        <a-button size="small" :disabled="!hasNext" @click="loadNextPage">
          {{ $t('common.next') }}
        </a-button>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import {
  listAutonomousRuns,
  getAutonomousRun,
  type AutonomousRunSummary,
} from '@/api/exploration';
import {
  effectiveStatus,
  effectiveStatusColor,
  type EffectiveStatus,
} from '@/utils/autonomousDisplay';

function rowStatus(record: AutonomousRunSummary): EffectiveStatus {
  return effectiveStatus({
    verdict: record.verdict,
    scenarioMatched: record.scenario_matched,
    passGateStatus: record.pass_gate_status,
  });
}

function rowStatusLabel(record: AutonomousRunSummary): string {
  const s = rowStatus(record);
  if (s === 'success') return t('autonomousHistory.statusSuccess');
  if (s === 'failure') return t('autonomousHistory.statusFailure');
  if (s === 'unverified') return t('autonomousHistory.statusUnverified');
  if (s === 'partial') return t('autonomousHistory.statusPartial');
  if (s === 'uncertain') return t('autonomousHistory.statusUncertain');
  return '—';
}

function rowTooltip(record: AutonomousRunSummary): string {
  // Expose the raw rule-side verdict, scenario match flag, and strict
  // gate outcome so the operator can tell "passed negative-path" from
  // "broken positive-path" and "unverified due to LLM blip" apart on
  // hover. The gate is the main status shown as the tag; this tooltip
  // adds the inputs the gate was computed from.
  const parts: string[] = [];
  if (record.verdict) parts.push(`${t('autonomousHistory.ruleVerdict')}: ${record.verdict}`);
  if (record.scenario_matched === true) {
    parts.push(t('autonomousHistory.scenarioMatched'));
  } else if (record.scenario_matched === false) {
    parts.push(t('autonomousHistory.scenarioMismatch'));
  }
  if (record.pass_gate_status) {
    parts.push(`${t('autonomousHistory.passGate')}: ${record.pass_gate_status}`);
  }
  return parts.join(' · ');
}

const { t } = useI18n();
const router = useRouter();

const runs = ref<AutonomousRunSummary[]>([]);
const loading = ref(false);
const hasNext = ref(false);
const nextCursor = ref<string | null>(null);
const cursorStack = ref<(string | null)[]>([]); // tracks previous cursors for "first" reset
const copyingRunId = ref<string | null>(null);

const columns = [
  { key: 'created_at', dataIndex: 'created_at', title: t('autonomousHistory.colCreated'), width: 180 },
  { key: 'spec_id', dataIndex: 'spec_id', title: t('autonomousHistory.colSpec'), width: 140 },
  { key: 'scenario', dataIndex: 'scenario', title: t('autonomousHistory.colScenario'), width: 150 },
  { key: 'verdict', dataIndex: 'verdict', title: t('autonomousHistory.colVerdict'), width: 130 },
  { key: 'status', dataIndex: 'status', title: t('autonomousHistory.colStatus'), width: 110 },
  { key: 'url', dataIndex: 'url', title: 'URL', ellipsis: true },
  { key: 'run_id', dataIndex: 'run_id', title: t('autonomousHistory.colRunId'), width: 100 },
  { key: 'actions', title: t('common.actions'), width: 180, fixed: 'right' as const },
];

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function statusColor(status: string): string {
  if (status === 'succeeded' || status === 'success') return 'green';
  if (status === 'failed' || status === 'error') return 'red';
  if (status === 'running' || status === 'pending') return 'blue';
  return 'default';
}

async function loadRuns(cursor: string | null): Promise<void> {
  loading.value = true;
  try {
    const page = await listAutonomousRuns({ limit: 20, cursor });
    runs.value = page.items;
    hasNext.value = page.has_next;
    nextCursor.value = page.next_cursor;
  } catch (err) {
    message.error((err as Error).message || t('error.network'));
  } finally {
    loading.value = false;
  }
}

async function loadFirstPage(): Promise<void> {
  cursorStack.value = [];
  await loadRuns(null);
}

async function loadNextPage(): Promise<void> {
  if (!nextCursor.value) return;
  cursorStack.value.push(nextCursor.value);
  await loadRuns(nextCursor.value);
}

async function copyRunJson(runId: string): Promise<void> {
  // Fetches the full run detail from /autonomous-runs/get and writes
  // its JSON-stringified form to the clipboard. The intent is "give
  // the whole run to Claude Code for analysis" — one click instead of
  // navigating to a detail view and hunting through a <pre> block.
  copyingRunId.value = runId;
  try {
    const detail = await getAutonomousRun(runId);
    const text = JSON.stringify(detail, null, 2);
    await navigator.clipboard.writeText(text);
    message.success(
      t('autonomousHistory.copied', { bytes: text.length }),
    );
  } catch (err) {
    message.error((err as Error).message || t('error.network'));
  } finally {
    copyingRunId.value = null;
  }
}

function viewDetail(runId: string): void {
  void router.push(`/exploration/autonomous/history/${runId}`);
}

function openWorkbench(): void {
  void router.push('/exploration/autonomous');
}

onMounted(() => {
  void loadFirstPage();
});
</script>

<style scoped>
.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.run-id {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  color: #595959;
}

.truncate {
  display: inline-block;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.muted {
  color: #bfbfbf;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  gap: 8px;
}
</style>
