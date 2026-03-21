<template>
  <div>
    <a-page-header
      title="Skill Detail"
      @back="goBack"
    >
      <template #extra>
        <a-space>
          <a-button @click="showEditModal">
            <template #icon><edit-outlined /></template>
            Edit
          </a-button>
          <a-popconfirm
            title="Delete this skill?"
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

      <a-card v-if="skill" :bordered="false" style="margin-top: 16px">
        <a-descriptions :column="2" bordered>
          <a-descriptions-item label="ID">
            {{ skill.id }}
          </a-descriptions-item>
          <a-descriptions-item label="Name">
            {{ skill.name }}
          </a-descriptions-item>
          <a-descriptions-item label="Version">
            {{ skill.version }}
          </a-descriptions-item>
          <a-descriptions-item label="Status">
            <a-tag :color="getStatusColor(skill.status)">
              {{ skill.status }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="Recording ID">
            {{ skill.recording_id || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="Description">
            {{ skill.description || '-' }}
          </a-descriptions-item>
          <a-descriptions-item label="Created At">
            {{ formatDate(skill.created_at) }}
          </a-descriptions-item>
          <a-descriptions-item label="Updated At">
            {{ formatDate(skill.updated_at) }}
          </a-descriptions-item>
          <a-descriptions-item label="Definition" :span="2">
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
      title="Edit Skill"
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
        <a-row :gutter="16">
          <a-col :span="16">
            <a-form-item label="Name" name="name">
              <a-input v-model:value="formData.name" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="Version" name="version">
              <a-input v-model:value="formData.version" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="Status" name="status">
              <a-select v-model:value="formData.status" style="width: 100%">
                <a-select-option value="draft">Draft</a-select-option>
                <a-select-option value="published">Published</a-select-option>
                <a-select-option value="archived">Archived</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="Recording ID" name="recording_id">
              <a-input v-model:value="formData.recording_id" allow-clear />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="Description" name="description">
          <a-textarea v-model:value="formData.description" :rows="2" />
        </a-form-item>
        <a-form-item label="Definition (JSON)" name="definition">
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
import { message, type FormInstance } from 'ant-design-vue';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons-vue';
import { useSkillsStore } from '@/stores';
import { safeParseJson, formatJsonString } from '@/utils';
import type { Skill, SkillUpdate, SkillStatus } from '@web-agent-flow/shared-types';

const route = useRoute();
const router = useRouter();
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

const rules = {
  name: [{ required: true, message: 'Name is required' }],
  version: [{ required: true, message: 'Version is required' }]
};

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
    message.error(e instanceof Error ? e.message : 'Failed to load skill');
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
    message.success('Skill updated');
    editModalOpen.value = false;
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Failed to update skill');
  }
}

async function handleDelete(): Promise<void> {
  try {
    await skillsStore.deleteSkill(route.params.id as string);
    message.success('Skill deleted');
    goBack();
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Failed to delete skill');
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
