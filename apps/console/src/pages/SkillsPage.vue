<template>
  <div>
    <a-card :bordered="false">
      <template #title>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>{{ $t('skills.title') }}</span>
          <a-button type="primary" @click="showCreateModal">
            <template #icon><plus-outlined /></template>
            {{ $t('skills.new') }}
          </a-button>
        </div>
      </template>

      <a-spin :spinning="loadingList">
        <a-table
          :columns="columns"
          :data-source="skills"
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
                <a-button type="link" size="small" @click="editSkill(record)">
                  {{ $t('common.edit') }}
                </a-button>
                <a-popconfirm
                  :title="$t('skills.deleteConfirm')"
                  :ok-text="$t('common.yes')"
                  :cancel-text="$t('common.no')"
                  @confirm="deleteSkill(record.id)"
                >
                  <a-button type="link" size="small" danger>
                    {{ $t('common.delete') }}
                  </a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>

          <template #emptyText>
            <a-empty :description="$t('skills.empty')">
              <a-button type="primary" @click="showCreateModal">
                <template #icon><plus-outlined /></template>
                {{ $t('skills.createTitle') }}
              </a-button>
            </a-empty>
          </template>
        </a-table>

        <div v-if="skills.length > 0" style="display: flex; justify-content: flex-end; margin-top: 16px; gap: 8px">
          <a-button size="small" :disabled="!skillsStore.hasPrev" @click="goFirstPage">{{ $t('common.first') }}</a-button>
          <a-button size="small" :disabled="!skillsStore.hasPrev" @click="goPrevPage">{{ $t('common.prev') }}</a-button>
          <a-button size="small" :disabled="!skillsStore.hasNext" @click="goNextPage">{{ $t('common.next') }}</a-button>
        </div>
      </a-spin>
    </a-card>

    <!-- Create/Edit Modal -->
    <a-modal
      v-model:open="modalOpen"
      :title="isEditing ? $t('skills.editTitle') : $t('skills.createTitle')"
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
        <a-row :gutter="16">
          <a-col :span="16">
            <a-form-item :label="$t('common.name')" name="name">
              <a-input v-model:value="formData.name" :placeholder="$t('skills.enterName')" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item :label="$t('common.version')" name="version">
              <a-input v-model:value="formData.version" placeholder="1.0.0" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item :label="$t('common.status')" name="status">
              <a-select v-model:value="formData.status" style="width: 100%">
                <a-select-option value="draft">{{ $t('status.draft') }}</a-select-option>
                <a-select-option value="published">{{ $t('status.published') }}</a-select-option>
                <a-select-option value="archived">{{ $t('status.archived') }}</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item :label="$t('skills.recordingId')" name="recording_id">
              <a-input v-model:value="formData.recording_id" :placeholder="$t('skills.optionalRecordingId')" allow-clear />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item :label="$t('common.description')" name="description">
          <a-textarea v-model:value="formData.description" :placeholder="$t('skills.enterDescription')" :rows="2" />
        </a-form-item>
        <a-form-item :label="$t('skills.definitionJson')" name="definition">
          <a-textarea
            v-model:value="formData.definitionStr"
            placeholder='{}'
            :rows="6"
            @blur="validateJson"
          />
          <div v-if="formErrors.definition" style="color: #ff4d4f; font-size: 12px; margin-top: 4px">
            {{ formErrors.definition }}
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
import { useSkillsStore } from '@/stores';
import { safeParseJson, formatJsonString } from '@/utils';
import type { Skill, SkillCreate, SkillUpdate, SkillStatus } from '@web-agent-flow/shared-types';

const router = useRouter();
const { t } = useI18n();
const skillsStore = useSkillsStore();

const formRef = ref<FormInstance>();
const modalOpen = ref(false);
const isEditing = ref(false);
const editingId = ref<string | null>(null);

const formData = reactive({
  name: '',
  version: '1.0.0',
  status: 'draft' as SkillStatus,
  recording_id: '',
  description: '',
  definitionStr: '{}'
});

const formErrors = reactive({
  definition: ''
});

const rules = computed(() => ({
  name: [{ required: true, message: t('common.nameRequired') }],
  version: [{ required: true, message: t('skills.versionRequired') }]
}));

