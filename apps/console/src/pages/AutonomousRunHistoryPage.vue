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
            <!-- Authoritative outcome is pass_gate_status. Running /
                 pending rows haven't produced a gate yet — show a
                 neutral loader instead of falling back to raw verdict
                 (which would render as "未通过" for negative-path
                 scenarios and mislead the operator). For completed
                 rows without a gate (ad-hoc runs with no spec), fall
                 back to scenario_matched / verdict as a last resort. -->
            <a-spin
              v-if="isRunningRow(record)"
              size="small"
            />
            <a-tooltip
              v-else-if="record.pass_gate_status || record.verdict || record.scenario_matched !== null"
              :title="rowTooltip(record)"
            >
              <a-tag :color="effectiveStatusColor(rowStatus(record))">
                {{ rowStatusLabel(record) }}
              </a-tag>
            </a-tooltip>
            <span v-else class="muted">—</span>
          </template>
          <template v-else-if="column.key === 'operator_review_status'">
            <a-tag :color="reviewStatusColor(record.operator_review_status)">
              {{ reviewStatusLabel(record.operator_review_status) }}
            </a-tag>
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
            <a-space :size="4">
              <a-button
                size="small"
                :loading="copyingRunId === record.run_id"
                @click="copyRunJson(record.run_id)"
              >
                {{ $t('autonomousHistory.copyData') }}
              </a-button>
              <a-button
                size="small"
                @click="viewDetail(record.run_id)"
              >
                {{ $t('autonomousHistory.viewDetail') }}
              </a-button>
              <a-popconfirm
                :title="$t('autonomousHistory.deleteConfirmPrompt')"
                :ok-text="$t('common.confirm')"
                :cancel-text="$t('common.cancel')"
                @confirm="handleDelete(record.run_id)"
              >
                <a-button
                  size="small"
                  danger
                  :loading="deletingRunId === record.run_id"
                >
                  {{ $t('autonomousHistory.deleteRun') }}
                </a-button>
              </a-popconfirm>
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
  deleteAutonomousRun,
  type AutonomousRunSummary,
} from '@/api/exploration';
import {
  effectiveStatus,
  effectiveStatusColor,
  type EffectiveStatus,
} from '@/utils/autonomousDisplay';

function isRunningRow(record: AutonomousRunSummary): boolean {
  // Persisted rows are normally created at run-completion time, so
  // "running" is rare in this list — but guard anyway so a row
  // captured mid-stream doesn't render a premature verdict tag.
  const s = (record.status || "").toLowerCase();
  return s === "running" || s === "pending" || s === "in_progress";
}

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
const deletingRunId = ref<string | null>(null);

const columns = [
  { key: 'created_at', dataIndex: 'created_at', title: t('autonomousHistory.colCreated'), width: 180 },
  { key: 'spec_id', dataIndex: 'spec_id', title: t('autonomousHistory.colSpec'), width: 140 },
  { key: 'scenario', dataIndex: 'scenario', title: t('autonomousHistory.colScenario'), width: 150 },
  { key: 'verdict', dataIndex: 'verdict', title: t('autonomousHistory.colVerdict'), width: 130 },
  { key: 'operator_review_status', dataIndex: 'operator_review_status', title: t('autonomousHistory.colReviewStatus'), width: 110 },
  { key: 'status', dataIndex: 'status', title: t('autonomousHistory.colStatus'), width: 110 },
  { key: 'url', dataIndex: 'url', title: 'URL', ellipsis: true },
  { key: 'run_id', dataIndex: 'run_id', title: t('autonomousHistory.colRunId'), width: 100 },
  { key: 'actions', title: t('common.actions'), width: 240, fixed: 'right' as const },
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

function reviewStatusColor(status: string | null | undefined): string {
  if (status === 'accepted') return 'green';
  if (status === 'rejected') return 'red';
  return 'default';
}

function reviewStatusLabel(status: string | null | undefined): string {
  if (status === 'accepted') return t('autonomousHistory.reviewAccepted');
  if (status === 'rejected') return t('autonomousHistory.reviewRejected');
  return t('autonomousHistory.reviewUnreviewed');
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
  // Fetches the full run detail from /autonomous-runs/{run_id} and writes
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

async function handleDelete(runId: string): Promise<void> {
  deletingRunId.value = runId;
  try {
    await deleteAutonomousRun(runId);
    message.success(t('autonomousHistory.deleteSuccess'));
    await loadRuns(cursorStack.value.length ? cursorStack.value[cursorStack.value.length - 1] : null);
  } catch (err) {
    message.error((err as Error).message || t('autonomousHistory.deleteFailed'));
  } finally {
    deletingRunId.value = null;
  }
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
