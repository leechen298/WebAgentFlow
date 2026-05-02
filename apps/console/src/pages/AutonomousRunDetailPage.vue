<template>
  <div class="run-detail">
    <a-page-header
      :title="$t('autonomousHistory.detailPageTitle')"
      @back="() => $router.push('/exploration/autonomous/history')"
    >
      <template #extra>
        <a-button @click="copyJson">{{ $t('autonomousHistory.copyData') }}</a-button>
        <a-button
          type="primary"
          @click="reopenInWorkbench"
          :disabled="!workbenchUrl"
        >
          {{ $t('autonomousHistory.reopenInWorkbench') }}
        </a-button>
        <a-popconfirm
          :title="$t('autonomousHistory.deleteConfirmPrompt')"
          :ok-text="$t('common.confirm')"
          :cancel-text="$t('common.cancel')"
          @confirm="handleDelete"
        >
          <a-button danger :loading="deleting">
            {{ $t('autonomousHistory.deleteRun') }}
          </a-button>
        </a-popconfirm>
      </template>
    </a-page-header>

    <a-spin :spinning="loading">
      <div v-if="loadError" class="load-error">
        <a-alert
          type="error"
          show-icon
          :message="$t('autonomousHistory.loadFailed')"
          :description="loadError"
        />
      </div>

      <div v-else-if="detail">
        <!-- Run config summary — mirrors the workbench's input form
             but read-only, so the operator can see exactly what
             was sent. -->
        <a-card
          :title="$t('autonomousHistory.runConfigTitle')"
          :bordered="false"
          class="config-card"
        >
          <a-descriptions :column="{ xs: 1, sm: 2, md: 3 }" size="small" bordered>
            <a-descriptions-item :label="$t('autonomousHistory.colRunId')">
              <code>{{ detail.run_id }}</code>
            </a-descriptions-item>
            <a-descriptions-item :label="$t('autonomousHistory.colCreated')">
              {{ formatDate(detail.created_at) }}
            </a-descriptions-item>
            <a-descriptions-item :label="$t('autonomousHistory.colStatus')">
              <a-tag :color="statusColor(detail.status)">{{ detail.status }}</a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="URL" :span="3">
              <code>{{ strategy.url || '—' }}</code>
            </a-descriptions-item>
            <a-descriptions-item
              v-if="strategy.goal"
              :label="$t('autonomousHistory.goal')"
              :span="3"
            >
              {{ strategy.goal }}
            </a-descriptions-item>
            <a-descriptions-item
              v-if="strategy.spec_id"
              :label="$t('autonomousHistory.colSpec')"
            >
              {{ strategy.spec_id }}
            </a-descriptions-item>
            <a-descriptions-item
              v-if="strategy.scenario"
              :label="$t('autonomousHistory.colScenario')"
            >
              {{ strategy.scenario }}
            </a-descriptions-item>
            <a-descriptions-item :label="$t('autonomousHistory.headless')">
              {{ strategy.headless ? 'true' : 'false' }}
            </a-descriptions-item>
            <a-descriptions-item
              v-if="hasFillValues"
              :label="$t('autonomousHistory.fillValues')"
              :span="3"
            >
              <div
                v-for="(v, k) in strategy.fill_values"
                :key="k"
                class="kv-row"
              >
                <code>{{ k }}</code> = <code>{{ v }}</code>
              </div>
            </a-descriptions-item>
            <a-descriptions-item
              v-if="hasToggleValues"
              :label="$t('autonomousHistory.toggleValues')"
              :span="3"
            >
              <div
                v-for="(v, k) in strategy.toggle_values"
                :key="k"
                class="kv-row"
              >
                <code>{{ k }}</code> = <code>{{ v }}</code>
              </div>
            </a-descriptions-item>
          </a-descriptions>
        </a-card>

        <!-- Reused blocks — same components as the live workbench. -->
        <PageAnalysisBlock
          :analysis="pageAnalysis"
          style="margin-top: 16px"
        />
        <StepTimelineBlock
          :steps="steps"
          style="margin-top: 16px"
        />
        <VerificationBlock
          :self-assessment="selfAssessment"
          :supervisor="supervisor"
          :scorecard="scorecard"
          style="margin-top: 16px"
        />

        <!-- Run review — operator-level acceptance / rejection. -->
        <a-card
          :title="$t('autonomousHistory.runReviewTitle')"
          :bordered="false"
          style="margin-top: 16px"
          class="run-review-card"
        >
          <a-space :size="12" align="center" wrap>
            <span>{{ $t('autonomousHistory.runReviewStatus') }}:</span>
            <a-tag :color="reviewTagColor">
              {{ $t(reviewI18nKey) }}
            </a-tag>
          </a-space>
          <div v-if="operatorReviewNote" class="run-review-note">
            <span class="note-label">{{ $t('autonomousHistory.runReviewNoteLabel') }}:</span>
            {{ operatorReviewNote }}
          </div>
          <div class="run-review-actions">
            <a-popconfirm
              v-if="canAcceptRun"
              :title="$t('autonomousHistory.runReviewAcceptPrompt')"
              :ok-text="$t('autonomousHistory.runReviewAccept')"
              :cancel-text="$t('common.cancel')"
              @confirm="onAcceptRun"
            >
              <a-button
                type="primary"
                :loading="updatingReview && pendingReviewAction === 'accepted'"
              >
                {{ $t('autonomousHistory.runReviewAccept') }}
              </a-button>
            </a-popconfirm>
            <a-button
              v-else
              type="primary"
              disabled
              :loading="updatingReview && pendingReviewAction === 'accepted'"
            >
              {{ $t('autonomousHistory.runReviewAccept') }}
            </a-button>
            <a-popconfirm
              v-if="canRejectRun"
              :title="$t('autonomousHistory.runReviewRejectPrompt')"
              :ok-text="$t('autonomousHistory.runReviewReject')"
              :cancel-text="$t('common.cancel')"
              @confirm="onRejectRun"
            >
              <a-button
                danger
                :loading="updatingReview && pendingReviewAction === 'rejected'"
                style="margin-left: 8px"
              >
                {{ $t('autonomousHistory.runReviewReject') }}
              </a-button>
            </a-popconfirm>
            <a-button
              v-else
              danger
              disabled
              :loading="updatingReview && pendingReviewAction === 'rejected'"
              style="margin-left: 8px"
            >
              {{ $t('autonomousHistory.runReviewReject') }}
            </a-button>
          </div>
          <div class="run-review-hint">
            {{ $t('autonomousHistory.runReviewHint') }}
          </div>
        </a-card>

        <!-- LearnedPath — read-only association info. -->
        <a-card
          :title="$t('autonomousHistory.learnedPathTitle')"
          :bordered="false"
          style="margin-top: 16px"
          class="learned-path-card"
        >
          <div v-if="learnedPath">
            <div class="learned-path-hint">
              {{ $t('autonomousHistory.learnedPathHint') }}
            </div>
            <a-descriptions :column="{ xs: 1, sm: 2 }" size="small" bordered>
              <a-descriptions-item :label="$t('common.id')">
                <code>{{ learnedPath.id }}</code>
              </a-descriptions-item>
              <a-descriptions-item :label="$t('common.status')">
                <a-tag :color="trustTagColor">{{ $t(trustI18nKey) }}</a-tag>
              </a-descriptions-item>
              <a-descriptions-item :label="$t('autonomousHistory.learnedPathRelation')">
                {{ $t(relationI18nKey) }}
              </a-descriptions-item>
              <a-descriptions-item :label="$t('autonomousHistory.learnedPathHitCount')">
                {{ learnedPath.hit_count }}
              </a-descriptions-item>
              <a-descriptions-item :label="$t('common.source')">
                <code>{{ learnedPath.source_run_id || '—' }}</code>
              </a-descriptions-item>
            </a-descriptions>
            <div class="learned-path-actions">
              <a-popconfirm
                v-if="canConfirmLearnedPath"
                :title="$t('autonomousHistory.learnedPathConfirmPrompt')"
                :ok-text="$t('autonomousHistory.learnedPathConfirm')"
                :cancel-text="$t('common.cancel')"
                @confirm="onConfirmPath"
              >
                <a-button
                  type="primary"
                  :loading="updatingTrust && pendingPathAction === 'confirmed'"
                >
                  {{ $t('autonomousHistory.learnedPathConfirm') }}
                </a-button>
              </a-popconfirm>
              <a-button
                v-else
                type="primary"
                disabled
                :loading="updatingTrust && pendingPathAction === 'confirmed'"
              >
                {{ $t('autonomousHistory.learnedPathConfirm') }}
              </a-button>
              <a-popconfirm
                v-if="canDeprecateLearnedPath"
                :title="$t('autonomousHistory.learnedPathRejectPrompt')"
                :ok-text="$t('autonomousHistory.learnedPathMarkWrong')"
                :cancel-text="$t('common.cancel')"
                @confirm="onDeprecatePath"
              >
                <a-button
                  danger
                  :loading="updatingTrust && pendingPathAction === 'deprecated'"
                  style="margin-left: 8px"
                >
                  {{ $t('autonomousHistory.learnedPathMarkWrong') }}
                </a-button>
              </a-popconfirm>
              <a-button
                v-else
                danger
                disabled
                :loading="updatingTrust && pendingPathAction === 'deprecated'"
                style="margin-left: 8px"
              >
                {{ $t('autonomousHistory.learnedPathMarkWrong') }}
              </a-button>
            </div>
          </div>
          <div v-else class="learned-path-absent">
            {{ $t(absentMessageKey) }}
          </div>
        </a-card>

        <!-- Escape hatch: full raw JSON for operators who want to
             drop the whole payload into Claude Code or another
             tool. -->
        <a-card
          :title="$t('autonomousHistory.rawJsonTitle')"
          :bordered="false"
          style="margin-top: 16px"
        >
          <template #extra>
            <a-button size="small" @click="copyJson">
              {{ $t('autonomousHistory.copyData') }}
            </a-button>
          </template>
          <a-collapse ghost>
            <a-collapse-panel key="raw" :header="$t('autonomousHistory.rawJsonPanel')">
              <pre class="raw-json">{{ rawJson }}</pre>
            </a-collapse-panel>
          </a-collapse>
        </a-card>
      </div>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import {
  getAutonomousRun,
  deleteAutonomousRun,
  patchLearnedPathTrust,
  patchRunReview,
  type AutonomousRunDetail,
  type LearnedPathPatchStatus,
  type LearnedPathTrust,
  type OperatorReviewStatus,
  type RunLearnedPathProjection,
} from '@/api/exploration';
import PageAnalysisBlock from '@/components/autonomous/PageAnalysisBlock.vue';
import StepTimelineBlock from '@/components/autonomous/StepTimelineBlock.vue';
import VerificationBlock from '@/components/autonomous/VerificationBlock.vue';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();