const columns = computed(() => [
  { title: t('common.name'), dataIndex: 'name', key: 'name' },
  { title: t('common.version'), dataIndex: 'version', key: 'version', width: 100 },
  { title: t('common.status'), dataIndex: 'status', key: 'status', width: 100 },
  { title: t('skills.recordingId'), dataIndex: 'recording_id', key: 'recording_id', width: 200 },
  { title: t('common.createdAt'), dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: t('common.actions'), key: 'actions', width: 200, fixed: 'right' as const }
]);

const skills = ref<Skill[]>([]);
const loadingList = computed(() => skillsStore.loadingList);
const loading = computed(() => skillsStore.loading);
const error = computed(() => skillsStore.error);

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    draft: 'default',
    published: 'green',
    archived: 'orange'
  };
  return colors[status] || 'default';
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString();
}

async function fetchSkills(): Promise<void> {
  try {
    await skillsStore.fetchFirstPage();
    skills.value = skillsStore.skills;
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('skills.loadFailed'));
  }
}

async function goNextPage(): Promise<void> {
  try {
    await skillsStore.fetchNextPage();
    skills.value = skillsStore.skills;
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('skills.loadFailed'));
  }
}

async function goPrevPage(): Promise<void> {
  try {
    await skillsStore.fetchPrevPage();
    skills.value = skillsStore.skills;
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('skills.loadFailed'));
  }
}

async function goFirstPage(): Promise<void> {
  await fetchSkills();
}

function showCreateModal(): void {
  isEditing.value = false;
  editingId.value = null;
  resetForm();
  modalOpen.value = true;
}

function editSkill(record: Skill): void {
  isEditing.value = true;
  editingId.value = record.id;
  formData.name = record.name;
  formData.version = record.version;
  formData.status = record.status;
  formData.recording_id = record.recording_id || '';
  formData.description = record.description || '';
  formData.definitionStr = formatJsonString(record.definition);
  formErrors.definition = '';
  modalOpen.value = true;
}

function resetForm(): void {
  formData.name = '';
  formData.version = '1.0.0';
  formData.status = 'draft';
  formData.recording_id = '';
  formData.description = '';
  formData.definitionStr = '{}';
  formErrors.definition = '';
}

function validateJson(): boolean {
  const str = formData.definitionStr;
  if (!str.trim()) {
    formErrors.definition = '';
    return true;
  }
  const result = safeParseJson(str);
  if (!result.success) {
    formErrors.definition = result.error;
    return false;
  }
  formErrors.definition = '';
  return true;
}

async function handleSave(): Promise<void> {
  try {
    await formRef.value?.validate();

    if (!validateJson()) {
      return;
    }

    const definitionResult = safeParseJson(formData.definitionStr, {});

    if (isEditing.value && editingId.value) {
      const updateData: SkillUpdate = {
        name: formData.name,
        version: formData.version,
        status: formData.status,
        recording_id: formData.recording_id || null,
        description: formData.description || null,
        definition: definitionResult.success ? (definitionResult.data as Record<string, unknown>) : undefined
      };
      await skillsStore.updateSkill(editingId.value, updateData);
      message.success(t('skills.updated'));
    } else {
      const createData: SkillCreate = {
        name: formData.name,
        version: formData.version,
        status: formData.status,
        recording_id: formData.recording_id || null,
        description: formData.description || null,
        definition: definitionResult.success ? (definitionResult.data as Record<string, unknown>) : {}
      };
      await skillsStore.createSkill(createData);
      message.success(t('skills.created'));
    }

    modalOpen.value = false;
    await fetchSkills();
  } catch (e) {
    if (e instanceof Error && e.message !== 'Validation failed') {
      message.error(e.message);
    }
  }
}

async function deleteSkill(id: string): Promise<void> {
  try {
    await skillsStore.deleteSkill(id);
    message.success(t('skills.deleted'));
    await fetchSkills();
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('skills.deleteFailed'));
  }
}

function viewDetail(id: string): void {
  void router.push(`/skills/${id}`);
}

onMounted(() => {
  void fetchSkills();
});
</script>
