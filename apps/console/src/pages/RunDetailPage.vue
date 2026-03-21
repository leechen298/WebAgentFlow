<template>
  <div>
    <a-page-header
      title="Run Detail"
      @back="goBack"
    >
      <template #extra>
        <a-space>
          <a-button @click="showEditModal">
            <template #icon><edit-outlined /></template>
            Edit
          </a-button>
          <a-popconfirm
            title="Delete this run?"
            ok-text="Yes"
            cancel-text="No"
            @confirm="handleDelete"
          >
            <a-button danger>
              <template #icon><delete-outlined /></template>
              Delete
            </a-button>
          </a-popconfirm>
        </a-space>
      </template>
    </a-page-header>

    <a-spin :spinning="loading">
      <a-alert
        v-if="error"
        message="Error"
        :description="error"
        type="error"
        show-icon
        style="margin-bottom: 16px"
      />

      <a-card v-if="run" :bordered="false" style="margin-top: 16px">
        <a-descriptions :column="2" bordered>
          <a-descriptions-item label="ID">
            {{ run.id }}
          </a-descriptions-item>
          <a-descriptions-item label="Skill ID">
            {{ run.skill_id }}
          </a-descriptions-item>
          <a-descriptions-item label="Status">
            <a-tag :color="getStatusColor(run.status)">
              {{ run.status }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="Created At">
            {{ formatDate(run.created_at) }}
          </a-descriptions-item>
          <a-descriptions-item label="Started At">
            {{ run.started_at ? formatDate(run.started_at) : '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="Finished At">
            {{ run.finished_at ? formatDate(run.finished_at) : '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="Input Payload" :span="2">
            <a-textarea
              :value="formatJsonString(run.input_payload)"
              :rows="4"
              readonly
            />
          </a-descriptions-item>
          <a-descriptions-item label="Result Payload" :span="2">
            <a-textarea
              :value="formatJsonString(run.result_payload)"
              :rows="4"
              readonly
            />
          </a-descriptions-item>
          <a-descriptions-item label="Logs" :span="2">
            <a-textarea
              :value="formatJsonString(run.logs)"
              :rows="4"
              readonly
            />
          </a-descriptions-item>
        </a-descriptions>
      </a-card>
    </a-spin>

    <!-- Edit Modal -->
    <a-modal
      v-model:open="editModalOpen"
      title="Edit Run"
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
          <a-input v-model:value="formData.skill_id" />
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
                allow-clear
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
                allow-clear
              />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="Input Payload (JSON)" name="input_payload">
          <a-textarea
            v-model:value="formData.inputPayloadStr"
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
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { message, type FormInstance } from 'ant-design-vue';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons-vue';
import { useRunsStore } from '@/stores';
import { safeParseJson, formatJsonString } from '@/utils';
import type { Run, RunUpdate, RunStatus } from '@web-agent-flow/shared-types';

const route = useRoute();
const router = useRouter();
const runsStore = useRunsStore();

const formRef = ref<FormInstance>();
const editModalOpen = ref(false);

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

const run = computed(() => runsStore.currentRun);
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

async function fetchRun(): Promise<void> {
  const id = route.params.id as string;
  if (!id) return;

  try {
    await runsStore.fetchRun(id);
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Failed to load run');
  }
}

function showEditModal(): void {
  if (!run.value) return;

  formData.skill_id = run.value.skill_id;
  formData.status = run.value.status;
  formData.started_at = run.value.started_at || undefined;
  formData.finished_at = run.value.finished_at || undefined;
  formData.inputPayloadStr = formatJsonString(run.value.input_payload);
  formData.resultPayloadStr = formatJsonString(run.value.result_payload);
  formData.logsStr = formatJsonString(run.value.logs);
  formErrors.input_payload = '';
  formErrors.result_payload = '';
  formErrors.logs = '';
  editModalOpen.value = true;
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

    const inputResult = safeParseJson(formData.inputPayloadStr);
    const resultResult = safeParseJson(formData.resultPayloadStr);
    const logsResult = safeParseJson(formData.logsStr);

    const updateData: RunUpdate = {
      skill_id: formData.skill_id,
      status: formData.status,
      started_at: formData.started_at || null,
      finished_at: formData.finished_at || null,
      input_payload: inputResult.success ? inputResult.data as Record<string, unknown> : undefined,
      result_payload: resultResult.success ? resultResult.data as Record<string, unknown> : null,
      logs: logsResult.success ? logsResult.data as Array<Record<string, unknown>> : null
    };

    await runsStore.updateRun(route.params.id as string, updateData);
    message.success('Run updated');
    editModalOpen.value = false;
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Failed to update run');
  }
}

async function handleDelete(): Promise<void> {
  try {
    await runsStore.deleteRun(route.params.id as string);
    message.success('Run deleted');
    goBack();
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Failed to delete run');
  }
}

function goBack(): void {
  void router.push('/runs');
}

onMounted(() => {
  void fetchRun();
});

onUnmounted(() => {
  runsStore.clearCurrent();
});
</script>
