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
          <a-descriptions-item label="Meta" :span="2">
            <a-textarea
              :value="formatJsonString(recording.meta)"
              :rows="4"
              readonly
            />
          </a-descriptions-item>
        </a-descriptions>
      </a-card>

      <!-- Events Tabs -->
      <a-card v-if="recording" :bordered="false" style="margin-top: 16px">
        <a-tabs v-model:activeKey="activeTab" @change="handleTabChange">
          <a-tab-pane key="raw" tab="Raw Events">
            <div style="margin-bottom: 8px; color: #666; font-size: 12px">
              {{ recording.events.length }} raw events
            </div>
            <a-textarea
              :value="formatJsonString(recording.events)"
              :rows="20"
              readonly
              style="font-family: monospace; font-size: 12px"
            />
          </a-tab-pane>

          <a-tab-pane key="normalized" tab="Normalized Recording">
            <a-spin :spinning="normLoading">
              <a-alert
                v-if="normError"
                :message="normError"
                type="error"
                show-icon
                style="margin-bottom: 12px"
              />

              <div v-if="normalized">
                <!-- Summary banner -->
                <a-descriptions
                  :column="6"
                  size="small"
                  bordered
                  style="margin-bottom: 16px"
                >
                  <a-descriptions-item label="Raw events">
                    {{ normalized.summary.event_count_raw }}
                  </a-descriptions-item>
                  <a-descriptions-item label="Normalized steps">
                    {{ normalized.summary.event_count_normalized }}
                  </a-descriptions-item>
                  <a-descriptions-item label="Segments">
                    {{ normalized.summary.segment_count }}
                  </a-descriptions-item>
                  <a-descriptions-item label="Pages">
                    {{ normalized.summary.page_count }}
                  </a-descriptions-item>
                  <a-descriptions-item label="iFrame">
                    <a-tag :color="normalized.summary.contains_iframe ? 'blue' : 'default'">
                      {{ normalized.summary.contains_iframe ? 'Yes' : 'No' }}
                    </a-tag>
                  </a-descriptions-item>
                  <a-descriptions-item label="Rich text">
                    <a-tag :color="normalized.summary.contains_richtext ? 'purple' : 'default'">
                      {{ normalized.summary.contains_richtext ? 'Yes' : 'No' }}
                    </a-tag>
                  </a-descriptions-item>
                </a-descriptions>

                <!-- Key actions -->
                <a-card size="small" title="Key Actions" style="margin-bottom: 16px">
                  <div v-if="normalized.key_actions.length === 0" style="color: #999">
                    No key actions detected.
                  </div>
                  <a-list
                    v-else
                    size="small"
                    :data-source="normalized.key_actions"
                  >
                    <template #renderItem="{ item }">
                      <a-list-item>
                        <a-space wrap>
                          <a-tag :color="actionColor(item.action_type)">
                            {{ item.action_type }}
                          </a-tag>
                          <span v-if="item.field_label" style="font-weight: 500">
                            {{ item.field_label }}
                          </span>
                          <span v-if="item.button_text" style="color: #666">
                            "{{ item.button_text }}"
                          </span>
                          <span v-if="item.value" style="color: #1677ff">
                            = {{ truncate(item.value, 60) }}
                          </span>
                          <a-tag v-if="item.in_iframe" color="cyan" style="font-size: 11px">
                            iframe
                          </a-tag>
                          <a-tag v-if="item.is_richtext" color="purple" style="font-size: 11px">
                            richtext
                          </a-tag>
                        </a-space>
                      </a-list-item>
                    </template>
                  </a-list>
                </a-card>

                <!-- Segments -->
                <div v-for="seg in normalized.segments" :key="seg.index" style="margin-bottom: 12px">
                  <a-card
                    size="small"
                    :title="`[${seg.type}] ${seg.title}`"
                    :headStyle="segmentHeaderStyle(seg.type)"
                  >
                    <div v-if="seg.steps.length === 0" style="color: #999">Empty segment.</div>
                    <a-table
                      v-else
                      :columns="stepColumns"
                      :data-source="seg.steps"
                      :pagination="false"
                      size="small"
                      row-key="timestamp"
                    >
                      <template #bodyCell="{ column, record }">
                        <template v-if="column.key === 'action_type'">
                          <a-tag :color="actionColor(record.action_type)">
                            {{ record.action_type }}
                          </a-tag>
                        </template>
                        <template v-else-if="column.key === 'field_label'">
                          {{ record.field_label || record.button_text || '—' }}
                        </template>
                        <template v-else-if="column.key === 'value'">
                          {{ record.value ? truncate(record.value, 50) : '—' }}
                        </template>
                        <template v-else-if="column.key === 'flags'">
                          <a-space>
                            <a-tag v-if="record.in_iframe" color="cyan" style="font-size: 11px">iframe</a-tag>
                            <a-tag v-if="record.is_richtext" color="purple" style="font-size: 11px">rt</a-tag>
                          </a-space>
                        </template>
                      </template>
                    </a-table>
                  </a-card>
                </div>

                <!-- Raw JSON toggle -->
                <a-collapse style="margin-top: 12px">
                  <a-collapse-panel key="json" header="Normalized JSON (raw)">
                    <a-textarea
                      :value="formatJsonString(normalized)"
                      :rows="20"
                      readonly
                      style="font-family: monospace; font-size: 11px"
                    />
                  </a-collapse-panel>
                </a-collapse>
              </div>

              <div v-else-if="!normLoading && !normError" style="color: #999; text-align: center; padding: 24px">
                Click the tab to load normalized recording.
              </div>
            </a-spin>
          </a-tab-pane>
        </a-tabs>
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
import { getNormalizedRecording } from '@/api/recordings';
import type { Recording, RecordingUpdate, RecordingStatus, NormalizedRecording } from '@web-agent-flow/shared-types';

