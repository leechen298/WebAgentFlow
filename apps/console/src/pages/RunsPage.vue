<template>
  <div>
    <a-card :bordered="false">
      <template #title>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>{{ $t('runs.title') }}</span>
          <a-button type="primary" @click="showCreateModal">
            <template #icon><plus-outlined /></template>
            {{ $t('runs.new') }}
          </a-button>
        </div>
      </template>

      <a-spin :spinning="loadingList">
        <a-table
          :columns="columns"
          :data-source="runs"
          :pagination="false"
          :loading="loadingList"
          row-key="id"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'">
              <a-tag :color="getStatusColor(record.status)">
                {{ record.status }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'started_at'">
              {{ record.started_at ? formatDate(record.started_at) : '-' }}
            </template>
            <template v-else-if="column.key === 'finished_at'">
              {{ record.finished_at ? formatDate(record.finished_at) : '-' }}
            </template>
            <template v-else-if="column.key === 'created_at'">
              {{ formatDate(record.created_at) }}
            </template>
            <template v-else-if="column.key === 'actions'">
              <a-space>
                <a-button type="link" size="small" @click="viewDetail(record.id)">
                  {{ $t('common.view') }}
                </a-button>
                <a-button type="link" size="small" @click="editRun(record)">
                  {{ $t('common.edit') }}
                </a-button>
                <a-popconfirm
                  :title="$t('runs.deleteConfirm')"
                  :ok-text="$t('common.yes')"
                  :cancel-text="$t('common.no')"
                  @confirm="deleteRun(record.id)"
                >
                  <a-button type="link" size="small" danger>
                    {{ $t('common.delete') }}
                  </a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>

          <template #emptyText>
            <a-empty :description="$t('runs.empty')">
              <a-button type="primary" @click="showCreateModal">
                <template #icon><plus-outlined /></template>
                {{ $t('runs.createTitle') }}
              </a-button>
            </a-empty>
          </template>
        </a-table>

        <div v-if="runs.length > 0" style="display: flex; justify-content: flex-end; margin-top: 16px; gap: 8px">
          <a-button size="small" :disabled="!runsStore.hasPrev" @click="goFirstPage">{{ $t('common.first') }}</a-button>
          <a-button size="small" :disabled="!runsStore.hasPrev" @click="goPrevPage">{{ $t('common.prev') }}</a-button>
          <a-button size="small" :disabled="!runsStore.hasNext" @click="goNextPage">{{ $t('common.next') }}</a-button>
        </div>
      </a-spin>
    </a-card>

    <!-- Create/Edit Modal -->
    <a-modal
      v-model:open="modalOpen"
      :title="isEditing ? $t('runs.editTitle') : $t('runs.createTitle')"
      :ok-text="$t('common.save')"
      :cancel-text="$t('common.cancel')"
      :confirm-loading="loading"
      @ok="handleSave"
      width="600px"
    >
      <a-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        layout="vertical"
      >
        <a-form-item :label="$t('runs.skillId')" name="skill_id">
          <a-input v-model:value="formData.skill_id" :placeholder="$t('runs.enterSkillId')" />
        </a-form-item>
        <a-form-item :label="$t('common.status')" name="status">
          <a-select v-model:value="formData.status" style="width: 100%">
            <a-select-option value="pending">{{ $t('status.pending') }}</a-select-option>
            <a-select-option value="queued">{{ $t('status.queued') }}</a-select-option>
            <a-select-option value="running">{{ $t('status.running') }}</a-select-option>
            <a-select-option value="succeeded">{{ $t('status.succeeded') }}</a-select-option>
            <a-select-option value="failed">{{ $t('status.failed') }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item :label="$t('common.startedAt')" name="started_at">
              <a-date-picker
                v-model:value="formData.started_at"
                show-time
                style="width: 100%"
                value-format="YYYY-MM-DDTHH:mm:ss.SSSZ"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item :label="$t('common.finishedAt')" name="finished_at">
              <a-date-picker
                v-model:value="formData.finished_at"
                show-time
                style="width: 100%"
                value-format="YYYY-MM-DDTHH:mm:ss.SSSZ"
              />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item :label="$t('runs.inputPayloadJson')" name="input_payload">
          <a-textarea
            v-model:value="formData.inputPayloadStr"
            placeholder='{}'
            :rows="3"
            @blur="validateJson('input_payload')"
          />
          <div v-if="formErrors.input_payload" style="color: #ff4d4f; font-size: 12px; margin-top: 4px">
            {{ formErrors.input_payload }}
          </div>
        </a-form-item>
        <a-form-item :label="$t('runs.resultPayloadJson')" name="result_payload">
          <a-textarea
            v-model:value="formData.resultPayloadStr"
            placeholder='{}'
            :rows="3"
            @blur="validateJson('result_payload')"
          />
          <div v-if="formErrors.result_payload" style="color: #ff4d4f; font-size: 12px; margin-top: 4px">
            {{ formErrors.result_payload }}
          </div>
        </a-form-item>
        <a-form-item :label="$t('runs.logsJsonArray')" name="logs">
          <a-textarea
            v-model:value="formData.logsStr"
            placeholder='[]'
            :rows="3"
            @blur="validateJson('logs')"
          />
          <div v-if="formErrors.logs" style="color: #ff4d4f; font-size: 12px; margin-top: 4px">
            {{ formErrors.logs }}
          </div>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { message, type FormInstance } from 'ant-design-vue';
import { PlusOutlined } from '@ant-design/icons-vue';
import { useRunsStore } from '@/stores';
import { safeParseJson, formatJsonString } from '@/utils';
import type { Run, RunCreate, RunUpdate, RunStatus } from '@web-agent-flow/shared-types';
import type { Dayjs } from 'dayjs';

const router = useRouter();
const { t } = useI18n();
const runsStore = useRunsStore();

const formRef = ref<FormInstance>();
const modalOpen = ref(false);
const isEditing = ref(false);
const editingId = ref<string | null>(null);

const formData = reactive({
  skill_id: '',
  status: 'pending' as RunStatus,
  started_at: undefined as string | undefined,
  finished_at: undefined as string | undefined,
  inputPayloadStr: '{}',
  resultPayloadStr: '',
  logsStr: ''
});

const formErrors = reactive({
  input_payload: '',
  result_payload: '',
  logs: ''
});

const rules = computed(() => ({
  skill_id: [{ required: true, message: t('runs.skillIdRequired') }]
}));

const columns = computed(() => [
  { title: t('runs.skillId'), dataIndex: 'skill_id', key: 'skill_id' },
  { title: t('common.status'), dataIndex: 'status', key: 'status', width: 120 },
  { title: t('common.startedAt'), dataIndex: 'started_at', key: 'started_at', width: 180 },
  { title: t('common.finishedAt'), dataIndex: 'finished_at', key: 'finished_at', width: 180 },
  { title: t('common.createdAt'), dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: t('common.actions'), key: 'actions', width: 200, fixed: 'right' as const }
]);

const runs = ref<Run[]>([]);
const loadingList = computed(() => runsStore.loadingList);
const loading = computed(() => runsStore.loading);
const error = computed(() => runsStore.error);

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: 'default',
    queued: 'blue',
    running: 'processing',
    succeeded: 'success',
    failed: 'error'
  };
  return colors[status] || 'default';
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

async function fetchRuns(): Promise<void> {
  try {
    await runsStore.fetchFirstPage();
    runs.value = runsStore.runs;
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('runs.loadFailed'));
  }
}

