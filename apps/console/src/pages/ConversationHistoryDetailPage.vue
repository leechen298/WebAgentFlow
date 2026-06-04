<template>
  <div>
    <a-page-header
      :title="$t('conversationHistory.detailPageTitle')"
      @back="$router.push('/conversation/history')"
    />

    <a-spin :spinning="loading">
      <a-card v-if="history" class="session-card">
        <a-descriptions :title="$t('conversationHistory.sessionInfo')" size="small" :column="4">
          <a-descriptions-item :label="$t('common.id')">
            <a-typography-text copyable>{{ history.session.id }}</a-typography-text>
          </a-descriptions-item>
          <a-descriptions-item :label="$t('conversationHistory.colStatus')">
            {{ history.session.status }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('conversationHistory.colMode')">
            {{ history.session.current_mode || '-' }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('conversationHistory.messageCount')">
            {{ history.messages.length }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('conversationHistory.eventCount')">
            {{ history.events.length }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('common.createdAt')">
            {{ history.session.created_at || '-' }}
          </a-descriptions-item>
          <a-descriptions-item :label="$t('common.updatedAt')">
            {{ history.session.updated_at || '-' }}
          </a-descriptions-item>
        </a-descriptions>
      </a-card>

      <a-card v-if="history" style="margin-top: 16px">
        <a-tabs v-model:activeKey="activeTab">
          <a-tab-pane key="timeline" :tab="$t('conversationHistory.tabDebugTimeline')">
            <div class="timeline-list">
              <div v-for="item in history.debug_timeline" :key="item.id" class="timeline-row">
                <div class="timeline-row-main">
                  <div class="timeline-title-line">
                    <strong>{{ item.title }}</strong>
                    <span class="status-tag" :class="`status-${item.status}`">
                      {{ timelineStatusLabel(item.status) }}
                    </span>
                    <span class="meta-tag">{{ item.kind }}</span>
                    <span class="meta-tag">{{ item.source }}</span>
                    <span class="time">{{ item.created_at || '-' }}</span>
                  </div>
                  <p class="timeline-summary">{{ item.summary }}</p>
                  <div class="timeline-ids">
                    <a-typography-text v-if="item.message_id" copyable>
                      message: {{ item.message_id }}
                    </a-typography-text>
                    <a-typography-text v-if="item.event_id" copyable>
                      event: {{ item.event_id }}
                    </a-typography-text>
                    <a-typography-text v-if="item.trace_id" copyable>
                      trace: {{ item.trace_id }}
                    </a-typography-text>
                  </div>
                  <details v-if="hasTimelineDetails(item.details)" class="timeline-details">
                    <summary>{{ $t('conversationHistory.timelineDetails') }}</summary>
                    <pre class="json-pre compact">{{ JSON.stringify(item.details, null, 2) }}</pre>
                  </details>
                </div>
              </div>
            </div>
            <a-empty
              v-if="history.debug_timeline.length === 0"
              :description="$t('conversationHistory.timelineEmpty')"
            />
          </a-tab-pane>

          <a-tab-pane key="transcript" :tab="$t('conversationHistory.tabTranscript')">
            <a-timeline>
              <a-timeline-item
                v-for="msg in history.messages"
                :key="msg.id"
                :color="msg.role === 'user' ? 'blue' : 'green'"
              >
                <p>
                  <strong>{{ msg.role }}</strong>
                  <span class="time">{{ msg.created_at }}</span>
                  <span v-if="msg.role === 'agent'" class="provenance-tag">
                    {{ provenanceLabel(msg) }}
                  </span>
                  <span
                    v-if="msg.role === 'agent' && msg.response_provenance?.fallback"
                    class="fallback-tag"
                  >
                    fallback
                  </span>
                </p>
                <p>{{ msg.content }}</p>
                <div
                  v-for="trace in tracesForMessage(msg)"
                  :key="trace.trace_id"
                  class="trace-summary"
                >
                  <span>{{ trace.provider || '-' }}</span>
                  <span>{{ trace.model || '-' }}</span>
                  <span>{{ trace.request_id || '-' }}</span>
                  <span>{{ trace.schema_name || '-' }}</span>
                  <span>{{ trace.latency_ms ?? '-' }} ms</span>
                  <span>{{ usageLabel(trace.usage) }}</span>
                  <span>{{ redactionLabel(trace.redaction) }}</span>
                </div>
              </a-timeline-item>
            </a-timeline>
            <a-empty v-if="history.messages.length === 0" />
          </a-tab-pane>

          <a-tab-pane key="events" :tab="$t('conversationHistory.tabEvents')">
            <a-timeline>
              <a-timeline-item v-for="evt in history.events" :key="evt.id">
                <p><strong>{{ evt.type }}</strong> <span class="time">{{ evt.created_at }}</span></p>
                <pre class="json-pre">{{ JSON.stringify(evt.payload, null, 2) }}</pre>
              </a-timeline-item>
            </a-timeline>
            <a-empty v-if="history.events.length === 0" />
          </a-tab-pane>

          <a-tab-pane key="learned_actions" :tab="$t('conversationHistory.tabLearnedActions')">
            <pre class="json-pre">{{ JSON.stringify(history.learned_actions, null, 2) }}</pre>
            <a-empty v-if="history.learned_actions.length === 0" />
          </a-tab-pane>

          <a-tab-pane key="evidence" :tab="$t('conversationHistory.tabEvidence')">
            <h4>Learning Runs</h4>
            <pre class="json-pre">{{ JSON.stringify(history.learning_runs, null, 2) }}</pre>
            <a-empty v-if="history.learning_runs.length === 0" />

            <h4 style="margin-top: 16px">Replay Summaries</h4>
            <pre class="json-pre">{{ JSON.stringify(history.replay_summaries, null, 2) }}</pre>
            <a-empty v-if="history.replay_summaries.length === 0" />
          </a-tab-pane>

          <a-tab-pane key="raw" :tab="$t('conversationHistory.tabRawJson')">
            <a-space style="margin-bottom: 8px">
              <a-button type="primary" size="small" @click="copyRawJson">
                {{ $t('conversationHistory.copyRawJson') }}
              </a-button>
            </a-space>
            <pre class="json-pre">{{ rawJson }}</pre>
          </a-tab-pane>
        </a-tabs>
      </a-card>

      <a-empty v-if="!loading && !history" :description="$t('error.notFound')" />
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { message } from 'ant-design-vue';
import {
  getConversationHistory,
  type ConversationHistoryMessage,
  type ConversationHistoryPayload,
  type ConversationDebugTimelineItem,
  type ConversationLlmTrace,
} from '@/api/conversation';

const { t } = useI18n();
const route = useRoute();

const loading = ref(false);
const history = ref<ConversationHistoryPayload | null>(null);
const activeTab = ref('timeline');

const sessionId = computed(() => String(route.params.session_id));

const rawJson = computed(() => {
  if (!history.value) return '';
  return JSON.stringify(history.value.raw, null, 2);
});

const tracesById = computed(() => {
  const index = new Map<string, ConversationLlmTrace>();
  for (const trace of history.value?.llm_traces || []) {
    index.set(trace.trace_id, trace);
  }
  return index;
});

async function load() {
  loading.value = true;
  try {
    const result = await getConversationHistory(sessionId.value);
    history.value = result;
  } catch {
    message.error(t('conversationHistory.loadFailed'));
    history.value = null;
  } finally {
    loading.value = false;
  }
}

async function copyRawJson() {
  try {
    await navigator.clipboard.writeText(rawJson.value);
    message.success(t('conversationHistory.copiedRawJson'));
  } catch {
    message.error('Copy failed');
  }
}

function provenanceLabel(messageItem: ConversationHistoryMessage): string {
  const sourceType = messageItem.response_provenance?.source_type || 'unknown';
  if (sourceType === 'code') return '代码生成';
  if (sourceType === 'agent') return 'Agent 生成';
  if (sourceType === 'hybrid') return '混合生成';
  return '未知来源';
}

function tracesForMessage(messageItem: ConversationHistoryMessage): ConversationLlmTrace[] {
  const ids = messageItem.response_provenance?.llm_trace_ids || [];
  return ids
    .map((id) => tracesById.value.get(id))
    .filter((trace): trace is ConversationLlmTrace => Boolean(trace));
}

function usageLabel(usage: Record<string, unknown>): string {
  const prompt = usage.prompt ?? '-';
  const completion = usage.completion ?? '-';
  const total = usage.total ?? '-';
  return `prompt ${prompt} / completion ${completion} / total ${total}`;
}

function redactionLabel(redaction: Record<string, unknown>): string {
  return redaction.applied === false ? 'not redacted' : 'redacted';
}

function timelineStatusLabel(status: ConversationDebugTimelineItem['status']): string {
  const key = `conversationHistory.timelineStatus.${status}`;
  const translated = t(key);
  return translated === key ? String(status) : translated;
}

function hasTimelineDetails(details: Record<string, unknown>): boolean {
  return Object.keys(details || {}).length > 0;
}

onMounted(() => {
  load();
});
</script>

<style scoped>
.session-card {
  margin-bottom: 8px;
}
.time {
  color: #999;
  font-size: 12px;
  margin-left: 8px;
}
.json-pre {
  background: #f6f8fa;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12px;
  max-height: 500px;
}
.provenance-tag,
.fallback-tag {
  display: inline-block;
  margin-left: 8px;
  padding: 1px 6px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  color: #595959;
  font-size: 12px;
  line-height: 18px;
}
.fallback-tag {
  color: #ad6800;
  border-color: #ffd591;
  background: #fff7e6;
}
.trace-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 6px;
  color: #595959;
  font-size: 12px;
}
.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.timeline-row {
  border-left: 3px solid #d9d9d9;
  padding: 8px 0 8px 12px;
}
.timeline-title-line {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.timeline-summary {
  color: #262626;
  margin: 6px 0;
}
.timeline-ids {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
}
.timeline-details {
  margin-top: 8px;
}
.timeline-details summary {
  color: #595959;
  cursor: pointer;
  font-size: 12px;
}
.json-pre.compact {
  margin-top: 6px;
  max-height: 260px;
}
.status-tag,
.meta-tag {
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  color: #595959;
  font-size: 12px;
  line-height: 18px;
  padding: 1px 6px;
}
.status-waiting,
.status-running {
  border-color: #91caff;
  color: #0958d9;
}
.status-success {
  border-color: #b7eb8f;
  color: #237804;
}
.status-warning {
  border-color: #ffd591;
  color: #ad6800;
}
.status-error,
.status-cancelled {
  border-color: #ffccc7;
  color: #a8071a;
}
</style>
