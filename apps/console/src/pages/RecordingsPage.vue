<template>
  <div>
    <a-card :bordered="false">
      <template #title>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>Recordings</span>
          <a-button type="primary" @click="showCreateModal">
            <template #icon><plus-outlined /></template>
            New Recording
          </a-button>
        </div>
      </template>

      <a-spin :spinning="loadingList">
        <a-table
          :columns="columns"
          :data-source="recordings"
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
            <template v-else-if="column.key === 'created_at'">
              {{ formatDate(record.created_at) }}
            </template>
            <template v-else-if="column.key === 'actions'">
              <a-space>
                <a-button type="link" size="small" @click="viewDetail(record.id)">
                  View
                </a-button>
                <a-button type="link" size="small" @click="editRecording(record)">
                  Edit
                </a-button>
                <a-popconfirm
                  title="Delete this recording?"
                  ok-text="Yes"
                  cancel-text="No"
                  @confirm="deleteRecording(record.id)"
                >
                  <a-button type="link" size="small" danger>
                    Delete
                  </a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>

          <template #emptyText>
            <a-empty description="No recordings yet">
              <a-button type="primary" @click="showCreateModal">
                <template #icon><plus-outlined /></template>
                Create Recording
              </a-button>
            </a-empty>
          </template>
        </a-table>
      </a-spin>
    </a-card>

    <!-- Create/Edit Modal -->
    <a-modal
      v-model:open="modalOpen"
      :title="isEditing ? 'Edit Recording' : 'Create Recording'"
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
          <a-input v-model:value="formData.name" placeholder="Enter recording name" />
        </a-form-item>
        <a-form-item label="Status" name="status">
          <a-select v-model:value="formData.status" style="width: 100%">
            <a-select-option value="draft">Draft</a-select-option>
            <a-select-option value="active">Active</a-select-option>
            <a-select-option value="archived">Archived</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="Source" name="source">
          <a-input v-model:value="formData.source" placeholder="Enter source (e.g., extension)" />
        </a-form-item>
        <a-form-item label="Events (JSON)" name="events">
          <a-textarea
            v-model:value="formData.eventsStr"
            placeholder='[]'
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
            placeholder='{}'
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
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { message, type FormInstance } from 'ant-design-vue';
import { PlusOutlined } from '@ant-design/icons-vue';
import { useRecordingsStore } from '@/stores';
import { safeParseJson, formatJsonString } from '@/utils';
import type { Recording, RecordingCreate, RecordingUpdate, RecordingStatus } from '@web-agent-flow/shared-types';

const router = useRouter();
const recordingsStore = useRecordingsStore();

const formRef = ref<FormInstance>();
const modalOpen = ref(false);
const isEditing = ref(false);
const editingId = ref<string | null>(null);

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

const columns = [
  { title: 'Name', dataIndex: 'name', key: 'name' },
  { title: 'Status', dataIndex: 'status', key: 'status', width: 120 },
  { title: 'Source', dataIndex: 'source', key: 'source', width: 150 },
  { title: 'Created At', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: 'Actions', key: 'actions', width: 200, fixed: 'right' as const }
];

const recordings = ref<Recording[]>([]);
const loadingList = computed(() => recordingsStore.loadingList);
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

async function fetchRecordings(): Promise<void> {
  try {
    await recordingsStore.fetchRecordings();
    recordings.value = recordingsStore.recordings;
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Failed to load recordings');
  }
}

function showCreateModal(): void {
  isEditing.value = false;
  editingId.value = null;
  resetForm();
  modalOpen.value = true;
}

function editRecording(record: Recording): void {
  isEditing.value = true;
  editingId.value = record.id;
  formData.name = record.name;
  formData.status = record.status;
  formData.source = record.source;
  formData.eventsStr = formatJsonString(record.events);
  formData.metaStr = formatJsonString(record.meta);
  formErrors.events = '';
  formErrors.meta = '';
  modalOpen.value = true;
}

function resetForm(): void {
  formData.name = '';
  formData.status = 'draft';
  formData.source = '';
  formData.eventsStr = '[]';
  formData.metaStr = '';
  formErrors.events = '';
  formErrors.meta = '';
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

    if (isEditing.value && editingId.value) {
      const updateData: RecordingUpdate = {
        name: formData.name,
        status: formData.status,
        source: formData.source,
        events: eventsResult.success ? eventsResult.data as Array<Record<string, unknown>> : undefined,
        meta: metaResult.success ? (metaResult.data as Record<string, unknown>) : null
      };
      await recordingsStore.updateRecording(editingId.value, updateData);
      message.success('Recording updated');
    } else {
      const createData: RecordingCreate = {
        name: formData.name,
        status: formData.status,
        source: formData.source,
        events: eventsResult.success ? eventsResult.data as Array<Record<string, unknown>> : [],
        meta: metaResult.success ? (metaResult.data as Record<string, unknown>) : null
      };
      await recordingsStore.createRecording(createData);
      message.success('Recording created');
    }

    modalOpen.value = false;
    recordings.value = recordingsStore.recordings;
  } catch (e) {
    if (e instanceof Error && e.message !== 'Validation failed') {
      message.error(e.message);
    }
  }
}

async function deleteRecording(id: string): Promise<void> {
  try {
    await recordingsStore.deleteRecording(id);
    message.success('Recording deleted');
    recordings.value = recordingsStore.recordings;
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Failed to delete recording');
  }
}

function viewDetail(id: string): void {
  void router.push(`/recordings/${id}`);
}

onMounted(() => {
  void fetchRecordings();
});
</script>