const detail = ref<AutonomousRunDetail | null>(null);
const loading = ref(false);
const loadError = ref<string>('');

const learnedPath = ref<RunLearnedPathProjection | null>(null);
const learnedPathTrust = ref<LearnedPathTrust | null>(null);
const passGateStatus = ref<'pass' | 'fail' | 'unverified' | null>(null);
const operatorReviewStatus = ref<OperatorReviewStatus>('unreviewed');
const operatorReviewNote = ref<string | null>(null);

const updatingTrust = ref(false);
const pendingPathAction = ref<LearnedPathPatchStatus | null>(null);
const updatingReview = ref(false);
const pendingReviewAction = ref<OperatorReviewStatus | null>(null);
const deleting = ref(false);

/**
 * Pick the right "no LearnedPath" copy based on the run's gate
 * outcome. `pass` but no ingest = hook failed or predates the feature;
 * anything else is the documented "non-pass doesn't sink" behaviour.
 * Null falls back to the generic string for historical pre-gate rows.
 */
const absentMessageKey = computed(() => {
  if (passGateStatus.value === 'pass') {
    return 'autonomousHistory.learnedPathAbsentPassButMissing';
  }
  if (passGateStatus.value === 'fail' || passGateStatus.value === 'unverified') {
    return 'autonomousHistory.learnedPathAbsentNotPass';
  }
  return 'autonomousHistory.learnedPathAbsent';
});

