<template>
  <div>
    <a-page-header :title="$t('learning.debugTitle')" />

    <!-- Input Form -->
    <a-card :bordered="false" style="margin-top: 16px">
      <a-form layout="inline" @finish="runInference">
        <a-form-item :label="$t('learning.recordingId')" required>
          <a-input
            v-model:value="recordingId"
            :placeholder="$t('learning.recordingIdPlaceholder')"
            style="width: 320px"
          />
        </a-form-item>
        <a-form-item :label="$t('learning.runId')">
          <a-input
            v-model:value="runId"
            :placeholder="$t('learning.runIdPlaceholder')"
            style="width: 320px"
          />
        </a-form-item>
        <a-form-item :label="$t('learning.scoreThreshold')">
          <a-input-number
            v-model:value="scoreThreshold"
            :min="0"
            :max="1"
            :step="0.05"
            style="width: 100px"
          />
        </a-form-item>
        <a-form-item :label="$t('learning.maxCandidates')">
          <a-input-number
            v-model:value="maxCandidates"
            :min="1"
            :max="500"
            style="width: 100px"
          />
        </a-form-item>
        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            :loading="loading"
            :disabled="!recordingId.trim()"
          >
            {{ $t('learning.runInference') }}
          </a-button>
        </a-form-item>
      </a-form>
    </a-card>

    <!-- Error -->
    <a-alert
      v-if="error"
      :message="$t('learning.error')"
      :description="error"
      type="error"
      show-icon
      closable
      style="margin-top: 16px"
      @close="error = null"
    />

    <!-- Summary -->
    <a-card
      v-if="result"
      :title="$t('learning.summary')"
      :bordered="false"
      style="margin-top: 16px"
    >
      <a-row :gutter="16">
        <a-col :span="4">
          <a-statistic :title="$t('learning.candidates')" :value="result.candidate_count" />
        </a-col>
        <a-col :span="4">
          <a-statistic :title="$t('learning.hints')" :value="result.hint_count" />
        </a-col>
        <a-col :span="4">
          <a-statistic :title="$t('learning.textIntentHits')" :value="stats.textIntent" />
        </a-col>
        <a-col :span="4">
          <a-statistic :title="$t('learning.iconIntentHits')" :value="stats.iconIntent" />
        </a-col>
        <a-col :span="4">
          <a-statistic :title="$t('learning.componentLibHits')" :value="stats.componentLib" />
        </a-col>
        <a-col :span="4">
          <a-statistic :title="$t('learning.mutationLinkageHits')" :value="stats.mutationLinkage" />
        </a-col>
      </a-row>
      <div style="margin-top: 12px">
        <span style="margin-right: 16px">
          {{ $t('learning.actionBreakdown') }}:
        </span>
        <a-tag v-for="(count, action) in stats.actionCounts" :key="action" color="blue">
          {{ action }}: {{ count }}
        </a-tag>
      </div>
      <div v-if="result.written_to_run" style="margin-top: 8px">
        <a-tag color="green">{{ $t('learning.writtenToRun') }}: {{ result.written_to_run }}</a-tag>
      </div>
      <div style="margin-top: 8px">
        <a-tag color="cyan">{{ $t('learning.markedReasonable') }}: {{ markedReasonable }}</a-tag>
        <a-tag color="orange">{{ $t('learning.markedUnreasonable') }}: {{ markedUnreasonable }}</a-tag>
      </div>
    </a-card>

    <!-- Candidates Table -->
    <a-card
      v-if="result"
      :title="$t('learning.candidateList')"
      :bordered="false"
      style="margin-top: 16px"
    >
      <template #extra>
        <a-space>
          <a-select
            v-model:value="filterAction"
            :placeholder="$t('learning.filterByAction')"
            style="width: 150px"
            allow-clear
          >
            <a-select-option
              v-for="action in availableActions"
              :key="action"
              :value="action"
            >
              {{ action }}
            </a-select-option>
          </a-select>
          <a-select
            v-model:value="filterSignal"
            :placeholder="$t('learning.filterBySignal')"
            style="width: 180px"
            allow-clear
          >
            <a-select-option value="text_intent">text_intent</a-select-option>
            <a-select-option value="icon_intent">icon_intent</a-select-option>
            <a-select-option value="component_lib">component_lib</a-select-option>
            <a-select-option value="mutation_linkage">mutation_linkage</a-select-option>
          </a-select>
        </a-space>
      </template>

      <a-table
        :columns="candidateColumns"
        :data-source="filteredCandidates"
        :pagination="{ pageSize: 20, showSizeChanger: true, showTotal: (t: number) => `${t} items` }"
        row-key="element_key"
        size="small"
        :scroll="{ x: 1200 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'priority'">
            <span>{{ record.priority }}</span>
          </template>
          <template v-if="column.key === 'element_key'">
            <span style="font-family: monospace; font-size: 12px">{{ record.element_key }}</span>
          </template>
          <template v-if="column.key === 'actions_list'">
            <a-tag v-for="a in record.inferred_actions" :key="a" :color="actionColor(a)">
              {{ a }}
            </a-tag>
          </template>
          <template v-if="column.key === 'score'">
            <a-tag :color="scoreColor(record.score)">{{ record.score.toFixed(3) }}</a-tag>
          </template>
          <template v-if="column.key === 'tag'">
            <span v-if="record.evidence.tag" style="font-family: monospace">&lt;{{ record.evidence.tag }}&gt;</span>
          </template>
          <template v-if="column.key === 'role'">
            <span v-if="record.evidence.role">{{ record.evidence.role }}</span>
          </template>
          <template v-if="column.key === 'component_lib'">
            <a-tag v-if="record.evidence.component_lib" color="purple">
              {{ record.evidence.component_lib }}
            </a-tag>
          </template>
          <template v-if="column.key === 'text_intent'">
            <a-tag v-if="record.evidence.text_intent" color="green">
              {{ record.evidence.text_intent }}
            </a-tag>
          </template>
          <template v-if="column.key === 'icon_intent'">
            <template v-if="record.evidence.icon_intent">
              <a-tag v-for="ic in record.evidence.icon_intent" :key="ic" color="cyan">
                {{ ic }}
              </a-tag>
            </template>
          </template>
          <template v-if="column.key === 'mutation'">
            <a-tag v-if="record.evidence.mutation_linkage" color="orange">linked</a-tag>
          </template>
          <template v-if="column.key === 'judgment'">
            <a-space>
              <a-button
                size="small"
                :type="judgments[record.element_key] === 'reasonable' ? 'primary' : 'default'"
                @click="markJudgment(record.element_key, 'reasonable')"
              >
                {{ $t('learning.reasonable') }}
              </a-button>
              <a-button
                size="small"
                :danger="judgments[record.element_key] === 'unreasonable'"
                :type="judgments[record.element_key] === 'unreasonable' ? 'primary' : 'default'"
                @click="markJudgment(record.element_key, 'unreasonable')"
              >
                {{ $t('learning.unreasonable') }}
              </a-button>
            </a-space>
          </template>
          <template v-if="column.key === 'detail'">
            <a-button size="small" type="link" @click="expandedKey = expandedKey === record.element_key ? null : record.element_key">
              {{ expandedKey === record.element_key ? $t('learning.collapse') : $t('learning.expand') }}
            </a-button>
          </template>
        </template>
      </a-table>

      <!-- Expanded evidence JSON -->
      <a-card
        v-if="expandedKey && expandedCandidate"
        :title="`Evidence: ${expandedKey}`"
        size="small"
        style="margin-top: 8px; background: #fafafa"
      >
        <pre style="font-size: 12px; max-height: 300px; overflow: auto">{{ JSON.stringify(expandedCandidate.evidence, null, 2) }}</pre>
      </a-card>
    </a-card>

    <!-- Hints Table -->
    <a-card
      v-if="result && result.interaction_hints.length > 0"
      :title="$t('learning.hintList')"
      :bordered="false"
      style="margin-top: 16px"
    >
      <a-table
        :columns="hintColumns"
        :data-source="result.interaction_hints"
        :pagination="false"
        row-key="element_key"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'action'">
            <a-tag :color="actionColor(record.action)">{{ record.action }}</a-tag>
          </template>
          <template v-if="column.key === 'element_key'">
            <span style="font-family: monospace; font-size: 12px">{{ record.element_key }}</span>
          </template>
          <template v-if="column.key === 'expected_effect'">
            <span v-if="record.expected_effect">{{ record.expected_effect }}</span>
            <span v-else style="color: #999">-</span>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { inferCandidates } from '@/api/learning';
