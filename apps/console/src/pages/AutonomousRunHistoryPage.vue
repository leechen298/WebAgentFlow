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
      :row-class-name="() => 'history-row'"
      :custom-row="(record: AutonomousRunSummary) => ({ onClick: () => openDetail(record.run_id) })"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'created_at'">
          {{ formatDate(record.created_at) }}
        </template>
        <template v-else-if="column.key === 'verdict'">
          <a-tag v-if="record.verdict" :color="verdictColor(record.verdict)">
            {{ record.verdict }}
          </a-tag>
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

  <a-drawer
    v-model:open="drawerOpen"
    :title="$t('autonomousHistory.detailTitle')"
    width="680"
    placement="right"
    :destroy-on-close="true"
  >
    <a-spin :spinning="detailLoading">
      <div v-if="detail" class="detail">
        <a-descriptions :column="1" size="small" bordered>
          <a-descriptions-item :label="$t('autonomousHistory.colRunId')">
            <code>{{ detail.run_id }}</code>
          </a-descriptions-item>
          <a-descriptions-item :label="$t('autonomousHistory.colCreated')">
            {{ formatDate(detail.created_at) }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('autonomousHistory.colStatus')">
            <a-tag :color="statusColor(detail.status)">{{ detail.status }}</a-tag>
          </a-descriptions-item>
          <a-descriptions-item
            v-if="detail.summary"
            :label="$t('autonomousHistory.colSummary')"
          >
            {{ detail.summary }}
          </a-descriptions-item>
        </a-descriptions>

        <h4 class="section-heading">{{ $t('autonomousHistory.strategyHeading') }}</h4>
        <pre class="json-block">{{ formatJson(detail.strategy) }}</pre>

        <h4 class="section-heading">{{ $t('autonomousHistory.resultHeading') }}</h4>
        <pre v-if="detail.result" class="json-block">{{ formatJson(detail.result) }}</pre>
        <a-empty v-else :description="$t('autonomousHistory.noResult')" />
      </div>
    </a-spin>
  </a-drawer>
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
  type AutonomousRunDetail,
} from '@/api/exploration';

const { t } = useI18n();
const router = useRouter();

const runs = ref<AutonomousRunSummary[]>([]);
const loading = ref(false);
const hasNext = ref(false);
const nextCursor = ref<string | null>(null);
const cursorStack = ref<(string | null)[]>([]); // tracks previous cursors for "first" reset

const drawerOpen = ref(false);
const detailLoading = ref(false);
const detail = ref<AutonomousRunDetail | null>(null);

const columns = [
  { key: 'created_at', dataIndex: 'created_at', title: t('autonomousHistory.colCreated'), width: 180 },
  { key: 'spec_id', dataIndex: 'spec_id', title: t('autonomousHistory.colSpec'), width: 160 },
  { key: 'scenario', dataIndex: 'scenario', title: t('autonomousHistory.colScenario'), width: 160 },
  { key: 'verdict', dataIndex: 'verdict', title: t('autonomousHistory.colVerdict'), width: 120 },
  { key: 'status', dataIndex: 'status', title: t('autonomousHistory.colStatus'), width: 110 },
  { key: 'url', dataIndex: 'url', title: 'URL', ellipsis: true },
  { key: 'run_id', dataIndex: 'run_id', title: t('autonomousHistory.colRunId'), width: 100 },
];

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function formatJson(obj: unknown): string {
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
}

function verdictColor(verdict: string): string {
  if (verdict === 'success') return 'green';
  if (verdict === 'incomplete' || verdict === 'no_progress') return 'orange';
  if (verdict === 'uncertain') return 'default';
  return 'blue';
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

async function openDetail(runId: string): Promise<void> {
  drawerOpen.value = true;
  detailLoading.value = true;
  detail.value = null;
  try {
    detail.value = await getAutonomousRun(runId);
  } catch (err) {
    message.error((err as Error).message || t('error.network'));
  } finally {
    detailLoading.value = false;
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

:deep(.history-row) {
  cursor: pointer;
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

.detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.section-heading {
  margin: 8px 0 4px;
  font-size: 13px;
  color: #595959;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.json-block {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  padding: 12px;
  font-size: 12px;
  max-height: 360px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