const reviewI18nKey = computed(() => {
  switch (operatorReviewStatus.value) {
    case 'accepted':
      return 'autonomousHistory.reviewAccepted';
    case 'rejected':
      return 'autonomousHistory.reviewRejected';
    default:
      return 'autonomousHistory.reviewUnreviewed';
  }
});

const reviewTagColor = computed(() => {
  switch (operatorReviewStatus.value) {
    case 'accepted':
      return 'green';
    case 'rejected':
      return 'red';
    default:
      return 'default';
  }
});

const trustI18nKey = computed(() => {
  switch (learnedPathTrust.value) {
    case 'confirmed':
      return 'autonomousHistory.trustConfirmed';
    case 'flaky':
      return 'autonomousHistory.trustFlaky';
    case 'deprecated':
      return 'autonomousHistory.trustDeprecated';
    default:
      return 'autonomousHistory.trustProvisional';
  }
});

const trustTagColor = computed(() => {
  switch (learnedPathTrust.value) {
    case 'confirmed':
      return 'green';
    case 'deprecated':
      return 'red';
    case 'flaky':
      return 'orange';
    default:
      return 'blue';
  }
});

const relationI18nKey = computed(() => {
  switch (learnedPath.value?.relation) {
    case 'source':
      return 'autonomousHistory.relationSource';
    case 'dedup_hit':
      return 'autonomousHistory.relationDedupHit';
    default:
      return 'autonomousHistory.relationNone';
  }
});