import type { InferCandidatesResult, CandidateElement } from '@/api/learning';

const { t } = useI18n();

// --- Form state ---
const recordingId = ref('');
const runId = ref('');
const scoreThreshold = ref(0.10);
const maxCandidates = ref(200);

// --- Result state ---
const loading = ref(false);
const error = ref<string | null>(null);
const result = ref<InferCandidatesResult | null>(null);

// --- Filters ---
const filterAction = ref<string | null>(null);
const filterSignal = ref<string | null>(null);

// --- Judgment (local only) ---
const judgments = ref<Record<string, 'reasonable' | 'unreasonable'>>({});

// --- Expanded evidence ---
const expandedKey = ref<string | null>(null);

// --- Computed ---
const stats = computed(() => {
  if (!result.value) return { textIntent: 0, iconIntent: 0, componentLib: 0, mutationLinkage: 0, actionCounts: {} };
  const candidates = result.value.candidate_elements;
  const actionCounts: Record<string, number> = {};
  let textIntent = 0;
  let iconIntent = 0;
  let componentLib = 0;
  let mutationLinkage = 0;
  for (const c of candidates) {
    for (const a of c.inferred_actions) {
      actionCounts[a] = (actionCounts[a] || 0) + 1;
    }
    if (c.evidence.text_intent) textIntent++;
    if (c.evidence.icon_intent?.length) iconIntent++;
    if (c.evidence.component_lib) componentLib++;
    if (c.evidence.mutation_linkage) mutationLinkage++;
  }
  return { textIntent, iconIntent, componentLib, mutationLinkage, actionCounts };
});