async function goNextPage(): Promise<void> {
  try {
    await runsStore.fetchNextPage();
    runs.value = runsStore.runs;
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('runs.loadFailed'));
  }
}

async function goPrevPage(): Promise<void> {
  try {
    await runsStore.fetchPrevPage();
    runs.value = runsStore.runs;
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('runs.loadFailed'));
  }
}

async function goFirstPage(): Promise<void> {
  await fetchRuns();
}

function showCreateModal(): void {
  isEditing.value = false;
  editingId.value = null;
  resetForm();
  modalOpen.value = true;
}

function editRun(record: Run): void {
  isEditing.value = true;
  editingId.value = record.id;
  formData.skill_id = record.skill_id;
  formData.status = record.status;
  formData.started_at = record.started_at || undefined;
  formData.finished_at = record.finished_at || undefined;
  formData.inputPayloadStr = formatJsonString(record.input_payload);
  formData.resultPayloadStr = formatJsonString(record.result_payload);
  formData.logsStr = formatJsonString(record.logs);
  formErrors.input_payload = '';
  formErrors.result_payload = '';
  formErrors.logs = '';
  modalOpen.value = true;
}

function resetForm(): void {
  formData.skill_id = '';
  formData.status = 'pending';
  formData.started_at = undefined;
  formData.finished_at = undefined;
  formData.inputPayloadStr = '{}';
  formData.resultPayloadStr = '';
  formData.logsStr = '';
  formErrors.input_payload = '';
  formErrors.result_payload = '';
  formErrors.logs = '';
}