const canAcceptRun = computed(
  () => operatorReviewStatus.value !== 'accepted' && !updatingReview.value,
);

const canRejectRun = computed(
  () => operatorReviewStatus.value !== 'rejected' && !updatingReview.value,
);

const canConfirmLearnedPath = computed(
  () => Boolean(learnedPath.value) && learnedPathTrust.value !== 'confirmed' && !updatingTrust.value,
);

const canDeprecateLearnedPath = computed(
  () => Boolean(learnedPath.value) && learnedPathTrust.value !== 'deprecated' && !updatingTrust.value,
);

// ─── Derived views over detail.result ────────────────────────
// `result` is the full AutonomousExplorationResult snapshot produced
// by the exploration run. Same shape the workbench SSE stream builds
// up; the detail page just slices it for the existing block
// components.

const strategy = computed<Record<string, unknown>>(
  () => (detail.value?.strategy as Record<string, unknown>) || {},
);

const result = computed<Record<string, unknown>>(
  () => (detail.value?.result as Record<string, unknown>) || {},
);

const pageAnalysis = computed<Record<string, unknown> | null>(() => {
  const r = result.value;
  return (r.page_analysis as Record<string, unknown>) || null;
});

const steps = computed<Array<Record<string, unknown>>>(() => {
  const r = result.value;
  return (r.steps as Array<Record<string, unknown>>) || [];
});

const selfAssessment = computed(() => {
  const r = result.value;
  // Rule-side self-assessment is stored as flat fields on the result,
  // not as a sub-object. Synthesize the shape VerificationBlock
  // expects.
  if (r.verdict === undefined && r.summary === undefined) return null;
  return {
    verdict: r.verdict as string | undefined,
    summary: r.summary as string | undefined,
    final_url: r.final_url as string | undefined,
    final_title: r.final_title as string | undefined,
  };
});

const supervisor = computed(() => {
  const r = result.value;
  return (r.supervisor as Record<string, unknown> | null) || null;
});

const scorecard = computed(() => {
  const r = result.value;
  const ver = r.verification as Record<string, unknown> | undefined;
  if (!ver) return null;
  return (ver.scorecard as Record<string, unknown>) || null;
});

const hasFillValues = computed(() => {
  const fv = strategy.value.fill_values as Record<string, unknown> | undefined;
  return fv && Object.keys(fv).length > 0;
});

const hasToggleValues = computed(() => {
  const tv = strategy.value.toggle_values as Record<string, unknown> | undefined;
  return tv && Object.keys(tv).length > 0;
});

const rawJson = computed(() => {
  if (!detail.value) return '';
  try {
    return JSON.stringify(detail.value, null, 2);
  } catch {
    return String(detail.value);
  }
});

// Deep-link back to the workbench with the same URL + scenario so
// the operator can re-run with the recorded inputs.
const workbenchUrl = computed<string | null>(() => {
  const url = strategy.value.url as string | undefined;
  if (!url) return null;
  const params = new URLSearchParams({ url });
  const scenario = strategy.value.scenario as string | undefined;
  if (scenario) params.set('scenario', scenario);
  const goal = strategy.value.goal as string | undefined;
  if (goal) params.set('goal', goal);
  return `/exploration/autonomous?${params.toString()}`;
});

// ─── Helpers ─────────────────────────────────────────────────

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function statusColor(status: string): string {
  if (status === 'succeeded' || status === 'success') return 'green';
  if (status === 'failed' || status === 'error') return 'red';
  if (status === 'running' || status === 'pending') return 'blue';
  return 'default';
}

