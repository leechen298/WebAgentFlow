<template>
  <div>
    <a-page-header
      :title="$t('nav.runDetail')"
      @back="goBack"
    >
      <template #extra>
        <a-space>
          <a-button @click="showEditModal">
            <template #icon><edit-outlined /></template>
            {{ $t('common.edit') }}
          </a-button>
          <a-popconfirm
            :title="$t('runs.deleteConfirm')"
            :ok-text="$t('common.yes')"
            :cancel-text="$t('common.no')"
            @confirm="handleDelete"
          >
            <a-button danger>
              <template #icon><delete-outlined /></template>
              {{ $t('common.delete') }}
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
          <a-descriptions-item :label="$t('common.id')">
            {{ run.id }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('runs.skillId')">
            {{ run.skill_id }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('common.status')">
            <a-tag :color="getStatusColor(run.status)">
              {{ run.status }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item :label="$t('common.createdAt')">
            {{ formatDate(run.created_at) }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('common.startedAt')">
            {{ run.started_at ? formatDate(run.started_at) : '-' }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('common.finishedAt')">
            {{ run.finished_at ? formatDate(run.finished_at) : '-' }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('runs.inputPayloadJson')" :span="2">
            <a-textarea
              :value="formatJsonString(run.input_payload)"
              :rows="4"
              readonly
            />
          </a-descriptions-item>
          <a-descriptions-item :label="$t('runs.resultPayloadJson')" :span="2">
            <a-textarea
              :value="formatJsonString(run.result_payload)"
              :rows="4"
              readonly
            />
          </a-descriptions-item>
          <a-descriptions-item :label="$t('runs.logsJsonArray')" :span="2">
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
      :title="$t('runs.editTitle')"
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
          <a-input v-model:value="formData.skill_id" />
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
                allow-clear
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
                allow-clear
              />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item :label="$t('runs.inputPayloadJson')" name="input_payload">
          <a-textarea
            v-model:value="formData.inputPayloadStr"
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
import { useI18n } from 'vue-i18n';
import { message, type FormInstance } from 'ant-design-vue';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons-vue';
import { useRunsStore } from '@/stores';
import { safeParseJson, formatJsonString } from '@/utils';
import type { Run, RunUpdate, RunStatus } from '@web-agent-flow/shared-types';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
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

const rules = computed(() => ({
  skill_id: [{ required: true, message: t('runs.skillIdRequired') }]
}));

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
    message.error(e instanceof Error ? e.message : t('runs.loadFailed'));
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
    message.success(t('runs.updated'));
    editModalOpen.value = false;
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('runs.updateFailed'));
  }
}

async function handleDelete(): Promise<void> {
  try {
    await runsStore.deleteRun(route.params.id as string);
    message.success(t('runs.deleted'));
    goBack();
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('runs.deleteFailed'));
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