const availableActions = computed(() => {
  if (!result.value) return [];
  const actions = new Set<string>();
  for (const c of result.value.candidate_elements) {
    for (const a of c.inferred_actions) actions.add(a);
  }
  return [...actions].sort();
});

const filteredCandidates = computed(() => {
  if (!result.value) return [];
  let list = result.value.candidate_elements;
  if (filterAction.value) {
    list = list.filter(c => c.inferred_actions.includes(filterAction.value!));
  }
  if (filterSignal.value) {
    list = list.filter(c => {
      const ev = c.evidence;
      switch (filterSignal.value) {
        case 'text_intent': return !!ev.text_intent;
        case 'icon_intent': return !!ev.icon_intent?.length;
        case 'component_lib': return !!ev.component_lib;
        case 'mutation_linkage': return !!ev.mutation_linkage;
        default: return true;
      }
    });
  }
  return list;
});

const markedReasonable = computed(() =>
  Object.values(judgments.value).filter(v => v === 'reasonable').length,
);
const markedUnreasonable = computed(() =>
  Object.values(judgments.value).filter(v => v === 'unreasonable').length,
);

const expandedCandidate = computed(() => {
  if (!expandedKey.value || !result.value) return null;
  return result.value.candidate_elements.find(c => c.element_key === expandedKey.value) ?? null;
});

// --- Columns ---
const candidateColumns = computed(() => [
  { title: '#', key: 'priority', dataIndex: 'priority', width: 50, sorter: (a: CandidateElement, b: CandidateElement) => a.priority - b.priority },
  { title: t('learning.elementKey'), key: 'element_key', dataIndex: 'element_key', ellipsis: true, width: 280 },
  { title: t('learning.inferredActions'), key: 'actions_list', width: 140 },
  { title: t('learning.score'), key: 'score', dataIndex: 'score', width: 80, sorter: (a: CandidateElement, b: CandidateElement) => a.score - b.score, defaultSortOrder: 'descend' as const },
  { title: 'tag', key: 'tag', width: 80 },
  { title: 'role', key: 'role', width: 80 },
  { title: 'component', key: 'component_lib', width: 120 },
  { title: 'text_intent', key: 'text_intent', width: 100 },
  { title: 'icon_intent', key: 'icon_intent', width: 120 },
  { title: 'mutation', key: 'mutation', width: 80 },
  { title: t('learning.judgment'), key: 'judgment', width: 160, fixed: 'right' as const },
  { title: '', key: 'detail', width: 70, fixed: 'right' as const },
]);

const hintColumns = computed(() => [
  { title: '#', dataIndex: 'priority', width: 50 },
  { title: t('learning.elementKey'), key: 'element_key', dataIndex: 'element_key', ellipsis: true },
  { title: t('learning.action'), key: 'action', dataIndex: 'action', width: 100 },
  { title: t('learning.reason'), dataIndex: 'reason', ellipsis: true },
  { title: t('learning.expectedEffect'), key: 'expected_effect', dataIndex: 'expected_effect', width: 200 },
]);

// --- Actions ---
async function runInference() {
  if (!recordingId.value.trim()) return;
  loading.value = true;
  error.value = null;
  result.value = null;
  judgments.value = {};
  expandedKey.value = null;
  try {
    result.value = await inferCandidates({
      recording_id: recordingId.value.trim(),
      run_id: runId.value.trim() || undefined,
      score_threshold: scoreThreshold.value,
      max_candidates: maxCandidates.value,
    });
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}

function markJudgment(key: string, value: 'reasonable' | 'unreasonable') {
  if (judgments.value[key] === value) {
    delete judgments.value[key];
    judgments.value = { ...judgments.value };
  } else {
    judgments.value = { ...judgments.value, [key]: value };
  }
}

function actionColor(action: string): string {
  switch (action) {
    case 'click': return 'blue';
    case 'input': return 'green';
    case 'select': return 'purple';
    case 'toggle': return 'orange';
    case 'hover': return 'cyan';
    default: return 'default';
  }
}

function scoreColor(score: number): string {
  if (score >= 0.8) return 'green';
  if (score >= 0.5) return 'blue';
  if (score >= 0.3) return 'orange';
  return 'default';
}
</script>