async function copyJson(): Promise<void> {
  if (!rawJson.value) {
    message.warning(t('autonomousHistory.noDataToCopy'));
    return;
  }
  try {
    await navigator.clipboard.writeText(rawJson.value);
    message.success(t('autonomousHistory.copied', { bytes: rawJson.value.length }));
  } catch (err) {
    message.error(t('error.network') + ': ' + (err as Error).message);
  }
}

function reopenInWorkbench(): void {
  if (workbenchUrl.value) void router.push(workbenchUrl.value);
}

// ─── Load ────────────────────────────────────────────────────

async function load(): Promise<void> {
  const runId = String(route.params.run_id || '');
  if (!runId) {
    loadError.value = 'Missing run_id in URL';
    return;
  }
  loading.value = true;
  loadError.value = '';
  try {
    const fetched = await getAutonomousRun(runId);
    detail.value = fetched;
    learnedPath.value = fetched.learned_path ?? null;
    learnedPathTrust.value = fetched.learned_path_trust ?? null;
    passGateStatus.value = fetched.pass_gate_status ?? null;
    operatorReviewStatus.value = fetched.operator_review_status ?? 'unreviewed';
    operatorReviewNote.value = fetched.operator_review_note ?? null;
  } catch (err) {
    loadError.value = (err as Error).message || String(err);
  } finally {
    loading.value = false;
  }
}

async function updateReview(status: OperatorReviewStatus): Promise<void> {
  const runId = String(route.params.run_id || '');
  if (!runId || updatingReview.value) return;
  updatingReview.value = true;
  pendingReviewAction.value = status;
  try {
    const updated = await patchRunReview(runId, { status });
    operatorReviewStatus.value = updated.operator_review_status;
    operatorReviewNote.value = updated.operator_review_note;
    message.success(t('autonomousHistory.runReviewUpdated'));
  } catch (err) {
    message.error((err as Error).message || String(err));
  } finally {
    updatingReview.value = false;
    pendingReviewAction.value = null;
  }
}

function onAcceptRun(): void {
  void updateReview('accepted');
}

function onRejectRun(): void {
  void updateReview('rejected');
}

async function updatePathTrust(status: LearnedPathPatchStatus): Promise<void> {
  const pathId = learnedPath.value?.id;
  if (!pathId || updatingTrust.value) return;
  updatingTrust.value = true;
  pendingPathAction.value = status;
  try {
    const updated = await patchLearnedPathTrust(pathId, { status });
    learnedPathTrust.value = updated.trust as LearnedPathTrust;
    if (learnedPath.value) {
      learnedPath.value = { ...learnedPath.value, trust: updated.trust as LearnedPathTrust };
    }
    message.success(t('autonomousHistory.learnedPathUpdated'));
  } catch (err) {
    message.error((err as Error).message || String(err));
  } finally {
    updatingTrust.value = false;
    pendingPathAction.value = null;
  }
}

function onConfirmPath(): void {
  void updatePathTrust('confirmed');
}

function onDeprecatePath(): void {
  void updatePathTrust('deprecated');
}

async function handleDelete(): Promise<void> {
  const runId = String(route.params.run_id || '');
  if (!runId) return;
  deleting.value = true;
  try {
    await deleteAutonomousRun(runId);
    message.success(t('autonomousHistory.deleteSuccess'));
    void router.push('/exploration/autonomous/history');
  } catch (err) {
    message.error((err as Error).message || t('autonomousHistory.deleteFailed'));
  } finally {
    deleting.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.run-detail {
  padding-bottom: 40px;
}
.config-card {
  margin-top: 16px;
}
.load-error {
  margin-top: 16px;
}
.kv-row {
  font-size: 12px;
  margin-bottom: 2px;
}
.raw-json {
  font-size: 11px;
  max-height: 480px;
  overflow: auto;
  background: #fafafa;
  padding: 10px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-break: break-word;
}
.run-review-card :deep(.ant-card-body) {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.run-review-actions {
  margin-top: 8px;
}
.run-review-hint {
  font-size: 12px;
  color: #888;
}
.run-review-note {
  font-size: 12px;
  color: #555;
  margin-top: 4px;
}
.run-review-note .note-label {
  font-weight: 500;
}
.learned-path-card :deep(.ant-card-body) {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.learned-path-actions {
  margin-top: 8px;
}
.learned-path-hint {
  font-size: 12px;
  color: #888;
}
.learned-path-absent {
  color: #888;
  font-size: 13px;
}
</style>