const route = useRoute();
const router = useRouter();
const recordingsStore = useRecordingsStore();

const formRef = ref<FormInstance>();
const editModalOpen = ref(false);
const activeTab = ref('raw');

const normalized = ref<NormalizedRecording | null>(null);
const normLoading = ref(false);
const normError = ref('');

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

const stepColumns = [
  { title: 'Action', key: 'action_type', width: 160 },
  { title: 'Field / Button', key: 'field_label' },
  { title: 'Value', key: 'value' },
  { title: 'Flags', key: 'flags', width: 100 },
];

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

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + '…' : s;
}

function actionColor(at: string): string {
  const map: Record<string, string> = {
    'navigate-page': 'geekblue',
    'fill-field': 'green',
    'select-field': 'lime',
    'edit-richtext': 'purple',
    'click-button': 'orange',
    'open-dialog': 'gold',
    'confirm-dialog': 'cyan',
    'cancel-dialog': 'red',
    'unknown-click': 'default',
  };
  return map[at] || 'default';
}

function segmentHeaderStyle(type: string): Record<string, string> {
  const bg: Record<string, string> = {
    navigation: '#e6f4ff',
    'form-fill': '#f6ffed',
    'dialog-interaction': '#fff7e6',
    'richtext-edit': '#f9f0ff',
    misc: '#fafafa',
  };
  return { background: bg[type] || '#fafafa' };
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

async function loadNormalized(): Promise<void> {
  const id = route.params.id as string;
  if (!id || normalized.value) return;
  normLoading.value = true;
  normError.value = '';
  try {
    normalized.value = await getNormalizedRecording(id);
  } catch (e) {
    normError.value = e instanceof Error ? e.message : 'Failed to load normalized recording';
  } finally {
    normLoading.value = false;
  }
}

function handleTabChange(key: string): void {
  if (key === 'normalized') {
    void loadNormalized();
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
    // Invalidate cached normalized result so it's re-fetched after edit
    normalized.value = null;
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
