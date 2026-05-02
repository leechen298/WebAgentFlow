<template>
  <div class="learned-path-catalog">
    <a-card :bordered="false">
      <template #title>
        <div class="catalog-header">
          <div class="catalog-title-group">
            <span class="catalog-title">{{ $t('learnedPaths.title') }}</span>
            <span class="catalog-subtitle">{{ $t('learnedPaths.subtitle') }}</span>
          </div>
          <a-space>
            <a-select
              v-model:value="trustFilter"
              style="width: 160px"
              size="small"
              :options="trustOptions"
              @change="onTrustFilterChange"
            />
            <a-button size="small" @click="loadFirstPage">
              {{ $t('common.refresh') }}
            </a-button>
          </a-space>
        </div>
      </template>

      <a-table
        :columns="columns"
        :data-source="paths"
        :pagination="false"
        :loading="loading"
        row-key="id"
        size="middle"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'scenario'">
            {{ record.scenario }}
          </template>
          <template v-else-if="column.key === 'page_template'">
            {{ record.page_template }}
          </template>
          <template v-else-if="column.key === 'trust'">
            <a-tag :color="trustColor(record.trust)">
              {{ $t(trustI18nKey(record.trust)) }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'source_run_id'">
            <router-link
              v-if="record.source_run_id"
              :to="`/exploration/autonomous/history/${record.source_run_id}`"
            >
              <code class="run-id">{{ record.source_run_id.slice(0, 8) }}</code>
            </router-link>
            <span v-else class="muted">—</span>
          </template>
          <template v-else-if="column.key === 'created_at'">
            {{ formatDate(record.created_at) }}
          </template>
          <template v-else-if="column.key === 'updated_at'">
            {{ formatDate(record.updated_at) }}
          </template>
          <template v-else-if="column.key === 'actions'">
            <a-space :size="4">
              <a-button size="small" @click="openActionsDrawer(record.id)">
                {{ $t('learnedPaths.viewActions') }}
              </a-button>
              <a-popconfirm
                v-if="canConfirm(record.trust)"
                :title="$t('learnedPaths.confirmPathPrompt')"
                :ok-text="$t('learnedPaths.confirmPath')"
                :cancel-text="$t('common.cancel')"
                @confirm="updateTrust(record.id, 'confirmed')"
              >
                <a-button
                  size="small"
                  type="primary"
                  :loading="updatingId === record.id && pendingStatus === 'confirmed'"
                >
                  {{ $t('learnedPaths.confirmPath') }}
                </a-button>
              </a-popconfirm>
              <a-button
                v-else
                size="small"
                type="primary"
                disabled
              >
                {{ $t('learnedPaths.confirmPath') }}
              </a-button>
              <a-popconfirm
                v-if="canMarkFlaky(record.trust)"
                :title="$t('learnedPaths.markFlakyPrompt')"
                :ok-text="$t('learnedPaths.markFlaky')"
                :cancel-text="$t('common.cancel')"
                @confirm="updateTrust(record.id, 'flaky')"
              >
                <a-button
                  size="small"
                  :loading="updatingId === record.id && pendingStatus === 'flaky'"
                >
                  {{ $t('learnedPaths.markFlaky') }}
                </a-button>
              </a-popconfirm>
              <a-button
                v-else
                size="small"
                disabled
              >
                {{ $t('learnedPaths.markFlaky') }}
              </a-button>
              <a-popconfirm
                v-if="canDeprecate(record.trust)"
                :title="$t('learnedPaths.deprecatePathPrompt')"
                :ok-text="$t('learnedPaths.deprecatePath')"
                :cancel-text="$t('common.cancel')"
                @confirm="updateTrust(record.id, 'deprecated')"
              >
                <a-button
                  size="small"
                  danger
                  :loading="updatingId === record.id && pendingStatus === 'deprecated'"
                >
                  {{ $t('learnedPaths.deprecatePath') }}
                </a-button>
              </a-popconfirm>
              <a-button
                v-else
                size="small"
                danger
                disabled
              >
                {{ $t('learnedPaths.deprecatePath') }}
              </a-button>
            </a-space>
          </template>
        </template>

        <template #emptyText>
          <a-empty :description="$t('learnedPaths.empty')" />
        </template>
      </a-table>

      <div v-if="paths.length > 0" class="pagination-bar">
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
      :title="$t('learnedPaths.actions')"
      width="560"
    >
      <a-spin :spinning="drawerLoading">
        <a-alert
          v-if="drawerError"
          type="error"
          show-icon
          :message="$t('learnedPaths.loadFailed')"
          :description="drawerError"
        />
        <div v-else-if="selectedPath">
          <a-descriptions :column="1" size="small" bordered>
            <a-descriptions-item :label="$t('common.id')">
              <code>{{ selectedPath.id }}</code>
            </a-descriptions-item>
            <a-descriptions-item :label="$t('learnedPaths.scenario')">
              {{ selectedPath.scenario }}
            </a-descriptions-item>
            <a-descriptions-item :label="$t('learnedPaths.pageTemplate')">
              {{ selectedPath.page_template }}
            </a-descriptions-item>
            <a-descriptions-item :label="$t('learnedPaths.trust')">
              <a-tag :color="trustColor(selectedPath.trust)">
                {{ $t(trustI18nKey(selectedPath.trust)) }}
              </a-tag>
            </a-descriptions-item>
            <a-descriptions-item :label="$t('learnedPaths.hitCount')">
              {{ selectedPath.hit_count }}
            </a-descriptions-item>
            <a-descriptions-item :label="$t('learnedPaths.sourceRun')">
              <router-link
                v-if="selectedPath.source_run_id"
                :to="`/exploration/autonomous/history/${selectedPath.source_run_id}`"
              >
                <code>{{ selectedPath.source_run_id }}</code>
              </router-link>
              <span v-else>—</span>
            </a-descriptions-item>
          </a-descriptions>

          <div class="actions-section">
            <h4>{{ $t('learnedPaths.actions') }}</h4>
            <a-empty v-if="!selectedPath.actions || selectedPath.actions.length === 0" :description="$t('learnedPaths.noActions')" />
            <a-timeline v-else>
              <a-timeline-item v-for="(action, idx) in selectedPath.actions" :key="idx">
                <div class="action-step">
                  <strong>Step {{ idx + 1 }}</strong>
                  <pre class="action-json">{{ JSON.stringify(action, null, 2) }}</pre>
                </div>
              </a-timeline-item>
            </a-timeline>
          </div>
        </div>
      </a-spin>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { message } from 'ant-design-vue';
import {
  listLearnedPaths,
  getLearnedPath,
  patchLearnedPathTrust,
  type LearnedPathSummary,
  type LearnedPathDetail,
  type LearnedPathTrust,
  type LearnedPathPatchStatus,
} from '@/api/exploration';

const { t } = useI18n();

const paths = ref<LearnedPathSummary[]>([]);
const loading = ref(false);
const hasNext = ref(false);
const nextCursor = ref<string | null>(null);
const cursorStack = ref<(string | null)[]>([]);

const trustFilter = ref<LearnedPathTrust | 'all'>('all');

const drawerOpen = ref(false);
const drawerLoading = ref(false);
const drawerError = ref('');
const selectedPath = ref<LearnedPathDetail | null>(null);

const updatingId = ref<string | null>(null);
const pendingStatus = ref<LearnedPathPatchStatus | null>(null);

const trustOptions = [
  { value: 'all', label: t('learnedPaths.allTrust') },
  { value: 'provisional', label: t('autonomousHistory.trustProvisional') },
  { value: 'confirmed', label: t('autonomousHistory.trustConfirmed') },
  { value: 'flaky', label: t('autonomousHistory.trustFlaky') },
  { value: 'deprecated', label: t('autonomousHistory.trustDeprecated') },
];

const columns = [
  { key: 'scenario', dataIndex: 'scenario', title: t('learnedPaths.scenario'), width: 180 },
  { key: 'page_template', dataIndex: 'page_template', title: t('learnedPaths.pageTemplate'), width: 180 },
  { key: 'trust', dataIndex: 'trust', title: t('learnedPaths.trust'), width: 120 },
  { key: 'hit_count', dataIndex: 'hit_count', title: t('learnedPaths.hitCount'), width: 100 },
  { key: 'source_run_id', dataIndex: 'source_run_id', title: t('learnedPaths.sourceRun'), width: 140 },
  { key: 'created_at', dataIndex: 'created_at', title: t('learnedPaths.createdAt'), width: 180 },
  { key: 'updated_at', dataIndex: 'updated_at', title: t('learnedPaths.updatedAt'), width: 180 },
  { key: 'actions', title: t('common.actions'), width: 360, fixed: 'right' as const },
];

function trustColor(trust: LearnedPathTrust): string {
  switch (trust) {
    case 'confirmed':
      return 'green';
    case 'deprecated':
      return 'red';
    case 'flaky':
      return 'orange';
    default:
      return 'blue';
  }
}

function trustI18nKey(trust: LearnedPathTrust): string {
  switch (trust) {
    case 'confirmed':
      return 'autonomousHistory.trustConfirmed';
    case 'flaky':
      return 'autonomousHistory.trustFlaky';
    case 'deprecated':
      return 'autonomousHistory.trustDeprecated';
    default:
      return 'autonomousHistory.trustProvisional';
  }
}

function canConfirm(trust: LearnedPathTrust): boolean {
  return trust !== 'confirmed';
}

function canMarkFlaky(trust: LearnedPathTrust): boolean {
  return trust !== 'flaky';
}

function canDeprecate(trust: LearnedPathTrust): boolean {
  return trust !== 'deprecated';
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

async function loadPaths(cursor: string | null): Promise<void> {
  loading.value = true;
  try {
    const page = await listLearnedPaths({
      limit: 20,
      cursor,
      trust: trustFilter.value === 'all' ? null : trustFilter.value,
    });
    paths.value = page.items;
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
  await loadPaths(null);
}

async function loadNextPage(): Promise<void> {
  if (!nextCursor.value) return;
  cursorStack.value.push(nextCursor.value);
  await loadPaths(nextCursor.value);
}

function onTrustFilterChange(): void {
  void loadFirstPage();
}

async function openActionsDrawer(pathId: string): Promise<void> {
  drawerOpen.value = true;
  drawerLoading.value = true;
  drawerError.value = '';
  selectedPath.value = null;
  try {
    selectedPath.value = await getLearnedPath(pathId);
  } catch (err) {
    drawerError.value = (err as Error).message || String(err);
  } finally {
    drawerLoading.value = false;
  }
}

async function updateTrust(pathId: string, status: LearnedPathPatchStatus): Promise<void> {
  if (updatingId.value) return;
  updatingId.value = pathId;
  pendingStatus.value = status;
  try {
    const updated = await patchLearnedPathTrust(pathId, { status });
    const idx = paths.value.findIndex((p) => p.id === pathId);
    if (idx !== -1) {
      paths.value[idx] = { ...paths.value[idx], trust: updated.trust };
    }
    if (selectedPath.value && selectedPath.value.id === pathId) {
      selectedPath.value = { ...selectedPath.value, trust: updated.trust };
    }
    message.success(t('learnedPaths.pathUpdated'));
  } catch (err) {
    message.error((err as Error).message || String(err));
  } finally {
    updatingId.value = null;
    pendingStatus.value = null;
  }
}

onMounted(() => {
  void loadFirstPage();
});
</script>

<style scoped>
.learned-path-catalog {
  padding-bottom: 40px;
}

.catalog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.catalog-title-group {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.catalog-title {
  font-weight: 600;
  font-size: 16px;
}

.catalog-subtitle {
  font-size: 12px;
  color: #888;
}

.run-id {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  color: #595959;
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

.actions-section {
  margin-top: 16px;
}

.actions-section h4 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
}

.action-step {
  margin-bottom: 8px;
}

.action-json {
  font-size: 11px;
  background: #fafafa;
  padding: 8px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 4px 0 0;
}
</style>