function validateJson(field: 'input_payload' | 'result_payload' | 'logs'): boolean {
  let str: string;
  switch (field) {
    case 'input_payload':
      str = formData.inputPayloadStr;
      break;
    case 'result_payload':
      str = formData.resultPayloadStr;
      break;
    case 'logs':
      str = formData.logsStr;
      break;
  }

  if (!str.trim()) {
    formErrors[field] = '';
    return true;
  }
  const result = safeParseJson(str);
  if (!result.success) {
    formErrors[field] = result.error;
    return false;
  }
  formErrors[field] = '';
  return true;
}

async function handleSave(): Promise<void> {
  try {
    await formRef.value?.validate();

    if (!validateJson('input_payload') || !validateJson('result_payload') || !validateJson('logs')) {
      return;
    }

    const inputResult = safeParseJson(formData.inputPayloadStr, {});
    const resultResult = safeParseJson(formData.resultPayloadStr, null);
    const logsResult = safeParseJson(formData.logsStr, []);

    if (isEditing.value && editingId.value) {
      const updateData: RunUpdate = {
        skill_id: formData.skill_id,
        status: formData.status,
        started_at: formData.started_at || null,
        finished_at: formData.finished_at || null,
        input_payload: inputResult.success ? inputResult.data as Record<string, unknown> : undefined,
        result_payload: resultResult.success ? resultResult.data as Record<string, unknown> : null,
        logs: logsResult.success ? logsResult.data as Array<Record<string, unknown>> : null
      };
      await runsStore.updateRun(editingId.value, updateData);
      message.success(t('runs.updated'));
    } else {
      const createData: RunCreate = {
        skill_id: formData.skill_id,
        status: formData.status,
        started_at: formData.started_at || null,
        finished_at: formData.finished_at || null,
        input_payload: inputResult.success ? inputResult.data as Record<string, unknown> : {},
        result_payload: resultResult.success ? resultResult.data as Record<string, unknown> : null,
        logs: logsResult.success ? logsResult.data as Array<Record<string, unknown>> : null
      };
      await runsStore.createRun(createData);
      message.success(t('runs.created'));
    }

    modalOpen.value = false;
    await fetchRuns();
  } catch (e) {
    if (e instanceof Error && e.message !== 'Validation failed') {
      message.error(e.message);
    }
  }
}

async function deleteRun(id: string): Promise<void> {
  try {
    await runsStore.deleteRun(id);
    message.success(t('runs.deleted'));
    await fetchRuns();
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('runs.deleteFailed'));
  }
}

function viewDetail(id: string): void {
  void router.push(`/runs/${id}`);
}

onMounted(() => {
  void fetchRuns();
});
</script>
