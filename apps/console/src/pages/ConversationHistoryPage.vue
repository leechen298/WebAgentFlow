<template>
  <div>
    <a-page-header
      :title="$t('conversationHistory.title')"
      :sub-title="$t('conversationHistory.subtitle')"
    />

    <a-card>
      <a-space style="margin-bottom: 16px; flex-wrap: wrap">
        <a-input
          v-model:value="filters.current_mode"
          :placeholder="$t('conversationHistory.filterMode')"
          style="width: 160px"
          allow-clear
        />
        <a-input
          v-model:value="filters.status"
          :placeholder="$t('conversationHistory.filterStatus')"
          style="width: 160px"
          allow-clear
        />
        <a-input-number
          v-model:value="filters.limit"
          :placeholder="$t('conversationHistory.filterLimit')"
          :min="1"
          :max="100"
          style="width: 120px"
        />
        <a-date-picker
          v-model:value="filters.updated_from"
          :placeholder="$t('conversationHistory.filterUpdatedFrom')"
          show-time
          style="width: 200px"
        />
        <a-date-picker
          v-model:value="filters.updated_to"
          :placeholder="$t('conversationHistory.filterUpdatedTo')"
          show-time
          style="width: 200px"
        />
        <a-button type="primary" @click="load">
          {{ $t('conversationHistory.refresh') }}
        </a-button>
      </a-space>

      <a-table
        :columns="columns"
        :data-source="items"
        :loading="loading"
        row-key="id"
        :pagination="false"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'session_id'">
            <a-typography-text copyable class="session-id">
              {{ record.id }}
            </a-typography-text>
          </template>
          <template v-if="column.key === 'last_user_message'">
            <span class="truncate">{{ record.last_user_message || '-' }}</span>
          </template>
          <template v-if="column.key === 'last_agent_message'">
            <span class="truncate">{{ record.last_agent_message || '-' }}</span>
          </template>
          <template v-if="column.key === 'actions'">
            <a-button type="link" size="small" @click="goDetail(record.id)">
              {{ $t('conversationHistory.viewDetail') }}
            </a-button>
            <a-button type="link" size="small" @click="copyId(record.id)">
              {{ $t('conversationHistory.copyId') }}
            </a-button>
          </template>
        </template>
      </a-table>

      <a-empty v-if="!loading && items.length === 0" :description="$t('conversationHistory.empty')" />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { message } from 'ant-design-vue';
import { listConversationSessions, type ConversationSessionSummary } from '@/api/conversation';

const { t } = useI18n();
const router = useRouter();

const loading = ref(false);
const items = ref<ConversationSessionSummary[]>([]);

const filters = reactive({
  current_mode: 'interactive_chat',
  status: undefined as string | undefined,
  limit: 50,
  updated_from: undefined as unknown,
  updated_to: undefined as unknown,
});

const columns = computed(() => [
  { title: t('conversationHistory.colUpdatedAt'), dataIndex: 'updated_at', key: 'updated_at', width: 180 },
  { title: t('conversationHistory.colSessionId'), key: 'session_id', width: 280 },
  { title: t('conversationHistory.colMode'), dataIndex: 'current_mode', key: 'current_mode', width: 140 },
  { title: t('conversationHistory.colStatus'), dataIndex: 'status', key: 'status', width: 140 },
  { title: t('conversationHistory.colLastUserMsg'), key: 'last_user_message' },
  { title: t('conversationHistory.colLastAgentMsg'), key: 'last_agent_message' },
  { title: t('conversationHistory.colLearnedActions'), dataIndex: 'learned_action_count', key: 'learned_action_count', width: 120 },
  { title: t('conversationHistory.colEvents'), dataIndex: 'event_count', key: 'event_count', width: 100 },
  { title: t('common.actions'), key: 'actions', width: 180, fixed: 'right' },
]);

async function load() {
  loading.value = true;
  try {
    const params: Record<string, unknown> = { limit: filters.limit };
    if (filters.current_mode) params.current_mode = filters.current_mode;
    if (filters.status) params.status = filters.status;
    if (filters.updated_from) {
      params.updated_from = (filters.updated_from as any).toISOString?.() || filters.updated_from;
    }
    if (filters.updated_to) {
      params.updated_to = (filters.updated_to as any).toISOString?.() || filters.updated_to;
    }
    const result = await listConversationSessions(params);
    items.value = result.items || [];
  } catch {
    message.error(t('conversationHistory.loadFailed'));
  } finally {
    loading.value = false;
  }
}

function goDetail(sessionId: string) {
  router.push(`/conversation/history/${sessionId}`);
}

async function copyId(sessionId: string) {
  try {
    await navigator.clipboard.writeText(sessionId);
    message.success(t('conversationHistory.copiedId'));
  } catch {
    message.error('Copy failed');
  }
}

onMounted(() => {
  load();
});
</script>

<style scoped>
.session-id {
  font-family: monospace;
  font-size: 12px;
}
.truncate {
  display: inline-block;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
