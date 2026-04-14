<template>
  <div>
    <a-page-header
      :title="$t('nav.skillDetail')"
      @back="goBack"
    >
      <template #extra>
        <a-space>
          <a-button @click="showEditModal">
            <template #icon><edit-outlined /></template>
            {{ $t('common.edit') }}
          </a-button>
          <a-popconfirm
            :title="$t('skills.deleteConfirm')"
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

      <a-card v-if="skill" :bordered="false" style="margin-top: 16px">
        <a-descriptions :column="2" bordered>
          <a-descriptions-item :label="$t('common.id')">
            {{ skill.id }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('common.name')">
            {{ skill.name }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('common.version')">
            {{ skill.version }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('common.status')">
            <a-tag :color="getStatusColor(skill.status)">
              {{ skill.status }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item :label="$t('skills.recordingId')">
            {{ skill.recording_id || '-' }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('common.description')">
            {{ skill.description || '-' }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('common.createdAt')">
            {{ formatDate(skill.created_at) }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('common.updatedAt')">
            {{ formatDate(skill.updated_at) }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('skills.definitionJson')" :span="2">
            <a-textarea
              :value="formatJsonString(skill.definition)"
              :rows="8"
              readonly
            />
          </a-descriptions-item>
        </a-descriptions>
      </a-card>
    </a-spin>

    <!-- Edit Modal -->
    <a-modal
      v-model:open="editModalOpen"
      :title="$t('skills.editTitle')"
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
              <a-input v-model:value="formData.name" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item :label="$t('common.version')" name="version">
              <a-input v-model:value="formData.version" />
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
              <a-input v-model:value="formData.recording_id" allow-clear />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item :label="$t('common.description')" name="description">
          <a-textarea v-model:value="formData.description" :rows="2" />
        </a-form-item>
        <a-form-item :label="$t('skills.definitionJson')" name="definition">
          <a-textarea
            v-model:value="formData.definitionStr"
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
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { message, type FormInstance } from 'ant-design-vue';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons-vue';
import { useSkillsStore } from '@/stores';
import { safeParseJson, formatJsonString } from '@/utils';
import type { Skill, SkillUpdate, SkillStatus } from '@web-agent-flow/shared-types';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();
const skillsStore = useSkillsStore();

const formRef = ref<FormInstance>();
const editModalOpen = ref(false);

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

const skill = computed(() => skillsStore.currentSkill);
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

async function fetchSkill(): Promise<void> {
  const id = route.params.id as string;
  if (!id) return;

  try {
    await skillsStore.fetchSkill(id);
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('skills.loadFailed'));
  }
}

function showEditModal(): void {
  if (!skill.value) return;

  formData.name = skill.value.name;
  formData.version = skill.value.version;
  formData.status = skill.value.status;
  formData.recording_id = skill.value.recording_id || '';
  formData.description = skill.value.description || '';
  formData.definitionStr = formatJsonString(skill.value.definition);
  formErrors.definition = '';
  editModalOpen.value = true;
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

    const definitionResult = safeParseJson(formData.definitionStr);

    const updateData: SkillUpdate = {
      name: formData.name,
      version: formData.version,
      status: formData.status,
      recording_id: formData.recording_id || null,
      description: formData.description || null,
      definition: definitionResult.success ? (definitionResult.data as Record<string, unknown>) : undefined
    };

    await skillsStore.updateSkill(route.params.id as string, updateData);
    message.success(t('skills.updated'));
    editModalOpen.value = false;
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('skills.updateFailed'));
  }
}

async function handleDelete(): Promise<void> {
  try {
    await skillsStore.deleteSkill(route.params.id as string);
    message.success(t('skills.deleted'));
    goBack();
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('skills.deleteFailed'));
  }
}

function goBack(): void {
  void router.push('/skills');
}

onMounted(() => {
  void fetchSkill();
});

onUnmounted(() => {
  skillsStore.clearCurrent();
});
</script>
