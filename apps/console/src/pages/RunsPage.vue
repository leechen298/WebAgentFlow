<template>
  <div>
    <a-card :bordered="false">
      <template #title>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>Runs</span>
          <a-button type="primary" @click="showCreateModal">
            <template #icon><plus-outlined /></template>
            New Run
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
                  View
                </a-button>
                <a-button type="link" size="small" @click="editRun(record)">
                  Edit
                </a-button>
                <a-popconfirm
                  title="Delete this run?"
                  ok-text="Yes"
                  cancel-text="No"
                  @confirm="deleteRun(record.id)"
                >
                  <a-button type="link" size="small" danger>
                    Delete
                  </a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>

          <template #emptyText>
            <a-empty description="No runs yet">
              <a-button type="primary" @click="showCreateModal">
                <template #icon><plus-outlined /></template>
                Create Run
              </a-button>
            </a-empty>
          </template>
        </a-table>
      </a-spin>
    </a-card>

    <!-- Create/Edit Modal -->
    <a-modal
      v-model:open="modalOpen"
      :title="isEditing ? 'Edit Run' : 'Create Run'"
      ok-text="Save"
      cancel-text="Cancel"
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
        <a-form-item label="Skill ID" name="skill_id">
          <a-input v-model:value="formData.skill_id" placeholder="Enter skill ID" />
        </a-form-item>
        <a-form-item label="Status" name="status">
          <a-select v-model:value="formData.status" style="width: 100%">
            <a-select-option value="pending">Pending</a-select-option>
            <a-select-option value="queued">Queued</a-select-option>
            <a-select-option value="running">Running</a-select-option>
            <a-select-option value="succeeded">Succeeded</a-select-option>
            <a-select-option value="failed">Failed</a-select-option>
          </a-select>
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="Started At" name="started_at">
              <a-date-picker
                v-model:value="formData.started_at"
                show-time
                style="width: 100%"
                value-format="YYYY-MM-DDTHH:mm:ss.SSSZ"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="Finished At" name="finished_at">
              <a-date-picker
                v-model:value="formData.finished_at"
                show-time
                style="width: 100%"
                value-format="YYYY-MM-DDTHH:mm:ss.SSSZ"
              />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="Input Payload (JSON)" name="input_payload">
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
        <a-form-item label="Result Payload (JSON)" name="result_payload">
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
        <a-form-item label="Logs (JSON Array)" name="logs">
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
import { message, type FormInstance } from 'ant-design-vue';
import { PlusOutlined } from '@ant-design/icons-vue';
import { useRunsStore } from '@/stores';
import { safeParseJson, formatJsonString } from '@/utils';
import type { Run, RunCreate, RunUpdate, RunStatus } from '@web-agent-flow/shared-types';
import type { Dayjs } from 'dayjs';

const router = useRouter();
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

const rules = {
  skill_id: [{ required: true, message: 'Skill ID is required' }]
};

const columns = [
  { title: 'Skill ID', dataIndex: 'skill_id', key: 'skill_id' },
  { title: 'Status', dataIndex: 'status', key: 'status', width: 120 },
  { title: 'Started At', dataIndex: 'started_at', key: 'started_at', width: 180 },
  { title: 'Finished At', dataIndex: 'finished_at', key: 'finished_at', width: 180 },
  { title: 'Created At', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: 'Actions', key: 'actions', width: 200, fixed: 'right' as const }
];

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
    await runsStore.fetchRuns();
    runs.value = runsStore.runs;
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Failed to load runs');
  }
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
      message.success('Run updated');
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
      message.success('Run created');
    }

    modalOpen.value = false;
    runs.value = runsStore.runs;
  } catch (e) {
    if (e instanceof Error && e.message !== 'Validation failed') {
      message.error(e.message);
    }
  }
}

async function deleteRun(id: string): Promise<void> {
  try {
    await runsStore.deleteRun(id);
    message.success('Run deleted');
    runs.value = runsStore.runs;
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Failed to delete run');
  }
}

function viewDetail(id: string): void {
  void router.push(`/runs/${id}`);
}

onMounted(() => {
  void fetchRuns();
});
</script>
