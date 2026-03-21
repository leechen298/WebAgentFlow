<template>
  <div>
    <a-page-header
      title="Recording Detail"
      @back="goBack"
    >
      <template #extra>
        <a-space>
          <a-button @click="showEditModal">
            <template #icon><edit-outlined /></template>
            Edit
          </a-button>
          <a-popconfirm
            title="Delete this recording?"
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

      <a-card v-if="recording" :bordered="false" style="margin-top: 16px">
        <a-descriptions :column="2" bordered>
          <a-descriptions-item label="ID">
            {{ recording.id }}
          </a-descriptions-item>
          <a-descriptions-item label="Name">
            {{ recording.name }}
          </a-descriptions-item>
          <a-descriptions-item label="Status">
            <a-tag :color="getStatusColor(recording.status)">
              {{ recording.status }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="Source">
            {{ recording.source }}
          </a-descriptions-item>
          <a-descriptions-item label="Created At">
            {{ formatDate(recording.created_at) }}
          </a-descriptions-item>
          <a-descriptions-item label="Updated At">
            {{ formatDate(recording.updated_at) }}
          </a-descriptions-item>
          <a-descriptions-item label="Events" :span="2">
            <a-textarea
              :value="formatJsonString(recording.events)"
              :rows="6"
              readonly
            />
          </a-descriptions-item>
          <a-descriptions-item label="Meta" :span="2">
            <a-textarea
              :value="formatJsonString(recording.meta)"
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
      title="Edit Recording"
      ok-text="Save"
      cancel-text="Cancel"
      :confirm-loading="loading"
      @ok="handleSave"
    >
      <a-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        layout="vertical"
      >
        <a-form-item label="Name" name="name">
          <a-input v-model:value="formData.name" />
        </a-form-item>
        <a-form-item label="Status" name="status">
          <a-select v-model:value="formData.status" style="width: 100%">
            <a-select-option value="draft">Draft</a-select-option>
            <a-select-option value="active">Active</a-select-option>
            <a-select-option value="archived">Archived</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="Source" name="source">
          <a-input v-model:value="formData.source" />
        </a-form-item>
        <a-form-item label="Events (JSON)" name="events">
          <a-textarea
            v-model:value="formData.eventsStr"
            :rows="4"
            @blur="validateJson('events')"
          />
          <div v-if="formErrors.events" style="color: #ff4d4f; font-size: 12px; margin-top: 4px">
            {{ formErrors.events }}
          </div>
        </a-form-item>
        <a-form-item label="Meta (JSON)" name="meta">
          <a-textarea
            v-model:value="formData.metaStr"
            :rows="3"
            @blur="validateJson('meta')"
          />
          <div v-if="formErrors.meta" style="color: #ff4d4f; font-size: 12px; margin-top: 4px">
            {{ formErrors.meta }}
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
import { useRecordingsStore } from '@/stores';
import { safeParseJson, formatJsonString } from '@/utils';
import type { Recording, RecordingUpdate, RecordingStatus } from '@web-agent-flow/shared-types';

const route = useRoute();
const router = useRouter();
const recordingsStore = useRecordingsStore();

const formRef = ref<FormInstance>();
const editModalOpen = ref(false);

const formData = reactive({
  name: '',
  status: 'draft' as RecordingStatus,
  source: '',
  eventsStr: '[]',
  metaStr: ''
});

const formErrors = reactive({
  events: '',
  meta: ''
});

const rules = {
  name: [{ required: true, message: 'Name is required' }],
  source: [{ required: true, message: 'Source is required' }]
};

const recording = computed(() => recordingsStore.currentRecording);
const loading = computed(() => recordingsStore.loading);
const error = computed(() => recordingsStore.error);

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    draft: 'default',
    active: 'green',
    archived: 'orange'
  };
  return colors[status] || 'default';
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

async function fetchRecording(): Promise<void> {
  const id = route.params.id as string;
  if (!id) return;

  try {
    await recordingsStore.fetchRecording(id);
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Failed to load recording');
  }
}

function showEditModal(): void {
  if (!recording.value) return;

  formData.name = recording.value.name;
  formData.status = recording.value.status;
  formData.source = recording.value.source;
  formData.eventsStr = formatJsonString(recording.value.events);
  formData.metaStr = formatJsonString(recording.value.meta);
  formErrors.events = '';
  formErrors.meta = '';
  editModalOpen.value = true;
}

function validateJson(field: 'events' | 'meta'): boolean {
  const str = field === 'events' ? formData.eventsStr : formData.metaStr;
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

    if (!validateJson('events') || !validateJson('meta')) {
      return;
    }

    const eventsResult = safeParseJson(formData.eventsStr);
    const metaResult = safeParseJson(formData.metaStr);

    const updateData: RecordingUpdate = {
      name: formData.name,
      status: formData.status,
      source: formData.source,
      events: eventsResult.success ? eventsResult.data as Array<Record<string, unknown>> : undefined,
      meta: metaResult.success ? (metaResult.data as Record<string, unknown>) : null
    };

    await recordingsStore.updateRecording(route.params.id as string, updateData);
    message.success('Recording updated');
    editModalOpen.value = false;
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Failed to update recording');
  }
}

async function handleDelete(): Promise<void> {
  try {
    await recordingsStore.deleteRecording(route.params.id as string);
    message.success('Recording deleted');
    goBack();
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Failed to delete recording');
  }
}

function goBack(): void {
  void router.push('/recordings');
}

onMounted(() => {
  void fetchRecording();
});

onUnmounted(() => {
  recordingsStore.clearCurrent();
});
</script>
