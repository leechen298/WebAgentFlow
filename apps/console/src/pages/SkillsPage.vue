<template>
  <div>
    <a-card :bordered="false">
      <template #title>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>Skills</span>
          <a-button type="primary" @click="showCreateModal">
            <template #icon><plus-outlined /></template>
            New Skill
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
                  View
                </a-button>
                <a-button type="link" size="small" @click="editSkill(record)">
                  Edit
                </a-button>
                <a-popconfirm
                  title="Delete this skill?"
                  ok-text="Yes"
                  cancel-text="No"
                  @confirm="deleteSkill(record.id)"
                >
                  <a-button type="link" size="small" danger>
                    Delete
                  </a-button>
                </a-popconfirm>
              </a-space>
            </template>
          </template>

          <template #emptyText>
            <a-empty description="No skills yet">
              <a-button type="primary" @click="showCreateModal">
                <template #icon><plus-outlined /></template>
                Create Skill
              </a-button>
            </a-empty>
          </template>
        </a-table>
      </a-spin>
    </a-card>

    <!-- Create/Edit Modal -->
    <a-modal
      v-model:open="modalOpen"
      :title="isEditing ? 'Edit Skill' : 'Create Skill'"
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
              <a-input v-model:value="formData.name" placeholder="Enter skill name" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="Version" name="version">
              <a-input v-model:value="formData.version" placeholder="1.0.0" />
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
              <a-input v-model:value="formData.recording_id" placeholder="Optional recording ID" allow-clear />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="Description" name="description">
          <a-textarea v-model:value="formData.description" placeholder="Enter description" :rows="2" />
        </a-form-item>
        <a-form-item label="Definition (JSON)" name="definition">
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
import { message, type FormInstance } from 'ant-design-vue';
import { PlusOutlined } from '@ant-design/icons-vue';
import { useSkillsStore } from '@/stores';
import { safeParseJson, formatJsonString } from '@/utils';
import type { Skill, SkillCreate, SkillUpdate, SkillStatus } from '@web-agent-flow/shared-types';

const router = useRouter();
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

const rules = {
  name: [{ required: true, message: 'Name is required' }],
  version: [{ required: true, message: 'Version is required' }]
};

const columns = [
  { title: 'Name', dataIndex: 'name', key: 'name' },
  { title: 'Version', dataIndex: 'version', key: 'version', width: 100 },
  { title: 'Status', dataIndex: 'status', key: 'status', width: 100 },
  { title: 'Recording ID', dataIndex: 'recording_id', key: 'recording_id', width: 200 },
  { title: 'Created At', dataIndex: 'created_at', key: 'created_at', width: 180 },
  { title: 'Actions', key: 'actions', width: 200, fixed: 'right' as const }
];

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
    await skillsStore.fetchSkills();
    skills.value = skillsStore.skills;
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Failed to load skills');
  }
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

    const definitionResult = safeParseJson(formData.definitionStr);

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
      message.success('Skill updated');
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
      message.success('Skill created');
    }

    modalOpen.value = false;
    skills.value = skillsStore.skills;
  } catch (e) {
    if (e instanceof Error && e.message !== 'Validation failed') {
      message.error(e.message);
    }
  }
}

async function deleteSkill(id: string): Promise<void> {
  try {
    await skillsStore.deleteSkill(id);
    message.success('Skill deleted');
    skills.value = skillsStore.skills;
  } catch (e) {
    message.error(e instanceof Error ? e.message : 'Failed to delete skill');
  }
}

function viewDetail(id: string): void {
  void router.push(`/skills/${id}`);
}

onMounted(() => {
  void fetchSkills();
});
</script>
