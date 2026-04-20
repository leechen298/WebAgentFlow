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
  type AutonomousRunDetail,
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
    detail.value = await getAutonomousRun(runId);
  } catch (err) {
    loadError.value = (err as Error).message || String(err);
  } finally {
    loading.value = false;
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
</style>
