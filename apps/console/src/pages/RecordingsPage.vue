<template>
  <div>
    <a-card :bordered="false">
      <template #title>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>{{ $t('recordings.title') }}</span>
          <a-button type="primary" @click="showCreateModal">
            <template #icon><plus-outlined /></template>
            {{ $t('recordings.new') }}
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
                  {{ $t('common.view') }}
                </a-button>
                <a-button type="link" size="small" @click="editRecording(record)">
                  {{ $t('common.edit') }}
                </a-button>
                <a-popconfirm
                  :title="$t('recordings.deleteConfirm')"
                  :ok-text="$t('common.yes')"
                  :cancel-text="$t('common.no')"
                  @confirm="deleteRecording(record.id)"
                >
                  <a-button type="link" size="small" danger>
                    {{ $t('common.delete') }}
                  </a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>

          <template #emptyText>
            <a-empty :description="$t('recordings.empty')">
              <a-button type="primary" @click="showCreateModal">
                <template #icon><plus-outlined /></template>
                {{ $t('recordings.createTitle') }}
              </a-button>
            </a-empty>
          </template>
        </a-table>

        <div v-if="recordings.length > 0" style="display: flex; justify-content: flex-end; margin-top: 16px; gap: 8px">
          <a-button size="small" :disabled="!recordingsStore.hasPrev" @click="goFirstPage">{{ $t('common.first') }}</a-button>
          <a-button size="small" :disabled="!recordingsStore.hasPrev" @click="goPrevPage">{{ $t('common.prev') }}</a-button>
          <a-button size="small" :disabled="!recordingsStore.hasNext" @click="goNextPage">{{ $t('common.next') }}</a-button>
        </div>
      </a-spin>
    </a-card>

    <!-- Create/Edit Modal -->
    <a-modal
      v-model:open="modalOpen"
      :title="isEditing ? $t('recordings.editTitle') : $t('recordings.createTitle')"
      :ok-text="$t('common.save')"
      :cancel-text="$t('common.cancel')"
      :confirm-loading="loading"
      @ok="handleSave"
    >
      <a-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        layout="vertical"
      >
        <a-form-item :label="$t('common.name')" name="name">
          <a-input v-model:value="formData.name" :placeholder="$t('recordings.enterName')" />
        </a-form-item>
        <a-form-item :label="$t('common.status')" name="status">
          <a-select v-model:value="formData.status" style="width: 100%">
            <a-select-option value="draft">{{ $t('status.draft') }}</a-select-option>
            <a-select-option value="active">{{ $t('status.active') }}</a-select-option>
            <a-select-option value="archived">{{ $t('status.archived') }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item :label="$t('common.source')" name="source">
          <a-input v-model:value="formData.source" :placeholder="$t('recordings.enterSource')" />
        </a-form-item>
        <a-form-item :label="$t('recordings.eventsJson')" name="events">
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
        <a-form-item :label="$t('recordings.metaJson')" name="meta">
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
import { useI18n } from 'vue-i18n';
import { message, type FormInstance } from 'ant-design-vue';
import { PlusOutlined } from '@ant-design/icons-vue';
import { useRecordingsStore } from '@/stores';
import { safeParseJson, formatJsonString } from '@/utils';
import type { Recording, RecordingCreate, RecordingUpdate, RecordingStatus } from '@web-agent-flow/shared-types';

const { t } = useI18n();
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

const rules = computed(() => ({
  name: [{ required: true, message: t('common.nameRequired') }],
  source: [{ required: true, message: t('recordings.sourceRequired') }],
}));

const columns = computed(() => [
  { title: t('common.name'), dataIndex: 'name', key: 'name' },
  { title: t('common.status'), dataIndex: 'status', key: 'status', width: 120 },
  { title: t('common.source'), dataIndex: 'source', key: 'source', width: 150 },
  { title: t('common.createdAt'), dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: t('common.actions'), key: 'actions', width: 200, fixed: 'right' as const },
]);

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
    await recordingsStore.fetchFirstPage();
    recordings.value = recordingsStore.recordings;
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('recordings.loadFailed'));
  }
}

async function goNextPage(): Promise<void> {
  try {
    await recordingsStore.fetchNextPage();
    recordings.value = recordingsStore.recordings;
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('recordings.loadFailed'));
  }
}

async function goPrevPage(): Promise<void> {
  try {
    await recordingsStore.fetchPrevPage();
    recordings.value = recordingsStore.recordings;
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('recordings.loadFailed'));
  }
}

async function goFirstPage(): Promise<void> {
  await fetchRecordings();
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

    const eventsResult = safeParseJson(formData.eventsStr, []);
    const metaResult = safeParseJson(formData.metaStr, null);

    if (isEditing.value && editingId.value) {
      const updateData: RecordingUpdate = {
        name: formData.name,
        status: formData.status,
        source: formData.source,
        events: eventsResult.success ? eventsResult.data as Array<Record<string, unknown>> : undefined,
        meta: metaResult.success ? (metaResult.data as Record<string, unknown>) : null
      };
      await recordingsStore.updateRecording(editingId.value, updateData);
      message.success(t('recordings.updated'));
    } else {
      const createData: RecordingCreate = {
        name: formData.name,
        status: formData.status,
        source: formData.source,
        events: eventsResult.success ? eventsResult.data as Array<Record<string, unknown>> : [],
        meta: metaResult.success ? (metaResult.data as Record<string, unknown>) : null
      };
      await recordingsStore.createRecording(createData);
      message.success(t('recordings.created'));
    }

    modalOpen.value = false;
    await fetchRecordings();
  } catch (e) {
    if (e instanceof Error && e.message !== 'Validation failed') {
      message.error(e.message);
    }
  }
}

async function deleteRecording(id: string): Promise<void> {
  try {
    await recordingsStore.deleteRecording(id);
    message.success(t('recordings.deleted'));
    await fetchRecordings();
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('recordings.deleteFailed'));
  }
}

function viewDetail(id: string): void {
  void router.push(`/recordings/${id}`);
}

onMounted(() => {
  void fetchRecordings();
});
</script>
